# INTERFACE.md — Granite Lifeline Field Definitions
**Version:** v1.5  
**Last updated:** 2026-08-01  
**Status:** Confirmed — 5-type anomaly_type enum (`electronic_throttle_tracking_fault` and `idle_speed_control_or_surge_degradation` removed by the Data Layer; `intake_air_temperature_sensor_or_heat_soak_fault` renamed to `intake_air_temperature_sensor_fault`, 2026-07-19); 2 types pending Model Layer support, with their §2.4 key-signal mappings and rationales supplied by the Data Layer on 2026-07-19; Model Layer Story 3 hardening retained (`notes` field, null estimation placeholders, `accelerator_pedal_sensor` detection); Model Layer input requirements retained as §1.5 (2026-07-11); Data Layer scripts 00–41 now produce the confirmed 46-column `production_features.csv` contract (4 sample keys, 16 A-class context/raw fields, 24 B-class production features, and 2 provenance fields) under an explicit run directory; new §2.5 batch output envelope and risk-score history shape added for Report Layer integration (2026-07-20); Data Layer's decision-level `proxy_decisions.csv` (scripts 50–70) confirmed executable end-to-end against real data, 21-column schema documented in §1.4 — still not wired into the live upload pipeline (2026-07-27); that gap is now closed — the Data Layer runs scripts 50–70 inside `run_data_pipeline_for_upload` and returns `proxy_decisions_path`, so `proxy_decisions.csv` is produced by a live single-CSV upload (2026-07-31); the Model Layer now forwards those two types' verdicts into its own output JSON, with the verdict → `risk_score`/`prediction_confidence` mapping defined in §2.4 (2026-08-01); Story 8 is complete, so `estimated_cycles_to_failure` and `estimated_failure_probability` now carry real projected values instead of the `null` placeholders they have emitted since v0.5 (2026-08-01)

---

## Pipeline Overview

