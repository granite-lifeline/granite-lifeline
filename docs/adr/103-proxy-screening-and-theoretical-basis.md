# ADR 103: Proxy Failure Screening and Theoretical-Basis Collection

## Status

Accepted

## Date

2026-07-19

## Context

The Data Layer needs to detect fault-like OBD-II behaviour, but the KIT corpus contains only healthy driving and no labelled physical failures. There is therefore no ground truth against which a detector could be trained or scored directly. The available substitute is a set of physically motivated proxy checks — threshold-and-persistence rules over cleaned signals and operating-condition state (ADR 101, ADR 102) that fire on the signal shapes a real failure would be expected to produce.

The difficulty is deciding which candidate checks are worth executing. A physically plausible symptom is not automatically a usable detector on this dataset: the signal may not be observable at the required resolution, the healthy corpus may contain no opportunity window to calibrate against, a zero-healthy-trigger rule may be structurally inert rather than validated, or the reference value the rule needs may simply not exist in the data (for example a commanded idle target, or a trustworthy throttle-position channel). A candidate can also be defensible in the literature yet impossible to freeze here without borrowing brand-specific calibration values that do not apply to this vehicle.

The Data Layer consequently needs a principled screening process that turns a catalogue of candidate failure symptoms into a small, defensible set of executable proxy checks, records the theoretical basis for each judgment form, and documents why the rejected candidates are not executed — so that a later validation stage (ADR 104) tests only rules that were meant to run, and so that "not executed" is never confused with "ran and found nothing".

## Decision

The Data Layer adopts a staged screening and theoretical-anchoring process for proxy checks, with a two-document contract separating executable rules from research derivation:

1. **Two-document contract.** `proxy_failure_definition.md` is the authoritative, implementation-facing specification of the executable proxies for the current freeze cycle (the 2026-07-19 contract revision): component, consumed signals, definition, final decision rules, required guards, coverage, key calibration evidence, and known limitations. `proxy_support.md` is the research and audit companion that retains observability derivations, literature anchoring, candidate selection and rejection paths, sensitivity/validation detail, and the completed empirical-falsifiability record. Final rules must be read from the definition document; the support document must not be read as rules.

2. **Four-stage screening per candidate.** Every candidate sub-check passes through: Stage 1 observability derivation (can the symptom be observed in this signal set, and in which enable window); Stage 2 literature anchoring (which vehicle-independent judgment form the check borrows, and from where); Stage 3 calibration and selection audit (pre-registered census against the healthy baseline, freeze/downgrade/infeasible decision); and Stage 4 empirical falsifiability (synthetic fault-injection reachability — governed by ADR 104). A candidate becomes an executable proxy only if it survives Stages 1–3 as an executable, frozen rule.

3. **Literature contributes forms, not values.** Cited sources contribute vehicle-independent judgment *forms* and enable-window structure. Every absolute threshold is either baseline-derived from this dataset's healthy distribution, or a regulatory allowance adopted only as an evaluability guard. No brand-specific calibration value from any source is adopted as a threshold.

4. **Executability gate.** Only frozen or explicitly executable rules produce runtime rows. Designs that are downgraded, documented-infeasible, removed, or descriptive produce no runtime rows, result states, or DTCs. `not_evaluable` is an outcome of an *executed* check whose guards or domain were not satisfied; it must never be used to represent a design that is not executed at all.

5. **Pre-registered calibration discipline.** Branch structures and orderings are pre-registered before results are seen; parameters must not hug the edge of the healthy envelope; out-of-calibration-domain inputs return `not_evaluable`; and any in-sample adjustment is disclosed. Frozen calibration values live in a versioned calibration registry and are never re-fitted on user-uploaded data.

6. **Decision roles and emission separation.** Every runtime row carries a `decision_role` of `verdict`, `pending_precursor`, `support`, or `arbitration_evidence`, and a `result_state` of `pass`, `triggered`, `not_evaluable`, or `pending` as permitted by that role. A `dtc_candidate_label` identifies the relevant diagnostic family but does not authorize emission: support and arbitration-evidence rows always set `dtc_emitted = false`, and only final routing determines whether a permitted verdict row emits a DTC.

7. **Resulting executable set.** The screening yields 14 executable runtime sub-checks across five proxy families, together with a documented set of non-executed designs and one family found infeasible in full.

The executable set is:

