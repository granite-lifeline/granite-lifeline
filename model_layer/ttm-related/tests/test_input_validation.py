"""
Story 3 tests: input validation, pedal fallback, output hardening.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.input_validation import (  # noqa: E402
    PLAUSIBLE_RANGES,
    validate_required_columns,
    validate_sensor_ranges,
)


def make_healthy_df(rows: int = 100) -> pd.DataFrame:
    """Small synthetic frame with all model signals in healthy ranges."""
    return pd.DataFrame(
        {
            "rpm": np.full(rows, 1500.0),
            "speed": np.full(rows, 60.0),
            "coolant_temp": np.full(rows, 90.0),
            "map": np.full(rows, 110.0),
            "maf": np.full(rows, 20.0),
            "tps": np.full(rows, 30.0),
        }
    )


class TestValidateRequiredColumns:
    def test_all_present_passes(self):
        validate_required_columns(
            ["Time", "rpm", "speed"], ["Time", "rpm"], "trip.csv"
        )

    def test_missing_columns_raise_and_are_named(self):
        with pytest.raises(ValueError) as excinfo:
            validate_required_columns(
                ["Time"], ["Time", "rpm", "speed"], "trip.csv"
            )
        message = str(excinfo.value)
        assert "rpm" in message
        assert "speed" in message
        assert "trip.csv" in message


class TestValidateSensorRanges:
    def test_anomalous_but_plausible_values_pass_untouched(self):
        # 120 degC is outside the healthy baseline but physically
        # plausible: the detector must be allowed to see it.
        df = make_healthy_df()
        df.loc[10:20, "coolant_temp"] = 120.0
        result = validate_sensor_ranges(df)
        assert result.notes == []
        assert result.repaired_counts == {}
        pd.testing.assert_frame_equal(result.df, df)

    def test_implausible_values_become_nan_with_note(self):
        df = make_healthy_df(rows=100)
        df.loc[3, "rpm"] = -500.0
        df.loc[7, "coolant_temp"] = 900.0
        result = validate_sensor_ranges(df)
        assert np.isnan(result.df.loc[3, "rpm"])
        assert np.isnan(result.df.loc[7, "coolant_temp"])
        assert result.repaired_counts["rpm"] == 1
        assert result.repaired_counts["coolant_temp"] == 1
        assert any("rpm" in note for note in result.notes)
        assert any("coolant_temp" in note for note in result.notes)

    def test_excess_implausible_values_raise(self):
        df = make_healthy_df(rows=10)
        df.loc[0:1, "rpm"] = -500.0  # 20% bad > 5% threshold
        with pytest.raises(ValueError) as excinfo:
            validate_sensor_ranges(df)
        assert "rpm" in str(excinfo.value)

    def test_all_nan_column_raises(self):
        df = make_healthy_df(rows=10)
        df["maf"] = np.nan
        with pytest.raises(ValueError) as excinfo:
            validate_sensor_ranges(df)
        assert "maf" in str(excinfo.value)

    def test_columns_without_ranges_are_ignored(self):
        df = make_healthy_df()
        df["timestamp"] = pd.date_range("2026-01-01", periods=len(df))
        df["unknown_feature"] = 1e9
        result = validate_sensor_ranges(df)
        assert result.notes == []

    def test_plausible_ranges_wider_than_healthy_baseline(self):
        # Guard: plausibility bounds must not shrink to healthy
        # ranges, or anomalies would be rejected at the door.
        assert PLAUSIBLE_RANGES["map"][1] >= 300
        assert PLAUSIBLE_RANGES["coolant_temp"][1] >= 120


def make_future_df(rows=20, pedal_delta=None):
    """Healthy future window for risk/JSON tests.

    Columns follow production_features.csv v1 (INTERFACE.md
    Section 1) subset the detector reads. pedal_delta=None omits
    the pedal channels entirely (degraded-input case).
    """
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01 10:00:00", periods=rows, freq="1s"
            ),
            "rpm": np.full(rows, 1500.0),
            "speed": np.full(rows, 60.0),
            "coolant_temp": np.full(rows, 90.0),
            "map": np.full(rows, 110.0),
            "maf": np.full(rows, 20.0),
            "tps": np.full(rows, 30.0),
            "ect_rate_180s": np.zeros(rows),
            "maf_integral_180s": np.full(rows, 1000.0),
            "speed_density_maf_residual": np.zeros(rows),
            "intake_ambient_delta": np.full(rows, 13.0),
            "intake_temp_stability": np.full(rows, 0.5),
            "map_range_60s": np.full(rows, 8.0),
            "pedal_slope": np.zeros(rows),
            "rpm_slope": np.zeros(rows),
            "pedal_mapping_residual": np.zeros(rows),
        }
    )
    if pedal_delta is not None:
        df["accel_pedal_d"] = np.full(rows, 25.0)
        df["accel_pedal_e"] = df["accel_pedal_d"] + pedal_delta
        df["accel_pedal_channel_delta"] = np.full(
            rows, float(pedal_delta)
        )
    return df


def make_residual_summary(mean=0.1, maximum=0.2):
    signals = ["rpm", "speed", "coolant_temp", "map", "maf", "tps"]
    return {
        signal: {"mean": mean, "max": maximum} for signal in signals
    }


class TestPedalDetection:
    def test_sustained_disagreement_selects_pedal_anomaly(self):
        from model.kit_residual_detector import calculate_risk

        future = make_future_df(pedal_delta=15.0)
        anomaly_type, risk_score, _, _, _ = calculate_risk(
            make_residual_summary(), future
        )
        assert anomaly_type == "accelerator_pedal_sensor"
        assert risk_score == 1.0

    def test_healthy_pedals_do_not_fire(self):
        from model.kit_residual_detector import calculate_risk

        future = make_future_df(pedal_delta=0.5)
        anomaly_type, _, _, _, _ = calculate_risk(
            make_residual_summary(), future
        )
        assert anomaly_type != "accelerator_pedal_sensor"

    def test_missing_pedals_fall_back_with_note(self):
        from model.kit_residual_detector import calculate_risk

        future = make_future_df(pedal_delta=None)
        anomaly_type, _, _, _, notes = calculate_risk(
            make_residual_summary(), future
        )
        assert anomaly_type != "accelerator_pedal_sensor"
        assert any(
            "accelerator_pedal_sensor" in note for note in notes
        )

    def test_all_nan_pedal_window_falls_back_with_note(self):
        # Group 1 delivers the pedal columns on every row, but a
        # selected window can still be all-NaN; the documented
        # pedal-score-0.0 fallback must fire, not a NaN score.
        from model.kit_residual_detector import calculate_risk

        future = make_future_df(pedal_delta=15.0)
        future["accel_pedal_channel_delta"] = np.nan
        anomaly_type, _, _, _, notes = calculate_risk(
            make_residual_summary(), future
        )
        assert anomaly_type != "accelerator_pedal_sensor"
        assert any(
            "accelerator_pedal_sensor" in note for note in notes
        )


class TestBuildInterfaceJson:
    REQUIRED_FIELDS = [
        "timestamp",
        "anomaly_type",
        "risk_score",
        "risk_level",
        "component",
        "prediction_confidence",
        "key_signals",
        "estimated_cycles_to_failure",
        "estimated_failure_probability",
        "notes",
    ]

    def build(self, future, anomaly_type, notes):
        from model.kit_residual_detector import build_interface_json

        return build_interface_json(
            future=future,
            residual_summary=make_residual_summary(),
            anomaly_type=anomaly_type,
            risk_score=0.5,
            confidence=0.8,
            top_residual_signals=["coolant_temp", "maf", "map"],
            notes=notes,
        )

    def test_all_required_fields_present(self):
        result = self.build(
            make_future_df(), "cooling_degradation", notes=[]
        )
        for field in self.REQUIRED_FIELDS:
            assert field in result, f"missing field: {field}"
        assert result["estimated_cycles_to_failure"] is None
        assert result["estimated_failure_probability"] is None
        assert result["notes"] == []

    def test_notes_passed_through(self):
        note = "accelerator_pedal_sensor detection disabled"
        result = self.build(
            make_future_df(), "cooling_degradation", notes=[note]
        )
        assert result["notes"] == [note]

    def test_cooling_key_signals_include_b_class_context(self):
        result = self.build(
            make_future_df(), "cooling_degradation", notes=[]
        )
        features = [
            signal["feature"] for signal in result["key_signals"]
        ]
        assert "coolant_temp" in features
        assert "ect_rate_180s" in features
        assert "maf_integral_180s" in features

    def test_pedal_key_signals_when_pedal_anomaly(self):
        result = self.build(
            make_future_df(pedal_delta=15.0),
            "accelerator_pedal_sensor",
            notes=[],
        )
        features = [
            signal["feature"] for signal in result["key_signals"]
        ]
        assert "accel_pedal_d" in features
        assert "accel_pedal_e" in features
        assert "accel_pedal_channel_delta" in features

    def test_output_is_json_serializable(self):
        import json

        result = self.build(
            make_future_df(), "cooling_degradation", notes=[]
        )
        json.dumps(result)


class TestLoadGroup1Features:
    def test_returns_frame_for_clean_input(self, tmp_path):
        from group1_fixtures import write_group1_csv
        from model.kit_residual_detector import load_group1_features

        csv_path = write_group1_csv(tmp_path / "production_features.csv")
        df = load_group1_features(csv_path)
        assert "rpm" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    def test_non_numeric_column_raises_named_error(self, tmp_path):
        from group1_fixtures import write_group1_csv
        from model.kit_residual_detector import load_group1_features

        csv_path = write_group1_csv(
            tmp_path / "production_features.csv",
            wrong_type_columns=["rpm_slope"],
        )
        with pytest.raises(ValueError) as excinfo:
            load_group1_features(csv_path)
        assert "rpm_slope" in str(excinfo.value)

    def test_policy_nan_columns_are_tolerated(self, tmp_path):
        # B-class policy NaNs:
        # episode/window features are NaN by design and
        # must load without error.
        from group1_fixtures import make_group1_frame
        from model.kit_residual_detector import load_group1_features

        frame = make_group1_frame(rows=10)
        frame["engine_start_episode_id"] = pd.NA
        frame["elapsed_since_engine_start"] = np.nan
        frame.loc[:3, "maf_integral_180s"] = np.nan
        csv_path = tmp_path / "production_features.csv"
        frame.to_csv(csv_path, index=False)
        df = load_group1_features(csv_path)
        assert df["elapsed_since_engine_start"].isna().all()

    def test_implausible_value_repaired_and_noted(self, tmp_path):
        from group1_fixtures import write_group1_csv
        from model.kit_residual_detector import (
            load_group1_features,
            prepare_segment,
        )

        csv_path = write_group1_csv(
            tmp_path / "production_features.csv", rows=30
        )
        df = load_group1_features(csv_path)
        df.loc[5, "rpm"] = -900.0
        repaired, notes = prepare_segment(df)
        assert any("rpm" in note for note in notes)
        # Repaired via interpolation, no negative rpm survives.
        assert (repaired["rpm"] >= 0).all()