```
KIT OBD-II CSV
    → [Data Layer]  production_features.csv: 4 sample keys + 16 context/raw fields + 24 production features + 2 provenance fields
    → [Model Layer / TTM]  anomaly_type, risk_score, risk_level, component, prediction_confidence, key_signals, estimated_cycles_to_failure, estimated_failure_probability, notes
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
| 21 | segment_gap_seconds | float (nullable) | Data Layer | Model Layer | Confirmed |
| 22 | engine_on_flag | boolean (nullable) | Data Layer | Model Layer | Confirmed |
| 23 | coolant_ambient_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 24 | intake_ambient_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 25 | accel_pedal_mean | float (nullable) | Data Layer | Model Layer | Confirmed |
| 26 | accel_pedal_channel_delta | float (nullable) | Data Layer | Model Layer | Confirmed |
| 27 | pedal_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 28 | rpm_slope | float (nullable) | Data Layer | Model Layer | Confirmed |
| 29 | speed_density_maf_residual | float (nullable) | Data Layer | Model Layer | Confirmed |
| 30 | pedal_mapping_residual | float (nullable) | Data Layer | Model Layer | Confirmed |
| 31 | engine_start_observed | boolean (nullable) | Data Layer | Model Layer | Confirmed |
| 32 | engine_start_episode_id | string (nullable) | Data Layer | Model Layer | Confirmed |
| 33 | elapsed_since_engine_start | float (nullable) | Data Layer | Model Layer | Confirmed |
| 34 | ect_start | float (nullable) | Data Layer | Model Layer | Confirmed |
| 35 | aat_start | float (nullable) | Data Layer | Model Layer | Confirmed |
| 36 | iat_start | float (nullable) | Data Layer | Model Layer | Confirmed |
| 37 | maf_integral_180s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 38 | ect_rate_180s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 39 | intake_temp_stability | float (nullable) | Data Layer | Model Layer | Confirmed |
| 40 | speed_std_120s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 41 | maf_std_120s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 42 | rpm_std_120s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 43 | accel_pedal_mean_std_120s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 44 | map_range_60s | float (nullable) | Data Layer | Model Layer | Confirmed |
| 45 | schema_version | string | Data Layer | Model Layer | Confirmed |
| 46 | calibration_version | string | Data Layer | Model Layer | Confirmed |
| 47 | failure_label | string | Data Layer | Model Layer (internal only) | TBD |
| 48 | risk_class | string | Data Layer | Model Layer (internal only) | TBD |
| 49 | condition_ratio | float | Data Layer | Model Layer (internal only) | TBD |
| 50 | window_id | string | Data Layer | Model Layer (internal only) | TBD |
| 50a | proxy_id | string | Data Layer | Model Layer (internal only) | Confirmed |
| 50b | sub_check_id | string | Data Layer | Model Layer (internal only) | Confirmed |
| 50c | result_state | string (enum) | Data Layer | Model Layer (internal only) | Confirmed |
| 50d | dtc_candidate_label | string | Data Layer | Model Layer (internal only) | Confirmed |
| 50e | dtc_emitted | boolean | Data Layer | Model Layer (internal only) | Confirmed |
| 51 | anomaly_type | string (enum) | Model Layer | Report Layer | Confirmed |
| 52 | risk_score | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 53 | risk_level | string | Model Layer | Report Layer → Dashboard | TBD |
| 54 | component | string | Model Layer | Report Layer → Dashboard | Confirmed (mirrors anomaly_type) |
| 55 | prediction_confidence | float (0–1) | Model Layer | Report Layer → Dashboard | Draft |
| 56 | key_signals | array of objects | Model Layer | Report Layer → Dashboard | Confirmed |
| 57 | estimated_cycles_to_failure | int \| null | Model Layer | Report Layer → Dashboard | Draft — projected number of chronological driving cycles until the trip-level mean risk reaches the Model Layer High-risk threshold; `null` when fewer than five trips exist, the trend is non-rising, or the projection exceeds 50 cycles. This is not a physical remaining-useful-life estimate. |
| 58 | estimated_failure_probability | float (0–1) \| null | Model Layer | Report Layer → Dashboard | Draft — model-based probability that the linear trip-risk projection crosses the High-risk threshold within the next 10 driving cycles; `null` when fewer than five trips exist. It is not an empirically calibrated probability of mechanical failure. |
| 59 | notes | array of strings | Model Layer | Report Layer → Dashboard | Confirmed — added Story 3 |
| 60 | risk_history | array of objects | Report Layer | Dashboard | TBD |
| 61 | anomaly_description | string | Report Layer | Dashboard | Draft |
| 62 | possible_cause | string | Report Layer | Dashboard | Draft |
| 63 | recommended_action | array of strings | Report Layer | Dashboard | Draft |

Rows 50a–50e are the decision-level fields of `proxy_decisions.csv` that the Model Layer reads when forwarding the two anomaly types it does not score itself. They are letter-suffixed because they belong to a separate decision-grain table rather than the row-level feature flow; the full 21-column schema is in §1.4.

**Status guide**
- **Confirmed** — field definition and content fully confirmed by owning layer
- **Draft** — field definition agreed, implementation can start
- **TBD** — direction known, details pending confirmation

---

## Section 1: Data Layer Output Fields

Consumed by: **Model Layer**

> **Confirmed by the Data Layer on 2026-07-08** (returned interface, `INTERFACE-from data layer.md`). Current Data Layer output is the row-level `feature_dataset.csv`. All fields listed below are required columns in the interface model.
> Numeric values may be nullable when the corresponding CSV cell is missing because of source-signal gaps, segment-boundary rules, rolling-window validity masks, event-only features, or baseline prediction availability.
>
> **Production handoff update (2026-07-19):** scripts 00–41 now implement the replacement `production_features.csv` contract with 46 ordered columns: 4 sample keys, 16 A-class context/raw fields, 24 B-class production features, and 2 provenance fields. The B-class production feature count remains 24. Normal runtime output is `data/processed/runs/<run_id>/features/41_production/production_features.csv`, with its adjacent `production_feature_manifest.json`; `run_id` is explicit and no stage may infer a `latest` run. The 2026-07-08 statements below remain historical delivery records for the legacy `feature_dataset.csv`, not the current production contract.

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

> **v0.4 §1.4 request resolved (2026-07-08):** the trip/cycle identifier the Model Layer asked for is delivered as `trip_id` above — one CSV file = one trip/drive cycle, assigned as a monotonic chronological index (`trip_0001`–`trip_0081`) from source filename date plus in-file start time, preserving all 81 trips. Story 8's risk-score-history and failure-estimation work is unblocked on the Data Layer side.
>
> **Production handoff continuity (2026-07-19):** the replacement contract retains the same four sample keys and trip/cycle semantics. For a fixed source dataset, raw-file discovery order must not change `trip_id`; source files are ordered by UTC trip start time with source filename as the deterministic tie-breaker. Sample rows are emitted in stable `(timestamp, trip_id, segment_id, row_in_segment)` order, and downstream windows must not cross trip or segment boundaries.

### 1.2 Raw signals

Fields ingested from KIT OBD-II CSV after field mapping and cleaning.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| coolant_temp | float (nullable) | Engine coolant temperature (°C) after cleaning | `92.5` | Confirmed |
| map | float (nullable) | Intake manifold absolute pressure (kPa) after cleaning | `85.0` | Confirmed |
| rpm | float (nullable) | Engine speed (RPM) after cleaning | `2500.0` | Confirmed |
| speed | float (nullable) | Vehicle speed (km/h) after cleaning and optional resampling | `48.0` | Confirmed |
| intake_temp | float (nullable) | Intake air temperature (°C) after cleaning | `35.0` | Confirmed |
| maf | float (nullable) | Mass airflow rate (g/s) after cleaning | `18.6` | Confirmed |
| tps | float (nullable) | Absolute throttle position (%) after cleaning | `42.0` | Confirmed |
| ambient_temp | float (nullable) | Ambient air temperature (°C) after cleaning | `22.0` | Confirmed |
| accel_pedal_d | float (nullable) | Accelerator pedal position D (%) after cleaning | `35.0` | Confirmed |
| accel_pedal_e | float (nullable) | Accelerator pedal position E (%) after cleaning | `37.5` | Confirmed |

> **Production handoff retention (2026-07-19):** all ten cleaned raw signals remain A-class columns in `production_features.csv` and are not counted among the 24 B-class production features. `tps` remains a Model Layer raw channel; removal of the non-executable electronic-throttle proxy does not remove this signal or authorize it as a proxy-verdict input.

### 1.3 Engineered  features

Derived from validated canonical/context inputs by the Data Layer. The replacement schema contains 24 ordered B-class fields used by the Model Layer as row-level inputs for analysis, TTM consumption, and later window-level aggregation.

> **Supersedes the provisional v0.1–v0.5 feature set.** `coolant_rolling_avg`, `rpm_rolling_avg`, `acceleration`, `load_stress`, and `rpm_variation` are no longer part of the interface; the Model Layer MVP keeps computing internal equivalents until Story 5 switches the pipeline to this output *(done 2026-07-13 — internal feature computation removed, see v0.8)*. Note also that `coolant_slope` is delivered in **°C/s within a segment** (earlier drafts specified °C/min) — Model Layer cooling thresholds are rescaled at the Story 5 switch *(done 2026-07-13: 2.0–8.0 °C/min → 0.0333–0.1333 °C/s, see v0.8)*.
>
> **Schema v1 replacement (2026-07-19):** the historical 21-field delivery described above is replaced in the planned `production_features.csv` by the following 24-field B-class allowlist. Removed legacy calculations remain documented in the note above but are not columns in the replacement file. Field identity, order, type, unit, null semantics, and version—not the number alone—define correctness.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| segment_gap_seconds | float (nullable) | Time from the previous observable segment end; populated only on the current segment's first row and null elsewhere or when predecessor context is unavailable (s) | `120.0` | Confirmed |
| engine_on_flag | boolean (nullable) | Engine-running indicator defined as `rpm >= 50`; null when RPM is not quality-valid | `true` | Confirmed |
| coolant_ambient_delta | float (nullable) | Difference between coolant and ambient temperature (°C) | `70.5` | Confirmed |
| intake_ambient_delta | float (nullable) | Difference between intake and ambient temperature (°C) | `13.0` | Confirmed |
| accel_pedal_mean | float (nullable) | Mean of quality-valid accelerator pedal channels D and E (%) | `36.25` | Confirmed |
| accel_pedal_channel_delta | float (nullable) | Absolute difference between quality-valid accelerator pedal channels D and E (percentage points) | `2.5` | Confirmed |
| pedal_slope | float (nullable) | Within-continuity rate of accelerator pedal mean change (percentage points/s) | `0.4` | Confirmed |
| rpm_slope | float (nullable) | Within-continuity rate of RPM change (rpm/s) | `12.0` | Confirmed |
| speed_density_maf_residual | float (nullable) | Actual MAF minus expected MAF from the frozen speed-density transform (g/s); production execution may predict but never fit | `1.2` | Confirmed |
| pedal_mapping_residual | float (nullable) | Pedal E minus its frozen linear prediction from pedal D (percentage points) | `0.8` | Confirmed |
| engine_start_observed | boolean (nullable) | True only at a valid within-continuity RPM transition from `<50` to `>=50` | `true` | Confirmed |
| engine_start_episode_id | string (nullable) | Foreign key to the authoritative engine-start episode table; null outside an observed episode | `"trip_0001_start_001"` | Confirmed |
| elapsed_since_engine_start | float (nullable) | Elapsed seconds from the observed RPM crossing; zero at the crossing and null outside the episode | `45.0` | Confirmed |
| ect_start | float (nullable) | Crossing-row engine coolant temperature stored in the episode table and mapped by episode key (°C) | `22.0` | Confirmed |
| aat_start | float (nullable) | Crossing-row ambient air temperature stored in the episode table and mapped by episode key (°C) | `18.0` | Confirmed |
| iat_start | float (nullable) | Crossing-row intake air temperature retained as engine-start/model context (°C) | `20.0` | Confirmed |
| maf_integral_180s | float (nullable) | Trapezoidal MAF integral over 181 valid 1 Hz endpoints / 180 intervals within one continuity block and engine-start episode (g) | `2800.0` | Confirmed |
| ect_rate_180s | float (nullable) | `(ECT[t] - ECT[t-180s]) / 3` over 181 valid 1 Hz endpoints (°C/min) | `4.0` | Confirmed |
| intake_temp_stability | float (nullable) | Sample standard deviation over 60 consecutive valid 1 Hz intake-temperature samples (°C) | `0.4` | Confirmed |
| speed_std_120s | float (nullable) | Sample standard deviation over 120 consecutive valid 1 Hz speed samples (km/h) | `1.5` | Confirmed |
| maf_std_120s | float (nullable) | Sample standard deviation over 120 consecutive valid 1 Hz MAF samples (g/s) | `0.8` | Confirmed |
| rpm_std_120s | float (nullable) | Sample standard deviation over 120 consecutive valid 1 Hz RPM samples (rpm) | `55.0` | Confirmed |
| accel_pedal_mean_std_120s | float (nullable) | Sample standard deviation over 120 consecutive valid 1 Hz pedal-mean samples (%) | `0.6` | Confirmed |
| map_range_60s | float (nullable) | Rolling maximum minus minimum over 60 consecutive valid 1 Hz MAP samples (kPa) | `3.0` | Confirmed |

#### Production output provenance

These two fields are appended after the 24 production features. They are required output columns but are not counted as B-class production features.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| schema_version | string | Version of the production feature schema used to assemble the row | `"feature_schema.v1"` | Confirmed |
| calibration_version | string | Version of the frozen calibration registry used by calibrated feature transforms | `"calibration.v1"` | Confirmed |

### 1.4 Proxy labels

> **Internal to Model Layer only.** Used for TTM training and evaluation. Do not flow to Report Layer or Dashboard.
>
> **Current live delivery (v1.5):** the Data Layer's upload path now runs
> proxy stages 50–70 by default and returns an absolute
> `proxy_decisions_path` alongside `production_features_path`.
> `proxy_decisions.csv` is a decision-grain table consumed by the Model
> Layer's optional `--proxy-decisions <path>` argument. The Dashboard upload
> pipeline passes this path through when present. The legacy row-level fields
> below are retained only as internal/superseded proxy-label fields; the live
> forwarding contract is the decision-level `proxy_decisions.csv` schema
> documented in the 2026-07-27 and 2026-07-31 notes below.

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| failure_label | string | Proxy failure label from engineering rules. **Not a real mechanical fault label.** | `"cooling_degradation"` | TBD — proxy label rules pending validation |
| risk_class | string | Proxy risk class from rule-based failure conditions | `"HIGH"` | TBD — thresholds pending calibration |
| condition_ratio | float | Ratio of samples within a window satisfying a proxy abnormal condition | `0.31` | TBD — aggregation threshold pending |
| window_id | string | Identifier for each sliding input window | `"001"` | TBD — depends on final windowing strategy |

> **Delivered (2026-07-12, Data Layer branch `gl-171`):** row-level master table `data_layer/proxy_design/proxy_training_labels.csv` (all 41 §1.1–1.3 columns + `proxy_flag_*`/`final_label_*` per anomaly type; 249,694 rows, 81 trips, 118 segments) and five duration window tables `data_layer/proxy_design/proxy_duration_tables/proxy_windows_{003,010,030,300,600}s.csv` (each window carries `trip_id`, `segment_id`, `window_start_timestamp`/`window_end_timestamp` — the alignment request below is satisfied). `failure_label` values match the §2.3 enum exactly (or `"normal"`); `risk_class` is binary HIGH/LOW; `window_id` format is `<segment_id>__<proxy_name>__w<NNNNNN>`. All data is healthy driving: every `final_label_*` is 0 (only sparse row-level `proxy_flag_*` candidates fire), so this delivery supports healthy-training filtering but contains no positive windows for evaluation — evaluation remains on Story 7 synthetic injection. Field statuses below to be flipped to Confirmed once `gl-171` merges.
>
> **Window-table alignment request (2026-07-11, Model Layer):** the Data Layer's labeled window table uses multiple duration-based window lengths, which will not line up one-to-one with the Model Layer's fixed 512+96-row windows. The table must therefore carry, per window: `trip_id`, `segment_id`, and start/end `timestamp`, so windows can be matched by time-range overlap instead of by `window_id`. The Model Layer uses these labels for (1) healthy-training-data filtering and (2) detection evaluation ground truth — they are **not** used to train TTM (fine-tuning uses healthy data only). `failure_label` naming to be reconciled against the §2.3 `anomaly_type` enum once the table is shared.
>
> **Proxy redevelopment note (2026-07-19):** the legacy delivery records above are retained unchanged. The failure definitions and production features are now being rebuilt against the versioned schema and calibration registry; scripts 50–70 will produce the new proxy evidence/decision outputs. The four fields in this subsection and their existing TBD statuses remain unchanged until that cross-layer replacement contract is completed.
>
> **New delivery confirmed executable (2026-07-27, Model Layer verification, GL-366):** the replacement contract referenced above is no longer just planned — `data_layer` scripts `50_rule_state_builder.py` → `60_event_evidence_builder.py` → `61_duration_evidence_builder.py` → `70_proxy_decision_builder.py` were run end-to-end against a real run directory (full 80-trip KIT dataset, stages 00–41 then 50–70) and produce `data/processed/runs/<run_id>/proxy/70_decisions/proxy_decisions.csv` plus `proxy_decision_manifest.json`. Confirmed 21-column schema (decision grain, one row per `(proxy_id, sub_check_id)` evaluation): `proxy_id, sub_check_id, unit_scope, trip_id, segment_id, engine_start_episode_id, evidence_start_timestamp, evidence_end_timestamp, direction, decision_role, result_state, decision_reason, decision_margin, dtc_candidate_label, dtc_emitted, routing_attribution, routed_dtc, confidence, confidence_capped_low, evidence_count, opportunity_present`. This is a **different, decision-level delivery** from the four row-level fields above (`failure_label`/`risk_class`/`condition_ratio`/`window_id`, still TBD/superseded) — it is not mapped onto them and no such mapping is proposed here. On the real dataset both currently-pending §2.3 anomaly types produce genuine `dtc_candidate_label` values (`intake_air_temperature_sensor_fault`: P0111, plus P0112/P0113 on the 4-S3 physical-range path once triggered; `map_load_signal_plausibility_fault`: P0106, with 5-S2 label-less until arbitration routing assigns one), confirming Group 1's DTC decision logic is real and working, not just unit-tested against synthetic frames. _(Correction, 2026-08-01: this sentence originally listed P0116 under the IAT type and P0128 under the MAP type. Both belong to `cooling_degradation` — P0116 is sub-check 1-S4 (support) and P0128 is 1-S1 (verdict). Re-verified per-sub-check against the 1,456-row GL-366 decision file.)_ This does **not** change either pending type's §2.3/§2.4 status — the Model Layer still will never compute their DTC decision logic (see Story 7's retired "Executable pending-type implementation" section) — it only documents that Group 1's own delivery is confirmed. The live-upload reachability gap recorded here was closed on 2026-07-31 and the Dashboard pass-through was added later; see the following notes.
>
> **Gap closed — proxy stages wired into the pipeline (2026-07-31, Data Layer):** the gap recorded above no longer exists. `run_data_pipeline` now accepts `include_proxy`, and `run_data_pipeline_for_upload` enables it by default, so scripts 50–70 execute in the same run directory immediately after stage 41. The returned summary carries `proxy_decisions_path` (absolute) alongside `production_features_path`, plus `proxy_stage_ids` and the four proxy manifests in `stage_manifests`. The batch and CLI paths are unchanged and stop at stage 41 unless `--include-proxy` is passed, and the 50–70 chain can still be rerun standalone against an existing run directory (as `run_fault_injection.py` does). Verified on a real single-CSV upload: both currently-pending §2.3 anomaly types produce genuine `dtc_candidate_label` values (`intake_air_temperature_sensor_fault` → P0111, `map_load_signal_plausibility_fault` → P0106). This does **not** change either pending type's §2.3/§2.4 status — the Model Layer still never computes their DTC decision logic; it only means the already-computed verdicts are now reachable from a live upload, so forwarding them can begin.
>
> **Upload acceptance semantics (2026-07-31, Data Layer):** uploads are validated by `run_data_pipeline_for_upload`, which raises `UploadRejected` with a stable `code`. Codes are `bad_filename`, `missing_columns`, `too_few_rows`, `unreadable_csv`, and `no_usable_segment`. Two changes are visible to the Dashboard. First, `too_few_rows` is now judged by recording duration (≥ 700 s) as well as raw row count: KIT files are sampled at 6–12 Hz across the corpus, so a row count cannot express a duration requirement. Second, `no_usable_segment` is raised **after** the pipeline has run when no contiguous cleaned `segment_id` reaches 700 rows (§1.5); unlike the pre-run codes it leaves the run directory in place and names it in the message. A fragmented recording can satisfy every pre-run check and still fail this — one trip in the reference corpus (731 s across 7 segments, longest 593 rows) does exactly that. Pipeline-stage failures surface as `DataPipelineError` with the original stage error chained.

### 1.5 Model Layer input requirements

Requirements the Model Layer places on `feature_dataset.csv` for TTM windowing, fine-tuning, and inference (recorded 2026-07-11; previously only documented in the Model Layer's internal stories).

| Requirement | Value | Rationale | Status |
|---|---|---|---|
| Sampling interval | 1 second, uniform (`dt_seconds` = 1.0 within a segment) | TTM context/forecast windows assume equally spaced rows | Satisfied — verified on the delivered `feature_dataset.csv` at the Story 5 switch (2026-07-13: 100% of rows `dt_seconds` = 1.0, no nulls; matches the gl-171 verification of 2026-07-12) |
| Minimum contiguous rows per `segment_id` | ≥ 700 | Model window is 512 context + 96 forecast rows, plus margin; windows must not cross segment boundaries, so shorter segments yield no usable window | Satisfied — verified on the delivered `feature_dataset.csv` at the Story 5 switch (2026-07-13: 83 of 118 segments ≥ 700 rows; matches the gl-171 verification of 2026-07-12) |
| Identity columns present | `trip_id`, `segment_id`, `timestamp` on every row | Segment-safe windowing, cycle indexing (Story 8), and time-range alignment with the Data Layer's labeled window table | Confirmed (§1.1) |

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
  "estimated_cycles_to_failure": 4,
  "estimated_failure_probability": 1.0,
  "notes": []
}
```

