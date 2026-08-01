# Story 7 evaluation note — Model Layer synthetic-fault detection

## Scope and outcome

This note evaluates the Model Layer's fine-tuned TTM residual detector on
three Model Layer anomaly types:

- `cooling_degradation`
- `air_intake_maf_anomaly`
- `accelerator_pedal_sensor`

The detector reliably identifies the injected cooling scenarios, detects
strong pedal disagreement more often than weak pedal disagreement, and has
very low sensitivity to the current MAF-under-read scenarios.  This is an
evaluation of synthetic perturbations, not evidence of performance on real
vehicle faults.

The other two executable anomaly types are **not Model Layer responsibilities**:
`intake_air_temperature_sensor_or_heat_soak_fault` and
`map_load_signal_plausibility_fault` are determined by the Data Layer's
rule-based proxy decisions and are connected directly by the Data Layer to the
final output.  They are deliberately excluded from the TTM metrics below.

## Model and evaluation design

- Model: official schema-v1 fine-tuned Granite TTM artifact,
  `epochs=5`, `learning_rate=5e-5`, batch size 8.
- Input: held-out validation segments from
  `production_features.csv`; 11 segments were usable and one was skipped
  because it lacked enough post-warmup rows.
- Window: 512 healthy context rows followed by 96 future rows.
- Injection: the future portion only was perturbed using schema-v1-aware
  cooling-offset, MAF-gain-drift, and pedal-channel-disagreement scenarios.
- Hit definition: the detector must raise an alarm and select the injected
  anomaly type. A wrong type is not counted as a hit.

The raw per-window results are in
`synthetic_eval_results_e5_lr5e-5.json`.  The injection functions propagate
changes through the delivered derived features using the frozen Data Layer
feature transforms; they do not encode the detector's decision thresholds.

## Risk-level calibration

The original alarm line was `risk_score >= 0.30`.  A reproducible threshold
sweep over synthetic results selected `risk_score >= 0.4129` as the Medium
(alarm) boundary: it maximises macro F1 among candidate lines with a healthy
false-positive rate (FPR) no greater than 10% on a deterministic
segment-level calibration subset.  `risk_score >= 0.90` is labelled High.

| Risk score | Output level | Action |
|---|---|---|
| `< 0.4129` | Low | Record only; no alarm |
| `0.4129–<0.90` | Medium | Inspection alarm |
| `>= 0.90` | High | Priority inspection alarm |

The policy is stored in `ttm-related/config/risk_level_calibration.v1.json`.
It is separate from, and does not modify,
`data_layer/calibration/calibration_registry.v1.json`: the latter remains the
frozen owner of physical proxy rules and feature transforms.

## How the evaluation numbers are calculated

For one test window, let `s` be the detector's `risk_score`, `y` be the
injected fault type, and `ŷ` be the detector's chosen anomaly type.  The
calibrated alarm decision is:

```text
alarm = 1  if s >= 0.4129
alarm = 0  if s < 0.4129
```

For an injected fault, an **exact hit** requires both an alarm and the correct
type:

```text
exact hit = 1  if alarm = 1 and ŷ = y
exact hit = 0  otherwise
```

For each fault type separately, the counts and metrics are:

| Name | Meaning | Formula |
|---|---|---|
| True positive (TP) | That fault was injected and the system alarmed with the correct type. | `count(alarm = 1 and ŷ = y)` |
| False positive (FP) | The system named this fault type, but it was not the injected type. | `count(alarm = 1 and ŷ = this type and y != this type)` |
| False negative (FN) | That fault was injected but was missed or named as another type. | `count(y = this type and not an exact hit)` |
| Precision | Of the alarms labelled as this type, how many were correct? | `TP / (TP + FP)` |
| Recall | Of the injected cases of this type, how many were found correctly? | `TP / (TP + FN)` |
| F1 | A single number that is high only when both precision and recall are high. | `2 × Precision × Recall / (Precision + Recall)` |

The **healthy false-positive rate (FPR)** answers a different question:

