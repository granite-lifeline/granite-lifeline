# Proxy Failure Support

## Intro

Document proxy failures and supporting evidence. 

## Structure

For each proxy include:

* Component
* Supporting signals/features
* Proxy Definition
* Judgment Method
  * Observability Derivation
  * Literature Anchoring
  * Decision Rules
  * Empirical Falsifiability

## Shared Conventions

**Output schema (all proxies):** every sub-check reports three states — `pass` / `triggered` / `not_evaluable` — as `proxy_id + sub_check_id + direction + DTC label`, aggregated to proxy level. Guards and domain failures produce `not_evaluable`, never a verdict. Duration-gated checks record a `decision_margin` (with 1 Hz integer signals, margins within ~±5 s are borderline by resolution).

**Empirical-falsifiability protocol (Stage 4, all proxies):** TBD-1 synthetic injection onto held-out healthy windows, target signal only; TBD-2 detectability curve (detection rate vs. graded severity); TBD-3 false-positive rate on held-out healthy trips (split by `trip_id`, per §5.3 leakage rules); TBD-4 acceptance criteria set jointly after the first TBD-2/3 run — Stage 3 thresholds may be revised once, then re-frozen.

**Calibration discipline:** pre-registered branches and orderings; no edge-hugging parameters; out-of-calibration-domain → `not_evaluable`; literature contributes vehicle-independent judgment forms — absolute values are baseline-derived, or regulatory defaults used only as guards.


## 1. cooling_degradation

**Component:** Cooling system (Radiator / Water Pump / Thermostat / Coolant Circulation)  

**Supporting Features:** `coolant_temp`, `ambient_temp`, `speed`, `rpm`, `coolant_slope`, `coolant_ambient_delta`, `coolant_stability`  

**Proxy Definition:** Flag abnormal coolant thermal behavior, including sustained overheating after warm-up, coolant temperature rising without plateau, abnormally slow warm-up and coolant temperature implausible relative to ambient temperature after cold soak.  

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

#### Stage 3 — Decision Rules (S1–S3 frozen and calibrated; S4 remains a supporting flag)

S4 retains its provisional values from the previous revision ("Expected Pattern") and remains a low-confidence supporting flag (its cold-soak mechanism lives in section 4). S1–S3 are calibrated against the project baseline and **frozen** (experiment records: `experiments/cooling_s1/`, `experiments/cooling_s2/`, `experiments/cooling_s3/`):

- **S1 Slow warm-up (P0128) — FROZEN.** 
  - *Rule:* at a qualified cold start, assign a warm-up time budget. If `coolant_temp` reaches `T_target` before the budget expires → `pass`. If the budget expires with sufficient heat input and `coolant_temp` still below `T_target` → `triggered` (direction low, P0128). Everything else → `not_evaluable`. One decision per start; no per-sample thresholding.
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

**Component:** MAF sensor / intake air measurement path  

**Supporting Features:** `maf`, `map`, `rpm`, `intake_temp`, `speed_density_maf_residual`, `maf_derived_air_load_raw`, `map_derived_air_load_raw`, `maf_map_cohesion`, `maf_stability`, `map_stability`  

**Proxy Definition:** Triggered when `maf_map_cohesion` remains high. This proxy identifies inconsistency between the MAF-side air-load estimate and the MAP-side air-load estimate, mainly indicating MAF sensor drift, contamination, response delay, or abnormalities in the intake measurement chain.  

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Under the same operating condition, MAF-based load and MAP-based load should remain physically consistent. Persistent deviation between the two indicates a plausibility abnormality in the air-mass measurement chain. [4]

**Observability argument.** `maf` has no direct ground truth in the signal set; it is observable only through **redundancy** with the parallel speed-density estimate `f(rpm, map, intake_temp)`. Consistency is evaluable in any engine-on window, but attribution is limited: a two-estimator disagreement cannot by itself identify which side (MAF or MAP) is at fault. Isolation therefore relies on the arbitration rule with section 5 (Stage 3 below), which uses MAP-side dedicated checks as the tie-breaker. Transient windows (acceleration, gear shifts) degrade the comparison and must be masked or down-weighted.

**Failure-mode enumeration.**

