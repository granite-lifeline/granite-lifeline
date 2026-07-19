from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from data_layer.pipeline_data.manifests import (
    ArtifactDescriptor,
    compute_source_dataset_identity,
    load_json_object,
    verify_manifest_artifacts,
)
from data_layer.pipeline_data.paths import RunLayout


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "data_layer/feature_engineering/src/00_input_contract_validator.py"
)
SPEC = importlib.util.spec_from_file_location(
    "script_00_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_00 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_00
SPEC.loader.exec_module(SCRIPT_00)


def _operating_fixture() -> pd.DataFrame:
    timestamps = [
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:00:01Z",
        "2026-01-01T00:00:02Z",
        "2026-01-02T00:00:00Z",
        "2026-01-02T00:00:01Z",
        "2026-01-02T00:00:02Z",
    ]
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "trip_id": ["trip_0001"] * 3 + ["trip_0002"] * 3,
            "segment_id": ["trip_0001_seg_001"] * 3
            + ["trip_0002_seg_001"] * 3,
            "row_in_segment": [1, 2, 3, 1, 2, 3],
            "dt_seconds": [1.0] * 6,
            "thermal_state": ["post_warmup"] * 6,
            "child_state": ["idle"] * 6,
            "operating_state": ["post_warmup__idle"] * 6,
            "condition_confidence": ["high"] * 6,
            "condition_quality_flags": ["OK"] * 6,
        }
    )
    values = {
        "coolant_temp": 80.0,
        "map": 45.0,
        "rpm": 800.0,
        "speed": 0.0,
        "intake_temp": 30.0,
        "maf": 4.0,
        "tps": 15.0,
        "ambient_temp": 20.0,
        "accel_pedal_d": 10.0,
        "accel_pedal_e": 10.0,
    }
    for signal, value in values.items():
        frame[signal] = value
    return frame[
        [
            *SCRIPT_00.KEY_COLUMNS,
            *SCRIPT_00.SIGNAL_COLUMNS,
            *SCRIPT_00.OPERATING_CONTEXT_COLUMNS,
        ]
    ]


def _quality_fixture(operating: pd.DataFrame) -> pd.DataFrame:
    rows = len(operating)
    frame = operating[SCRIPT_00.KEY_COLUMNS].copy()
    frame["source_file"] = ["a.csv"] * 3 + ["b.csv"] * 3
    for column in (
        "brand",
        "model",
        "origin",
        "destination",
        "route",
        "condition",
    ):
        frame[column] = "fixture"
    frame["route_sequence"] = pd.NA
    frame["source_extension"] = ".csv"
    frame["source_timestamp_was_monotonic"] = True
    frame["source_sample_count"] = [3] * rows
    frame["observed_sensor_count"] = len(SCRIPT_00.SIGNAL_COLUMNS)
    for column in SCRIPT_00.PER_SIGNAL_QUALITY_COLUMNS:
        frame[column] = False
    frame["is_imputed_any"] = False
    frame["is_suspicious_any"] = False
    frame["had_hard_invalid_source_any"] = False
    frame["quality_flags"] = pd.NA
    return frame[SCRIPT_00.QUALITY_COLUMNS]


def _layout_with_inputs(tmp_path: Path) -> RunLayout:
    layout = RunLayout.for_run_id("script-00-test", repo_root=tmp_path)
    layout.operating_conditions_dir.mkdir(parents=True)
    layout.cleaning_dir.mkdir(parents=True)
    layout.feature_contract.parent.mkdir(parents=True)
    layout.feature_contract.write_bytes(
        (
            REPO_ROOT / "data_layer/contracts/feature_manifest.v1.json"
        ).read_bytes()
    )
    operating = _operating_fixture()
    quality = _quality_fixture(operating)
    operating.to_csv(layout.operating_condition_enriched, index=False)
    quality.to_csv(layout.cleaning_quality, index=False)
    return layout


def _validate(layout: RunLayout):
    return SCRIPT_00.validate_authoritative_inputs(
        layout, load_json_object(layout.feature_contract)
    )


def test_valid_inputs_are_one_to_one_and_restored_to_global_order(
    tmp_path: Path,
) -> None:
    layout = _layout_with_inputs(tmp_path)
    operating = pd.read_csv(layout.operating_condition_enriched)
    quality = pd.read_csv(layout.cleaning_quality)
    operating.sample(frac=1, random_state=7).to_csv(
        layout.operating_condition_enriched, index=False
    )
    quality.sample(frac=1, random_state=11).to_csv(
        layout.cleaning_quality, index=False
    )

    validated = _validate(layout)

    expected_keys = operating[SCRIPT_00.KEY_COLUMNS].sort_values(
        SCRIPT_00.KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        validated.ordered_keys,
        expected_keys,
        check_dtype=False,
    )
    pd.testing.assert_frame_equal(
        validated.canonical[SCRIPT_00.KEY_COLUMNS],
        validated.quality[SCRIPT_00.KEY_COLUMNS],
    )
    assert validated.trip_count == 2
    assert validated.segment_count == 2
    assert validated.continuity_block_count == 2


