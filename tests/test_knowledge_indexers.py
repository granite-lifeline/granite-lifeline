"""Tests for RAG knowledge indexer anomaly type lists."""

from report_layer.rag import knowledge_indexer, symptom_knowledge_indexer
from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES


def test_fault_knowledge_indexer_uses_six_current_types():
    """Test fault knowledge indexer follows the shared six-type list."""
    expected_types = list(GROUND_KNOWLEDGE_ANOMALY_TYPES)

    assert knowledge_indexer.EXPECTED_ANOMALY_TYPES == expected_types
    assert len(knowledge_indexer.EXPECTED_ANOMALY_TYPES) == 6
    assert "electronic_throttle_tracking_fault" not in (
        knowledge_indexer.EXPECTED_ANOMALY_TYPES
    )


def test_symptom_knowledge_indexer_uses_six_current_types():
    """Test symptom knowledge indexer follows the shared six-type list."""
    expected_types = list(GROUND_KNOWLEDGE_ANOMALY_TYPES)

    assert symptom_knowledge_indexer.EXPECTED_ANOMALY_TYPES == expected_types
    assert len(symptom_knowledge_indexer.EXPECTED_ANOMALY_TYPES) == 6
    assert "electronic_throttle_tracking_fault" not in (
        symptom_knowledge_indexer.EXPECTED_ANOMALY_TYPES
    )


def test_fault_knowledge_indexer_expected_document_count():
    """Test fault knowledge indexer now expects 24 documents."""
    assert len(knowledge_indexer.EXPECTED_ANOMALY_TYPES) * 4 == 24


def test_symptom_knowledge_indexer_expected_document_count():
    """Test symptom knowledge indexer now expects 6 documents."""
    assert len(symptom_knowledge_indexer.EXPECTED_ANOMALY_TYPES) == 6


def test_grounded_knowledge_yaml_has_expected_types():
    """Test source YAML contains every current indexer anomaly type."""
    data = knowledge_indexer.load_knowledge_yaml()
    proxy_failures = data["proxy_failures"]

    knowledge_indexer.validate_anomaly_types(proxy_failures)
    assert "intake_air_temperature_sensor_or_heat_soak_fault" in (
        proxy_failures
    )