```text
healthy FPR = healthy windows that raised any alarm / all healthy windows
```

For this calibrated result it is `1 / 11 = 0.091`: one of the eleven healthy
segments raised an alarm.  It does **not** mean there is a 9.1% probability of
a real vehicle fault.

The macro F1 gives each of the three Model Layer fault types equal weight,
regardless of how many synthetic cases each has:

```text
macro F1 = (F1cooling + F1MAF + F1pedal) / 3
         = (1.000 + 0.074 + 0.490) / 3
         = 0.521
```

The exact-hit rate is the fraction of all injected cases that were both
alarmed and assigned the correct type:

```text
exact hit rate = 60 exact hits / 154 injected cases = 0.390
```

These formulas define detection performance on this synthetic experiment.
They are not a measure of how often a real car will fail.

## Detection results

The table below reports results on all 11 usable validation segments using the
calibrated `0.4129` alarm line.

| Injected Model Layer type | Precision | Recall | F1 | Interpretation |
|---|---:|---:|---:|---|
| Cooling degradation | 1.000 | 1.000 | 1.000 | All injected cooling cases were identified correctly. |
| MAF anomaly | 0.200 | 0.045 | 0.074 | Most injected MAF-under-read cases were missed. |
| Accelerator pedal sensor | 1.000 | 0.325 | 0.490 | Stronger pedal disagreements were detected more often than weaker ones. |
| **Macro average** | — | — | **0.521** | Equal-weight average across the three types. |

The same results with the underlying counts are shown below, so the fractions
can be checked directly.

| Injected Model Layer type | TP | FP | FN | Precision calculation | Recall calculation |
|---|---:|---:|---:|---|---|
| Cooling degradation | 33 | 0 | 0 | `33 / (33 + 0) = 1.000` | `33 / (33 + 0) = 1.000` |
| MAF anomaly | 2 | 8 | 42 | `2 / (2 + 8) = 0.200` | `2 / (2 + 42) = 0.045` |
| Accelerator pedal sensor | 25 | 0 | 52 | `25 / (25 + 0) = 1.000` | `25 / (25 + 52) = 0.325` |

Additional summaries at the calibrated line:

- Micro F1: **0.541**
- Exact hit rate: **0.390**
- Healthy FPR: **0.091** (1 alarm in 11 healthy segments)

For comparison, the former `0.30` alarm line had macro F1 **0.533**, exact
hit rate **0.455**, and healthy FPR **0.273** (3 alarms in 11 healthy
segments).  Raising the line therefore reduced healthy alarms, but it also
suppressed some weak pedal detections.  This is a stated trade-off, not a
claim of universal improvement.

## Calibration hold-out check

Eight segments selected the alarm line and three segments were held out from
that choice.  The selected line produced no healthy alarms in the calibration
subset, but one of the three held-out healthy segments had `risk_score = 1.0`.
Consequently, held-out healthy FPR was 1/3.  No threshold at or below 1.0 can
remove that particular alarm without disabling every possible detection.

This reveals a remaining detector/scoring problem: changing only the
Low/Medium/High line cannot eliminate all false positives.  The published
policy is therefore explicitly provisional.

## Failure-estimation method and demonstration

`estimated_cycles_to_failure` is a **risk-threshold-crossing projection**, not
a prediction of a physical component's remaining useful life. The estimator
uses the accumulated `risk_history.csv` records across chronological trips.
At least five different trips are required; otherwise both estimation fields
remain `null` and the output explains why.

### Method

First, multiple 96-second detector windows within one trip are converted to a
single trip risk by their arithmetic mean:

```text
r_i = (1 / n_i) × sum(risk_score_i,w), for windows w in trip i
```

This prevents a single noisy window from defining the entire driving cycle.
The chronological trip risks are then fitted by ordinary least squares:

```text
r_i = a + b i
```

where `b` is the estimated mean risk-score increase per driving cycle. When
`b > 0`, the point estimate to the configured High-risk threshold
`T_high = 0.90` is:

```text
estimated_cycles_to_failure = ceil((T_high - r_latest) / b)
```