> `estimated_cycles_to_failure` / `estimated_failure_probability` are emitted by
> the Story 8 risk-history estimator when enough rising history is available.
> They remain required-but-nullable fields: `null` is still valid when history is
> insufficient, flat/falling, or outside the projection horizon. `notes` is always present
> (empty array when nothing is degraded) and carries human-readable messages about
> input repairs and disabled detections, e.g.
> `"accel_pedal_d/accel_pedal_e unavailable in input; accelerator_pedal_sensor detection disabled"`.

### 2.2 Field definitions

| Field Name | Type | Description | Example | Status |
|---|---|---|---|---|
| timestamp | string (ISO 8601) | Pass-through from Data Layer | `"2026-06-16T10:00:00Z"` | Draft |
| anomaly_type | string (enum) | Fault/anomaly classification output by TTM. Five values defined — see Section 2.3. First 3 confirmed by Model Layer, remaining 2 from Data Layer. | `"cooling_degradation"` | Updated |
| risk_score | float (0–1) | Probability / severity of detected anomaly, output by TTM | `0.82` | Draft |
| risk_level | string | Risk classification derived from risk_score by Model Layer. Values: `Low` \| `Medium` \| `High`. Thresholds pending calibration. | `"Medium"` | TBD — thresholds pending calibration |
| component | string | Affected component. **Mirrors anomaly_type** — retained as a separate field for downstream compatibility (e.g., Dashboard component-based filtering), though currently redundant with anomaly_type. | `"cooling_degradation"` | Updated |
| prediction_confidence | float (0–1) | Model confidence in risk_score, provided directly by Model Layer. | `0.84` | Draft |
| key_signals | array of objects | Top signals contributing to risk prediction, in order of importance. Structure: `[{feature, value, unit, reference_range}]`. See Section 2.4. | See JSON above | Confirmed |
| estimated_cycles_to_failure | int \| null | Estimated number of drive cycles (trips) remaining before the detected anomaly is projected to reach the Model Layer High-risk threshold, extrapolated from risk score history/trend. Uses the Data Layer `trip_id`/cycle index (Section 1.1). `null` when history is insufficient, flat/falling, or beyond the projection horizon. This is not a physical remaining-useful-life estimate. | `4` | Confirmed — Story 8 |
| estimated_failure_probability | float (0–1) \| null | Model-based probability that the risk-score projection crosses the High-risk threshold within the fixed horizon. Together with the field above, supports the Report Layer phrase "72% probability of failure within the next X cycles". `null` when history is insufficient. This is not empirically calibrated against labelled mechanical failures. | `1.0` | Confirmed — Story 8 |
| notes | array of strings | Degradation and fallback messages from Model Layer input validation and disabled detections (e.g. repaired implausible sensor values, pedal channels unavailable). Always present; empty array when nothing is degraded. | `["repaired 3 implausible coolant_temp value(s) outside [-40.0, 150.0]"]` | Confirmed — added Story 3 |

