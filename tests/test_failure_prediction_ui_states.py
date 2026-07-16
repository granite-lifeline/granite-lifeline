"""Tests for Failure Prediction UI states and theme support."""

import importlib.util
import re
import sys
from pathlib import Path

from dashboard.data_loader import load_dashboard_data
from dashboard.failure_prediction import (
    PENDING_FAILURE_PREDICTION_TEXT,
    format_failure_prediction_text,
    get_data_quality_notes,
)


def load_dashboard_app_module():
    """Load dashboard/app.py so theme tokens can be tested."""
    dashboard_dir = str(Path("dashboard").resolve())
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)

    spec = importlib.util.spec_from_file_location(
        "dashboard_app_for_test",
        Path("dashboard/app.py"),
    )
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return app_module


def test_failure_prediction_has_value_and_null_states():
    """Test dashboard data covers has-value and null UI states."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    cooling_text, cooling_has_value = format_failure_prediction_text(
        data["cooling_system_stress"]
    )
    intake_text, intake_has_value = format_failure_prediction_text(
        data["air_intake_maf_anomaly"]
    )

    expected_text = (
        "72% probability of failure within the next 15 trips"
    )

    assert cooling_text == expected_text
    assert cooling_has_value is True
    assert intake_text == PENDING_FAILURE_PREDICTION_TEXT
    assert intake_has_value is False


def test_data_quality_notes_visible_and_hidden_states():
    """Test notes list displays only when non-empty."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    cooling_notes = get_data_quality_notes(data["cooling_system_stress"])
    intake_notes = get_data_quality_notes(data["air_intake_maf_anomaly"])

    assert cooling_notes == [
        (
            "Coolant readings include repaired sensor gaps from the "
            "latest drive cycle."
        ),
        "Failure estimate may become more stable after more drive cycles.",
    ]
    assert intake_notes == []


def test_failure_prediction_icon_differs_from_trend_icon():
    """Test Failure Prediction does not reuse the trend icon."""
    app_text = Path("dashboard/app.py").read_text(encoding="utf-8")

    assert 'show_icon_heading("Risk Score Trend"' in app_text
    assert re.search(r'lucide_icon\(\s*"trending-up",\s*size=24', app_text)
    assert 'lucide_icon("alert-triangle", size=22' in app_text


def test_light_and_dark_theme_tokens_support_failure_prediction_card():
    """Test light and dark themes both include card styling tokens."""
    app_module = load_dashboard_app_module()
    needed_tokens = [
        "glass_surface",
        "glass_border",
        "shadow",
        "accent",
        "text",
        "text_secondary",
    ]

    for mode in ["light", "dark"]:
        tokens = app_module.THEME_TOKENS[mode]
        for token in needed_tokens:
            assert token in tokens
            assert tokens[token]
