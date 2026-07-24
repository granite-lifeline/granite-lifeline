# Synthetic Fault-Injection Methodology

**Project:** Granite Lifeline
**Layer:** Data Layer
**Status:** Completed experimental validation
**Execution date:** 2026-07-24
**Configuration:** `configs/fault_injection_cases.v1.json`

---

## 1. Purpose and Scope

The fault-injection study evaluates whether the frozen proxy-decision rules respond to controlled, fault-like signal perturbations. The source OBD-II corpus contains healthy driving observations rather than labelled component failures; consequently, Stage 4 tests empirical detectability under synthetic interventions and does not estimate real-world failure prevalence or physical-component recall.

The study covers all 14 executable runtime sub-checks across the five proxy families:

1. cooling degradation;
2. mass-air-flow anomaly;
3. accelerator-pedal sensor disagreement;
4. intake-air-temperature sensor fault;
5. manifold-pressure/load-signal plausibility.

Designs explicitly classified as non-executable in `proxy_support.md` are not converted into artificial runtime verdicts. Their exclusion preserves the distinction between a rejected research design and an executed check returning `not_evaluable`.

---

## 2. Experimental Unit and Campaign Structure

The experimental unit is a scoped proxy decision associated with an injected `trip_id` and, where applicable, a `segment_id` or engine-start episode. Each configured case contains:

- the target proxy and sub-check;
- one declared raw target signal;
- an eligibility selector matching the frozen rule guards;
- an injection transformation;
- three ordered severity points;
- an expected decision state and, where applicable, candidate DTC and emission behaviour.

Each severity point is applied to three independent trips. Multiple trips at the same severity are injected into one copied run and evaluated separately, reducing duplicated pipeline execution without changing decision grain. The completed campaign comprises:

| Quantity                       | Count |
| ------------------------------ | ----: |
| Executable sub-check cases     |    14 |
| Severity points per case       |     3 |
| Independent trips per severity |     3 |
| End-to-end injected runs       |    42 |
| Scoped injection observations  |   126 |

---

## 3. Intervention-Control Principles

### 3.1 Target-signal-only intervention

An injection may modify only its declared source signal. For example, an MAF case may change `maf` but may not alter pedal position, engine speed, operating state, confidence, or quality flags to make the rule easier to trigger. Strategy-specific validation prevents a transformation from declaring one target while internally modifying another.

Derived features are recomputed after intervention because they are deterministic consequences of the modified signal. This distinction is essential: recomputing `speed_density_maf_residual` after changing MAF is valid propagation, whereas changing a guard signal to manufacture eligibility is an uncontrolled multi-signal intervention.

### 3.2 Frozen-rule execution

The calibration registry is loaded read-only. The Stage-4 runner does not fit models, calculate new quantiles, search candidate thresholds, or modify persistence parameters. The same proxy stages used for ordinary runtime decisions are rerun:

```text
production_features
    ↓
50_rule_state
    ↓
60_event_evidence
    ↓
61_duration_evidence
    ↓
70_proxy_decisions
```

### 3.3 Opportunity-window eligibility

Candidate windows must satisfy the target rule's unmodified enable conditions before injection. Examples include:

- post-warm-up state and ambient-domain compliance for overheating;
- high-load, high-confidence operation for MAF under-read;
- naturally steady pedal and RPM conditions for residual evidence;
- material context change for stuck IAT/MAP checks;
- qualified long-gap, first-row engine-off, later observed-start evidence for cold-start support checks;
- state-specific pedal-step thresholds and separable magnitude bins for MAP response events.

The selector retains trip and segment boundaries and does not concatenate separate episodes to obtain the requested duration.

### 3.4 Independent-trip replication

Replicates are selected from different `trip_id` values. This avoids treating overlapping windows from one drive as independent observations and reduces dependence on a single favourable signal context.

---

## 4. Severity Design

Three ordered severity points are used to distinguish threshold behaviour from simple reachability:

- a control, below-boundary, or mild intervention;
- a boundary or moderate intervention;
- a strong intervention.

Severity may be expressed as magnitude, gain, duration, offset, or event count according to the physical symptom:

| Failure form                   | Severity variable                 |
| ------------------------------ | --------------------------------- |
| Temperature level              | injected °C                      |
| Temperature plausibility       | offset from ambient               |
| Sensor gain error              | multiplicative factor             |
| Zero/stuck signal              | duration in seconds               |
| Redundant-channel disagreement | percentage-point offset or delta  |
| Step-response failure          | number of suppressed valid events |

The design expects context-dependent rules such as residual bands to show graded rather than necessarily threshold-exact response. Deterministic physical-range or persistence rules are expected to reproduce their inclusive/exclusive boundaries directly.

---

## 5. Derived-Feature Recalculation

After injection, the runner recomputes all proxy-consumed derivatives affected by the supported target signals, including:

- coolant/ambient and intake/ambient deltas;
- pedal-channel mean, absolute delta, slope, and mapping residual;
- speed-density expected MAF and residual;
- ECT 180-second rate;
- IAT 60-sample stability;
- 120-sample RPM, speed, MAF, and pedal standard deviations;
- MAP 60-sample range;
- 180-second MAF trapezoidal integral.