| #  | Symptom | Statistic (feature) | Enable window | DTC label |
| -- | ------- | ------------------- | ------------- | --------- |
| S1 | MAF drift/contamination — persistent bias vs. parallel estimate | `maf_map_cohesion` sustained above tolerance AND `speed_density_maf_residual`sustained above tolerance | `steady_driving` | P0101 |
| S2 | MAF under-read at high load (classic contamination signature) | `maf_derived_air_load_raw` - `map_derived_air_load_raw` Negative residuals indicate MAF anomalies. (positive residuals point to MAP anomalies) | `high_load` | P0101 |
| S3 | Stuck/low MAF signal | `maf_stability` < baseline AND `map_stability` > baseline **TBD: feature not yet implemented** | `engine_on` with changing load context | P0102 |

#### Stage 2 — Literature Anchoring (TBD)

- Bosch Automotive Handbook [4] — **Borrowed: physical basis only** (two-estimator redundancy and air-mass measurement principles; existing source, retained).
- Nyberg & Nielsen [5], intake-system fault-isolation patent [6] — **Borrowed: model-based cross-check architecture** (MAF/MAP two-estimator reduced form; the throttle-model input (tps) is not available in this dataset, so this proxy uses only the two-estimator consistency check, not the full throttle-model implementation).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] (pre-2006 numbering (e)(16); renumbered in the OAL 2006 text) — **Borrowed: mandate** (comprehensive component monitoring requirement; MAF is an input component covered under this requirement).
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — **Borrowed: rationality fault diagnostic requirement** (defines the required diagnostic scope — circuit continuity, out-of-range, and rationality faults with "inappropriately high nor inappropriately low" two-sided verification; provides the regulatory basis for S1 (MAF drift — cross-sensor rationality) and S3 (stuck/low MAF signal — out-of-range)).

#### Stage 3 — Decision Rules (provisional)

Retained from the previous revision ("Expected Pattern"): `maf_map_cohesion` > 0.25-0.30 for 5-10 s as an initial proxy hint, not a final decision threshold; or under steady-state conditions, the standardized deviation between `maf_derived_air_load_raw` and `map_derived_air_load_raw` exceeds 25-30%. Transient acceleration, gear shifts, and rapid throttle-change windows should be down-weighted or masked.

