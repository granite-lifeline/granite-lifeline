# INTERFACE.md — Granite Lifeline Field Definitions
**Version:** v0.5  
**Last updated:** 2026-07-08  
**Status:** Confirmed — 7-type anomaly_type enum; 4 types pending Model Layer support; 2 failure-estimation fields added per S3.1 standup

---

## Pipeline Overview

```
KIT OBD-II CSV
    → [Data Layer]  raw signals + engineered features + proxy labels
    → [Model Layer / TTM]  anomaly_type, risk_score, risk_level, component, prediction_confidence, key_signals, estimated_cycles_to_failure, estimated_failure_probability
    → [Report Layer / Granite]  anomaly_description, possible_cause, recommended_action + pass-through fields
    → [Dashboard]
```

---

## Master Field Table

All fields in data-flow order. Pass-through fields originate in one layer and are forwarded unchanged by a later layer.

| # | Field Name | Type | Origin Layer | Consumed by | Status |
|---|---|---|---|---|---|
| 1 | timestamp | string (ISO 8601) | Data Layer | Model Layer | Confirmed |
| 2 | trip_id | string | Data Layer | Model Layer | Confirmed |
| 3 | segment_id | string | Data Layer | Model Layer | Confirmed |
| 4 | row_in_segment | int | Data Layer | Model Layer | Confirmed |
| 5 | dt_seconds | float (nullable) | Data Layer | Model Layer | Confirmed |
| 6 | thermal_state | string | Data Layer | Model Layer | Confirmed |
| 7 | child_state | string | Data Layer | Model Layer | Confirmed |
| 8 | operating_state | string | Data Layer | Model Layer | Confirmed |
| 9 | condition_confidence | string | Data Layer | Model Layer | Confirmed |
| 10 | condition_quality_flags | string | Data Layer | Model Layer | Confirmed |
| 11 | coolant_temp | float (nullable) | Data Layer | Model Layer | Confirmed |
| 12 | map | float (nullable) | Data Layer | Model Layer | Confirmed |
| 13 | rpm | float (nullable) | Data Layer | Model Layer | Confirmed |
| 14 | speed | float (nullable) | Data Layer | Model Layer | Confirmed |
| 15 | intake_temp | float (nullable) | Data Layer | Model Layer | Confirmed |
| 16 | maf | float (nullable) | Data Layer | Model Layer | Confirmed |
| 17 | tps | float (nullable) | Data Layer | Model Layer | Confirmed |
| 18 | ambient_temp | float (nullable) | Data Layer | Model Layer | Confirmed |
| 19 | accel_pedal_d | float (nullable) | Data Layer | Model Layer | Confirmed |
| 20 | accel_pedal_e | float (nullable) | Data Layer | Model Layer | Confirmed |
| 21 | coolant_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 22 | coolant_ambient_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 23 | coolant_stability | float (nullable) | Data Layer | Model Layer | Confirmed |
| 24 | intake_ambient_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 25 | intake_temp_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 26 | maf_derived_air_load_raw | float (nullable) | Data Layer | Model Layer | Confirmed |
| 27 | map_derived_air_load_raw | float (nullable) | Data Layer | Model Layer | Confirmed |
| 28 | maf_map_cohesion | float (nullable) | Data Layer | Model Layer | Confirmed |
| 29 | speed_density_maf_residual | float (nullable) | Data Layer | Model Layer | Confirmed |
| 30 | map_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 31 | accel_pedal_mean | float (nullable) | Data Layer | Model Layer | Confirmed |
| 32 | pedal_throttle_gap | float (nullable) | Data Layer | Model Layer | Confirmed |
| 33 | pedal_to_throttle_delay | float (nullable) | Data Layer | Model Layer | Confirmed |
| 34 | tps_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 35 | accel_pedal_channel_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 36 | accel_pedal_channel_ratio | float (nullable) | Data Layer | Model Layer | Confirmed |
| 37 | pedal_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 38 | engine_on_flag | float (0/1, nullable) | Data Layer | Model Layer | Confirmed |
| 39 | rpm_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 40 | idle_flag | float (0/1, nullable) | Data Layer | Model Layer | Confirmed |
| 41 | idle_rpm_stability | float (nullable) | Data Layer | Model Layer | Confirmed |
| 42 | failure_label | string | Data Layer | Model Layer (internal only) | TBD |
| 43 | risk_class | string | Data Layer | Model Layer (internal only) | TBD |
| 44 | condition_ratio | float | Data Layer | Model Layer (internal only) | TBD |
| 45 | window_id | string | Data Layer | Model Layer (internal only) | TBD |
| 46 | anomaly_type | string (enum) | Model Layer | Report Layer | Confirmed |
| 47 | risk_score | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 48 | risk_level | string | Model Layer | Report Layer → Dashboard | TBD |
| 49 | component | string | Model Layer | Report Layer → Dashboard | Confirmed (mirrors anomaly_type) |
| 50 | prediction_confidence | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 51 | key_signals | array of objects | Model Layer | Report Layer → Dashboard | Confirmed |
| 52 | estimated_cycles_to_failure | int | Model Layer | Report Layer → Dashboard | Draft — required client output; estimation method Story 8 |
| 53 | estimated_failure_probability | float (0–1) | Model Layer | Report Layer → Dashboard | Draft — required client output; estimation method Story 8 |
| 54 | risk_history | array of objects | Report Layer | Dashboard | TBD |
| 55 | anomaly_description | string | Report Layer | Dashboard | Draft |
| 56 | possible_cause | string | Report Layer | Dashboard | Draft |
| 57 | recommended_action | array of strings | Report Layer | Dashboard | Draft |

