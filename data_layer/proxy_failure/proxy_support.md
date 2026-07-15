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
| S5 | Stuck/frozen ECT signal | `coolant_stability` near zero across thermal transients | any engine-on window with expected thermal change | P0116/P0117/P0118 — **TBD: sub-check not yet specified** |

**Ambient compensation note.** Warm-up duration scales with ambient temperature (corroborated independently by the Leon owner's manual, p. 112: the warm-up phase "also depends on the outside temperature"). S1's expected duration must therefore be conditioned on `ambient_temp` at engine start — **TBD: binning vs. regression form.**

#### Stage 2 — Literature Anchoring (TBD)

- Bosch Automotive Handbook [4] — cooling-system function and thermal-balance argument (existing source, retained).
- CARB Title 13 CCR §1968.2 mandates thermostat monitoring (failure of coolant to reach regulating temperature) — **TBD: extract exact clause reference.**
- **TBD: OEM/patent precedent for overheat detection and plateau-loss windows.**

#### Stage 3 — Decision Rules (provisional; literature-derived values, not yet baseline-calibrated)

The following provisional values are retained from the previous revision ("Expected Pattern"). All are literature-informed engineering values and **must be recalibrated against the project baseline (TBD)** — per thermal state, and for S1 additionally per ambient-temperature band:

- S2 Overheating: coolant_temp > 105°C for 3-5 min after warm-up
- S3 Rising without plateau: coolant_slope > 2°C/min for 2-3 min
- S1 Slow warm-up: coolant_temp < 70-75°C after 10-15 min running
- S4 Sensor plausibility: abs(coolant_temp - ambient_temp) > 10-15°C after cold soak (cold-soak qualification via `cold_soak_candidate_flag`, see feature 2.20 and section 3.4)

Output: three-state per sub-check (`pass` / `triggered` / `not_evaluable`), reported as `proxy_id + sub_check_id + direction + DTC label` — same schema as 3.6.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** slow-ramp warm-up retardation and depressed plateau on `coolant_temp` (S1/S3); sustained positive offset above critical band (S2); frozen-value and start-offset injections (S4/S5).
- **TBD-2/3/4:** detectability curve, false-positive rate on held-out trips, acceptance criteria — same protocol as 3.6 Stage 4.

## 2. air_intake_maf_anomaly

**Component:** MAF sensor / intake air measurement path  

**Supporting Features:** `maf`, `map`, `rpm`, `intake_temp`, `maf_derived_air_load_raw`, `map_derived_air_load_raw`, `maf_map_cohesion`  

**Proxy Definition:** Triggered when `maf_map_cohesion` remains high. This proxy identifies inconsistency between the MAF-side air-load estimate and the MAP-side air-load estimate, mainly indicating MAF sensor drift, contamination, response delay, or abnormalities in the intake measurement chain.  

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Under the same operating condition, MAF-based load and MAP-based load should remain physically consistent. Persistent deviation between the two indicates a plausibility abnormality in the air-mass measurement chain. [4]

**Observability argument.** `maf` has no direct ground truth in the signal set; it is observable only through **redundancy** with the parallel speed-density estimate `f(rpm, map, intake_temp)`. Consistency is evaluable in any engine-on window, but attribution is limited: a two-estimator disagreement cannot by itself identify which side (MAF or MAP) is at fault. Isolation therefore relies on the arbitration rule with section 3.5 (Stage 3 below), which uses MAP-side dedicated checks as the tie-breaker. Transient windows (acceleration, gear shifts) degrade the comparison and must be masked or down-weighted.

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| F1 | MAF drift/contamination — persistent bias vs. parallel estimate | `maf_map_cohesion` sustained above tolerance | steady-state, per `operating_state` | P0101 |
| F2 | MAF under-read at high load (classic contamination signature) | signed residual of `maf_derived_air_load_raw` vs. `map_derived_air_load_raw` at high load | `high_load_transient` / `high_speed_cruise` | P0101 |
| F3 | Stuck/low MAF signal | `maf_stability` (rolling std, analogous to `map_stability`) — **TBD: feature not yet implemented (see feature backlog)** | engine-on with changing load context | P0102 |
| F4 | Unattributable MAF–MAP disagreement | `maf_map_cohesion` high, 3.5 MAP-dedicated checks inconclusive | steady-state | P006A (air-metering chain inconsistency, no isolation) |

#### Stage 2 — Literature Anchoring (TBD)

- Bosch Automotive Handbook [4] (existing source, retained).
- Model-based MAF/MAP cross-check architecture: same references as 3.5 ([5][6]) — the throttle-model input is not available here (unreliable `tps`), so this proxy uses the two-estimator reduced form. **TBD: confirm citation scope.**
- **TBD: CARB §1968.2 MAF rationality monitoring clause.**

#### Stage 3 — Decision Rules (provisional)

Retained from the previous revision ("Expected Pattern"): `maf_map_cohesion` > 0.25-0.30 for 5-10 s as an initial proxy hint, not a final decision threshold; or under steady-state conditions, the standardized deviation between `maf_derived_air_load_raw` and `map_derived_air_load_raw` exceeds 25-30%. Transient acceleration, gear shifts, and rapid throttle-change windows should be down-weighted or masked.

- **TBD: per-`operating_state` tolerance bands from project baseline** (a single global cohesion threshold will misfire at high load; cf. the state-dependent bias documented in 3.5's steady-state check note).
- **Arbitration rule (shared evidence with 3.5):** cohesion high **and** 3.5's MAP-dedicated checks (step-response, stuck-signal) normal → attribute to MAF, report under 3.2 (P0101/P0102). Cohesion high **and** MAP-dedicated checks abnormal → attribute to MAP, report under 3.5 (P0106). Cohesion high, both sides inconclusive → report F4 (P006A, no isolation).
- Output: three-state per sub-check, same schema as 3.6.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** multiplicative gain drift (0.7…0.95×) and additive offset on `maf`; load-dependent under-read (gain reduction scaled by `maf` magnitude) for F2; frozen-value injection for F3. Injection on `maf` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — same protocol as 3.6 Stage 4.

## 3. accelerator_pedal_sensor

**Component:** Accelerator pedal position sensors (dual/redundant)   

**Supporting Features:** `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_channel_delta`, `accel_pedal_channel_ratio`, `pedal_slope`  

**Proxy Definition:** The proportional relationship, correlation, or dynamic behavior between pedal channels D/E is inconsistent. This proxies pedal sensor channel drift, contact abnormalities, or redundancy-monitoring failure.  

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** The ETC system uses two potentiometers on the pedal and throttle device to provide redundancy, and continuously checks all sensors and calculations that affect throttle opening while the engine is running. [1]

**Observability argument.** This is the only proxy whose reference is not a physical model but the **redundant channel itself**: each channel is the other's ground truth, so consistency is observable at every sample where both channels are valid — no operating-condition restriction is physically required (enable window = engine-on, both channels non-missing). One precondition must hold for the proxy to be meaningful: the two channels must be genuinely independent measurements, not gateway-duplicated copies (cleaning-QA degeneracy check; in this dataset the measured D/E correlation of 0.9824 with distinct value tracks confirms genuine dual-track redundancy).

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| F1 | Channel relation drift — ratio/offset bias | residual of learned mapping `accel_pedal_e = a·accel_pedal_d + b`; `accel_pedal_channel_delta`, `accel_pedal_channel_ratio` | engine-on, both channels valid | P2138 |
| F2 | One channel frozen while the other moves | per-channel variance asymmetry over rolling window; `pedal_slope` on one channel with zero slope on the other | engine-on, active pedal motion | P2138 |
| F3 | Correlation collapse / noise burst | rolling correlation below bound; residual spike count | engine-on | P2138 |

All modes map to P2138; sub-check identity and severity tier carry the differentiation in the output schema.

#### Stage 2 — Literature Anchoring (TBD)

- SAE J2012 [1] — DTC definition (existing source, retained).
- Bosch Automotive Handbook [4] — ETC dual-sensor redundancy design. **TBD: page reference.**
- **TBD: CARB §1968.2 comprehensive-component monitoring clause (pedal position sensor as input component).**

#### Stage 3 — Decision Rules (provisional)

Retained from the previous revision ("Expected Pattern"): First learn the dataset normal-reference mapping `accel_pedal_e = a * accel_pedal_d + b`; trigger if the residual remains above 5-10 percentage points, the channel correlation coefficient is below 0.95, or one channel changes while the other channel freezes for more than 1 s.

- **TBD: recalibrate all three thresholds from the project baseline residual distribution** — measured healthy D/E correlation is 0.9824, so the 0.95 correlation bound and the 5-10 pp residual band are plausible but unverified against per-window quantiles; the 1 s freeze duration must be re-examined against 1 Hz sampling (a 1 s freeze is a single sample; minimum credible freeze duration at this rate is likely 2-3 s).
- Output: three-state per sub-check, same schema as 3.6.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** additive offset and gain error on one channel (F1); frozen-value on one channel during active pedal motion (F2); additive noise bursts (F3). Injection on one channel at a time, other channel untouched.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — same protocol as 3.6 Stage 4.

## 4. intake_air_temperature_sensor_fault

**Component:** Intake-air temperature (IAT) sensor circuit and signal plausibility

**Supporting Features:** `intake_temp`, `ambient_temp`, `coolant_temp`, `speed`, `rpm`, `maf`, `map`, `operating_state`, `intake_ambient_delta`, `intake_temp_stability`, `segment_gap_seconds`, `cold_soak_candidate_flag`, `condition_confidence` 

**Proxy Definition:** The IAT signal fails a rationality (plausibility) check against ambient/other temperature references after a cold soak, or remains unresponsive (skewed/stuck) despite sustained vehicle speed and airflow that would normally change intake-air temperature. This proxies IAT sensor circuit degradation, signal drift, or signal sticking, consistent with SAE J2012 DTC P0111 (Intake Air Temperature Sensor 1 Circuit Range/Performance) [1].

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Intake air temperature directly affects air density and combustion efficiency — colder air is denser, and heated intake air reduces effective oxygen content [4, p. 786]. Under normal operation, IAT should closely track ambient/coolant temperature references immediately after a cold soak, before engine heat has propagated to the intake path, and should respond dynamically to changes in vehicle speed and airflow once the engine is running. A signal that is implausible relative to reference sensors at cold start, or that fails to vary despite sustained flow, indicates the sensor circuit is not measuring true intake-air temperature — consistent with the OEM diagnostic logic underlying P0111 [1][2][3].

**Observability argument.** IAT plausibility is observable against three independent references, each with its own window and confidence level: (a) the **equalization reference** at cold-soak start — the strongest physical check, but of limited availability in this dataset (true soak duration cannot be reconstructed from logged data; strict cold starts are rare), which is precisely why the cold-soak check is demoted to a low-confidence supporting flag rather than a primary judgment (see Stage 3); (b) the **thermal-response reference** under sustained airflow — a healthy IAT must vary when flow context changes, observable in any sustained moving window, and therefore the primary judgment; (c) the **post-load heat-soak signature** — a dataset-derived secondary reference with no direct DTC support.

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| F1 | Stuck/skewed IAT — no thermal response | `intake_temp_stability` near zero despite sustained speed/load | sustained-airflow window | P0111 |
| F2 | IAT implausible at cold start | `intake_ambient_delta` at segment start, qualified by `cold_soak_candidate_flag` | cold-soak segment start | P0111 (confidence modifier, not standalone trigger) |
| F3 | IAT out of physical range | raw bounds on `intake_temp` — **TBD: explicit range sub-check not yet specified** | any | P0113 |
| F4 | Abnormal heat-soak profile | `intake_temp` vs. project-derived idle-window reference | post-high-load idle/low-speed window | secondary engineering flag, no code |

#### Stage 2 — Literature Anchoring

- SAE J2012 [1] — P0111/P0113 definitions (existing source, retained).
- Cold-soak test-design framework [2] — documents cold-soak duration as a standard test precondition for ECT (P0116) rationality checks; cited for methodology only, not as an IAT-specific primary source (existing note, retained).
- IAT monitoring-circuit evaluation patent [3] — stuck/response-failure detection architecture (existing source, retained).
- Bosch Automotive Handbook [4, p. 786] — physical basis (existing source, retained).

#### Stage 3 — Decision Rules

*(retained in full from the previous revision ("Expected Pattern"); calibration parameters marked therein remain project-calibrated values, not SAE-mandated constants)*

- *Cold-soak plausibility check (low-confidence candidate, not a confirmed rationality check):* True cold-soak duration cannot be reliably reconstructed from this dataset, since `engine_on_flag` only reflects whether the engine is running within a recorded sample and cannot confirm that the vehicle stayed off across a gap between segments/trips. This check is therefore demoted from a primary detection judgment to a low-confidence supporting flag.

  *Definition:* `cold_soak_candidate_flag` is set when `segment_gap_seconds` (time since the previous segment/trip's last sample) exceeds a calibrated duration (on the order of six to eight hours, per [2]), AND the first sample of the new segment shows both `coolant_temp` and `intake_temp` close to `ambient_temp`. This dual-signal cross-check is required precisely because the time gap alone cannot prove the vehicle was actually off throughout — a long gap with normal (non-decayed) coolant/intake temperature at restart indicates the vehicle was very likely operated during the gap, while a long gap with both temperatures converged toward ambient is much stronger physical evidence of genuine soak, largely independent of what happened during the untracked interval.

  *Usage:* Once triggered, `cold_soak_candidate_flag` should not independently produce a fault verdict at the same confidence level as the skewed-signal or heat-soak checks below. It should instead be used as a confidence modifier — e.g., raising the confidence of a co-occurring `intake_ambient_delta` anomaly at that same sample, or being logged as a separate low-confidence candidate consistent with this project's existing `condition_confidence` (high/medium/low) tiering — rather than as a standalone P0111 trigger.

  *Note: [2] documents this cold-soak test-design framework for ECT (P0116) rationality checks, not IAT specifically, and is cited here only for the underlying methodology (cold-soak duration as a standard test precondition), not as an IAT-specific primary source.*

- *Skewed/stuck-signal check:* Once speed/load context (`speed`, `rpm`, `maf`, `map`, or `operating_state`) indicates sustained airflow, `intake_temp_stability` (a rolling standard deviation of `intake_temp` over that window, analogous to `coolant_stability`) stays near zero despite sustained speed/load — indicating the signal is not tracking expected thermal dynamics [3]. This sustained-window check is the primary judgment for this pattern, since a single-sample or instantaneous-slope check cannot distinguish a truly stuck signal from ordinary sample-to-sample noise. `tps` is not used as an airflow proxy in this dataset because its physical meaning is unreliable.

  As with the cold-soak check, the window length and drift/variance thresholds are implementation-specific calibration parameters, not SAE-mandated constants, and should be tuned against this project's own data.

- *Post-high-load heat-soak check (dataset-derived, no direct DTC support):* Rather than during high-load driving itself, elevated `intake_temp` is more physically expected to appear in an idle or low-speed window that follows a period of high load — a classic heat-soak pattern in which residual engine-bay heat conducts into the stationary intake path once ram-air cooling stops. This project's own baseline is consistent with that mechanism: within `post_warmup__idle` windows, `intake_temp` reaches a P99 of approximately 63°C, noticeably higher than the P99 seen during `post_warmup__high_load` driving itself (~45°C) [own baseline, not literature-sourced]. `intake_temp` sustained above this project-derived idle-window reference for an extended duration is treated as a secondary engineering flag rather than a standardized threshold, since no SAE/OEM DTC defines a fixed physical high-temperature limit for IAT under normal (non-circuit-fault) conditions; this threshold should be re-validated as more trip data accumulates rather than treated as fixed.

- Output: three-state per sub-check, same schema as 3.6. **TBD: F3 explicit range bounds.**

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** frozen-value injection during sustained-flow windows (F1); additive offset at cold-start samples (F2); out-of-range clamp (F3). Injection on `intake_temp` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — same protocol as 3.6 Stage 4.

## 5. map_load_signal_plausibility_fault

**Component:** Intake manifold absolute pressure (MAP) sensor / load-signal plausibility

**Supporting Features:** `map`, `maf`, `rpm`, `accel_pedal_mean`, `pedal_slope`, `intake_temp`, `speed_density_maf_residual`, `map_slope`, `map_stability`

**Excluded / Diagnostic Context:** `tps` is retained only as raw diagnostic context and is not used as a triggering input for this proxy, because its physical meaning is unreliable in the current KIT Seat Leon dataset (see data-quality note below).

**Proxy Definition:** MAP fails to reasonably reflect load changes, or its relationship with MAF, driver-demand/load context, and engine speed is inconsistent. This proxies MAP sensor drift, blockage, hose issues, signal sticking, or load-measurement-chain abnormalities, consistent primarily with SAE J2012 DTC P0106 (Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance) [1]. This project's step-response implementation substitutes accelerator-pedal demand for throttle position as the trigger signal because `tps` in this dataset does not behave as a physically interpretable throttle-opening percentage (see data-quality note below). This approximates the diagnostic intent of P0068 (MAP/MAF - Throttle Position Correlation) rather than implementing its literal throttle-position-based definition; P0106 remains the primary, unaffected DTC support for this failure.

### Judgment Method

#### Stage 1 — Observability Derivation

**Monitored function.** Intake manifold absolute pressure is a preferred method for monitoring engine load, and relative charge can be determined from available measurement signals such as MAF or MAP through an intake-manifold model [4, pp. 897, 912, 914, 919, 928]. In the original model-based intake-system diagnostic architecture, a throttle model estimates mass flow through the throttle body from ambient pressure, MAP, throttle position, and intake air temperature, while an intake-manifold model estimates MAP from the throttle-body flow and engine pumping flow; measured and modeled values are then cross-compared to detect and isolate sensor faults [5][6]. In this project, the literal throttle-position trigger is replaced by a driver-demand trigger because the available `tps` channel is not trustworthy, while the steady-state MAP/MAF/RPM consistency check remains unchanged. If MAP is distorted, load, ignition timing, fuel injection, and torque calculations will all be biased [4].

**Observability argument.** MAP is verifiable against three independent references, each defining one sub-check: the **command side** (a driver-demand step must produce a MAP response — observable at pedal step events), the **parallel estimator** (MAF-derived air load must agree with MAP-derived air load — observable in steady-state windows; this is the evidence shared with 3.2, subject to the arbitration rule), and the **expected own-dynamics** (healthy MAP varies with operating context — a near-zero-variance window while context changes is only explainable by signal sticking).

**Failure-mode enumeration.**

| # | Symptom | Statistic (feature) | Enable window | DTC label |
|---|---|---|---|---|
| F1 | MAP unresponsive to demand step | `abs(map_slope)` near zero within response window after `pedal_slope` step event | pedal step events, per `operating_state` | P0106 |
| F2 | Steady-state MAP/MAF cross-inconsistency | `speed_density_maf_residual` outside per-state tolerance | steady-state windows | P0106 (shared evidence with 3.2 — arbitration rule applies) |
| F3 | Stuck MAP signal | `map_stability` below per-state low-variance bound while context changes | sustained engine-on window | P0106 |

#### Stage 2 — Literature Anchoring

- Bosch Automotive Handbook [4] — MAP as load-monitoring method (existing source, retained).
- Nyberg & Nielsen [5], intake-system fault-isolation patent [6] — model-based cross-check architecture. Their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation (existing note, retained).
- **TBD: CARB §1968.2 MAP rationality monitoring clause.**

#### Stage 3 — Decision Rules

*(retained in full from the previous revision ("Expected Pattern"), including all per-state calibration anchors)*

- *Step-response check:* Following an `accel_pedal_mean` step event detected via `pedal_slope` exceeding a calibrated magnitude, `abs(map_slope)` remains near zero within a calibrated response window - indicating MAP is not responding to driver torque demand. This keeps the same model-based intake-flow rationality architecture, but uses the validated pedal-demand signal as the command-side trigger instead of the unreliable `tps` signal; a persistent mismatch between expected load response and measured MAP over a calibrated interval is flagged as a rationality failure [5][6].

  *Note: the specific step-magnitude and response-window values (e.g., a threshold on `pedal_slope` and a sub-second response window) are OEM/platform-calibrated parameters within this model-based architecture, not values fixed by SAE J2012, and should be derived empirically from this project's own healthy-trip baseline. References [5][6] support the general architecture of comparing modeled-vs-measured MAP to detect rationality failures, but their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation. Both the step-detection threshold on `pedal_slope` and the "near zero" tolerance on `map_slope` must be calibrated per `operating_state`, not as single global values. In the current high-confidence post-warmup baseline, positive `pedal_slope` P99 rises from about `8.1 %/s` at idle to `10.0 %/s` in steady driving, `24.3 %/s` during acceleration, and `27.85 %/s` at high load. Similarly, positive `map_slope` P99 rises from about `6 kPa/s` at idle to `23 kPa/s` in steady driving, `45 kPa/s` during acceleration, and `74 kPa/s` at high load. A response-window tolerance sized for idle would therefore flag normal high-load MAP fluctuation as anomalous, while a tolerance sized for high load would fail to catch a genuinely stuck MAP at idle.*

- *Steady-state cross-consistency check:* Under steady-state conditions, the standardized deviation between the MAF-derived air load and the MAP-derived air load (`speed_density_maf_residual`) exceeds a calibrated tolerance - directly analogous to the throttle-model/intake-manifold-model cross-check in which MAF-side and MAP-side flow estimates are compared against each other and against direct sensor measurements to isolate which sensor is inconsistent [5][6].

  *Note: `speed_density_maf_residual` carries a strong operating-state-dependent bias even under healthy conditions in this project's baseline - for example, its median is near zero at idle/steady-driving/acceleration but rises to roughly +7.5 g/s at high load, with the high-load P99 climbing to about 61 g/s versus single digits or low tens at other states. A single global tolerance would therefore misfire under high-load operation by flagging healthy behavior, while also being too loose at idle. This check must use a per-`operating_state` tolerance band derived from this project's own baseline distribution, not one fixed global threshold.*

- *Stuck-signal check:* `map_stability` remains below a calibrated low-variance threshold for an extended engine-running window while operating conditions (RPM, pedal demand, MAF, or speed/load state) are changing — consistent with MAP signal-sticking failure modes covered under the same rationality-diagnostic family.

  *Note: This check should now use `map_stability` as the primary sustained-window feature rather than relying on consecutive zero `map_slope` samples. The low-variance threshold and required duration must be calibrated per `operating_state`, because healthy MAP variability differs substantially between idle, steady-driving, acceleration, and high-load windows. As an initial lower-tail calibration anchor from the current high-confidence post-warmup baseline, `map_stability` P05 is approximately `1.1 kPa` at idle, `3.0 kPa` in steady driving, `3.1 kPa` during acceleration, and `12.3 kPa` at high load. These values are provisional state-specific starting points, not final fault thresholds; the check must also require changing RPM, pedal demand, MAF, or speed/load context over a sustained window.*

- **Arbitration rule (shared evidence with 3.2):** see 3.2 Stage 3 — F2 evidence is attributed to MAP only when F1 or F3 also triggers; otherwise it flows to 3.2's attribution logic.
- Output: three-state per sub-check, same schema as 3.6.

*Data-quality note:* `tps` in this dataset is saturated near 83.1-83.5% across nearly all operating states (idle, high load, and steady driving alike). A simple `100 - tps` inversion does not recover a physically meaningful throttle-opening signal, and `tps` does not correlate with `accel_pedal_mean`, `map`, `maf`, or `rpm` in the expected physical direction. Conversely, `map` shows a more physically plausible response to `pedal_slope` changes than to `tps`, supporting the choice of pedal demand as the substitute trigger signal. `tps` is therefore treated as unreliable for step-detection purposes in this failure and retained only as raw diagnostic context, not as a triggering input.

#### Stage 4 — Empirical Falsifiability (TBD)

- **TBD-1 Injection design:** suppressed step response (hold `map` constant across injected pedal-step windows) for F1; additive offset / gain error on `map` in steady-state windows for F2; frozen-value injection for F3. Injection on `map` only.
- **TBD-2/3/4:** detectability curve, false-positive rate, acceptance criteria — same protocol as 3.6 Stage 4.

## 6. idle_speed_control_or_surge_degradation

**Component:** Idle-speed control / engine-speed control

**Supporting Features:** `rpm`, `speed`, `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_mean`, `maf`, `map`, `operating_state`, `idle_rpm_stability`, `rpm_slope`

**Proxy Definition:** Under idle conditions, RPM fluctuation is excessive, cyclic surging occurs, or the engine cannot stabilize near its expected idle speed. This proxies idle-control degradation, intake/fuel-injection/ignition disturbances, excessive EGR, or insufficient load compensation, consistent with SAE J2012 DTCs P0506 (Idle Air Control System RPM Lower Than Expected) and P0507 (Idle Air Control System RPM Higher Than Expected) [1].

### Judgment Method

#### Stage 1 — Observability Derivation

*(absorbs and extends the former "Physical Logic" section; establishes **what data to analyse and why**, prior to any calibration)*

**Monitored function.** Idle-speed control is a closed loop: the ECU adjusts an actuating quantity (fuel-injection quantity on diesel engines; idle-air actuation on petrol engines) to hold the controlled variable — engine speed — at a target value, against disturbances from accessory loads, intake/EGR flow variation, and combustion-quality variation [4, pp. 916, 1000, 1137].

**Observability argument.** The health of a regulation loop is observable only while the loop is active and its reference is constant. This dictates, rather than merely suggests, both the observation window and the observed variable:

- *Window (enable conditions):* engine running, vehicle stationary, **driver demand fully released** (the loop is not in regulation mode while the pedal commands torque), thermal state qualified (warm idle and warm-up idle have different targets and must carry separate baselines). Operationally: `child_state == idle` from the operating-condition layer, split by `thermal_state` (`post_warmup__idle` / `warmup__idle`), **plus `accel_pedal_mean` at its released resting level** (calibration anchor: resting value ≈ 14 % in this dataset; threshold TBD from pedal-at-rest distribution). The pedal-release condition is an addition relative to the previous revision, which defined idle from smoothed speed and acceleration only; it follows directly from the "reference constant" requirement.
- *Variable:* the controlled variable `rpm`. Actuator-side signals are unavailable (no injection-quantity or idle-actuator PID), so the loop is observed from its output side only; actuator-level fault isolation (as in [9]) is out of scope.

**Failure-mode enumeration.** Control theory bounds the observable symptom space of a degrading regulation loop to three patterns, each mapping to one statistic and one DTC label:

| # | Loop symptom | Statistic (feature) | DTC label |
|---|---|---|---|
| S1 | Steady-state offset — loop cannot reach target | window mean `rpm` vs. reference band | below band → P0506; above band → P0507 |
| S2 | Sustained oscillation (surge) — loop unstable or disturbance periodic | `idle_rpm_stability` (10 s rolling std) exceeding bound; `rpm_slope` repeated sign reversals above amplitude | P0507-type (surge) |
| S3 | Degraded disturbance rejection — variance growth without full oscillation | same `idle_rpm_stability` statistic, lower severity tier | pending-tier flag, no code |

**Context covariates.** `maf` and `map` within the idle window serve as disturbance context (e.g., accessory-load episodes raise idle target and airflow simultaneously); they separate legitimate load-compensated idle-ups from S1 faults. The dataset's observed bimodality of warm idle (≈27 % of `post_warmup__idle` rows at rpm ≥ 850 with elevated `maf`) is expected behaviour under this reading and must be inside the healthy baseline, not flagged.

**Sampling-rate limitation (honest bound on observability).** Idle surge in the literature spans roughly 0.5–5 Hz; at 1 Hz sampling, components above 0.5 Hz alias. S2 is therefore sensitive only to slow surge and to the aliased variance footprint of fast surge — it cannot resolve fast-surge waveform shape. This is a stated limitation, not a defect of the method.

#### Stage 2 — Literature Anchoring

*(establishes that the architecture is standard practice, not a project invention)*

- **Regulatory mandate:** CARB Title 13 CCR §1968.2 requires OBD monitoring of idle control — detection when the system cannot achieve target idle speed within manufacturer tolerances [2]. This grounds the *existence* of the monitor; the regulation is current (2004+ MY vehicles, revised through 2019).
- **Window qualification:** idle-diagnostic patents evaluate idle-RPM faults only once idling conditions are confirmed [7] — Stage 1's enable window is the dataset adaptation of this precondition.
- **Asymmetric tolerance band:** one documented OEM implementation uses a band on the order of −100/+200–400 rpm around target idle [8]; cited to motivate an asymmetric band design (idle-up is legitimate under load compensation; idle-down is not), not as values to adopt.
- **Duration gating and residual architecture:** model-based idle FDI compares expected vs. actual speed response with persistence requirements [9]; the deviation-and-duration rule below mirrors this.
- **Reference source:** no PID exposes the ECU's commanded idle target, so the reference band is derived from this project's own healthy-trip baseline — a stated substitution, consistent with the project-wide policy that thresholds are project-calibrated parameters, not SAE-mandated constants.

#### Stage 3 — Decision Rules (calibrated against project baseline)

*(retains the calibrated content of the former "Expected Pattern" section)*

- **Window admission:** contiguous idle episode within one `segment_id`; minimum duration 10 s for S2 (full-window rule of `idle_rpm_stability`); episodes shorter than 10 s are evaluated for S1 only if ≥ N_min samples (N_min TBD), else **not evaluable**.
- **S1 deviation-and-duration:** window mean rpm outside the per-state reference band for a calibrated persistence time → triggered, direction selects P0506/P0507. Reference band: per-`operating_state` healthy-trip distribution (`post_warmup__idle` / `warmup__idle` separately), asymmetric per [8]'s motivation. Band edges and persistence time: **TBD — from baseline quantiles after the settled-idle filter (below) is applied.**
- **S2 stability/variance:** `idle_rpm_stability` > threshold, or `rpm_slope` sign reversals above per-state P95 amplitude. Current provisional anchors (project baseline, high-confidence post-warmup rows):

  | operating_state | idle_rpm_stability p95 / p99 (rpm) | rpm_slope p95 / p99 (rpm/s) | provisional threshold |
  |---|---:|---:|---:|
  | `post_warmup__idle` | 118.2 / 335.1 | 139.9 / 472.1 | 150 rpm |
  | `warmup__idle` | 75.8 / 354.8 | 61.0 / 537.4 | 100 rpm |

- **Settled-idle refinement:** baselines are computed from settled idle only — samples after the first 10 s of each idle episode — to exclude entry transients; **recalibration of the table above under this filter: TBD.**
- **Output:** three-state per sub-check (`pass` / `triggered` / `not_evaluable`), reported as `proxy_id + sub_check_id + direction + DTC label`, aggregated to proxy level for reporting.

#### Stage 4 — Empirical Falsifiability (TBD)

*(the validation that substitutes for absent real-failure labels; to be implemented after Stages 1–3 are frozen)*

- **TBD-1 Synthetic fault injection:** onto held-out healthy idle windows, inject (a) parameterised steady offsets (±50…±300 rpm ramped and stepped) for S1, and (b) additive low-frequency oscillation (≤ 0.5 Hz, amplitude 30…300 rpm) plus variance inflation for S2/S3, respecting the 1 Hz aliasing bound. Injection operates on `rpm` only; all other signals untouched.
- **TBD-2 Detectability curve:** detection rate vs. injected amplitude per sub-check; report the minimum detectable offset/amplitude at the calibrated thresholds.
- **TBD-3 False-positive rate:** run the frozen rules on held-out healthy trips (split by `trip_id`, respecting the leakage rules in the operating-condition analysis §5.3); report per-window and per-trip FP rates.
- **TBD-4 Acceptance criteria:** minimum detectable amplitude and maximum FP rate to be set jointly with the team after the first TBD-2/TBD-3 run; thresholds from Stage 3 may be revised once, then re-frozen.

---

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
