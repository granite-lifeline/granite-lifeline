"""
Retrieval Method Comparison Script for GL-156.

This script compares two retrieval methods for the fault_knowledge
ChromaDB collection:
- Method A: Metadata-filtered retrieval (ADR 303)
- Method B: Semantic vector search

Part of GL-118 (RAG vs Baseline Evaluation) in the Granite Lifeline
MSc project at the University of Bristol, sponsored by IBM.
"""

import sys
import time
from pathlib import Path

import chromadb

# Add PROJECT_ROOT to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))


# Anomaly types and their symptom descriptions
ANOMALY_SYMPTOMS = {
    "cooling_degradation": (
        "The engine temperature gauge is rising higher than normal "
        "and the coolant is getting too hot"
    ),
    "intake_air_temperature_sensor_or_heat_soak_fault": (
        "The engine is struggling to start in cold weather and fuel "
        "consumption has increased"
    ),
    "air_intake_maf_anomaly": (
        "The engine feels sluggish and the airflow sensor reading "
        "seems inconsistent with engine load"
    ),
    "map_load_signal_plausibility_fault": (
        "The engine is jerking under partial load and the manifold "
        "pressure reading seems wrong"
    ),
    "electronic_throttle_tracking_fault": (
        "The accelerator pedal response is delayed and the engine "
        "sometimes goes into limp mode"
    ),
    "accelerator_pedal_sensor": (
        "The two accelerator pedal sensors are showing different "
        "readings when the pedal is pressed"
    ),
    "idle_speed_control_or_surge_degradation": (
        "The engine RPM is fluctuating and surging at idle with "
        "the car stationary"
    ),
}

# Number of trials per anomaly type per method
NUM_TRIALS = 3


def test_metadata_retrieval(collection, anomaly_type):
    """
    Test Method A: Metadata-filtered retrieval.

    Args:
        collection: ChromaDB collection instance
        anomaly_type: The anomaly type to retrieve

    Returns:
        tuple: (is_correct, retrieval_time_ms)
    """
    start_time = time.time()

    results = collection.get(
        where={
            "$and": [
                {"anomaly_type": {"$eq": anomaly_type}},
                {"section": {"$eq": "description_causes"}}
            ]
        }
    )

    end_time = time.time()
    retrieval_time_ms = (end_time - start_time) * 1000

    # Check if we got exactly one result with correct anomaly_type
    is_correct = (
        len(results["ids"]) == 1 and
        results["metadatas"][0]["anomaly_type"] == anomaly_type
    )

    return is_correct, retrieval_time_ms


def test_semantic_retrieval(collection, anomaly_type, symptom_description):
    """
    Test Method B: Semantic vector search.

    Args:
        collection: ChromaDB collection instance
        anomaly_type: The expected anomaly type
        symptom_description: The symptom description to query

    Returns:
        tuple: (is_correct, retrieval_time_ms)
    """
    start_time = time.time()

    results = collection.query(
        query_texts=[symptom_description],
        n_results=1
    )

    end_time = time.time()
    retrieval_time_ms = (end_time - start_time) * 1000

    # Check if the returned document's anomaly_type matches expected
    is_correct = (
        len(results["ids"][0]) > 0 and
        results["metadatas"][0][0]["anomaly_type"] == anomaly_type
    )

    return is_correct, retrieval_time_ms