**Status guide**
- **Confirmed** — field definition and content fully confirmed by owning layer
- **Draft** — field definition agreed, implementation can start
- **TBD** — direction known, details pending confirmation

---

## Section 1: Data Layer Output Fields

Consumed by: **Model Layer**

> Current Data Layer output is the row-level `feature_dataset.csv`. All fields listed below are required columns in the interface model. 
> Numeric values may be nullable when the corresponding CSV cell is missing because of source-signal gaps, segment-boundary rules, rolling-window validity masks, event-only features, or baseline prediction availability.

### 1.1 Key, time, and operating-condition fields

Fields used to preserve row identity, trip/segment boundaries, and operating-condition context.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| timestamp | string (ISO 8601) | Aligned timestamp converted from KIT raw time | `"2026-06-16T10:00:00Z"` | Confirmed |
| trip_id | string | Trip identifier derived from source trip/file boundary | `"trip_0001"` | Confirmed |
| segment_id | string | Segment identifier; windows and slopes must not cross segment boundaries | `"trip_0001_seg_001"` | Confirmed |
| row_in_segment | int | Row index within the segment | `1` | Confirmed |
| dt_seconds | float (nullable) | Time delta from the previous row in the same segment | `1.0` | Confirmed |
| thermal_state | string | Thermal operating state assigned by the Data Layer | `"post_warmup"` | Confirmed |
| child_state | string | Driving-state subtype assigned by the Data Layer | `"steady_driving"` | Confirmed |
| operating_state | string | Combined operating-condition label | `"post_warmup_steady_driving"` | Confirmed |
| condition_confidence | string | Confidence level for the operating-condition assignment | `"high"` | Confirmed |
| condition_quality_flags | string | Quality flag for the operating-condition assignment | `"OK"` | Confirmed |

*`trip_id` is assigned in chronological cycle order, sorted by source filename date and in-file start time.*

### 1.2 Raw signals

Fields ingested from KIT OBD-II CSV after field mapping and cleaning.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| coolant_temp | float (nullable) | Engine coolant temperature (degC) after cleaning | `92.5` | Confirmed |
| map | float (nullable) | Intake manifold absolute pressure (kPa) after cleaning | `85.0` | Confirmed |
| rpm | float (nullable) | Engine speed (RPM) after cleaning | `2500.0` | Confirmed |
| speed | float (nullable) | Vehicle speed (km/h) after cleaning and optional resampling | `48.0` | Confirmed |
| intake_temp | float (nullable) | Intake air temperature (degC) after cleaning | `35.0` | Confirmed |
| maf | float (nullable) | Mass airflow rate (g/s) after cleaning | `18.6` | Confirmed |
| tps | float (nullable) | Absolute throttle position (%) after cleaning | `42.0` | Confirmed |
| ambient_temp | float (nullable) | Ambient air temperature (degC) after cleaning | `22.0` | Confirmed |
| accel_pedal_d | float (nullable) | Accelerator pedal position D (%) after cleaning | `35.0` | Confirmed |
| accel_pedal_e | float (nullable) | Accelerator pedal position E (%) after cleaning | `37.5` | Confirmed |

