# Proxy Failure research

## Current

### 3.1 cooling_degradation

**Component:** Cooling system (Radiator / Water Pump / Thermostat / Coolant Circulation)  

**Supporting Features:** `coolant_temp`, `ambient_temp`, `speed`, `rpm`, `coolant_slope`, `coolant_ambient_delta`, `coolant_stability`  

**Proxy Definition:** Flag abnormal coolant thermal behavior, including sustained overheating after warm-up, coolant temperature rising without plateau, abnormally slow warm-up and coolant temperature implausible relative to ambient temperature after cold soak.  

**Expected Pattern:** 
- Overheating: coolant_temp > 105°C for 3-5 min after warm-up
- Rising without plateau: coolant_slope > 2°C/min for 2-3 min
- Slow warm-up: coolant_temp < 70-75°C after 10-15 min running
- Sensor plausibility: abs(coolant_temp - ambient_temp) > 10-15°C after cold soak

**Physical Logic:** The cooling system prevents thermal overload, lubricating-oil burn-off, and abnormal combustion caused by excessive component temperatures. Coolant and engine temperatures need to remain stable within a narrow range. If the temperature stays above the stable post-warm-up range for an extended period, heat input and heat dissipation capacity are out of balance.  

**Source:** Bosch Automotive Handbook

### 3.2 air_intake_maf_anomaly

**Component:** MAF sensor / intake air measurement path  

**Supporting Features:** `maf`, `map`, `rpm`, `intake_temp`, `maf_derived_air_load_raw`, `map_derived_air_load_raw`, `maf_map_cohesion`  

**Proxy Definition:** Triggered when `maf_map_cohesion` remains high. This proxy identifies inconsistency between the MAF-side air-load estimate and the MAP-side air-load estimate, mainly indicating MAF sensor drift, contamination, response delay, or abnormalities in the intake measurement chain.  

**Expected Pattern:** `maf_map_cohesion` > 0.25-0.30 for 5-10 s as an initial proxy hint, not a final decision threshold; or under steady-state conditions, the standardized deviation between `maf_derived_air_load_raw` and `map_derived_air_load_raw` exceeds 25-30%. Transient acceleration, gear shifts, and rapid throttle-change windows should be down-weighted or masked.  

**Physical Logic:** Under the same operating condition, MAF-based load and MAP-based load should remain physically consistent. Persistent deviation between the two indicates a plausibility abnormality in the air-mass measurement chain.  

**Source:** Bosch Automotive Handbook  

### 3.3 accelerator_pedal_sensor

**Component:** Accelerator pedal position sensors (dual/redundant)   

**Supporting Features:** `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_channel_delta`, `accel_pedal_channel_ratio`, `pedal_slope`  

**Proxy Definition:** The proportional relationship, correlation, or dynamic behavior between pedal channels D/E is inconsistent. This proxies pedal sensor channel drift, contact abnormalities, or redundancy-monitoring failure.  

**Expected Pattern:** First learn the dataset normal-reference mapping `accel_pedal_e = a * accel_pedal_d + b`; trigger if the residual remains above 5-10 percentage points, the channel correlation coefficient is below 0.95, or one channel changes while the other channel freezes for more than 1 s.  

**Physical Logic:** The ETC system uses two potentiometers on the pedal and throttle device to provide redundancy, and continuously checks all sensors and calculations that affect throttle opening while the engine is running.  

**Source:** SAE International. (2002). *Diagnostic trouble code definitions*

### 3.4 intake_air_temperature_sensor_fault

**Component:** Intake-air temperature (IAT) sensor circuit and signal plausibility

**Supporting Features:** `intake_temp`, `ambient_temp`, `coolant_temp`, `speed`, `rpm`, `maf`, `map`, `operating_state`, `intake_ambient_delta`, `intake_temp_stability`, `segment_gap_seconds`, `cold_soak_candidate_flag`, `condition_confidence` 

**Proxy Definition:** The IAT signal fails a rationality (plausibility) check against ambient/other temperature references after a cold soak, or remains unresponsive (skewed/stuck) despite sustained vehicle speed and airflow that would normally change intake-air temperature. This proxies IAT sensor circuit degradation, signal drift, or signal sticking, consistent with SAE J2012 DTC P0111 (Intake Air Temperature Sensor 1 Circuit Range/Performance) [1].

