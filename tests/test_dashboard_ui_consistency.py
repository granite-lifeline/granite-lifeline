"""Source checks for Dashboard UI consistency and Carbon theme work."""

import re
import sys
from pathlib import Path

from dashboard.theme import ICONS


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _dashboard_python_sources() -> list[Path]:
    return sorted(Path("dashboard").rglob("*.py"))


def test_streamlit_app_routes_import_cleanly():
    """GL-383: app entry point can import every Dashboard route."""
    dashboard_dir = str(Path("dashboard").resolve())
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)

    import dashboard.app as app

    assert callable(app.main)
    assert callable(app.show_overview_page)
    assert callable(app.show_detail_page)
    assert callable(app.show_local_run_page)
    assert callable(app.show_what_if_page)


def test_theme_defines_shared_dashboard_ui_classes():
    src = _read("dashboard/theme.py")

    for class_name in [
        "gl-page-title",
        "gl-page-subtitle",
        "gl-section-heading",
        "gl-glass-panel",
        "gl-empty-state",
    ]:
        assert class_name in src


def test_theme_uses_ibm_carbon_palette_tokens():
    src = _read("dashboard/theme.py")

    for token in [
        '"bg": "#f4f4f4"',
        '"surface_alt": "#f4f4f4"',
        '"border": "#e0e0e0"',
        '"text": "#161616"',
        '"text_secondary": "#525252"',
        '"accent": "#0f62fe"',
        '"accent_hover": "#0043ce"',
        '"accent_subtle": "#edf5ff"',
        '"focus": "#0f62fe"',
        '"bg": "#161616"',
        '"surface": "#262626"',
        '"surface_alt": "#393939"',
        '"border": "#525252"',
        '"text": "#f4f4f4"',
        '"accent": "#78a9ff"',
        '"accent_hover": "#a6c8ff"',
    ]:
        assert token in src


def test_global_buttons_use_carbon_hover_and_focus_tokens():
    src = _read("dashboard/theme.py")

    assert 'background: {tokens["accent_subtle"]} !important;' in src
    assert 'background: {tokens["accent_hover"]} !important;' in src
    assert 'outline: 2px solid {tokens["focus"]} !important;' in src


def test_streamlit_builtin_running_decoration_is_hidden():
    """GL-386: use our loading card instead of Streamlit's blue bar."""
    src = _read("dashboard/theme.py")

    assert '[data-testid="stDecoration"]' in src
    assert '[data-testid="stStatusWidget"]' in src
    assert "display: none !important;" in src


def test_reusable_ui_helpers_cover_title_heading_and_empty_state():
    src = _read("dashboard/ui_components.py")

    assert "def page_title_html" in src
    assert "def section_heading_html" in src
    assert "def empty_state_html" in src


def test_literal_lucide_icons_are_registered():
    """GL-383: prevent runtime KeyError from unregistered icon names."""
    missing: list[str] = []
    for path in _dashboard_python_sources():
        src = path.read_text(encoding="utf-8")
        for icon_name in re.findall(r'lucide_icon\(\s*"([^"]+)"', src):
            if icon_name not in ICONS:
                missing.append(f"{path}:{icon_name}")

    assert missing == []


def test_main_dashboard_pages_use_shared_consistency_helpers():
    overview_src = _read("dashboard/pages/overview.py")
    detail_src = _read("dashboard/pages/detail.py")
    local_run_src = _read("dashboard/pages/local_run.py")
    what_if_src = _read("dashboard/pages/what_if.py")

    assert "page_title_html(" in overview_src
    assert "page_title_html(" in detail_src
    assert "page_title_html(" in local_run_src
    assert "page_title_html(" in what_if_src

    assert "empty_state_html(" in overview_src
    assert "empty_state_html(" in detail_src
    assert "empty_state_html(" in what_if_src

    assert "section_heading_html(" in overview_src
    assert "section_heading_html(" in detail_src


