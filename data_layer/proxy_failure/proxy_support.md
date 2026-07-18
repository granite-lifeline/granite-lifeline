# Proxy Failure Research Support

## Intro

Research and audit companion to the authoritative [`proxy_failure_definition.md`](proxy_failure_definition.md). This document preserves observability derivations, literature anchoring, pre-registration decisions, candidate selection and rejection paths, sensitivity/validation detail, and the open Stage 4 fault-injection work. Final implementation rules must be read from the definition document.

## Structure

For each executable proxy this document retains:

* Observability derivation
* Literature anchoring
* Calibration, candidate-selection, sensitivity, and rejection audit
* Empirical falsifiability (Stage 4)

The formal component, support-signal contract, definition, final rules, guards, coverage summary, key evidence, and limitations are maintained in [`proxy_failure_definition.md`](proxy_failure_definition.md).  

## Shared Conventions

**Output schema (all proxies):** every sub-check reports three states — `pass` / `triggered` / `not_evaluable` — as `proxy_id + sub_check_id + direction + DTC label`, aggregated to proxy level. Guards and domain failures produce `not_evaluable`, never a verdict. Duration-gated checks record a `decision_margin` (with 1 Hz integer signals, margins within ~±5 s are borderline by resolution).

**Empirical-falsifiability protocol (Stage 4, all proxies):** TBD-1 synthetic injection onto held-out healthy windows, target signal only; TBD-2 detectability curve (detection rate vs. graded severity); TBD-3 false-positive rate on held-out healthy trips (split by `trip_id`, per §5.3 leakage rules); TBD-4 acceptance criteria set jointly after the first TBD-2/3 run — Stage 3 thresholds may be revised once, then re-frozen.

**Calibration discipline:** pre-registered branches and orderings; no edge-hugging parameters; out-of-calibration-domain → `not_evaluable`; literature contributes vehicle-independent judgment forms — absolute values are baseline-derived, or regulatory defaults used only as guards.

## Note — Non-Executed Sub-checks

The following sub-checks were evaluated through the pre-registered data-analysis process and found unsuitable for execution. They are retained in this document only as research and audit records. They are intentionally excluded from [`proxy_failure_definition.md`](proxy_failure_definition.md), are not part of the runtime decision pipeline, and must not produce a verdict or DTC.

| Sub-check | Final status | Why it is not executable | Runtime treatment |
|---|---|---|---|
| `2-S1` — MAF/MAP cohesion band | Downgraded | No operating state simultaneously met the registered healthy-episode margin and opportunity-coverage requirements. The cohesion measure cannot support a calibrated standalone band on this dataset. | Do not calculate for verdict use; research/descriptive corroboration only. |
| `2-S3a` — Stuck MAF | Documented infeasibility | The healthy corpus contains no joint opportunity with both material context change and a 60-s exactly flat MAF signal. A zero-trigger rule would therefore be structurally inert rather than validated. | Do not execute; the 60-s rolling-range statistic may remain in offline research only. |
| `3-S2` — Single-channel pedal freeze | Documented infeasibility | Short persistence produced healthy triggers or inadequate duration margin; longer persistence reduced opportunity coverage to 7/66 trips in one direction and 3/66 in the other. | Do not execute; both directions have no P2138 verdict. |
| `3-S3` — Pedal channel-noise burst | Downgraded | Healthy 5-s and 10-s high-`delta_std_10s` episodes remained under both quiet gates despite 66/66 opportunity coverage, so no standalone noise threshold could be frozen. | Do not execute for verdict use; offline descriptive corroboration only. |
| `4-S4` — Post-high-load IAT heat-soak observation | Removed from the failure definition | The observation has no corresponding DTC, does not isolate an IAT sensor fault, and lacks a frozen persistence rule. S1/S2/S3 already cover the executable IAT failure definition. | Research observation only; no runtime computation, verdict, engineering flag, or DTC. |

These are final non-execution decisions for the current cycle, not unfinished implementation tasks. Reintroducing any item requires a new scope decision and, where a detector is proposed, new evidence plus a pre-registered calibration/freeze decision.


## 1. cooling_degradation