| Family | Executable sub-checks | Roles / candidate DTCs |
| ------ | --------------------- | ---------------------- |
| 1. cooling_degradation | 1-S1 slow warm-up; 1-S2 overheating; 1-S3 rising-without-plateau; 1-S4 cold-start ECT plausibility | verdict P0128; verdict P0217; pending_precursor (no independent DTC); support P0116 |
| 2. air_intake_maf_anomaly | 2-S2 high-load under-read; 2-S3b zero MAF while firing | verdict P0101 candidate; verdict P0102 |
| 3. accelerator_pedal_sensor | 3-S1a channel-relation residual; 3-S1b extreme disagreement | verdict P2138; verdict P2138 high tier |
| 4. intake_air_temperature_sensor_fault | 4-S1 stuck/no-response; 4-S2 cold-start IAT plausibility; 4-S3 physical range | verdict P0111; support P0111; verdict P0112/P0113 |
| 5. map_load_signal_plausibility_fault | 5-S1 step response; 5-S2 steady-state residual; 5-S3 stuck MAP | verdict P0106; arbitration_evidence (no independent DTC); verdict P0106 |

The non-executed designs, retained only as research/audit records, are:

| Design | Status | Reason |
| ------ | ------ | ------ |
| 2-S1 MAF/MAP cohesion band | Downgraded | No operating state met the healthy-episode margin and coverage requirements; retained as descriptive corroboration only. |
| 2-S3a stuck MAF | Documented infeasibility | No healthy joint opportunity with both material context change and a 60-s exactly flat MAF; a zero-trigger rule would be structurally inert. |
| 3-S2 single-channel pedal freeze | Documented infeasibility | Short persistence produced healthy triggers or inadequate margin; longer persistence collapsed opportunity coverage (7/66 and 3/66 trips). |
| 3-S3 pedal channel-noise burst | Downgraded | Healthy episodes remained under both quiet gates despite full coverage; no standalone noise threshold could be frozen. |
| 4-S4 post-high-load IAT heat-soak | Removed | No corresponding DTC, does not isolate a sensor fault, no frozen persistence rule; S1/S2/S3 already cover the executable IAT definition. |
| 6. idle_speed_control_or_surge_degradation (family) | Documented infeasibility | No PID exposes the commanded idle target; the required 70-s persistence exists in only 1.5–9.1% of trips; and no engine-specific nominal-idle data sheet was obtained. |

A related screening outcome is that `electronic_throttle_tracking_fault` is not defined as a proxy: the `tps` channel is saturated near 83.1–83.5% across operating states with long stretches of zero rate of change, so no trustworthy throttle-position observation is available and pedal demand is used as the substitute trigger where a throttle-model input would otherwise be needed.

## Rationale

### Why separate the definition and support documents?

An implementation-facing team needs a single, unambiguous specification of what runs, while an auditor needs the full derivation, rejected branches, and sensitivity analysis behind each rule. Combining both in one file makes it easy to read a rejected candidate or a superseded threshold as if it were an active rule. The split keeps `proxy_failure_definition.md` as the one executable specification and moves all research history to `proxy_support.md`, with each executable proxy cross-linked to its audit section.

### Why derive observability before choosing a rule?

A proxy is only meaningful if the failure symptom is observable in the available signal set and in a specific enable window. Deriving observability first forces each check to name its reference (a physical model, a redundant channel, or a parallel estimator) and its enable window before any threshold is chosen. This is what surfaces cases where a symptom is real but unobservable at 1 Hz integer resolution, or observable only against *changing* context — for example a stuck signal is detectable only when the surrounding context is moving, otherwise a legitimately flat healthy signal is indistinguishable from a fault.

### Why treat literature as forms rather than values?

The cited standards, handbooks, and patents describe diagnostic architectures for other vehicles and platforms. Their numeric calibrations are platform-specific and would be wrong here. Borrowing only the vehicle-independent judgment form (for example "warm-up target is defined relative to the regulating temperature", or "declare a fault only after a persistence counter") while deriving every absolute threshold from this dataset's own healthy baseline keeps the rules both defensible and correctly calibrated. Regulatory values are adopted only as evaluability guards, never as verdict thresholds.

### Why the executability gate and the `not_evaluable` distinction?

