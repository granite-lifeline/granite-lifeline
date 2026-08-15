import copy
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.validate_output import validate_output  # noqa: E402


def valid_output():
    return {
        "timestamp": "2026-01-01T07:16:42Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 0.2338,
        "risk_level": "Low",
        "component": "cooling_degradation",
        "prediction_confidence": 0.9301,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 58.0,
                "unit": "degC",
                "reference_range": [90, 95],
            }
        ],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
    }


def test_valid_output_passes():
    assert validate_output(valid_output()) == []


def test_secondary_risk_passes_when_distinct_and_not_higher():
    data = valid_output()
    secondary = valid_output()
    secondary["anomaly_type"] = "air_intake_maf_anomaly"
    secondary["component"] = "air_intake_maf_anomaly"
    secondary["risk_score"] = 0.2
    data["secondary_risk"] = secondary
    assert validate_output(data) == []


def test_secondary_risk_must_be_distinct_and_ranked_second():
    data = valid_output()
    secondary = valid_output()
    secondary["risk_score"] = 0.9
    data["secondary_risk"] = secondary
    errors = validate_output(data)
    assert any("must differ" in error for error in errors)
    assert any("must not exceed" in error for error in errors)


def test_missing_required_field_fails():
    data = valid_output()
    del data["notes"]
    errors = validate_output(data)
    assert "missing required field: notes" in errors


def test_invalid_anomaly_type_fails():
    data = valid_output()
    data["anomaly_type"] = "unknown_fault"
    data["component"] = "unknown_fault"
    errors = validate_output(data)
    assert any("anomaly_type is not allowed" in error for error in errors)


def test_retired_anomaly_types_fail():
    for retired in (
        "intake_air_temperature_sensor_or_heat_soak_fault",
        "idle_speed_control_or_surge_degradation",
    ):
        data = valid_output()
        data["anomaly_type"] = retired
        data["component"] = retired
        errors = validate_output(data)
        assert any("anomaly_type is not allowed" in error for error in errors)


def test_component_must_equal_anomaly_type():
    data = valid_output()
    data["component"] = "air_intake_maf_anomaly"
    errors = validate_output(data)
    assert "component must equal anomaly_type" in errors


def test_risk_score_out_of_range_fails():
    data = valid_output()
    data["risk_score"] = 1.1
    errors = validate_output(data)
    assert "risk_score must be between 0 and 1" in errors


def test_prediction_confidence_out_of_range_fails():
    data = valid_output()
    data["prediction_confidence"] = -0.1
    errors = validate_output(data)
    assert "prediction_confidence must be between 0 and 1" in errors


def test_nullable_estimation_fields_pass():
    data = valid_output()
    data["estimated_cycles_to_failure"] = None
    data["estimated_failure_probability"] = None
    assert validate_output(data) == []


def test_non_null_estimation_fields_validate_ranges():
    data = valid_output()
    data["estimated_cycles_to_failure"] = 12
    data["estimated_failure_probability"] = 0.72
    assert validate_output(data) == []

    bad = copy.deepcopy(data)
    bad["estimated_cycles_to_failure"] = -1
    bad["estimated_failure_probability"] = 1.4
    errors = validate_output(bad)
    assert any("estimated_cycles_to_failure" in error for error in errors)
    assert any("estimated_failure_probability" in error for error in errors)


def test_key_signal_item_requires_expected_shape():
    data = valid_output()
    del data["key_signals"][0]["reference_range"]
    errors = validate_output(data)
    assert (
        "key_signals[0] missing required field: reference_range"
        in errors
    )


def test_key_signal_value_is_not_checked_against_reference_range():
    data = valid_output()
    data["key_signals"][0]["value"] = 150.0
    data["key_signals"][0]["reference_range"] = [90, 95]
    assert validate_output(data) == []


def test_notes_must_be_list_of_strings():
    data = valid_output()
    data["notes"] = "no issues"
    errors = validate_output(data)
    assert "notes must be a list" in errors

    data = valid_output()
    data["notes"] = ["ok", 123]
    errors = validate_output(data)
    assert "notes[1] must be a string" in errors
