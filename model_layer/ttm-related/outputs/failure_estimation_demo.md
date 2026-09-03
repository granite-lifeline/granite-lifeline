# Failure-estimation result

Source risk history: `ttm-related/tests/fixtures/risk_history_rising.csv`.

## Result

- Estimated cycles to High-risk threshold: `4`.
- Threshold-crossing probability within the next 10 trips: `1.0`.
- High-risk threshold: `0.9000`.
- Estimated trend slope: `0.07885714` risk score per trip.

## Method

Each trip is represented by the mean of its detector-window risk scores. A least-squares line is fitted across chronological trips:

```text
r_i = a + b i
```

where `r_i` is trip-level mean risk and `b` is average risk change per trip. If `b > 0`, the point estimate is:

```text
cycles = ceil((High threshold - latest trip risk) / b)
```

The probability is the normal-error-model probability that the linear projection crosses the High threshold within the next 10 trips. It is not a real failure probability.

## Trip-level history

| Cycle | Trip | Mean risk | Windows |
|---:|---|---:|---:|
| 1 | trip_0001 | 0.1900 | 2 |
| 2 | trip_0002 | 0.2700 | 2 |
| 3 | trip_0003 | 0.3400 | 2 |
| 4 | trip_0004 | 0.4200 | 2 |
| 5 | trip_0005 | 0.5050 | 2 |
| 6 | trip_0006 | 0.5850 | 2 |

## Notes

- Failure estimate is a linear projection of trip-level mean risk to the High-risk threshold (0.9000); it is not a calibrated probability of mechanical failure.
- estimated_failure_probability is the model-based probability of crossing that threshold within the next 10 trips.
