# Retrieval Method Comparison: Three Approaches

## Test Setup

This evaluation compares three retrieval methods:

- **Method A (Metadata-filtered retrieval)**: Uses `collection.get()` with exact `anomaly_type` metadata matching and `section='description_causes'` filter on `fault_knowledge` collection (28 documents: 7 anomaly types × 4 sections) — current approach per ADR 303
- **Method B (Semantic search, section-level)**: Uses `collection.query()` with symptom descriptions on `fault_knowledge` collection (28 documents with section-level chunking: description+causes, actions_low, actions_medium, actions_high)
- **Method B2 (Semantic search, document-level)**: Uses `collection.query()` with symptom descriptions on `symptom_knowledge` collection (7 documents with document-level chunking: each document contains merged description, causes, and all actions)

**Trials per method**: 3

**Anomaly types tested**: 7

## Results

| Anomaly Type | Method A Correct | Method A Time (ms) | Method B Correct | Method B Time (ms) | Method B2 Correct | Method B2 Time (ms) |
|--------------|------------------|--------------------|------------------|--------------------|-----------------|---------------------|
| cooling_degradation | ✓ | 1.35 | ✓ | 69.00 | ✓ | 56.90 |
| intake_air_temperature_sensor_or_heat_soak_fault | ✓ | 0.46 | ✗ | 87.78 | ✓ | 75.90 |
| air_intake_maf_anomaly | ✓ | 0.50 | ✗ | 79.36 | ✓ | 57.35 |
| map_load_signal_plausibility_fault | ✓ | 0.35 | ✓ | 57.84 | ✓ | 123.85 |
| electronic_throttle_tracking_fault | ✓ | 0.38 | ✗ | 58.14 | ✗ | 55.83 |
| accelerator_pedal_sensor | ✓ | 0.30 | ✓ | 54.39 | ✓ | 54.29 |
| idle_speed_control_or_surge_degradation | ✓ | 0.29 | ✓ | 54.43 | ✓ | 54.14 |

## Key Findings

### Accuracy

- **Method A**: 7/7 correct (100.0%)
- **Method B**: 4/7 correct (57.1%)
- **Method B2**: 6/7 correct (85.7%)

### Speed

- **Method A**: 0.52 ms average
- **Method B**: 65.85 ms average
- **Method B2**: 68.33 ms average
- **Speed comparison**: Method B is 126.93x slower than Method A; Method B2 is 131.71x slower than Method A

## Conclusion

This evaluation compares three retrieval approaches:

1. **Method A**: Metadata filtering on 28-document collection (deterministic, exact matching)
2. **Method B**: Semantic search on 28-document collection with section-level chunking (4 documents per anomaly type)
3. **Method B2**: Semantic search on 7-document collection with document-level chunking (1 document per anomaly type)

**Key Insight**: Methods B and B2 use the same underlying knowledge but different chunking strategies. Method B uses section-level chunking (description+causes separate from actions), while Method B2 uses document-level chunking (all content merged into a single document per anomaly type).

**Chunking Strategy for Semantic Search**: Method B2 (document-level) performed better for semantic search. Document-level chunking (merging all content) is more appropriate for semantic search because it provides richer context for embedding models to match symptom descriptions to the complete anomaly profile.

**Recommendation**: Continue using **Method A (Metadata-filtered retrieval)** as specified in ADR 303.

**Rationale**:

1. **Perfect accuracy**: Method A correctly retrieves the target document in 100% of cases
2. **Superior performance**: Method A is 126.93x faster than Method B and 131.71x faster than Method B2
3. **Deterministic behavior**: Metadata filtering provides predictable, exact matching without dependency on embedding model semantics
4. **Alignment with ADR 303**: The current architecture decision is validated by these results
