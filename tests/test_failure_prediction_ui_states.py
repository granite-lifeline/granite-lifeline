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

    # This fixture's cooling_degradation entry is risk_level "High" with
    # a non-null estimated_failure_probability — "chance of crossing
    # into High risk" would be self-contradictory here, so it must not
    # appear; see test_failure_prediction.py for the dedicated unit test.
    assert "chance of crossing" not in cooling_text
    assert "already reached the High-risk threshold" in cooling_text
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
    assert '"Risk Trend"' in src
    assert re.search(r'lucide_icon\(\s*"trending-up",\s*size=24', src)
    assert re.search(r'lucide_icon\(\s*"alert-triangle",\s*size=24', src)


def test_failure_prediction_uses_top_summary_banner_layout():
    """Test new summary banner appears before risk cards."""
    src = _detail_text()

    incomplete_index = src.index("Incomplete Data")
    heading_index = src.index('"Failure Prediction", failure_icon')
    card_call_index = src.index("_render_failure_prediction")
    risk_index = src.index('"Risk Level"')

    assert "section_heading_html(" in src
    assert incomplete_index < heading_index
    assert card_call_index < risk_index


def test_failure_prediction_value_state_explains_threshold_projection():
    """Test value state renders the qualified projection text."""
    src = _detail_text()

    assert "_html.escape(prediction_text)" in src
    assert "probability of failure within the next" not in src


def test_failure_prediction_pending_matches_info_notice_style():
    """Test pending state follows the compact info notice style."""
    src = _detail_text()

    assert "_html.escape(prediction_text)" in src
    assert re.search(r'lucide_icon\(\s*"info",\s*size=20', src)
    assert "border-radius:12px;padding:16px 20px" in src
    assert "max-width:600px" in src


def test_owner_limitation_replaces_internal_data_notes():
    """Detail page shows a plain limitation, not internal model notes."""
    src = _detail_text()

    assert "Data Quality Notes</div>" not in src
    assert "This is a risk-pattern estimate, not a confirmed mechanical fault." in src
    assert "Important limitation</div>" not in src
    assert 'background:{tokens["glass_surface"]}' in src


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


def test_overview_export_workflow_has_quick_download_then_options():
    """Test GL-380 keeps downloads visible before advanced filters."""
    src = _overview_text()

    assert "overview_export_options_open" in src
    assert "Ready to download" in src
    assert "export-quick-summary" in src
    assert "Customize export options" in src
    assert "export_options_toggle" in src
    assert "section_key in DEFAULT_EXPORT_SECTIONS" in src

    download_index = src.index("overview_download_pdf")
    options_index = src.index("export_options_toggle")
    component_filter_index = src.index("export_dropdown_components")

    assert download_index < options_index
    assert options_index < component_filter_index


def test_overview_export_panel_ui_has_cards_and_options_panel():
    """Test GL-381 export panel has polished download and options UI."""
    src = _overview_text()

    assert "def _export_download_card_html" in src
    assert "export-download-card" in src
    assert "export-download-icon" in src
    assert "export-download-title" in src
    assert "export-download-meta" in src
    assert "Diagnostic report" in src
    assert "Key signals table" in src
    assert "csv_card_meta" in src
    assert "pdf_card_meta" in src
    assert '"activity",' in src
    assert '"table",' not in src

    assert ".st-key-overview_download_pdf button" in src
    assert ".st-key-overview_download_csv button" in src
    assert src.count('background: {tokens["accent"]} !important;') >= 2
    assert src.count('color: {tokens["accent_contrast"]} !important;') >= 4
    assert ".st-key-export_options_toggle button" in src
    assert ".st-key-export_options_panel" in src
    assert 'st.container(key="export_options_panel")' in src
    assert '<div class="export-options-title">Export options</div>' in src


def test_empty_and_error_states_use_shared_polished_components():
    """Test GL-382 replaces bare Streamlit warnings/errors in key flows."""
    overview_src = _overview_text()
    detail_src = _detail_text()

    assert "Choose a CSV file first" in overview_src
    assert "PDF export unavailable" in overview_src
    assert "Component not found" in detail_src
    assert "selected_component_keys = list(component_keys)" in overview_src

    assert "empty_state_html(" in overview_src
    assert "danger_card_html(" in overview_src
    assert "empty_state_html(" in detail_src

    assert "Please select a CSV file before clicking Run Analysis." not in (
        overview_src
    )
    assert "Select at least one component to export." not in overview_src
    assert "No export components selected" not in overview_src
    assert 'st.error("Component not found.")' not in detail_src


def test_detail_empty_sections_have_user_facing_empty_states():
    """GL-383: detail page covers missing trend and signal sections."""
    src = _detail_text()

    assert "Incomplete Data" in src
    assert "Trend not available" in src
    assert "No signal data available" in src
    assert "Risk Trend data" in src
    assert "Key Signals data" in src


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
