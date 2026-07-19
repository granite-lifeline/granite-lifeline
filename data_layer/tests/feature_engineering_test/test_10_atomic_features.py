from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

from data_layer.pipeline_data.manifests import (
    ManifestValidationError,
    load_json_object,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.tests.feature_engineering_test import (
    test_00_input_contract as fixture_00,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "data_layer/feature_engineering/src/10_atomic_feature_builder.py"
)
SPEC = importlib.util.spec_from_file_location(
    "script_10_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_10 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_10
SPEC.loader.exec_module(SCRIPT_10)


def _prepared_layout(tmp_path: Path):
    layout = fixture_00._layout_with_inputs(tmp_path)
    fixture_00.SCRIPT_00.run_input_contract_validation(
        layout,
        creation_time_utc="2026-07-19T12:00:00Z",
    )
    return layout


def test_eight_atomic_formulas_and_quality_boundaries_are_deterministic(
    tmp_path: Path,
) -> None:
    layout = fixture_00._layout_with_inputs(tmp_path)
    operating = pd.read_csv(layout.operating_condition_enriched)
    operating.loc[:2, "rpm"] = [0.0, 50.0, 100.0]
    operating.loc[:2, "accel_pedal_d"] = [10.0, 12.0, 14.0]
    operating.loc[:2, "accel_pedal_e"] = [20.0, 22.0, 24.0]
    operating.to_csv(layout.operating_condition_enriched, index=False)

    quality = pd.read_csv(layout.cleaning_quality)
    quality.loc[1, "rpm_is_suspicious"] = True
    quality.loc[1, "is_suspicious_any"] = True
    quality.loc[1, "accel_pedal_d_is_imputed"] = True
    quality.loc[1, "is_imputed_any"] = True
    quality.to_csv(layout.cleaning_quality, index=False)
    fixture_00.SCRIPT_00.run_input_contract_validation(
        layout,
        creation_time_utc="2026-07-19T12:00:00Z",
    )

    inputs = SCRIPT_10.load_atomic_inputs(layout)
    output = SCRIPT_10.build_atomic_features(inputs)

    assert list(output.columns) == [
        *SCRIPT_10.KEY_COLUMNS,
        *SCRIPT_10.ATOMIC_FEATURE_COLUMNS,
    ]
    assert output["engine_on_flag"].tolist()[:3] == [False, pd.NA, True]
    assert output["coolant_ambient_delta"].tolist()[:3] == [60.0, 60.0, 60.0]
    assert output["intake_ambient_delta"].tolist()[:3] == [10.0, 10.0, 10.0]
    assert output["accel_pedal_mean"].iloc[0] == 15.0
    assert pd.isna(output["accel_pedal_mean"].iloc[1])
    assert output["accel_pedal_mean"].iloc[2] == 19.0
    assert output["accel_pedal_channel_delta"].iloc[0] == 10.0
    assert pd.isna(output["accel_pedal_channel_delta"].iloc[1])
    assert output["accel_pedal_channel_delta"].iloc[2] == 10.0
    assert output["pedal_slope"].iloc[:4].isna().all()
    assert output["pedal_slope"].iloc[4:].tolist() == [0.0, 0.0]
    assert output["rpm_slope"].iloc[:4].isna().all()
    assert output["rpm_slope"].iloc[4:].tolist() == [0.0, 0.0]

    assert pd.isna(output["segment_gap_seconds"].iloc[0])
    assert output["segment_gap_seconds"].iloc[3] == 86398.0
    assert output["segment_gap_seconds"].notna().sum() == 1


def test_atomic_output_and_manifest_are_portable_and_complete(
    tmp_path: Path,
) -> None:
    layout = _prepared_layout(tmp_path)

    output, manifest = SCRIPT_10.run_atomic_feature_builder(
        layout,
        creation_time_utc="2026-07-19T12:01:00Z",
    )

    assert layout.atomic_features.is_file()
    assert layout.atomic_features_manifest.is_file()
    stored = load_json_object(layout.atomic_features_manifest)
    assert stored == manifest
    assert manifest["stage_id"] == "10"
    assert manifest["calibration_version"] == "not_applicable"
    assert manifest["source_dataset_identity"] == load_json_object(
        layout.input_contract_manifest
    )["source_dataset_identity"]
    assert [
        item["artifact_id"] for item in manifest["ordered_input_artifacts"]
    ] == [
        "feature_contract",
        "input_contract_manifest",
        "operating_condition_enriched",
        "cleaning_quality",
    ]
    assert [
        item["artifact_id"] for item in manifest["ordered_output_artifacts"]
    ] == ["atomic_features"]
    assert manifest["output_contract"]["ordered_columns"] == list(
        output.columns)
    assert len(manifest["output_contract"]["feature_columns"]) == 8
    assert not any(
        item["artifact_id"] == "calibration_registry"
        for item in manifest["ordered_input_artifacts"]
    )
    verify_manifest_artifacts(
        manifest,
        run_dir=layout.run_dir,
        repo_root=layout.repo_root,
    )


def test_changed_authoritative_input_fails_script_00_checksum(
    tmp_path: Path,
) -> None:
    layout = _prepared_layout(tmp_path)
    with layout.operating_condition_enriched.open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write("\n")

    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        SCRIPT_10.load_atomic_inputs(layout)


def test_wrong_or_incomplete_stage_00_manifest_is_rejected(
    tmp_path: Path,
) -> None:
    layout = _prepared_layout(tmp_path)
    manifest = load_json_object(layout.input_contract_manifest)
    manifest["stage_id"] = "10"
    write_json_atomic(layout.input_contract_manifest, manifest)

    with pytest.raises(SCRIPT_10.AtomicFeatureError, match="stage 00"):
        SCRIPT_10.load_atomic_inputs(layout)


def test_atomic_contract_name_or_owner_drift_is_rejected(
    tmp_path: Path,
) -> None:
    layout = _prepared_layout(tmp_path)
    contract = load_json_object(layout.feature_contract)
    contract["features"][0]["owner_script"] = "different_builder.py"

    with pytest.raises(
        SCRIPT_10.AtomicFeatureError, match="contract has drifted"
    ):
        SCRIPT_10._validate_atomic_feature_contract(contract)