def run_comparison():
    """Run the retrieval method comparison."""
    # Initialize ChromaDB client
    chroma_db_path = PROJECT_ROOT / "report_layer" / "rag" / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_db_path))
    collection = client.get_collection(name="fault_knowledge")

    print("=" * 79)
    print("Retrieval Method Comparison: Metadata Filter vs Semantic Search")
    print("=" * 79)
    print(f"\nChromaDB Path: {chroma_db_path}")
    print(f"Collection: fault_knowledge")
    print(f"Number of trials per method: {NUM_TRIALS}")
    print(f"Number of anomaly types: {len(ANOMALY_SYMPTOMS)}")
    print("\n" + "=" * 79)

    results = {}

    for anomaly_type, symptom_description in ANOMALY_SYMPTOMS.items():
        print(f"\nTesting: {anomaly_type}")

        # Test Method A (Metadata-filtered retrieval)
        method_a_times = []
        method_a_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_metadata_retrieval(
                collection, anomaly_type
            )
            method_a_times.append(time_ms)
            if not is_correct:
                method_a_correct = False
            print(f"  Method A Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_a_avg_time = sum(method_a_times) / len(method_a_times)

        # Test Method B (Semantic vector search)
        method_b_times = []
        method_b_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_semantic_retrieval(
                collection, anomaly_type, symptom_description
            )
            method_b_times.append(time_ms)
            if not is_correct:
                method_b_correct = False
            print(f"  Method B Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_b_avg_time = sum(method_b_times) / len(method_b_times)

        results[anomaly_type] = {
            "method_a_correct": method_a_correct,
            "method_a_time": method_a_avg_time,
            "method_b_correct": method_b_correct,
            "method_b_time": method_b_avg_time,
        }

    # Print summary table
    print("\n" + "=" * 79)
    print("RESULTS SUMMARY")
    print("=" * 79)
    print(f"\n{'Anomaly Type':<50} {'A Correct':<12} {'A Time':<12} "
          f"{'B Correct':<12} {'B Time':<12}")
    print("-" * 79)

    for anomaly_type, result in results.items():
        print(f"{anomaly_type:<50} "
              f"{'✓' if result['method_a_correct'] else '✗':<12} "
              f"{result['method_a_time']:.2f} ms{'':<4} "
              f"{'✓' if result['method_b_correct'] else '✗':<12} "
              f"{result['method_b_time']:.2f} ms")

    print("=" * 79)

    # Write results to markdown file
    write_markdown_report(results)


def write_markdown_report(results):
    """
    Write the comparison results to a markdown file.

    Args:
        results: Dictionary of results by anomaly type
    """
    output_path = (
        PROJECT_ROOT / "report_layer" / "evaluation" /
        "v4-meta-semantic-comparison" / "retrieval_comparison.md"
    )

    # Calculate summary statistics
    method_a_correct_count = sum(
        1 for r in results.values() if r["method_a_correct"]
    )
    method_b_correct_count = sum(
        1 for r in results.values() if r["method_b_correct"]
    )
    method_a_avg_time = sum(
        r["method_a_time"] for r in results.values()
    ) / len(results)
    method_b_avg_time = sum(
        r["method_b_time"] for r in results.values()
    ) / len(results)

    with open(output_path, "w") as f:
        f.write("# Retrieval Method Comparison: "
                "Metadata Filter vs Semantic Search\n\n")

        f.write("## Test Setup\n\n")
        f.write("This evaluation compares two retrieval methods for the "
                "`fault_knowledge` ChromaDB collection:\n\n")
        f.write("- **Method A (Metadata-filtered retrieval)**: Uses "
                "`collection.get()` with exact `anomaly_type` metadata "
                "matching and `section='description_causes'` filter "
                "(current approach per ADR 303)\n")
        f.write("- **Method B (Semantic vector search)**: Uses "
                "`collection.query()` with symptom descriptions to find "
                "semantically similar documents, then validates if the "
                "returned document's `anomaly_type` metadata matches the "
                "expected type\n\n")
        f.write(f"**Collection**: `fault_knowledge` (28 documents: "
                f"7 anomaly types × 4 sections)\n\n")
        f.write(f"**Trials per method**: {NUM_TRIALS}\n\n")
        f.write(f"**Anomaly types tested**: {len(ANOMALY_SYMPTOMS)}\n\n")

        f.write("## Results\n\n")
        f.write("| Anomaly Type | Method A Correct | Method A Time (ms) | "
                "Method B Correct | Method B Time (ms) |\n")
        f.write("|--------------|------------------|--------------------"
                "|------------------|--------------------|\n")

        for anomaly_type, result in results.items():
            f.write(f"| {anomaly_type} | "
                    f"{'✓' if result['method_a_correct'] else '✗'} | "
                    f"{result['method_a_time']:.2f} | "
                    f"{'✓' if result['method_b_correct'] else '✗'} | "
                    f"{result['method_b_time']:.2f} |\n")

        f.write("\n## Key Findings\n\n")
        f.write("### Accuracy\n\n")
        f.write(f"- **Method A**: {method_a_correct_count}/"
                f"{len(results)} correct "
                f"({method_a_correct_count / len(results) * 100:.1f}%)\n")
        f.write(f"- **Method B**: {method_b_correct_count}/"
                f"{len(results)} correct "
                f"({method_b_correct_count / len(results) * 100:.1f}%)\n\n")

        f.write("### Speed\n\n")
        f.write(f"- **Method A**: {method_a_avg_time:.2f} ms average\n")
        f.write(f"- **Method B**: {method_b_avg_time:.2f} ms average\n")
        f.write(f"- **Speed difference**: Method B is "
                f"{method_b_avg_time / method_a_avg_time:.2f}x "
                f"{'slower' if method_b_avg_time > method_a_avg_time else 'faster'} "  # noqa: E501
                f"than Method A\n\n")

        f.write("## Conclusion\n\n")

        if method_a_correct_count == len(results):
            f.write("**Recommendation**: Continue using **Method A "
                    "(Metadata-filtered retrieval)** as specified in "
                    "ADR 303.\n\n")
            f.write("**Rationale**:\n\n")
            f.write("1. **Perfect accuracy**: Method A correctly retrieves "
                    "the target document in 100% of cases\n")
            f.write(f"2. **Superior performance**: Method A is "
                    f"{method_b_avg_time / method_a_avg_time:.2f}x faster "
                    f"than semantic search\n")
            f.write("3. **Deterministic behavior**: Metadata filtering "
                    "provides predictable, exact matching without "
                    "dependency on embedding model semantics\n")
            f.write("4. **Alignment with ADR 303**: The current "
                    "architecture decision is validated by these results\n")
        else:
            f.write("**Recommendation**: Further investigation required.\n\n")
            f.write("Method A did not achieve 100% accuracy. Review the "
                    "collection structure and metadata consistency.\n")

    print(f"\nMarkdown report written to: {output_path}")


if __name__ == "__main__":
    run_comparison()
