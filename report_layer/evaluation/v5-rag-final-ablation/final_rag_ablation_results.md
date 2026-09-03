# Final-pipeline RAG ablation results

All conditions use the final production prompts, identical certainty guidance, temperature, validator and correction loop.

> The legacy quality score and heuristic counts below are screening outputs. Manual review is required for relevance, mechanical accuracy and action safety.

| Condition | Reports | Fallbacks | Mean legacy quality | Unsupported numbers | Unsafe owner actions | Raw fields |
|---|---:|---:|---:|---:|---:|---:|
| controlled_baseline | 5 | 0 | 0.860 | 0 | 0 | 2 |
| cause_rag | 5 | 0 | 0.930 | 0 | 0 | 2 |
| current_full_rag | 5 | 0 | 0.930 | 0 | 0 | 2 |
| owner_safe_rag | 5 | 0 | 0.930 | 0 | 0 | 2 |

## Per-report results

| Anomaly | Risk | Condition | Overall | Validator warnings | Unsupported numbers | Unsafe actions |
|---|---|---|---:|---:|---:|---:|
| cooling_degradation | Low | controlled_baseline | 0.90 | 1 | 0 | 0 |
| cooling_degradation | Low | cause_rag | 1.00 | 0 | 0 | 0 |
| cooling_degradation | Low | current_full_rag | 1.00 | 0 | 0 | 0 |
| cooling_degradation | Low | owner_safe_rag | 1.00 | 0 | 0 | 0 |
| air_intake_maf_anomaly | Low | controlled_baseline | 0.82 | 1 | 0 | 0 |
| air_intake_maf_anomaly | Low | cause_rag | 0.93 | 0 | 0 | 0 |
| air_intake_maf_anomaly | Low | current_full_rag | 0.93 | 0 | 0 | 0 |
| air_intake_maf_anomaly | Low | owner_safe_rag | 0.93 | 0 | 0 | 0 |
| accelerator_pedal_sensor | Medium | controlled_baseline | 0.85 | 1 | 0 | 0 |
| accelerator_pedal_sensor | Medium | cause_rag | 0.88 | 0 | 0 | 0 |
| accelerator_pedal_sensor | Medium | current_full_rag | 0.88 | 0 | 0 | 0 |
| accelerator_pedal_sensor | Medium | owner_safe_rag | 0.88 | 0 | 0 | 0 |
| intake_air_temperature_sensor_fault | High | controlled_baseline | 0.90 | 1 | 0 | 0 |
| intake_air_temperature_sensor_fault | High | cause_rag | 1.00 | 0 | 0 | 0 |
| intake_air_temperature_sensor_fault | High | current_full_rag | 1.00 | 0 | 0 | 0 |
| intake_air_temperature_sensor_fault | High | owner_safe_rag | 1.00 | 0 | 0 | 0 |
| map_load_signal_plausibility_fault | High | controlled_baseline | 0.82 | 1 | 0 | 0 |
| map_load_signal_plausibility_fault | High | cause_rag | 0.85 | 0 | 0 | 0 |
| map_load_signal_plausibility_fault | High | current_full_rag | 0.85 | 0 | 0 | 0 |
| map_load_signal_plausibility_fault | High | owner_safe_rag | 0.85 | 0 | 0 | 0 |
