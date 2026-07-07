# INTERFACE.md — Granite Lifeline Field Definitions
**Version:** v0.4  
**Last updated:** 2026-07-07  
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
| 1 | timestamp | string (ISO 8601) | Data Layer | Model Layer | Draft |
| 2 | rpm | float | Data Layer | Model Layer | Draft |
| 3 | speed | float | Data Layer | Model Layer | Draft |
| 4 | coolant_temp | float | Data Layer | Model Layer | Draft |
| 5 | map | float | Data Layer | Model Layer | Draft |
| 6 | maf | float | Data Layer | Model Layer | Draft |
| 7 | tps | float | Data Layer | Model Layer | Draft |
| 8 | accel_pedal_d | float | Data Layer | Model Layer | Draft |
| 9 | accel_pedal_e | float | Data Layer | Model Layer | Draft |
| 10 | coolant_rolling_avg | float | Data Layer | Model Layer | Draft |
| 11 | rpm_rolling_avg | float | Data Layer | Model Layer | Draft |
| 12 | coolant_slope | float | Data Layer | Model Layer | Draft |
| 13 | acceleration | float | Data Layer | Model Layer | Draft |
| 14 | load_stress | float | Data Layer | Model Layer | Draft |
| 15 | maf_map_cohesion | float | Data Layer | Model Layer | Draft |
| 16 | rpm_variation | float | Data Layer | Model Layer | Draft |
| 17 | failure_label | string | Data Layer | Model Layer (internal only) | TBD |
| 18 | risk_class | string | Data Layer | Model Layer (internal only) | TBD |
| 19 | condition_ratio | float | Data Layer | Model Layer (internal only) | TBD |
| 20 | window_id | string | Data Layer | Model Layer (internal only) | TBD |
| 21 | anomaly_type | string (enum) | Model Layer | Report Layer | Confirmed |
| 22 | risk_score | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 23 | risk_level | string | Model Layer | Report Layer → Dashboard | TBD |
| 24 | component | string | Model Layer | Report Layer → Dashboard | Confirmed (mirrors anomaly_type) |
| 25 | prediction_confidence | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 26 | key_signals | array of objects | Model Layer | Report Layer → Dashboard | Confirmed |
| 27 | estimated_cycles_to_failure | int | Model Layer | Report Layer → Dashboard | Draft — required client output; estimation method Story 8 |
| 28 | estimated_failure_probability | float (0–1) | Model Layer | Report Layer → Dashboard | Draft — required client output; estimation method Story 8 |
| 29 | risk_history | array of objects | Report Layer | Dashboard | TBD |
| 30 | anomaly_description | string | Report Layer | Dashboard | Draft |
| 31 | possible_cause | string | Report Layer | Dashboard | Draft |
| 32 | recommended_action | array of strings | Report Layer | Dashboard | Draft |

**Status guide**
- **Confirmed** — field definition and content fully confirmed by owning layer
- **Draft** — field definition agreed, implementation can start
- **TBD** — direction known, details pending confirmation

*Pending Data Layer fields referenced by Section 2.4 (`intake_temp`, `ambient_temp`,
`intake_ambient_delta`, `map_slope`, `pedal_throttle_gap`, `idle_flag`,
`idle_rpm_stability`, `rpm_slope`) will be added to this table by the Data Layer once
their definitions are confirmed.*

---

## Section 1: Data Layer Output Fields

Consumed by: **Model Layer**

### 1.1 Raw signals

Fields ingested from KIT OBD-II CSV after field mapping and cleaning.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| timestamp | string (ISO 8601) | Aligned timestamp converted from KIT raw time | `"2026-06-16T10:00:00Z"` | Draft |
| rpm | float | Engine speed (RPM) after cleaning | `2500.0` | Draft |
| speed | float | Vehicle speed (km/h) after cleaning and optional resampling | `48.0` | Draft |
| coolant_temp | float | Engine coolant temperature (°C) after cleaning | `92.5` | Draft |
| map | float | Intake manifold absolute pressure (kPa) after cleaning | `85.0` | Draft |
| maf | float | Mass airflow rate (g/s) after cleaning | `18.6` | Draft |
| tps | float | Absolute throttle position (%) after cleaning | `42.0` | Draft |
| accel_pedal_d | float | Accelerator pedal position D (%) after cleaning | `35.0` | Draft |
| accel_pedal_e | float | Accelerator pedal position E (%) after cleaning | `37.5` | Draft |

### 1.2 Engineered features

Derived from raw signals by Data Layer. Used by Model Layer as inputs for TTM fine-tuning and inference.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| coolant_rolling_avg | float | Rolling average of coolant temperature over a 30-second window (°C) | `91.8` | Draft |
| rpm_rolling_avg | float | Rolling average of engine RPM over a 10-second window | `2450.0` | Draft |
| coolant_slope | float | Rate of coolant temperature change over a rolling window (°C/min) | `3.1` | Draft |
| acceleration | float | Estimated vehicle acceleration from speed change over time (m/s²) | `0.8` | Draft |
| load_stress | float | Engine load stress indicator derived from RPM × TPS | `105000.0` | Draft |
| maf_map_cohesion | float | Normalised deviation between MAF and MAP, representing intake consistency | `0.18` | Draft |
| rpm_variation | float | Rolling standard deviation of RPM over a 15-second window, representing combustion stability | `120.0` | Draft |

### 1.3 Proxy labels

> **Internal to Model Layer only.** Used for TTM training and evaluation. Do not flow to Report Layer or Dashboard.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| failure_label | string | Proxy failure label from engineering rules. **Not a real mechanical fault label.** | `"cooling_risk"` | TBD — proxy label rules pending validation |
| risk_class | string | Proxy risk class from rule-based failure conditions | `"HIGH"` | TBD — thresholds pending calibration |
| condition_ratio | float | Ratio of samples within a window satisfying a proxy abnormal condition | `0.31` | TBD — aggregation threshold pending |
| window_id | string | Identifier for each sliding input window | `"001"` | TBD — depends on final windowing strategy |

### 1.4 Request to Data Layer: trip/cycle identifier (added 2026-07-07)

> **Needed for the new Model Layer failure-estimation fields** (`estimated_cycles_to_failure`,
> `estimated_failure_probability` — see Section 2.2). To accumulate a risk score history and
> express "failure within the next X cycles", the Model Layer needs a **cycle unit**. We verified
> this is fully derivable from the raw KIT data (`dataset/10.35097-1130/data/dataset/OBD-II-Dataset/`):
>
> - **One CSV file = one trip/drive cycle.** The filename encodes date + vehicle + route + condition
>   (e.g. `2017-07-05_Seat_Leon_RT_S_Stau.csv`), and the in-file `Time` column gives the start time
>   for ordering multiple trips on the same day.
> - **Chronological continuity holds**: all 81 trips are the same Seat Leon, so trips sorted by
>   filename date then start time form a genuine per-vehicle history.
> - **Trip boundaries are file boundaries** — no extra metadata is needed.
>
> **Ask:** forward a `trip_id` (or monotonically increasing cycle index) column per row, derived
> from source filename + start time, and do not merge trips without it. This is a small mechanical
> addition on the Data Layer side.

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

|      |      |      |
|---|---|---|
|      |      |      |
|      |      |      |
