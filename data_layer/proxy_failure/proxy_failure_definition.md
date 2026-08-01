# Proxy Failure Definitions

## Purpose and Scope

This is the authoritative, implementation-facing definition of the executable proxy failures for the current freeze cycle (**2026-07-19 contract revision**). It contains only the component, consumed support signals, proxy definition, final decision rules, required guards, coverage, key calibration evidence, and known limitations.

Research derivations, candidate grids, sensitivity analyses, LOTO/Bootstrap details, rejected branches, superseded forms, and the open fault-injection program are maintained in [`proxy_support.md`](proxy_support.md). Each proxy below links to its corresponding audit section.

## Shared Conventions

- Every runtime row records `proxy_id`, `sub_check_id`, `direction`, `decision_role`, `result_state`, `decision_reason`, `decision_margin`, `dtc_candidate_label`, and `dtc_emitted`, plus routing, confidence, and provenance where applicable. `decision_role` is one of `verdict`, `pending_precursor`, `support`, or `arbitration_evidence`; `result_state` is one of `pass`, `triggered`, `not_evaluable`, or `pending` as permitted by that role.
- `dtc_candidate_label` identifies the relevant diagnostic family but does not authorize emission. Support and arbitration-evidence rows always set `dtc_emitted = false`; final routing alone determines whether a permitted verdict row emits a DTC.
- Guard, data-quality, opportunity, and calibration-domain failures produce `result_state = not_evaluable` with an explicit `decision_reason`, never a normal or abnormal result.
- Duration-gated checks record `decision_margin`; at 1 Hz with integer-quantized signals, margins within approximately ±5 s are resolution-borderline.
- Only frozen or explicitly executable rules produce runtime rows. `pending` precursors, support, and arbitration evidence may execute but do not independently emit a DTC. Downgraded, descriptive, removed, and documented-infeasible designs produce no runtime rows; `not_evaluable` must not be used to represent a design that is not executed.
- Frozen calibration values are applied from the calibration registry. They are not re-fitted on user-uploaded data.

## 1. cooling_degradation

