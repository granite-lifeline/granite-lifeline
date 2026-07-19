from __future__ import annotations

import dataclasses
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
from data_layer.tests.feature_engineering_test import (
    test_20_engine_start_context as fixture_20,
)
from data_layer.tests.feature_engineering_test import (
    test_30_window_features as fixture_30,
)
from data_layer.tests.feature_engineering_test import (
    test_40_calibrated_features as fixture_40,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "data_layer/feature_engineering/src/41_production_feature_assembler.py"
)
SPEC = importlib.util.spec_from_file_location(
    "script_41_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_41 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_41
SPEC.loader.exec_module(SCRIPT_41)


def _production_layout(tmp_path: Path):
    rows = 241
    layout, _ = fixture_20._sequence_layout(
        tmp_path, [0.0, *([100.0] * (rows - 1))]
    )
    layout.calibration_registry.parent.mkdir(parents=True)
    layout.calibration_registry.write_bytes(
        (
            REPO_ROOT / "data_layer/calibration/calibration_registry.v1.json"
        ).read_bytes()
    )
    layout.calibration_release_manifest.write_bytes(
        (
            REPO_ROOT
            / "data_layer/calibration/calibration_registry.v1.manifest.json"
        ).read_bytes()
    )
    fixture_20._run_upstream(layout)
    fixture_20.SCRIPT_20.run_engine_start_context_builder(
        layout, creation_time_utc="2026-07-19T12:02:00Z"
    )
    fixture_30.SCRIPT_30.run_window_feature_builder(
        layout, creation_time_utc="2026-07-19T12:03:00Z"
    )
    fixture_40.SCRIPT_40.run_calibrated_feature_builder(
        layout, creation_time_utc="2026-07-19T12:04:00Z"
    )
    return layout


def test_exact_46_column_order_pass_through_and_provenance(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    inputs = SCRIPT_41.load_production_inputs(layout)
    output = SCRIPT_41.build_production_features(inputs)
    groups = SCRIPT_41._feature_groups(inputs.feature_contract)

    assert list(output.columns) == groups["all"]
    assert len(output.columns) == 46
    assert len(groups["context"]) == 16
    assert len(groups["features"]) == 24
    pd.testing.assert_frame_equal(
        output[[*SCRIPT_41.KEY_COLUMNS, *groups["context"]]],
        inputs.canonical[[*SCRIPT_41.KEY_COLUMNS, *groups["context"]]],
        check_dtype=False,
    )
    assert output["schema_version"].eq("feature_schema.v1").all()
    assert output["calibration_version"].eq("calibration.v1").all()
    assert output["timestamp"].str.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
    ).all()


def test_shuffled_one_to_one_inputs_restore_identical_global_order(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    inputs = SCRIPT_41.load_production_inputs(layout)
    expected = SCRIPT_41.build_production_features(inputs)
    shuffled = dataclasses.replace(
        inputs,
        atomic=inputs.atomic.sample(
            frac=1, random_state=1).reset_index(drop=True),
        calibrated=inputs.calibrated.sample(
            frac=1, random_state=2).reset_index(drop=True),
        engine_start_context=inputs.engine_start_context.sample(
            frac=1, random_state=3
        ).reset_index(drop=True),
        windows=inputs.windows.sample(
            frac=1, random_state=4).reset_index(drop=True),
        engine_start_episodes=inputs.engine_start_episodes.sample(
            frac=1, random_state=5
        ).reset_index(drop=True),
    )

    actual = SCRIPT_41.build_production_features(shuffled)

    pd.testing.assert_frame_equal(actual, expected)


def test_unexpected_columns_and_invalid_dtype_are_rejected(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    inputs = SCRIPT_41.load_production_inputs(layout)
    atomic_extra = inputs.atomic.assign(research_diagnostic=1.0)
    with pytest.raises(SCRIPT_41.ProductionAssemblyError, match="unexpected"):
        SCRIPT_41.build_production_features(
            dataclasses.replace(inputs, atomic=atomic_extra)
        )

    atomic_bad = inputs.atomic.copy()
    boolean_position = list(atomic_bad.columns).index("engine_on_flag")
    bad_values = atomic_bad.pop("engine_on_flag").astype("object")
    bad_values.iloc[0] = "maybe"
    atomic_bad.insert(boolean_position, "engine_on_flag", bad_values)
    with pytest.raises(
        SCRIPT_41.ProductionAssemblyError, match="invalid boolean"
    ):
        SCRIPT_41.build_production_features(
            dataclasses.replace(inputs, atomic=atomic_bad)
        )


def test_episode_foreign_key_and_start_mapping_are_revalidated(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    inputs = SCRIPT_41.load_production_inputs(layout)
    context = inputs.engine_start_context.copy()
    first_reference = context["engine_start_episode_id"].first_valid_index()
    assert first_reference is not None
    context.loc[
        first_reference, "engine_start_episode_id"
    ] = "trip_0001_start_999"

    with pytest.raises(SCRIPT_41.ProductionAssemblyError, match="orphan"):
        SCRIPT_41.build_production_features(
            dataclasses.replace(inputs, engine_start_context=context)
        )


def test_manifest_records_strict_schema_and_all_direct_inputs(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    output, manifest = SCRIPT_41.run_production_feature_assembler(
        layout, creation_time_utc="2026-07-19T12:05:00Z"
    )

    assert len(output) == 241
    assert manifest["schema_version"] == "feature_schema.v1"
    assert manifest["calibration_version"] == "calibration.v1"
    contract = manifest["output_contract"]
    assert contract["total_column_count"] == 46
    assert contract["context_field_count"] == 16
    assert contract["feature_count"] == 24
    assert contract["provenance_column_count"] == 2
    assert contract["strict_allowlist_enforced"] is True
    assert contract["assembler_imputation_performed"] is False
    assert contract["episode_foreign_keys_validated"] is True
    assert [
        item["artifact_id"] for item in manifest["ordered_input_artifacts"]
    ] == [
        "feature_contract",
        "stage_00_manifest",
        "stage_10_manifest",
        "stage_20_manifest",
        "stage_30_manifest",
        "stage_40_manifest",
        "operating_condition_enriched",
        "atomic_features",
        "engine_start_context",
        "engine_start_episodes",
        "window_features",
        "calibrated_features",
    ]
    assert [
        item["artifact_id"] for item in manifest["ordered_output_artifacts"]
    ] == ["production_features"]
    verify_manifest_artifacts(
        manifest, run_dir=layout.run_dir, repo_root=layout.repo_root
    )


def test_upstream_checksum_and_contract_drift_are_rejected(
    tmp_path: Path,
) -> None:
    layout = _production_layout(tmp_path)
    with layout.window_features.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        SCRIPT_41.load_production_inputs(layout)

    contract = load_json_object(layout.feature_contract)
    contract["total_column_count"] = 45
    with pytest.raises(
        SCRIPT_41.ProductionAssemblyError, match="identity has drifted"
    ):
        SCRIPT_41._feature_groups(contract)
