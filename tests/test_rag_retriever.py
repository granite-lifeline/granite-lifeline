"""
Unit tests for RAG retriever metadata-filtered retrieval functions.

This module tests the ChromaDB retrieval functions in
report_layer/rag/rag_retriever.py to ensure correct metadata filtering,
fallback handling, and exception safety.

Task: GL-113 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from report_layer.rag.rag_retriever import (  # noqa: E402
    retrieve_actions,
    retrieve_all,
    retrieve_description_causes,
)
from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES  # noqa: E402

# Six current anomaly types
ANOMALY_TYPES = GROUND_KNOWLEDGE_ANOMALY_TYPES

# Three risk levels
RISK_LEVELS = ["low", "medium", "high"]

# Fallback messages
FALLBACK_DESCRIPTION = (
    "No specific fault knowledge found for this anomaly type."
)
FALLBACK_ACTIONS = "No specific action guidance found for this risk level."


@pytest.mark.parametrize("anomaly_type", ANOMALY_TYPES)
def test_retrieve_description_causes_valid_types(anomaly_type):
    """
    Test retrieve_description_causes returns valid content for all
    anomaly types.

    Verifies that the function returns non-empty content that is not
    the fallback message and contains relevant technical terms.
    """
    result = retrieve_description_causes(anomaly_type)

    # Assert non-empty
    assert result, f"Result is empty for {anomaly_type}"

    # Assert not fallback message
    assert result != FALLBACK_DESCRIPTION, (
        f"Returned fallback for valid type {anomaly_type}"
    )

    # Assert contains relevant content (case-insensitive)
    result_lower = result.lower()
    relevant_terms = [
        "description",
        "cause",
        "sensor",
        "temperature",
        "pressure",
        "coolant",
        "intake",
        "maf",
        "map",
        "throttle",
        "pedal",
        "idle",
        "rpm",
        "engine",
    ]

    has_relevant_term = any(term in result_lower for term in relevant_terms)
    assert has_relevant_term, (
        f"Result for {anomaly_type} does not contain relevant terms"
    )


@pytest.mark.parametrize(
    "anomaly_type,risk_level",
    [(at, rl) for at in ANOMALY_TYPES for rl in RISK_LEVELS],
)
def test_retrieve_actions_valid_combinations(anomaly_type, risk_level):
    """
    Test retrieve_actions returns valid content for all anomaly type
    and risk level combinations.

    Tests all 18 combinations (6 anomaly types × 3 risk levels) to
    ensure proper metadata filtering.
    """
    result = retrieve_actions(anomaly_type, risk_level)

    # Assert non-empty
    assert result, (
        f"Result is empty for {anomaly_type} at {risk_level} risk"
    )

    # Assert not fallback message
    assert result != FALLBACK_ACTIONS, (
        f"Returned fallback for valid combination: "
        f"{anomaly_type}, {risk_level}"
    )


def test_retrieve_description_causes_invalid_type():
    """
    Test retrieve_description_causes returns fallback for invalid
    anomaly type.

    Verifies graceful handling of non-existent anomaly types without
    raising exceptions.
    """
    result = retrieve_description_causes("nonexistent_type")

    # Assert returns exact fallback message
    assert result == FALLBACK_DESCRIPTION, (
        "Did not return fallback message for invalid anomaly type"
    )


def test_retrieve_actions_invalid_anomaly_type():
    """
    Test retrieve_actions returns fallback for invalid anomaly type.

    Verifies graceful handling when anomaly type does not exist in the
    knowledge base.
    """
    result = retrieve_actions("nonexistent_type", "medium")

    # Assert returns exact fallback message
    assert result == FALLBACK_ACTIONS, (
        "Did not return fallback message for invalid anomaly type"
    )


def test_retrieve_actions_invalid_risk_level():
    """
    Test retrieve_actions returns fallback for invalid risk level.

    Verifies graceful handling when risk level is not one of the
    expected values (low, medium, high).
    """
    result = retrieve_actions("cooling_degradation", "critical")

    # Assert returns exact fallback message
    assert result == FALLBACK_ACTIONS, (
        "Did not return fallback message for invalid risk level"
    )


def test_retrieve_all_valid_combination():
    """
    Test retrieve_all returns both description/causes and actions for
    valid input.

    Verifies that the function correctly combines results from both
    retrieval functions.
    """
    result = retrieve_all("cooling_degradation", "medium")

    # Assert dict has correct keys
    assert "description_causes" in result, "Missing description_causes key"
    assert "actions" in result, "Missing actions key"

    # Assert both values are non-empty
    assert result["description_causes"], "description_causes is empty"
    assert result["actions"], "actions is empty"

    # Assert neither value is a fallback message
    assert result["description_causes"] != FALLBACK_DESCRIPTION, (
        "description_causes is fallback message"
    )
    assert result["actions"] != FALLBACK_ACTIONS, (
        "actions is fallback message"
    )


def test_retrieve_all_invalid_anomaly_type():
    """
    Test retrieve_all returns fallback messages for invalid anomaly
    type.

    Verifies that both retrieval functions return their respective
    fallback messages when the anomaly type does not exist.
    """
    result = retrieve_all("nonexistent_type", "medium")

    # Assert dict has correct keys
    assert "description_causes" in result, "Missing description_causes key"
    assert "actions" in result, "Missing actions key"

    # Assert both values are fallback messages
    assert result["description_causes"] == FALLBACK_DESCRIPTION, (
        "description_causes is not fallback message for invalid type"
    )
    assert result["actions"] == FALLBACK_ACTIONS, (
        "actions is not fallback message for invalid type"
    )
