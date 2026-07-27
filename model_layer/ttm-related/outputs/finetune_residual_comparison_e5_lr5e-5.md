# Fine-tuned TTM Residual Comparison

Generated at: `2026-07-20T15:48:05.794724+00:00`

Validation windows: `250`
Validation segments: `12`

| Metric | Zero-shot MAE | Fine-tuned MAE | Improvement |
|---|---:|---:|---:|
| Overall | 58.0004 | 54.9666 | 5.23% |
| rpm | 296.2420 | 279.1437 | 5.77% |
| speed | 16.6351 | 15.7059 | 5.59% |
| coolant_temp | 1.1624 | 1.1586 | 0.33% |
| map | 21.6310 | 21.6636 | -0.15% |
| maf | 10.2556 | 10.1954 | 0.59% |
| tps | 2.0764 | 1.9324 | 6.93% |

## Decision Rule

Fine-tuning is considered beneficial if the overall validation MAE decreases by at least 5% and at least 4 of the 6 model signals do not get worse.

Result: **clear improvement**.
