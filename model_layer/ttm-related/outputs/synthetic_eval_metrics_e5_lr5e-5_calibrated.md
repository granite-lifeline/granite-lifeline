# GL-322 synthetic-fault evaluation

Alarm threshold: `0.4129`. A hit requires an alarm and the correct anomaly type.

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| cooling_degradation | 33 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| air_intake_maf_anomaly | 2 | 8 | 42 | 0.200 | 0.045 | 0.074 |
| accelerator_pedal_sensor | 25 | 0 | 52 | 1.000 | 0.325 | 0.490 |

Macro F1: **0.521**; micro F1: **0.541**; healthy FPR: **0.091**.

Exact hit rate: **0.390**; attribution accuracy without the alarm threshold: **0.565**.

## Severity response

| Scenario | Runs | Hit rate | Alarm rate | Mean risk |
|---|---:|---:|---:|---:|
| cooling_offset_10c | 11 | 1.000 | 1.000 | 1.000 |
| cooling_offset_15c | 11 | 1.000 | 1.000 | 1.000 |
| cooling_offset_5c | 11 | 1.000 | 1.000 | 0.978 |
| maf_gain_0.70 | 11 | 0.000 | 0.000 | 0.222 |
| maf_gain_0.80 | 11 | 0.000 | 0.000 | 0.222 |
| maf_gain_0.90 | 11 | 0.091 | 0.091 | 0.249 |
| maf_gain_0.95 | 11 | 0.091 | 0.091 | 0.272 |
| pedal_d_offset_10pp | 11 | 0.909 | 1.000 | 0.974 |
| pedal_d_offset_20pp | 11 | 0.909 | 1.000 | 1.000 |
| pedal_d_offset_2pp | 11 | 0.000 | 0.091 | 0.300 |
| pedal_d_offset_5pp | 11 | 0.091 | 0.182 | 0.410 |
| pedal_e_gain_1.05 | 11 | 0.000 | 0.091 | 0.300 |
| pedal_e_gain_1.10 | 11 | 0.091 | 0.182 | 0.308 |
| pedal_e_gain_1.20 | 11 | 0.273 | 0.364 | 0.448 |