The validation stage (ADR 104) must test only rules that were intended to run. If a non-executed design could emit `not_evaluable`, it would appear in runtime output as if it were a live check that merely lacked an opportunity, blurring the line between "we chose not to run this" and "this ran and could not decide". Restricting `not_evaluable` to executed checks, and giving non-executed designs no runtime footprint at all, keeps that distinction clean and auditable.

### Why decision roles and DTC-emission separation?

Not every active proxy row is an independently reportable fault. A precursor may indicate an early-stage condition without confirming it; a support row may provide sensor-trust evidence; an arbitration-evidence row may show a disagreement that cannot by itself identify the faulty sensor. Encoding these as distinct `decision_role` values, and separating the candidate DTC label from actual emission, prevents a row that merely says `triggered` from being mistaken for a confirmed, emittable diagnosis.

### Why pre-register the calibration?

Because the corpus is healthy-only, a rule can trivially achieve zero healthy false positives by sitting above the healthy envelope — which demonstrates specificity by construction but says nothing about detection capability. Pre-registering branch orderings and margin/coverage criteria before seeing results, and disclosing any in-sample adjustment, prevents thresholds from being quietly tuned to the healthy data and makes the freeze decision honest about what it has and has not shown.

## Alternatives Considered

### Adopt Literature or OEM Threshold Values Directly

**Rejected.** The numeric calibrations in the cited standards, handbooks, and patents are platform-specific and do not apply to this vehicle. Adopting them would produce rules that are neither calibrated to this dataset nor honestly attributable to the source. Only vehicle-independent judgment forms are borrowed; absolute thresholds are baseline-derived or used as regulatory guards.

### Execute Every Candidate Sub-check

**Rejected.** Several candidates cannot be frozen into a valid detector on this dataset: some have no healthy opportunity window to calibrate against, some would be structurally inert (a zero-trigger rule with no separating evidence), and some produce healthy triggers at any usable persistence. Executing them anyway would add runtime rows with no evidentiary value and would misrepresent research-grade or infeasible designs as live checks.

### A Single Combined Proxy Document

**Rejected.** Merging executable rules with research derivation invites reading rejected branches, superseded forms, or descriptive statistics as active rules. Separating the authoritative definition from the research support keeps a single executable specification and preserves the audit trail without contaminating it.

### Build a `tps`-based Throttle-Tracking Proxy

**Rejected — signal unusable.** The `tps` channel is saturated near 83.1–83.5% across operating states and shows long stretches of zero rate of change, with no physically plausible correlation to pedal, MAP, MAF, or RPM. No trustworthy throttle-position observation can be recovered, so `electronic_throttle_tracking_fault` is not defined and accelerator-pedal demand substitutes for the throttle-model input where one is needed. `tps` is retained only as raw diagnostic context.

### Include an Idle-Speed Control Proxy

**Rejected — documented infeasibility.** No PID exposes the ECU-commanded idle target, the healthy released-idle population is legitimately multi-modal, the required persistence is available in too few trips, and no engine-specific nominal-idle data sheet was obtained. No idle sub-check can support a DTC-level verdict on this dataset, so the family produces no runtime rows and is retired from the anomaly enum.

## Consequences

### Positive

- The Data Layer ships a small, defensible set of 14 executable proxy sub-checks, each with a stated observability basis, borrowed judgment form, and baseline-derived calibration.
- The definition/support split gives implementers one unambiguous specification and auditors a complete derivation and rejection trail.
- The executability gate and role/emission model make runtime output interpretable: verdicts, precursors, support, and arbitration evidence are distinguishable, and non-executed designs leave no misleading footprint.
- Pre-registered calibration discipline keeps freeze decisions honest about specificity-by-construction versus demonstrated capability, and sets up ADR 104 to test only intended rules.
- Baseline-derived thresholds and regulatory-guard-only usage keep the rules calibrated to this vehicle while remaining traceable to established diagnostic forms.

### Negative

- The proxies establish physically motivated, controlled-detectability evidence only; because the corpus is healthy, they do not establish real-world fault recall.
- Several plausible symptoms (stuck MAF, single-channel pedal freeze, idle-speed control, throttle tracking) yield no executable detector on this dataset, so coverage of the failure space is deliberately incomplete.
- Thresholds and enable windows are tied to this dataset's healthy distribution and to its 1 Hz integer resolution, and would need re-freezing on a different corpus.
- Maintaining two synchronized documents plus a versioned calibration registry adds process overhead.