- **TBD: per-`operating_state` tolerance bands from project baseline** (a single global cohesion threshold will misfire at high load; cf. the state-dependent bias documented in section 5's steady-state check note).
- **Arbitration rule (shared evidence with section 5):** cohesion high **and** section 5's MAP-dedicated checks (step-response, stuck-signal) normal → attribute to MAF, report under section 2 (P0101/P0102). Cohesion high **and** MAP-dedicated checks abnormal → attribute to MAP, report under section 5 (P0106). Cohesion high, both sides inconclusive → report F4 (P006A, no isolation).
- Output: three-state per sub-check, see Shared Conventions.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** multiplicative gain drift (0.7…0.95×) and additive offset on `maf`; load-dependent under-read (gain reduction scaled by `maf` magnitude) for S2; frozen-value injection for S3. Injection on `maf` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 3. accelerator_pedal_sensor

**Component:** Accelerator pedal position sensors (dual/redundant)   

**Supporting Features:** `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_channel_delta`, `accel_pedal_channel_ratio`, `pedal_slope`  

**Proxy Definition:** The proportional relationship, correlation, or dynamic behavior between pedal channels D/E is inconsistent. This proxies pedal sensor channel drift, contact abnormalities, or redundancy-monitoring failure.  

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** The ETC system uses two potentiometers on the pedal and throttle device to provide redundancy, and continuously checks all sensors and calculations that affect throttle opening while the engine is running. [1]

**Observability argument.** This is the only proxy whose reference is not a physical model but the **redundant channel itself**: each channel is the other's ground truth, so consistency is observable at every sample where both channels are valid — no operating-condition restriction is physically required (enable window = engine-on, both channels non-missing). One precondition must hold for the proxy to be meaningful: the two channels must be genuinely independent measurements, not gateway-duplicated copies (cleaning-QA degeneracy check; in this dataset the measured D/E correlation of 0.9824 with distinct value tracks confirms genuine dual-track redundancy).

**Failure-mode enumeration.**

| #   | Symptom                                                              | Statistic (feature)                                                                             | Enable window                                                                                                                 | DTC label |
| --- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------- |
| S1a | Channel relation drift — ratio/offset bias                          | `accel_pedal_channel_delta` >= max  AND `accel_pedal_channel_ratio out of threshold range` | `steady_driving`, `acceleration`, <br />The specific judgment threshold range varies under different working conditions | P2138     |
| S1b | Channel relation drift — extreme delta under all working conditions | `accel_pedal_channel_delta >= max`                                                            | any                                                                                                                           | P2138     |
| S2  | One channel frozen while the other moves                             | compare delta of`accel_pedal_d` and `accel_pedal_d`                                        | engine-on, active pedal motion                                                                                                | P2138     |
| S3  | Correlation collapse / noise burst                                   | `accel_pedal_channel_delta`rolling std                                                                    | engine-on                                                                                                                     | P2138     |


All modes map to P2138; sub-check identity and severity tier carry the differentiation in the output schema.

#### Stage 2 — Literature Anchoring

- SAE J2012 [1] — **Borrowed: DTC identities only** (P2138 pedal position sensor range/performance; the standard gives the DTC name, not the detection criteria).
- Bosch Automotive Handbook [4] — **Borrowed: ETC dual-sensor redundancy design** (p. 706; describes the dual-potentiometer architecture used in electronic throttle control systems).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] (pre-2006 numbering (e)(16); renumbered in the OAL 2006 text) — **Borrowed: mandate** (comprehensive component monitoring; pedal position sensor is an input component covered under this requirement, listed as part of the throttle control system input chain).
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — **Borrowed: rationality fault diagnostic requirement** (dual-channel accelerator pedal sensors are a direct application — channel correlation is a standard rationality check where each channel verifies the other's plausibility).
- ISO 26262-5:2018 [12] — **Borrowed: functional-safety framework for redundant sensing** (provides the safety-mechanism design rationale for dual-channel consistency monitoring as an automotive E/E systems diagnostic mechanism; the specific implementation is an OEM design choice).


#### Stage 3 — Decision Rules (provisional)

Retained from the previous revision ("Expected Pattern"): First learn the dataset normal-reference mapping `accel_pedal_e = a * accel_pedal_d + b`; trigger if the residual remains above 5-10 percentage points, the channel correlation coefficient is below 0.95, or one channel changes while the other channel freezes for more than 1 s.

- **TBD: recalibrate all three thresholds from the project baseline residual distribution** — measured healthy D/E correlation is 0.9824, so the 0.95 correlation bound and the 5-10 pp residual band are plausible but unverified against per-window quantiles; the 1 s freeze duration must be re-examined against 1 Hz sampling (a 1 s freeze is a single sample; minimum credible freeze duration at this rate is likely 2-3 s).
- Output: three-state per sub-check, see Shared Conventions.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** additive offset and gain error on one channel (S1); frozen-value on one channel during active pedal motion (S2); additive noise bursts (S3). Injection on one channel at a time, other channel untouched.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 4. intake_air_temperature_sensor_fault

**Component:** Intake-air temperature (IAT) sensor circuit and signal plausibility

**Supporting Features:** `intake_temp`, `ambient_temp`, `coolant_temp`, `speed`, `rpm`, `maf`, `map`, `operating_state`, `intake_ambient_delta`, `intake_temp_stability`, `segment_gap_seconds`, `cold_soak_candidate_flag`, `condition_confidence` 

**Proxy Definition:** The IAT signal fails a rationality (plausibility) check against ambient/other temperature references after a cold soak, or remains unresponsive (skewed/stuck) despite sustained vehicle speed and airflow that would normally change intake-air temperature. This proxies IAT sensor circuit degradation, signal drift, or signal sticking, consistent with SAE J2012 DTC P0111 (Intake Air Temperature Sensor 1 Circuit Range/Performance) [1].

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
| S4 | Abnormal heat-soak profile | `intake_temp` vs. project-derived idle-window reference | post-high-load idle/low-speed window | secondary engineering flag, no code |

#### Stage 2 — Literature Anchoring

- SAE J2012 [1] — **Borrowed: DTC identities only** (P0111 range/performance; P0112/P0113 out-of-range low/high); the standard gives names, not criteria.
- CARB Title 13 CCR §1968.2, section (e)(15) [13] — **Borrowed: mandate and the two-sided rationality form; no values.** Comprehensive-component monitoring requires input components to be checked for "lack of circuit continuity, out-of-range values, and, where feasible, rationality faults", with rationality verifying "that a sensor output is neither inappropriately high nor inappropriately low (e.g., “two-sided” diagnostics)" ((e)(15.2.1)(A)); rationality, circuit, and out-of-range faults must store distinct codes ((e)(15.2.1)(B)) — grounds S1/S2 (rationality) and the direction split in S3. The diesel mirror (f)(15.1.1)(A) names the intake air temperature sensor explicitly; the gasoline input-component list is non-exhaustive ("may include"). Jurisdiction note as in section 1.
- Delphi patent US7120535 [3] — **Borrowed: stuck/response-failure detection architecture** (measured vs. expected IAT evaluation; assignee and title verified against the patent record).
- Cold-soak test-design framework [2] — **Borrowed: methodology only** (soak duration as a standard test precondition); ECT-oriented, not IAT-specific (existing note, retained).
- Bosch Automotive Handbook [4, p. 786] — **Borrowed: physical basis only** (air density / effective oxygen content).
- SAE J1979 [19] — **Borrowed: physical measurement bounds** for S3 (PID 0x0F intake air temperature, −40…215°C).

#### Stage 3 — Decision Rules

*(S1 frozen from the pre-registered census; S2 executable v1; S3 range rule closed; S4 provisional engineering flag)*

- **S2 Cold-start IAT plausibility — executable v1** (low-confidence P0111 support; structural mirror of section 1's S4). Supersedes the `cold_soak_candidate_flag`-gated form: that flag requires IAT ≈ AAT inside its own enable condition, so a faulty IAT could never be flagged (circular gating). The flag stays in the feature layer but no longer enables S2.
  - *Eligibility (segment first row; any failure → `not_evaluable`):* `segment_gap ≥ 6 h` [2]; first-row RPM < 50 with an off→on transition observed later in the segment; ECT/IAT/AAT present, none imputed or suspicious. **ECT is the cold-soak witness:** `|ECT − AAT| ≤ 15°C`, else `not_evaluable` — a long gap with warm sensors cannot distinguish "vehicle ran during the gap" from a fault.
  - *Verdict:* `|IAT − AAT| > 7°C` → IAT cold-start plausibility candidate (direction inconsistent, low-confidence P0111 support); ≤ 7°C → `pass`.
  - *Calibration basis (both thresholds provisional):* the same 18-event strict baseline as section 1's S4 — healthy `|IAT−AAT|` max 5°C → verdict 7°C (zero healthy candidates); healthy `|ECT−AAT|` max 11°C → witness 15°C. Thresholds are per-sensor, not numerically mirrored; both sensors far from AAT → both mirror checks `not_evaluable`.
  - *Consumers:* confidence modifier for co-occurring IAT anomalies (S1/S4 of this section) via `condition_confidence` tiering — never a standalone P0111 trigger. Cross-failure note: `intake_temp` feeds the speed-density estimates of sections 2 and 5; an S2 candidate should down-weight their confidence (wiring to be added in those sections' passes).
  - *Note:* [2] documents the cold-soak framework for ECT (P0116) checks, not IAT specifically — cited for methodology only.

- **S1 Stuck/no-response IAT — FROZEN (hard-stuck only; P0111 candidate).** Supersedes the "sustained airflow" form.
  - *Rule:* engine on; IAT/speed/MAF/RPM valid, none imputed or suspicious; context change within a 120-s window is material — `speed_std ≥ 12.4 km/h` OR `maf_std ≥ 8.5 g/s` (healthy-baseline quantiles of 120-s window variation; **TBD: record exact quantile definition and trip weighting**, values in `experiments/intake_s1/`). If `intake_temp_stability ≤ 0.1°C` is then sustained for 120 s → `triggered` (P0111 stuck-IAT candidate). Minimum evaluable window 240 s; `pass` = at least one evaluable context-change opportunity with no trigger; otherwise `not_evaluable`.
  - *Calibration evidence (pre-registered census, `experiments/intake_s1/`):* zero healthy triggers; longest healthy flat episode under material context change 29 s → 91 s headroom against the 120-s requirement; robust to relaxing stability to 0.25°C (longest 47 s, still zero). Context opportunities: 306 episodes across 66/66 trips.
  - *Integer-resolution caveat:* IAT is 1°C-quantized at 1 Hz — 61.8% of adjacent samples are unchanged and the longest raw constant-value run is 149 s. All of it lies outside the enable gate (steady cruise), which is exactly why the context-change gate is mandatory (cf. the frozen-ECT deferral in section 1).
  - *Scope statement:* detects **hard-stuck / no-response only**. Slow drift and mild skew are not observable without a reference model; cold-start offset is partially covered by S2. This narrows the proxy definition's "signal drift" claim — recorded as a capability limit, not a TBD.
  - *No in-sample tuning occurred* under the pre-registered grid ordering (one-line confirmation of the recorded ordering pending from the experiment workstream); no LOTO required.
  - *Maturity:* research-grade P0111 stuck-candidate; detection capability awaits Stage 4 frozen-IAT injection. `tps` remains excluded as an airflow proxy (unreliable in this dataset).

- *Post-high-load heat-soak check (dataset-derived, no direct DTC support):* Rather than during high-load driving itself, elevated `intake_temp` is more physically expected to appear in an idle or low-speed window that follows a period of high load — a classic heat-soak pattern in which residual engine-bay heat conducts into the stationary intake path once ram-air cooling stops. This project's own baseline is consistent with that mechanism: within `post_warmup__idle` windows, `intake_temp` reaches a P99 of approximately 63°C, noticeably higher than the P99 seen during `post_warmup__high_load` driving itself (~45°C) [own baseline, not literature-sourced]. `intake_temp` sustained above this project-derived idle-window reference for an extended duration is treated as a secondary engineering flag rather than a standardized threshold, since no SAE/OEM DTC defines a fixed physical high-temperature limit for IAT under normal (non-circuit-fault) conditions; this threshold should be re-validated as more trip data accumulates rather than treated as fixed. **Status: provisional engineering flag (S4), frozen as-is — no DTC, lowest confidence tier.**

- Output: three-state per sub-check, see Shared Conventions. S3 range rule (TBD closed): any sample of `intake_temp` outside −40…215°C [19] → `triggered` (direction low → P0112, high → P0113); evaluated continuously; `not_evaluable` only when the signal is missing.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** frozen-value injection during qualified context-change windows (S1); additive offset at qualified cold-start samples (S2); out-of-range clamp (S3). Injection on `intake_temp` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — per the Shared Conventions Stage-4 protocol.

## 5. map_load_signal_plausibility_fault

**Component:** Intake manifold absolute pressure (MAP) sensor / load-signal plausibility

**Supporting Features:** `map`, `maf`, `rpm`, `accel_pedal_mean`, `pedal_slope`, `intake_temp`, `speed_density_maf_residual`, `map_slope`, `map_stability`

**Excluded / Diagnostic Context:** `tps` is retained only as raw diagnostic context and is not used as a triggering input for this proxy, because its physical meaning is unreliable in the current KIT Seat Leon dataset (see data-quality note below).

**Proxy Definition:** MAP fails to reasonably reflect load changes, or its relationship with MAF, driver-demand/load context, and engine speed is inconsistent. This proxies MAP sensor drift, blockage, hose issues, signal sticking, or load-measurement-chain abnormalities, consistent primarily with SAE J2012 DTC P0106 (Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance) [1]. This project's step-response implementation substitutes accelerator-pedal demand for throttle position as the trigger signal because `tps` in this dataset does not behave as a physically interpretable throttle-opening percentage (see data-quality note below). This approximates the diagnostic intent of P0068 (MAP/MAF - Throttle Position Correlation) rather than implementing its literal throttle-position-based definition; P0106 remains the primary, unaffected DTC support for this failure.

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Intake manifold absolute pressure is a preferred method for monitoring engine load, and relative charge can be determined from available measurement signals such as MAF or MAP through an intake-manifold model [4, pp. 897, 912, 914, 919, 928]. In the original model-based intake-system diagnostic architecture, a throttle model estimates mass flow through the throttle body from ambient pressure, MAP, throttle position, and intake air temperature, while an intake-manifold model estimates MAP from the throttle-body flow and engine pumping flow; measured and modeled values are then cross-compared to detect and isolate sensor faults [5][6]. In this project, the literal throttle-position trigger is replaced by a driver-demand trigger because the available `tps` channel is not trustworthy, while the steady-state MAP/MAF/RPM consistency check remains unchanged. If MAP is distorted, load, ignition timing, fuel injection, and torque calculations will all be biased [4].

**Observability argument.** MAP is verifiable against three independent references, each defining one sub-check: the **command side** (a driver-demand step must produce a MAP response — observable at pedal step events), the **parallel estimator** (MAF-derived air load must agree with MAP-derived air load — observable in steady-state windows; this is the evidence shared with section 2, subject to the arbitration rule), and the **expected own-dynamics** (healthy MAP varies with operating context — a near-zero-variance window while context changes is only explainable by signal sticking).

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature)| Enable window | DTC label |
| - | ------- | ------------------ | ------------- | --------- |
| S1 | MAP unresponsive to demand step                                                             | `abs(map_slope)` near zero within response window after `pedal_slope` step event | pedal step events, per`operating_state`                    | P0106                                                        |
| S2 | Steady-state MAP/MAF cross-inconsistency                                                    | `speed_density_maf_residual` outside per-state tolerance                           | `steady_driving`                                           | P0106                                                        |
| S2_Arbitration | If MAP_F1 concurrent trigger: MAP fault;  Elif signed_residual large negative: MAF fault | `maf_derived_air_load_raw - map_derived_air_load_raw`                              | on F2 trigger                                                | P0106 (shared evidence with 3.2 — arbitration rule applies) |
| S3 | Stuck MAP signal                                                                            | `map_stability <` baseline AND `maf_stability` > baseline                       | engine-on, not in idle state, with other signals fluctuating | P0106                                                        |

#### Stage 2 — Literature Anchoring

- Bosch Automotive Handbook [4] — **Borrowed: physical basis only** (MAP as load-monitoring method, pp. 897, 912, 914, 919, 928; existing source, retained).
- Nyberg & Nielsen [5], intake-system fault-isolation patent [6] — **Borrowed: model-based cross-check architecture** (their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation; existing note, retained).
- CARB Title 13 CCR §1968.2 (e)(15.1.1)(A) [13] (pre-2006 numbering (e)(16); renumbered in the OAL 2006 text) — **Borrowed: mandate** (comprehensive component monitoring; MAP sensor is an input component covered under this requirement).
- CARB Title 13 CCR §1968.2 (e)(15.2.1)(A) [13] — **Borrowed: rationality fault diagnostic requirement** (MAP rationality explicitly demonstrated through two-sided verification — the signal must be neither "inappropriately high" (sensor stuck high vs. pedal demand) nor "inappropriately low" (sensor stuck low, or frozen at ambient); directly supports the step-response check (S1), the cross-estimator check (S2), and the stuck-signal check (S3)).
- CARB Title 13 CCR §1968.2 (e)(15.3.1)(A) [13] — **Borrowed: continuous monitoring for range**; (e)(15.3.1)(B) — **rationality per manufacturer-defined conditions**.
- Note on substituting pedal demand for throttle position: The regulation at (e)(15.2.1)(A) states rationality checks shall be performed "to the extent feasible" and "where feasible." The specific rationality check method is not prescribed — the regulation requires the outcome (two-sided verification), not the means. This project's substitution of the unreliable `tps` signal with the validated pedal-demand signal is consistent with this regulatory framework.


#### Stage 3 — Decision Rules

*(retained in full from the previous revision ("Expected Pattern"), including all per-state calibration anchors)*

- *Step-response check:* Following an `accel_pedal_mean` step event detected via `pedal_slope` exceeding a calibrated magnitude, `abs(map_slope)` remains near zero within a calibrated response window - indicating MAP is not responding to driver torque demand. This keeps the same model-based intake-flow rationality architecture, but uses the validated pedal-demand signal as the command-side trigger instead of the unreliable `tps` signal; a persistent mismatch between expected load response and measured MAP over a calibrated interval is flagged as a rationality failure [5][6].

  *Note: the specific step-magnitude and response-window values (e.g., a threshold on `pedal_slope` and a sub-second response window) are OEM/platform-calibrated parameters within this model-based architecture, not values fixed by SAE J2012, and should be derived empirically from this project's own healthy-trip baseline. References [5][6] support the general architecture of comparing modeled-vs-measured MAP to detect rationality failures, but their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation. Both the step-detection threshold on `pedal_slope` and the "near zero" tolerance on `map_slope` must be calibrated per `operating_state`, not as single global values. In the current high-confidence post-warmup baseline, positive `pedal_slope` P99 rises from about `8.1 %/s` at idle to `10.0 %/s` in steady driving, `24.3 %/s` during acceleration, and `27.85 %/s` at high load. Similarly, positive `map_slope` P99 rises from about `6 kPa/s` at idle to `23 kPa/s` in steady driving, `45 kPa/s` during acceleration, and `74 kPa/s` at high load. A response-window tolerance sized for idle would therefore flag normal high-load MAP fluctuation as anomalous, while a tolerance sized for high load would fail to catch a genuinely stuck MAP at idle.*

- *Steady-state cross-consistency check:* Under steady-state conditions, the standardized deviation between the MAF-derived air load and the MAP-derived air load (`speed_density_maf_residual`) exceeds a calibrated tolerance - directly analogous to the throttle-model/intake-manifold-model cross-check in which MAF-side and MAP-side flow estimates are compared against each other and against direct sensor measurements to isolate which sensor is inconsistent [5][6].

  *Note: `speed_density_maf_residual` carries a strong operating-state-dependent bias even under healthy conditions in this project's baseline - for example, its median is near zero at idle/steady-driving/acceleration but rises to roughly +7.5 g/s at high load, with the high-load P99 climbing to about 61 g/s versus single digits or low tens at other states. A single global tolerance would therefore misfire under high-load operation by flagging healthy behavior, while also being too loose at idle. This check must use a per-`operating_state` tolerance band derived from this project's own baseline distribution, not one fixed global threshold.*

- *Stuck-signal check:* `map_stability` remains below a calibrated low-variance threshold for an extended engine-running window while operating conditions (RPM, pedal demand, MAF, or speed/load state) are changing — consistent with MAP signal-sticking failure modes covered under the same rationality-diagnostic family.

  *Note: This check should now use `map_stability` as the primary sustained-window feature rather than relying on consecutive zero `map_slope` samples. The low-variance threshold and required duration must be calibrated per `operating_state`, because healthy MAP variability differs substantially between idle, steady-driving, acceleration, and high-load windows. As an initial lower-tail calibration anchor from the current high-confidence post-warmup baseline, `map_stability` P05 is approximately `1.1 kPa` at idle, `3.0 kPa` in steady driving, `3.1 kPa` during acceleration, and `12.3 kPa` at high load. These values are provisional state-specific starting points, not final fault thresholds; the check must also require changing RPM, pedal demand, MAF, or speed/load context over a sustained window.*

- **Arbitration rule (shared evidence with section 2):** see section 2 Stage 3 — S2 evidence is attributed to MAP only when S1 or S3 also triggers; otherwise it flows to section 2's attribution logic.
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

## Pending Work — Feature-Layer Reconciliation

The per-section Supporting-Features lines are Stage-1 hypotheses. The frozen rules consume a different, smaller set: some declared features were replaced by multi-minute aggregates (1 Hz integer resolution), one was decomposed because it contained its own verdict (`cold_soak_candidate_flag`), and several new features were imposed by the literature-anchored rule forms. **For implementation, the single authoritative list below supersedes the Supporting-Features lines. It grows as the remaining sections freeze.**

Features to generate (consumed by the frozen/executable rules of sections 1 and 4):

1. `engine_start_observed` / `engine_start_episode_id` — RPM off→on crossing (RPM < 50 → ≥ 50) within a segment; all episode-scoped features key on this, not on `segment_id` (a segment can contain multiple starts).
2. `elapsed_since_engine_start` — seconds since the observed start event (never derived from `thermal_state`).
3. `ect_start`, `aat_start`, `iat_start` — episode-start values (eligibility of 1-S1, 1-S4, 4-S2).
4. `time_to_target_79c` — time from engine start to first ECT ≥ T_target, with right-censoring recorded (1-S1).
5. `maf_integral_180s` — trailing 180-s MAF integral, reset per engine-start episode, not per segment (heat-input guard, 1-S1).
6. `ect_rate_180s` — (ECT[t] − ECT[t−180 s]) / 3, °C/min (1-S3).
7. `ect_exceedance_run_s` — running duration of `coolant_temp` at or above a given threshold (persistence for 1-S2/1-S3).
8. `speed_std_120s`, `maf_std_120s` — 120-s rolling standard deviations (context-change gate, 4-S1).
9. `intake_temp_stability` — rolling standard deviation of `intake_temp`, window per the census definition (verdict input, 4-S1).
10. `decision_margin` — per-decision output field (budget − time_to_target for 1-S1; analogous margins for duration-gated checks).

Existing features retained as consumed: `segment_gap_seconds`, `coolant_ambient_delta`, `intake_ambient_delta`, `thermal_state`, `operating_state`, `condition_confidence`, and the imputed/suspicious data-quality flags.

Legacy: `cold_soak_candidate_flag` stays in the feature layer but is no longer an enable input for any rule (circular gating — see 1-S4 / 4-S2).


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
