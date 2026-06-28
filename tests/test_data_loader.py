"""
Tests for dashboard data loader.
"""

import pytest
from dashboard.data_loader import (
    load_report_data,
    convert_to_component_dict,
    load_dashboard_data
)


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
    assert len(data) == 3

    # Verify all expected components are present
    assert "cooling_system_stress" in data
    assert "air_intake_maf_anomaly" in data
    assert "accelerator_pedal_sensor" in data

    # Verify data structure for one component
    cooling = data["cooling_system_stress"]
    assert cooling["risk_level"] == "High"
    assert cooling["risk_score"] == 0.86
    assert "key_signals" in cooling
    assert "risk_history" in cooling
    assert "anomaly_description" in cooling
    assert "possible_cause" in cooling
    assert "recommended_action" in cooling


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
        "recommended_action"
    ]

    for component_data in data.values():
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