### Mitigation Strategies

- Every executable proxy links to its `proxy_support.md` audit section, and non-executed designs are recorded with an explicit final status and reason rather than silently dropped.
- Frozen calibration values are held in a versioned registry and are prediction-only in production — never re-fitted on user data.
- Capability claims are deferred to ADR 104's synthetic fault-injection campaign, and the limitation that synthetic detectability is not real-fault recall is stated explicitly.
- Reintroducing any non-executed design requires a new scope decision plus, where a detector is proposed, new evidence and a pre-registered calibration/freeze decision.

## Implementation

### Specification and Research Documents

- Authoritative executable rules: `data_layer/proxy_failure/proxy_failure_definition.md`
- Research and audit support: `data_layer/proxy_failure/proxy_support.md`

### Frozen Proxy Stages

- Rule state: `data_layer/proxy_failure/src/50_rule_state_builder.py`
- Event evidence: `data_layer/proxy_failure/src/60_event_evidence_builder.py`
- Duration evidence: `data_layer/proxy_failure/src/61_duration_evidence_builder.py`
- Proxy decisions: `data_layer/proxy_failure/src/70_proxy_decision_builder.py`

### Calibration Records

- Frozen calibration registry: `data_layer/calibration/calibration_registry.v1.json`
- The Stage 3 evidence behind each freeze/downgrade/infeasibility decision comes from pre-registered per-family censuses (observability derivations, candidate grids, margin/coverage criteria, and sensitivity checks). These census artefacts are maintained separately and are not part of this repository; their results and conclusions are recorded in `proxy_support.md`.

### Runtime Output Contract

Every executed row records `proxy_id`, `sub_check_id`, `direction`, `decision_role`, `result_state`, `decision_reason`, `decision_margin`, `dtc_candidate_label`, and `dtc_emitted`, plus routing, confidence, and provenance where applicable. The executable `anomaly_type` families here correspond to the five-type enum confirmed in `docs/INTERFACE.md` v1.x.

## Related Decisions

- ADR 101: Continuity-Aware Data Cleaning and Trip Segmentation — supplies the cleaned, segmented signals and quality provenance the proxies consume.
- ADR 102: Hierarchical Operating-Condition State Machine and Stratified Analysis — supplies the thermal and kinematic enable windows the proxy rules are written against.
- ADR 104: Graded Synthetic Fault-Injection Validation for Proxy Checks — the Stage 4 empirical-falsifiability campaign that validates the 14 executable sub-checks defined here.
- ADR 201: Residual Detection over Classification — the Model Layer avoids training against these proxy labels, using them only for healthy-context filtering and as a synthetic evaluation key.
- `docs/INTERFACE.md`: cross-layer contract; §2.3/§2.4 record the five-type `anomaly_type` enum and the removal of the throttle and idle families.

## References

Theoretical-basis sources collected during screening (judgment forms borrowed; absolute values baseline-derived or used as regulatory guards):

- SAE J2012 — Diagnostic trouble code definitions (DTC identities only: P0128, P0217, P0116, P0101/P0102, P2138, P0111/P0112/P0113, P0106).
- Bosch Automotive Handbook (10th ed.) — physical basis for cooling, air-mass measurement, MAP load monitoring, and ETC dual-sensor redundancy.
- California Air Resources Board, Title 13 CCR §1968.2 (OBD II), sections (e)(10) and (e)(15) — monitoring mandate, two-sided rationality form, enable-window and guard structure (design precedent, not applicable law).
- SAE 2000-01-0939; SAE 2007-01-2570 — model-based expected-warm-up architecture and overheating phenomenology (cooling S1/S2/S3).
- Nyberg & Nielsen (SAE 970209); intake-system fault-isolation patent US6701282 — model-based MAF/MAP two-estimator cross-check.
- Ford US6463892; Toyota US6200021; Ford 2019 MY OBD System Operation Summary — S2/S3 judgment architecture, heat-input gating, and production-practice confirmation.
- Delphi US7120535 — IAT stuck/response-failure detection architecture.
- ISO 26262-5:2018 — functional-safety framework for redundant sensing (pedal dual-channel).
- SAE J1979 — OBD-II PID physical bounds (intake air temperature −40…215 degC, used by 4-S3).
- Wang et al. (2021), E3S Web of Conferences — OBD function test / cold-soak methodology.
