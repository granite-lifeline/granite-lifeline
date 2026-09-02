"""
Unit tests for RAG retriever metadata-filtered retrieval functions.

The retriever must be importable in fresh CI environments where the local
ChromaDB knowledge collection has not been generated yet. These tests use a
fake collection so they validate retrieval behavior without relying on
generated local artifacts.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from report_layer.rag import rag_retriever  # noqa: E402
from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES  # noqa: E402


ANOMALY_TYPES = GROUND_KNOWLEDGE_ANOMALY_TYPES
RISK_LEVELS = ["low", "medium", "high"]
FALLBACK_DESCRIPTION = (
    "No specific fault knowledge found for this anomaly type."
)
FALLBACK_ACTIONS = "No specific action guidance found for this risk level."


class FakeCollection:
    """Minimal Chroma collection fake for metadata-filtered get calls."""

    def __init__(self):
        self.calls = []

    def get(self, where):
        self.calls.append(where)
        filters = {
            item_key: item_value["$eq"]
            for item in where["$and"]
            for item_key, item_value in item.items()
        }

        anomaly_type = filters.get("anomaly_type")
        section = filters.get("section")
        risk_level = filters.get("risk_level")

        if anomaly_type not in ANOMALY_TYPES:
            return {"documents": []}
        if section == "description_causes":
            return {
                "documents": [
                    f"Description and causes for {anomaly_type}."
                ]
            }
        if section == "actions" and risk_level in RISK_LEVELS:
            return {
                "documents": [
                    f"{risk_level.title()} risk actions for {anomaly_type}."
                ]
            }
        return {"documents": []}


@pytest.fixture
def fake_collection(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(rag_retriever, "_get_collection", lambda: collection)
    return collection


@pytest.mark.parametrize("anomaly_type", ANOMALY_TYPES)
def test_retrieve_description_causes_valid_types(
    anomaly_type, fake_collection
):
    result = rag_retriever.retrieve_description_causes(anomaly_type)

    assert result == f"Description and causes for {anomaly_type}."
    assert fake_collection.calls[-1] == {
        "$and": [
            {"anomaly_type": {"$eq": anomaly_type}},
            {"section": {"$eq": "description_causes"}},
        ]
    }


@pytest.mark.parametrize(
    "anomaly_type,risk_level",
    [(at, rl) for at in ANOMALY_TYPES for rl in RISK_LEVELS],
)
def test_retrieve_actions_valid_combinations(
    anomaly_type, risk_level, fake_collection
):
    result = rag_retriever.retrieve_actions(anomaly_type, risk_level)

    assert result == f"{risk_level.title()} risk actions for {anomaly_type}."
    assert fake_collection.calls[-1] == {
        "$and": [
            {"anomaly_type": {"$eq": anomaly_type}},
            {"section": {"$eq": "actions"}},
            {"risk_level": {"$eq": risk_level}},
        ]
    }


def test_retrieve_description_causes_invalid_type(fake_collection):
    result = rag_retriever.retrieve_description_causes("nonexistent_type")

    assert result == FALLBACK_DESCRIPTION


def test_retrieve_actions_invalid_anomaly_type(fake_collection):
    result = rag_retriever.retrieve_actions("nonexistent_type", "medium")

    assert result == FALLBACK_ACTIONS


def test_retrieve_actions_invalid_risk_level(fake_collection):
    result = rag_retriever.retrieve_actions("cooling_degradation", "critical")

    assert result == FALLBACK_ACTIONS


def test_retrieve_all_valid_combination(fake_collection):
    result = rag_retriever.retrieve_all("cooling_degradation", "medium")

    assert result == {
        "description_causes": (
            "Description and causes for cooling_degradation."
        ),
        "actions": "Medium risk actions for cooling_degradation.",
    }


def test_retrieve_all_invalid_anomaly_type(fake_collection):
    result = rag_retriever.retrieve_all("nonexistent_type", "medium")

    assert result == {
        "description_causes": FALLBACK_DESCRIPTION,
        "actions": FALLBACK_ACTIONS,
    }


def test_retrieve_all_falls_back_when_collection_is_missing(monkeypatch):
    monkeypatch.setattr(rag_retriever, "_get_collection", lambda: None)

    result = rag_retriever.retrieve_all("cooling_degradation", "medium")

    assert result == {
        "description_causes": FALLBACK_DESCRIPTION,
        "actions": FALLBACK_ACTIONS,
    }


def test_collection_lookup_recovers_after_retry_interval(monkeypatch):
    collection = FakeCollection()

    class FakeClient:
        def get_collection(self, name):
            assert name == rag_retriever.COLLECTION_NAME
            return collection

    clients = [RuntimeError("index not ready"), FakeClient()]

    def persistent_client(path):
        assert path == str(rag_retriever.CHROMA_DB_PATH)
        client = clients.pop(0)
        if isinstance(client, Exception):
            raise client
        return client

    clock = iter([10.0, 10.0, 12.0, 16.0])
    monkeypatch.setattr(
        rag_retriever.chromadb,
        "PersistentClient",
        persistent_client,
    )
    monkeypatch.setattr(
        rag_retriever.time,
        "monotonic",
        lambda: next(clock),
    )
    monkeypatch.setattr(rag_retriever, "_client", None)
    monkeypatch.setattr(rag_retriever, "_collection", None)
    monkeypatch.setattr(rag_retriever, "_collection_retry_after", 0.0)

    assert rag_retriever._get_collection() is None
    assert rag_retriever._get_collection() is None
    assert rag_retriever._get_collection() is collection
