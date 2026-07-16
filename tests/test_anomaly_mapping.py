"""Tests for shared anomaly type mapping names."""

from shared.anomaly_mapping import (
    ANOMALY_TYPE_MAPPING_TABLE,
    GROUND_KNOWLEDGE_ANOMALY_TYPES,
)
from shared.interface_models import AnomalyType


def test_anomaly_mapping_has_six_current_types():
    """Test shared anomaly mapping follows the current interface enum."""
    expected_types = set(AnomalyType.__args__)

    assert set(GROUND_KNOWLEDGE_ANOMALY_TYPES) == expected_types
    assert len(GROUND_KNOWLEDGE_ANOMALY_TYPES) == 6
    assert "electronic_throttle_tracking_fault" not in (
        GROUND_KNOWLEDGE_ANOMALY_TYPES
    )


def test_mapping_table_has_same_six_types():
    """Test mapping table uses the same names on each side."""
    interface_names = {
        row["interface_name"] for row in ANOMALY_TYPE_MAPPING_TABLE
    }
    ground_names = {
        row["grounded_knowledge_key"] for row in ANOMALY_TYPE_MAPPING_TABLE
    }
    dashboard_names = {
        row["dashboard_key"] for row in ANOMALY_TYPE_MAPPING_TABLE
    }
    expected_types = set(AnomalyType.__args__)

    assert interface_names == expected_types
    assert ground_names == expected_types
    assert dashboard_names == expected_types
    assert len(ANOMALY_TYPE_MAPPING_TABLE) == 6
