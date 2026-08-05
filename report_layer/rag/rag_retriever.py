"""
RAG Retriever for Fault Knowledge Base.

This module provides metadata-filtered retrieval functions to query the
ChromaDB fault knowledge collection for diagnostic report generation.

Task: GL-112 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import chromadb


# ChromaDB configuration
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "fault_knowledge"

logger = logging.getLogger(__name__)

FALLBACK_DESCRIPTION = (
    "No specific fault knowledge found for this anomaly type."
)
FALLBACK_ACTIONS = "No specific action guidance found for this risk level."

_client: Optional[chromadb.PersistentClient] = None
_collection = None
_collection_unavailable = False


def _get_collection():
    """
    Return the ChromaDB fault knowledge collection when available.

    The collection is created by running the RAG indexer locally. CI and fresh
    clones may not have that generated database yet, so collection lookup must
    happen lazily and degrade to fallback retrieval text instead of failing at
    import time.
    """
    global _client, _collection, _collection_unavailable

    if _collection is not None:
        return _collection
    if _collection_unavailable:
        return None

    try:
        _client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        _collection = _client.get_collection(name=COLLECTION_NAME)
        return _collection
    except Exception as exc:
        _collection_unavailable = True
        logger.warning(
            "ChromaDB collection %r is unavailable at %s: %s",
            COLLECTION_NAME,
            CHROMA_DB_PATH,
            exc,
        )
        return None


def retrieve_description_causes(anomaly_type: str) -> str:
    """
    Retrieve description and causes for a specific anomaly type.

    Args:
        anomaly_type: The anomaly type identifier (e.g.,
            "cooling_degradation").

    Returns:
        The description and causes document content, or a fallback
        message if not found.
    """
    try:
        collection = _get_collection()
        if collection is None:
            return FALLBACK_DESCRIPTION

        result = collection.get(
            where={
                "$and": [
                    {"anomaly_type": {"$eq": anomaly_type}},
                    {"section": {"$eq": "description_causes"}},
                ]
            }
        )

        if result and result["documents"] and len(result["documents"]) > 0:
            return result["documents"][0]

        return FALLBACK_DESCRIPTION

    except Exception:
        return FALLBACK_DESCRIPTION


def retrieve_actions(anomaly_type: str, risk_level: str) -> str:
    """
    Retrieve recommended actions for a specific anomaly type and risk
    level.

    Args:
        anomaly_type: The anomaly type identifier (e.g.,
            "cooling_degradation").
        risk_level: The risk level, in any case ("Low", "low",
            "MEDIUM", etc. are all accepted). Stored metadata uses
            lowercase, so this is normalized internally rather than
            relying on every caller to lowercase it first — a wrong-case
            value used to fail silently and return FALLBACK_ACTIONS with
            no error or warning.

    Returns:
        The actions document content for the specified risk level, or a
        fallback message if not found.
    """
    try:
        collection = _get_collection()
        if collection is None:
            return FALLBACK_ACTIONS

        normalized_risk_level = (
            risk_level.lower() if risk_level else risk_level
        )
        result = collection.get(
            where={
                "$and": [
                    {"anomaly_type": {"$eq": anomaly_type}},
                    {"section": {"$eq": "actions"}},
                    {"risk_level": {"$eq": normalized_risk_level}},
                ]
            }
        )

        if result and result["documents"] and len(result["documents"]) > 0:
            return result["documents"][0]

        return FALLBACK_ACTIONS

    except Exception:
        return FALLBACK_ACTIONS


def retrieve_all(anomaly_type: str, risk_level: str) -> Dict[str, str]:
    """
    Retrieve both description/causes and actions for a specific anomaly
    type and risk level.

    Args:
        anomaly_type: The anomaly type identifier (e.g.,
            "cooling_degradation").
        risk_level: The risk level ("low", "medium", or "high").

    Returns:
        A dictionary with keys "description_causes" and "actions"
        containing the retrieved content or fallback messages.
    """
    return {
        "description_causes": retrieve_description_causes(anomaly_type),
        "actions": retrieve_actions(anomaly_type, risk_level),
    }