def test_export_panel_keeps_downloads_available_when_selection_is_empty():
    """GL-383: empty component selection falls back to all components."""
    src = _read("dashboard/pages/overview.py")

    fallback_index = src.index(
        "selected_component_keys = list(component_keys)"
    )
    components_index = src.index("selected_components = [")
    summary_index = src.index("summary_html = (")

    assert fallback_index < components_index
    assert fallback_index < summary_index
    assert "No export components selected" not in src


def test_export_download_buttons_share_primary_visual_style():
    """GL-383: PDF and CSV export buttons stay visually consistent."""
    src = _read("dashboard/pages/overview.py")

    pdf_rule = src.index(".st-key-overview_download_pdf button {{")
    csv_rule = src.index(".st-key-overview_download_csv button {{")

    for rule_start in [pdf_rule, csv_rule]:
        rule = src[rule_start: rule_start + 260]
        assert 'background: {tokens["accent"]} !important;' in rule
        assert 'border: 1.5px solid {tokens["accent"]} !important;' in rule
        assert 'color: {tokens["accent_contrast"]} !important;' in rule


def test_key_empty_and_error_states_do_not_use_bare_streamlit_alerts():
    """GL-383: polished states remain on shared Dashboard components."""
    overview_src = _read("dashboard/pages/overview.py")
    detail_src = _read("dashboard/pages/detail.py")

    assert "Choose a CSV file first" in overview_src
    assert "PDF export unavailable" in overview_src
    assert "Component not found" in detail_src
    assert 'st.warning("Please select a CSV file' not in overview_src
    assert 'st.error("Component not found.")' not in detail_src


def test_csv_analysis_loading_state_is_visible_and_disables_buttons():
    """GL-386: CSV analysis should show clear loading feedback."""
    src = _read("dashboard/pages/overview.py")

    assert "CSV_ANALYSIS_RUNNING_KEY" in src
    assert "Analysing your CSV..." in src
    assert "CSV_PROGRESS_STAGES" in src
    assert "checking_upload" in src
    assert "csv-analysis-percent" in src
    assert "conic-gradient(" in src
    assert "csv-analysis-progress-rail" not in src
    assert "csv-analysis-progress-fill" not in src
    assert "csv-analysis-spinner" not in src
    assert "st.progress(" not in src
    assert '"Analysing..." if analysis_running else "Run Analysis"' in src
    assert "disabled=analysis_running" in src
    assert ".st-key-csv_submit_btn button:disabled" in src
    assert ".st-key-landing_run_btn button:disabled" in src


def test_csv_analysis_loading_is_cleared_before_failure_states():
    """GL-415: failure and timeout states should replace loading feedback."""
    src = _read("dashboard/pages/overview.py")

    assert "def _clear_csv_analysis_loading" in src
    assert 'hasattr(target, "empty")' in src
    assert src.count("_clear_csv_analysis_loading(loading_slot)") >= 5


def test_selected_file_upload_button_is_hidden():
    """GL-386: selected file row should not show a second Upload button."""
    src = _read("dashboard/pages/overview.py")

    assert '[data-testid="stFileUploaderDropzone"] button::after' in src
    assert '[data-testid="stFileUploader"] button::after' not in src
    assert "section > div + button" in src
    assert "> button:not(:first-child)" in src
    assert '.st-key-csv_upload_section' in src
    assert '.st-key-landing_upload_card' in src
    assert '[data-testid="stFileUploaderDeleteBtn"]' in src


def test_local_run_page_has_guide_layout_and_copy_commands():
    """GL-426: local-run help uses a structured guide page."""
    app_src = _read("dashboard/app.py")
    src = _read("dashboard/pages/local_run.py")

    assert "from pages.local_run import show_local_run_page" in app_src
    assert 'st.session_state["page"] == "local_run"' in app_src
    assert "show_local_run_page()" in app_src
    assert "def show_local_run_page() -> None" in src
    assert "How to Run Locally" in src
    assert "Setup overview" in src
    assert (
        "Follow these steps to run the app on your computer and try "
        in src
    )
    assert "data, model, report, and dashboard pipeline" not in src
    assert "Prepare project" in src
    assert "Install tools" in src
    assert "Start Granite" in src
    assert "Open dashboard" in src
    assert "Why local setup is needed" not in src
    assert "Before running" in src
    assert "Copy commands" in src
    assert "Setup overview included" in src
    assert "uv run streamlit run dashboard/app.py" in src


