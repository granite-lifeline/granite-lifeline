# Retrieval Method Comparison — Re-run on Current 5 Anomaly Types

Re-run of the GL-166 four-way comparison (`retrieval_comparison.py`) against the current 5-anomaly-type knowledge base, after the Data Layer's schema-v1 retirement of `electronic_throttle_tracking_fault` and `idle_speed_control_or_surge_degradation`. The original 7-type/28-document result is preserved unchanged in `retrieval_comparison.md` for historical provenance.

One methodological correction versus the original script: a one-time embedding-model warm-up call (~90ms vs ~54ms steady-state, confirmed by isolating 5 consecutive Method B calls) is discarded before timed trials, so it isn't misattributed to semantic search's per-query cost.

**Trials per method**: 3

**Anomaly types tested**: 5 (cooling_degradation, intake_air_temperature_sensor_fault, air_intake_maf_anomaly, map_load_signal_plausibility_fault, accelerator_pedal_sensor)

**Collections**: fault_knowledge (20 docs, section-level) / symptom_knowledge (5 docs, document-level)

## Results Table

| Anomaly Type | A (Meta+20) | A ms | B (Sem+20) | B ms | C (Meta+5) | C ms | D (Sem+5) | D ms |
|---|---|---|---|---|---|---|---|---|
| cooling_degradation | correct | 0.416 | correct | 57.40 | correct | 0.355 | correct | 59.94 |
| intake_air_temperature_sensor_fault | correct | 0.317 | WRONG | 54.21 | correct | 0.313 | correct | 54.21 |
| air_intake_maf_anomaly | correct | 0.304 | WRONG | 53.90 | correct | 0.299 | correct | 53.98 |
| map_load_signal_plausibility_fault | correct | 0.335 | correct | 54.70 | correct | 0.294 | correct | 54.00 |
| accelerator_pedal_sensor | correct | 0.311 | correct | 53.88 | correct | 0.286 | correct | 54.99 |

## Summary

- Method A (metadata filter, section-level, 20 docs): 100.0% accuracy, 0.337 ms average
- Method B (semantic search, section-level, 20 docs): 60.0% accuracy, 54.82 ms average
- Method C (metadata filter, document-level, 5 docs): 100.0% accuracy, 0.310 ms average
- Method D (semantic search, document-level, 5 docs): 100.0% accuracy, 55.43 ms average

**Method A vs Method B (the production knowledge base, exact-match vs semantic)**: 163x faster, 100% vs 60% accuracy.

**Comparison to the original 7-type result** (`retrieval_comparison.md`): Method A was 100% accurate in both runs. Method B's accuracy on the current 5-type set (60%, 3/5) is close to the original's 4/7 (~57%) — the advantage of metadata filtering over semantic search on the production knowledge base is not an artifact of the old 7-type set; it reproduces on current data.
