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
    test_20_engine_start_context as fixture_20,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "data_layer/feature_engineering/src/30_window_feature_builder.py"
SPEC = importlib.util.spec_from_file_location("script_30_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_30 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCRIPT_30
SPEC.loader.exec_module(SCRIPT_30)


def _window_layout(
    tmp_path: Path,
    rows: int,
    *,
    rpm: list[float] | None = None,
    segments: list[str] | None = None,
) -> RunLayout:
    rpm = rpm or [0.0, *([100.0] * (rows - 1))]
    layout, _ = fixture_20._sequence_layout(tmp_path, rpm, segments)
    operating = pd.read_csv(layout.operating_condition_enriched)
    sequence = pd.Series(range(rows), dtype="float64")
    operating["coolant_temp"] = sequence
    operating["intake_temp"] = sequence
    operating["speed"] = sequence
    operating["maf"] = 2.0
    operating["map"] = sequence.mod(10)
    operating["accel_pedal_d"] = sequence
    operating["accel_pedal_e"] = sequence
    operating.to_csv(layout.operating_condition_enriched, index=False)
    return layout


def _run_upstream(layout: RunLayout) -> None:
    fixture_20._run_upstream(layout)
    fixture_20.SCRIPT_20.run_engine_start_context_builder(
        layout, creation_time_utc="2026-07-19T12:02:00Z"
    )


def test_exact_window_lengths_formulas_and_null_prefixes(tmp_path: Path) -> None:
    layout = _window_layout(tmp_path, 241)
    _run_upstream(layout)

    output = SCRIPT_30.build_window_features(SCRIPT_30.load_window_inputs(layout))

    assert output["maf_integral_180s"].first_valid_index() == 181
    assert output.loc[181, "maf_integral_180s"] == pytest.approx(360.0)
    assert output["ect_rate_180s"].first_valid_index() == 180
    assert output.loc[180, "ect_rate_180s"] == pytest.approx(60.0)
    assert output["intake_temp_stability"].first_valid_index() == 59
    assert output["speed_std_120s"].first_valid_index() == 119
    assert output["maf_std_120s"].first_valid_index() == 119
    assert output.loc[119, "maf_std_120s"] == pytest.approx(0.0)
    assert output.loc[119, "speed_std_120s"] == pytest.approx(
        pd.Series(range(120), dtype="float64").std(ddof=1)
    )
    assert output.loc[119, "accel_pedal_mean_std_120s"] == pytest.approx(
        pd.Series(range(120), dtype="float64").std(ddof=1)
    )
    assert output["map_range_60s"].first_valid_index() == 59
    assert output.loc[59, "map_range_60s"] == pytest.approx(9.0)


def test_invalid_quality_breaks_and_restarts_signal_windows(tmp_path: Path) -> None:
    layout = _window_layout(tmp_path, 300)
    quality = pd.read_csv(layout.cleaning_quality)
    quality.loc[100, "maf_is_suspicious"] = True
    quality.loc[100, "is_suspicious_any"] = True
    quality.to_csv(layout.cleaning_quality, index=False)
    _run_upstream(layout)

    output = SCRIPT_30.build_window_features(SCRIPT_30.load_window_inputs(layout))

    assert pd.isna(output.loc[99, "maf_std_120s"])
    assert output.loc[100:219, "maf_std_120s"].isna().all()
    assert output.loc[220, "maf_std_120s"] == pytest.approx(0.0)
    assert output.loc[180:280, "maf_integral_180s"].isna().all()
    assert output.loc[281, "maf_integral_180s"] == pytest.approx(360.0)
    assert output.loc[180, "ect_rate_180s"] == pytest.approx(60.0)


def test_maf_integral_cannot_cross_engine_start_episode(tmp_path: Path) -> None:
    rpm = [0.0, *([100.0] * 190), 0.0, *([100.0] * 200)]
    layout = _window_layout(tmp_path, len(rpm), rpm=rpm)
    _run_upstream(layout)

    output = SCRIPT_30.build_window_features(SCRIPT_30.load_window_inputs(layout))

    assert output.loc[181, "maf_integral_180s"] == pytest.approx(360.0)
    assert output.loc[191:371, "maf_integral_180s"].isna().all()
    assert output.loc[372, "maf_integral_180s"] == pytest.approx(360.0)


def test_segment_boundary_restarts_all_windows(tmp_path: Path) -> None:
    rows = 260
    segments = ["trip_0001_seg_001"] * 130 + ["trip_0001_seg_002"] * 130
    layout = _window_layout(tmp_path, rows, segments=segments)
    _run_upstream(layout)

    output = SCRIPT_30.build_window_features(SCRIPT_30.load_window_inputs(layout))

    assert output.loc[129, "speed_std_120s"] == pytest.approx(
        pd.Series(range(10, 130), dtype="float64").std(ddof=1)
    )
    assert output.loc[130:248, "speed_std_120s"].isna().all()
    assert output.loc[249, "speed_std_120s"] == pytest.approx(
        pd.Series(range(130, 250), dtype="float64").std(ddof=1)
    )
    assert output.loc[130:188, "map_range_60s"].isna().all()
    assert output.loc[189, "map_range_60s"] == pytest.approx(9.0)


def test_output_grain_manifest_and_upstream_checksum_enforcement(tmp_path: Path) -> None:
    layout = _window_layout(tmp_path, 241)
    _run_upstream(layout)

    output, manifest = SCRIPT_30.run_window_feature_builder(
        layout, creation_time_utc="2026-07-19T12:03:00Z"
    )

    assert list(output.columns) == [*SCRIPT_30.KEY_COLUMNS, *SCRIPT_30.B3_COLUMNS]
    assert manifest["calibration_version"] == "not_applicable"
    assert [
        item["artifact_id"] for item in manifest["ordered_output_artifacts"]
    ] == ["window_features"]
    assert manifest["output_contract"]["row_count"] == 241
    assert manifest["output_contract"]["ordered_columns"] == list(output.columns)
    verify_manifest_artifacts(
        manifest, run_dir=layout.run_dir, repo_root=layout.repo_root
    )

    with layout.engine_start_context.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        SCRIPT_30.load_window_inputs(layout)


def test_b3_contract_drift_is_rejected(tmp_path: Path) -> None:
    layout = RunLayout.for_run_id("script-30-contract", repo_root=tmp_path)
    layout.feature_contract.parent.mkdir(parents=True)
    layout.feature_contract.write_bytes(
        (REPO_ROOT / "data_layer/contracts/feature_manifest.v1.json").read_bytes()
    )
    contract = load_json_object(layout.feature_contract)
    contract["features"][16]["window_contract"]["endpoint_count"] = 180

    with pytest.raises(SCRIPT_30.WindowFeatureError, match="contract has drifted"):
        SCRIPT_30._validate_b3_contract(contract)
