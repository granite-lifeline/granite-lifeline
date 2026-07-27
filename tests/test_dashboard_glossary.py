"""Tests for dashboard signal glossary and tooltip display."""

from pathlib import Path

from dashboard.glossary import (
    DEFAULT_SIGNAL_TOOLTIP,
    get_signal_display_name,
    get_signal_tooltip,
)


def test_glossary_has_plain_name_and_tooltip_for_common_signal():
    """Test common signal can show a plain name and useful tooltip."""
    assert get_signal_display_name("maf") == "Mass Airflow"
    assert "air" in get_signal_tooltip("maf").lower()
    assert "engine" in get_signal_tooltip("maf").lower()


def test_glossary_fallback_for_unknown_signal():
    """Test unknown signal keeps raw name and uses fallback tooltip."""
    assert get_signal_display_name("my_test_signal") == "my_test_signal"
    assert get_signal_tooltip("my_test_signal") == DEFAULT_SIGNAL_TOOLTIP


def test_detail_page_uses_custom_signal_tooltip():
    """Test Detail page renders the larger custom tooltip block."""
    src = Path("dashboard/pages/detail.py").read_text(encoding="utf-8")

    assert "signal-name-tip-wrap" in src
    assert "signal-name-tip-box" in src
    assert "signal-tip-icon" in src
    assert "get_signal_tooltip(sig[\"feature\"])" in src