### 1.3 Engineered features

Derived from raw signals by the Data Layer. Used by the Model Layer as row-level inputs for analysis, TTM consumption, and later window-level aggregation.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| coolant_slope | float (nullable) | Rate of coolant temperature change within the same segment (degC/s) | `3.1` | Confirmed |
| coolant_ambient_delta | float (nullable) | Difference between coolant temperature and ambient temperature (degC) | `70.5` | Confirmed |
| coolant_stability | float (nullable) | Rolling coolant-temperature stability under valid post-warmup context | `0.4` | Confirmed |
| intake_ambient_delta | float (nullable) | Difference between intake temperature and ambient temperature (degC) | `13.0` | Confirmed |
| intake_temp_slope | float (nullable) | Rate of intake temperature change within the same segment (degC/s) | `0.2` | Confirmed |
| maf_derived_air_load_raw | float (nullable) | Raw MAF-side air-load proxy derived from MAF and RPM | `0.45` | Confirmed |
| map_derived_air_load_raw | float (nullable) | Raw MAP-side speed-density air-load proxy derived from RPM, MAP, and intake temperature | `720.0` | Confirmed |
| maf_map_cohesion | float (nullable) | Z-scored absolute difference between MAF-side and MAP-side air-load proxies | `0.18` | Confirmed |
| speed_density_maf_residual | float (nullable) | Residual between actual MAF and the MAP/speed-density baseline expected MAF | `1.2` | Confirmed |
| map_slope | float (nullable) | Rate of MAP change within the same segment (kPa/s) | `0.5` | Confirmed |
| accel_pedal_mean | float (nullable) | Mean of accelerator pedal channels D and E (%) | `36.25` | Confirmed |
| pedal_throttle_gap | float (nullable) | Residual between actual TPS and baseline expected TPS from pedal/RPM context (%) | `2.1` | Confirmed |
| pedal_to_throttle_delay | float (nullable) | Event-only delay from pedal step response to throttle response (s); non-event rows are nullable | `1.0` | Confirmed |
| tps_slope | float (nullable) | Rate of TPS change within the same segment (%/s) | `0.3` | Confirmed |
| accel_pedal_channel_delta | float (nullable) | Absolute difference between accelerator pedal channels D and E (%) | `2.5` | Confirmed |
| accel_pedal_channel_ratio | float (nullable) | Ratio between accelerator pedal channels D and E | `0.93` | Confirmed |
| pedal_slope | float (nullable) | Rate of accelerator pedal mean change within the same segment (%/s) | `0.4` | Confirmed |
| engine_on_flag | float (0/1, nullable) | Engine-running indicator derived from RPM | `1.0` | Confirmed |
| rpm_slope | float (nullable) | Rate of RPM change within the same segment (rpm/s) | `12.0` | Confirmed |
| idle_flag | float (0/1, nullable) | Idle-state indicator from operating-condition analysis | `0.0` | Confirmed |
| idle_rpm_stability | float (nullable) | Rolling RPM stability under valid idle context | `55.0` | Confirmed |

### 1.4 Proxy labels

> **Internal to Model Layer only.** Used for TTM training and evaluation. Do not flow to Report Layer or Dashboard.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| failure_label | string | Proxy failure label from engineering rules. **Not a real mechanical fault label.** | `"cooling_degradation"` | TBD — proxy label rules pending validation |
| risk_class | string | Proxy risk class from rule-based failure conditions | `"HIGH"` | TBD — thresholds pending calibration |
| condition_ratio | float | Ratio of samples within a window satisfying a proxy abnormal condition | `0.31` | TBD — aggregation threshold pending |
| window_id | string | Identifier for each sliding input window | `"001"` | TBD — depends on final windowing strategy |

