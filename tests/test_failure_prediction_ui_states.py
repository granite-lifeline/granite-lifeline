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
    """Load dashboard/theme.py so theme tokens can be tested.

    After the refactor, THEME_TOKENS lives in dashboard/theme.py.
    """
    dashboard_dir = str(Path("dashboard").resolve())
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)

    spec = importlib.util.spec_from_file_location(
        "dashboard_theme_for_test",
        Path("dashboard/theme.py"),
    )
    theme_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme_module)
    return theme_module


def _detail_text() -> str:
    """Read dashboard/pages/detail.py as text for source-level checks."""
    return Path("dashboard/pages/detail.py").read_text(encoding="utf-8")


def _overview_text() -> str:
    """Read dashboard/pages/overview.py as text for source-level checks."""
    return Path("dashboard/pages/overview.py").read_text(encoding="utf-8")


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
        mock["cooling_degradation"]
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

    cooling_notes = get_data_quality_notes(mock["cooling_degradation"])
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
    src = _detail_text()

    assert 'show_icon_heading(' in src
    assert '"Risk Score Trend"' in src
    assert re.search(r'lucide_icon\(\s*"trending-up",\s*size=24', src)
    assert re.search(r'lucide_icon\(\s*"alert-triangle",\s*size=24', src)


def test_failure_prediction_uses_top_summary_banner_layout():
    """Test new summary banner appears before risk cards."""
    src = _detail_text()

    incomplete_index = src.index("Incomplete Data")
    heading_index = src.index('"Failure Prediction", failure_icon')
    card_call_index = src.index("_render_failure_prediction")
    risk_index = src.index('"Risk Score"')

    assert "section_heading_html(" in src
    assert incomplete_index < heading_index
    assert card_call_index < risk_index


def test_failure_prediction_value_state_emphasizes_key_values():
    """Test value state highlights probability and trip count evenly."""
    src = _detail_text()

    assert "{pct}%" in src
    assert "{cnt} trips" in src
    assert src.count("font-size:16px") >= 2
    assert "justify-content:center;gap:8px;flex-wrap:wrap" in src


def test_failure_prediction_pending_matches_info_notice_style():
    """Test pending state follows the compact info notice style."""
    src = _detail_text()

    assert "_html.escape(prediction_text)" in src
    assert re.search(r'lucide_icon\(\s*"info",\s*size=20', src)
    assert "border-radius:12px;padding:16px 20px" in src
    assert "max-width:600px" in src


def test_data_quality_notes_uses_content_card_style():
    """Test notes render as a content card when notes exist."""
    src = _detail_text()

    assert "Data Quality Notes</div>" in src
    assert 'info", size=18, color=tokens["accent"]' in src
    assert 'background:{tokens["glass_surface"]}' in src
    assert 'border:1px solid {tokens["glass_border"]}' in src
    assert 'border-bottom:2px solid {tokens["border"]}' in src


def test_overview_page_has_pdf_and_csv_export_controls():
    """Test Overview Page exposes filtered PDF and CSV downloads."""
    src = _overview_text()

    assert "_show_dashboard_export_controls(sorted_components, tokens)" in src
    assert "build_diagnostic_pdf_bytes" in src
    assert "build_key_signals_csv_bytes" in src
    assert 'section_heading_html(\n                "Export Report"' in src
    assert "Report components" in src
    assert "export_dropdown_components" in src
    assert "export_dropdown_pdf" in src
    assert "export_dropdown_csv" in src
    assert "overview_component_choice_" in src
    assert "overview_pdf_choice_" in src
    assert "overview_csv_choice_" in src
    assert "_make_export_file_name" in src
    assert "component_names" in src
    assert "pdf_detail_names" in src
    assert "csv_detail_names" in src
    assert 'strftime("%Y_%m_%d")' in src
    assert "PDF sections" in src
    assert "CSV columns" in src
    assert "st.checkbox(" in src
    assert "_build_zip_bytes" in src
    assert "st.download_button(" in src
    assert '"Download PDF"' in src
    assert '"Download CSV"' in src


def test_light_and_dark_theme_tokens_support_failure_prediction_card():
    """Test light and dark themes both include card styling tokens."""
    theme_module = load_dashboard_app_module()
    needed_tokens = [
        "glass_surface",
        "glass_border",
        "shadow",
        "accent",
        "accent_hover",
        "accent_subtle",
        "focus",
        "text",
        "text_secondary",
    ]

    for mode in ["light", "dark"]:
        tokens = theme_module.THEME_TOKENS[mode]
        for token in needed_tokens:
            assert token in tokens
            assert tokens[token]
