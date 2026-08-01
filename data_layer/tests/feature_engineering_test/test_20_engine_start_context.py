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
)
from data_layer.pipeline_data.paths import RunLayout
from data_layer.tests.feature_engineering_test import (
    test_00_input_contract as fixture_00,
)
from data_layer.tests.feature_engineering_test import (
    test_10_atomic_features as fixture_10,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "data_layer/feature_engineering/src/20_engine_start_context_builder.py"
)
SPEC = importlib.util.spec_from_file_location(
    "script_20_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_20 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_20
SPEC.loader.exec_module(SCRIPT_20)


def _sequence_layout(
    tmp_path: Path,
    rpm: list[float],
    segments: list[str] | None = None,
) -> tuple[RunLayout, pd.DataFrame]:
    rows = len(rpm)
    segments = segments or ["trip_0001_seg_001"] * rows
    layout = RunLayout.for_run_id("script-20-test", repo_root=tmp_path)
    layout.operating_conditions_dir.mkdir(parents=True)
    layout.cleaning_dir.mkdir(parents=True)
    layout.feature_contract.parent.mkdir(parents=True)
    layout.feature_contract.write_bytes(
        (
            REPO_ROOT / "data_layer/contracts/feature_manifest.v1.json"
        ).read_bytes()
    )

    template = fixture_00._operating_fixture().iloc[0]
    operating = pd.DataFrame([template.to_dict() for _ in range(rows)])
    operating["timestamp"] = pd.date_range(
        "2026-01-01T00:00:00Z", periods=rows, freq="s"
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    operating["trip_id"] = "trip_0001"
    operating["segment_id"] = segments
    operating["row_in_segment"] = (
        operating.groupby("segment_id", sort=False).cumcount() + 1
    )
    operating["rpm"] = rpm
    operating["coolant_temp"] = [20.0 + index for index in range(rows)]
    operating["ambient_temp"] = [10.0 + index for index in range(rows)]
    operating["intake_temp"] = [15.0 + index for index in range(rows)]
    operating.to_csv(layout.operating_condition_enriched, index=False)

    quality_template = fixture_00._quality_fixture(
        fixture_00._operating_fixture()
    ).iloc[0]
    quality = pd.DataFrame([quality_template.to_dict() for _ in range(rows)])
    quality[SCRIPT_20.KEY_COLUMNS] = operating[SCRIPT_20.KEY_COLUMNS]
    quality["source_file"] = "a.csv"
    quality["source_sample_count"] = rows
    quality.to_csv(layout.cleaning_quality, index=False)
    return layout, quality


def _run_upstream(layout: RunLayout) -> None:
    fixture_00.SCRIPT_00.run_input_contract_validation(
        layout,
        creation_time_utc="2026-07-19T12:00:00Z",
    )
    fixture_10.SCRIPT_10.run_atomic_feature_builder(
        layout,
        creation_time_utc="2026-07-19T12:01:00Z",
    )


def test_multiple_starts_invalid_rpm_and_foreign_key_mapping(
    tmp_path: Path,
) -> None:
    layout, quality = _sequence_layout(
        tmp_path,
        [0, 0, 50, 100, 100, 0, 0, 60, 60, 60, 60, 0],
    )
    quality.loc[7, "coolant_temp_is_suspicious"] = True
    quality.loc[7, "is_suspicious_any"] = True
    quality.loc[9, "rpm_is_suspicious"] = True
    quality.loc[9, "is_suspicious_any"] = True
    quality.to_csv(layout.cleaning_quality, index=False)
    _run_upstream(layout)

    inputs = SCRIPT_20.load_engine_start_inputs(layout)
    context, episodes = SCRIPT_20.build_engine_start_context(inputs)

    observed_indexes = context["engine_start_observed"].eq(True)
    assert observed_indexes.loc[lambda value: value].index.tolist() == [2, 7]
    assert pd.isna(context.loc[9, "engine_start_observed"])
    assert context.loc[10, "engine_start_observed"] == False  # noqa: E712
    assert context.loc[2:4, "engine_start_episode_id"].tolist() == [
        "trip_0001_start_001"
    ] * 3
    assert context.loc[7:8, "engine_start_episode_id"].tolist() == [
        "trip_0001_start_002"
    ] * 2
    assert context.loc[
        [0, 1, 5, 6, 9, 10, 11], "engine_start_episode_id"
    ].isna().all()
    assert context.loc[2:4, "elapsed_since_engine_start"].tolist() == [
                                                                 0.0, 1.0, 2.0]
    assert context.loc[7:8, "elapsed_since_engine_start"].tolist() == [
                                                                 0.0, 1.0]

    assert episodes["engine_start_episode_id"].tolist() == [
        "trip_0001_start_001",
        "trip_0001_start_002",
    ]
    assert episodes["termination_reason"].tolist() == [
        "rpm_below_50",
        "rpm_invalid",
    ]
    assert episodes["episode_sample_count"].tolist() == [3, 2]
    assert episodes["episode_duration_seconds"].tolist() == [2.0, 1.0]
    episode_start_columns = ["ect_start", "aat_start", "iat_start"]
    assert episodes.loc[0, episode_start_columns].tolist() == [
        22.0,
        12.0,
        17.0,
    ]
    assert pd.isna(episodes.loc[1, "ect_start"])
    assert episodes.loc[1, "aat_start"] == 17.0
    assert episodes.loc[1, "iat_start"] == 22.0
    for column in ("ect_start", "aat_start", "iat_start"):
        mapped = context["engine_start_episode_id"].map(
            episodes.set_index("engine_start_episode_id")[column]
        )
        pd.testing.assert_series_equal(
            context[column], mapped, check_names=False)


def test_segment_boundary_cannot_create_an_observed_start(
    tmp_path: Path,
) -> None:
    segments = ["trip_0001_seg_001"] * 3 + ["trip_0001_seg_002"] * 3
    layout, _ = _sequence_layout(
        tmp_path,
        [0, 0, 0, 60, 0, 60],
        segments,
    )
    _run_upstream(layout)

    context, episodes = SCRIPT_20.build_engine_start_context(
        SCRIPT_20.load_engine_start_inputs(layout)
    )

    observed_indexes = context["engine_start_observed"].eq(True)
    assert observed_indexes.loc[lambda value: value].index.tolist() == [5]
    assert pd.isna(context.loc[3, "engine_start_episode_id"])
    assert episodes["start_row_in_segment"].tolist() == [3]
    assert episodes["termination_reason"].tolist() == ["end_of_data"]


def test_context_and_episode_outputs_have_distinct_grains_and_manifest(
    tmp_path: Path,
) -> None:
    layout, _ = _sequence_layout(tmp_path, [0, 50, 100, 0])
    _run_upstream(layout)

    context, episodes, manifest = SCRIPT_20.run_engine_start_context_builder(
        layout,
        creation_time_utc="2026-07-19T12:02:00Z",
    )

    assert len(context) == 4
    assert len(episodes) == 1
    assert list(context.columns) == [
        *SCRIPT_20.KEY_COLUMNS,
        *SCRIPT_20.B2_COLUMNS,
    ]
    assert list(episodes.columns) == SCRIPT_20.EPISODE_COLUMNS
    assert not episodes.duplicated(
        ["trip_id", "engine_start_episode_id"]).any()
    assert [
        item["artifact_id"] for item in manifest["ordered_output_artifacts"]
    ] == ["engine_start_context", "engine_start_episodes"]
    assert manifest["calibration_version"] == "not_applicable"
    assert manifest["output_contract"]["sample_table"]["row_count"] == 4
    assert manifest["output_contract"]["episode_table"]["row_count"] == 1
    verify_manifest_artifacts(
        manifest,
        run_dir=layout.run_dir,
        repo_root=layout.repo_root,
    )


def test_atomic_checksum_drift_is_rejected(tmp_path: Path) -> None:
    layout, _ = _sequence_layout(tmp_path, [0, 50, 100])
    _run_upstream(layout)
    with layout.atomic_features.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        SCRIPT_20.load_engine_start_inputs(layout)


def test_b2_contract_drift_is_rejected(tmp_path: Path) -> None:
    layout, _ = _sequence_layout(tmp_path, [0, 50, 100])
    _run_upstream(layout)
    contract = load_json_object(layout.feature_contract)
    contract["features"][10]["dtype"] = "float64"

    with pytest.raises(
        SCRIPT_20.EngineStartError, match="contract has drifted"
    ):
        SCRIPT_20._validate_b2_contract(contract)
