"""
RAG Retriever for Fault Knowledge Base.

This module provides metadata-filtered retrieval functions to query the
ChromaDB fault knowledge collection for diagnostic report generation.

Task: GL-112 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

from pathlib import Path
from typing import Dict

import chromadb


# ChromaDB configuration
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "fault_knowledge"

# Initialize ChromaDB client at module level
_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
_collection = _client.get_collection(name=COLLECTION_NAME)


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
        result = _collection.get(
            where={
                "$and": [
                    {"anomaly_type": {"$eq": anomaly_type}},
                    {"section": {"$eq": "description_causes"}},
                ]
            }
        )

        if result and result["documents"] and len(result["documents"]) > 0:
            return result["documents"][0]

        return "No specific fault knowledge found for this anomaly type."

    except Exception:
        return "No specific fault knowledge found for this anomaly type."


def retrieve_actions(anomaly_type: str, risk_level: str) -> str:
    """
    Retrieve recommended actions for a specific anomaly type and risk
    level.

    Args:
        anomaly_type: The anomaly type identifier (e.g.,
            "cooling_degradation").
        risk_level: The risk level ("low", "medium", or "high").

    Returns:
        The actions document content for the specified risk level, or a
        fallback message if not found.
    """
    try:
        result = _collection.get(
            where={
                "$and": [
                    {"anomaly_type": {"$eq": anomaly_type}},
                    {"section": {"$eq": "actions"}},
                    {"risk_level": {"$eq": risk_level}},
                ]
            }
        )

        if result and result["documents"] and len(result["documents"]) > 0:
            return result["documents"][0]

        return "No specific action guidance found for this risk level."

    except Exception:
        return "No specific action guidance found for this risk level."


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
