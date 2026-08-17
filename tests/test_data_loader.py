"""
Tests for dashboard data loader.
"""

import json
from pathlib import Path

import pytest
from dashboard.data_loader import (
    load_report_data,
    convert_to_component_dict,
    load_static_dashboard_data,
    load_dashboard_data,
    load_model_output_for_dashboard,
)


DASHBOARD_TEST_DATA_DIR = Path("dashboard/tests")


def test_load_report_data_success():
    """Test loading valid report data from JSON file."""
    data = load_report_data("dashboard/tests/ui_required_data.json")

    assert isinstance(data, list)
    assert len(data) == 5

    # Check first component
    assert data[0]["component"] == "cooling_degradation"
    assert data[0]["risk_level"] == "High"
    assert data[0]["risk_score"] == 0.86


def test_load_static_dashboard_data():
    """Test static demo loading without invoking the report pipeline."""
    data = load_static_dashboard_data("dashboard/tests/ui_required_data.json")
    component_data = {
        k: v for k, v in data.items() if k != "_data_source"
    }

    assert len(component_data) == 5
    assert set(data["_data_source"].values()) == {"mock"}
    assert "intake_air_temperature_sensor_fault" in component_data
    assert "map_load_signal_plausibility_fault" in component_data


def test_batch_model_output_keeps_each_affected_component(monkeypatch):
    """Dashboard input keeps every Medium/High component from batch output."""
    calls = []

    def make_model_piece(component, score, level, timestamp):
        return {
            "timestamp": timestamp,
            "anomaly_type": component,
            "risk_score": score,
            "risk_level": level,
            "component": component,
            "prediction_confidence": 0.8,
            "key_signals": [
                {
                    "feature": "coolant_temp",
                    "value": 100.0,
                    "unit": "°C",
                    "reference_range": [90.0, 95.0],
                },
            ],
            "estimated_cycles_to_failure": None,
            "estimated_failure_probability": None,
            "notes": [],
        }

    def fake_generate_report(model_output, risk_history=None):
        calls.append((model_output["component"], risk_history))
        return {
            **model_output,
            "risk_history": risk_history,
            "anomaly_description": "some issue",
            "possible_cause": "some cause",
            "recommended_action": ["check soon"],
        }

    import report_layer.pipeline.report_generator as report_generator

    monkeypatch.setattr(
        report_generator,
        "generate_report",
        fake_generate_report,
    )

    cooling = make_model_piece(
        "cooling_degradation", 0.91, "High", "2026-01-01T10:00:00Z"
    )
    air_secondary = make_model_piece(
        "air_intake_maf_anomaly", 0.71, "Medium", "2026-01-01T10:00:00Z"
    )
    air_primary = make_model_piece(
        "air_intake_maf_anomaly", 0.86, "Medium", "2026-01-01T10:10:00Z"
    )
    pedal_low = make_model_piece(
        "accelerator_pedal_sensor", 0.2, "Low", "2026-01-01T10:10:00Z"
    )
    cooling["secondary_risk"] = air_secondary
    air_primary["secondary_risk"] = pedal_low

    data = load_model_output_for_dashboard(
        {
            "summary": cooling,
            "windows": [
                {
                    "trip_id": "trip_0001",
                    "segment_id": "trip_0001_seg_001",
                    "window_id": "trip_0001_seg_001__w000",
                    **cooling,
                },
                {
                    "trip_id": "trip_0001",
                    "segment_id": "trip_0001_seg_001",
                    "window_id": "trip_0001_seg_001__w001",
                    **air_primary,
                },
            ],
        },
        source="uploaded",
    )

    assert set(k for k in data if k != "_data_source") == {
        "cooling_degradation",
        "air_intake_maf_anomaly",
    }
    assert data["air_intake_maf_anomaly"]["risk_score"] == 0.86
    assert data["_data_source"] == {
        "cooling_degradation": "uploaded",
        "air_intake_maf_anomaly": "uploaded",
    }
    assert [component for component, _ in calls] == [
        "cooling_degradation",
        "air_intake_maf_anomaly",
    ]
    air_history = data["air_intake_maf_anomaly"]["risk_history"]
    assert [entry["risk_score"] for entry in air_history] == [0.71, 0.86]


def test_low_risk_model_output_does_not_create_dashboard_card(monkeypatch):
    """A no-risk analysis opens the Dashboard without placeholder reports."""
    import report_layer.pipeline.report_generator as report_generator

    monkeypatch.setattr(
        report_generator,
        "generate_report",
        lambda *_args, **_kwargs: pytest.fail(
            "Low-risk output should not invoke report generation"
        ),
    )
    low = {
        "timestamp": "2026-01-01T10:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 0.2,
        "risk_level": "Low",
        "component": "cooling_degradation",
        "prediction_confidence": 0.8,
        "key_signals": [],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
    }

    assert load_model_output_for_dashboard(low, source="uploaded") == {
        "_data_source": {}
    }


def test_load_report_data_file_not_found():
    """Test error handling when file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_report_data("nonexistent_file.json")


def test_convert_to_component_dict():
    """Test converting report list to component-keyed dictionary."""
    report_list = [
        {"component": "cooling_degradation", "risk_score": 0.86},
        {"component": "air_intake_maf_anomaly", "risk_score": 0.61},
    ]

    result = convert_to_component_dict(report_list)

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "cooling_degradation" in result
    assert "air_intake_maf_anomaly" in result
    assert result["cooling_degradation"]["risk_score"] == 0.86


def test_convert_to_component_dict_missing_component():
    """Test handling reports without component field."""
    report_list = [
        {"component": "cooling_degradation", "risk_score": 0.86},
        {"risk_score": 0.61},  # Missing component field
    ]

    result = convert_to_component_dict(report_list)

    # Should only include the valid component
    assert len(result) == 1
    assert "cooling_degradation" in result


def test_load_dashboard_data():
    """Test end-to-end dashboard data loading."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    assert isinstance(data, dict)
    # Exclude the _data_source metadata key when counting components
    component_data = {
        k: v for k, v in data.items() if k != "_data_source"
    }
    assert len(component_data) == 5

    # Verify all 5 confirmed anomaly types are present.
    cooling_key = "cooling_degradation"
    assert cooling_key in component_data
    assert "air_intake_maf_anomaly" in component_data
    assert "accelerator_pedal_sensor" in component_data
    assert "intake_air_temperature_sensor_fault" in component_data
    assert "map_load_signal_plausibility_fault" in component_data

    # Verify data structure for the cooling component
    cooling = component_data[cooling_key]
    if data["_data_source"].get(cooling_key) == "real":
        sample_path = Path(
            "model_layer/ttm-related/outputs/kit_residual_sample.json"
        )
        expected_risk_level = json.loads(
            sample_path.read_text(encoding="utf-8")
        )["risk_level"]
        assert cooling["risk_level"] == expected_risk_level
    else:
        assert cooling["risk_level"] in {"High", "Medium", "Low", None}
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

        # Verify risk_history structure — None is allowed (real pipeline
        # does not yet populate history; mock data has a list)
        rh = component_data["risk_history"]
        if rh is not None:
            for entry in rh:
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
