# ADR 201: Residual-Based Anomaly Detection over Classification for Model Layer

## Status
Accepted

## Date
2026-07-22

## Context
The Model Layer (Group 2) integrates IBM Granite TTM (`ibm-granite/granite-timeseries-ttm-r2`)
to detect anomalous engine sensor behaviour from OBD-II time-series data and produce the
interface JSON (`anomaly_type`, `risk_score`, `risk_level`, `key_signals`, ...) consumed by
the Report Layer. The original project brief's suggested architecture recommended starting
with a classical supervised classifier (Logistic Regression / Random Forest) trained against
a proxy failure condition, and only exploring time-series sequence models (e.g. LSTM) as a
later-stage enhancement.

The critical constraint on this choice: the KIT Automotive OBD-II dataset has no real fault
labels. All 81 trips are healthy driving. The only failure-relevant information available is
the Data Layer's (Group 1) proxy failure conditions — physically motivated threshold rules
(e.g. overheating thresholds), not verified real faults. Training a classifier against these
proxy labels and then evaluating detection quality against the same proxy rules would be
circular: the classifier would learn to reproduce the rule rather than detect genuine
physical degradation, and any evaluation against it would not indicate real-world detection
ability.

An early draft design (committed 2026-06-15) followed the brief's suggestion directly:
extract TTM's internal feature embeddings for a window of sensor data and attach a
classifier head to predict a discrete anomaly type. Five days later (commit `dc41e3b`,
2026-06-20) this was replaced with the current design in the residual detector
(`kit_residual_detector.py`): TTM is used zero-shot as a forecaster of
6 signals (`rpm`, `speed`, `coolant_temp`, `map`, `maf`, `tps`) over a 512-step context /
96-step horizon window; the residual between forecast and observed values, normalized
against physically-derived healthy reference ranges and combined with rule-assisted
thresholds, becomes the anomaly signal. No classifier head was ever built.

Three approaches were considered for turning TTM into an anomaly detector.

**Option A — Classifier head on TTM embeddings**: extract TTM's internal feature embeddings
for a window of sensor data and train a lightweight classification head (e.g. a linear layer)
on top, to output a discrete anomaly type directly, per the original draft design.

**Option B — Train a fault-detection sequence model from scratch**: train a custom neural
sequence model (e.g. an LSTM), as suggested by the project brief as a later-stage
exploration, end-to-end on this vehicle's data to learn healthy vs. anomalous patterns
without a pretrained foundation model.

**Option C — Zero-shot residual/forecast-based detection**: use TTM zero-shot purely as a
forecaster of the "normal" continuation of the 6 signals; treat the forecast residual
magnitude, normalized against physically-derived healthy reference ranges, as the anomaly
signal, combined with rule-based physical thresholds for specific components; no training on
fault examples at all.

## Decision
**Option C is selected**: zero-shot TTM forecast-residual detection, later fine-tuned only on
healthy data (Story 6) without changing this underlying paradigm.

## Rationale

### Why not Option A (classifier head on TTM embeddings)?
A classifier head needs fault examples to learn from, and the dataset provides none — all 81
trips are healthy driving. The only available "labels" are Group 1's proxy failure
conditions, which are physically motivated threshold rules rather than verified faults.
Training against these proxy labels and evaluating against the same rules would be circular:
the classifier would learn to reproduce the rule, not detect genuine physical degradation.
The original draft design predates this circularity being fully worked through with Group 1's
proxy definitions.

### Why not Option B (train a sequence model from scratch)?
The project brief itself frames a from-scratch sequence model as a later-stage exploration,
only "once [a simpler approach] works reliably" — not a requirement for the MVP. A
from-scratch model must learn "normal" driving behaviour for this vehicle from a small,
single-vehicle dataset (81 trips) with no pretraining, which is a high risk of
over/under-fitting given the limited data and would delay having any working end-to-end
pipeline for weeks. It offers no advantage over a pretrained foundation model when the goal
is learning "normal" continuation rather than classifying discrete fault categories.

