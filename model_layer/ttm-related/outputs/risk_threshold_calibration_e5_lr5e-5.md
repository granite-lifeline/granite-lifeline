# Model risk-threshold calibration (epochs=5, lr=5e-5)

## Decision

- **Low:** score `< 0.4129` — record only.
- **Medium:** score `>= 0.4129` and `< 0.9000` — inspection alarm.
- **High:** score `>= 0.9000` — priority inspection alarm.

The alarm line was selected on the calibration subset by maximising macro F1 while requiring healthy false-positive rate (FPR) <= 10%. The High boundary is a conservative near-maximum-evidence label; it is not a calibrated probability of vehicle failure.

## Selection evidence

- Selected alarm line: `0.4129`.
- Calibration segments (8): trip_0002_seg_001, trip_0008_seg_005, trip_0012_seg_001, trip_0021_seg_001, trip_0025_seg_001, trip_0060_seg_001, trip_0072_seg_001, trip_0078_seg_001
- Held-out segments (3): trip_0010_seg_001, trip_0023_seg_002, trip_0065_seg_001

| Evaluation subset | Alarm line | Macro F1 | Exact hit rate | Healthy FPR | Healthy alarms |
|---|---:|---:|---:|---:|---:|
| Previous policy (all segments) | 0.3000 | 0.533 | 0.455 | 0.273 | 3/11 |
| Calibration subset | 0.4129 | 0.509 | 0.393 | 0.000 | 0/8 |
| Held-out subset | 0.4129 | 0.522 | 0.381 | 0.333 | 1/3 |
| All 11 segments | 0.4129 | 0.521 | 0.390 | 0.091 | 1/11 |

## Important limitation

The selected line meets the 10% healthy-FPR target on the eight calibration segments, but the three held-out segments contain one healthy score of 1.0. Therefore their healthy FPR is 1/3, and no threshold at or below 1.0 can remove that false alarm. This policy is consequently provisional: it makes the choice reproducible, but does not prove real-fault performance or safety suitability.

## Frozen Data Layer registry check

Read-only registry: `data_layer/calibration/calibration_registry.v1.json` (`calibration.v1`, SHA-256 `856998172dc71565b879be97d4a9e737b5ca7c969923bf44b4aec2efa44d2f10`).

The registry was not modified. Its cooling (1-S1/1-S3), MAF (2-S2), and pedal (3-S1a) rules remain the source for the physical evidence features; this Model Layer policy only maps the already-normalised risk score to Low, Medium, or High.

## Reproduction

```bash
.venv/bin/python ttm-related/src/model/risk_threshold_calibration.py
```

The complete candidate-line table is stored in the companion JSON file. No TTM training or synthetic-injection run is performed here.