---

## Section 2: Model Layer Output Fields

Consumed by: **Report Layer** (and pass-through to Dashboard where noted)

### 2.1 Output JSON example

```json
{
  "timestamp": "2026-06-16T10:00:00Z",
  "anomaly_type": "cooling_degradation",
  "risk_score": 0.82,
  "risk_level": "Medium",
  "component": "cooling_degradation",
  "prediction_confidence": 0.84,
  "key_signals": [
  {"feature": "coolant_temp", "value": 102, "unit": "°C", "reference_range": [90, 95]}
  ],
  "estimated_cycles_to_failure": 120,
  "estimated_failure_probability": 0.72
}
```

### 2.2 Field definitions

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| timestamp | string (ISO 8601) | Pass-through from Data Layer | `"2026-06-16T10:00:00Z"` | Draft |
| anomaly_type | string (enum) | Fault/anomaly classification output by TTM. Seven values defined — see Section 2.3. First 3 confirmed by Model Layer, remaining 4 from Data Layer. | `"cooling_degradation"` | Updated |
| risk_score | float (0–1) | Probability / severity of detected anomaly, output by TTM | `0.82` | Draft |
| risk_level | string | Risk classification derived from risk_score by Model Layer. Values: `Low` \| `Medium` \| `High`. Thresholds pending calibration. | `"Medium"` | TBD — thresholds pending calibration |
| component | string | Affected component. **Mirrors anomaly_type** — retained as a separate field for downstream compatibility (e.g., Dashboard component-based filtering), though currently redundant with anomaly_type. | `"cooling_degradation"` | Updated |
| prediction_confidence | float (0–1) | Model confidence in risk_score, provided directly by Model Layer. | `0.84` | Draft |
| key_signals | array of objects | Top signals contributing to risk prediction, in order of importance. Structure: `[{feature, value, unit, reference_range}]`. See Section 2.4. | See JSON above | Confirmed |
| estimated_cycles_to_failure | int | Estimated number of drive cycles (trips) remaining before the detected anomaly is projected to reach failure threshold, extrapolated from risk score history/trend. Requires the Data Layer `trip_id`/cycle index (Section 1.4). | `120` | Draft — required client output; estimation method Story 8 |
| estimated_failure_probability | float (0–1) | Probability that failure occurs within the `estimated_cycles_to_failure` horizon. Together with the field above, supports the Report Layer phrase "72% probability of failure within the next X cycles". | `0.72` | Draft — required client output; estimation method Story 8 |

### 2.3 anomaly_type Classification

> Updated on 2026-06-29 to align with grounded_knowledge.yaml proxy_failures definitions.
> Expanded from 3 to 7 anomaly types to match Data Layer domain knowledge.
>
> Note: `component` mirrors `anomaly_type` for all values (see 2.2).

| anomaly_type | component | Status |
|---|---|---|
| `cooling_degradation` | `cooling_degradation` | Confirmed - Model Layer supported |
| `air_intake_maf_anomaly` | `air_intake_maf_anomaly` | Confirmed - Model Layer supported |
| `accelerator_pedal_sensor` | `accelerator_pedal_sensor` | Confirmed - Model Layer supported |
| `intake_air_temperature_sensor_or_heat_soak_fault` | `intake_air_temperature_sensor_or_heat_soak_fault` | Pending - Data Layer defined, Model Layer TBD |
| `map_load_signal_plausibility_fault` | `map_load_signal_plausibility_fault` | Pending - Data Layer defined, Model Layer TBD |
| `electronic_throttle_tracking_fault` | `electronic_throttle_tracking_fault` | Pending - Data Layer defined, Model Layer TBD |
| `idle_speed_control_or_surge_degradation` | `idle_speed_control_or_surge_degradation` | Pending - Data Layer defined, Model Layer TBD |

### 2.4 anomaly_type → key_signals Mapping

> Updated on 2026-06-29. First 3 mappings confirmed by Model Layer. Remaining 4 mappings defined by Data Layer based on grounded_knowledge.yaml.
>
> Report Layer uses this mapping to understand which signals are expected to be anomalous for each fault type. This supports prompt design and test case construction (typical vs atypical scenarios).

