import pytest

from scripts.smoke_test_local_pipeline import validate_dashboard_reports


def _report() -> dict:
    return {
        "timestamp": "2026-08-07T10:00:00Z",
        "risk_score": 0.8,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.8,
        "key_signals": [],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
        "risk_history": None,
        "anomaly_description": "An unusual cooling pattern was detected.",
        "possible_cause": "Restricted coolant flow may explain the pattern.",
        "recommended_action": ["Ask a mechanic to inspect the vehicle."],
    }


def test_validate_dashboard_reports_accepts_complete_report():
    assert validate_dashboard_reports({
        "cooling_degradation": _report(),
        "_data_source": {"cooling_degradation": "uploaded"},
    }) == ["cooling_degradation"]


def test_validate_dashboard_reports_rejects_empty_fallback():
    report = _report()
    report["anomaly_description"] = ""
    report["possible_cause"] = ""
    report["recommended_action"] = []

    with pytest.raises(RuntimeError, match="cooling_degradation"):
        validate_dashboard_reports({"cooling_degradation": report})


def test_validate_dashboard_reports_rejects_one_incomplete_component():
    complete = _report()
    incomplete = _report()
    incomplete["component"] = "air_intake_maf_anomaly"
    incomplete["anomaly_description"] = ""
    incomplete["possible_cause"] = ""
    incomplete["recommended_action"] = []

    with pytest.raises(RuntimeError, match="air_intake_maf_anomaly"):
        validate_dashboard_reports({
            "cooling_degradation": complete,
            "air_intake_maf_anomaly": incomplete,
        })