[Authoritative definition and final rules](proxy_failure_definition.md#1-cooling_degradation)

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** The cooling system prevents thermal overload, lubricating-oil burn-off, and abnormal combustion caused by excessive component temperatures. Coolant and engine temperatures need to remain stable within a narrow range. If the temperature stays above the stable post-warm-up range for an extended period, heat input and heat dissipation capacity are out of balance. [4]

**Observability argument.** The thermal state of the cooling system is observable only through `coolant_temp` relative to its physical references — ambient temperature, elapsed running time, and heat input implied by `rpm`/`speed`. Different failure symptoms are observable in **different thermal windows**, so this proxy carries three distinct enable windows rather than one: the warm-up phase (slow warm-up is observable only before the plateau), the post-warm-up phase (overheating and plateau-loss are observable only after regulation begins), and the segment start after a cold soak (sensor plausibility is observable only before engine heat propagates).

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| S1 | Slow warm-up — heat retention insufficient (thermostat stuck open) | time-to-temperature; `coolant_slope` over the warm-up phase | `warmup`, from engine start | P0128 (P0125/P0126 as consequence codes) |
| S2 | Overheating — heat dissipation insufficient | `coolant_temp` above critical band, duration-gated | `post_warmup` | P0217 |
| S3 | Rising without plateau — regulation lost | sustained positive `coolant_slope` after warm-up | `post_warmup` | P0217 family (early stage) |
| S4 | ECT implausible at cold start | `coolant_ambient_delta` at segment start after qualified cold soak | cold-soak segment start | P0116 |

**Ambient compensation note.** Warm-up duration scales with ambient temperature (corroborated independently by the Leon owner's manual, p. 112: the warm-up phase "also depends on the outside temperature"). S1's expected duration must therefore be conditioned on `ambient_temp` at engine start — **Resolved: binning/lookup form, per [13] ((e)(10.2.1)(C), (e)(10.2.2)(B)(ii)) — see Stages 2–3.**

#### Stage 2 — Literature Anchoring (S1–S3 anchored; remaining TBD: Bosch 10th-edition page references)

*Each source is annotated with what is borrowed from it. Rule: literature contributes vehicle-independent judgment **forms**; every absolute value is either a regulatory allowance adopted as a guard default, or baseline-derived. No brand-specific calibration values are adopted anywhere.*

- Bosch Automotive Handbook [4] — **Borrowed: physical basis only; no thresholds.** Cooling-system function (prevention of thermal overload, lubricating-oil combustion, uncontrolled combustion from excessive component temperatures) and the requirement that coolant/engine temperature be regulated within a narrow range — supports the first two sentences of the Monitored-function paragraph (the heat-input/dissipation-balance inference is project reasoning, not [4]). The thermostat-regulation passage additionally grounds the plateau concept (S3) and the stuck-open mechanism (S1), and establishes that map-controlled thermostats have a **condition-dependent** regulating temperature — the reason `T_reg` must be estimated from the project baseline rather than quoted as a nominal constant. Verified verbatim in the web-capture edition, pp. 736 ("Cooling") and 771–772 ("Regulation of coolant temperature"); **TBD: 10th-edition page references.**

- CARB Title 13 CCR §1968.2, section (e)(10) [13] — **Borrowed: vehicle-independent judgment forms and enable-window structure; no absolute temperatures.** Cited as design precedent (US light-duty gasoline OBD II), not as law applicable to this Euro-market vehicle.
  - (e)(10.1.1) mandates thermostat monitoring → grounds S1's existence.
  - (e)(10.2.1)(A): malfunction = coolant fails, within a manufacturer-calibrated time after engine start, to reach (i) the highest enable temperature required by other diagnostics, or (ii) a warmed-up temperature within 20°F (11°C) of the nominal thermostat regulating temperature → **threshold form `T_target = T_reg − 11°C`**, defined relative to the vehicle's own regulating temperature; `T_reg` itself is baseline-derived here.
  - (e)(10.2.1)(C), (e)(10.2.2)(B)(ii): compensation expressed as a function of temperature at engine start, with binned time budgets → **ambient compensation in binning/lookup form** (closes Stage 1's binning-vs-regression TBD); bin edges and per-bin budgets are baseline-derived.
  - (e)(10.3.1)(B)/(C): low-ambient disablement (ambient at start below 20°F/−7°C) and no-call under false-diagnosis conditions (hot restart; the regulation's own example of idle exceeding 50% of warm-up time) → **enable-window guard structure**. The guard values are regulatory allowances/examples, not physical constants: adopted as defaults, they affect evaluability only (never a verdict), and their sensitivity is checked in Stage 4.
  - (e)(10.1.2), (e)(10.2.2)(C): ECT rationality and stuck-in-range mandates → regulatory umbrella for S4; the stuck-in-range clause ("to the extent feasible") documents why a frozen-ECT sub-check is deferred rather than implemented (current features cannot separate a frozen signal from a normal integer-resolution plateau; feature redesign required).

- SAE 2000-01-0939 [10] — **Borrowed: model-based expected-warm-up architecture (vehicle-independent method); no calibration values.** Engine-coolant-temperature model for cooling-system/ECT diagnosis; demonstrates observability of slow warm-up and cold-start rationality faults through modeled-vs-measured ECT. Primary methodological support for S1 and S4, and the v2 upgrade path for S1 (heat-input budget in place of wall-clock budget).

- SAE 2007-01-2570 [11] — **Borrowed: failure phenomenology only; no thresholds.** Experimental overheating study showing that cooling-system degradation produces sustained coolant-temperature rise and loss of thermal regulation → supports S2/S3's symptom split (level check vs. trend check).

- Ford 2019 MY OBD System Operation Summary, "Thermostat Monitor" [14] — **Borrowed: production-practice confirmation of the architecture; all numeric calibrations therein are platform-specific and are NOT adopted.** Confirms in production: the once-per-driving-cycle single-decision structure with early pass on reaching target; the idle/low-load no-call guard (CARB's example implemented in practice); ambient-conditioned expected-time lookup; and a model-based (engine speed/load combustion-heat) warm-up reference consistent with [10].

- Ford patent US6463892B1 [15] — **Borrowed: the S2/S3 judgment architecture; no numeric values.** A thermodynamic model estimates expected coolant temperature from heat input; measured ECT is compared against it in two regions, split at the thermostat opening temperature. Agreement below / disagreement above → thermostat stuck **closed** (the failure mechanism behind overheating — S2). Disagreement below / agreement above → stuck **open** (S1). Disagreement in both → ECT **sensor** fault (supports the attribution language and the frozen-ECT deferral). A fault is declared only after a continuous counter reaches a calibrated count — the persistence-gating precedent for S2/S3 duration requirements.

- Toyota patent US6200021B1 [16] — **Borrowed: heat-input gating and start-temperature conditioning; no numeric values.** Judgment is enabled only once accumulated heat generation since engine start (implemented as accumulated intake-air amount) exceeds a reference that decreases with the start coolant temperature. Direct production precedent for S1's cumulative-MAF heat-input guard and its start-condition scaling. Its dual-estimator gating (separate expected temperatures under assumed-normal and assumed-faulty operation, each gating one decision direction) is the anti-false-call structure S2/S3 inherit.

- Hyundai patent US10934924B1 [17] — **Borrowed: one magnitude anchor only; a control patent, not a diagnostic one.** A modern thermal-management strategy treats ~110–115°C as the upper edge of intended coolant operation ("engine coolant temperature of about 110° C. to 115° C. or more is set to a coolant temperature threshold"). Evidence of where "high" begins on a current engine — not a fault threshold.

- Nissan patent US4401848A [18] — tertiary example only: a 1980 voice-warning patent that announces overheat at 115°C. Historical OEM warning-threshold data point; no architecture borrowed.

- **Standards note for S2:** SAE J2012 defines P0217 only as a name — "Engine Coolant Over Temperature Condition" [1] — and CARB §1968.2 does not mandate an overheat monitor [13]. S2 is therefore an engineering flag, not a regulatory monitor, and its critical band must be fully baseline-derived. The independent anchors bound it from both sides: healthy plateau ≈90°C (baseline) < critical band < pressurized-system boiling point >120°C ([4], web-capture edition p. 769), with 110–115°C as the OEM operating ceiling in between [17][18].

#### Stage 3 — Calibration and Selection Audit (S1–S3 frozen and calibrated; S4 remains a supporting flag)

S4 retains its provisional values from the previous revision ("Expected Pattern") and remains a low-confidence supporting flag (its cold-soak mechanism lives in section 4). S1–S3 are calibrated against the project baseline and **frozen** (experiment records: `experiments/cooling_s1/`, `experiments/cooling_s2/`, `experiments/cooling_s3/`):

- **S1 Slow warm-up (P0128) — FROZEN.** 
  - *Rule:* at a qualified cold start, assign a warm-up time budget. If `coolant_temp` reaches `T_target` before the budget expires → `pass`. If the budget expires with sufficient heat input and `coolant_temp` still below `T_target` → `triggered` (direction low, P0128). Everything else → `not_evaluable`. One decision per start; no per-sample thresholding.
  - *Right-censor handling:* if the target is not reached and the continuous episode ends before budget expiry, record `time_to_target_79c_is_right_censored = true` and the available follow-up duration; return `not_evaluable`, never `triggered`.
  - *Frozen parameters:* `T_target = 79°C`, from `T_reg_est − 11°C` [13], where `T_reg_est = 90°C` = median of per-trip post-warm-up plateau medians over the 66 healthy trips, computed in `experiments/cooling_s1/` and corroborated by the row-level baseline median of 90.00°C in the model team's healthy-baseline table (the map thermostat's commanded setpoint is not observable — stated substitution — project-wide policy: reference levels unobservable in the signal set are baseline-derived). The budget formula is a project-designed discretization of the model-based expected-warm-up reference [10][14], adopted after two simpler estimators failed (full derivation record: `experiments/cooling_s1/`). Budget = Σ over ECT bands (<30 / 30–50 / 50–65 / 65–79°C) of ΔT ÷ healthy warm-up rate for that band (per-trip median → across-trip P25), × safety factor 1.30, computed per ambient bin (≤5°C / >5°C), capped at 30 min. Resulting budgets: 16.5–26.9 min (cold bin), 8.3–18.2 min (warm bin).
  - *Eligibility (at start; any failure → `not_evaluable`):* engine start observed in the log (RPM off→on transition); start `coolant_temp` ≤ 50°C and < `T_target`; `ambient_temp` at start ≥ −7°C [13]; ECT/ambient/MAF present. A 6-hour cold soak is **not** required — that is S4's precondition, not S1's.
  - *Asymmetry:* starts without cold-soak evidence may `trigger` but never `pass` — residual engine heat could explain a fast warm-up, so an early pass on such a start is uninformative; these are reported as "no anomaly observed".
  - *Heat-input guard:* at budget expiry, if the trailing 180-s MAF integral is below the healthy P25 (≈2800 g), report `not_evaluable` — the engine did not produce enough combustion heat to expect a normal warm-up [13][14]; gating architecture per [16].
  - *Decision margin:* every decision records `decision_margin = budget − time_to_target`. Margins within about ±5 s are borderline: with 1 Hz integer-degree ECT, one sample is the physical resolution of this decision.
  - *Provenance:* the −11°C offset is the regulatory threshold **form**, relative to this vehicle's own regulating temperature (vehicle-independent) [13]; −7°C and the heat/idle guards are regulatory allowances/examples adopted as defaults — they affect evaluability only, never a verdict.
  - *Sensor-trust clause (consumer of S4):* if S4 flags this segment's start ECT as implausible, the S1 result is reported as `not_evaluable_due_to_ect_plausibility` — a cold-start ECT bias would otherwise be misattributed to the thermostat, the exact misattribution [15]'s two-region architecture exists to prevent. An S4 `not_evaluable` must never be used to raise S1 confidence.
  - *Calibration validation (performed at freezing; full record in `experiments/cooling_s1/` — this is Stage 3 evidence that the calibration is sound, not the Stage 4 program):* 51 qualified cold starts, of which 20 reach a decision point (**decision coverage 39.2%** — a dataset property; read all figures below together with it).  
  Healthy false positives: 0/20 in-sample; 1/20 under leave-one-trip-out (a borderline start missing its budget by 4.6 s on a ~16-min budget, i.e., at decision resolution; reported as-is, no further tuning — the one in-sample adjustment, safety factor 1.20 → 1.30, is disclosed here).  
  Smoke-test injections (two types, single severity: warm-up rate halved; ECT capped at 65°C): 93.8% detected among decision-covered cases (93.75% out-of-fold), 65.2% over all cases — the gap comes from short observation windows and the heat guard, not the thresholds.  
  LOTO stability: `T_reg_est` = 90°C in all 66 folds, max band-rate drift 5.45% (limit 10%), ambient fallback confined to the known weak cell (>5°C, start ECT <30°C, 8 trips).  
  **Maturity: provisional research-grade P0128 candidate** — validated on this dataset's healthy trips and synthetic smoke tests only; real-fault recall not claimable (dataset-wide limitation); thermostat indicated, not isolated. No further calibration iteration planned.  

- **S2 Overheating (P0217) — FROZEN.** 
  - *Rule:* in a qualified post-warm-up window, `coolant_temp ≥ 105°C` sustained for ≥180 s → `triggered` (direction high, P0217). At ≥110°C sustained ≥30 s, the same trigger carries higher confidence — **this upper tier is provisional**: no healthy data exists near 110°C, so it awaits Stage 4 injection. `pass` = at least 180 s of evaluable post-warm-up time with no trigger; otherwise `not_evaluable`.
  - *Calibration evidence (pre-registered census, `experiments/cooling_s2/`):* healthy envelope max 101°C (fixed 66-trip cohort; 103°C across all 77 post-warm-up trips) — 105°C sits above every healthy observation; per-trip margin to threshold: min 4°C, median 11°C. Longest healthy episode ≥100°C lasted 87 s, so the 180 s persistence has 93 s of headroom (continuous-counter form per [15]). Trip-level coverage: 57/66 trips have at least one evaluable window (86% — vs. S1’s 39.2%, illustrating the evaluability gap between level checks and cold-start checks).
  - *Guards:* `thermal_state == post_warmup`, engine on, ECT/ambient present; **ambient domain guard**: ambient at window start >25°C → `not_evaluable` (post-warm-up ambient in this dataset: median 11°C, max 33°C; 25–33°C weakly supported, >33°C unobserved — hot-climate behavior is outside the calibration domain).
  - *Honesty note:* both thresholds lie above all healthy observations, so healthy zero-false-positive holds **by construction**; the reported healthy-side quantity is therefore the margin distribution, not an FP rate. Detection capability rests entirely on Stage 4 injection.
  - *Attribution:* P0217 is a condition-level code; without a thermal model [15], a sensor stuck at a high value cannot be excluded — report as "overtemperature condition indicated; sensor fault not excluded".
  - *No in-sample tuning occurred* (the pre-registered 104–105°C escalation rule was never invoked), so no LOTO round is required — unlike S1, there is no tuned parameter to cross-validate.

- **S3 Rising without plateau — FROZEN as S2's pending precursor** (demoted from independent detection). Supersedes "coolant_slope > 2°C/min for 2-3 min".
  - *Census finding (`experiments/cooling_s3/`):* slope shape alone cannot separate regulation loss from the map thermostat's legitimate mode-switch climbs [4]. Without a level condition, 2°C/min still leaves 17 healthy 120-s episodes (2 at 180 s). The five known healthy ≥100°C episodes climb at 0.67–2.67°C/min with 9–11°C cumulative rise — indistinguishable from an early fault except by how they end (3/5 settle back to the ~91°C plateau; 2/5 right-censored at trip end). Independent early P0217 detection is therefore **not viable on this vehicle**; this is a documented negative finding, not a gap.
  - *Rule (level-conditioned precursor):* in a qualified post-warm-up window, 180-s ECT rate ≥ 0.5°C/min AND `coolant_temp` ≥ 100°C, sustained for ≥180 s → **`pending` only** (P0217 family, early stage, lower severity tier). S3 never outputs `triggered` on its own; P0217 is confirmed only when S2 fires (105°C/180 s, or 110°C/30 s provisional tier). Minimum evaluable window: 360 s.
  - *Calibration evidence:* pre-registered fixed ordering selected r = 0.5°C/min, d = 180 s, L = 100°C — zero healthy triggers; nearest healthy episode 87 s → 93 s headroom. Candidates at L = 90/95°C were rejected by the pre-registered 60-s headroom requirement (nearest healthy episode 147 s against d = 180 s). Trip coverage: 54/66 (81.8%; S2: 86.4%).
  - *Stage 4 open items:* whether the precursor delivers real lead time ahead of S2, and whether short injections get absorbed into `pending` without confirmation.
  - *No in-sample tuning occurred* (fixed pre-registered candidate ordering) — no LOTO required.

- **S4 Cold-start ECT plausibility — executable v1** (low-confidence P0116 flag; S1's sensor-trust guard). Supersedes the `cold_soak_candidate_flag`-gated form: that flag requires ECT ≈ AAT inside its own enable condition, so a faulty ECT could never be flagged (circular gating). The flag stays in the feature layer but no longer enables S4.
  - *Eligibility (all at segment first row; any failure → `not_evaluable`):* `segment_gap ≥ 6 h`; first-row RPM < 50 with an RPM off→on transition observed later in the segment; ECT/IAT/AAT present, none imputed or suspicious. **IAT is the cold-soak witness:** `|IAT − AAT| ≤ 7°C`, else `not_evaluable` — a long gap with warm sensors cannot distinguish "vehicle ran during the gap" from a fault.
  - *Verdict:* `|ECT − AAT| > 15°C` → ECT cold-start plausibility candidate (direction inconsistent, low-confidence P0116 support). ≤ 15°C → `pass`.
  - *Output constraint:* this is support/confidence evidence and a sensor-trust guard for 1-S1; it must never independently emit a P0116 DTC.
  - *Calibration basis (both thresholds provisional):* strict healthy baseline = **18 events** (observed engine start — the same event set underpinning S1). `|IAT−AAT|` healthy max 5°C → witness 7°C; `|ECT−AAT|` healthy max 11°C → verdict 15°C; zero healthy candidates at these values. Looser eligibility without the observed-start requirement produced 5 false candidates (all logs starting mid-run) — the strict form is mandatory. Architecture precedent: [15]'s exponential soak-decay start estimate with start-up tolerance; [2] for soak-duration methodology.
  - *Mirror:* section 4's F2 uses ECT as the witness to judge IAT — structural mirror only, thresholds calibrated separately. Both checks read raw three-sensor deltas, so there is no circular dependency; both sensors far from AAT → both checks `not_evaluable`.
  - *Maturity:* implementable low-confidence research-grade P0116 plausibility candidate. It cannot isolate the ECT fault, nor prove a true cold soak: `segment_gap` is a logging gap, not verified engine-off time; IAT can return to ambient faster than coolant; AAT faults and common-mode faults are not excluded.

Output: three-state per sub-check (`pass` / `triggered` / `not_evaluable`), reported as `proxy_id + sub_check_id + direction + DTC label` — see Shared Conventions.

#### Stage 4 — Empirical Falsifiability (TBD — owned by the fault-injection workstream)

*Boundary note:* the S1 validation figures reported under Stage 3 came from **smoke-test injections used to freeze the calibration** (two fault types, one severity each). They are Stage 3 evidence, not the Stage 4 program. Stage 4 remains the systematic study on generated fault data, per the Shared Conventions Stage-4 protocol:

- **TBD-1 Injection design:** slow-ramp warm-up retardation and depressed plateau on `coolant_temp` (S1/S3); sustained positive offset above the critical band (S2); start-offset injection (S4 flag). For S1, the pilot injection harness, the 23 source cycles, and the 51-start event set in `experiments/cooling_s1/` are reusable as-is.
- **TBD-2 Detectability curve:** detection rate vs. **graded** injected severity per sub-check; the S1 pilots cover a single severity point — the curve is open. The `decision_margin` field is the intended x-axis companion.
- **TBD-3 False-positive rate:** on held-out healthy trips under the frozen rules (split by `trip_id`, per §5.3 leakage rules); for S1 the LOTO fold machinery is reusable.
- **TBD-4 Acceptance criteria:** set jointly after the first TBD-2/3 run; per protocol, Stage 3 thresholds may be revised **once**, then re-frozen. Note for S1: one in-sample adjustment (1.20 → 1.30) has already been spent (disclosed in Stage 3) — a TBD-4 revision would further erode validation independence and must be weighed accordingly.

## 2. air_intake_maf_anomaly

[Authoritative definition and final rules](proxy_failure_definition.md#2-air_intake_maf_anomaly)

**Non-executed sub-checks:** `2-S1` (downgraded; descriptive research evidence only) and `2-S3a` (documented infeasibility). Neither sub-check is part of the runtime decision pipeline and neither may produce a verdict or DTC.

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Under the same operating condition, MAF-based load and MAP-based load should remain physically consistent. Persistent deviation between the two indicates a plausibility abnormality in the air-mass measurement chain. [4]

**Observability argument.** `maf` has no direct ground truth in the signal set; it is observable only through **redundancy** with the parallel speed-density estimate `f(rpm, map, intake_temp)`. Consistency is evaluable in any engine-on window, but attribution is limited: a two-estimator disagreement cannot by itself identify which side (MAF or MAP) is at fault. Isolation therefore relies on the arbitration rule with section 5 (Stage 3 below), which uses MAP-side dedicated checks as the tie-breaker. Transient windows (acceleration, gear shifts) degrade the comparison and must be masked or down-weighted.

**Failure-mode enumeration.**

| # | Symptom | Stage-1 observable | Enable window | Output |
|---|---|---|---|---|
| S1 | MAF drift/contamination — persistent bias vs. parallel estimate | `speed_density_maf_residual` sustained outside the healthy tolerance band; `maf_map_cohesion` as descriptive corroborator | steady-state windows | shared evidence — no direct DTC (arbitration with section 5) |
| S2 | MAF under-read at high load (classic contamination signature) | `speed_density_maf_residual` (= `maf` − expected MAF) sustained on the low side | `post_warmup__high_load` | P0101 candidate (direction low; subject to arbitration) |
| S3a | Stuck MAF signal | MAF sustained exactly constant while rpm/speed/pedal context materially changes | engine-on with a context-change opportunity | P0101 candidate |
| S3b | Zero/low MAF while firing | `maf` = 0 sustained while rpm ≥ 500 | engine running | P0102 candidate (direction low) |

*Attribution note: a two-estimator disagreement (S1) cannot identify the faulty side by itself; residual sign alone does not attribute (a positive residual can be MAF over-read or MAP-side under-estimate). Attribution is performed only by the frozen routing rule (Stage 3), with 5-S1 / 5-S3 as MAP-side witnesses.*

#### Stage 2 — Literature Anchoring (TBD)

- Bosch Automotive Handbook [4] — **Borrowed: physical basis only** (two-estimator redundancy and air-mass measurement principles; existing source, retained).
- Nyberg & Nielsen [5], intake-system fault-isolation patent [6] — **Borrowed: model-based cross-check architecture** (MAF/MAP two-estimator reduced form; the throttle-model input (tps) is not available in this dataset, so this proxy uses only the two-estimator consistency check, not the full throttle-model implementation).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] (pre-2006 numbering (e)(16); renumbered in the OAL 2006 text) — **Borrowed: mandate** (comprehensive component monitoring requirement; MAF is an input component covered under this requirement).
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — **Borrowed: rationality fault diagnostic requirement** (defines the required diagnostic scope — circuit continuity, out-of-range, and rationality faults with "inappropriately high nor inappropriately low" two-sided verification; supports the diagnostic scope of S1/S2 (cross-sensor rationality) and S3a/S3b (stuck / out-of-range). The regulation does not prescribe the residual band, the under-read threshold, or the exact-flat context gate — those judgment forms are this project's data-driven implementations).

#### Stage 3 — Calibration and Selection Audit (S1 downgraded — no cohesion band; S2 frozen; S3a documented infeasibility; S3b frozen; pre-registered censuses, results 2026-07-18)

**Metric unification (2026-07-18).** The implemented z-difference form of `maf_map_cohesion` — |z(`maf_derived_air_load_raw`) − z(`map_derived_air_load_raw`)|, standardized against the golden post_warmup steady-driving reference in `feature_baselines.json` — is the authoritative Stage 3 statistic. The historical relative-deviation form ("> 0.25–0.30", i.e. 25–30% of expected load; never implemented) and the informal 1.8 z-threshold are **retired as historical notes and inherit nothing**; all thresholds come from the pre-registered census. *Dependency:* the standardization parameters are interim dataset-fitted values — when the model group's Story 5 fitted baseline lands, cohesion values change and this section must be re-frozen (recorded as a re-freeze trigger, not a blocker).

**Census registration (2026-07-18, `experiments/maf_census/`).** Three pre-registered censuses; the JSONs are the binding specification. Registered design resolutions:

1. *2-S1 cohesion band:* one-sided upper trip-equal P99.5 per state (cohesion is nonnegative); **reuses the frozen 5-S2 steady-state mask unchanged** — re-deriving a second mask would let the two sides of the MAF/MAP arbitration see different evidence windows; overlap with 5-S2 out-of-band episodes is quantified for the arbitration wiring.
2. *2-S2 high-load under-read:* direction low only (`speed_density_maf_residual` = `maf` − expected, so under-read = low side); enable = `post_warmup__high_load` **without** the steady mask (sustained pulls are exactly what the mask excludes); dual-track registration — episode form (persistence 5/10/30 s) with a trip-level median fallback (trips with ≥ 60 high-load samples, healthy per-trip-median P5 threshold, ≥ 33/66 qualifying floor), plus a direction sanity halt (healthy high-load median must be positive).
3. *2-S3 split:* C1 stuck (**P0101**, not P0102) mirrors 5-S3's context-gated exact-constant rule — `maf` is 0.005 g/s-quantized with only 10.7% zero consecutive diffs, so exact 60-s constancy is strong evidence; context thresholds must reproduce `map_census` values (halt on divergence). C2 zero/low (**P0102**) = zero-MAF run ≥ d at rpm ≥ 500, with the run-length floor calibrated above the healthy zero-run distribution (233 healthy engine-on zero-MAF samples are a known cleaning quirk — single-sample triggering is forbidden). The census's strict rolling statistic settles the Stage 1 `maf_stability` feature TBD.

**Frozen decision rules (census results 2026-07-18, `experiments/maf_census/outputs/`; pre-registered branch orderings followed, no post-result tuning, empty amendment logs):**

- **S1 Cohesion band — DOWNGRADED (branch c; no banded output).** No operating state satisfied the pre-registered admissibility (zero healthy episodes with margin ≥ 10 s AND steady coverage ≥ 17/66): idle failed margin at 10 s (6 s) and coverage at 30 s (12/66); steady_driving had 4 healthy episodes at 10 s and missed the 30-s margin by 2 s (8 s vs. 10 — near-miss recorded, not rescued); acceleration passed margin but had 3/66 coverage; high_load margin 5 s at 10 s, coverage 1/66 at 30 s. `maf_map_cohesion` is retained as **descriptive corroborating evidence only** (F4 route); the executable shared-evidence trigger for the MAF/MAP arbitration is section 5's frozen S2 residual band (steady_driving, ≥ 30 s).
- **S2 High-load under-read — FROZEN (branch a; direction low; P0101 candidate).**
  - *Rule:* `operating_state == post_warmup__high_load`, high confidence, quality-valid; `speed_density_maf_residual < −18.495 g/s` (healthy trip-equal P0.5) at every consecutive valid 1 Hz sample for ≥ 10 s → `triggered` (P0101 candidate, direction low). Subject to arbitration: a concurrent 5-S1/5-S3 trigger reroutes attribution to MAP.
  - *Calibration evidence:* zero healthy episodes; longest healthy under-read run 3 s → 7 s margin (above the ~±5 s resolution band, but thin — disclosed); 5-s persistence rejected by the pre-registered 5-s margin floor (margin 2 s); coverage 52/66 trips (78.8%); direction sanity check passed (healthy high-load residual median +7.91 g/s, positive as required); trip-level fallback registered but not needed.
- **S3a Stuck MAF — NOT FROZEN (branch c; documented dataset infeasibility).** The healthy census contains **zero** joint (material-context + 60-s exact-flat MAF) episodes: with `maf` quantized at 0.005 g/s, healthy MAF is never exactly constant for 60 s under changing context. A zero-healthy-trigger rule would therefore be structurally inert — the pre-registered nearest-healthy-joint-episode guard exists precisely to block this freeze. Stuck-MAF detection is deferred to Stage 4 injection as descriptive evidence; the 60-s rolling max−min statistic remains defined (settling the Stage 1 `maf_stability` TBD) but is consumed by no frozen rule.
- **S3b Zero MAF while firing — FROZEN (branch a; P0102, direction low).**
  - *Rule:* `maf == 0.0` at every consecutive valid engine-on sample with `rpm ≥ 500`, sustained ≥ 10 s → `triggered` (P0102 candidate). A firing engine cannot draw zero air; the 500-rpm floor excludes cranking ambiguity.
  - *Calibration evidence:* 193 healthy zero-MAF samples / 150 runs in the quality domain (known cleaning quirk), longest healthy run at rpm ≥ 500 = 3 s → 7 s margin; zero healthy triggers; 5-s persistence rejected by the margin floor (2 s); no healthy zero-run overlaps the `maf_had_hard_invalid_source` flag.
- **Routing (mirror of section 5):** 5-S2 band evidence (or a 2-S2 trigger) + MAP-side witnesses (5-S1/5-S3) normal → attribute MAF, report under this section (P0101/P0102); a MAP-side witness abnormal → attribute MAP, report under section 5 (P0106); evidence present but neither side evaluable → F4 (P006A, no isolation). With the cohesion band downgraded, F4 has no standalone calibrated trigger of its own and can only be reached through the routes above.
- **IAT confidence wiring:** when 4-S2 cold-start IAT plausibility support is active, cap `confidence_tier` at `low` for IAT-dependent 2-S2 residual evidence. Do not alter 2-S3b, which uses only raw MAF and RPM.
- Output: three-state per sub-check (`2-S1` descriptive, `2-S2`, `2-S3a` non-executable, `2-S3b`), `decision_margin` per episode, see Shared Conventions.

- Previous provisional text (historical): `maf_map_cohesion` > 0.25-0.30 for 5-10 s as an initial proxy hint; or steady-state standardized deviation exceeding 25-30%. Retired per the metric unification above.
- ~~TBD: per-`operating_state` tolerance bands from project baseline~~ — resolved by the census registration (per-state one-sided bands, branch a/b/c).
- **Arbitration rule (shared evidence with section 5):** cohesion high **and** section 5's MAP-dedicated checks (step-response, stuck-signal) normal → attribute to MAF, report under section 2 (P0101/P0102). Cohesion high **and** MAP-dedicated checks abnormal → attribute to MAP, report under section 5 (P0106). Cohesion high, both sides inconclusive → report F4 (P006A, no isolation).
- Output: three-state per sub-check, see Shared Conventions.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** multiplicative gain drift (0.7…0.95×) and additive offset on `maf`; load-dependent under-read (gain reduction scaled by `maf` magnitude) for S2; frozen-value injection for S3. Injection on `maf` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 3. accelerator_pedal_sensor

[Authoritative definition and final rules](proxy_failure_definition.md#3-accelerator_pedal_sensor)

**Non-executed sub-checks:** `3-S2` (documented infeasibility) and `3-S3` (downgraded; descriptive research evidence only). Neither sub-check is part of the runtime decision pipeline and neither may produce a verdict or DTC.

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** The ETC system uses two potentiometers on the pedal and throttle device to provide redundancy, and continuously checks all sensors and calculations that affect throttle opening while the engine is running. [1]

**Observability argument.** This is the only proxy whose reference is not a physical model but the **redundant channel itself**: each channel is the other's ground truth, so consistency is observable at every sample where both channels are valid — no operating-condition restriction is physically required (enable window = engine-on, both channels non-missing). One precondition must hold for the proxy to be meaningful: the two channels must be genuinely independent measurements, not gateway-duplicated copies (cleaning-QA degeneracy check; in this dataset the measured D/E correlation of 0.9824 with distinct value tracks confirms genuine dual-track redundancy).

**Failure-mode enumeration.**

| # | Symptom | Stage-1 observable | Enable window | Output |
|---|---|---|---|---|
| S1a | Channel relation drift — ratio/offset bias | residual of the learned mapping `accel_pedal_e = a·accel_pedal_d + b` sustained outside the healthy band | engine-on, both channels valid, **transient-masked** (low `pedal_slope`) | P2138 candidate |
| S1b | Extreme channel disagreement | `accel_pedal_channel_delta` above all healthy observations | any engine-on window (unmasked) | P2138 candidate — high severity tier |
| S2 | One channel frozen while the other moves | candidate channel exactly constant while the other channel materially moves | engine-on, active pedal motion | P2138 candidate (direction = frozen channel) |
| S3 | Noise burst on either channel | rolling std of `accel_pedal_channel_delta` sustained above the healthy upper tail | engine-on, transient-masked | P2138 candidate |

*Revision note (2026-07-18):* the enable restriction to `steady_driving`/`acceleration` is replaced by a transient mask — the observability argument above holds at every valid sample, but 1 Hz asynchronous D/E sampling inflates instantaneous deltas during fast pedal motion (healthy active-pedal delta P99.5 ≈ 20.8 pp vs ≈ 8.1 pp released, max 63.5 pp), which is a sampling artifact, not a fault signature. `accel_pedal_channel_ratio` is demoted to descriptive corroborator (healthy distribution 0.18–4.66, unstable under division). Rolling correlation was rejected as the S3 statistic (degenerate on the 63.8% released-pedal samples); member A's delta-rolling-std form is adopted.

All modes map to P2138; sub-check identity and severity tier carry the differentiation in the output schema.

#### Stage 2 — Literature Anchoring

- SAE J2012 [1] — **Borrowed: DTC identities only** (P2138 pedal position sensor range/performance; the standard gives the DTC name, not the detection criteria).
- Bosch Automotive Handbook [4] — **Borrowed: ETC dual-sensor redundancy design** (p. 706; describes the dual-potentiometer architecture used in electronic throttle control systems).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] (pre-2006 numbering (e)(16); renumbered in the OAL 2006 text) — **Borrowed: mandate** (comprehensive component monitoring; pedal position sensor is an input component covered under this requirement, listed as part of the throttle control system input chain).
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — **Borrowed: rationality fault diagnostic requirement** (dual-channel accelerator pedal sensors are a direct application — channel correlation is a standard rationality check where each channel verifies the other's plausibility).
- ISO 26262-5:2018 [12] — **Borrowed: functional-safety framework for redundant sensing** (provides the safety-mechanism design rationale for dual-channel consistency monitoring as an automotive E/E systems diagnostic mechanism; the specific implementation is an OEM design choice).

#### Stage 3 — Calibration and Selection Audit (S1 frozen; S2 documented infeasibility; S3 downgraded; census results 2026-07-18)

**Census registration (2026-07-18, `experiments/pedal_census/`; rev 2 after pre-run review, no results seen).** Three pre-registered censuses; the JSONs are the binding specification. Registered design resolutions:

1. *Transient mask instead of state gate (S1a):* |`pedal_slope`| ≤ trip-equal P50 sustained ≥ 3 s, **with a degeneracy guard** — the 5-S2 census measured this P50 as exactly 0, so if it degenerates the registered fallback (P50 of the *nonzero* |`pedal_slope`| distribution) takes over, logged, never silently accepted. Masked **pedal-range bin coverage** is reported; if masked samples above 16 pp cover < 10% of samples or < 17/66 trips, S1a freezes as an **offset-only** detector (gain-drift claims then require Stage 4 injection).
2. *S1 two-tier structure (mirror of 1-S2):* S1a banded residual of a **trip-equal weighted** least-squares reference mapping fitted inside the mask (a, b frozen; D/E correlation must reproduce the 0.9824 anchor within 0.01 — a pipeline check, not proof of full-range linearity); S1b extreme delta = smallest 5-pp multiple above the healthy maximum, unmasked, **provisional and specificity-only** (constructive zero-FP demonstrates no detection capability; validity rests on Stage 4 offset/gain injection), with a numeric artifact guard (≥ 5 of top-10 from one trip, quality-flag proximity, or single-source concentration → halt).
3. *S2 per-direction adjudication:* persistence starts at 2 s with explicit semantics (d s = d consecutive 1-s differences = d+1 raw samples; supersedes the historical "more than 1 s" rule); D-frozen and E-frozen are censused **and adjudicated separately** (full freeze / partial freeze / infeasible), opportunity coverage defined per direction on the moving channel alone; motion-enable quantiles taken over *nonzero* differences (zero-inflation guard); structural-inertia guard applies per direction. All S2 margins sit in the ±5 s borderline-by-resolution band — any freeze is labeled resolution-borderline and Stage 4 frozen-channel injection is a necessary condition for capability claims.
4. *S3 endogeneity fix — per-channel quiet gates, low-motion scope:* a mask derived from the channel mean would be closed by the very noise it should detect; instead delta-std is censused separately under gate_D and gate_E (each channel's own quietness), so noise on one channel stays visible under the other channel's gate. All 10 samples of the rolling window must lie inside the gate (endpoint-only containment forbidden). S3 is declared **low-motion-only**; any freeze is conditional on Stage 4 noise injection confirming the gates do not absorb bursts — until then triggers corroborate 3-S1a rather than standing alone.
5. *Parameter provenance (honest wording):* historical values ("5–10 pp", "0.95 correlation", "1 s freeze") inherit nothing. **Data thresholds** (band edges, gate/enable quantile values, extreme-delta base) are census-calibrated; **design constants** (window lengths, persistence grids, margin floors, 5-pp rounding, gate persistence) are fixed pre-run by registration and do not come from the census.

**Frozen decision rules and negative findings (`experiments/pedal_census/outputs/`):**

- **S1a Channel-relation residual — FROZEN (branch a; offset-and-gain scope; P2138 candidate).**
  - *Rule:* quality-valid engine-on samples use the registered low-motion mask. The all-sample trip-equal P50 of |`pedal_slope`| was `0`, so the pre-registered degeneracy fallback activated: nonzero-distribution trip-equal P50 = `2.4 pp/s`, sustained for at least `3 s`. Inside that mask, the binding trip-equal weighted mapping is `E = 0.997273·D + 0.383103`; residual `r = E − (0.997273·D + 0.383103)`. A same-side residual below `−1.8350 pp` or above `+1.3777 pp` continuously for `30 s` triggers 3-S1a. A trip with a qualifying 30-s masked opportunity and no trigger may pass; otherwise the sub-check is `not_evaluable`.
  - *Calibration evidence:* full-population D/E correlation `0.982518` reproduces the `0.9824 ± 0.01` pipeline anchor; masked correlation rises to `0.997397`, consistent with removal of asynchronous 1-Hz transients. Zero healthy 30-s triggers; longest healthy low/high residual episodes `18/9 s`, giving `12/21 s` margins; masked coverage `66/66` trips. Samples above 16 pp comprise `18.19%` of the masked population and occur in `66/66` trips, passing both registered range-visibility floors, so S1a retains offset-and-gain scope rather than narrowing to offset-only.
  - *Execution record:* activation of the registered nonzero-P50 fallback is logged in the S1 pre-registration. A prior halt also corrected the correlation anchor's applicable domain from the masked fit population to its native full valid engine-on population; no mask, fit, threshold, grid, or branch rule changed.

- **S1b Extreme channel disagreement — FROZEN PROVISIONALLY (branch a high tier; specificity-only P2138 candidate).**
  - *Rule:* unmasked `accel_pedal_channel_delta ≥ 65 pp` sustained for `2 s` (two consecutive valid endpoints) triggers the high tier.
  - *Calibration evidence and limit:* healthy cohort maximum `60 pp`; the registered 5-pp rounding gives `65 pp`, below the observed attainable channel-span disagreement of `71 pp`. The top-10 artifact guard passed (maximum concentration `3/10` by trip/source/segment; no ±2-s quality flags). Healthy zero-trigger status is constructive because the threshold is above the healthy maximum; it establishes specificity only. Detection capability depends entirely on Stage 4 one-channel offset/gain injection.

- **S2 Single-channel freeze — DOCUMENTED INFEASIBILITY (no executable 3-S2 verdict).**
  - Both registered directions failed independently. Under the P90 motion enable, D-frozen/E-moving uses `|ΔE| ≥ 18.1 pp/s`; E-frozen/D-moving uses `|ΔD| ≥ 18.5 pp/s`. At `2 s` (two consecutive differences, three raw samples), healthy data contains `3` DE and `1` ED trigger episodes. At `3 s`, healthy triggers fall to zero but the duration margin is only `1 s`, below the registered `2 s` floor. At `5 s`, margins reach `3 s` but opportunity coverage falls to `7/66` trips for DE and `3/66` for ED, below the `17/66` floor. P95 strengthened enables do not rescue either direction; `10 s` is stress-test-only with zero opportunity.
  - *Consequence:* both directions output `not_evaluable`; no P2138 rule is frozen from S2. Frozen-channel Stage 4 injection remains descriptive evidence and a possible redesign input, not validation of a current detector.

- **S3 Channel-noise burst — DOWNGRADED (branch c; corroborator only).**
  - *Census form:* low-motion per-channel gates are retained as the descriptive architecture: gate_D uses nonzero-difference P50 `3.5 pp/s`, gate_E `3.1 pp/s`, each sustained `3 s`; all ten samples forming `delta_std_10` must lie inside the gate. Binding healthy P99.5 anchors are `0.9315 pp` under gate_D and `1.6121 pp` under gate_E.
  - *Negative finding:* both freeze-eligible persistence values fail. Under gate_D, healthy trigger counts are `32` at 5 s and `8` at 10 s (longest episode `16 s`); under gate_E they are `14` and `5` (longest `10 s`). The zero-trigger 30-s rows are stress-test-only and cannot rescue a branch. Coverage is `66/66`, so failure is not caused by opportunity starvation.
  - *Artifact-guard amendment:* the first run halted because endpoint-level top-10 rolling windows concentrated within one episode; adjacent 10-s windows share 9/10 samples, making endpoints the wrong statistical unit. The approved amendment uses one maximum endpoint per independent high-std episode and checks its full ten-sample composition window. The amended guard passes for both gates (maximum trip/segment/source concentration `2/10`; no quality flags) without changing thresholds, persistence, coverage, or branch outcome.
  - *Consequence:* 3-S3 produces no standalone P2138 verdict and is retained only as descriptive corroboration for 3-S1a. Any future standalone noise detector requires Stage 4 burst injection plus a new pre-registered freeze.

- Output: three-state per sub-check (`3-S1a`, `3-S1b`, `3-S2`, `3-S3`), all P2138 with sub-check identity and severity tier carrying differentiation; `decision_margin` per episode, see Shared Conventions.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** additive offset and gain error on one channel (S1); frozen-value on one channel during active pedal motion (S2); additive noise bursts (S3). Injection on one channel at a time, other channel untouched.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 4. intake_air_temperature_sensor_fault

[Authoritative definition and final rules](proxy_failure_definition.md#4-intake_air_temperature_sensor_fault)

**Removed research item:** `4-S4` is retained below only as a historical research observation. It is not an IAT sensor-fault sub-check, is not part of the runtime pipeline, and produces no engineering flag, verdict, or DTC.

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Intake air temperature directly affects air density and combustion efficiency — colder air is denser, and heated intake air reduces effective oxygen content [4, p. 786]. Under normal operation, IAT should closely track ambient/coolant temperature references immediately after a cold soak, before engine heat has propagated to the intake path, and should respond dynamically to changes in vehicle speed and airflow once the engine is running. A signal that is implausible relative to reference sensors at cold start, or that fails to vary despite sustained flow, indicates the sensor circuit is not measuring true intake-air temperature — consistent with the OEM diagnostic logic underlying P0111 [1][2][3].

**Observability argument.** IAT plausibility is observable against three independent references, each with its own window and confidence level: (a) the **equalization reference** at cold-soak start — the strongest physical check, but of limited availability in this dataset (true soak duration cannot be reconstructed from logged data; strict cold starts are rare), which is precisely why the cold-soak check is demoted to a low-confidence supporting flag rather than a primary judgment (see Stage 3); (b) the **thermal-response reference** — a healthy IAT must vary when flow context changes; crucially, the converse also holds: in steady cruise at stable ambient a healthy IAT is legitimately flat, so a stuck signal is observable only against **changing** flow context (the same trap that invalidated the frozen-ECT sub-check in section 1). The enable window is therefore "sustained window with material context change", and this is the primary judgment; (c) the **post-load heat-soak signature** — a dataset-derived secondary reference with no direct DTC support.

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| S1 | Stuck/skewed IAT — no thermal response | `intake_temp_stability` near zero while flow context changes | sustained window **with changing flow context** | P0111 |
| S2 | IAT implausible at cold start | `intake_ambient_delta` at segment start, qualified by observed-start + ECT-witness eligibility (v1; mirrors section 1 S4) | cold-soak segment start | P0111 (confidence modifier, not standalone trigger) |
| S3 | IAT out of physical range | raw bounds on `intake_temp` vs. J1979 PID 0x0F physical range (−40…215°C) [19] | any sample | P0112 (low) / P0113 (high) |
| S4 | Post-high-load heat-soak observation | `intake_temp` vs. project-derived idle-window reference | post-high-load idle/low-speed window | non-executed research observation; no runtime output or code |

#### Stage 2 — Literature Anchoring

- SAE J2012 [1] — **Borrowed: DTC identities only** (P0111 range/performance; P0112/P0113 out-of-range low/high); the standard gives names, not criteria.
- CARB Title 13 CCR §1968.2, section (e)(15) [13] — **Borrowed: mandate and the two-sided rationality form; no values.** Comprehensive-component monitoring requires input components to be checked for "lack of circuit continuity, out-of-range values, and, where feasible, rationality faults", with rationality verifying "that a sensor output is neither inappropriately high nor inappropriately low (e.g., “two-sided” diagnostics)" ((e)(15.2.1)(A)); rationality, circuit, and out-of-range faults must store distinct codes ((e)(15.2.1)(B)) — grounds S1/S2 (rationality) and the direction split in S3. The diesel mirror (f)(15.1.1)(A) names the intake air temperature sensor explicitly; the gasoline input-component list is non-exhaustive ("may include"). Jurisdiction note as in section 1.
- Delphi patent US7120535 [3] — **Borrowed: stuck/response-failure detection architecture** (measured vs. expected IAT evaluation; assignee and title verified against the patent record).
- Cold-soak test-design framework [2] — **Borrowed: methodology only** (soak duration as a standard test precondition); ECT-oriented, not IAT-specific (existing note, retained).
- Bosch Automotive Handbook [4, p. 786] — **Borrowed: physical basis only** (air density / effective oxygen content).
- SAE J1979 [19] — **Borrowed: physical measurement bounds** for S3 (PID 0x0F intake air temperature, −40…215°C).

#### Stage 3 — Calibration and Selection Audit

*(S1 frozen from the pre-registered census; S2 executable v1; S3 range rule closed; S4 retained only as a non-executed research observation)*

- **S2 Cold-start IAT plausibility — executable v1** (low-confidence P0111 support; structural mirror of section 1's S4). Supersedes the `cold_soak_candidate_flag`-gated form: that flag requires IAT ≈ AAT inside its own enable condition, so a faulty IAT could never be flagged (circular gating). The flag stays in the feature layer but no longer enables S2.
  - *Eligibility (segment first row; any failure → `not_evaluable`):* `segment_gap ≥ 6 h` [2]; first-row RPM < 50 with an off→on transition observed later in the segment; ECT/IAT/AAT present, none imputed or suspicious. **ECT is the cold-soak witness:** `|ECT − AAT| ≤ 15°C`, else `not_evaluable` — a long gap with warm sensors cannot distinguish "vehicle ran during the gap" from a fault.
  - *Verdict:* `|IAT − AAT| > 7°C` → IAT cold-start plausibility candidate (direction inconsistent, low-confidence P0111 support); ≤ 7°C → `pass`.
  - *Calibration basis (both thresholds provisional):* the same 18-event strict baseline as section 1's S4 — healthy `|IAT−AAT|` max 5°C → verdict 7°C (zero healthy candidates); healthy `|ECT−AAT|` max 11°C → witness 15°C. Thresholds are per-sensor, not numerically mirrored; both sensors far from AAT → both mirror checks `not_evaluable`.
  - *Consumers:* confidence modifier for co-occurring IAT anomalies — never a standalone P0111 trigger. Because `intake_temp` feeds the speed-density residual used by sections 2 and 5, an active S2 candidate caps `confidence_tier` at `low` for 2-S2 and 5-S2. It does not alter 2-S3b, 5-S1, or 5-S3.
  - *Note:* [2] documents the cold-soak framework for ECT (P0116) checks, not IAT specifically — cited for methodology only.

- **S1 Stuck/no-response IAT — FROZEN (hard-stuck only; P0111 candidate).** Supersedes the "sustained airflow" form.
  - *Rule:* engine on; IAT/speed/MAF/RPM valid, none imputed or suspicious; context change within a 120-s window is material — `speed_std ≥ 12.4 km/h` OR `maf_std ≥ 8.5 g/s`. These are trip-equal weighted q50 values over valid 120-s endpoints from the fixed 66-trip cohort, with each trip contributing total weight one (`experiments/intake_s1/iat_s1_census_preregistration.json`; reproduced in `outputs/iat_s1_summary.json`). If `intake_temp_stability ≤ 0.1°C` is then sustained for 120 s → `triggered` (P0111 stuck-IAT candidate). Minimum evaluable window 240 s; `pass` = at least one evaluable context-change opportunity with no trigger; otherwise `not_evaluable`.
  - *Calibration evidence (pre-registered census, `experiments/intake_s1/`):* zero healthy triggers; longest healthy flat episode under material context change 29 s → 91 s headroom against the 120-s requirement; robust to relaxing stability to 0.25°C (longest 47 s, still zero). Context opportunities: 306 episodes across 66/66 trips.
  - *Integer-resolution caveat:* IAT is 1°C-quantized at 1 Hz — 61.8% of adjacent samples are unchanged and the longest raw constant-value run is 149 s. All of it lies outside the enable gate (steady cruise), which is exactly why the context-change gate is mandatory (cf. the frozen-ECT deferral in section 1).
  - *Scope statement:* detects **hard-stuck / no-response only**. Slow drift and mild skew are not observable without a reference model; cold-start offset is partially covered by S2. This narrows the proxy definition's "signal drift" claim — recorded as a capability limit, not a TBD.
  - *No in-sample tuning occurred* under the pre-registered grid ordering (one-line confirmation of the recorded ordering pending from the experiment workstream); no LOTO required.
  - *Maturity:* research-grade P0111 stuck-candidate; detection capability awaits Stage 4 frozen-IAT injection. `tps` remains excluded as an airflow proxy (unreliable in this dataset).

- *Post-high-load heat-soak observation (dataset-derived, no direct DTC support):* Rather than during high-load driving itself, elevated `intake_temp` is more physically expected to appear in an idle or low-speed window that follows a period of high load — a classic heat-soak pattern in which residual engine-bay heat conducts into the stationary intake path once ram-air cooling stops. This project's own baseline is consistent with that mechanism: within `post_warmup__idle` windows, `intake_temp` reaches a P99 of approximately 63°C, noticeably higher than the P99 seen during `post_warmup__high_load` driving itself (~45°C) [own baseline, not literature-sourced]. This is retained solely as a research observation: it has no corresponding DTC, does not isolate an IAT sensor fault, and never had a frozen persistence requirement. **Status: non-executed; no runtime computation, engineering flag, verdict, or DTC.**

- Output: three-state per sub-check, see Shared Conventions. S3 range rule (TBD closed): any sample of `intake_temp` outside −40…215°C [19] → `triggered` (direction low → P0112, high → P0113); evaluated continuously; `not_evaluable` only when the signal is missing.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** frozen-value injection during qualified context-change windows (S1); additive offset at qualified cold-start samples (S2); out-of-range clamp (S3). Injection on `intake_temp` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 5. map_load_signal_plausibility_fault

[Authoritative definition and final rules](proxy_failure_definition.md#5-map_load_signal_plausibility_fault)

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Intake manifold absolute pressure is a preferred method for monitoring engine load, and relative charge can be determined from available measurement signals such as MAF or MAP through an intake-manifold model [4, pp. 897, 912, 914, 919, 928]. In the original model-based intake-system diagnostic architecture, a throttle model estimates mass flow through the throttle body from ambient pressure, MAP, throttle position, and intake air temperature, while an intake-manifold model estimates MAP from the throttle-body flow and engine pumping flow; measured and modeled values are then cross-compared to detect and isolate sensor faults [5][6]. In this project, the literal throttle-position trigger is replaced by a driver-demand trigger because the available `tps` channel is not trustworthy, while the steady-state MAP/MAF/RPM consistency check remains unchanged. If MAP is distorted, load, ignition timing, fuel injection, and torque calculations will all be biased [4].

**Observability argument.** MAP is verifiable through three **complementary evidence routes**, each defining one sub-check: the **command side** (a driver-demand step must produce a MAP response — observable at pedal step events), the **parallel estimator** (MAF-derived air load must agree with MAP-derived air load — observable in steady-state windows), and the **expected own-dynamics** (healthy MAP varies with operating context — a sustained exactly-constant window while context changes is only explainable by signal sticking). S1 and S3 are **MAP-side dedicated witnesses**; S2 is **shared disagreement evidence** — the residual is not an independent ground truth, cannot by itself identify which sensor is at fault, and must pass through the frozen Stage 3 routing rule before any attribution.

**Failure-mode enumeration.**

| # | Symptom | Stage-1 observable | Enable window | Output |
|---|---|---|---|---|
| S1 | MAP unresponsive to demand step | event-level MAP excursion following a positive pedal-demand step | qualified pedal-step events, attributed per `operating_state` | P0106 candidate |
| S2 | Steady-state MAP/MAF cross-inconsistency | `speed_density_maf_residual` sustained outside the healthy tolerance band | steady-state windows | shared evidence — no direct DTC (section 2 arbitration) |
| S3 | Stuck MAP signal | MAP sustained exactly constant while rpm/speed/pedal context materially changes | engine-on with a context-change opportunity | P0106 candidate |

*S2 is shared disagreement evidence. Attribution is performed only by the frozen Stage 3 routing rule (MAP-side witnesses = 5-S1 / 5-S3); it is not a separate failure mode and has no sub-check of its own.*

#### Stage 2 — Literature Anchoring

- Bosch Automotive Handbook [4] — MAP as load-monitoring method (existing source, retained).
- Nyberg & Nielsen [5], intake-system fault-isolation patent [6] — model-based cross-check architecture. Their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation (existing note, retained).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] *(pre-2006 numbering (e)(16); renumbered in the OAL 2006 text)* — comprehensive component monitoring: MAP sensor is an input component covered under this requirement.
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — rationality fault diagnostic requirement. MAP rationality requires two-sided verification: the signal must be neither "inappropriately high" (sensor stuck high vs. pedal demand) nor "inappropriately low" (sensor stuck low, or frozen at ambient). The regulation supports the **diagnostic scope** of all three sub-checks; it does not prescribe the pedal-step event form, the residual band, or the exact-flat context gate — those specific judgment forms are this project's data-driven implementations.
- CARB Title 13 CCR §1968.2 (e)(15.3.1)(A) [13] — continuous monitoring for range; (e)(15.3.1)(B) — rationality per manufacturer-defined conditions.
- Note on substituting pedal demand for throttle position: The regulation at (e)(15.2.1)(A) states rationality checks shall be performed "to the extent feasible" and "where feasible." The specific rationality check method is not prescribed — the regulation requires the outcome (two-sided verification), not the means. This project's substitution of the unreliable tps signal with the validated pedal-demand signal is consistent with this regulatory framework.

#### Stage 3 — Calibration and Selection Audit (S1 frozen; S2 partial freeze — steady_driving only; S3 frozen; pre-registered censuses, results 2026-07-18)

**Census registration (2026-07-18, `experiments/map_census/`).** Three pre-registered censuses supply the calibration for this section — S1 step-event census, S2 steady-state residual-band census, S3 stuck-signal census (structural mirror of 4-S1, exact-constant convention for 1 kPa integer MAP). The three JSON pre-registrations are the binding specification; the design freedoms left open by the planning record were resolved as follows:

1. *S1 no-response label threshold:* per (operating-state × magnitude-bin) trip-equal weighted **P01** of the healthy conditional response distribution is binding; P05 is diagnostic-only. (A P05 label would fix the in-sample no-response base rate at 5% by construction, making the <1% freeze-branch criterion unsatisfiable; the real test is the divergence between the trip-equal threshold and the event-weighted base rate.) Bins whose P01 threshold falls below the 1 kPa MAP resolution are declared non-separable → `not_evaluable`.
2. *S1 branch structure is three-way:* (a) pooled m-of-n freeze; (b) restricted freeze on the subset of operating states individually satisfying the criteria (covering ≥ 50% of valid events), other states `not_evaluable`; (c) demotion to an S3 corroborating witness. The planning record listed only (a)/(c); (b) added per the project-wide three-branch convention.
3. *S2 concretizations:* high-load degeneracy criterion = band width (P99.5 − P0.5) ≥ 3× the widest band among idle/steady_driving/acceleration → `high_load` in-domain `not_evaluable` (guard, not verdict); steady-state mask thresholds = global trip-equal weighted P50 of |`pedal_slope`| and |`rpm_slope`| sustained ≥ 10 s (P25 sensitivity-only, cannot select the branch).
4. *S3 strengthened enable form:* two-of-three over the 120-s context stds (rpm/speed/pedal), not all-three AND — an all-three conjunction would predictably starve the 17/66 opportunity-coverage floor.

**Frozen decision rules (census results 2026-07-18, `experiments/map_census/outputs/`; pre-registered branch orderings followed, no post-result tuning, empty amendment logs):**

- **S1 Step-response — FROZEN (branch a; hard no-response only; P0106 candidate).**
  - *Rule:* per-state step detection on positive `pedal_slope` ≥ trip-equal P95 (idle `9.2` / steady_driving `11.4` / acceleration `18.6` / high_load `26.5` %/s); a valid event requires contiguous valid samples t0−1…t0+2; response = max over t+0…t+2 of |`map` − `map`(t0−1)|; no-response = response < per (state × magnitude-bin) trip-equal P01 (idle `8.0`/`4.0` kPa lo/hi; steady_driving bin_hi `3.0`; acceleration `4.0`/`9.0`; high_load `13.4`/`1.0`). steady_driving bin_lo is **non-separable** (P01 = 0 < 1 kPa resolution) → its events `not_evaluable`. Trigger = ≥ 3 no-response among the trip's most recent 4 valid events; `decision_margin` = no-response count − 3.
  - *Calibration evidence:* zero healthy 3-of-4 triggers; 2-of-3 rejected under the pre-registered ordering (2 healthy triggers in 1 trip); pooled event-weighted no-response rate 0.955% against the < 1% freeze criterion — **passes with thin margin (0.045 pp), disclosed as-is**; trip-equal rate 0.597% (divergence direction consistent with clustering, as the registration anticipated); coverage 56/66 trips (84.8%) ≥ 80%; nearest healthy miss 2-of-4; 942 valid events, 1176 detected.
  - *Caveats:* idle bins rest on 29/23 events — their P01 is effectively a sample minimum, statistically fragile (no per-bin minimum event count was pre-registered; recorded as a registration gap, not repaired post hoc). high_load bin_hi P01 = `1.0` kPa sits exactly at integer resolution — a 1-LSB flicker counts as a response, making the check near-vacuous in that bin; Stage 4 injection must probe both.
  - *Scope:* hard no-response only, per the scope statement below; graded-response degradation out of scope at 1 Hz.

- **S2 Steady-state residual — PARTIAL FREEZE (branch b; steady_driving only; no direct DTC — arbitration evidence).**
  - *Rule:* steady mask = `pedal_slope` exactly 0 AND |`rpm_slope`| ≤ 9 rpm/s, sustained ≥ 10 s (the trip-equal P50 of |`pedal_slope`| is 0.0 — the registered mask definition degenerates to exact pedal flatness; disclosed, not repaired). Within post_warmup `steady_driving`: evidence = `speed_density_maf_residual` outside the trip-equal band [`−4.04`, `+16.71`] g/s on the same side for ≥ 30 s. `idle` / `acceleration` / `high_load` are in-domain `not_evaluable` — excluded by the registered episode/margin/coverage criteria (idle and high_load had healthy 10-s episodes or margins < 10 s, and 30-s steady coverage below the 17/66 floor; acceleration coverage 3/66 at 10 s). The high-load degeneracy guard itself did **not** fire (band width 43.5 < 3 × 20.7 g/s).
  - *Calibration evidence:* at 30 s, zero healthy same-side episodes on either side (margins 19 s low / 12 s high); steady coverage 44/66 trips; 10-s persistence rejected by healthy episodes (low side 11 s, high side up to 18 s, 3 trips).
  - *Routing:* a trigger produces no code by itself — S1 or S3 co-trigger → attribute to MAP (P0106); otherwise the evidence flows to section 2's arbitration (P0101/P0102/P006A).

- **S3 Stuck MAP — FROZEN (branch a; P0106 candidate).**
  - *Rule:* engine on; `map`/`rpm`/`speed`/pedal channels valid, none imputed or suspicious; context material within a 120-s window — `rpm_std ≥ 241` OR `speed_std ≥ 12.4 km/h` OR `pedal_std ≥ 9.9 %` (trip-equal q50 thresholds). If the 60-s rolling max−min of `map` equals exactly 0 sustained for 120 s under material context → `triggered`. Minimum evaluable window 240 s; `pass` = ≥ 1 context opportunity with no trigger; otherwise `not_evaluable`.
  - *Calibration evidence:* zero healthy triggers; 10 healthy joint (context + flat) episodes observed, longest 31 s → 89 s margin against the 120-s requirement; context-opportunity coverage 66/66 trips, temporal coverage 66/66.
  - *Consistency note:* the speed q50 here (12.39 km/h) reproduces 4-S1's frozen 12.4 km/h gate — same quantile convention and pipeline, an independent cross-check of both censuses.
  - *Maturity:* research-grade P0106 stuck-candidate; detection capability awaits Stage 4 frozen-value injection.

*Scope statement (S1):* detects **hard no-response only** — a demand step followed by complete absence of MAP excursion. Slow or attenuated response degradation is not observable at 1 Hz sampling: the physical MAP response to a pedal step completes within a single sampling interval, so only the binary presence/absence of a response survives resampling. This matches the S1 symptom definition ("MAP unresponsive to demand step") and mirrors section 4's S1 hard-stuck-only narrowing — recorded as a capability limit, not a TBD. Graded-response sensitivity is deferred to Stage 4 injection as a descriptive study only.

*Superseded (2026-07-18):* the pre-census descriptive forms of the three checks — per-state `pedal_slope`/`map_slope` tolerances with their P99 anchors, per-state residual bands, and `map_stability` low-variance thresholds with their P05 anchors — are superseded by the frozen census-derived rules above and were removed from this section to keep a single executable specification. The anchors and full text survive in the census planning record (`experiments/map_census/` pre-registrations) and git history; they must not be read as rules.

- **Arbitration rule (shared evidence with section 2):** see section 2 Stage 3 — S2 evidence is attributed to MAP only when S1 or S3 also triggers; otherwise it flows to section 2's attribution logic.
- **IAT confidence wiring:** when 4-S2 cold-start IAT plausibility support is active, cap `confidence_tier` at `low` for IAT-dependent 5-S2 residual evidence. Do not alter 5-S1 or 5-S3.
- Output: three-state per sub-check, see Shared Conventions.

*Data-quality note:* `tps` in this dataset is saturated near 83.1-83.5% across nearly all operating states (idle, high load, and steady driving alike). A simple `100 - tps` inversion does not recover a physically meaningful throttle-opening signal, and `tps` does not correlate with `accel_pedal_mean`, `map`, `maf`, or `rpm` in the expected physical direction. Conversely, `map` shows a more physically plausible response to `pedal_slope` changes than to `tps`, supporting the choice of pedal demand as the substitute trigger signal. `tps` is therefore treated as unreliable for step-detection purposes in this failure and retained only as raw diagnostic context, not as a triggering input.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** suppressed step response (hold `map` constant across injected pedal-step windows) for S1; additive offset / gain error on `map` in steady-state windows for S2; frozen-value injection for S3. Injection on `map` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 6. idle_speed_control_or_surge_degradation — documented infeasibility (no DTC output)

**Component:** Idle-speed control / engine-speed control. **Investigated DTCs:** P0506 / P0507 [1]. CARB §1968.2 (e)(15.2.2)(B) mandates the monitor and defines the asymmetric default band — a malfunction when target idle cannot be achieved "within 200 rpm above the target speed or 100 rpm below" [13]; window-qualification and band precedents [7][8]; model-based FDI architecture [9].

**Finding (three pre-registered censuses; full record and calibrated rule drafts: `experiments/idle_speed/`):** no idle sub-check can produce a DTC-level verdict on this dataset, for three independent reasons:

1. No PID exposes the ECU's commanded idle target, and the healthy released-idle population is legitimately multi-modal (≈775 / 950 / 1050 rpm: warm-up fast idle and load compensation) — no stable reference band exists in either direction.
2. The persistence required by the calibration discipline (70 s) exceeds what this corpus offers: continuous released settled idle ≥70 s exists in only 1.5–9.1% of trips, below the pre-registered 20% deployment floor — a property of the driving profile, not of the rules.
3. The two Seat Leon manuals on file contain no numeric nominal idle speed; the authoritative value lives in per-engine ELSA/AU emissions data sheets (CZCA/CZEA), not obtained.

**Retained by-products (in the experiment record):** released-pedal admission threshold (`accel_pedal_mean ≤ 14.9%`), settled-idle filter, per-state amplitude baselines and sign-reversal statistics.

**Consequences:** the `anomaly_type` enum entry for idle is to be retired or marked non-executable (interface change, model-layer team). Revival requires any one of: a commanded-target PID, an idle-rich corpus, or the AU/EET nominal-idle data sheet for this engine.

---

Legacy / demoted (stay in the feature layer, no longer verdict or enable inputs): `cold_soak_candidate_flag` (circular gating — see 1-S4 / 4-S2); `map_stability`, `map_slope` (superseded by items 15 and 11); `accel_pedal_channel_ratio` (distribution-unstable, descriptive); `maf_map_cohesion` with `maf_derived_air_load_raw` / `map_derived_air_load_raw` (2-S1 downgraded — descriptive, F4 corroboration); `coolant_slope`, `coolant_stability` (superseded by items 6–7); the 60-s MAF rolling range (defined by the 2-S3a census, unconsumed — kept as the settled `maf_stability` spec for any future re-registration).


## Reference

[1] SAE International. (2007). *Diagnostic trouble code definitions* (SAE Standard No. J2012_200706). SAE International.

[2] Wang, L., Zou, X., Qin, H., & Geng, P. (2021). Design of OBD function test on production vehicle (PVE). *E3S Web of Conferences, 268*, 01047. https://doi.org/10.1051/e3sconf/202126801047

[3] *Method and apparatus to evaluate an intake air temperature monitoring circuit* (U.S. Patent No. 7,120,535). (2006). U.S. Patent and Trademark Office.

[4] Bosch, Robert GmbH. (2018). *Bosch automotive handbook* (10th ed.). SAE International.

[5] Nyberg, M., & Nielsen, L. (1997). Model based diagnosis for the air intake system of the SI-engine (SAE Technical Paper 970209). SAE International. https://doi.org/10.4271/970209

[6] *Fault identification diagnostic for intake system sensors* (U.S. Patent No. 6,701,282). (2004). U.S. Patent and Trademark Office.

[7] *Idle air control system diagnostic* (U.S. Patent No. 5,408,871). (1995). U.S. Patent and Trademark Office.

[8] *System for detecting functional abnormalities of idle speed control system* (U.S. Patent No. 5,936,152). (1999). U.S. Patent and Trademark Office.

[9] Montes-Solano, C. A., & Pisu, P. (2009). Model based fault detection and isolation in idle speed control of IC engines. Proceedings of the 7th IFAC Symposium on Fault Detection, Supervision and Safety of Technical Processes (SAFEPROCESS 2009), Barcelona, Spain. https://doi.org/10.3182/20090630-4-ES-2003.00149

[10] Yoo, I., Simpson, K., Bell, M., & Majkowski, S. (2000). *An engine coolant temperature model and application for cooling system diagnosis* (SAE Technical Paper No. 2000-01-0939). SAE International. https://doi.org/10.4271/2000-01-0939

[11] Ebrinc, A., & Cehreli, Z. (2007). *Overheating investigation on 5-cylinder engine* (SAE Technical Paper No. 2007-01-2570). SAE International. https://doi.org/10.4271/2007-01-2570

[12] International Organization for Standardization. (2018). *Road vehicles — Functional safety — Part 5: Product development at the hardware level* (ISO Standard No. 26262-5:2018). ISO.

[13] California Air Resources Board. *Title 13, California Code of Regulations, §1968.2: Malfunction and diagnostic system requirements — 2004 and subsequent model-year passenger cars, light-duty trucks, and medium-duty vehicles and engines*, sections (e)(10) (engine cooling system monitoring, pp. 50–52) and (e)(15) (comprehensive component monitoring, incl. the idle-speed-control clause (e)(15.2.2)(B)) (OAL 2006 amendment text; current codification cross-checked via Cornell LII, accessed 2026-07-17).

[14] Ford Motor Company. (2017). *2019 MY OBD system operation summary for gasoline engines* (Rev. Oct. 24, 2017), "Thermostat Monitor," pp. 150–151. https://www.fordservicecontent.com/ford_content/catalog/motorcraft/OBDSM1900.pdf

[15] *Method for detecting cooling system faults* (U.S. Patent No. 6,463,892). (2002). Ford Global Technologies. U.S. Patent and Trademark Office.

[16] *Abnormality detector apparatus for a coolant apparatus for cooling an engine* (U.S. Patent No. 6,200,021). (2001). Toyota Motor Corp. U.S. Patent and Trademark Office.

[17] *Vehicle thermal management system applying an integrated thermal management valve and a cooling circuit control method thereof* (U.S. Patent No. 10,934,924). (2021). Hyundai Motor Co. / Kia Motors Corp. U.S. Patent and Trademark Office.

[18] *Voice warning system for an automotive vehicle* (U.S. Patent No. 4,401,848). (1983). Nissan Motor Co. U.S. Patent and Trademark Office.

[19] SAE International. *E/E diagnostic test modes* (SAE Standard No. J1979). Cited for OBD-II PID physical measurement bounds (PID 0x0F, intake air temperature: −40 to 215°C).