| anomaly_type | key_signals (in order of importance) | Rationale | Status |
|---|---|---|---|
| `cooling_degradation` | `coolant_temp`, `coolant_slope`, `coolant_stability` | After warm-up phase (>85°C reached), flag elevated risk when: (1) coolant temp exceeds ~100°C, and/or (2) temp keeps rising at >2–3°C/min instead of plateauing. Normal range is 90–95°C. | Confirmed |
| `air_intake_maf_anomaly` | `maf`, `map`, `maf_map_cohesion` | MAF correlates with intake MAP at ~0.83 average (range 0.6–0.9). Proxy: fit "expected MAF" baseline from map, then flag when residual (actual − expected MAF) is large/sustained. Suggests MAF sensor drift, dirty air filter, or vacuum leak. | Confirmed |
| `accelerator_pedal_sensor` | `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_channel_delta` | Dual redundant sensors show high correlation (0.96–0.99) consistently across all 81 trips. Mean absolute difference ~0.8pp, with brief spikes >10pp in ~1% of samples (likely sensor lag during fast movements, not faults). | Confirmed |
| `intake_air_temperature_sensor_or_heat_soak_fault` | `intake_temp`, `ambient_temp`, `intake_ambient_delta` | Intake temperature abnormally high or low relative to ambient temperature, or does not vary with vehicle speed/load. Proxies IAT sensor faults, severe heat soak, or poor thermal management. | Data Layer defined |
| `map_load_signal_plausibility_fault` | `map`, `maf`, `tps`, `map_slope` | MAP cannot reasonably reflect load changes, or its relationship with MAF, throttle position, and engine speed is inconsistent. Proxies MAP sensor drift, blockage, hose issues, or signal sticking. | Data Layer defined |
| `electronic_throttle_tracking_fault` | `accel_pedal_d`, `accel_pedal_e`, `tps`, `pedal_throttle_gap` | After pedal demand increases, throttle opening does not change accordingly, or actual throttle position remains offset from expected value. Proxies ETC actuator sticking or position-control abnormalities. | Data Layer defined |
| `idle_speed_control_or_surge_degradation` | `rpm`, `idle_flag`, `idle_rpm_stability`, `rpm_slope` | Under idle conditions, RPM fluctuation is excessive, cyclic surging occurs, or engine cannot stabilize near target idle speed. Proxies idle-control degradation or combustion-stability issues. | Data Layer defined |

---

## Section 3: Report Layer Output Fields

Consumed by: **Dashboard**

Report Layer acts as a unified packager: it passes through fields from Model Layer unchanged, adds three Granite-generated fields, and maintains `risk_history` via local persistent storage.

### 3.1 Pass-through fields

Originate in Model Layer, forwarded unchanged by Report Layer.

| Field Name | Type | Example | Status |
|---|---|---|---|
| timestamp | string (ISO 8601) | `"2026-06-16T10:00:00Z"` | Draft |
| risk_score | float (0–1) | `0.72` | Draft |
| risk_level | string (Low/Medium/High) | `"Medium"` | Draft |
| component | string | `"cooling_degradation"` | Confirmed |
| prediction_confidence | float (0–1) | `0.84` | Draft |
| key_signals | array of objects | See Section 2 | Confirmed |
| estimated_cycles_to_failure | int | `120` | Draft — required client output |
| estimated_failure_probability | float (0–1) | `0.72` | Draft — required client output |

### 3.2 Report Layer maintained fields

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| risk_history | array of objects | Historical risk scores for trend visualisation. Report Layer appends `{timestamp, risk_score}` to local persistent storage on each inference call. Required by brief: "risk score over time". Structure: `[{timestamp, risk_score}]` | `[{"timestamp": "2026-06-15T10:00:00Z", "risk_score": 0.65}, {"timestamp": "2026-06-16T10:00:00Z", "risk_score": 0.82}]` | TBD — storage implementation pending Sprint 2 |

### 3.3 Generated fields