[Research and calibration audit](proxy_support.md#1-cooling_degradation)

**Component:** Cooling system (radiator / water pump / thermostat / coolant circulation).

**Support signals:** `coolant_temp`, `ambient_temp`, `intake_temp`, `rpm`, `maf`, `coolant_ambient_delta`, `intake_ambient_delta`, `segment_gap_seconds`, engine-start episode fields, `time_to_target_79c`, `time_to_target_79c_is_right_censored`, `time_to_target_79c_censor_time_s`, `maf_integral_180s`, `ect_rate_180s`, `ect_exceedance_run_s`, and `decision_margin`.

**Definition:** Detect abnormal coolant thermal behavior: slow warm-up, sustained overheating, a level-conditioned rising-temperature precursor, or cold-start ECT implausibility. The judgment form follows coolant-model and regulatory monitoring precedents; project thresholds are baseline-calibrated except for explicitly identified regulatory guard forms [1–8].

### Final rules

#### 1-S1 — Slow warm-up (frozen; P0128)

- At a qualified observed RPM `<50` to `>=50` crossing, use crossing-row `ect_start` and `aat_start`, set `T_target = 79°C` (`T_reg_est = 90°C`, minus the 11°C regulatory form [4]), and assign the frozen ambient-bin/ECT-band warm-up budget: 16.5–26.9 min for ambient ≤5°C and 8.3–18.2 min for ambient >5°C. A computed budget above the maximum deployable budget of 30 min is outside the calibration/deployment domain and returns `not_evaluable`; it must not be clipped to 30 min.
- Reaching `T_target` before budget expiry is `pass` only when 1-S4 is evaluable and `pass`. Budget expiry below `T_target`, with sufficient heat input and all 1-S1 guards satisfied, is `triggered` (low, P0128). Otherwise return `not_evaluable` with an explicit reason.
- Eligibility: observed within-continuity-block RPM off→on start; `ect_start ≤ 50°C` and below target; `aat_start ≥ −7°C`; ECT, ambient, and MAF present and quality-valid. At expiry, the trapezoidal `maf_integral_180s` over 181 valid 1 Hz endpoints / 180 intervals must satisfy the frozen raw registry comparison `> 2800.6549999999997 g` (display value approximately 2800 g).
- Sensor-trust/asymmetry wiring: if 1-S4 is `pass`, 1-S1 may return its normal three states. If 1-S4 support is `triggered`, 1-S1 returns `not_evaluable` with `decision_reason = ect_plausibility`. If 1-S4 is `not_evaluable` solely because cold-soak/predecessor evidence is unavailable, 1-S1 may `triggered` or return `not_evaluable` but may never `pass`. Any failure of 1-S1's own required-signal, quality, guard, or calibration-domain conditions always returns `not_evaluable`, regardless of 1-S4.
- Right-censor guard: if ECT has not reached 79°C and the continuous observation ends before the assigned budget expires, return `not_evaluable`; record the censor flag and available follow-up duration rather than treating the truncated episode as a failure.
- Coverage and key evidence: 20/51 qualified starts reached a decision point (39.2%); healthy in-sample false positives 0/20. The threshold/reference level was stable across the recorded validation; synthetic smoke tests are calibration evidence only, not real-fault recall evidence.
- Limitations: provisional research-grade candidate; real-fault recall is unknown; thermostat failure is indicated, not isolated. Short logs and the heat-input guard materially limit coverage.

#### 1-S2 — Overheating (frozen; P0217)

- In a qualified post-warm-up window, `coolant_temp ≥ 105°C` for ≥180 s is `triggered`. `coolant_temp ≥ 110°C` for ≥30 s is the same trigger at higher but provisional confidence.
- Guards: engine on; `thermal_state == post_warmup`; ECT and ambient present; ambient at window start >25°C is outside calibration and returns `not_evaluable`.
- `pass` requires at least 180 s of evaluable post-warm-up time with no trigger; otherwise `not_evaluable`.
- Coverage and key evidence: 57/66 trips evaluable (86%); healthy maximum 101°C in the fixed cohort; longest healthy ≥100°C episode 87 s, leaving 93 s persistence headroom.
- Limitations: thresholds lie above the observed healthy envelope, so zero healthy false positives are constructive; detection capability awaits fault injection. Report “overtemperature condition indicated; sensor fault not excluded.”

#### 1-S3 — Rising without plateau (frozen pending precursor; no independent DTC)

- With `decision_role = pending_precursor`, a qualified post-warm-up window with 180-s ECT rate ≥0.5°C/min while `coolant_temp ≥ 100°C`, sustained ≥180 s, returns `pending` only. P0217 is confirmed only by 1-S2. Minimum evaluable window: 360 s.
- Coverage and key evidence: 54/66 trips (81.8%); zero healthy precursor triggers; nearest healthy episode 87 s, leaving 93 s headroom.
- Limitations: slope alone cannot separate regulation loss from legitimate map-thermostat mode changes. Real lead time and short-injection behavior remain unverified.

#### 1-S4 — Cold-start ECT plausibility (executable v1; low-confidence P0116 support)

- With `decision_role = support`, evaluate ECT/IAT/AAT at the canonical segment first row. Require `segment_gap ≥ 6 h`, first-row RPM <50 followed by an observed off→on transition in the same segment and continuity block, valid non-imputed/non-suspicious ECT/IAT/AAT, and IAT witness `|IAT − AAT| ≤ 7°C`. Otherwise return `not_evaluable` with a reason.
- `|ECT − AAT| > 15°C` returns support `result_state = triggered`, `dtc_candidate_label = P0116`, and `dtc_emitted = false`; ≤15°C returns `pass`.
- Coverage and key evidence: calibrated on 18 strict observed-start events; healthy maxima were 5°C for `|IAT−AAT|` and 11°C for `|ECT−AAT|`, with zero healthy candidates at the selected thresholds.
- Limitations: cannot isolate ECT, verify a true cold soak, or exclude AAT/common-mode faults. It is low-confidence support evidence and a sensor-trust guard for 1-S1; it must never independently emit a P0116 DTC.

## 2. air_intake_maf_anomaly

[Research and calibration audit](proxy_support.md#2-air_intake_maf_anomaly)

**Component:** MAF sensor / intake-air measurement path.

**Support signals:** `maf`, `map`, `rpm`, `intake_temp`, `speed_density_maf_residual`, `operating_state`, `thermal_state`, `condition_confidence`, quality flags, `residual_band_run_s`, and `zero_maf_run_s`.

**Definition:** Detect high-load MAF under-read or zero flow while the engine is firing, and route shared MAF/MAP disagreement evidence using independent MAP witnesses. A two-estimator disagreement does not identify the faulty side by itself [1,3,4,9,10].

### Final rules

#### 2-S2 — High-load under-read (frozen; low-direction P0101 candidate)

- Under `post_warmup__high_load`, high confidence, and valid quality, `speed_density_maf_residual < −18.495 g/s` at every consecutive 1 Hz sample for ≥10 s is `triggered`.
- Coverage and key evidence: 52/66 trips (78.8%); zero healthy episodes; longest healthy run 3 s, leaving 7 s headroom; the healthy high-load residual median was positive as required.
- Limitation: persistence margin is thin. A concurrent abnormal 5-S1 or 5-S3 reroutes attribution to MAP.

#### 2-S3b — Zero MAF while firing (frozen; low-direction P0102)

- `maf == 0.0` for ≥10 consecutive valid seconds while `rpm ≥ 500` is `triggered`.
- Key evidence: longest healthy qualifying zero run 3 s, leaving 7 s headroom; zero healthy triggers.
- Guard/limitation: missing or invalid signal returns `not_evaluable`; the 500-rpm floor excludes cranking ambiguity. Cleaning-related isolated zero samples make persistence mandatory.

#### Routing

- 2-S3b bypasses residual arbitration and remains a direct P0102 path because it consumes only raw MAF and RPM.
- For 2-S2 or 5-S2 residual evidence, 5-S1/5-S3 normal and evaluable → attribute to MAF/P0101.
- Either MAP-side witness abnormal → attribute to MAP/P0106.
- Residual evidence present but the required witnesses not evaluable → F4/P006A without isolation.
- Residual sign alone never determines attribution.
- When 4-S2 cold-start IAT plausibility support is active, cap the confidence of IAT-dependent 2-S2 residual evidence at `low`; 2-S3b is unaffected because it does not use IAT.

## 3. accelerator_pedal_sensor

[Research and calibration audit](proxy_support.md#3-accelerator_pedal_sensor)

**Component:** Dual/redundant accelerator-pedal position sensors.

**Support signals:** `accel_pedal_d`, `accel_pedal_e`, `pedal_slope`, `accel_pedal_channel_delta`, `rpm`, `pedal_lowmotion_mask`, `pedal_mapping_residual`, and `channel_delta_extreme_run_s`.

**Definition:** Detect sustained disagreement in the redundant D/E channel relationship. All executable modes map to P2138; sub-check identity and severity tier distinguish them [1,3,4,11].

### Final rules

#### 3-S1a — Channel-relation residual (frozen; P2138)

- For quality-valid engine-on samples, apply `|pedal_slope| ≤ 2.4 pp/s` sustained ≥3 s. Inside that mask, compute `r = E − (0.997273·D + 0.383103)`.
- A same-side residual below `−1.8350 pp` or above `+1.3777 pp` continuously for ≥30 s is `triggered`.
- `pass` requires a qualifying 30-s masked opportunity with no trigger; otherwise `not_evaluable`.
- Coverage and key evidence: 66/66 trips; zero healthy triggers; longest healthy low/high episodes 18/9 s, giving 12/21 s margins. Samples above 16 pp represent 18.19% of the masked population across 66/66 trips, supporting offset-and-gain scope.
- Limitation: 1 Hz asynchronous channel sampling necessitates the low-motion mask.

#### 3-S1b — Extreme disagreement (provisionally frozen; specificity-only P2138 high tier)

- Unmasked `accel_pedal_channel_delta ≥ 65 pp` for 2 consecutive valid seconds is `triggered`.
- Key evidence: healthy maximum 60 pp; artifact guard passed; zero healthy triggers.
- Limitation: the threshold is above the healthy maximum and proves specificity only. Detection capability depends on one-channel offset/gain injection.

## 4. intake_air_temperature_sensor_fault

[Research and calibration audit](proxy_support.md#4-intake_air_temperature_sensor_fault)

**Component:** Intake-air-temperature sensor circuit and signal plausibility.

**Support signals:** `intake_temp`, `ambient_temp`, `coolant_temp`, `speed`, `rpm`, `maf`, `operating_state`, `intake_ambient_delta`, `intake_temp_stability`, `segment_gap_seconds`, `condition_confidence`, `speed_std_120s`, `maf_std_120s`, and quality flags.

**Definition:** Detect an IAT signal that is hard-stuck despite material flow-context change, implausible against cold-start references, or outside its physical PID range [1–4,12,13].

### Final rules

#### 4-S1 — Stuck/no-response IAT (frozen; hard-stuck P0111 candidate)

- Require engine on and valid, non-imputed, non-suspicious IAT/speed/MAF/RPM. Material change in a 120-s context window is `speed_std ≥ 12.4 km/h` OR `maf_std ≥ 8.5 g/s`; both thresholds are trip-equal weighted q50 values over valid 120-s endpoints from the fixed 66-trip cohort, with each trip contributing total weight one.
- Under that gate, `intake_temp_stability ≤ 0.1°C` sustained for ≥120 s is `triggered`. Minimum evaluable window: 240 s. `pass` requires at least one eligible context-change opportunity without a trigger; otherwise `not_evaluable`.
- Coverage and key evidence: context opportunities in 66/66 trips; zero healthy triggers; longest healthy flat episode under material context 29 s, leaving 91 s headroom. The result remained trigger-free at a 0.25°C sensitivity check.
- Limitations: detects hard-stuck/no-response only, not slow drift or mild skew. Detection capability awaits frozen-IAT injection. IAT is 1°C-quantized, so the context gate is mandatory.

#### 4-S2 — Cold-start IAT plausibility (executable v1; low-confidence P0111 support)

- With `decision_role = support`, evaluate ECT/IAT/AAT at the canonical segment first row. Require `segment_gap ≥ 6 h`, first-row RPM <50 followed by an observed off→on transition in the same segment and continuity block, valid non-imputed/non-suspicious ECT/IAT/AAT, and ECT witness `|ECT − AAT| ≤ 15°C`. Otherwise return `not_evaluable` with a reason.
- `|IAT − AAT| > 7°C` returns support `result_state = triggered`, `dtc_candidate_label = P0111`, and `dtc_emitted = false`; ≤7°C returns `pass`.
- Coverage and key evidence: 18 strict observed-start events; healthy maxima 5°C (`|IAT−AAT|`) and 11°C (`|ECT−AAT|`), with zero healthy candidates.
- Limitations: confidence modifier only, never a standalone P0111 DTC; both sensors far from AAT make the mirrored checks `not_evaluable`. When activated at the qualified observed start, its confidence cap applies prospectively from that start through the end of the current continuity segment and never retroactively. A later episode in the same segment cannot clear the cap; a continuity break clears it. The cap affects only IAT-dependent residual evidence in 2-S2 and 5-S2, without changing 2-S3b, 5-S1, or 5-S3.

#### 4-S3 — Physical range (closed rule; P0112/P0113)

- Any valid `intake_temp` outside −40…215°C is `triggered`: low → P0112; high → P0113 [13]. Missing signal returns `not_evaluable`.

## 5. map_load_signal_plausibility_fault

[Research and calibration audit](proxy_support.md#5-map_load_signal_plausibility_fault)

**Component:** MAP sensor / load-signal plausibility.

**Support signals:** `map`, `maf`, `rpm`, `speed`, `intake_temp`, `accel_pedal_mean`, `pedal_slope`, `rpm_slope`, `speed_density_maf_residual`, `operating_state`, `thermal_state`, `condition_confidence`, pedal-step event evidence, `steady_state_mask`, `residual_band_run_s`, `rpm_std_120s`, `speed_std_120s`, `accel_pedal_mean_std_120s`, `map_range_60s`, and quality flags. `tps` is diagnostic context only.

**Definition:** Detect MAP hard no-response to driver-demand steps, shared steady-state MAP/MAF inconsistency, or a hard-stuck MAP signal under material context change. Accelerator-pedal demand substitutes for unreliable `tps`; P0106 is the primary DTC support [1,3,4,9,10].

### Final rules

#### 5-S1 — Step response (frozen; hard no-response P0106)

- Require `thermal_state == post_warmup`, `condition_confidence == high`, and quality-valid MAP, RPM, `accel_pedal_d`, and `accel_pedal_e`. Within that domain, detect positive `pedal_slope` steps at per-state trip-equal P95: idle 9.2, steady-driving 11.4, acceleration 18.6, and high-load 26.5 %/s. A valid event requires contiguous quality-valid samples t0−1…t0+2.
- Response is the maximum `|map − map(t0−1)|` over t0…t0+2. No-response thresholds by state × magnitude bin are: idle 8.0/4.0 kPa; steady-driving high bin 3.0; acceleration 4.0/9.0; high-load 13.4/1.0. Steady-driving low-bin events are non-separable and `not_evaluable`.
- At least 3 no-responses among the trip's most recent 4 valid events is `triggered`; `decision_margin = count − 3`.
- Coverage and key evidence: 56/66 trips (84.8%); zero healthy 3-of-4 triggers; 942 valid events from 1176 detected; event-weighted no-response rate 0.955%, only 0.045 percentage points below the registered 1% criterion.
- Limitations: hard no-response only. Idle-bin thresholds are statistically fragile (29/23 events); the high-load high-bin 1.0-kPa threshold is at signal resolution and near-vacuous. Graded response degradation is not observable at 1 Hz.

#### 5-S2 — Steady-state residual (partial freeze; shared arbitration evidence)

- With `decision_role = arbitration_evidence`, require `pedal_slope == 0` and `|rpm_slope| ≤ 9 rpm/s` for ≥10 s. Only in post-warm-up `steady_driving`, a same-side `speed_density_maf_residual` outside [`−4.04`, `+16.71`] g/s for ≥30 s returns `result_state = triggered` shared evidence with `dtc_emitted = false`.
- Idle, acceleration, and high-load are `not_evaluable`. The evidence produces no code by itself and follows section 2 routing.
- Coverage and key evidence: 44/66 trips; zero healthy 30-s episodes; low/high persistence margins 19/12 s.
- Limitation: the pedal gate degenerates to exact flatness; disclosed and frozen without post-result repair.

#### 5-S3 — Stuck MAP (frozen; P0106)

- Require engine on and valid, non-imputed/non-suspicious MAP/RPM/speed/pedal channels. Material 120-s context is `rpm_std ≥ 241` OR `speed_std ≥ 12.4 km/h` OR `pedal_std ≥ 9.9%`.
- `map_range_60s == 0` sustained for ≥120 s under material context is `triggered`. Minimum evaluable window: 240 s. `pass` requires at least one context opportunity without a trigger; otherwise `not_evaluable`.
- Coverage and key evidence: context and temporal coverage 66/66; zero healthy triggers; longest healthy joint episode 31 s, leaving 89 s headroom.
- Limitation: research-grade stuck candidate; detection capability awaits frozen-value injection.

#### Routing and data-quality guard

- 5-S2 evidence is attributed to MAP only when 5-S1 or 5-S3 also triggers; otherwise it follows the MAF-side arbitration in section 2.
- When 4-S2 cold-start IAT plausibility support is active, cap the confidence of IAT-dependent 5-S2 residual evidence at `low`; 5-S1 and 5-S3 are unaffected because they do not consume IAT.
- `tps` is excluded as a trigger because it is saturated near 83.1–83.5% and lacks the expected physical relationships in this dataset. Pedal demand is the frozen substitute.

## Reference

[1] SAE International. (2007). *Diagnostic trouble code definitions* (SAE Standard No. J2012_200706). SAE International.

[2] Wang, L., Zou, X., Qin, H., & Geng, P. (2021). Design of OBD function test on production vehicle (PVE). *E3S Web of Conferences, 268*, 01047. https://doi.org/10.1051/e3sconf/202126801047

[3] Bosch, Robert GmbH. (2018). *Bosch automotive handbook* (10th ed.). SAE International.

[4] California Air Resources Board. *Title 13, California Code of Regulations, §1968.2: Malfunction and diagnostic system requirements — 2004 and subsequent model-year passenger cars, light-duty trucks, and medium-duty vehicles and engines*, sections (e)(10) and (e)(15) (OAL 2006 amendment text; current codification cross-checked via Cornell LII, accessed 2026-07-17).

[5] Yoo, I., Simpson, K., Bell, M., & Majkowski, S. (2000). *An engine coolant temperature model and application for cooling system diagnosis* (SAE Technical Paper No. 2000-01-0939). SAE International. https://doi.org/10.4271/2000-01-0939

[6] Ford Motor Company. (2017). *2019 MY OBD system operation summary for gasoline engines* (Rev. Oct. 24, 2017), “Thermostat Monitor,” pp. 150–151. https://www.fordservicecontent.com/ford_content/catalog/motorcraft/OBDSM1900.pdf

[7] *Method for detecting cooling system faults* (U.S. Patent No. 6,463,892). (2002). Ford Global Technologies. U.S. Patent and Trademark Office.

[8] *Abnormality detector apparatus for a coolant apparatus for cooling an engine* (U.S. Patent No. 6,200,021). (2001). Toyota Motor Corp. U.S. Patent and Trademark Office.

[9] Nyberg, M., & Nielsen, L. (1997). Model based diagnosis for the air intake system of the SI-engine (SAE Technical Paper 970209). SAE International. https://doi.org/10.4271/970209

[10] *Fault identification diagnostic for intake system sensors* (U.S. Patent No. 6,701,282). (2004). U.S. Patent and Trademark Office.

[11] International Organization for Standardization. (2018). *Road vehicles — Functional safety — Part 5: Product development at the hardware level* (ISO Standard No. 26262-5:2018). ISO.

[12] *Method and apparatus to evaluate an intake air temperature monitoring circuit* (U.S. Patent No. 7,120,535). (2006). U.S. Patent and Trademark Office.

[13] SAE International. *E/E diagnostic test modes* (SAE Standard No. J1979). Cited for OBD-II PID physical measurement bounds (PID 0x0F, intake air temperature: −40 to 215°C).
