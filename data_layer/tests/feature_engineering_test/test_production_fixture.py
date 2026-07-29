from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_layer.pipeline_data.manifests import (
    load_json_object,
    ordered_column_contract_from_feature_manifest,
    sha256_file,
    validate_ordered_column_contract,
)
from data_layer.tests.feature_engineering_test import (
    test_41_production_assembler as fixture_41,
)
from data_layer.tests.fixtures import generate_production_fixture as generator


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "data_layer/tests/fixtures"
CSV_PATH = FIXTURE_DIR / "production_features.v1.fixture.csv"
MANIFEST_PATH = FIXTURE_DIR / "production_features.v1.fixture.manifest.json"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]


def _contains_key(frame: pd.DataFrame, key: dict) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for name in KEYS:
        mask &= frame[name].eq(key[name])
    return mask


def test_tracked_fixture_matches_frozen_script_41_contract() -> None:
    frame = pd.read_csv(CSV_PATH, low_memory=False)
    fixture_manifest = load_json_object(MANIFEST_PATH)
    contract = load_json_object(
        REPO_ROOT / "data_layer/contracts/feature_manifest.v1.json"
    )
    expected_fields = ordered_column_contract_from_feature_manifest(contract)
    actual_fields = fixture_manifest["ordered_column_contract"]

    validate_ordered_column_contract(actual_fields, expected_fields)
    groups = fixture_41.SCRIPT_41._feature_groups(contract)
    assert list(frame.columns) == groups["all"]
    assert len(frame.columns) == 46
    assert 1 <= len(frame) <= 300
    assert CSV_PATH.stat().st_size < 500_000
    assert fixture_manifest["row_count"] == len(frame)
    assert fixture_manifest["fixture_artifact"]["sha256"] == sha256_file(
        CSV_PATH)
    assert fixture_manifest["schema_version"] == "feature_schema.v1"
    assert fixture_manifest["calibration_version"] == "calibration.v1"
    normalized = fixture_41.SCRIPT_41._normalize_and_validate_dtypes(
        frame, contract
    )
    assert not normalized[KEYS].duplicated().any()
    assert normalized[KEYS].equals(
        normalized.sort_values(
            KEYS, kind="stable").reset_index(drop=True)[KEYS]
    )


def test_fixture_covers_null_episode_boundary_and_quality_cases() -> None:
    frame = pd.read_csv(CSV_PATH, low_memory=False)
    manifest = load_json_object(MANIFEST_PATH)
    coverage = manifest["coverage"]
    episode = coverage["complete_engine_start_episode"]
    episode_rows = frame[frame["engine_start_episode_id"].eq(
        episode["episode_id"])]

    assert episode["episode_id"] == generator.EPISODE_ID
    assert episode["termination_reason"] == "continuity_break"
    assert len(episode_rows) == episode["source_episode_sample_count"]
    assert len(episode_rows) == episode["fixture_episode_sample_count"]
    assert episode_rows["engine_start_observed"].eq(True).sum() == 1
    assert episode_rows["elapsed_since_engine_start"].iloc[0] == 0.0
    assert episode_rows["elapsed_since_engine_start"].iloc[-1] > 180.0
    assert episode_rows["ect_start"].notna().all()
    assert episode_rows["maf_integral_180s"].notna().any()
    assert frame["engine_start_episode_id"].isna().any()

    incomplete_key = coverage["incomplete_window_sample"]
    complete_key = coverage["complete_maf_window_sample"]
    pedal_key = coverage["missing_pedal_channel_sample"]
    boundary_key = coverage["segment_first_with_gap"]
    incomplete = frame.loc[_contains_key(frame, incomplete_key)].iloc[0]
    complete = frame.loc[_contains_key(frame, complete_key)].iloc[0]
    pedal = frame.loc[_contains_key(frame, pedal_key)].iloc[0]
    boundary = frame.loc[_contains_key(frame, boundary_key)].iloc[0]
    assert pd.isna(incomplete["maf_integral_180s"])
    assert pd.notna(complete["maf_integral_180s"])
    assert pd.isna(pedal["accel_pedal_d"]) or pd.isna(pedal["accel_pedal_e"])
    assert pd.isna(pedal["accel_pedal_mean"])
    assert pd.isna(pedal["pedal_mapping_residual"])
    assert boundary["row_in_segment"] == 1
    assert pd.notna(boundary["segment_gap_seconds"])
    assert _contains_key(frame, coverage["quality_valid_sample"]).sum() == 1
    assert coverage["quality_invalid_samples"]
    assert all(
        _contains_key(frame, key).sum() == 1
        for key in coverage["quality_invalid_samples"]
    )


def test_fixture_generation_policy_is_fixed_and_portable() -> None:
    manifest = load_json_object(MANIFEST_PATH)
    policy = manifest["selection_policy"]
    provenance = manifest["source_provenance"]

    assert policy["engine_start_episode_id"] == generator.EPISODE_ID
    assert policy["additional_fixed_sample_key"] == generator.BOUNDARY_KEY
    assert policy["include_full_episode"] is True
    assert policy["include_immediate_global_neighbors"] is True
    assert policy["final_order"] == KEYS
    assert provenance["run_id"] == "2026-07-19-data-layer-v1"
    assert not Path(provenance["production_features_path"]).is_absolute()
    assert not Path(provenance["production_manifest_path"]).is_absolute()