def test_local_run_copy_commands_are_grouped_by_step():
    """GL-427: commands should be grouped into easy-to-copy blocks."""
    src = _read("dashboard/pages/local_run.py")

    assert "def _command_block(" in src
    assert "Copy this block" in src
    assert "local-run-command-label" in src
    assert "local-run-copy-hint" in src
    assert "local-run-command-note" in src
    assert 'with st.container(key=f"local_run_command_{number}")' in src
    assert "Project setup" in src
    assert "Install command" in src
    assert "Report helper commands" in src
    assert "Dashboard commands" in src
    assert (
        "git clone https://github.com/granite-lifeline/granite-lifeline.git\\n"
        in src
    )
    assert "ollama serve\\nollama pull granite4.1:8b" in src
    assert (
        "uv run python -m report_layer.rag.symptom_knowledge_indexer\\n"
        in src
    )


def test_local_run_page_uses_consistent_dashboard_styling():
    """GL-428: local-run guide follows Dashboard and What-If styling."""
    overview_src = _read("dashboard/pages/overview.py")
    src = _read("dashboard/pages/local_run.py")

    assert 'background: transparent !important;' in overview_src
    assert 'border: 1.5px solid {tokens["border"]} !important;' in overview_src
    assert 'background: {hex_to_rgba(tokens["accent"], 0.07)} !important;' in (
        overview_src
    )
    assert ".st-key-local_run_commands_card" in src
    assert 'background: {tokens["glass_surface"]};' in src
    assert 'border: 1px solid {tokens["glass_border"]};' in src
    assert 'border-radius: 16px;' in src
    assert 'box-shadow: 0 2px 12px {tokens["shadow"]};' in src
    assert ".local-run-command-label" in src
    assert 'background: {tokens["surface_alt"]};' in src
    assert 'border-radius: 12px 12px 0 0;' in src
    assert '[data-testid="stCodeBlock"]' in src
    assert 'border-radius: 0 0 12px 12px;' in src
    assert 'border-left: 4px solid {tokens["accent"]};' in src
    assert ".st-key-local_run_back_btn button:active" in src
    assert "@media (max-width: 760px)" in src


def test_local_run_navigation_and_upload_behaviour_are_preserved():
    """GL-429: local-run UI navigation should not break upload behaviour."""
    overview_src = _read("dashboard/pages/overview.py")
    local_run_src = _read("dashboard/pages/local_run.py")

    assert 'st.session_state["page"] = "local_run"' in overview_src
    assert 'st.session_state["page"] = "overview"' in local_run_src
    assert 'key="local_run_back_btn"' in local_run_src
    assert "st.rerun()" in local_run_src

    # Upload behaviour still uses the existing upload and analysis widgets.
    assert 'key="landing_csv_uploader"' in overview_src
    assert 'key="landing_run_btn"' in overview_src
    assert 'key="csv_file_uploader"' in overview_src
    assert 'key="csv_submit_btn"' in overview_src
    assert '"Analysing..." if analysis_running else "Run Analysis"' in (
        overview_src
    )
    assert "disabled=analysis_running" in overview_src

    # Command blocks remain individually addressable for UI testing.
    for index in range(1, 5):
        assert re.search(rf"_command_block\(\s+{index},", local_run_src)
    assert 'with st.container(key=f"local_run_command_{number}")' in (
        local_run_src
    )


def test_upload_pages_link_to_local_run_guide():
    """GL-426: upload areas use a button instead of a large inline guide."""
    src = _read("dashboard/pages/overview.py")

    assert "def _show_local_run_button(tokens: dict, key: str)" in src
    assert "How to Run Locally" in src
    assert 'st.session_state["page"] = "local_run"' in src
    assert '_show_local_run_button(tokens, "landing_local_run_btn")' in src
    assert (
        '_show_local_run_button(tokens, "dashboard_upload_local_run_btn")'
        in src
    )


