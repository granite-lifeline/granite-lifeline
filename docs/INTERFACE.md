# INTERFACE.md — Granite Lifeline Field Definitions
**Version:** v0.2  
**Last updated:** 2026-06-20  
**Status:** Confirmed — anomaly_type classification updated per Model Layer confirmation

---

## Pipeline Overview

```
KIT OBD-II CSV
    → [Data Layer]  raw signals + engineered features + proxy labels
    → [Model Layer / TTM]  anomaly_type, risk_score, risk_level, component, prediction_confidence, key_signals
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
| 8 | coolant_rolling_avg | float | Data Layer | Model Layer | Draft |
| 9 | rpm_rolling_avg | float | Data Layer | Model Layer | Draft |
| 10 | coolant_slope | float | Data Layer | Model Layer | Draft |
| 11 | acceleration | float | Data Layer | Model Layer | Draft |
| 12 | load_stress | float | Data Layer | Model Layer | Draft |
| 13 | maf_map_cohesion | float | Data Layer | Model Layer | Draft |
| 14 | rpm_variation | float | Data Layer | Model Layer | Draft |
| 15 | failure_label | string | Data Layer | Model Layer (internal only) | TBD |
| 16 | risk_class | string | Data Layer | Model Layer (internal only) | TBD |
| 17 | condition_ratio | float | Data Layer | Model Layer (internal only) | TBD |
| 18 | window_id | string | Data Layer | Model Layer (internal only) | TBD |
| 19 | anomaly_type | string (enum) | Model Layer | Report Layer | Confirmed |
| 20 | risk_score | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 21 | risk_level | string | Model Layer | Report Layer → Dashboard | TBD |
| 22 | component | string | Model Layer | Report Layer → Dashboard | Confirmed (mirrors anomaly_type) |
| 23 | prediction_confidence | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 24 | key_signals | array of objects | Model Layer | Report Layer → Dashboard | Confirmed |
| 25 | risk_history | array of objects | Report Layer | Dashboard | TBD |
| 26 | anomaly_description | string | Report Layer | Dashboard | Draft |
| 27 | possible_cause | string | Report Layer | Dashboard | Draft |
| 28 | recommended_action | array of strings | Report Layer | Dashboard | Draft |

**Status guide**
- **Confirmed** — field definition and content fully confirmed by owning layer
- **Draft** — field definition agreed, implementation can start
- **TBD** — direction known, details pending confirmation

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

---

## Section 2: Model Layer Output Fields

Consumed by: **Report Layer** (and pass-through to Dashboard where noted)

### 2.1 Output JSON example

```json
{
  "timestamp": "2026-06-16T10:00:00Z",
  "anomaly_type": "cooling_system_stress",
  "risk_score": 0.82,
  "risk_level": "Medium",
  "component": "cooling_system_stress",
  "prediction_confidence": 0.84,
  "key_signals": [
  {"feature": "coolant_temp", "value": 102, "unit": "°C", "reference_range": [90, 95]}
  ]
}
```

### 2.2 Field definitions

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| timestamp | string (ISO 8601) | Pass-through from Data Layer | `"2026-06-16T10:00:00Z"` | Draft |
| anomaly_type | string (enum) | Fault/anomaly classification output by TTM. Three confirmed values — see Section 2.3. | `"cooling_system_stress"` | Confirmed |
| risk_score | float (0–1) | Probability / severity of detected anomaly, output by TTM | `0.82` | Draft |
| risk_level | string | Risk classification derived from risk_score by Model Layer. Values: `Low` \| `Medium` \| `High`. Thresholds pending calibration. | `"Medium"` | TBD — thresholds pending calibration |
| component | string | Affected component. **Mirrors anomaly_type** — retained as a separate field for downstream compatibility (e.g., Dashboard component-based filtering), though currently redundant with anomaly_type. | `"cooling_system_stress"` | Confirmed |
| prediction_confidence | float (0–1) | Model confidence in risk_score, provided directly by Model Layer. | `0.84` | Draft |
| key_signals | array of objects | Top signals contributing to risk prediction, in order of importance. Structure: `[{feature, value, unit, reference_range}]`. See Section 2.4. | See JSON above | Confirmed |

### 2.3 anomaly_type Classification

> Confirmed by Model Layer on 2026-06-20. Replaces the previous interim classification (`cooling_degradation` / `vacuum_leak` / `intake_blockage`).
>
> Note: `component` mirrors `anomaly_type` for all three values (see 2.2).

| anomaly_type | component |
|---|---|
| `cooling_system_stress` | `cooling_system_stress` |
| `air_intake_maf_anomaly` | `air_intake_maf_anomaly` |
| `accelerator_pedal_sensor` | `accelerator_pedal_sensor` |

### 2.4 anomaly_type → key_signals Mapping (Confirmed)

> All three mappings confirmed by Model Layer on 2026-06-20.
>
> Report Layer uses this mapping to understand which signals are expected to be anomalous for each fault type. This supports prompt design and test case construction (typical vs atypical scenarios).

| anomaly_type | key_signals (in order of importance) | Rationale |
|---|---|---|
| `cooling_system_stress` | `coolant_temp` | After warm-up phase (>85°C reached), flag elevated risk when: (1) coolant temp exceeds ~100°C, and/or (2) temp keeps rising at >2–3°C/min instead of plateauing. Normal range is 90–95°C. Matches brief's example: "Coolant temperature rising faster than normal—possible water pump degradation." |
| `air_intake_maf_anomaly` | `maf`, `map` | MAF correlates with intake MAP at ~0.83 average (range 0.6–0.9). Proxy: fit "expected MAF" baseline from map, then flag when residual (actual − expected MAF) is large/sustained. Suggests MAF sensor drift, dirty air filter, or vacuum leak. |
| `accelerator_pedal_sensor` | `accel_pedal_d`, `accel_pedal_e` | Dual redundant sensors show high correlation (0.96–0.99) consistently across all 81 trips. Mean absolute difference ~0.8pp, with brief spikes >10pp in ~1% of samples (likely sensor lag during fast movements, not faults). |

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
| component | string | `"cooling_system_stress"` | Confirmed |
| prediction_confidence | float (0–1) | `0.84` | Draft |
| key_signals | array of objects | See Section 2 | Confirmed |

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
