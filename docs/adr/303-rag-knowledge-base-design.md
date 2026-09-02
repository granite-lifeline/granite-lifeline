# ADR 303: RAG Knowledge Base Design for Report Layer

## Status
Accepted

## Date
2026-06-29

## Context
The Report Layer uses IBM Granite 4.1 8B (via Ollama) to generate three-section diagnostic reports (anomalous behaviour description, possible cause, and recommended action) from Model Layer anomaly evidence. Reviewed automotive knowledge is used for possible explanations and actions; the observation section uses only the supplied Model Layer evidence.

A fault knowledge base is maintained in `shared/ground_knowledge/grounded_knowledge.yaml` for the five runtime anomaly types: `cooling_degradation`, `intake_air_temperature_sensor_fault`, `air_intake_maf_anomaly`, `map_load_signal_plausibility_fault`, and `accelerator_pedal_sensor`. Each entry contains a description, possible causes, and separate Low-, Medium-, and High-risk actions.

The Report Layer receives a `ModelLayerOutput` object containing the selected `anomaly_type` alongside `risk_score`, `risk_level`, `key_signals`, and `prediction_confidence`. The selected type is anomaly evidence, not a confirmed mechanical diagnosis. Its key exactly matches one of the five knowledge-base entries.

Three approaches were considered for injecting fault knowledge into the Granite LLM prompt:

**Option A — Full prompt injection**: embed all five anomaly type entries directly into the system prompt on every call.

**Option B — Semantic vector search RAG**: embed the knowledge base into ChromaDB using vector embeddings; retrieve relevant chunks using semantic similarity search against the input sensor values or anomaly description.

**Option C — Metadata-filtered retrieval**: store each anomaly type entry in ChromaDB with the `anomaly_type` string as a metadata field; retrieve using exact metadata filter on `anomaly_type` rather than vector similarity.

## Decision
**Option C is selected**: metadata-filtered retrieval using ChromaDB's Python client.

The indexer creates four records for each anomaly type: one description-and-causes record and three risk-specific action records. During generation, Layer 2 retrieves the description-and-causes record by `anomaly_type` and `section`; Layer 3 also includes `risk_level` when retrieving its action record. Layer 1 does not receive retrieved automotive knowledge.

## Rationale

### Why not Option A (full prompt injection)?
Embedding all five anomaly type entries into every prompt call introduces unnecessary token overhead, as only one anomaly type is relevant per inference call. Long context windows risk attention dilution, where the LLM may underweight critical fault knowledge buried in a lengthy prompt. This approach is also not scalable: adding new anomaly types requires modifying the prompt template directly.

### Why not Option B (semantic vector search)?
The `anomaly_type` field in `ModelLayerOutput` is an exact category key supplied by the Model Layer. Semantic similarity search is designed for cases where the query is fuzzy or unstructured. Using vector search when the target category is already available introduces unnecessary ranking variation: the requested entry may not always rank highest depending on embedding quality and chunk boundaries. Exact metadata filtering is more predictable for this use case.

### Why Option C (metadata-filtered retrieval)?
The `anomaly_type` field provides an exact retrieval key. Metadata filtering avoids similarity-ranking variation and keeps the retrieval step lightweight. It ensures that the returned record matches the category selected upstream; it does not verify that the upstream category is mechanically correct. ChromaDB supports metadata filtering natively. This approach also allows the knowledge base to be extended by adding new anomaly type records without changing prompt templates.

This decision is supported by Huang et al. (2025), which identifies faithfulness hallucination — where LLM output is unfaithful to provided context — as a key risk. Supplying reviewed, source-attributed fault knowledge gives the Report Layer a defined evidence source for possible explanations and actions.

## Implementation

The setup process runs `report_layer/rag/knowledge_indexer.py`, which deletes and rebuilds the `fault_knowledge` collection from `grounded_knowledge.yaml`. It checks that all five runtime types are present and that the completed collection contains 20 records. Records include `anomaly_type` and `section` metadata; action records also include a lowercase `risk_level`. Retrieval uses an exact `$and` metadata filter.

The context builder was extended with two enhancements: (1) confidence-based certainty guidance — the LLM receives explicit language strength instructions based on prediction_confidence thresholds; (2) multi-signal correlation analysis — when multiple signals are abnormal simultaneously, the context explicitly flags this pattern to support systemic root cause analysis.

The runtime uses a local persistent ChromaDB collection and Ollama `granite4.1:8b`. If the collection is temporarily unavailable, retrieval returns bounded fallback text and retries the collection after a short interval.

## Consequences

### Positive
- **Deterministic retrieval**: exact metadata match guarantees the correct fault knowledge entry is always returned.
- **Reduced hallucination**: grounding the prompt in retrieved, source-attributed fault knowledge reduces factuality and faithfulness hallucination risk, consistent with Huang et al. (2025).
- **Scalable**: new anomaly types can be added to the knowledge base without modifying retrieval logic or prompt templates.
- **Lightweight**: only the relevant anomaly type entry is injected per inference call, minimising token overhead.

### Negative
- Requires the ChromaDB dependency and an index built during local setup.
- Knowledge base must be kept in sync with `grounded_knowledge.yaml` `anomaly_type` naming — any naming mismatch between the YAML and the ChromaDB metadata will cause retrieval failure.

### Mitigation
The indexer validates the five runtime anomaly types and the final 20-record count. The readiness check verifies the local collection before a complete pipeline run. Runtime lookup degrades to explicit fallback text if the collection is unavailable.

## Related Decisions
- ADR 301: Context Injection Design for Granite LLM Prompt
- ADR 302: Granite LLM Model Selection for Diagnostic Report Generation
- GL-55: Three-layer prompt template design

## References
- Huang et al. (2025). A Survey on Hallucination in Large Language Models. ACM Transactions on Information Systems.
- ChromaDB metadata filtering: https://docs.trychroma.com/guides#filtering-by-metadata