Generated by the three-layer Granite prompt chain.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| anomaly_description | string | Granite Layer 1: human-readable description of detected anomalous behaviour, including brief explanation of risk_level in practical terms | `"Coolant temperature is rising at 3.1°C/min, exceeding the normal range of 0–2°C/min. Medium risk means the issue is not immediately dangerous but should be addressed soon."` | Draft |
| possible_cause | string | Granite Layer 2: likely root cause inferred from key_signals and anomaly_type | `"Rising coolant temperature under sustained load may indicate cooling system degradation."` | Draft |
| recommended_action | array of strings | Granite Layer 3: suggested inspection or maintenance actions. Wording strength reflects prediction_confidence — high confidence gives specific actions, low confidence gives observational recommendations. | `["Check coolant level", "Inspect radiator"]` | Draft |

---

## Change Log

| Version | Date | Changes |
|---|---|---|
| v0.1 draft | 2026-06-16 | Initial consolidated draft. Key changes from individual layer drafts: (1) `explanation_text` → split into `anomaly_description` + `possible_cause` + `recommended_action`; (2) `affected_signals` (name list) → `key_signals` (object array with value/unit/reference_range); (3) `prediction_confidence` added as Draft — provided directly by Model Layer; (4) `component` origin clarified — derived by Model Layer from `anomaly_type`, mapping defined; (5) `risk_level` origin clarified — derived by Model Layer from `risk_score`; (6) `risk_history` origin resolved — Report Layer maintains persistent local storage, required by project brief; (7) Interim static mapping added for `anomaly_type` → `key_signals` (Section 2.4); (8) Field renamed: `normal_range` → `reference_range` (aligned with Data Layer naming); (9) `reference_range` source confirmed — Data Layer provides V1.0 in Sprint 2 Week 1, based on KIT dataset statistics |
| v0.2 | 2026-06-20 | Model Layer confirmed final `anomaly_type` classification, replacing interim values (`cooling_degradation` / `vacuum_leak` / `intake_blockage`) with: `cooling_system_stress`, `air_intake_maf_anomaly`, `accelerator_pedal_sensor`. All three `key_signals` mappings (Section 2.4) now confirmed — no longer interim. `component` field retained but now mirrors `anomaly_type` exactly (previously a distinct derived value). |
| v0.3 | 2026-07-04 | `anomaly_type` enum expanded from 3 to 7 per Data Layer grounded_knowledge.yaml proxy_failures (Sections 2.3/2.4, dated 2026-06-29). Model Layer registered the 4 pending types as 0.0-score placeholders in `kit_residual_detector.py` until the Data Layer forwards their key signals. `maf_map_cohesion` implementation moved from raw maf/map ratio to the agreed z-scored air-load difference (interim trip-window baseline; trigger calibrated at 1.8 across 36 healthy trips). Fixed stale `cooling_system_stress` example in Section 3.1. |
| v0.4 | 2026-07-07 | Added two Model Layer output fields requested by Report Layer at the S3.1 standup (mandatory client output — "72% probability of failure within the next X cycles" driven by risk score history): `estimated_cycles_to_failure` (int) and `estimated_failure_probability` (float 0–1). Added to Master Field Table (rows 27–28), Section 2.1 JSON example, Section 2.2 definitions, and Section 3.1 pass-through. Added Section 1.4 asking Data Layer to forward a `trip_id`/cycle-index column (verified derivable from raw KIT data: one CSV file = one trip; filename encodes date/route; `Time` column orders same-day trips). Estimation method to be implemented in Model Layer Story 8. |
| v0.5 | 2026-07-08 | Added Key, time, and operating-condition fields to the Master Field Table and Section 1.1. Expanded Section 1.2 raw signals to include the finalized cleaned signal set. Replaced earlier provisional engineered fields (`coolant_rolling_avg`, `rpm_rolling_avg`, `acceleration`, `load_stress`, `rpm_variation`) with the finalized 21 Data Layer derived features in Section 1.3. Reconstructed `trip_id` generation to satisfy Section 1.4: one CSV file maps to one trip/drive cycle, and trip_id is now assigned as a chronological cycle index derived from source filename date plus in-file start time, preserving all 81 trips and producing monotonic trip_0001–trip_0081 ordering for Model Layer risk-history and failure-estimation use. |

|      |      |      |
|---|---|---|
|      |      |      |
|      |      |      |
