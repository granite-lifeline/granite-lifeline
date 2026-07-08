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


KIT_HEADERS = {
    "Time": "Time",
    "rpm": "Engine RPM [RPM]",
    "speed": "Vehicle Speed Sensor [km/h]",
    "coolant_temp": "Engine Coolant Temperature [°C]",
    "map": "Intake Manifold Absolute Pressure [kPa]",
    "maf": "Air Flow Rate from Mass Flow Sensor [g/s]",
    "tps": "Absolute Throttle Position [%]",
    "accel_pedal_d": "Accelerator Pedal Position D [%]",
    "accel_pedal_e": "Accelerator Pedal Position E [%]",
}


def write_kit_csv(path, rows=30, with_pedals=True, rpm_override=None):
    """Write a minimal KIT-format trip CSV for loader tests."""
    time_col = [f"10:00:{i:02d}.0" for i in range(rows)]
    data = {
        KIT_HEADERS["Time"]: time_col,
        KIT_HEADERS["rpm"]: np.full(rows, 1500.0),
        KIT_HEADERS["speed"]: np.full(rows, 60.0),
        KIT_HEADERS["coolant_temp"]: np.full(rows, 90.0),
        KIT_HEADERS["map"]: np.full(rows, 110.0),
        KIT_HEADERS["maf"]: np.full(rows, 20.0),
        KIT_HEADERS["tps"]: np.full(rows, 30.0),
    }
    if with_pedals:
        data[KIT_HEADERS["accel_pedal_d"]] = np.full(rows, 25.0)
        data[KIT_HEADERS["accel_pedal_e"]] = np.full(rows, 25.5)
    if rpm_override is not None:
        data[KIT_HEADERS["rpm"]] = rpm_override
    pd.DataFrame(data).to_csv(path, index=False)
    return path


def make_future_df(rows=20, pedal_delta=None):
    """Healthy future window for risk/JSON tests.

    pedal_delta=None omits the pedal channels entirely.
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
            "coolant_slope": np.zeros(rows),
            "coolant_stability": np.zeros(rows),
            "acceleration": np.zeros(rows),
            "load_stress": np.full(rows, 45000.0),
            "maf_map_cohesion": np.zeros(rows),
            "rpm_variation": np.full(rows, 10.0),
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
    def test_derived_delta_added_when_pedals_present(self):
        from model.kit_residual_detector import add_derived_features

        df = make_healthy_df()
        df["accel_pedal_d"] = 25.0
        df["accel_pedal_e"] = 26.0
        out = add_derived_features(df)
        assert "accel_pedal_channel_delta" in out.columns
        assert out["accel_pedal_channel_delta"].iloc[0] == 1.0

    def test_no_delta_and_no_crash_without_pedals(self):
        from model.kit_residual_detector import add_derived_features

        out = add_derived_features(make_healthy_df())
        assert "accel_pedal_channel_delta" not in out.columns

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

    def test_cooling_key_signals_include_stability(self):
        result = self.build(
            make_future_df(), "cooling_degradation", notes=[]
        )
        features = [
            signal["feature"] for signal in result["key_signals"]
        ]
        assert "coolant_temp" in features
        assert "coolant_slope" in features
        assert "coolant_stability" in features

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


class TestLoadAndResampleKitCsv:
    def test_returns_frame_and_empty_notes_for_clean_input(
        self, tmp_path
    ):
        from model.kit_residual_detector import load_and_resample_kit_csv

        csv_path = write_kit_csv(tmp_path / "trip.csv")
        df, notes = load_and_resample_kit_csv(csv_path, "1s")
        assert notes == []
        assert "rpm" in df.columns

    def test_missing_pedal_columns_add_note(self, tmp_path):
        from model.kit_residual_detector import load_and_resample_kit_csv

        csv_path = write_kit_csv(
            tmp_path / "trip.csv", with_pedals=False
        )
        df, notes = load_and_resample_kit_csv(csv_path, "1s")
        assert any("accel_pedal" in note for note in notes)
        assert "accel_pedal_d" not in df.columns

    def test_implausible_value_repaired_and_noted(self, tmp_path):
        from model.kit_residual_detector import load_and_resample_kit_csv

        rpm = np.full(30, 1500.0)
        rpm[5] = -900.0
        csv_path = write_kit_csv(
            tmp_path / "trip.csv", rpm_override=rpm
        )
        df, notes = load_and_resample_kit_csv(csv_path, "1s")
        assert any("rpm" in note for note in notes)
        # Repaired via interpolation, no negative rpm survives.
        assert (df["rpm"] >= 0).all()
