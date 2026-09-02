"""
Tests for Pydantic models in shared/interface_models.py.

These tests validate the BASIC version of the models (no Literal enums,
no range validators, no custom cross-field validators). Stricter
validation will be tested once those features are added.
"""

import pytest
from pydantic import ValidationError

from shared.interface_models import (
    AnomalyType,
    DataLayerOutput,
    KeySignal,
    ModelLayerOutput,
    ReportLayerOutput,
    RiskHistoryEntry,
    RiskLevel,
)


class TestAnomalyType:
    """Tests for the shared anomaly type names."""

    def test_anomaly_type_has_five_current_names(self):
        """Test AnomalyType matches the current five-type interface enum."""
        expected_types = {
            "cooling_degradation",
            "air_intake_maf_anomaly",
            "accelerator_pedal_sensor",
            "intake_air_temperature_sensor_fault",
            "map_load_signal_plausibility_fault",
        }

        actual_types = set(AnomalyType.__args__)

        assert actual_types == expected_types
        assert "electronic_throttle_tracking_fault" not in actual_types
        assert "idle_speed_control_or_surge_degradation" not in actual_types


def test_risk_level_has_three_interface_values():
    assert set(RiskLevel.__args__) == {"Low", "Medium", "High"}


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
            "segment_gap_seconds": 120.0,
            "engine_on_flag": True,
            "coolant_ambient_delta": 70.5,
            "intake_ambient_delta": 13.0,
            "accel_pedal_mean": 36.25,
            "accel_pedal_channel_delta": 2.5,
            "pedal_slope": 0.4,
            "rpm_slope": 12.0,
            "speed_density_maf_residual": 1.2,
            "pedal_mapping_residual": 0.8,
            "engine_start_observed": True,
            "engine_start_episode_id": "trip_0001_start_001",
            "elapsed_since_engine_start": 45.0,
            "ect_start": 22.0,
            "aat_start": 18.0,
            "iat_start": 20.0,
            "maf_integral_180s": 2800.0,
            "ect_rate_180s": 4.0,
            "intake_temp_stability": 0.4,
            "speed_std_120s": 1.5,
            "maf_std_120s": 0.8,
            "rpm_std_120s": 55.0,
            "accel_pedal_mean_std_120s": 0.6,
            "map_range_60s": 3.0,
            "schema_version": "feature_schema.v1",
            "calibration_version": "calibration.v1",
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
            "segment_gap_seconds": 120.0,
            "engine_on_flag": True,
            "coolant_ambient_delta": 70.5,
            "intake_ambient_delta": 13.0,
            "accel_pedal_mean": 36.25,
            "accel_pedal_channel_delta": 2.5,
            "pedal_slope": 0.4,
            "rpm_slope": 12.0,
            "speed_density_maf_residual": 1.2,
            "pedal_mapping_residual": 0.8,
            "engine_start_observed": True,
            "engine_start_episode_id": "trip_0001_start_001",
            "elapsed_since_engine_start": 45.0,
            "ect_start": 22.0,
            "aat_start": 18.0,
            "iat_start": 20.0,
            "maf_integral_180s": 2800.0,
            "ect_rate_180s": 4.0,
            "intake_temp_stability": 0.4,
            "speed_std_120s": 1.5,
            "maf_std_120s": 0.8,
            "rpm_std_120s": 55.0,
            "accel_pedal_mean_std_120s": 0.6,
            "map_range_60s": 3.0,
            "schema_version": "feature_schema.v1",
            "calibration_version": "calibration.v1",
        }
        output = DataLayerOutput(**data)
        assert output.failure_label is None
        assert output.risk_class is None

    def test_data_layer_output_nullable_fields(self):
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
            "segment_gap_seconds": 120.0,
            "engine_on_flag": None,
            "coolant_ambient_delta": None,
            "intake_ambient_delta": 13.0,
            "accel_pedal_mean": 36.25,
            "accel_pedal_channel_delta": 2.5,
            "pedal_slope": 0.4,
            "rpm_slope": 12.0,
            "speed_density_maf_residual": 1.2,
            "pedal_mapping_residual": 0.8,
            "engine_start_observed": True,
            "engine_start_episode_id": "trip_0001_start_001",
            "elapsed_since_engine_start": 45.0,
            "ect_start": 22.0,
            "aat_start": 18.0,
            "iat_start": 20.0,
            "maf_integral_180s": 2800.0,
            "ect_rate_180s": 4.0,
            "intake_temp_stability": 0.4,
            "speed_std_120s": 1.5,
            "maf_std_120s": 0.8,
            "rpm_std_120s": 55.0,
            "accel_pedal_mean_std_120s": None,
            "map_range_60s": 3.0,
            "schema_version": "feature_schema.v1",
            "calibration_version": "calibration.v1",
        }
        output = DataLayerOutput(**data)
        assert output.engine_on_flag is None
        assert output.coolant_ambient_delta is None
        assert output.accel_pedal_mean_std_120s is None

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
            "segment_gap_seconds": 120.0,
            "engine_on_flag": None,
            "coolant_ambient_delta": None,
            "intake_ambient_delta": 13.0,
            "accel_pedal_mean": 36.25,
            "accel_pedal_channel_delta": 2.5,
            "pedal_slope": 0.4,
            "rpm_slope": 12.0,
            "speed_density_maf_residual": 1.2,
            "pedal_mapping_residual": 0.8,
            "engine_start_observed": True,
            "engine_start_episode_id": "trip_0001_start_001",
            "elapsed_since_engine_start": 45.0,
            "ect_start": 22.0,
            "aat_start": 18.0,
            "iat_start": 20.0,
            "maf_integral_180s": 2800.0,
            "ect_rate_180s": 4.0,
            "intake_temp_stability": 0.4,
            "speed_std_120s": 1.5,
            "maf_std_120s": 0.8,
            "rpm_std_120s": 55.0,
            "accel_pedal_mean_std_120s": None,
            "map_range_60s": 3.0,
            "schema_version": "feature_schema.v1",
            "calibration_version": "calibration.v1",
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
            "segment_gap_seconds": 120.0,
            "engine_on_flag": True,
            "coolant_ambient_delta": 70.5,
            "intake_ambient_delta": 13.0,
            "accel_pedal_mean": 36.25,
            "accel_pedal_channel_delta": 2.5,
            "pedal_slope": 0.4,
            "rpm_slope": 12.0,
            "speed_density_maf_residual": 1.2,
            "pedal_mapping_residual": 0.8,
            "engine_start_observed": True,
            "engine_start_episode_id": "trip_0001_start_001",
            "elapsed_since_engine_start": 45.0,
            "ect_start": 22.0,
            "aat_start": 18.0,
            "iat_start": 20.0,
            "maf_integral_180s": 2800.0,
            "ect_rate_180s": 4.0,
            "intake_temp_stability": 0.4,
            "speed_std_120s": 1.5,
            "maf_std_120s": 0.8,
            "rpm_std_120s": 55.0,
            "accel_pedal_mean_std_120s": 0.6,
            "map_range_60s": 3.0,
            "schema_version": "feature_schema.v1",
            "calibration_version": "calibration.v1",
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
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
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
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
        }
        output = ModelLayerOutput(**data)
        assert output.risk_level is None

    def test_model_layer_output_rejects_unknown_risk_level(self):
        data = {
            "timestamp": "2026-06-16T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": 0.82,
            "risk_level": "Critical",
            "component": "cooling_degradation",
            "prediction_confidence": 0.84,
            "key_signals": [],
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
        }

        with pytest.raises(ValidationError):
            ModelLayerOutput(**data)

    def test_model_layer_output_accepts_second_ranked_component(self):
        primary = {
            "timestamp": "2026-08-07T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": 0.9271,
            "risk_level": "High",
            "component": "cooling_degradation",
            "prediction_confidence": 0.91,
            "key_signals": [],
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
            "notes": [],
        }
        secondary = {
            **primary,
            "anomaly_type": "air_intake_maf_anomaly",
            "risk_score": 0.8479,
            "risk_level": "Medium",
            "component": "air_intake_maf_anomaly",
        }
        output = ModelLayerOutput(
            **primary, secondary_risk=secondary
        )

        assert output.secondary_risk is not None
        assert (
            output.secondary_risk.component
            == "air_intake_maf_anomaly"
        )
        assert output.secondary_risk.risk_score == 0.8479

    @pytest.mark.parametrize(
        ("secondary_component", "secondary_score"),
        [
            ("cooling_degradation", 0.8),
            ("air_intake_maf_anomaly", 0.95),
        ],
    )
    def test_model_layer_output_rejects_invalid_secondary_ranking(
        self, secondary_component, secondary_score
    ):
        primary = {
            "timestamp": "2026-08-07T10:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": 0.9271,
            "risk_level": "High",
            "component": "cooling_degradation",
            "prediction_confidence": 0.91,
            "key_signals": [],
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
            "notes": [],
        }
        secondary = {
            **primary,
            "anomaly_type": secondary_component,
            "risk_score": secondary_score,
            "component": secondary_component,
        }

        with pytest.raises(ValidationError):
            ModelLayerOutput(**primary, secondary_risk=secondary)

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
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
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
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
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
