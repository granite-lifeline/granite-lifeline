"""Tests for dashboard anomaly display names."""

from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES
from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES


def test_dashboard_display_names_cover_current_anomaly_types():
    """Test dashboard has labels for all current anomaly types."""
    for anomaly_type in GROUND_KNOWLEDGE_ANOMALY_TYPES:
        assert anomaly_type in COMPONENT_DISPLAY_NAMES
        assert COMPONENT_DISPLAY_NAMES[anomaly_type]


def test_dashboard_display_names_remove_throttle_type():
    """Test removed throttle anomaly type is not shown by Dashboard."""
    assert "electronic_throttle_tracking_fault" not in COMPONENT_DISPLAY_NAMES
    assert "Electronic Throttle" not in COMPONENT_DISPLAY_NAMES.values()


def test_dashboard_keeps_legacy_cooling_alias():
    """Test old cooling display alias still works for older mock data."""
    assert COMPONENT_DISPLAY_NAMES["cooling_system_stress"] == "Cooling System"
