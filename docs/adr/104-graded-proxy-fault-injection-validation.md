# ADR 104: Graded Synthetic Fault-Injection Validation for Proxy Checks

## Status

Accepted

## Date

2026-07-24

## Context

The Data Layer defines proxy checks for fault-like OBD-II behaviour, but the source corpus contains healthy driving observations rather than labelled physical failures. Healthy-data evaluation can measure whether the frozen rules remain quiet on available normal data, but it cannot demonstrate that the rules are reachable when their intended abnormal signal patterns occur.

Therefore requires controlled fault injection: selected source signals are modified in copied pipeline runs and the existing proxy stages are rerun to determine whether the expected decision is produced.

The first implementation of the fault-injection runner provided a useful smoke test. It covered 11 proxy sub-checks with one fixed injection specification per case and confirmed that those injected examples reached their expected result states. This established basic end-to-end feasibility, but it was not sufficient as the final validation design because:

- three executable runtime sub-checks were not covered;
- one injected example per case did not demonstrate repeatability across independent trips;
- one fault magnitude did not show boundary or severity behaviour;
- trigger presence alone did not fully validate DTC identity and emission semantics;
- a positive healthy baseline could, in principle, be incorrectly credited to the injection;
- opportunity selection and single-signal intervention controls needed stronger enforcement.

The validation design was therefore revised rather than treating the first smoke-test result as final evidence.

## Decision

The first fault-injection design is superseded by a graded, paired, end-to-end campaign covering all 14 executable runtime sub-checks across the five proxy families.

The second version applies the following rules:

1. **Complete executable coverage:** every runtime sub-check classified as executable in the proxy design is represented by one registered injection case. Designs rejected as non-executable are not converted into artificial runtime verdicts.
2. **Three ordered severity points:** every case contains a mild/control or boundary point, a moderate point, and a strong point appropriate to the physical symptom.
3. **Independent-trip replication:** every severity point is applied to three different `trip_id` values.
4. **Opportunity-window eligibility:** candidate windows must satisfy the target rule's unmodified operating-state, signal-quality, continuity, and confidence guards before injection.
5. **Single-signal intervention:** a case may modify only its declared raw target signal. Guard signals cannot be altered to manufacture eligibility.
6. **Derived-feature recomputation:** features deterministically affected by the modified signal are recomputed within trip and segment boundaries.
7. **Frozen-rule execution:** the registered calibration and proxy thresholds are not refitted. The normal rule-state, event-evidence, duration-evidence, and proxy-decision stages are rerun unchanged.
8. **Healthy/injected pairing:** every injected observation is compared with the equivalent healthy decision so that an existing positive cannot be counted as injection success.
9. **Semantic adjudication:** acceptance checks the scoped result state, expected DTC identity, and whether the decision role should emit or suppress a DTC.
10. **Registered campaign acceptance:** each case must have a non-decreasing detection rate as severity increases and a strongest-severity observed detection rate of at least 0.8.

The completed second-version campaign contains:

| Quantity                       | Count |
| ------------------------------ | ----: |
| Executable sub-check cases     |    14 |
| Severity points per case       |     3 |
| Independent trips per severity |     3 |
| End-to-end injected runs       |    42 |
| Scoped injection observations  |   126 |

All 14 cases met the registered acceptance criteria. Every severity curve was non-decreasing, and every case achieved 3/3 detection at its strongest severity while preserving the expected result-state, DTC, and emission contract.

## Version Evolution

### Version 1: Reachability Smoke Test

The first version covered 11 cases:

- 1-S2 coolant overheating;
- 1-S3 rising-coolant precursor;
- 2-S2 MAF under-read;
- 2-S3b zero MAF while firing;
- 3-S1a pedal-channel mapping offset;
- 3-S1b extreme pedal disagreement;
- 4-S1 frozen IAT in changing context;
- 4-S3 low-range IAT;
- 5-S1 suppressed MAP step response;
- 5-S2 high MAP/MAF residual evidence;
- 5-S3 frozen MAP in changing context.

Each case used one fixed injection specification. All 11 smoke-test cases reached their expected outputs. This version demonstrated that the runner could copy an existing run, modify a target signal, rerun proxy stages, and collect the matching decision.

### Version 2: Graded Validation Campaign

The second version retained the original 11 checks and added the three remaining executable sub-checks:

- 1-S1 slow coolant warm-up;
- 1-S4 cold-start ECT offset;
- 4-S2 cold-start IAT offset.

It also replaced single-example reachability with severity testing, independent-trip replication, healthy-baseline pairing, stricter selector validation, derived-feature recomputation, DTC/emission adjudication, Wilson confidence intervals, and per-case acceptance criteria.

Version 1 remains useful as implementation history, but the project conclusions are based on Version 2.

## Rationale

### Why use synthetic injection?

The available source data does not contain labelled component failures, and intentionally creating physical faults in a vehicle is unsafe and outside the project scope. Synthetic intervention provides a controlled way to test whether the frozen decision logic responds to the signal forms it claims to detect.

This establishes controlled detectability and implementation reachability. It does not establish physical-component causation or real-world recall.

### Why test multiple severities?