def test_upload_layout_no_longer_renders_inline_local_run_card():
    """GL-426: upload cards stay focused on upload and analysis."""
    src = _read("dashboard/pages/overview.py")

    assert 'with st.container(key="dashboard_upload_pair")' in src
    assert 'with st.container(key="landing_upload_pair")' in src
    assert ".st-key-dashboard_upload_pair" in src
    assert ".st-key-landing_upload_pair" in src
    assert "max-width: 1160px !important;" in src
    assert "max-width: 560px !important;" in src
    assert "min-height: 315px !important;" in src
    assert 'st.columns([1, 2, 1], gap="large")' in src
    assert "_show_how_to_run_locally" not in src
    assert '_show_how_to_run_locally(tokens, "landing_local_run")' not in src
    assert (
        '_show_how_to_run_locally(tokens, "dashboard_local_run")' not in src
    )


def test_what_if_level_pill_centered_and_bar_left_filled():
    src = _read("dashboard/pages/what_if.py")

    assert ".wi-cell-change {" in src
    assert "align-items: center;" in src
    assert "justify-content: center;" in src
    assert ".wi-cell-risk {" in src
    assert ".wi-level-stack {" in src
    assert '<div class="wi-level-stack">' in src
    assert "min-width: 78px;" in src
    assert "width: 78px;" in src
    assert "display: flex;" in src
    assert ".wi-cell-risk {{" in src
    assert "align-items: center;" in src
    assert ".wi-bar-track {{ width: 78px; }}" in src
    assert "justify-content: flex-start;" in src
    assert ".wi-col-hdr.right {" in src
    assert "text-align: center;" in src


def test_what_if_step_arrows_are_visible():
    src = _read("dashboard/pages/what_if.py")

    assert ".wi-step:not(:last-child)::after" in src
    assert 'color: {T["text_secondary"]};' in src
    assert "font-size: 16px;" in src
    assert "font-weight: 700;" in src


def test_what_if_layout_has_refined_sections_and_responsive_grid():
    src = _read("dashboard/pages/what_if.py")

    assert ".wi-section-row {" in src
    assert ".wi-section-meta {" in src
    assert '<div class="wi-section-meta">5 presets</div>' in src
    assert "height: 132px;" in src
    assert "min-height: 36px !important;" in src
    assert "position: sticky;" in src
    assert "top: 18px;" in src
    assert "st.columns([1.05, 1.7], gap=\"large\")" in src
    assert "minmax(140px, 1fr)" in src
    assert "minmax(112px, 128px)" in src
    assert ".wi-col-headers {{ display: none; }}" in src
    assert ".wi-cell-change {{" in src
    assert "align-items: flex-start;" in src


def test_what_if_back_button_uses_light_blue_then_deep_blue_hover():
    src = _read("dashboard/pages/what_if.py")

    assert "← Back to Overview" in src
    assert ".st-key-what_if_back_btn button {" in src
    assert 'background: {T["accent_subtle"]} !important;' in src
    assert 'border: 1.5px solid {T["accent"]} !important;' in src
    assert 'color: {T["accent"]} !important;' in src
    assert ".st-key-what_if_back_btn button * {" in src
    assert ".st-key-what_if_back_btn button:hover" in src
    assert ".st-key-what_if_back_btn button:hover *" in src
    assert 'background: {T["accent_hover"]} !important;' in src
    assert 'border-color: {T["accent_hover"]} !important;' in src
    assert 'color: {T["accent_contrast"]} !important;' in src
    assert ".st-key-what_if_back_btn button:active" in src


def test_detail_back_button_uses_light_blue_then_deep_blue_hover():
    src = _read("dashboard/pages/detail.py")

    assert 'key="detail_back_btn"' in src
    assert 'key="detail_missing_back_btn"' in src
    assert ".st-key-detail_back_btn button" in src
    assert 'background: {tokens["accent_subtle"]} !important;' in src
    assert 'border: 1.5px solid {tokens["accent"]} !important;' in src
    assert '.st-key-detail_back_btn button:hover' in src
    assert 'background: {tokens["accent_hover"]} !important;' in src
    assert 'border-color: {tokens["accent_hover"]} !important;' in src
    assert 'color: {tokens["accent_contrast"]} !important;' in src