### 2.3 anomaly_type Classification

> Updated on 2026-06-29 to align with grounded_knowledge.yaml proxy_failures definitions.
> Expanded from 3 to 7 anomaly types to match Data Layer domain knowledge.
>
> **Reduced from 7 to 6 (2026-07-14, recording the Data Layer's 2026-07-13 removal):** `electronic_throttle_tracking_fault` is removed from the enum. Its judgement requires a credible actual throttle-position observation, but in the delivered dataset `tps` is saturated most of the time with a rate of change stuck at 0 for long stretches, and no substitute observation is feasible — the condition cannot be determined unless the dataset itself is updated. Data Layer guidance: any new proxy failure should avoid relying on `tps`. Note `tps` remains a TTM forecast channel and `pedal_throttle_gap` remains a delivered column — only the failure judgement is removed.
>
>
> **Reduced from 6 to 5 (2026-07-19, recording the Data Layer's documented infeasibility finding):** `idle_speed_control_or_surge_degradation` is removed from the enum. No idle sub-check can support a DTC-level verdict on this dataset for three independent reasons: (1) no PID exposes the ECU-commanded idle target, while the healthy released-idle population is legitimately multi-modal (approximately 775 / 950 / 1050 rpm because of warm-up fast idle and load compensation), so no stable reference band exists in either direction; (2) the required 70-second persistence is available in only 1.5–9.1% of trips, below the pre-registered 20% deployment floor; and (3) the available Seat Leon manuals provide no numeric nominal idle speed, while the required engine-specific ELSA/AU data sheets were not obtained. Failure 6 is therefore documented-infeasible, produces no runtime decision row, must not be represented as `not_evaluable`, and must not emit P0506/P0507. Revival requires a commanded-target PID, an idle-rich corpus, or an engine-specific nominal-idle data sheet.
>
> Note: `component` mirrors `anomaly_type` for all values (see 2.2).

| anomaly_type | component | Status |
|---|---|---|
| `cooling_degradation` | `cooling_degradation` | Confirmed - Model Layer supported |
| `air_intake_maf_anomaly` | `air_intake_maf_anomaly` | Confirmed - Model Layer supported |
| `accelerator_pedal_sensor` | `accelerator_pedal_sensor` | Confirmed - Model Layer supported (implemented Story 3: dual-channel delta rule, window mean scored 2–10pp; falls back to 0.0 score + note when pedal channels are absent) |
| `intake_air_temperature_sensor_fault` | `intake_air_temperature_sensor_fault` | Pending - Data Layer defined, Model Layer TBD |
| `map_load_signal_plausibility_fault` | `map_load_signal_plausibility_fault` | Pending - Data Layer defined, Model Layer TBD |

### 2.4 anomaly_type → key_signals Mapping

> Updated on 2026-06-29. First 3 mappings confirmed by Model Layer. Remaining 4 mappings defined by Data Layer based on grounded_knowledge.yaml.
>
> Report Layer uses this mapping to understand which signals are expected to be anomalous for each fault type. This supports prompt design and test case construction (typical vs atypical scenarios).
>
> **Update (2026-07-08):** every key_signal referenced by the four pending types is now confirmed and forwarded in the Data Layer `feature_dataset.csv` (Section 1.3), so Model Layer support for those types is no longer blocked on data availability — implementation is scheduled via Story 5. Rationale text below still quotes coolant limits in °C/min; the delivered `coolant_slope` unit is °C/s (see §1.3 note).
>
> **Naming reconciliation (2026-07-13, Story 5, Model Layer):** the delivered `feature_dataset.csv` column names were compared against the key_signals naming in this table — they match the v0.6/v0.7 interface exactly, no renames needed. The pending types' key signals (`intake_temp`, `ambient_temp`, `intake_ambient_delta`, `map_slope`, `idle_flag`, `idle_rpm_stability`, `rpm_slope`) are all confirmed **forwarded** in the delivery (reconciled: none renamed, none deferred). The pending types remain 0.0-score placeholders in the detector until their scoring is implemented.
>
> **Update (2026-07-14, v0.9):** `electronic_throttle_tracking_fault` row removed per the Data Layer's 2026-07-13 removal (see §2.3 note). The three remaining pending types' Rationale cells are reset to TBD — the earlier grounded_knowledge.yaml text is superseded by the Data Layer's forthcoming theory write-up, which they will fill in here.
>
> **Update (2026-07-19, Data Layer proxy/schema reconciliation):** `idle_speed_control_or_surge_degradation` is removed from this mapping following the documented-infeasibility decision in §2.3, reducing the executable `anomaly_type` enum from 6 to 5. `intake_air_temperature_sensor_or_heat_soak_fault` is renamed to `intake_air_temperature_sensor_fault`: the research-only heat-soak design 4-S4 is removed and produces no runtime row, while the executable IAT family now consists of stuck/no-response detection, cold-start plausibility support, and physical-range checks. The key-signal lists and Rationales for all five retained anomaly types are reconciled with the authoritative proxy definitions and the replacement `production_features.csv` schema. Legacy fields `coolant_slope`, `coolant_stability`, `maf_map_cohesion`, and `map_slope` are no longer production features. `tps` remains a delivered raw Model Layer channel and diagnostic context but is not a MAP trigger; accelerator-pedal demand is used instead. Frozen calibrated transforms are prediction-only in production and must never be fitted on user data. Model Layer implementation of the revised mappings remains pending.
>
> **Verdict forwarding for the two Data-Layer-scored types (2026-08-01, Model Layer, GL-368).** The gap closed on 2026-07-31 (§1.4) makes `proxy_decisions.csv` reachable from a live upload, so `intake_air_temperature_sensor_fault` and `map_load_signal_plausibility_fault` now carry the Data Layer's already-computed verdicts instead of the permanent `0.0` placeholder. This is **relaying, not scoring** — their §2.3 Status stays "Pending – Data Layer defined, Model Layer TBD" and the Model Layer still never computes their DTC decision logic. Master Field Table rows 50a–50e are the fields read. Nothing in §2.1/§2.5 changes shape: no new fields, and `validate_output.py`'s `anomaly_type` enum already admitted both values.
>
> **How the decision is supplied.** The detector takes an optional `--proxy-decisions <path>` argument, intended to receive the run summary's `proxy_decisions_path`. Without it, behaviour is exactly as before (both types score `0.0`). **Dashboard integration complete:** the upload path now reads both `production_features_path` and `proxy_decisions_path` from the Data Layer summary, validates the proxy file when present, and passes it to the Model Layer subprocess.
>
> **Grain and matching.** Decisions are one row per sub-check × evaluation unit (`unit_scope` ∈ `trip` | `engine_start_episode` | `segment_first_row`), while Model Layer output is per 512+96-row window. A decision is matched on `trip_id`, additionally requiring a `segment_id` match for `segment_first_row` rows; a null `segment_id` there means the evidence spanned several segments and is treated as trip-wide. Every window in a trip therefore inherits that trip's verdict. **Documented limitation:** a trip-level verdict cannot localise which window the evidence came from, so a window preceding the evidence interval carries the same score as one containing it.
>
> **`result_state` → `risk_score`.** Highest matching row wins: a `verdict` row with `dtc_emitted = true` → `0.9` (High); a `verdict` row `triggered` without `dtc_emitted` → `0.6`; a `support` or `arbitration_evidence` row `triggered` → `0.5` (these roles cannot independently emit a DTC); all applicable rows `pass` → `0.0`; only `not_evaluable`, or no applicable rows → `0.0`.
>
> **`confidence` → `prediction_confidence`.** When a forwarded type wins `anomaly_type`, `prediction_confidence` carries the Data Layer's confidence rather than the TTM residual spread, which had no part in the score: `high` → `0.9`, `provisional` → `0.6`, `low` → `0.35` (the Model Layer's existing confidence floor). `confidence_capped_low = true` forces `0.35` regardless of the stated label, and where several rows back one verdict the weakest is reported.
>
> **Provenance in `notes`.** A forwarded detection appends one note naming the anomaly type, the contributing `sub_check_id`s, the DTC code (`routed_dtc` where routing assigned one, else `dtc_candidate_label`), and the confidence label. `key_signals` follow this table's existing order for the two types, restricted to signals delivered in `production_features.csv`.
>
> **Arbitration.** `5-S2` rows are counted only when `routing_attribution` is absent or `MAP`: shared MAF/MAP residual evidence is attributed by independent MAP witnesses and never by residual sign (`calibration_registry.v1.json` `routing.maf_map_arbitration`, `residual_sign_attribution_forbidden: true`). `2-S2` rows routed to MAP are deliberately **not** forwarded — forwarding scope is defined by `proxy_id`, and routing changes the DTC code, not proxy ownership.
>
> **Validation note.** All 81 KIT trips are healthy driving, so every row in the current real delivery is `pass` or `not_evaluable` and no `triggered` verdict exists in the corpus. Forwarding was verified end-to-end against the real decision file (output identical to a no-flag run, as expected), and the triggered branches were verified against handcrafted decision rows.

| anomaly_type | key_signals (in order of importance) | Rationale | Status |
|---|---|---|---|
| `cooling_degradation` | `coolant_temp`, `ect_start`, `aat_start`, `maf_integral_180s`, `ect_rate_180s` | Four executable paths are defined: (1) slow warm-up when ECT fails to reach 79°C within the frozen ambient/starting-ECT budget, subject to valid start context, right-censor protection, and `maf_integral_180s > 2800.6549999999997 g`; (2) overheating when coolant temperature remains at least 105°C for 180 s or at least 110°C for 30 s in qualified post-warm-up operation; (3) a pending-only rising-temperature precursor when `ect_rate_180s ≥ 0.5°C/min` while coolant temperature is at least 100°C for 180 s; and (4) low-confidence cold-start ECT plausibility support when a qualified start follows a segment gap of at least 6 h and `\|ECT − AAT\| > 15°C` while IAT agrees with ambient. The precursor and cold-start support paths cannot independently emit a DTC. | Confirmed, **Detection method update** |
| `air_intake_maf_anomaly` | `maf`, `speed_density_maf_residual`, `rpm`, `map`, `intake_temp` | Two direct MAF paths are defined: (1) high-load under-read when the frozen speed-density MAF residual remains below −18.495 g/s for at least 10 consecutive valid seconds under high-confidence `post_warmup__high_load`; and (2) zero MAF while firing when `maf == 0.0` persists for at least 10 valid seconds with `rpm ≥ 500`. Residual evidence is shared with the MAP path and is attributed using independent MAP witnesses; residual sign alone never identifies the faulty sensor. The production pipeline applies a frozen speed-density transform and must never fit an expected-MAF baseline on user data. | Confirmed, **Detection method update** |
| `accelerator_pedal_sensor` | `accel_pedal_d`, `accel_pedal_e`, `pedal_mapping_residual`, `pedal_slope`, `accel_pedal_channel_delta`, `engine_on_flag` | Two executable P2138 paths are defined: (1) sustained channel-relation disagreement when, under quality-valid engine-on and low-motion conditions ( `abs(pedal_slope) ≤ 2.4 pp/s` ), `pedal_mapping_residual` remains below −1.8350 pp or above +1.3777 pp for at least 30 s; and (2) extreme unmasked disagreement when `accel_pedal_channel_delta ≥ 65 pp` for 2 consecutive valid seconds. The low-motion guard protects the residual path from the dataset's asynchronous 1 Hz channel sampling. | Confirmed, **Detection method update** |
| `intake_air_temperature_sensor_fault` | `intake_temp`, `intake_temp_stability`, `intake_ambient_delta`, `segment_gap_seconds`, `speed_std_120s`, `maf_std_120s`, `ambient_temp`, `coolant_temp` | Three executable paths are defined: (1) hard-stuck/no-response IAT when `intake_temp_stability ≤ 0.1°C` persists for at least 120 s despite material speed/MAF context change; (2) low-confidence cold-start support when a qualified start follows a segment gap of at least 6 h, ECT agrees with ambient within 15°C, and `\|IAT − AAT\| > 7°C`; and (3) physical-range detection outside −40…215°C. The cold-start path is support evidence only and cannot independently emit P0111. | Data Layer defined |
| `map_load_signal_plausibility_fault` | `map`, `pedal_slope`, `speed_density_maf_residual`, `map_range_60s`, `rpm_slope`, `rpm_std_120s`, `speed_std_120s`, `accel_pedal_mean_std_120s` | Three executable paths are defined: (1) repeated MAP no-response following qualified accelerator-pedal demand steps, triggered by at least 3 no-responses among the 4 most recent valid events; (2) shared steady-state MAP/MAF arbitration evidence when the speed-density MAF residual remains outside [−4.04, +16.71] g/s for at least 30 s under flat-pedal, stable-RPM post-warm-up driving; and (3) hard-stuck MAP when `map_range_60s == 0` persists for at least 120 s despite material RPM, speed, or pedal variation. `tps` is excluded as a trigger because it is unreliable in this dataset; pedal demand is the frozen substitute. | Data Layer defined |

### 2.5 Batch output envelope and risk-score history (Story 8)

> **Status: Integrated and stable.** Single-window invocations keep emitting the bare §2.1 object, while batch invocations emit the `{summary, windows}` envelope below. Story 8 is implemented: `estimated_cycles_to_failure` / `estimated_failure_probability` now carry real projected values when enough risk history exists, while remaining nullable for insufficient or non-rising histories.

The dashboard's final assembly runs the Model Layer over the full uploaded feature CSV in one click, so the detector supports a batch mode (`--batch`): one invocation sweeps every eligible segment (≥ 700 contiguous rows, §1.5) with non-overlapping 512+96-row windows that never cross segment boundaries. A batch run emits one envelope JSON:

```json
{
  "summary": { "...": "§2.1 interface JSON of the worst-risk window, unchanged" },
  "windows": [
    {
      "trip_id": "trip_0001",
      "segment_id": "trip_0001_seg_001",
      "window_id": "trip_0001_seg_001__w000",
      "...": "all §2.1 fields for this window"
    }
  ]
}
```

- `summary` — the highest-`risk_score` window's output (ties broken by file order), schema identical to §2.1: a parser built for the single-window shape reads `summary` unchanged.
- `windows` — every analysed window's §2.1 object plus three identity fields: `trip_id`, `segment_id`, and `window_id` (`<segment_id>__w<NNN>`, zero-based in file order — this is a Model Layer internal batch identifier, distinct from the Data Layer's proxy-evidence `window_id` (Master Field Table row 50, `<segment_id>__<proxy_name>__w<NNNNNN>`, §1.4).

**Risk-score history (Model Layer internal).** Every inference call — single or batch — appends `{trip_id, window_id, timestamp, risk_score}` per analysed window to `ttm-related/outputs/risk_history.csv` (path overridable via `--history-file`); re-runs skip records whose `(trip_id, window_id)` already exist, so the file stays duplicate-free. This ordered history is the input to the implemented Story 8 trend estimator that emits `estimated_cycles_to_failure`/`estimated_failure_probability` when the projection rules are satisfied; it is distinct from the Report Layer's §3.2 `risk_history` display field. Structure validation (ordered timestamps per trip, non-empty, risk_score in [0, 1]) is provided by `risk_history.py` for all consumers.

**Dashboard error contract.** Expected input/validation failures exit non-zero with a single `ERROR: <message>` line on stderr (no traceback), so the dashboard button can display the message to the user directly.

**Integration readiness (2026-07-20).** The schema v1 repoint of the fine-tuning split, fault-injection formulas, and synthetic evaluation sweep (GL-318/GL-320/GL-321) is complete and verified end-to-end against the real `production_features.csv` — the pipeline producing this JSON shape is stable, not just a design proposal. Report Layer can build and test its parser against §2.1 and §2.5 today.

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
| estimated_cycles_to_failure | int \| null | `4` | Confirmed — Story 8 projection, nullable |
| estimated_failure_probability | float (0–1) \| null | `1.0` | Confirmed — Story 8 projection, nullable |
| notes | array of strings | `[]` | Confirmed — added Story 3 |

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
| v0.5 | 2026-07-07 | Story 3 output hardening. (1) New Model Layer output field `notes` (array of strings, always present, empty when clean) carrying input-repair and detection-fallback messages — added to Master Field Table, Sections 2.1/2.2, and 3.1 pass-through. (2) `estimated_cycles_to_failure` / `estimated_failure_probability` are now emitted by the pipeline as `null` placeholders until Story 8 — consumers (incl. `validate_output.py`) must treat them as required but nullable. (3) `accelerator_pedal_sensor` detection implemented via the dual-channel disagreement rule from Section 2.4 (`accel_pedal_channel_delta` window mean, scored between 2pp and 10pp — thresholds tunable); when pedal channels are absent the score is forced to 0.0, `anomaly_type` falls back to the next-highest score, and a note is emitted. (4) Model Layer input validation added: required-column check plus two-tier range semantics — physically implausible values (outside sensor limits, e.g. coolant beyond [-40, 150]°C) are repaired to NaN + interpolation with a note, or rejected with a clear error above 5% of rows per column; values that are merely outside the healthy baseline pass through untouched so genuine anomalies remain detectable. |
| v0.6 | 2026-07-08 | Merged the Data Layer's returned interface (`INTERFACE-from data layer.md`, delivered 2026-07-08, forked from v0.4 and also labelled "v0.5" — renumbered here to v0.6). Section 1 replaced with the confirmed `feature_dataset.csv` field set: (1) new §1.1 key/time/operating-condition fields incl. `trip_id`/`segment_id` — **the v0.4 §1.4 trip/cycle-identifier request is satisfied** (chronological `trip_0001`–`trip_0081`), unblocking Story 8; (2) raw signals now include `intake_temp` and `ambient_temp`, all nullable; (3) 21 confirmed engineered features replace the provisional set — `coolant_rolling_avg`, `rpm_rolling_avg`, `acceleration`, `load_stress`, `rpm_variation` are dropped from the interface (Model Layer MVP computes internal equivalents until Story 7); (4) `coolant_slope` unit changed °C/min → °C/s (per segment) — Model Layer cooling thresholds rescale at the Story 7 switch; (5) all key_signals for the four pending anomaly types are now forwarded, resolving the Master Field Table "pending Data Layer fields" open item (footnote removed). Model Layer v0.5 Story 3 changes (`notes`, nullable estimation placeholders, pedal detection) retained — the Data Layer fork predates them and they remain in force. |
| v0.7 | 2026-07-11 | Model Layer input requirements made explicit after the Data Layer's window-table query. (1) New §1.5: 1-second uniform sampling and ≥700 contiguous rows per `segment_id` (512 context + 96 forecast, windows never cross segments) — both previously implicit, now Requested pending Data Layer confirmation; identity columns requirement confirmed. (2) §1.4 note added: the labeled proxy window table must carry per-window `trip_id`/`segment_id`/start–end `timestamp` for time-range alignment with the Model Layer's fixed windows; labels are used for healthy-training filtering and evaluation only, not TTM training; `failure_label` naming to be reconciled with the §2.3 enum. *Addendum 2026-07-12:* Data Layer delivered the row-level label master table and five duration window tables on branch `gl-171`; alignment columns present, `failure_label` naming matches the §2.3 enum exactly, §1.5 sampling/segment-length requirements verified on the delivered data (see §1.4/§1.5 notes). *Addendum 2 (2026-07-12):* Model Layer stories renumbered to the new execution order — the pipeline switch is now Story 5 (was 7), fine-tuning Story 6 (was 5), synthetic evaluation Story 7 (was 6); forward references in this document use the new numbers, while older changelog rows keep the numbering used at the time of writing. |
| v0.8 | 2026-07-13 | Story 5 pipeline switch (Model Layer). (1) Naming reconciliation: Group 1's delivered `feature_dataset.csv` column names compared against the §2.4 key_signals naming — they match the v0.6/v0.7 interface exactly, no renames needed; the pending types' key signals (`intake_temp`, `ambient_temp`, `intake_ambient_delta`, `map_slope`, `idle_flag`, `idle_rpm_stability`, `rpm_slope`) are all confirmed forwarded in the delivery (reconciled: none renamed, none deferred). (2) Pipeline switch done: the detector consumes `feature_dataset.csv` directly with segment-safe 512+96 windowing; internal feature computation (`add_derived_features` and the KIT raw-CSV loading path) removed; `coolant_slope` risk thresholds rescaled to °C/s per §1.3 (2.0–8.0 °C/min → 0.0333–0.1333 °C/s); the `maf_map_cohesion` trigger recalibrated on the delivered column's healthy distribution. (3) §1.5 sampling-interval and minimum-segment-rows requirements marked satisfied — verified directly on the delivered `feature_dataset.csv`. |
| v0.9 | 2026-07-14 | Anomaly enum reduced 7 → 6, recording the Data Layer's removal of `electronic_throttle_tracking_fault` (Layla, 2026-07-13: judgement needs a credible actual throttle-position observation, but `tps` in the delivered dataset is saturated with rate of change stuck at 0 for long stretches and no substitute observation is feasible; future proxy failures should avoid relying on `tps`). §2.3 and §2.4 rows removed; §2.2 enum count updated; the three remaining pending types' §2.4 Rationale cells reset to TBD pending the Data Layer's theory write-up (literature in the team Zotero; explanation doc to land on their branch). `tps` remains a TTM forecast channel and `pedal_throttle_gap` remains a delivered column. Recorded by the Model Layer (decision 2026-07-14, superseding the earlier plan to wait for the Data Layer's own INTERFACE update). Detector/validator code cleanup was already done in Story 5 (2026-07-13). |
| v1.0 | 2026-07-19 | Data Layer production-feature and proxy-contract replacement. (1) Replaced the planned Model handoff with the versioned `production_features.csv` contract: 4 sample keys + 16 delivered A-class context/raw fields + 24 ordered B-class production features + `schema_version` and `calibration_version` (46 columns total; production feature count remains 24). The existing `feature_dataset.csv` statements, trip/cycle-resolution note, proxy-label delivery notes, and Model Layer §1.5 requirements are retained as implementation/history records while scripts 00–41 and the real replacement file remain pending. (2) Preserved chronological `trip_id` assignment (one source CSV = one drive cycle), stable sample ordering, trip/segment boundaries, all five operating-condition fields, all ten cleaned raw channels including diagnostic-only `tps`, and all other Model/Report output fields and types. (3) Replaced the legacy 21 engineered-feature rows with the schema-v1 24-field B-class allowlist; calibrated transforms are prediction-only and must never fit user data. (4) Reduced the executable `anomaly_type` enum from 6 to 5 by retiring documented-infeasible `idle_speed_control_or_surge_degradation`; it produces no runtime row, cannot be represented as `not_evaluable`, and cannot emit P0506/P0507. The prior removal of `electronic_throttle_tracking_fault` remains recorded. (5) Renamed `intake_air_temperature_sensor_or_heat_soak_fault` to `intake_air_temperature_sensor_fault` because research-only heat-soak design 4-S4 is removed; reconciled all five §2.4 key-signal mappings and rationales against the authoritative proxy definitions and replacement schema, including updated cooling, MAF, pedal, IAT, and MAP paths. |
| v1.1 | 2026-07-20 | Model Layer (Story 8) added new §2.5: batch output envelope and risk-score history. `--batch` sweeps every eligible segment (≥ 700 rows, §1.5) with non-overlapping 512+96-row windows and emits a `{summary, windows}` envelope — `summary` keeps the §2.1 single-window schema (worst-risk window), `windows` adds `trip_id`/`segment_id`/`window_id` identity per analysed window (Model Layer's internal `window_id` format, distinct from the Data Layer's proxy-evidence `window_id`, Master Field Table row 50). Proposed to the Report Layer 2026-07-17; both the single-window and batch shapes are now stable and ready for Report Layer integration — only the Story 8 estimator (`estimated_cycles_to_failure`/`estimated_failure_probability`, still `null`) remains open. Risk-score history persistence (`{trip_id, window_id, timestamp, risk_score}` per window, deduped, structure-validated by `risk_history.py`) documented as the Story 8 estimator's input, distinct from the Report Layer's own §3.2 `risk_history` display field. Dashboard-friendly CLI error contract documented (single `ERROR:` line, no traceback). This addition follows the schema v1 repoint of the fine-tuning split, fault injection, and synthetic evaluation sweep (GL-318/GL-320/GL-321), verified end-to-end against real `production_features.csv`. |
| v1.2 | 2026-07-27 | Model Layer (Story 7, GL-366) verified Group 1's decision-level proxy delivery by running scripts `50_rule_state_builder.py`→`60_event_evidence_builder.py`→`61_duration_evidence_builder.py`→`70_proxy_decision_builder.py` end-to-end against a real run (full 80-trip KIT dataset, stages 00–41 then 50–70; no fixture/run directory previously existed for these stages). §1.4 updated with a dated note recording the confirmed `proxy_decisions.csv` 21-column schema and manifest shape, and confirming both currently-pending anomaly types (`intake_air_temperature_sensor_fault`, `map_load_signal_plausibility_fault`) produce real `dtc_candidate_label` values against real data — Group 1's DTC decision logic genuinely works, not just unit-tested against synthetic frames. This is a distinct, decision-level delivery from the four legacy row-level §1.4 fields (`failure_label`/`risk_class`/`condition_ratio`/`window_id`), not a replacement for them, and does **not** change either pending type's §2.3/§2.4 status — that scope decision (Model Layer never scores these two types) is unchanged. Confirms the still-open gap: `run_data_pipeline`/`run_data_pipeline_for_upload` does not call stages 50–70, so this delivery cannot reach a live end-to-end demo until Group 1/Group 3 wire it in (Data Layer's own README milestone M6). |
| v1.3 | 2026-07-31 | Data Layer wired the proxy engine into the public pipeline, closing the gap §1.4 recorded on 2026-07-27. (1) `run_data_pipeline` gained an `include_proxy` switch and `run_data_pipeline_for_upload` enables it by default, so scripts 50–70 run in the same run directory after stage 41 and `proxy_decisions.csv` is produced by a live single-CSV upload; the summary adds `proxy_decisions_path` (absolute), `proxy_stage_ids`, and the four proxy manifests. Batch and CLI runs are unchanged and stop at stage 41 unless `--include-proxy` is passed. Verified on real data: `intake_air_temperature_sensor_fault` → P0111 and `map_load_signal_plausibility_fault` → P0106. This does not change either pending type's §2.3/§2.4 status. (2) Master Field Table gained rows 50a–50e for the decision-level fields the Model Layer reads when forwarding those two types. (3) Upload rejection semantics recorded in §1.4: new code `no_usable_segment` (raised after the run when no contiguous segment reaches 700 rows, and unlike the pre-run codes it keeps the run directory), and `too_few_rows` now also enforces a ≥ 700 s recording duration because the corpus is sampled at 6–12 Hz. Pipeline-stage failures now surface as `DataPipelineError` with the original error chained. |
| v1.4 | 2026-08-01 | Model Layer (Story 7, GL-368) began forwarding the Data Layer's already-computed verdicts for the two anomaly types it does not score itself. (1) New §2.4 note defines the forwarding contract: the optional `--proxy-decisions` input, the trip-grain matching rule with its localisation limitation, the `result_state` → `risk_score` mapping (`dtc_emitted` → 0.9, triggered verdict → 0.6, triggered support/arbitration evidence → 0.5, otherwise 0.0), the `confidence` → `prediction_confidence` mapping (high/provisional/low → 0.9/0.6/0.35, with `confidence_capped_low` forcing 0.35), the `notes` provenance line, and the 5-S2 arbitration gate. No field is added or changed in §2.1/§2.5, and both types keep their §2.3 "Pending" status — this is relaying an already-computed verdict, not Model Layer scoring. (2) At v1.4 time the Dashboard still needed to pass the run summary's `proxy_decisions_path` through to the detector; the current Dashboard upload path now does this. (3) Corrected the 2026-07-27 §1.4 note, which misattributed P0116 and P0128 to the two pending types; both belong to `cooling_degradation` (1-S4 and 1-S1 respectively). |
| v1.5 | 2026-08-01 | Model Layer (Story 8, GL-289) completed the failure estimator, so rows 57–58 stop being `null` placeholders and carry real values. (1) `estimated_cycles_to_failure` is now the projected number of chronological driving cycles until the trip-level mean risk reaches the Model Layer High-risk line (0.90 in `config/risk_level_calibration.v1.json`): detector-window risk scores are aggregated into per-trip means, a least-squares line `r_i = a + b·i` is fitted across chronological trips, and the crossing point is rounded up. It is emitted as `null` when fewer than five trips of history exist, when the trend is flat or falling, or when the projection exceeds 50 cycles — it is **not** a physical remaining-useful-life estimate. (2) `estimated_failure_probability` is the normal-error-model probability that the same linear projection crosses the High line within a fixed 10-cycle horizon; `null` for insufficient history, `0.0` for flat healthy history. It is **not** an empirically calibrated probability of mechanical failure — the KIT dataset supplies no labelled failure times, so nothing in it is fitted to observed failures. (3) Consumer impact: both fields remain typed `int \| null` and `float (0–1) \| null` with no shape change, but the Report Layer and Dashboard will now receive non-null values where earlier fixtures exercised nullable-only behaviour. (4) The committed contract sample `model_layer/ttm-related/outputs/kit_residual_sample.json` is refreshed accordingly (`4` cycles, `1.0` probability) and carries two `notes` entries stating it comes from a deliberately-rising synthetic history and is not a real-vehicle lifetime claim; method and limitations are written up in `model_layer/ttm-related/outputs/evaluation_note.md`. |
