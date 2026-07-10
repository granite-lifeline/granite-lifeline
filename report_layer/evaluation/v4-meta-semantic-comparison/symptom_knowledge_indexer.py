"""
Symptom Knowledge Indexer for GL-156.

This module creates a ChromaDB collection with document-level chunking
strategy. Each of the 7 anomaly types is stored as a single merged
document containing description, causes, and all actions.

Part of GL-118 (RAG vs Baseline Evaluation) in the Granite Lifeline
MSc project at the University of Bristol, sponsored by IBM.
"""

from pathlib import Path
from typing import Any, Dict, List

import chromadb
import yaml


# Seven canonical anomaly types from grounded_knowledge.yaml
EXPECTED_ANOMALY_TYPES = [
    "cooling_degradation",
    "intake_air_temperature_sensor_or_heat_soak_fault",
    "air_intake_maf_anomaly",
    "map_load_signal_plausibility_fault",
    "electronic_throttle_tracking_fault",
    "accelerator_pedal_sensor",
    "idle_speed_control_or_surge_degradation",
]

# ChromaDB configuration
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHROMA_DB_PATH = PROJECT_ROOT / "report_layer" / "rag" / "chroma_db"
COLLECTION_NAME = "symptom_knowledge"

# Knowledge source path
KNOWLEDGE_SOURCE = (
    PROJECT_ROOT / "shared" / "ground_knowledge" /
    "grounded_knowledge.yaml"
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


def create_merged_document(
    anomaly_type: str, anomaly_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a single merged document for an anomaly type.

    Merges description, causes, and all actions (low, medium, high)
    into a single document string.

    Args:
        anomaly_type: The anomaly type identifier.
        anomaly_data: The anomaly data from the YAML.

    Returns:
        Document dict with id, content, and metadata.
    """
    report_layer = anomaly_data["report_layer"]
    description = report_layer["description"]
    causes = report_layer["causes"]
    actions = report_layer["actions"]

    # Merge all content in specified order:
    # 1. Description
    # 2. All causes (joined by newline)
    # 3. All actions from low, medium, high (joined by newline)
    causes_text = "\n".join(causes)
    actions_low = extract_action_strings(actions["low"])
    actions_medium = extract_action_strings(actions["medium"])
    actions_high = extract_action_strings(actions["high"])

    merged_content = (
        f"{description}\n"
        f"{causes_text}\n"
        f"{actions_low}\n"
        f"{actions_medium}\n"
        f"{actions_high}"
    )

    return {
        "id": anomaly_type,
        "content": merged_content,
        "metadata": {"anomaly_type": anomaly_type},
    }


def index_symptom_knowledge() -> int:
    """
    Index the symptom knowledge base into ChromaDB.

    Creates a collection with 7 documents (one per anomaly type),
    where each document contains merged description, causes, and
    actions.

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
            "Unexpected YAML structure: expected dict with "
            "'proxy_failures'"
        )

    # Validate all anomaly types are present
    validate_anomaly_types(proxy_failures)

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Check if index is already up to date
    existing_count = collection.count()
    expected_count = len(EXPECTED_ANOMALY_TYPES)  # 7 documents

    if existing_count == expected_count:
        # Verify all expected document IDs exist
        try:
            collection.get(ids=EXPECTED_ANOMALY_TYPES)
            print(
                f"✓ Index is already up to date "
                f"({expected_count} documents present)"
            )
            return existing_count
        except Exception:
            # Some documents are missing, proceed with re-indexing
            pass

    # Create merged documents for all anomaly types
    all_documents = []
    for anomaly_type in EXPECTED_ANOMALY_TYPES:
        anomaly_data = proxy_failures[anomaly_type]
        document = create_merged_document(anomaly_type, anomaly_data)
        all_documents.append(document)
        print(f"✓ Indexed {anomaly_type} (1 merged document)")

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
    """Main entry point for the symptom knowledge indexer."""
    print("=" * 79)
    print("Granite Lifeline - Symptom Knowledge Indexer")
    print("Task: GL-156 (Document-Level Semantic Search Evaluation)")
    print("=" * 79)
    print()

    try:
        print(f"Knowledge source: {KNOWLEDGE_SOURCE}")
        print(f"ChromaDB path: {CHROMA_DB_PATH}")
        print(f"Collection name: {COLLECTION_NAME}")
        print()

        total_docs = index_symptom_knowledge()

        print()
        print("=" * 79)
        print(f"✓ Indexing complete: {total_docs} documents stored")
        print(f"  - {len(EXPECTED_ANOMALY_TYPES)} anomaly types")
        print("  - 1 merged document per type (description + causes + "
              "actions)")
        print("=" * 79)

    except Exception as e:
        print()
        print("=" * 79)
        print(f"✗ Indexing failed: {e}")
        print("=" * 79)
        raise


if __name__ == "__main__":
    main()
