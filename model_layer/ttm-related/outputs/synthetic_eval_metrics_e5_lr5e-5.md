# GL-322 synthetic-fault evaluation

Alarm threshold: `0.3`. A hit requires an alarm and the correct anomaly type.

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| cooling_degradation | 33 | 7 | 0 | 0.825 | 1.000 | 0.904 |
| air_intake_maf_anomaly | 2 | 11 | 42 | 0.154 | 0.045 | 0.070 |
| accelerator_pedal_sensor | 35 | 0 | 42 | 1.000 | 0.455 | 0.625 |

Macro F1: **0.533**; micro F1: **0.579**; healthy FPR: **0.273**.

Exact hit rate: **0.455**; attribution accuracy without the alarm threshold: **0.565**.

## Severity response

| Scenario | Runs | Hit rate | Alarm rate | Mean risk |
|---|---:|---:|---:|---:|
| cooling_offset_10c | 11 | 1.000 | 1.000 | 1.000 |
| cooling_offset_15c | 11 | 1.000 | 1.000 | 1.000 |
| cooling_offset_5c | 11 | 1.000 | 1.000 | 0.978 |
| maf_gain_0.70 | 11 | 0.000 | 0.091 | 0.222 |
| maf_gain_0.80 | 11 | 0.000 | 0.091 | 0.222 |
| maf_gain_0.90 | 11 | 0.091 | 0.182 | 0.249 |
| maf_gain_0.95 | 11 | 0.091 | 0.182 | 0.272 |
| pedal_d_offset_10pp | 11 | 0.909 | 1.000 | 0.974 |
| pedal_d_offset_20pp | 11 | 0.909 | 1.000 | 1.000 |
| pedal_d_offset_2pp | 11 | 0.000 | 0.273 | 0.300 |
| pedal_d_offset_5pp | 11 | 0.909 | 1.000 | 0.410 |
| pedal_e_gain_1.05 | 11 | 0.000 | 0.273 | 0.300 |
| pedal_e_gain_1.10 | 11 | 0.182 | 0.273 | 0.308 |
| pedal_e_gain_1.20 | 11 | 0.273 | 0.364 | 0.448 |
