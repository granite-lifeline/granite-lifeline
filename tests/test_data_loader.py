"""
Tests for dashboard data loader.
"""

import json
from pathlib import Path

import pytest
from dashboard.data_loader import (
    load_report_data,
    convert_to_component_dict,
    load_dashboard_data
)


DASHBOARD_TEST_DATA_DIR = Path("dashboard/tests")


def test_load_report_data_success():
    """Test loading valid report data from JSON file."""
    data = load_report_data("dashboard/tests/ui_required_data.json")

    assert isinstance(data, list)
    assert len(data) == 3

    # Check first component
    assert data[0]["component"] == "cooling_system_stress"
    assert data[0]["risk_level"] == "High"
    assert data[0]["risk_score"] == 0.86


def test_load_report_data_file_not_found():
    """Test error handling when file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_report_data("nonexistent_file.json")


def test_convert_to_component_dict():
    """Test converting report list to component-keyed dictionary."""
    report_list = [
        {"component": "cooling_system_stress", "risk_score": 0.86},
        {"component": "air_intake_maf_anomaly", "risk_score": 0.61},
    ]

    result = convert_to_component_dict(report_list)

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "cooling_system_stress" in result
    assert "air_intake_maf_anomaly" in result
    assert result["cooling_system_stress"]["risk_score"] == 0.86


def test_convert_to_component_dict_missing_component():
    """Test handling reports without component field."""
    report_list = [
        {"component": "cooling_system_stress", "risk_score": 0.86},
        {"risk_score": 0.61},  # Missing component field
    ]

    result = convert_to_component_dict(report_list)

    # Should only include the valid component
    assert len(result) == 1
    assert "cooling_system_stress" in result


def test_load_dashboard_data():
    """Test end-to-end dashboard data loading."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    assert isinstance(data, dict)
    # Exclude the _data_source metadata key when counting components
    component_data = {
        k: v for k, v in data.items() if k != "_data_source"
    }
    assert len(component_data) == 3

    # Verify all 3 confirmed anomaly types are present (cooling may appear
    # under its canonical key "cooling_degradation" when loaded via the
    # real-data path, or under the legacy mock key "cooling_system_stress"
    # when falling back).
    cooling_key = (
        "cooling_degradation"
        if "cooling_degradation" in component_data
        else "cooling_system_stress"
    )
    assert cooling_key in component_data
    assert "air_intake_maf_anomaly" in component_data
    assert "accelerator_pedal_sensor" in component_data

    # Verify data structure for the cooling component
    cooling = component_data[cooling_key]
    assert cooling["risk_level"] == "High"
    assert "key_signals" in cooling
    assert "risk_history" in cooling
    assert "anomaly_description" in cooling
    assert "possible_cause" in cooling
    assert "recommended_action" in cooling
    assert "estimated_failure_probability" in cooling
    assert "estimated_cycles_to_failure" in cooling

    # Verify _data_source metadata is present
    assert "_data_source" in data
    assert isinstance(data["_data_source"], dict)


def test_report_data_interface_compliance():
    """Test that loaded data complies with INTERFACE.md fields."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    required_fields = [
        "timestamp",
        "risk_score",
        "risk_level",
        "component",
        "prediction_confidence",
        "key_signals",
        "risk_history",
        "anomaly_description",
        "possible_cause",
        "recommended_action",
        "estimated_cycles_to_failure",
        "estimated_failure_probability",
        "notes",
    ]

    # Skip the _data_source metadata entry — it is not a component report
    for component_data in (
        v for k, v in data.items() if k != "_data_source"
    ):
        for field in required_fields:
            assert field in component_data, \
                f"Missing required field: {field}"

        # Verify key_signals structure
        for signal in component_data["key_signals"]:
            assert "feature" in signal
            assert "value" in signal
            assert "unit" in signal
            assert "reference_range" in signal

        # Verify risk_history structure
        for entry in component_data["risk_history"]:
            assert "timestamp" in entry
            assert "risk_score" in entry

        # Verify recommended_action is a list
        assert isinstance(component_data["recommended_action"], list)

        # Verify future Failure Prediction UI fields are passed through
        assert "estimated_cycles_to_failure" in component_data
        assert "estimated_failure_probability" in component_data
        assert isinstance(component_data["notes"], list)


def test_all_dashboard_test_data_has_failure_prediction_fields():
    """Test all dashboard UI fixtures include failure prediction fields."""
    required_fields = [
        "estimated_cycles_to_failure",
        "estimated_failure_probability",
        "notes",
    ]

    for path in DASHBOARD_TEST_DATA_DIR.glob("ui_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for report in data:
            for field in required_fields:
                assert field in report, f"{path} missing {field}"
            assert isinstance(report["notes"], list), \
                f"{path} notes must be a list"


def test_dashboard_test_data_covers_failure_prediction_states():
    """Test fixtures cover value, null, and notes display states."""
    reports = []
    for path in DASHBOARD_TEST_DATA_DIR.glob("ui_*.json"):
        reports.extend(json.loads(path.read_text(encoding="utf-8")))

    has_value_state = any(
        report.get("estimated_failure_probability") is not None
        and report.get("estimated_cycles_to_failure") is not None
        for report in reports
    )
    has_null_state = any(
        report.get("estimated_failure_probability") is None
        or report.get("estimated_cycles_to_failure") is None
        for report in reports
    )
    has_notes_state = any(report.get("notes") for report in reports)

    assert has_value_state
    assert has_null_state
    assert has_notes_state