### Why Option C (zero-shot forecast/residual)?
This sidesteps the missing-fault-label problem entirely: a forecasting model only needs
healthy examples to learn "normal", and the dataset has that in abundance. Any deviation
from the model's own prediction shows up as an elevated residual, independent of Group 1's
proxy label definitions. TTM is pretrained on diverse time-series and works zero-shot
immediately, giving a working end-to-end pipeline (data → forecast → residual → risk score →
interface JSON) very early, before any task-specific training. It also keeps evaluation
independent from Group 1's proxy conditions: proxy labels are used only to (a) filter which
segments count as healthy context data, and (b) act as a synthetic fault-injection answer key
for evaluation (Story 7) — never as classifier training targets, avoiding Option A's
circularity. A forecast residual can also flag deviation before a fixed threshold is
crossed, matching the "leading indicator" framing needed for a prediction task, whereas
Options A/B and simple rule thresholds only fire once a value is already out of range.
Fine-tuning was added later (Story 6) but only on healthy data, preserving the same "learn
normal, flag deviation" principle rather than converting the model into a classifier.

## Implementation
The residual detector (`kit_residual_detector.py`) loads
`ibm-granite/granite-timeseries-ttm-r2` zero-shot via `tsfm_public.toolkit.get_model`, with
`DEFAULT_CONTEXT_LENGTH = 512` and `DEFAULT_PREDICTION_LENGTH = 96` over `MODEL_SIGNALS =
["rpm", "speed", "coolant_temp", "map", "maf", "tps"]`. Windows are drawn from a single
segment (`MIN_SEGMENT_ROWS = 700`) so no window crosses a segment boundary. Residuals are
computed as `|prediction - truth|` per signal, summarized as mean/max over the forecast
window, then normalized against per-signal healthy reference ranges (`REFERENCE_RANGES`) and
combined with rule-assisted physical thresholds per anomaly type (`calculate_risk`) to
produce `anomaly_type` (argmax over candidate types), `risk_score`, and `risk_level` (Low
< 0.3, Medium 0.3–0.7, High > 0.7). Confidence is derived only from residual-based scores;
rule-only scores (e.g. the pedal score) are explicitly excluded from the confidence
calculation.

## Consequences

### Positive
- Workable without any fault-labelled data, matching the actual constraints of this project.
- Detection is evaluation-independent from Group 1's proxy definitions, avoiding circular
  validation.
- Fast initial iteration: zero-shot from day one, no training bottleneck for the MVP.
- Extends naturally to fine-tuning (Story 6) without changing the core detection paradigm.

### Negative
- Cannot directly output a calibrated fault probability the way a trained classifier could;
  `risk_score` is a residual-derived heuristic combined with rule thresholds, not a learned
  probability.
- Requires physically-derived reference ranges and rule thresholds per anomaly type to
  translate raw residuals into meaningful risk — an added domain-knowledge burden compared to
  a classifier that learns thresholds implicitly.
- Multiple scoring paths per anomaly type (including still-pending types) add complexity
  relative to a single classifier output.
- Evaluation still ultimately depends on Group 1's proxy definitions and synthetic fault
  injection (Story 7) rather than real-world validated faults — the missing-label problem is
  avoided for training but not eliminated for evaluation.

### Mitigation
Evaluation uses synthetic fault injection (Story 7) as an independent check rather than the
same proxy thresholds used for healthy-segment filtering, keeping some separation between
"what counts as healthy context" and "what counts as a detected fault" even though both trace
back to Group 1's physical proxy work.

## Related Decisions
- The tps-driven removal of `electronic_throttle_tracking_fault` (July 2026) — a downstream
  anomaly-type-scope decision within this same residual-detection architecture.
- `INTERFACE.md` — the shared contract defining `anomaly_type`, `risk_score`, and
  `risk_level`.

## References

- Original project brief (Predictive Model recommendation).
- Internal team notes on design rationale (Q1, Q2, Q3a/Q3b).
- Early draft design materials (superseded classifier-head architecture, June 2026).
- `kit_residual_detector.py` — current implementation.
