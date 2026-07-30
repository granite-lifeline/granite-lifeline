"""Source checks for Dashboard UI consistency and Carbon theme work."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


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


def test_reusable_ui_helpers_cover_title_heading_and_empty_state():
    src = _read("dashboard/ui_components.py")

    assert "def page_title_html" in src
    assert "def section_heading_html" in src
    assert "def empty_state_html" in src


def test_main_dashboard_pages_use_shared_consistency_helpers():
    overview_src = _read("dashboard/pages/overview.py")
    detail_src = _read("dashboard/pages/detail.py")
    what_if_src = _read("dashboard/pages/what_if.py")

    assert "page_title_html(" in overview_src
    assert "page_title_html(" in detail_src
    assert "page_title_html(" in what_if_src

    assert "empty_state_html(" in overview_src
    assert "empty_state_html(" in detail_src
    assert "empty_state_html(" in what_if_src

    assert "section_heading_html(" in overview_src
    assert "section_heading_html(" in detail_src


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
    assert ".wi-cell-risk {{ align-items: center; }}" in src
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