**Expected Pattern:**
- *Cold-soak plausibility check (low-confidence candidate, not a confirmed rationality check):* True cold-soak duration cannot be reliably reconstructed from this dataset, since `engine_on_flag` only reflects whether the engine is running within a recorded sample and cannot confirm that the vehicle stayed off across a gap between segments/trips. This check is therefore demoted from a primary detection judgment to a low-confidence supporting flag.

  *Definition:* `cold_soak_candidate_flag` is set when `segment_gap_seconds` (time since the previous segment/trip's last sample) exceeds a calibrated duration (on the order of six to eight hours, per [2]), AND the first sample of the new segment shows both `coolant_temp` and `intake_temp` close to `ambient_temp`. This dual-signal cross-check is required precisely because the time gap alone cannot prove the vehicle was actually off throughout — a long gap with normal (non-decayed) coolant/intake temperature at restart indicates the vehicle was very likely operated during the gap, while a long gap with both temperatures converged toward ambient is much stronger physical evidence of genuine soak, largely independent of what happened during the untracked interval.

  *Usage:* Once triggered, `cold_soak_candidate_flag` should not independently produce a fault verdict at the same confidence level as the skewed-signal or heat-soak checks below. It should instead be used as a confidence modifier — e.g., raising the confidence of a co-occurring `intake_ambient_delta` anomaly at that same sample, or being logged as a separate low-confidence candidate consistent with this project's existing `condition_confidence` (high/medium/low) tiering — rather than as a standalone P0111 trigger.

  *Note: [2] documents this cold-soak test-design framework for ECT (P0116) rationality checks, not IAT specifically, and is cited here only for the underlying methodology (cold-soak duration as a standard test precondition), not as an IAT-specific primary source.*

- *Skewed/stuck-signal check:* Once speed/load context (`speed`, `rpm`, `maf`, `map`, or `operating_state`) indicates sustained airflow, `intake_temp_stability` (a rolling standard deviation of `intake_temp` over that window, analogous to `coolant_stability`) stays near zero despite sustained speed/load — indicating the signal is not tracking expected thermal dynamics [3]. This sustained-window check is the primary judgment for this pattern, since a single-sample or instantaneous-slope check cannot distinguish a truly stuck signal from ordinary sample-to-sample noise. `tps` is not used as an airflow proxy in this dataset because its physical meaning is unreliable.

  As with the cold-soak check, the window length and drift/variance thresholds are implementation-specific calibration parameters, not SAE-mandated constants, and should be tuned against this project's own data.

- *Post-high-load heat-soak check (dataset-derived, no direct DTC support):* Rather than during high-load driving itself, elevated `intake_temp` is more physically expected to appear in an idle or low-speed window that follows a period of high load — a classic heat-soak pattern in which residual engine-bay heat conducts into the stationary intake path once ram-air cooling stops. This project's own baseline is consistent with that mechanism: within `post_warmup__idle` windows, `intake_temp` reaches a P99 of approximately 63°C, noticeably higher than the P99 seen during `post_warmup__high_load` driving itself (~45°C) [own baseline, not literature-sourced]. `intake_temp` sustained above this project-derived idle-window reference for an extended duration is treated as a secondary engineering flag rather than a standardized threshold, since no SAE/OEM DTC defines a fixed physical high-temperature limit for IAT under normal (non-circuit-fault) conditions; this threshold should be re-validated as more trip data accumulates rather than treated as fixed.

**Physical Logic:** Intake air temperature directly affects air density and combustion efficiency — colder air is denser, and heated intake air reduces effective oxygen content [4, p. 786]. Under normal operation, IAT should closely track ambient/coolant temperature references immediately after a cold soak, before engine heat has propagated to the intake path, and should respond dynamically to changes in vehicle speed and airflow once the engine is running. A signal that is implausible relative to reference sensors at cold start, or that fails to vary despite sustained flow, indicates the sensor circuit is not measuring true intake-air temperature — consistent with the OEM diagnostic logic underlying P0111 [1][2][3].

### 3.5 map_load_signal_plausibility_fault

**Component:** Intake manifold absolute pressure (MAP) sensor / load-signal plausibility

**Supporting Features:** `map`, `maf`, `rpm`, `accel_pedal_mean`, `pedal_slope`, `intake_temp`, `speed_density_maf_residual`, `map_slope`, `map_stability`

**Excluded / Diagnostic Context:** `tps` is retained only as raw diagnostic context and is not used as a triggering input for this proxy, because its physical meaning is unreliable in the current KIT Seat Leon dataset (see data-quality note below).

**Proxy Definition:** MAP fails to reasonably reflect load changes, or its relationship with MAF, driver-demand/load context, and engine speed is inconsistent. This proxies MAP sensor drift, blockage, hose issues, signal sticking, or load-measurement-chain abnormalities, consistent primarily with SAE J2012 DTC P0106 (Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance) [1]. This project's step-response implementation substitutes accelerator-pedal demand for throttle position as the trigger signal because `tps` in this dataset does not behave as a physically interpretable throttle-opening percentage (see data-quality note below). This approximates the diagnostic intent of P0068 (MAP/MAF - Throttle Position Correlation) rather than implementing its literal throttle-position-based definition; P0106 remains the primary, unaffected DTC support for this failure.

**Expected Pattern:**
- *Step-response check:* Following an `accel_pedal_mean` step event detected via `pedal_slope` exceeding a calibrated magnitude, `abs(map_slope)` remains near zero within a calibrated response window - indicating MAP is not responding to driver torque demand. This keeps the same model-based intake-flow rationality architecture, but uses the validated pedal-demand signal as the command-side trigger instead of the unreliable `tps` signal; a persistent mismatch between expected load response and measured MAP over a calibrated interval is flagged as a rationality failure [5][6].

  *Note: the specific step-magnitude and response-window values (e.g., a threshold on `pedal_slope` and a sub-second response window) are OEM/platform-calibrated parameters within this model-based architecture, not values fixed by SAE J2012, and should be derived empirically from this project's own healthy-trip baseline. References [5][6] support the general architecture of comparing modeled-vs-measured MAP to detect rationality failures, but their specific implementations use throttle position as a model input; this project's substitution of pedal demand for that input is not directly validated by those sources and should be treated as this project's own dataset-driven adaptation. Both the step-detection threshold on `pedal_slope` and the "near zero" tolerance on `map_slope` must be calibrated per `operating_state`, not as single global values. In the current high-confidence post-warmup baseline, positive `pedal_slope` P99 rises from about `8.1 %/s` at idle to `10.0 %/s` in steady driving, `24.3 %/s` during acceleration, and `27.85 %/s` at high load. Similarly, positive `map_slope` P99 rises from about `6 kPa/s` at idle to `23 kPa/s` in steady driving, `45 kPa/s` during acceleration, and `74 kPa/s` at high load. A response-window tolerance sized for idle would therefore flag normal high-load MAP fluctuation as anomalous, while a tolerance sized for high load would fail to catch a genuinely stuck MAP at idle.*

- *Steady-state cross-consistency check:* Under steady-state conditions, the standardized deviation between the MAF-derived air load and the MAP-derived air load (`speed_density_maf_residual`) exceeds a calibrated tolerance - directly analogous to the throttle-model/intake-manifold-model cross-check in which MAF-side and MAP-side flow estimates are compared against each other and against direct sensor measurements to isolate which sensor is inconsistent [5][6].

  *Note: `speed_density_maf_residual` carries a strong operating-state-dependent bias even under healthy conditions in this project's baseline - for example, its median is near zero at idle/steady-driving/acceleration but rises to roughly +7.5 g/s at high load, with the high-load P99 climbing to about 61 g/s versus single digits or low tens at other states. A single global tolerance would therefore misfire under high-load operation by flagging healthy behavior, while also being too loose at idle. This check must use a per-`operating_state` tolerance band derived from this project's own baseline distribution, not one fixed global threshold.*

- *Stuck-signal check:* `map_stability` remains below a calibrated low-variance threshold for an extended engine-running window while operating conditions (RPM, pedal demand, MAF, or speed/load state) are changing — consistent with MAP signal-sticking failure modes covered under the same rationality-diagnostic family.

  *Note: This check should now use `map_stability` as the primary sustained-window feature rather than relying on consecutive zero `map_slope` samples. The low-variance threshold and required duration must be calibrated per `operating_state`, because healthy MAP variability differs substantially between idle, steady-driving, acceleration, and high-load windows. As an initial lower-tail calibration anchor from the current high-confidence post-warmup baseline, `map_stability` P05 is approximately `1.1 kPa` at idle, `3.0 kPa` in steady driving, `3.1 kPa` during acceleration, and `12.3 kPa` at high load. These values are provisional state-specific starting points, not final fault thresholds; the check must also require changing RPM, pedal demand, MAF, or speed/load context over a sustained window.*

**Physical Logic:** Intake manifold absolute pressure is a preferred method for monitoring engine load, and relative charge can be determined from available measurement signals such as MAF or MAP through an intake-manifold model [4, pp. 897, 912, 914, 919, 928]. In the original model-based intake-system diagnostic architecture, a throttle model estimates mass flow through the throttle body from ambient pressure, MAP, throttle position, and intake air temperature, while an intake-manifold model estimates MAP from the throttle-body flow and engine pumping flow; measured and modeled values are then cross-compared to detect and isolate sensor faults [5][6]. In this project, the literal throttle-position trigger is replaced by a driver-demand trigger because the available `tps` channel is not trustworthy, while the steady-state MAP/MAF/RPM consistency check remains unchanged. If MAP is distorted, load, ignition timing, fuel injection, and torque calculations will all be biased [4].

*Data-quality note:* `tps` in this dataset is saturated near 83.1-83.5% across nearly all operating states (idle, high load, and steady driving alike). A simple `100 - tps` inversion does not recover a physically meaningful throttle-opening signal, and `tps` does not correlate with `accel_pedal_mean`, `map`, `maf`, or `rpm` in the expected physical direction. Conversely, `map` shows a more physically plausible response to `pedal_slope` changes than to `tps`, supporting the choice of pedal demand as the substitute trigger signal. `tps` is therefore treated as unreliable for step-detection purposes in this failure and retained only as raw diagnostic context, not as a triggering input.

### 3.6 idle_speed_control_or_surge_degradation

**Component:** Idle-speed control / engine-speed control

**Supporting Features:** `rpm`, `speed`, `accel_pedal_d`, `accel_pedal_e`, `maf`, `map`, `operating_state`, `idle_rpm_stability`, `rpm_slope`

**Proxy Definition:** Under idle conditions, RPM fluctuation is excessive, cyclic surging occurs, or the engine cannot stabilize near its expected idle speed. This proxies idle-control degradation, intake/fuel-injection/ignition disturbances, excessive EGR, or insufficient load compensation, consistent with SAE J2012 DTCs P0506 (Idle Air Control System RPM Lower Than Expected), P0507 (Idle Air Control System RPM Higher Than Expected), and P0519 (Idle Air Control System Performance) [1].

**Expected Pattern:**
- *Window definition:* An idle window is defined using the project's existing `operating_state`/`child_state` classification (`== idle`), derived from smoothed vehicle speed and speed-derived acceleration rather than accelerator-pedal position or `tps`, consistent with the standard precondition in idle-diagnostic patents that idle RPM faults are evaluated only once idling conditions are confirmed [7].

- *Deviation-and-duration check:* Measured idle RPM is compared against an expected idle-RPM reference band derived from this project's own `post_warmup__idle`/`warmup__idle` healthy-trip baseline — not an ECU-internal commanded target, which no PID in this dataset exposes. A fault is flagged when the deviation persists outside a calibrated tolerance band for a calibrated duration, mirroring the general duration-gated architecture of OEM idle-diagnostic systems [7]. One documented OEM implementation uses an asymmetric band on the order of −100/+200–400 rpm around target idle [8] — cited only to motivate an asymmetric design, not as a value to adopt; this project's band and reference are both project-derived/provisional, calibrated separately by `operating_state`.

- *Stability/variance check:* `idle_rpm_stability` (rolling std of RPM, 10 s full contiguous idle window — not bridging non-idle intervals; `min_valid_fraction` may later cover brief missing-sample gaps only) exceeding a calibrated bound, or `rpm_slope` showing repeated sign reversals above a calibrated amplitude, indicates cyclic surging (P0507-type) rather than a steady offset (P0506-type). The 10 s window reflects the second-scale dynamics of idle-speed control, in contrast to the 60 s windows used for slower thermal features (`coolant_stability`, `intake_temp_stability`); it also improves usable idle coverage from ~19.3% (30 s window) to ~57.6% (10 s window), since median idle-episode length is ~13 s. Idle episodes shorter than 10 s yield no `idle_rpm_stability` value at all (not a lower-precision one); surge behavior confined to such short episodes must be caught via `rpm_slope` instead.

  Current baseline (project-derived/provisional; standard deviation in rpm unless noted):

  | operating_state | idle_rpm_stability p95 / p99 | rpm_slope p95 / p99 (rpm/s) | proposed `idle_rpm_stability` threshold |
  |---|---:|---:|---:|
  | `post_warmup__idle` | 118.2 / 335.1 | 139.9 / 472.1 | **150 rpm** |
  | `warmup__idle` | 75.8 / 354.8 | 61.0 / 537.4 | **100 rpm** |

  `warmup__idle` shows a tighter p95 than `post_warmup__idle` (likely tighter closed-loop control during warm-up) but a comparable p99, so its threshold sits closer to its own p95 while `post_warmup__idle`'s leaves more margin toward p99. `rpm_slope`'s sign-reversal amplitude threshold should reference the same per-state p95 values.

**Physical Logic:** Idle-speed control aims to maintain target idle speed under disturbances from accessory loads, intake/EGR flow variation, and combustion-quality variation [4, pp. 916, 1000, 1137]. Model-based idle-speed diagnostics treat this as a closed-loop system where residual generators compare expected versus actual engine-speed response to isolate actuator- or load-sensing-path faults [9]. Persistent RPM fluctuation or failure to converge to an expected idle speed, evaluated within a properly qualified idle window, reflects degradation in this control loop or the combustion stability it depends on [1][4]. "Expected idle speed" here is approximated from the dataset's own healthy-trip distribution, since no ECU-reported commanded value is available.

## Deleted

### 3.7 electronic_throttle_tracking_fault — Excluded (Not Implementable with Current Dataset)

**Component:** Electronic throttle control (ETC) / throttle actuator command-response tracking

**Status:** Excluded from the current proxy failure set. Unlike `cooling_degradation` and `air_intake_maf_anomaly`, which are deferred pending DTC-mapping coordination, this exclusion is not a coordination-pending state — it reflects a data-acquisition limitation that additional trip data of the same kind cannot resolve.

**Reason for Exclusion:** This failure's diagnostic intent (SAE J2012 P2111/P2112/P2108) requires an independent observation of actual throttle position to distinguish actuator-tracking faults from driver-demand or air-path issues. In this dataset, the only available throttle-position channel (`tps`) shows a sampling artifact — long flat stretches interrupted by large abrupt jumps (`tps_slope` p50/p95 ≈ 0 across all operating states, with p99 spiking to 50+ %/s specifically in acceleration/high-load states), consistent with polling-interval/refresh-rate behavior of the OBD dongle rather than continuous physical throttle response [own baseline finding]. A candidate derived feature (`pedal_throttle_gap`, a conditional residual of `tps` against an expected-value model over `accel_pedal_mean`/`rpm`/`operating_state`) was evaluated as a substitute, but its widened-residual regions coincide with exactly the same operating states where the sampling artifact concentrates, making it structurally unable to separate a true actuator fault from the measurement artifact. No other signal in the current feature set (`map`, `maf`, `rpm`) provides an independent observation of throttle position; using them alone would duplicate `map_load_signal_plausibility_fault`'s step-response check under a different DTC label rather than provide independent evidence.

**Reconsideration Criteria:** This exclusion should be revisited if (a) raw per-PID polling timestamps become available to correct for refresh-rate artifacts, or (b) a higher-fidelity throttle-position source (e.g., VCDS/UDS measuring-block data) is captured alongside future trips.

## Reference

[1] SAE International. (2002). *Diagnostic trouble code definitions* (SAE Standard No. J2012_200204). SAE International.

[2] Wang, L., Zou, X., Qin, H., & Geng, P. (2021). Design of OBD function test on production vehicle (PVE). *E3S Web of Conferences, 268*, 01047. https://doi.org/10.1051/e3sconf/202126801047

[3] *Method and apparatus to evaluate an intake air temperature monitoring circuit* (U.S. Patent No. 7,120,535). (2006). U.S. Patent and Trademark Office.

[4] Bosch, Robert GmbH. (2018). *Bosch automotive handbook* (10th ed.). SAE International.

[5] Nyberg, M., & Nielsen, L. (1997). Model based diagnosis for the air intake system of the SI-engine (SAE Technical Paper 970209). SAE International. https://doi.org/10.4271/970209

[6] *Fault identification diagnostic for intake system sensors* (U.S. Patent No. 6,701,282). (2004). U.S. Patent and Trademark Office.

[7] *Idle air control system diagnostic* (U.S. Patent No. 5,408,871). (1995). U.S. Patent and Trademark Office.

[8] *System for detecting functional abnormalities of idle speed control system* (U.S. Patent No. 5,936,152). (1999). U.S. Patent and Trademark Office.

[9] Montes-Solano, C. A., & Pisu, P. (2009). Model based fault detection and isolation in idle speed control of IC engines. Proceedings of the 7th IFAC Symposium on Fault Detection, Supervision and Safety of Technical Processes (SAFEPROCESS 2009), Barcelona, Spain. https://doi.org/10.3182/20090630-4-ES-2003.00149
