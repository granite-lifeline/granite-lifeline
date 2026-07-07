# Retrieval Method Comparison: Metadata Filter vs Semantic Search

## Test Setup

This evaluation compares two retrieval methods for the `fault_knowledge` ChromaDB collection:

- **Method A (Metadata-filtered retrieval)**: Uses `collection.get()` with exact `anomaly_type` metadata matching and `section='description_causes'` filter (current approach per ADR 303)
- **Method B (Semantic vector search)**: Uses `collection.query()` with symptom descriptions to find semantically similar documents, then validates if the returned document's `anomaly_type` metadata matches the expected type

**Collection**: `fault_knowledge` (28 documents: 7 anomaly types × 4 sections)

**Trials per method**: 3

**Anomaly types tested**: 7

## Results

| Anomaly Type | Method A Correct | Method A Time (ms) | Method B Correct | Method B Time (ms) |
|--------------|------------------|--------------------|------------------|--------------------|
| cooling_degradation | ✓ | 3.65 | ✓ | 100.25 |
| intake_air_temperature_sensor_or_heat_soak_fault | ✓ | 0.30 | ✗ | 54.91 |
| air_intake_maf_anomaly | ✓ | 0.27 | ✗ | 55.20 |
| map_load_signal_plausibility_fault | ✓ | 0.29 | ✓ | 55.25 |
| electronic_throttle_tracking_fault | ✓ | 0.60 | ✗ | 56.44 |
| accelerator_pedal_sensor | ✓ | 0.34 | ✓ | 70.84 |
| idle_speed_control_or_surge_degradation | ✓ | 0.60 | ✓ | 73.76 |

## Key Findings

### Accuracy

- **Method A**: 7/7 correct (100.0%)
- **Method B**: 4/7 correct (57.1%)

### Speed

- **Method A**: 0.86 ms average
- **Method B**: 66.66 ms average
- **Speed difference**: Method B is 77.15x slower than Method A

## Conclusion

**Recommendation**: Continue using **Method A (Metadata-filtered retrieval)** as specified in ADR 303.

**Rationale**:

1. **Perfect accuracy**: Method A correctly retrieves the target document in 100% of cases
2. **Superior performance**: Method A is 77.15x faster than semantic search
3. **Deterministic behavior**: Metadata filtering provides predictable, exact matching without dependency on embedding model semantics
4. **Alignment with ADR 303**: The current architecture decision is validated by these results
