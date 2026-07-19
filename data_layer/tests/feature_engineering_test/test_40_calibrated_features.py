from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

from data_layer.pipeline_data.manifests import load_json_object, verify_manifest_artifacts
from data_layer.tests.feature_engineering_test import (
    test_20_engine_start_context as fixture_20,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT / "data_layer/feature_engineering/src/40_calibrated_feature_builder.py"
)
SPEC = importlib.util.spec_from_file_location("script_40_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_40 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_40
SPEC.loader.exec_module(SCRIPT_40)


def _calibrated_layout(tmp_path: Path):
    layout, _ = fixture_20._sequence_layout(tmp_path, [100.0, 100.0, 100.0])
    calibration_dir = layout.calibration_registry.parent
    calibration_dir.mkdir(parents=True)
    layout.calibration_registry.write_bytes(
        (REPO_ROOT / "data_layer/calibration/calibration_registry.v1.json").read_bytes()
    )
    layout.calibration_release_manifest.write_bytes(
        (
            REPO_ROOT
            / "data_layer/calibration/calibration_registry.v1.manifest.json"
        ).read_bytes()
    )
    operating = pd.read_csv(layout.operating_condition_enriched)
    operating[["map", "rpm", "intake_temp", "maf"]] = [
        [100.0, 1000.0, 20.0, 30.0],
        [300.0, 3000.0, 100.0, 100.0],
        [100.0, 1000.0, 20.0, 30.0],
    ]
    operating[["accel_pedal_d", "accel_pedal_e"]] = [
        [10.0, 12.0],
        [20.0, 25.0],
        [10.0, 12.0],
    ]
    operating.to_csv(layout.operating_condition_enriched, index=False)
    quality = pd.read_csv(layout.cleaning_quality)
    quality.loc[2, "maf_is_suspicious"] = True
    quality.loc[2, "accel_pedal_e_is_imputed"] = True
    quality.loc[2, "is_suspicious_any"] = True
    quality.loc[2, "is_imputed_any"] = True
    quality.to_csv(layout.cleaning_quality, index=False)
    fixture_20._run_upstream(layout)
    return layout


def _expected_speed_residual(row: pd.Series, transform: dict) -> float:
    raw_load = row["rpm"] * row["map"] / (row["intake_temp"] + 273.15)
    values = {
        "map_derived_air_load_raw": raw_load,
        "map": row["map"],
        "rpm": row["rpm"],
        "intake_temp": row["intake_temp"],
    }
    prediction = transform["intercept"]
    for name in transform["ordered_input_features"]:
        bounds = transform["prediction_clipping_bounds"][name]
        clipped = min(max(values[name], bounds["lower"]), bounds["upper"])
        prediction += transform["coefficients"][name] * clipped
    return row["maf"] - prediction


def test_frozen_formulas_apply_clipping_without_target_winsorization(
    tmp_path: Path,
) -> None:
    layout = _calibrated_layout(tmp_path)
    inputs = SCRIPT_40.load_calibrated_inputs(layout)
    output = SCRIPT_40.build_calibrated_features(inputs)
    transform = inputs.registry["feature_transforms"]["speed_density_maf"]

    for index in (0, 1):
        expected = _expected_speed_residual(inputs.canonical.loc[index], transform)
        assert output.loc[index, "speed_density_maf_residual"] == pytest.approx(expected)
    assert inputs.canonical.loc[1, "maf"] == 100.0
    pedal = inputs.registry["feature_transforms"]["pedal_mapping"]
    assert output.loc[0, "pedal_mapping_residual"] == pytest.approx(
        12.0 - (pedal["a"] * 10.0 + pedal["b"])
    )
    assert output.loc[1, "pedal_mapping_residual"] == pytest.approx(
        25.0 - (pedal["a"] * 20.0 + pedal["b"])
    )
    assert "map_derived_air_load_raw" not in output.columns


def test_any_required_quality_invalidity_yields_null(tmp_path: Path) -> None:
    layout = _calibrated_layout(tmp_path)
    output = SCRIPT_40.build_calibrated_features(
        SCRIPT_40.load_calibrated_inputs(layout)
    )

    assert math.isnan(output.loc[2, "speed_density_maf_residual"])
    assert math.isnan(output.loc[2, "pedal_mapping_residual"])
    assert output.loc[:1, SCRIPT_40.B1B_COLUMNS].notna().all().all()


def test_release_checksum_drift_is_rejected(tmp_path: Path) -> None:
    layout = _calibrated_layout(tmp_path)
    registry = load_json_object(layout.calibration_registry)
    registry["feature_transforms"]["pedal_mapping"]["a"] += 0.01
    layout.calibration_registry.write_text(
        json.dumps(registry), encoding="utf-8"
    )

    with pytest.raises(
        SCRIPT_40.CalibratedFeatureError, match="checksum/release binding"
    ):
        SCRIPT_40.load_calibrated_inputs(layout)


def test_online_fit_policy_drift_is_rejected(tmp_path: Path) -> None:
    layout = _calibrated_layout(tmp_path)
    registry = load_json_object(layout.calibration_registry)
    registry["online_policy"]["fit_allowed"] = True

    with pytest.raises(SCRIPT_40.CalibratedFeatureError, match="online policy"):
        SCRIPT_40._validate_registry(registry)
    assert not hasattr(SCRIPT_40, "fit")


def test_output_manifest_is_calibration_bound_and_sample_grain(tmp_path: Path) -> None:
    layout = _calibrated_layout(tmp_path)
    output, manifest = SCRIPT_40.run_calibrated_feature_builder(
        layout, creation_time_utc="2026-07-19T12:04:00Z"
    )

    assert list(output.columns) == [*SCRIPT_40.KEY_COLUMNS, *SCRIPT_40.B1B_COLUMNS]
    assert manifest["calibration_version"] == "calibration.v1"
    assert manifest["calibration_contract"]["application_mode"] == "predict_only"
    assert manifest["calibration_contract"]["fit_allowed"] is False
    assert manifest["calibration_contract"]["hidden_intermediates_emitted"] is False
    assert manifest["output_contract"]["row_count"] == 3
    input_ids = [item["artifact_id"] for item in manifest["ordered_input_artifacts"]]
    assert input_ids == [
        "feature_contract",
        "calibration_registry",
        "calibration_release_manifest",
        "input_contract_manifest",
        "atomic_features_manifest",
        "operating_condition_enriched",
        "cleaning_quality",
        "atomic_features",
    ]
    assert [
        item["artifact_id"] for item in manifest["ordered_output_artifacts"]
    ] == ["calibrated_features"]
    verify_manifest_artifacts(
        manifest, run_dir=layout.run_dir, repo_root=layout.repo_root
    )


def test_b1b_contract_drift_is_rejected(tmp_path: Path) -> None:
    layout = _calibrated_layout(tmp_path)
    contract = load_json_object(layout.feature_contract)
    contract["features"][8]["unit"] = "kg/s"

    with pytest.raises(SCRIPT_40.CalibratedFeatureError, match="contract has drifted"):
        SCRIPT_40._validate_b1b_contract(contract)