The estimator does not emit an implausibly distant result: no crossing within
50 future trips is returned as `null`. A flat or decreasing trend (`b <= 0`)
also has no projected crossing cycle.

For uncertainty, the linear-model residuals provide a prediction standard
error at a fixed horizon of 10 future trips. The reported probability is:

```text
P(r_(latest + 10) >= T_high)
= 1 - Φ((T_high - r_hat_(latest + 10)) / SE_prediction)
```

Here `Φ` is the standard normal cumulative distribution function. Therefore
`estimated_failure_probability` means **the model-based probability that the
risk trajectory crosses the High-risk line within 10 trips**. It is not an
empirically measured probability that the vehicle mechanically fails.

### Reproducible synthetic trend result

No real KIT trip sequence contains a labelled degradation-to-failure history,
so the following is an estimator-validation demonstration, not a vehicle
lifetime claim. Six synthetic chronological trips, each with two detector
windows, were supplied to the estimator:

| Cycle | Mean risk |
|---:|---:|
| 1 | 0.190 |
| 2 | 0.270 |
| 3 | 0.340 |
| 4 | 0.420 |
| 5 | 0.505 |
| 6 | 0.585 |

The fitted result is:

```text
b = 0.07885714 risk score per trip
r_latest = 0.585
estimated cycles = ceil((0.90 - 0.585) / 0.07885714) = 4
P(crossing High within 10 trips) = 1.0000
```

The high probability is expected for this deliberately rising synthetic
example. It must not be reported as “100% chance that a real car fails.” The
formal result and the exact synthetic history are
`failure_estimation_demo.{json,md}` and
`tests/fixtures/risk_history_rising.csv`.

## Limitations and responsible interpretation

1. **Synthetic faults only.** The injected perturbations emulate expected
   sensor/process changes but are not labelled real faults. Detection on a
   labelled external fault dataset is required before claiming real-world
   generalisation.
2. **KIT-specific calibration.** The data, feature transforms, and threshold
   experiment are based on the KIT vehicle dataset. They should not be treated
   as calibrated for other vehicles, sensor hardware, or operating conditions.
3. **Incomplete Model Layer coverage.** This note evaluates only the three
   anomaly types owned by the Model Layer. IAT/heat-soak and MAP-plausibility
   decisions come directly from the Data Layer and are out of scope for TTM
   scoring and these metrics.
4. **MAF sensitivity is inadequate.** The present MAF-under-read injection
   design is rarely detected. Improving it requires changes to the evidence or
   risk-scoring logic, not merely a different alarm threshold.
5. **Risk score is not failure probability.** Low/Medium/High describes the
   detector's normalised anomaly evidence. It is not a probability that the
   vehicle will fail, and it must not be used as a safety decision.
6. **Trend projection is not RUL.** The Story 8 estimate assumes a linear
   continuation of trip-level risk. Real degradation can plateau, recover,
   jump, or depend on maintenance and operating conditions; labelled
   degradation-to-failure histories are required for a real RUL model.

## Reproduction

```bash
# Reproduce the threshold selection from the preserved raw results
.venv/bin/python ttm-related/src/model/risk_threshold_calibration.py

# Recompute calibrated metrics without re-running TTM or overwriting baseline metrics
.venv/bin/python ttm-related/src/model/synthetic_evaluation_metrics.py

# Reproduce the synthetic rising-history failure-estimation demonstration
.venv/bin/python ttm-related/src/model/failure_estimation.py \
  ttm-related/tests/fixtures/risk_history_rising.csv \
  --json-output ttm-related/outputs/failure_estimation_demo.json \
  --markdown-output ttm-related/outputs/failure_estimation_demo.md
```

Formal supporting files:

- `risk_threshold_calibration_e5_lr5e-5.{json,md}`
- `synthetic_eval_metrics_e5_lr5e-5_calibrated.{json,md}`
- `synthetic_eval_results_e5_lr5e-5.json`
- `failure_estimation_demo.{json,md}`
