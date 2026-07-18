"""Tests for Failure Prediction UI states and theme support."""

import importlib.util
import re
import sys
from pathlib import Path

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
    # Load mock data directly (bypasses real pipeline) so the exact
    # values from ui_required_data.json are used for formatting checks.
    from dashboard.data_loader import (
        load_report_data, convert_to_component_dict
    )
    mock = convert_to_component_dict(
        load_report_data("dashboard/tests/ui_required_data.json")
    )

    cooling_text, cooling_has_value = format_failure_prediction_text(
        mock["cooling_system_stress"]
    )
    intake_text, intake_has_value = format_failure_prediction_text(
        mock["air_intake_maf_anomaly"]
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
    from dashboard.data_loader import (
        load_report_data, convert_to_component_dict
    )
    mock = convert_to_component_dict(
        load_report_data("dashboard/tests/ui_required_data.json")
    )

    cooling_notes = get_data_quality_notes(mock["cooling_system_stress"])
    intake_notes = get_data_quality_notes(mock["air_intake_maf_anomaly"])

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
    assert re.search(r'lucide_icon\(\s*"alert-triangle",\s*size=24', app_text)


def test_failure_prediction_uses_top_summary_banner_layout():
    """Test new summary banner appears before risk cards."""
    app_text = Path("dashboard/app.py").read_text(encoding="utf-8")

    incomplete_index = app_text.index("Incomplete Data")
    heading_index = app_text.index("Failure Prediction</h2>")
    card_call_index = app_text.index("show_failure_prediction_card")
    risk_index = app_text.index('show_icon_heading("Risk Score"')

    assert "grid-template-columns: 24px auto 24px" in app_text
    assert incomplete_index < heading_index
    assert card_call_index < risk_index


def test_failure_prediction_value_state_emphasizes_key_values():
    """Test value state highlights probability and trip count evenly."""
    app_text = Path("dashboard/app.py").read_text(encoding="utf-8")

    assert "{failure_percent}%" in app_text
    assert "{cycles_count} trips" in app_text
    assert app_text.count("font-size: 16px") >= 2
    assert "justify-content: center; gap: 8px; flex-wrap: wrap" in app_text


def test_failure_prediction_pending_matches_info_notice_style():
    """Test pending state follows the compact info notice style."""
    app_text = Path("dashboard/app.py").read_text(encoding="utf-8")

    assert "html.escape(prediction_text)" in app_text
    assert re.search(r'lucide_icon\(\s*"info",\s*size=20', app_text)
    assert "border-radius: 12px; padding: 16px 20px" in app_text
    assert "max-width: 600px" in app_text


def test_data_quality_notes_uses_content_card_style():
    """Test notes render as a content card when notes exist."""
    app_text = Path("dashboard/app.py").read_text(encoding="utf-8")

    assert "Data Quality Notes</div>" in app_text
    assert 'info", size=18, color=tokens["accent"]' in app_text
    assert 'background: {tokens["glass_surface"]}' in app_text
    assert 'border: 1px solid {tokens["glass_border"]}' in app_text
    assert 'border-bottom: 2px solid {tokens["border"]}' in app_text


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
