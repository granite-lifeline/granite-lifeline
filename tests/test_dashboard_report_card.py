"""Tests for dashboard diagnostic report card helpers."""

import json
from pathlib import Path

from dashboard import app


MOCK_REPORT_PATH = Path("tests/mock_data/mock_report_output.json")

ALLOWED_REPORT_FIELDS = {
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
}


def read_reports():
    with open(MOCK_REPORT_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def test_mock_report_file_uses_only_interface_fields():
    reports = read_reports()

    for report in reports:
        extra_fields = set(report.keys()) - ALLOWED_REPORT_FIELDS
        assert extra_fields == set()


def test_mock_report_file_has_all_main_risk_levels():
    reports = read_reports()
    risk_levels = {
        report.get("risk_level")
        for report in reports
        if report.get("risk_level")
    }

    assert "Low" in risk_levels
    assert "Medium" in risk_levels
    assert "High" in risk_levels


def test_find_report_for_component_from_mock_data():
    report = app.get_report_for_component("cooling_system_stress")

    assert report["component"] == "cooling_system_stress"
    assert report["risk_level"] == "High"
    assert report["prediction_confidence"] == 0.88


def test_report_text_uses_fallback_for_missing_or_empty_value():
    report = {
        "anomaly_description": "",
    }

    assert app.get_report_text(
        report,
        "anomaly_description",
        "Anomaly description is not available yet.",
    ) == "Anomaly description is not available yet."

    assert app.get_report_text(
        report,
        "possible_cause",
        "Possible cause is not available yet.",
    ) == "Possible cause is not available yet."


def test_recommended_actions_use_fallback_for_empty_list():
    report = {
        "recommended_action": [],
    }

    assert app.get_report_actions(report) == [
        "Recommended actions are not available yet."
    ]


def test_recommended_actions_skip_empty_items():
    report = {
        "recommended_action": [
            "Check coolant level.",
            "",
            "   ",
            "Ask a mechanic to inspect the cooling system.",
        ],
    }

    assert app.get_report_actions(report) == [
        "Check coolant level.",
        "Ask a mechanic to inspect the cooling system.",
    ]


def test_prediction_confidence_text_for_valid_value():
    report = {
        "prediction_confidence": 0.84,
    }

    assert app.get_confidence_text(report) == "Prediction confidence: 84%"


def test_prediction_confidence_text_uses_fallback_for_bad_value():
    assert app.get_confidence_text({}) == "Prediction confidence unavailable"
    assert app.get_confidence_text({
        "prediction_confidence": 1.5,
    }) == "Prediction confidence unavailable"
    assert app.get_confidence_text({
        "prediction_confidence": "not a number",
    }) == "Prediction confidence unavailable"


def test_risk_badge_uses_fallback_for_missing_risk_level():
    badge_html = app.get_report_risk_badge_html(
        {},
        app.THEME_TOKENS["light"],
    )

    assert "Risk level unavailable" in badge_html
