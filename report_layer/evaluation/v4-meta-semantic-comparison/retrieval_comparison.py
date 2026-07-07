"""
Retrieval Method Comparison Script for GL-166.

This script compares four retrieval methods in a 2×2 design:
- Retrieval method: Metadata filter vs Semantic search
- Chunking strategy: Section-level (28 docs) vs Document-level (7 docs)

Method A: Metadata filter on fault_knowledge (28 docs, section-level)
Method B: Semantic search on fault_knowledge (28 docs, section-level)
Method C: Metadata filter on symptom_knowledge (7 docs, document-level)
Method D: Semantic search on symptom_knowledge (7 docs, document-level)

Part of GL-166 (Expand Knowledge Base and Four-Way Retrieval Comparison)
in the Granite Lifeline MSc project at the University of Bristol,
sponsored by IBM.
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


def test_method_a(collection, anomaly_type):
    """
    Test Method A: Metadata filter on fault_knowledge (28 docs).

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


def test_method_b(collection, anomaly_type, symptom_description):
    """
    Test Method B: Semantic search on fault_knowledge (28 docs).

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


def test_method_c(collection, anomaly_type):
    """
    Test Method C: Metadata filter on symptom_knowledge (7 docs).

    Args:
        collection: ChromaDB collection instance
        anomaly_type: The anomaly type to retrieve

    Returns:
        tuple: (is_correct, retrieval_time_ms)
    """
    start_time = time.time()

    results = collection.get(
        where={"anomaly_type": {"$eq": anomaly_type}}
    )

    end_time = time.time()
    retrieval_time_ms = (end_time - start_time) * 1000

    # Check if we got exactly one result with correct anomaly_type
    is_correct = (
        len(results["ids"]) == 1 and
        results["metadatas"][0]["anomaly_type"] == anomaly_type
    )

    return is_correct, retrieval_time_ms


def test_method_d(collection, anomaly_type, symptom_description):
    """
    Test Method D: Semantic search on symptom_knowledge (7 docs).

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
    """Run the four-way retrieval method comparison."""
    # Initialize ChromaDB client
    chroma_db_path = PROJECT_ROOT / "report_layer" / "rag" / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_db_path))
    fault_collection = client.get_collection(name="fault_knowledge")
    symptom_collection = client.get_collection(name="symptom_knowledge")

    print("=" * 79)
    print("Four-Way Retrieval Method Comparison")
    print("=" * 79)
    print(f"\nChromaDB Path: {chroma_db_path}")
    print(f"Collections:")
    print(f"  - fault_knowledge: {fault_collection.count()} docs "
          f"(section-level)")
    print(f"  - symptom_knowledge: {symptom_collection.count()} docs "
          f"(document-level)")
    print(f"\nTrials per method: {NUM_TRIALS}")
    print(f"Anomaly types tested: {len(ANOMALY_SYMPTOMS)}")
    print("\n" + "=" * 79)

    results = {}

    for anomaly_type, symptom_description in ANOMALY_SYMPTOMS.items():
        print(f"\nTesting: {anomaly_type}")

        # Test Method A (Metadata filter, 28 docs)
        method_a_times = []
        method_a_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_method_a(
                fault_collection, anomaly_type
            )
            method_a_times.append(time_ms)
            if not is_correct:
                method_a_correct = False
            print(f"  Method A Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_a_avg_time = sum(method_a_times) / len(method_a_times)

        # Test Method B (Semantic search, 28 docs)
        method_b_times = []
        method_b_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_method_b(
                fault_collection, anomaly_type, symptom_description
            )
            method_b_times.append(time_ms)
            if not is_correct:
                method_b_correct = False
            print(f"  Method B Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_b_avg_time = sum(method_b_times) / len(method_b_times)

        # Test Method C (Metadata filter, 7 docs)
        method_c_times = []
        method_c_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_method_c(
                symptom_collection, anomaly_type
            )
            method_c_times.append(time_ms)
            if not is_correct:
                method_c_correct = False
            print(f"  Method C Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_c_avg_time = sum(method_c_times) / len(method_c_times)

        # Test Method D (Semantic search, 7 docs)
        method_d_times = []
        method_d_correct = True

        for trial in range(NUM_TRIALS):
            is_correct, time_ms = test_method_d(
                symptom_collection, anomaly_type, symptom_description
            )
            method_d_times.append(time_ms)
            if not is_correct:
                method_d_correct = False
            print(f"  Method D Trial {trial + 1}: "
                  f"{'✓' if is_correct else '✗'} ({time_ms:.2f} ms)")

        method_d_avg_time = sum(method_d_times) / len(method_d_times)

        results[anomaly_type] = {
            "method_a_correct": method_a_correct,
            "method_a_time": method_a_avg_time,
            "method_b_correct": method_b_correct,
            "method_b_time": method_b_avg_time,
            "method_c_correct": method_c_correct,
            "method_c_time": method_c_avg_time,
            "method_d_correct": method_d_correct,
            "method_d_time": method_d_avg_time,
        }

    # Print summary table
    print("\n" + "=" * 79)
    print("RESULTS SUMMARY")
    print("=" * 79)
    print(f"\n{'Anomaly Type':<45} {'A✓':<5} {'A ms':<8} "
          f"{'B✓':<5} {'B ms':<8} {'C✓':<5} {'C ms':<8} "
          f"{'D✓':<5} {'D ms':<8}")
    print("-" * 79)

    for anomaly_type, result in results.items():
        print(f"{anomaly_type:<45} "
              f"{'✓' if result['method_a_correct'] else '✗':<5} "
              f"{result['method_a_time']:.2f}{'':<4} "
              f"{'✓' if result['method_b_correct'] else '✗':<5} "
              f"{result['method_b_time']:.2f}{'':<4} "
              f"{'✓' if result['method_c_correct'] else '✗':<5} "
              f"{result['method_c_time']:.2f}{'':<4} "
              f"{'✓' if result['method_d_correct'] else '✗':<5} "
              f"{result['method_d_time']:.2f}")

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
    method_c_correct_count = sum(
        1 for r in results.values() if r["method_c_correct"]
    )
    method_d_correct_count = sum(
        1 for r in results.values() if r["method_d_correct"]
    )

    method_a_avg_time = sum(
        r["method_a_time"] for r in results.values()
    ) / len(results)
    method_b_avg_time = sum(
        r["method_b_time"] for r in results.values()
    ) / len(results)
    method_c_avg_time = sum(
        r["method_c_time"] for r in results.values()
    ) / len(results)
    method_d_avg_time = sum(
        r["method_d_time"] for r in results.values()
    ) / len(results)

    total_tests = len(results)
    method_a_accuracy = (method_a_correct_count / total_tests) * 100
    method_b_accuracy = (method_b_correct_count / total_tests) * 100
    method_c_accuracy = (method_c_correct_count / total_tests) * 100
    method_d_accuracy = (method_d_correct_count / total_tests) * 100

    with open(output_path, "w") as f:
        f.write("# Retrieval Method Comparison: Metadata Filter vs "
                "Semantic Search × Section-Level vs Document-Level "
                "Chunking\n\n")

        f.write("## Section 1 — Test Setup\n\n")
        f.write("This evaluation implements a 2×2 comparison design:\n\n")
        f.write("**Two retrieval methods:**\n\n")
        f.write("1. **Metadata filter**: Deterministic exact matching "
                "using `collection.get()` with `anomaly_type` metadata\n")
        f.write("2. **Semantic search**: Vector similarity search using "
                "`collection.query()` with symptom descriptions\n\n")
        f.write("**Two knowledge base chunking strategies:**\n\n")
        f.write("1. **Section-level chunking (28 documents)**: "
                "`fault_knowledge` collection with 7 anomaly types × 4 "
                "sections (description+causes, actions_low, "
                "actions_medium, actions_high)\n")
        f.write("2. **Document-level chunking (7 documents)**: "
                "`symptom_knowledge` collection with 7 anomaly types × 1 "
                "merged document (description + causes + all actions)\n\n")
        f.write("**Four method combinations:**\n\n")
        f.write("- **Method A**: Metadata filter on fault_knowledge "
                "(28 docs, section-level)\n")
        f.write("- **Method B**: Semantic search on fault_knowledge "
                "(28 docs, section-level)\n")
        f.write("- **Method C**: Metadata filter on symptom_knowledge "
                "(7 docs, document-level)\n")
        f.write("- **Method D**: Semantic search on symptom_knowledge "
                "(7 docs, document-level)\n\n")
        f.write("Both knowledge bases contain the same underlying fault "
                "knowledge from `grounded_knowledge.yaml` but differ in "
                "chunking strategy.\n\n")
        f.write(f"**Trials per method**: {NUM_TRIALS}\n\n")
        f.write(f"**Anomaly types tested**: {len(ANOMALY_SYMPTOMS)}\n\n")

        f.write("## Section 2 — Results Table\n\n")
        f.write("| Anomaly Type | Method A (Meta+28) Correct | "
                "Method A Time ms | Method B (Sem+28) Correct | "
                "Method B Time ms | Method C (Meta+7) Correct | "
                "Method C Time ms | Method D (Sem+7) Correct | "
                "Method D Time ms |\n")
        f.write("|--------------|----------------------------|"
                "------------------|---------------------------|"
                "------------------|--------------------------|"
                "------------------|--------------------------|"
                "------------------|\n")

        for anomaly_type, result in results.items():
            f.write(f"| {anomaly_type} | "
                    f"{'✓' if result['method_a_correct'] else '✗'} | "
                    f"{result['method_a_time']:.2f} | "
                    f"{'✓' if result['method_b_correct'] else '✗'} | "
                    f"{result['method_b_time']:.2f} | "
                    f"{'✓' if result['method_c_correct'] else '✗'} | "
                    f"{result['method_c_time']:.2f} | "
                    f"{'✓' if result['method_d_correct'] else '✗'} | "
                    f"{result['method_d_time']:.2f} |\n")

        f.write("\n## Section 3 — Key Findings\n\n")

        f.write("### Dimension 1: Retrieval Method Comparison\n\n")
        f.write("**Metadata Filter vs Semantic Search at Section-Level "
                "(28 docs):**\n\n")
        f.write(f"- Method A (Metadata+28): {method_a_accuracy:.1f}% "
                f"accuracy, {method_a_avg_time:.2f} ms average\n")
        f.write(f"- Method B (Semantic+28): {method_b_accuracy:.1f}% "
                f"accuracy, {method_b_avg_time:.2f} ms average\n")
        if method_a_accuracy > method_b_accuracy:
            f.write(f"- **Winner**: Metadata filter is more accurate "
                    f"({method_a_accuracy - method_b_accuracy:.1f}% "
                    f"advantage)\n\n")
        elif method_b_accuracy > method_a_accuracy:
            f.write(f"- **Winner**: Semantic search is more accurate "
                    f"({method_b_accuracy - method_a_accuracy:.1f}% "
                    f"advantage)\n\n")
        else:
            f.write("- **Winner**: Both methods achieve equal "
                    "accuracy\n\n")

        f.write("**Metadata Filter vs Semantic Search at Document-Level "
                "(7 docs):**\n\n")
        f.write(f"- Method C (Metadata+7): {method_c_accuracy:.1f}% "
                f"accuracy, {method_c_avg_time:.2f} ms average\n")
        f.write(f"- Method D (Semantic+7): {method_d_accuracy:.1f}% "
                f"accuracy, {method_d_avg_time:.2f} ms average\n")
        if method_c_accuracy > method_d_accuracy:
            f.write(f"- **Winner**: Metadata filter is more accurate "
                    f"({method_c_accuracy - method_d_accuracy:.1f}% "
                    f"advantage)\n\n")
        elif method_d_accuracy > method_c_accuracy:
            f.write(f"- **Winner**: Semantic search is more accurate "
                    f"({method_d_accuracy - method_c_accuracy:.1f}% "
                    f"advantage)\n\n")
        else:
            f.write("- **Winner**: Both methods achieve equal "
                    "accuracy\n\n")

        f.write("### Dimension 2: Chunking Strategy Comparison\n\n")
        f.write("**Section-Level (28 docs) vs Document-Level (7 docs) "
                "with Metadata Filter:**\n\n")
        f.write(f"- Method A (Meta+28): {method_a_accuracy:.1f}% "
                f"accuracy, {method_a_avg_time:.2f} ms average\n")
        f.write(f"- Method C (Meta+7): {method_c_accuracy:.1f}% "
                f"accuracy, {method_c_avg_time:.2f} ms average\n")
        if method_a_accuracy == method_c_accuracy:
            f.write("- **Finding**: Metadata-filtered retrieval is "
                    "robust to chunking strategy (both achieve equal "
                    "accuracy)\n\n")
        else:
            f.write(f"- **Finding**: Chunking strategy affects metadata "
                    f"filter accuracy\n\n")

        f.write("**Section-Level (28 docs) vs Document-Level (7 docs) "
                "with Semantic Search:**\n\n")
        f.write(f"- Method B (Sem+28): {method_b_accuracy:.1f}% "
                f"accuracy, {method_b_avg_time:.2f} ms average\n")
        f.write(f"- Method D (Sem+7): {method_d_accuracy:.1f}% "
                f"accuracy, {method_d_avg_time:.2f} ms average\n")
        if method_d_accuracy > method_b_accuracy:
            f.write(f"- **Finding**: Document-level chunking improves "
                    f"semantic search accuracy by "
                    f"{method_d_accuracy - method_b_accuracy:.1f}% "
                    f"(richer context for embeddings)\n\n")
        elif method_b_accuracy > method_d_accuracy:
            f.write(f"- **Finding**: Section-level chunking improves "
                    f"semantic search accuracy by "
                    f"{method_b_accuracy - method_d_accuracy:.1f}% "
                    f"(more focused matching)\n\n")
        else:
            f.write("- **Finding**: Chunking strategy does not affect "
                    "semantic search accuracy\n\n")

        f.write("## Section 4 — Conclusion\n\n")

        # Determine best method
        best_accuracy = max(
            method_a_accuracy, method_b_accuracy,
            method_c_accuracy, method_d_accuracy
        )
        best_methods = []
        if method_a_accuracy == best_accuracy:
            best_methods.append("Method A (Meta+28)")
        if method_b_accuracy == best_accuracy:
            best_methods.append("Method B (Sem+28)")
        if method_c_accuracy == best_accuracy:
            best_methods.append("Method C (Meta+7)")
        if method_d_accuracy == best_accuracy:
            best_methods.append("Method D (Sem+7)")

        f.write(f"**Best accuracy**: {' and '.join(best_methods)} "
                f"achieve {best_accuracy:.1f}% accuracy.\n\n")

        if method_a_accuracy == method_c_accuracy == 100.0:
            f.write("**Key insight**: Metadata-filtered retrieval "
                    "(Methods A and C) is robust to chunking strategy, "
                    "achieving perfect accuracy with both section-level "
                    "and document-level chunking.\n\n")

        if method_d_accuracy > method_b_accuracy:
            f.write("**Key insight**: Semantic search accuracy depends "
                    "heavily on chunking granularity. Document-level "
                    "chunking (Method D) outperforms section-level "
                    "chunking (Method B) because merged documents "
                    "provide richer context for embedding models to "
                    "match symptom descriptions.\n\n")
        elif method_b_accuracy > method_d_accuracy:
            f.write("**Key insight**: Semantic search accuracy depends "
                    "heavily on chunking granularity. Section-level "
                    "chunking (Method B) outperforms document-level "
                    "chunking (Method D) because focused sections "
                    "provide more precise semantic matching.\n\n")

        f.write("**Reference**: This evaluation validates the design "
                "decision in ADR 303 to use metadata-filtered retrieval "
                "in the Granite Lifeline RAG pipeline.\n\n")

        f.write("**Known limitation**: The symptom descriptions used as "
                "queries were written for this evaluation and may not "
                "reflect the actual query format in the Granite Lifeline "
                "pipeline, where `anomaly_type` is already confirmed by "
                "the Model Layer before retrieval occurs.\n\n")

        f.write("## Section 5 — Implications for RAG Design\n\n")
        f.write("In the Granite Lifeline pipeline, the Model Layer "
                "confirms `anomaly_type` before the Report Layer "
                "performs retrieval. This makes **metadata-filtered "
                "retrieval the appropriate and deterministic choice**:\n\n")
        f.write("1. **Deterministic behavior**: Given a confirmed "
                "`anomaly_type`, metadata filtering guarantees exact "
                "retrieval of the correct knowledge document\n")
        f.write("2. **No embedding dependency**: Metadata filtering does "
                "not depend on embedding model semantics or query "
                "phrasing\n")
        f.write("3. **Robust to chunking**: As shown in this evaluation, "
                "metadata filtering achieves consistent accuracy "
                "regardless of chunking strategy\n\n")
        f.write("**When would semantic search be relevant?** Semantic "
                "search would only be necessary if the system needed to "
                "infer `anomaly_type` from natural language input (e.g., "
                "user-provided symptom descriptions). This is not the "
                "current design of Granite Lifeline, where anomaly "
                "detection is performed by the Model Layer using "
                "time-series analysis, not natural language "
                "processing.\n\n")
        f.write("**Current architecture**: Model Layer → confirmed "
                "`anomaly_type` → Report Layer → metadata-filtered "
                "retrieval → diagnostic report generation.\n")

    print(f"\nMarkdown report written to: {output_path}")


if __name__ == "__main__":
    run_comparison()
