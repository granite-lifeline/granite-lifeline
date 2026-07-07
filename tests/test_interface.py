"""
Tests for Pydantic models in shared/interface_models.py.

These tests validate the BASIC version of the models (no Literal enums,
no range validators, no custom cross-field validators). Stricter
validation will be tested once those features are added.
"""

import pytest
from pydantic import ValidationError

from shared.interface_models import (
    DataLayerOutput,
    KeySignal,
    ModelLayerOutput,
    ReportLayerOutput,
    RiskHistoryEntry,
)


class TestDataLayerOutput:
    """Tests for DataLayerOutput model."""

    def test_valid_data_layer_output(self):
        """Test DataLayerOutput accepts complete valid payload."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "trip_id": "trip_0001",
            "segment_id": "trip_0001_seg_001",
            "row_in_segment": 1,
            "dt_seconds": 1.0,
            "thermal_state": "post_warmup",
            "child_state": "steady_driving",
            "operating_state": "post_warmup_steady_driving",
            "condition_confidence": "high",
            "condition_quality_flags": "OK",
            "coolant_temp": 92.5,
            "map": 85.0,
            "rpm": 2500.0,
            "speed": 48.0,
            "intake_temp": 35.0,
            "maf": 18.6,
            "tps": 42.0,
            "ambient_temp": 22.0,
            "accel_pedal_d": 35.0,
            "accel_pedal_e": 37.5,
            "coolant_slope": 3.1,
            "coolant_ambient_delta": 70.5,
            "coolant_stability": 0.4,
            "intake_ambient_delta": 13.0,
            "intake_temp_slope": 0.2,
            "maf_derived_air_load_raw": 0.45,
            "map_derived_air_load_raw": 720.0,
            "maf_map_cohesion": 0.18,
            "speed_density_maf_residual": 1.2,
            "map_slope": 0.5,
            "accel_pedal_mean": 36.25,
            "pedal_throttle_gap": 2.1,
            "pedal_to_throttle_delay": 1.0,
            "tps_slope": 0.3,
            "accel_pedal_channel_delta": 2.5,
            "accel_pedal_channel_ratio": 0.93,
            "pedal_slope": 0.4,
            "engine_on_flag": 1.0,
            "rpm_slope": 12.0,
            "idle_flag": 0.0,
            "idle_rpm_stability": 55.0,

            "failure_label": "cooling_risk",
            "risk_class": "HIGH",
            "condition_ratio": 0.31,
            "window_id": "001",
        }
        output = DataLayerOutput(**data)
        assert output.timestamp == "2026-06-16T10:00:00Z"
        assert output.rpm == 2500.0
        assert output.failure_label == "cooling_risk"

    def test_data_layer_output_optional_fields(self):
        """Test DataLayerOutput works without optional proxy labels."""
        data = {
           "timestamp": "2026-06-16T10:00:00Z",
            "trip_id": "trip_0001",
            "segment_id": "trip_0001_seg_001",
            "row_in_segment": 1,
            "dt_seconds": 1.0,
            "thermal_state": "post_warmup",
            "child_state": "steady_driving",
            "operating_state": "post_warmup_steady_driving",
            "condition_confidence": "high",
            "condition_quality_flags": "OK",
            "coolant_temp": 92.5,
            "map": 85.0,
            "rpm": 2500.0,
            "speed": 48.0,
            "intake_temp": 35.0,
            "maf": 18.6,
            "tps": 42.0,
            "ambient_temp": 22.0,
            "accel_pedal_d": 35.0,
            "accel_pedal_e": 37.5,
            "coolant_slope": 3.1,
            "coolant_ambient_delta": 70.5,
            "coolant_stability": 0.4,
            "intake_ambient_delta": 13.0,
            "intake_temp_slope": 0.2,
            "maf_derived_air_load_raw": 0.45,
            "map_derived_air_load_raw": 720.0,
            "maf_map_cohesion": 0.18,
            "speed_density_maf_residual": 1.2,
            "map_slope": 0.5,
            "accel_pedal_mean": 36.25,
            "pedal_throttle_gap": 2.1,
            "pedal_to_throttle_delay": 1.0,
            "tps_slope": 0.3,
            "accel_pedal_channel_delta": 2.5,
            "accel_pedal_channel_ratio": 0.93,
            "pedal_slope": 0.4,
            "engine_on_flag": 1.0,
            "rpm_slope": 12.0,
            "idle_flag": 0.0,
            "idle_rpm_stability": 55.0,
        }
        output = DataLayerOutput(**data)
        assert output.failure_label is None
        assert output.risk_class is None

    def test_data_layer_output_optional_fields(self):
        """Test DataLayerOutput accepts nullable CSV feature values."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "trip_id": "trip_0001",
            "segment_id": "trip_0001_seg_001",
            "row_in_segment": 1,
            "dt_seconds": 1.0,
            "thermal_state": "post_warmup",
            "child_state": "steady_driving",
            "operating_state": "post_warmup_steady_driving",
            "condition_confidence": "high",
            "condition_quality_flags": "OK",
            "coolant_temp": 92.5,
            "map": 85.0,
            "rpm": 2500.0,
            "speed": 48.0,
            "intake_temp": 35.0,
            "maf": 18.6,
            "tps": 42.0,
            "ambient_temp": 22.0,
            "accel_pedal_d": 35.0,
            "accel_pedal_e": 37.5,
            "coolant_slope": 3.1,
            "coolant_ambient_delta": 70.5,
            "coolant_stability": None,
            "intake_ambient_delta": 13.0,
            "intake_temp_slope": 0.2,
            "maf_derived_air_load_raw": 0.45,
            "map_derived_air_load_raw": 720.0,
            "maf_map_cohesion": 0.18,
            "speed_density_maf_residual": 1.2,
            "map_slope": 0.5,
            "accel_pedal_mean": 36.25,
            "pedal_throttle_gap": 2.1,
            "pedal_to_throttle_delay": None,
            "tps_slope": 0.3,
            "accel_pedal_channel_delta": 2.5,
            "accel_pedal_channel_ratio": 0.93,
            "pedal_slope": 0.4,
            "engine_on_flag": 1.0,
            "rpm_slope": 12.0,
            "idle_flag": 0.0,
            "idle_rpm_stability": None,
        }
        output = DataLayerOutput(**data)
        assert output.coolant_stability is None
        assert output.pedal_to_throttle_delay is None
        assert output.idle_rpm_stability is None

    def test_data_layer_output_missing_required_field(self):
        """Test DataLayerOutput raises error when required field missing."""
        data = {
             "timestamp": "2026-06-16T10:00:00Z",
            "trip_id": "trip_0001",
            "segment_id": "trip_0001_seg_001",
            "row_in_segment": 1,
            "dt_seconds": 1.0,
            "thermal_state": "post_warmup",
            "child_state": "steady_driving",
            "operating_state": "post_warmup_steady_driving",
            "condition_confidence": "high",
            "condition_quality_flags": "OK",
            "coolant_temp": 92.5,
            "map": 85.0,
            "rpm": 2500.0,
            # Missing 'speed' - required field
            "intake_temp": 35.0,
            "maf": 18.6,
            "tps": 42.0,
            "ambient_temp": 22.0,
            "accel_pedal_d": 35.0,
            "accel_pedal_e": 37.5,
            "coolant_slope": 3.1,
            "coolant_ambient_delta": 70.5,
            "coolant_stability": 0.4,
            "intake_ambient_delta": 13.0,
            "intake_temp_slope": 0.2,
            "maf_derived_air_load_raw": 0.45,
            "map_derived_air_load_raw": 720.0,
            "maf_map_cohesion": 0.18,
            "speed_density_maf_residual": 1.2,
            "map_slope": 0.5,
            "accel_pedal_mean": 36.25,
            "pedal_throttle_gap": 2.1,
            "pedal_to_throttle_delay": 1.0,
            "tps_slope": 0.3,
            "accel_pedal_channel_delta": 2.5,
            "accel_pedal_channel_ratio": 0.93,
            "pedal_slope": 0.4,
            "engine_on_flag": 1.0,
            "rpm_slope": 12.0,
            "idle_flag": 0.0,
            "idle_rpm_stability": 55.0,
        }
        with pytest.raises(ValidationError):
            DataLayerOutput(**data)

    def test_data_layer_output_wrong_type(self):
        """Test DataLayerOutput raises error for wrong field type."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "trip_id": "trip_0001",
            "segment_id": "trip_0001_seg_001",
            "row_in_segment": 1,
            "dt_seconds": 1.0,
            "thermal_state": "post_warmup",
            "child_state": "steady_driving",
            "operating_state": "post_warmup_steady_driving",
            "condition_confidence": "high",
            "condition_quality_flags": "OK",
            "coolant_temp": 92.5,
            "map": 85.0,
            "rpm": "not_a_float",  # Wrong type
            "speed": 48.0,
            "intake_temp": 35.0,
            "maf": 18.6,
            "tps": 42.0,
            "ambient_temp": 22.0,
            "accel_pedal_d": 35.0,
            "accel_pedal_e": 37.5,
            "coolant_slope": 3.1,
            "coolant_ambient_delta": 70.5,
            "coolant_stability": 0.4,
            "intake_ambient_delta": 13.0,
            "intake_temp_slope": 0.2,
            "maf_derived_air_load_raw": 0.45,
            "map_derived_air_load_raw": 720.0,
            "maf_map_cohesion": 0.18,
            "speed_density_maf_residual": 1.2,
            "map_slope": 0.5,
            "accel_pedal_mean": 36.25,
            "pedal_throttle_gap": 2.1,
            "pedal_to_throttle_delay": 1.0,
            "tps_slope": 0.3,
            "accel_pedal_channel_delta": 2.5,
            "accel_pedal_channel_ratio": 0.93,
            "pedal_slope": 0.4,
            "engine_on_flag": 1.0,
            "rpm_slope": 12.0,
            "idle_flag": 0.0,
            "idle_rpm_stability": 55.0,
        }
        with pytest.raises(ValidationError):
            DataLayerOutput(**data)


class TestKeySignal:
    """Tests for KeySignal nested model."""

    def test_valid_key_signal(self):
        """Test KeySignal accepts valid payload."""
        data = {
            "feature": "coolant_temp",
            "value": 102.0,
            "unit": "°C",
            "reference_range": [90.0, 95.0],
        }
        signal = KeySignal(**data)
        assert signal.feature == "coolant_temp"
        assert signal.value == 102.0
        assert signal.reference_range == [90.0, 95.0]

    def test_key_signal_missing_required_field(self):
        """Test KeySignal raises error when required field missing."""
        data = {
            # Missing 'feature' - required field
            "value": 102.0,
            "unit": "°C",
            "reference_range": [90.0, 95.0],
        }
        with pytest.raises(ValidationError):
            KeySignal(**data)


class TestModelLayerOutput:
    """Tests for ModelLayerOutput model."""

    def test_valid_model_layer_output(self):
        """Test ModelLayerOutput accepts complete valid payload."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": 0.82,
            "risk_level": "Medium",
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [
                {
                    "feature": "coolant_temp",
                    "value": 102.0,
                    "unit": "°C",
                    "reference_range": [90.0, 95.0],
                },
                {
                    "feature": "coolant_slope",
                    "value": 3.1,
                    "unit": "°C/min",
                    "reference_range": [0.0, 2.0],
                },
            ],
        }
        output = ModelLayerOutput(**data)
        assert output.anomaly_type == "cooling_degradation"
        assert output.risk_score == 0.82
        assert len(output.key_signals) == 2
        assert output.key_signals[0].feature == "coolant_temp"

    def test_model_layer_output_optional_risk_level(self):
        """Test ModelLayerOutput works without optional risk_level."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "anomaly_type": "air_intake_maf_anomaly",
            "risk_score": 0.65,
            # risk_level omitted (TBD field)
            "component": "air_intake_maf_anomaly",
            "prediction_confidence": 0.78,
            "key_signals": [
                {
                    "feature": "maf",
                    "value": 15.2,
                    "unit": "g/s",
                    "reference_range": [10.0, 20.0],
                }
            ],
        }
        output = ModelLayerOutput(**data)
        assert output.risk_level is None

    def test_model_layer_output_missing_required_field(self):
        """Test ModelLayerOutput raises error when required field missing."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            # Missing 'risk_score' - required field
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [],
        }
        with pytest.raises(ValidationError):
            ModelLayerOutput(**data)

    def test_model_layer_output_wrong_type(self):
        """Test ModelLayerOutput raises error for wrong field type."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": "not_a_float",  # Wrong type
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [],
        }
        with pytest.raises(ValidationError):
            ModelLayerOutput(**data)

    # NOTE: Range validation (e.g., risk_score > 1.0) and enum validation
    # (e.g., anomaly_type = "invalid_value") are NOT tested here because
    # the current BASIC models do not enforce these constraints.
    # These tests will be added when stricter validation is implemented.


class TestRiskHistoryEntry:
    """Tests for RiskHistoryEntry nested model."""

    def test_valid_risk_history_entry(self):
        """Test RiskHistoryEntry accepts valid payload."""
        data = {
            "timestamp": "2026-06-15T10:00:00Z",
            "risk_score": 0.65,
        }
        entry = RiskHistoryEntry(**data)
        assert entry.timestamp == "2026-06-15T10:00:00Z"
        assert entry.risk_score == 0.65


class TestReportLayerOutput:
    """Tests for ReportLayerOutput model."""

    def test_valid_report_layer_output(self):
        """Test ReportLayerOutput accepts complete valid payload."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "risk_score": 0.72,
            "risk_level": "Medium",
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [
                {
                    "feature": "coolant_temp",
                    "value": 102.0,
                    "unit": "°C",
                    "reference_range": [90.0, 95.0],
                }
            ],
            "risk_history": [
                {"timestamp": "2026-06-15T10:00:00Z", "risk_score": 0.65},
                {"timestamp": "2026-06-16T10:00:00Z", "risk_score": 0.72},
            ],
            "anomaly_description": "Coolant temperature rising faster.",
            "possible_cause": "Possible water pump degradation.",
            "recommended_action": ["Check coolant level", "Inspect radiator"],
        }
        output = ReportLayerOutput(**data)
        assert output.component == "cooling_degradation"
        assert output.risk_history is not None
        assert len(output.risk_history) == 2
        assert output.risk_history[0].risk_score == 0.65
        assert len(output.recommended_action) == 2

    def test_report_layer_output_optional_fields(self):
        """Test ReportLayerOutput works without optional fields."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "risk_score": 0.72,
            # risk_level omitted (TBD field)
            "component": "accelerator_pedal_sensor",
            "prediction_confidence": 0.91,
            "key_signals": [
                {
                    "feature": "accel_pedal_d",
                    "value": 35.0,
                    "unit": "%",
                    "reference_range": [0.0, 100.0],
                }
            ],
            # risk_history omitted (TBD field)
            "anomaly_description": "Pedal sensor discrepancy detected.",
            "possible_cause": "Sensor calibration drift.",
            "recommended_action": ["Inspect pedal sensors"],
        }
        output = ReportLayerOutput(**data)
        assert output.risk_level is None
        assert output.risk_history is None

    def test_report_layer_output_missing_required_field(self):
        """Test ReportLayerOutput raises error when required field missing."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "risk_score": 0.72,
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [],
            # Missing 'anomaly_description' - required field
            "possible_cause": "Possible water pump degradation.",
            "recommended_action": ["Check coolant level"],
        }
        with pytest.raises(ValidationError):
            ReportLayerOutput(**data)

    def test_report_layer_output_wrong_type(self):
        """Test ReportLayerOutput raises error for wrong field type."""
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "risk_score": 0.72,
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [],
            "anomaly_description": "Coolant temperature rising faster.",
            "possible_cause": "Possible water pump degradation.",
            "recommended_action": "not_a_list",  # Wrong type
        }
        with pytest.raises(ValidationError):
            ReportLayerOutput(**data)

    # NOTE: Range validation and enum validation are NOT tested here
    # because the current BASIC models do not enforce these constraints.
    # These tests will be added when stricter validation is implemented.
