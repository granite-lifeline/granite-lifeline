"""
ChromaDB Knowledge Indexer for Fault Knowledge Base.

This module indexes the grounded knowledge YAML into ChromaDB for RAG-based
diagnostic report generation. Each anomaly type is stored as four separate
documents: description+causes, and three risk-level-specific action lists.

Task: GL-111 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

from pathlib import Path
from typing import Any, Dict, List

import chromadb
import yaml

from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES


# Five current anomaly types from docs/INTERFACE.md v1.1.
EXPECTED_ANOMALY_TYPES = list(GROUND_KNOWLEDGE_ANOMALY_TYPES)

# ChromaDB configuration
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "fault_knowledge"

# Knowledge source path
KNOWLEDGE_SOURCE = (
    Path(__file__).parent.parent.parent
    / "shared"
    / "ground_knowledge"
    / "grounded_knowledge.yaml"
)


def load_knowledge_yaml() -> Any:
    """
    Load and parse the grounded knowledge YAML file.

    Returns:
        Parsed YAML structure (list of dicts).

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    if not KNOWLEDGE_SOURCE.exists():
        raise FileNotFoundError(
            f"Knowledge source not found: {KNOWLEDGE_SOURCE}"
        )

    with open(KNOWLEDGE_SOURCE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def validate_anomaly_types(proxy_failures: Dict[str, Any]) -> None:
    """
    Validate that all expected anomaly types are present in the YAML.

    Args:
        proxy_failures: The proxy_failures section from the YAML.

    Raises:
        ValueError: If any expected anomaly type is missing.
    """
    present_types = set(proxy_failures.keys())
    expected_types = set(EXPECTED_ANOMALY_TYPES)
    missing_types = expected_types - present_types

    if missing_types:
        raise ValueError(
            f"Missing anomaly types in YAML: {sorted(missing_types)}"
        )


def extract_action_strings(actions: List[Dict[str, str]]) -> str:
    """
    Extract action strings from a list of action dictionaries.

    Args:
        actions: List of dicts with 'action' and 'source' keys.

    Returns:
        Newline-separated string of action texts.
    """
    return "\n".join(action["action"] for action in actions)


def create_documents_for_anomaly(
    anomaly_type: str, anomaly_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Create four ChromaDB documents for a single anomaly type.

    Args:
        anomaly_type: The anomaly type identifier.
        anomaly_data: The anomaly data from the YAML.

    Returns:
        List of four document dicts with id, content, and metadata.
    """
    report_layer = anomaly_data["report_layer"]
    description = report_layer["description"]
    causes = report_layer["causes"]
    actions = report_layer["actions"]

    # Document 1: description + causes
    causes_text = "\n".join(causes)
    desc_causes_content = f"{description}\n{causes_text}"

    # Documents 2-4: actions by risk level
    actions_low = extract_action_strings(actions["low"])
    actions_medium = extract_action_strings(actions["medium"])
    actions_high = extract_action_strings(actions["high"])

    documents = [
        {
            "id": f"{anomaly_type}_description_causes",
            "content": desc_causes_content,
            "metadata": {
                "anomaly_type": anomaly_type,
                "section": "description_causes",
            },
        },
        {
            "id": f"{anomaly_type}_actions_low",
            "content": actions_low,
            "metadata": {
                "anomaly_type": anomaly_type,
                "section": "actions",
                "risk_level": "low",
            },
        },
        {
            "id": f"{anomaly_type}_actions_medium",
            "content": actions_medium,
            "metadata": {
                "anomaly_type": anomaly_type,
                "section": "actions",
                "risk_level": "medium",
            },
        },
        {
            "id": f"{anomaly_type}_actions_high",
            "content": actions_high,
            "metadata": {
                "anomaly_type": anomaly_type,
                "section": "actions",
                "risk_level": "high",
            },
        },
    ]

    return documents


def index_knowledge_base() -> int:
    """
    Index the fault knowledge base into ChromaDB.

    Returns:
        Number of documents indexed.

    Raises:
        ValueError: If anomaly types are missing from the YAML.
    """
    # Load YAML
    data = load_knowledge_yaml()
    # YAML returns a dict with proxy_failures key
    if isinstance(data, dict) and "proxy_failures" in data:
        proxy_failures = data["proxy_failures"]
    else:
        raise ValueError(
            "Unexpected YAML structure: expected dict with 'proxy_failures'"
        )

    # Validate all anomaly types are present
    validate_anomaly_types(proxy_failures)

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Recreate the collection on every run so source-content changes are
    # reflected even when document IDs and counts stay the same.
    expected_count = len(EXPECTED_ANOMALY_TYPES) * 4
    client.delete_collection(name=COLLECTION_NAME)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Create documents for all anomaly types
    all_documents = []
    for anomaly_type in EXPECTED_ANOMALY_TYPES:
        anomaly_data = proxy_failures[anomaly_type]
        documents = create_documents_for_anomaly(anomaly_type, anomaly_data)
        all_documents.extend(documents)
        print(f"✓ Indexed {anomaly_type} (4 documents)")

    # Batch add to ChromaDB
    ids = [doc["id"] for doc in all_documents]
    contents = [doc["content"] for doc in all_documents]
    metadatas = [doc["metadata"] for doc in all_documents]

    collection.upsert(
        ids=ids,
        documents=contents,
        metadatas=metadatas,
    )

    # Validate indexing
    final_count = collection.count()
    if final_count != expected_count:
        raise ValueError(
            f"Indexing validation failed: expected {expected_count} "
            f"documents, found {final_count}"
        )

    return final_count


def main() -> None:
    """Main entry point for the knowledge indexer."""
    print("=" * 60)
    print("Granite Lifeline - Fault Knowledge Base Indexer")
    print("Task: GL-111 (RAG-Enhanced Diagnostic Report Generation)")
    print("=" * 60)
    print()

    try:
        print(f"Knowledge source: {KNOWLEDGE_SOURCE}")
        print(f"ChromaDB path: {CHROMA_DB_PATH}")
        print(f"Collection name: {COLLECTION_NAME}")
        print()

        total_docs = index_knowledge_base()

        print()
        print("=" * 60)
        print(f"✓ Indexing complete: {total_docs} documents stored")
        print(f"  - {len(EXPECTED_ANOMALY_TYPES)} anomaly types")
        print("  - 4 documents per type (desc+causes, 3 risk levels)")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Indexing failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
