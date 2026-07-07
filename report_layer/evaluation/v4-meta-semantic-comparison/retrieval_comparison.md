# Retrieval Method Comparison: Metadata Filter vs Semantic Search × Section-Level vs Document-Level Chunking

## Section 1 — Test Setup

This evaluation implements a 2×2 comparison design:

**Two retrieval methods:**

1. **Metadata filter**: Deterministic exact matching using `collection.get()` with `anomaly_type` metadata
2. **Semantic search**: Vector similarity search using `collection.query()` with symptom descriptions

**Two knowledge base chunking strategies:**

1. **Section-level chunking (28 documents)**: `fault_knowledge` collection with 7 anomaly types × 4 sections (description+causes, actions_low, actions_medium, actions_high)
2. **Document-level chunking (7 documents)**: `symptom_knowledge` collection with 7 anomaly types × 1 merged document (description + causes + all actions)

**Four method combinations:**

- **Method A**: Metadata filter on fault_knowledge (28 docs, section-level)
- **Method B**: Semantic search on fault_knowledge (28 docs, section-level)
- **Method C**: Metadata filter on symptom_knowledge (7 docs, document-level)
- **Method D**: Semantic search on symptom_knowledge (7 docs, document-level)

Both knowledge bases contain the same underlying fault knowledge from `grounded_knowledge.yaml` but differ in chunking strategy.

**Trials per method**: 3

**Anomaly types tested**: 7

## Section 2 — Results Table

| Anomaly Type | Method A (Meta+28) Correct | Method A Time ms | Method B (Sem+28) Correct | Method B Time ms | Method C (Meta+7) Correct | Method C Time ms | Method D (Sem+7) Correct | Method D Time ms |
|--------------|----------------------------|------------------|---------------------------|------------------|--------------------------|------------------|--------------------------|------------------|
| cooling_degradation | ✓ | 0.46 | ✓ | 72.98 | ✓ | 0.32 | ✓ | 57.25 |
| intake_air_temperature_sensor_or_heat_soak_fault | ✓ | 0.30 | ✗ | 55.96 | ✓ | 0.29 | ✓ | 56.77 |
| air_intake_maf_anomaly | ✓ | 0.32 | ✗ | 56.16 | ✓ | 0.28 | ✓ | 55.25 |
| map_load_signal_plausibility_fault | ✓ | 0.29 | ✓ | 57.93 | ✓ | 0.28 | ✓ | 56.58 |
| electronic_throttle_tracking_fault | ✓ | 0.35 | ✗ | 56.20 | ✓ | 0.33 | ✗ | 55.34 |
| accelerator_pedal_sensor | ✓ | 0.29 | ✓ | 55.96 | ✓ | 0.36 | ✓ | 62.72 |
| idle_speed_control_or_surge_degradation | ✓ | 0.38 | ✓ | 71.89 | ✓ | 0.30 | ✓ | 57.94 |