Rolling operations are grouped by `(trip_id, segment_id)` so that state cannot leak across trip or continuity boundaries. The MAF integral follows the documented 181-endpoint, 180-interval trapezoidal definition rather than a simple rolling sum.

---

## 6. Detection Adjudication

An injected observation is counted as detected only when all applicable conditions are satisfied:

1. the decision is scoped to the injected trip and segment/episode;
2. the injected `result_state` matches the configured expectation;
3. the same scoped healthy decision was not already positive;
4. the candidate DTC matches the expected identity when specified;
5. `dtc_emitted` matches the rule's decision role.

This adjudication distinguishes four runtime roles:

| Decision role            | Active state  | Independent DTC emission        |
| ------------------------ | ------------- | ------------------------------- |
| `verdict`              | `triggered` | Permitted according to the rule |
| `pending_precursor`    | `pending`   | No                              |
| `support`              | `triggered` | No                              |
| `arbitration_evidence` | `triggered` | No                              |

Therefore, a support or arbitration row is not considered correct merely because it contains a candidate label; its non-emission contract must also hold.

---

## 7. Campaign Acceptance Criteria

Each configured case must satisfy all of the following:

1. at least three ordered severity points;
2. at least three independent trips at every severity point;
3. non-decreasing observed detection rate with increasing severity;
4. observed strongest-severity detection rate of at least 0.8;
5. correct result-state, DTC-identity, and emission semantics.

Detection proportions are accompanied by Wilson 95% intervals. These intervals communicate the limited precision of three-trip severity samples; the acceptance decision uses the registered observed-rate criterion rather than treating the interval as a field-recall estimate.

All 14 executable cases satisfied the campaign criteria. The final strongest-severity response was 3/3 for every case, and all severity curves were non-decreasing.

---

## 8. Quality-Control Checks

The implementation applies the following controls:

| Check                                     | Purpose                                                            |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Required-field and unique-case validation | Prevent incomplete or ambiguous case definitions                   |
| Fixed strategy-target validation          | Prevent hidden modification of a different source signal           |
| Auxiliary-guard mutation rejection        | Enforce single-signal intervention                                 |
| Same-trip/segment continuity              | Prevent artificial duration across unrelated data                  |
| Opportunity-count validation              | Fail explicitly when independent eligible windows are insufficient |
| Healthy/injected paired comparison        | Prevent pre-existing positives from being credited to injection    |
| Role and DTC contract validation          | Verify diagnostic semantics, not only trigger presence             |
| Severity monotonicity                     | Detect counter-intuitive loss of response as faults strengthen     |
| Manifest checksum refresh                 | Preserve artifact integrity after controlled modification          |
| Existing-run result collection            | Allow summary recovery without rerunning completed experiments     |
| Unit and proxy regression tests           | Protect campaign helpers and frozen decision behaviour             |

During the campaign, these controls identified and corrected three experimental-design defects:

1. overheating windows selected outside the registered ambient domain;
2. MAP step events selected with a global threshold rather than the frozen state-specific thresholds;
3. a low-severity coolant-rate trajectory whose initial step created an unintended rate artifact.

The affected cases were rerun, and only corrected results were included in the final merged summary.

---

## 9. Reproducibility and Artifacts

The campaign is executed from the repository root:

```powershell
python data_layer/fault_injection/src/run_fault_injection.py `
  --base-run-id recalibrate_20260723
```

Primary versioned inputs:

- `data_layer/fault_injection/configs/fault_injection_cases.v1.json`
- `data_layer/calibration/calibration_registry.v1.json`
- `data_layer/proxy_failure/src/50_rule_state_builder.py`
- `data_layer/proxy_failure/src/60_event_evidence_builder.py`
- `data_layer/proxy_failure/src/61_duration_evidence_builder.py`
- `data_layer/proxy_failure/src/70_proxy_decision_builder.py`

Primary results:

- `outputs/fault_injection_summary_20260724T205415Z.csv`: one row per injected trip-level observation;
- `outputs/fault_injection_summary_20260724T205415Z.json`: observation rows, detectability curves, Wilson intervals, monotonicity checks, healthy-base execution, and acceptance results;
- `data/processed/runs/stage4_*`: copied feature artifacts, recomputed evidence, proxy decisions, and manifests for each injected run;
- `data_layer/proxy_failure/proxy_stage4_report.md`: paste-ready results organised by proxy family.

---

## 10. Interpretation and Validity Limits

The experiment demonstrates that the frozen rules respond consistently to the specified synthetic signal shapes and preserve their decision/DTC contracts. It also establishes boundary behaviour for several deterministic rules and confirms graded context dependence for residual-based rules.

The results must not be interpreted as:

- proof that a physical component caused the injected signal shape;
- an estimate of field failure prevalence;
- a substitute for labelled real-fault recall;
- validation of designs excluded from runtime execution;
- evidence that attribution ambiguity between coupled sensors has been removed.

The Stage-1 to Stage-3 observability, attribution, and maturity limitations remain applicable. Stage 4 adds controlled detectability evidence; it does not change the physical information content of the available OBD-II signals.
