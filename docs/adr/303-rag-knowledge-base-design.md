# ADR 303: RAG Knowledge Base Design for Report Layer

## Status
Accepted

## Date
2026-06-29

## Context
The Report Layer uses IBM Granite 4.1 8B (via Ollama) to generate three-section diagnostic reports (anomalous behaviour description, probable physical root cause, recommended inspection action) from OBD-II sensor anomaly data. The model requires grounding in fault domain knowledge to reduce hallucination and produce accurate, source-backed diagnostic content.

A fault knowledge base has been compiled in `shared/ground_knowledge/fault_knowledge_all.md`, covering seven proxy failure anomaly types: `cooling_degradation`, `intake_air_temperature_sensor_or_heat_soak_fault`, `air_intake_maf_anomaly`, `map_load_signal_plausibility_fault`, `electronic_throttle_tracking_fault`, `accelerator_pedal_sensor`, and `idle_speed_control_or_surge_degradation`. Each anomaly type entry contains a description, causes list, and actions list (low, medium, high risk levels).

The Report Layer receives a `ModelLayerOutput` object from the Model Layer containing a confirmed `anomaly_type` field alongside `risk_score`, `risk_level`, `key_signals`, and `prediction_confidence`. The `anomaly_type` field is an exact string match to entries in the knowledge base.

Three approaches were considered for injecting fault knowledge into the Granite LLM prompt:

**Option A — Full prompt injection**: embed all seven anomaly type entries directly into the system prompt on every call.

**Option B — Semantic vector search RAG**: embed the knowledge base into ChromaDB using vector embeddings; retrieve relevant chunks using semantic similarity search against the input sensor values or anomaly description.

**Option C — Metadata-filtered retrieval**: store each anomaly type entry in ChromaDB with the `anomaly_type` string as a metadata field; retrieve using exact metadata filter on `anomaly_type` rather than vector similarity.

## Decision
**Option C is selected**: metadata-filtered retrieval using ChromaDB with LangChain.

Each anomaly type entry from `fault_knowledge_all.md` is stored as a document in ChromaDB with metadata field `anomaly_type` set to the exact anomaly type string. At inference time, the Report Layer queries ChromaDB using a metadata filter for the `anomaly_type` value from `ModelLayerOutput`, retrieving only the relevant entry. The retrieved content is injected into the Granite LLM prompt as grounding context before generation.

## Rationale

### Why not Option A (full prompt injection)?
Embedding all seven anomaly type entries into every prompt call introduces unnecessary token overhead, as only one anomaly type is relevant per inference call. Long context windows risk attention dilution, where the LLM may underweight critical fault knowledge buried in a lengthy prompt. This approach is also not scalable: adding new anomaly types requires modifying the prompt template directly.

### Why not Option B (semantic vector search)?
The `anomaly_type` field in `ModelLayerOutput` is an exact, confirmed string produced by the Model Layer. Semantic similarity search is designed for cases where the query is fuzzy or unstructured. Using vector search when the target anomaly type is already known introduces unnecessary non-determinism: the correct entry may not always rank highest depending on embedding quality and chunk boundaries. Exact metadata filtering is more reliable and predictable for this use case.

### Why Option C (metadata-filtered retrieval)?
The `anomaly_type` field provides a guaranteed exact key for retrieval. Metadata filtering eliminates retrieval uncertainty, ensures the correct fault knowledge entry is always returned, and keeps the retrieval step lightweight. ChromaDB supports metadata filtering natively. This approach also allows the knowledge base to be extended by adding new anomaly type documents without changing retrieval logic or prompt templates.

This decision is supported by Huang et al. (2025), which identifies faithfulness hallucination — where LLM output is unfaithful to provided context — as a key risk in LLM-based diagnostic systems. Grounding the prompt with retrieved, source-attributed fault knowledge directly mitigates this risk.

## Implementation

The knowledge base is stored in `shared/ground_knowledge/grounded_knowledge.yaml` and indexed into ChromaDB at pipeline initialisation. Each document is stored with metadata: `{"anomaly_type": "<anomaly_type_string>", "risk_level": "<risk_level>"}`. At inference time, the retrieval query is: `collection.get(where={"anomaly_type": anomaly_type, "risk_level": risk_level})`. Retrieved content is injected into the Granite LLM prompt as a context block before the three-layer prompt chain defined in GL-55.

The context builder was extended with two enhancements: (1) confidence-based certainty guidance — the LLM receives explicit language strength instructions based on prediction_confidence thresholds; (2) multi-signal correlation analysis — when multiple signals are abnormal simultaneously, the context explicitly flags this pattern to support systemic root cause analysis.

Development environment: ChromaDB local instance, Ollama granite4.1:8b. The ChromaDB index is rebuilt from `grounded_knowledge.yaml` on pipeline startup to ensure consistency with the knowledge base.

## Consequences

### Positive
- **Deterministic retrieval**: exact metadata match guarantees the correct fault knowledge entry is always returned.
- **Reduced hallucination**: grounding the prompt in retrieved, source-attributed fault knowledge reduces factuality and faithfulness hallucination risk, consistent with Huang et al. (2025).
- **Scalable**: new anomaly types can be added to the knowledge base without modifying retrieval logic or prompt templates.
- **Lightweight**: only the relevant anomaly type entry is injected per inference call, minimising token overhead.

### Negative
- Requires ChromaDB dependency and index initialisation at pipeline startup.
- Knowledge base must be kept in sync with `grounded_knowledge.yaml` `anomaly_type` naming — any naming mismatch between the YAML and the ChromaDB metadata will cause retrieval failure.

### Mitigation
A startup validation check will verify that all `anomaly_type` values in `grounded_knowledge.yaml` have a corresponding document in the ChromaDB collection, and raise an error if any are missing.

## Related Decisions
- ADR 301: Context Injection Design for Granite LLM Prompt
- ADR 302: Granite LLM Model Selection for Diagnostic Report Generation
- GL-55: Three-layer prompt template design

## References
- Huang et al. (2025). A Survey on Hallucination in Large Language Models. ACM Transactions on Information Systems.
- LangChain ChromaDB integration: https://python.langchain.com/docs/integrations/vectorstores/chroma
- ChromaDB metadata filtering: https://docs.trychroma.com/guides#filtering-by-metadata