def test_manifest_records_only_two_data_authorities_and_portable_hashes(
    tmp_path: Path,
) -> None:
    layout = _layout_with_inputs(tmp_path)

    validated, manifest = SCRIPT_00.run_input_contract_validation(
        layout,
        creation_time_utc="2026-07-19T12:00:00Z",
    )

    stored = load_json_object(layout.input_contract_manifest)
    assert stored == manifest
    assert manifest["stage_id"] == "00"
    assert manifest["calibration_version"] == "not_applicable"
    assert manifest["ordered_output_artifacts"] == []
    assert [
        item["artifact_id"] for item in manifest["ordered_input_artifacts"]
    ] == [
        "feature_contract",
        "operating_condition_enriched",
        "cleaning_quality",
    ]
    data_descriptors = [
        ArtifactDescriptor.from_mapping(item)
        for item in manifest["ordered_input_artifacts"]
        if item["artifact_id"] != "feature_contract"
    ]
    assert manifest["source_dataset_identity"] == (
        compute_source_dataset_identity(data_descriptors)
    )
    assert manifest["validation_summary"]["row_count"] == len(
        validated.ordered_keys
    )
    verify_manifest_artifacts(
        manifest,
        run_dir=layout.run_dir,
        repo_root=layout.repo_root,
    )
    assert "\\" not in json.dumps(manifest)


def test_missing_required_column_is_rejected(tmp_path: Path) -> None:
    layout = _layout_with_inputs(tmp_path)
    frame = pd.read_csv(
        layout.operating_condition_enriched).drop(columns=["rpm"])
    frame.to_csv(layout.operating_condition_enriched, index=False)

    with pytest.raises(SCRIPT_00.InputContractError, match="missing required"):
        _validate(layout)


@pytest.mark.parametrize(
    "bad_timestamp",
    [
        "2026-01-01T00:00:00.000000Z",
        "2026-01-01 00:00:00+00:00",
        "2026-01-01T00:00:00",
    ],
)
def test_noncanonical_timestamp_text_is_rejected(
    tmp_path: Path,
    bad_timestamp: str,
) -> None:
    layout = _layout_with_inputs(tmp_path)
    frame = pd.read_csv(layout.operating_condition_enriched)
    frame.loc[0, "timestamp"] = bad_timestamp
    frame.to_csv(layout.operating_condition_enriched, index=False)

    with pytest.raises(SCRIPT_00.InputContractError, match="YYYY-MM-DD"):
        _validate(layout)


def test_duplicate_or_mismatched_keys_are_rejected(tmp_path: Path) -> None:
    layout = _layout_with_inputs(tmp_path)
    frame = pd.read_csv(layout.cleaning_quality)
    frame.loc[1, SCRIPT_00.KEY_COLUMNS] = frame.loc[
        0, SCRIPT_00.KEY_COLUMNS
    ].to_numpy()
    frame.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(SCRIPT_00.InputContractError, match="duplicate"):
        _validate(layout)

    layout = _layout_with_inputs(tmp_path / "mismatch")
    frame = pd.read_csv(layout.cleaning_quality)
    frame.loc[0, "timestamp"] = "2026-01-01T00:00:10Z"
    frame.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(SCRIPT_00.InputContractError, match="key sets differ"):
        _validate(layout)


def test_gap_and_non_one_based_rows_are_rejected(tmp_path: Path) -> None:
    layout = _layout_with_inputs(tmp_path)
    operating = pd.read_csv(layout.operating_condition_enriched)
    quality = pd.read_csv(layout.cleaning_quality)
    operating.loc[1, "timestamp"] = "2026-01-01T00:00:05Z"
    quality.loc[1, "timestamp"] = "2026-01-01T00:00:05Z"
    operating.to_csv(layout.operating_condition_enriched, index=False)
    quality.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(SCRIPT_00.InputContractError, match="1 Hz"):
        _validate(layout)

    layout = _layout_with_inputs(tmp_path / "rows")
    operating = pd.read_csv(layout.operating_condition_enriched)
    quality = pd.read_csv(layout.cleaning_quality)
    operating.loc[0, "row_in_segment"] = 0
    quality.loc[0, "row_in_segment"] = 0
    operating.to_csv(layout.operating_condition_enriched, index=False)
    quality.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(
        SCRIPT_00.InputContractError, match="positive integers"
    ):
        _validate(layout)


def test_trip_source_identity_and_quality_aggregates_are_rejected_on_drift(
    tmp_path: Path,
) -> None:
    layout = _layout_with_inputs(tmp_path)
    quality = pd.read_csv(layout.cleaning_quality)
    quality.loc[3:, "source_file"] = "a.csv"
    quality.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(SCRIPT_00.InputContractError, match="one-to-one"):
        _validate(layout)

    layout = _layout_with_inputs(tmp_path / "aggregate")
    quality = pd.read_csv(layout.cleaning_quality)
    quality.loc[0, "rpm_is_imputed"] = True
    quality.to_csv(layout.cleaning_quality, index=False)
    with pytest.raises(SCRIPT_00.InputContractError, match="is_imputed_any"):
        _validate(layout)


def test_frozen_unit_contract_drift_is_rejected(tmp_path: Path) -> None:
    layout = _layout_with_inputs(tmp_path)
    contract = load_json_object(layout.feature_contract)
    rpm = next(
        item for item in contract["context_fields"] if item["name"] == "rpm"
    )
    rpm["unit"] = "revolutions_per_second"

    with pytest.raises(
        SCRIPT_00.InputContractError, match="contract has drifted"
    ):
        SCRIPT_00.validate_authoritative_inputs(layout, contract)