A single strong injection can prove only that some extreme value reaches a rule. Three ordered points show whether the detector behaves coherently near its boundary and whether detection is maintained as the fault becomes stronger. This is particularly important for persistence, residual, and context-dependent rules whose response cannot be represented by one scalar threshold alone.

### Why use independent trips?

Repeating overlapping windows in one trip would overstate the amount of independent evidence and could hide dependence on one favourable driving condition. Using three different trips at every severity tests the same rule under multiple naturally occurring contexts.

### Why compare against the healthy baseline?

An injected decision is informative only if the equivalent healthy unit was not already positive. Paired comparison prevents an existing trigger from being misreported as an effect of the injected intervention.

### Why validate DTC and emission semantics?

Not every active proxy row is an independently reportable fault. Verdict rows may emit a DTC, while precursor, support, and arbitration-evidence rows may be active without emission. Checking only whether a row says `triggered` would ignore this distinction and could accept diagnostically incorrect behaviour.

## Alternatives Considered

### Retain the 11-Case Smoke Test as Final Validation

**Rejected.** It demonstrated basic reachability but did not cover all executable checks, replication, severity response, or complete diagnostic semantics.

### Inject Only the Strongest Fault

**Rejected.** Extreme-value reachability provides no evidence about boundary behaviour and can conceal a non-monotonic or overly brittle detector.

### Modify Multiple Signals to Create an Ideal Fault Scenario

**Rejected.** Changing guard and target signals together would make causal interpretation impossible. The campaign would no longer show that the declared source-signal intervention produced the decision.

### Recalibrate Thresholds After Injection

**Rejected.** Refitting against injected data would test a newly adapted rule rather than the frozen production rule and would make the validation circular.

### Count Any Trigger Anywhere in the Run

**Rejected.** A result must be scoped to the injected trip and segment or episode. Otherwise, an unrelated decision elsewhere in the copied run could be incorrectly credited to the intervention.

### Treat Synthetic Detection as Real-World Recall

**Rejected.** Synthetic cases test the implemented signal hypotheses. They do not measure how often real component failures generate those shapes, so they cannot provide field recall or overall diagnostic accuracy.

## Consequences

### Positive

- All executable proxy checks now have controlled end-to-end detectability evidence.
- Severity curves provide stronger evidence than one extreme injection.
- Independent-trip replication reduces dependence on one selected context.
- Paired healthy comparisons prevent pre-existing positives from being counted.
- DTC identity and emission checks validate diagnostic meaning rather than trigger presence alone.
- Frozen calibration preserves separation between rule design and rule validation.
- Machine-readable CSV and JSON outputs support both review and automated regression testing.

### Negative

- The campaign is more complex and computationally expensive than the first 11-case smoke test.
- Three trips per severity provide limited statistical precision even though they satisfy the registered project acceptance rule.
- Selector logic must remain synchronized with the frozen enable conditions of each proxy check.
- Derived-feature recomputation must be updated if a future proxy consumes a new dependency.
- Synthetic signal shapes may not reproduce the coupled behaviour of a physical component failure.

### Mitigation Strategies

- Configuration validation enforces required fields, unique case IDs, allowed strategy/target combinations, severity order, and independent-trip counts.
- Rolling and duration calculations are bounded by `trip_id` and `segment_id`.
- Wilson 95% intervals accompany observed detection proportions to communicate limited sample precision.
- Existing proxy and campaign regression tests protect frozen decision behaviour.
- Conclusions explicitly distinguish healthy-data specificity, synthetic detectability, and unmeasured real-fault recall.

## Implementation

### Configuration

- Case registry: `data_layer/fault_injection/configs/fault_injection_cases.v1.json`
- Frozen calibration: `data_layer/calibration/calibration_registry.v1.json`

### Runner

- Fault-injection runner: `data_layer/fault_injection/src/run_fault_injection.py`
- Methodology: `data_layer/fault_injection/fault_injection_methodology.md`

### Frozen Proxy Stages

- Rule state: `data_layer/proxy_failure/src/50_rule_state_builder.py`
- Event evidence: `data_layer/proxy_failure/src/60_event_evidence_builder.py`
- Duration evidence: `data_layer/proxy_failure/src/61_duration_evidence_builder.py`
- Proxy decisions: `data_layer/proxy_failure/src/70_proxy_decision_builder.py`

### Results

- Observation-level table: `data_layer/fault_injection/outputs/fault_injection_summary_20260724T205415Z.csv`
- Detailed campaign summary: `data_layer/fault_injection/outputs/fault_injection_summary_20260724T205415Z.json`
- Proxy-family Stage-4 conclusions: `data_layer/proxy_failure/proxy_support.md`

### Regression Tests

- Campaign tests: `data_layer/tests/proxy_test/test_fault_injection_campaign.py`
- Proxy-decision tests: `data_layer/tests/proxy_test/test_70_proxy_decisions.py`

## Related Decisions

- ADR 101: Continuity-Aware Data Cleaning and Trip Segmentation
- ADR 201: Residual Detection over Classification
- `data_layer/proxy_failure/proxy_support.md`: proxy definitions, calibration, feasibility, and Stage-4 results
- `data_layer/fault_injection/fault_injection_methodology.md`: complete experimental design and validity limits
