# Production Feature and Proxy Pipeline Schema

**Status:** implementation contract  
**Date:** 2026-07-19  
**Authoritative rule sources:** [`../proxy_failure/proxy_failure_definition.md`](../proxy_failure/proxy_failure_definition.md) and [`../proxy_failure/proxy_support.md`](../proxy_failure/proxy_support.md)

## 1. Purpose

This document defines the field ownership, table grains, and script boundaries for the production pipeline:

```text
formatted input dataset
  -> cleaning pipeline
  -> operating-condition analysis
  -> production feature generation
  -> proxy evidence and decision
```

It replaces the former single-table assumption. A field is classified by its actual consumer and grain, not merely because it is derived from another field.

The schema contains four field classes:

1. **Canonical and operating-condition fields** — keys, cleaned raw signals, data-quality flags, and operating-condition context passed into the feature/proxy pipeline. The versioned model handoff delivers A1 sample keys, `dt_seconds`, the five A4 operating-condition fields, and the ten cleaned A2 raw signals; A3 quality-detail fields remain internal unless separately contracted.
2. **Production features delivered to the model/rule group** — the versioned B-class set of reusable sample/context/window features delivered under the production handoff; schema v1 currently contains 24 B-class fields. A retained model-context field need not have a current proxy-verdict consumer.
3. **Data-team internal fields and calibration artifacts** — hidden calculation intermediates, offline baselines, frozen thresholds, and research-only diagnostics that are not delivered as model features.
4. **Proxy/integration evidence and decision fields** — masks, opportunities, events, run lengths, margins, typed result states, and DTC routing generated after the production-feature layer.

The production path must never fit baselines or thresholds on a user-uploaded dataset. Online execution loads a previously frozen calibration registry. Recalibration is a separate offline/admin workflow.

## 2. Structure

### 2.1 Field ownership tree

```text
Pipeline fields
├── A. Upstream canonical and operating-condition fields
│   ├── A1. Sample keys
│   │   ├── timestamp
│   │   ├── trip_id
│   │   ├── segment_id
│   │   ├── row_in_segment
│   │   └── dt_seconds
│   ├── A2. Cleaned raw signals
│   │   ├── coolant_temp
│   │   ├── ambient_temp
│   │   ├── intake_temp
│   │   ├── maf
│   │   ├── map
│   │   ├── rpm
│   │   ├── speed
│   │   ├── tps
│   │   ├── accel_pedal_d
│   │   └── accel_pedal_e
│   ├── A3. Data-quality fields
│   │   ├── per-signal missing / imputed / suspicious flags
│   │   ├── per-signal hard-invalid-source flags
│   │   └── sample-level cleaning/audit status
│   └── A4. Operating-condition context
│       ├── thermal_state
│       ├── child_state
│       ├── operating_state
│       ├── condition_confidence
│       └── condition_quality_flags
│
├── B. Production features delivered to the model layer (24 in schema v1)
│   ├── B1. Sample-level features (10)
│   │   ├── B1a. Deterministic/atomic (8)
│   │   │   ├── segment_gap_seconds
│   │   │   ├── engine_on_flag
│   │   │   ├── coolant_ambient_delta
│   │   │   ├── intake_ambient_delta
│   │   │   ├── accel_pedal_mean
│   │   │   ├── accel_pedal_channel_delta
│   │   │   ├── pedal_slope
│   │   │   └── rpm_slope
│   │   └── B1b. Frozen-calibration transforms (2)
│   │       ├── speed_density_maf_residual
│   │       └── pedal_mapping_residual
│   ├── B2. Engine-start context (6)
│   │   ├── engine_start_observed
│   │   ├── engine_start_episode_id
│   │   ├── elapsed_since_engine_start
│   │   ├── ect_start
│   │   ├── aat_start
│   │   └── iat_start
│   └── B3. Window-level features (8)
│       ├── maf_integral_180s
│       ├── ect_rate_180s
│       ├── intake_temp_stability
│       ├── speed_std_120s
│       ├── maf_std_120s
│       ├── rpm_std_120s
│       ├── accel_pedal_mean_std_120s
│       └── map_range_60s
│
├── C. Data layer internal fields and calibration artifacts
│   ├── C1. Hidden online calculation intermediates
│   │   ├── map_derived_air_load_raw (input to the frozen speed-density transform)
│   │   ├── expected_maf
│   │   └── pedal_e_expected
│   ├── C2. Frozen calibration registry (JSON, not feature columns)
│   │   ├── speed-density coefficients, intercept, input domains, and clipping bounds
│   │   ├── pedal D/E mapping coefficients and residual bands
│   │   ├── 4-S1 context-gate thresholds with trip-equal q50 definition, cohort, and weighting provenance
│   │   ├── cooling target, warm-up budgets, and heat-input guard
│   │   ├── MAF residual threshold and duration
│   │   ├── MAP pedal-step and response thresholds
│   │   ├── steady-state residual bands
│   │   ├── IAT/MAP context thresholds
│   │   ├── persistence and m-of-n constants
│   │   └── calibration version, cohort, provenance, and validity domain
│   ├── C3. Research-only / non-executed diagnostics
│   │   ├── maf_derived_air_load_raw
│   │   ├── maf_air_load_z
│   │   ├── map_air_load_z
│   │   ├── maf_map_cohesion
│   │   ├── delta_std_10s
│   │   ├── 60-s MAF rolling range
│   │   ├── coolant_slope
│   │   ├── coolant_stability
│   │   ├── intake_temp_slope
│   │   ├── map_slope
│   │   ├── map_stability
│   │   ├── accel_pedal_channel_ratio
│   │   ├── idle_flag
│   │   ├── idle_rpm_stability
│   │   ├── cold_soak_candidate_flag
│   │   └── post_high_load_iat_heat_soak_observation
│   └── C4. Internal analysis outputs
│       ├── operating-condition counts and signal summaries
│       ├── candidate grids and sensitivity tables
│       ├── LOTO / Bootstrap outputs
│       ├── calibration audit tables
│       └── research diagnostic tables
│
└── D. Proxy/integration evidence and decision fields
    ├── D1. Rule-state and eligibility fields
    │   ├── per-sub-check quality_valid / eligible / context_opportunity
    │   ├── steady_state_mask
    │   ├── pedal_lowmotion_mask
    │   ├── material_context flags
    │   ├── time_to_target_79c
    │   ├── time_to_target_79c_is_right_censored
    │   └── time_to_target_79c_censor_time_s
    ├── D2. Event evidence
    │   ├── pedal_step_event_id
    │   ├── pedal_step_magnitude_bin
    │   ├── step_response
    │   ├── no_response_flag
    │   └── recent_valid_event_count / recent_no_response_count
    ├── D3. Duration evidence
    │   ├── ect_exceedance_run_s
    │   ├── residual_band_run_s
    │   ├── zero_maf_run_s
    │   ├── channel_delta_extreme_run_s
    │   └── per-sub-check duration_episode_id
    └── D4. Decision outputs
        ├── proxy_id
        ├── sub_check_id
        ├── direction
        ├── decision_role: verdict / pending_precursor / support / arbitration_evidence
        ├── result_state: pass / triggered / not_evaluable / pending
        ├── decision_reason
        ├── decision_margin
        ├── dtc_candidate_label
        ├── dtc_emitted
        ├── attribution / routing result
        ├── confidence tier
        └── calibration_version
```

### 2.2 Grain and key contract

Fields with different grains must not be forced into a single equal-row-count CSV.

| Table grain | Required key | Content |
|---|---|---|
| Sample | `timestamp + trip_id + segment_id + row_in_segment` | Canonical signals, operating context, and the versioned production-feature set (24 fields in schema v1) |
| Engine-start episode | `trip_id + engine_start_episode_id` | Start time, start values, episode eligibility, and episode-level evidence |
| Pedal-step event | `trip_id + pedal_step_event_id` | Step detection, response, no-response label, and rolling event evidence |
| Duration episode | `proxy_id + sub_check_id + trip_id + duration_episode_id` | Same-side or threshold run evidence and duration margins |
| Proxy decision | `proxy_id + sub_check_id + trip_id + decision_id` | Typed decision role and result state, direction, reason, DTC permission/emission, routing, margin, and provenance |

#### Delivered A-class model context

`production_features.csv` retains the following 16 A-class context/raw columns after the four sample keys and before the 24 B-class production features. These columns are delivered to preserve the confirmed Model Layer input contract, but they are not counted in `feature_count`. Detailed A3 cleaning/audit flags and internal operating-condition calculations remain outside this handoff.

| Position after keys | Field | Class | Type | Unit | Nullable | Owning upstream output |
|---:|---|---|---|---|---|---|
| 1 | `dt_seconds` | A1 | float | s | No | `operating_condition_enriched.csv` |
| 2 | `thermal_state` | A4 | string | categorical | No | `operating_condition_enriched.csv` |
| 3 | `child_state` | A4 | string | categorical | No | `operating_condition_enriched.csv` |
| 4 | `operating_state` | A4 | string | categorical | No | `operating_condition_enriched.csv` |
| 5 | `condition_confidence` | A4 | string | categorical | No | `operating_condition_enriched.csv` |
| 6 | `condition_quality_flags` | A4 | string | categorical flags | No | `operating_condition_enriched.csv` |
| 7 | `coolant_temp` | A2 | float | °C | Yes | cleaned canonical data |
| 8 | `map` | A2 | float | kPa | Yes | cleaned canonical data |
| 9 | `rpm` | A2 | float | rpm | Yes | cleaned canonical data |
| 10 | `speed` | A2 | float | km/h | Yes | cleaned canonical data |
| 11 | `intake_temp` | A2 | float | °C | Yes | cleaned canonical data |
| 12 | `maf` | A2 | float | g/s | Yes | cleaned canonical data |
| 13 | `tps` | A2 | float | % | Yes | cleaned canonical data |
| 14 | `ambient_temp` | A2 | float | °C | Yes | cleaned canonical data |
| 15 | `accel_pedal_d` | A2 | float | % | Yes | cleaned canonical data |
| 16 | `accel_pedal_e` | A2 | float | % | Yes | cleaned canonical data |

`tps` is retained as a cleaned raw Model Layer channel for backward compatibility. Removal of the non-executable electronic-throttle proxy does not remove this raw signal from the model handoff or authorize its use in a proxy verdict. `dt_seconds` retains the upstream operating-condition implementation contract: it is computed within `segment_id` and emitted as a non-null float in seconds for the canonical 1 Hz table.

#### Trip/cycle identity and sample-row order

One discovered raw KIT CSV file is exactly one trip/drive cycle. Cleaning must never merge two source files into one `trip_id`, even when their timestamps are adjacent. Before assigning identifiers, source files are ordered by the tuple `(trip_start_timestamp_utc, source_filename)`, where `trip_start_timestamp_utc` is the minimum valid source timestamp after combining the filename date with the in-file time, applying the configured source timezone, and converting to UTC. The source filename is the deterministic tie-breaker.

`trip_id` is the 1-based ordinal in that order, formatted as `trip_<zero-padded ordinal>` with a minimum width of four digits (`trip_0001`, `trip_0002`, ...). The mapping is deterministic for a fixed source-dataset identity and must not depend on filesystem discovery order. Adding, removing, or replacing a raw source file creates a different source-dataset identity and may renumber subsequent trips.

Every sample-grain production output, including `production_features.csv`, must be stable-sorted by `(timestamp, trip_id, segment_id, row_in_segment)` after timestamps have been normalized to UTC. This is the authoritative global row order: timestamp is the primary chronological key and the remaining sample keys are deterministic tie-breakers. Within each `(trip_id, segment_id)`, `row_in_segment` is 1-based and strictly increasing, timestamps are strictly increasing at the canonical 1 Hz cadence, and downstream windows must never cross a trip or segment boundary. A one-to-one join must explicitly restore this order rather than relying on incidental join order.

`engine_start_episode_id`, although delivered with sample context, is an episode foreign key into `engine_start_episodes.csv`. The episode table is the authoritative storage for the start timestamp and `ect_start` / `aat_start` / `iat_start`. The sample-grain context maps those three values by foreign key to every row inside the episode; it must never recalculate them row by row. The episode ID and mapped start values are null outside an observed episode.

An observed engine start is an RPM transition from `<50` to `>=50` within one valid continuity block. The crossing row is the episode start and the only row where `engine_start_observed = true`. An episode continues while RPM remains valid and `>=50`; the first later valid RPM `<50`, a continuity break, or an invalid/missing RPM terminates it. A segment may contain multiple episodes, but a transition must never cross a segment or continuity boundary. `elapsed_since_engine_start` is zero at the crossing row, increases from timestamps within the episode, and is null outside it.

The cold-soak plausibility checks 1-S4 and 4-S2 use ECT/IAT/AAT at the canonical segment first row, followed by a later observed start in that same segment and continuity block. They do not consume the crossing-row `ect_start` / `aat_start` / `iat_start` fields.

For 1-S1, `time_to_target_79c` records elapsed seconds to the first observed ECT ≥79°C and is null when the target is not observed. In that case `time_to_target_79c_is_right_censored = true`, and `time_to_target_79c_censor_time_s` records the available continuous follow-up duration from the observed engine start. Script 70 compares the censor time with the frozen warm-up budget so that an episode truncated before budget expiry cannot be mistaken for a failure to reach target.

### 2.3 Production-feature definitions

#### Sample-level deterministic/atomic

| Feature | Definition summary | Primary consumers |
|---|---|---|
| `segment_gap_seconds` | Time between the current segment start and the previous observable segment end; populated only on the segment first row and unknown when predecessor context is unavailable | 1-S4, 4-S2 |
| `engine_on_flag` | `rpm >= 50`; missing RPM remains unknown | General enable logic |
| `coolant_ambient_delta` | `coolant_temp - ambient_temp` | 1-S4 |
| `intake_ambient_delta` | `intake_temp - ambient_temp` | 4-S2 |
| `accel_pedal_mean` | `(accel_pedal_d + accel_pedal_e) / 2`; null unless both source channels are present and quality-valid | 5-S3 context, shared pedal calculations |
| `accel_pedal_channel_delta` | `abs(accel_pedal_d - accel_pedal_e)`; null unless both source channels are present and quality-valid | 3-S1b |
| `pedal_slope` | Within-continuity-block first difference of `accel_pedal_mean` divided by positive valid elapsed time; null across a boundary or when either endpoint is invalid | 3-S1a, 5-S1, 5-S2 |
| `rpm_slope` | Within-continuity-block first difference of RPM divided by positive valid elapsed time; null across a boundary or when either endpoint is invalid | 5-S2 |

#### Sample-level frozen-calibration transforms

| Feature | Definition summary | Primary consumers |
|---|---|---|
| `speed_density_maf_residual` | Observed MAF minus expected MAF from the frozen speed-density calibration; uploaded data must not refit the model | 2-S2, 5-S2 and MAF/MAP routing |
| `pedal_mapping_residual` | `accel_pedal_e - (a * accel_pedal_d + b)` using frozen `a` and `b` | 3-S1a |

#### Engine-start context

| Feature | Definition summary | Primary consumers |
|---|---|---|
| `engine_start_observed` | True only on an observed within-continuity-block RPM `<50` to `>=50` crossing row | 1-S1 and episode construction; 1-S4/4-S2 require the event but use segment-first-row sensor values |
| `engine_start_episode_id` | Stable identifier assigned per observed start episode; not interchangeable with `segment_id` | All episode-scoped calculations |
| `elapsed_since_engine_start` | Seconds since the episode's observed crossing row; null outside the episode | Warm-up and episode-window logic |
| `ect_start` | ECT at the observed crossing row, stored once in the episode table and mapped by episode foreign key | 1-S1 |
| `aat_start` | Ambient temperature at the observed crossing row, stored once in the episode table and mapped by episode foreign key | 1-S1 |
| `iat_start` | IAT at the observed crossing row, stored once in the episode table and mapped by episode foreign key | Retained engine-start/model context; no current proxy-verdict consumer |

#### Window-level

| Feature | Definition summary | Primary consumers |
|---|---|---|
| `maf_integral_180s` | Trapezoidal integral over 181 consecutive valid 1 Hz endpoints from `t−180 s` through `t` (180 one-second intervals), within one continuity block and engine-start episode; any missing/invalid endpoint makes the value null | 1-S1 heat-input guard |
| `ect_rate_180s` | `(ECT[t] - ECT[t-180 s]) / 3`, °C/min, requiring 181 consecutive valid 1 Hz endpoints spanning 180 s within one continuity block | 1-S3 pending precursor |
| `intake_temp_stability` | Sample standard deviation over 60 consecutive valid 1 Hz IAT samples; incomplete or quality-invalid windows are null | 4-S1 |
| `speed_std_120s` | Sample standard deviation over 120 consecutive valid 1 Hz speed samples | 4-S1, 5-S3 |
| `maf_std_120s` | Sample standard deviation over 120 consecutive valid 1 Hz MAF samples | 4-S1 |
| `rpm_std_120s` | Sample standard deviation over 120 consecutive valid 1 Hz RPM samples | 5-S3 |
| `accel_pedal_mean_std_120s` | Sample standard deviation over 120 consecutive valid 1 Hz pedal-mean samples | 5-S3 |
| `map_range_60s` | Rolling maximum minus minimum over 60 consecutive valid 1 Hz MAP samples | 5-S3 |

All rolling windows must remain inside one valid continuity block. Segment boundary, non-consecutive sample time, missing source data, imputation, or a suspicious source sample breaks the window unless an individual rule explicitly states otherwise. Window lengths expressed as elapsed spans include both endpoints: an `N`-second endpoint-to-endpoint span at 1 Hz requires `N+1` endpoints; a window defined as `N` samples requires exactly `N` endpoints.

## 3. Process

### 3.1 Script inventory

The data-layer scope contains **12 functional scripts**: ten online scripts (00–70) and two offline/admin scripts (90–91). Cleaning and operating-condition analysis remain upstream pipelines. The project-wide orchestrator is owned by the integration group and is not implemented in this data-layer work package.

All scripts that depend on temporal continuity must import the same non-executable shared library: `data_layer/pipeline_data/continuity.py`. It owns continuity-block construction, consecutive-sample checks, strict rolling-window admission, and invalid-sample break semantics. Scripts 20, 30, 50, 60, and 61 must not reimplement these rules locally. The shared contract is verified by `data_layer/tests/pipeline_data_test/test_continuity_contract.py`; this library and its test do not change the functional-script count.

#### Online production scripts

| Order | Script | Input | Responsibility | Output |
|---:|---|---|---|---|
| 00 | `00_input_contract_validator.py` | Cleaned CSV + operating-condition enriched CSV | Validate schema, units, 1 Hz continuity metadata, unique sample keys, required raw signals, quality fields, operating-context fields, and the frozen trip/cycle identity and sample-row-order contract. It must not impute or refit. | `input_contract_manifest.json`; validated input references |
| 10 | `10_atomic_feature_builder.py` | Validated canonical/condition sample data | Generate the 8 deterministic B1a features. | `atomic_features.csv`, sample grain |
| 20 | `20_engine_start_context_builder.py` | Validated canonical data + atomic features | Detect within-continuity-block RPM `<50` to `>=50` transitions, assign episode IDs, store authoritative start values once per episode, and map the 6 B2 context fields to sample rows by episode foreign key. | `engine_start_context.csv`, sample grain; `engine_start_episodes.csv`, episode grain |
| 30 | `30_window_feature_builder.py` | Canonical data + atomic features + engine-start context | Generate the 8 B3 rolling/episode-window features under the shared strict continuity and quality contract. | `window_features.csv`, sample grain |
| 40 | `40_calibrated_feature_builder.py` | Canonical data + atomic features + frozen `calibration_registry.json` | Apply, but never fit, the frozen speed-density and pedal-mapping transforms; keep hidden intermediates internal. The implementation exposes no fit path in production mode. | `calibrated_features.csv`, sample grain, containing the 2 B1b features |
| 41 | `41_production_feature_assembler.py` | Validated canonical/condition data + atomic + engine-start context + window + calibrated feature tables | Perform one-to-one sample-key joins, carry forward the ordered 16-field A-class context/raw allowlist, explicitly restore and validate the frozen global sample-row order, validate the ordered 24-field B-class feature allowlist from the versioned schema manifest, attach schema/calibration versions, and reject missing or unexpected output columns. The output contains 46 columns in schema v1; validation must not rely on counts alone. | `production_features.csv`; `production_feature_manifest.json` |
| 50 | `50_rule_state_builder.py` | Canonical/condition data + production features + frozen registry | Build sub-check eligibility, quality-valid, context-opportunity, masks, direct physical-range evidence, and engine-start decision state. Materialize every canonical/feature value required by script 70, including 1-S1 target time, right-censor flag/time, expiry ECT/heat evidence, and 4-S3 IAT range evidence. | `rule_state.csv`, sample grain; `engine_start_rule_state.csv`, episode grain; explicit evidence-schema manifest |
| 60 | `60_event_evidence_builder.py` | Rule state + canonical signals + production features + frozen registry | Detect and deduplicate pedal-step events, calculate response/no-response evidence, and maintain recent valid-event counts. | `pedal_step_events.csv`, event grain |
| 61 | `61_duration_evidence_builder.py` | Rule state + canonical signals + production features + frozen registry | Build threshold/same-side run episodes and duration evidence for executable sub-checks only. | `duration_episodes.csv`, duration-episode grain |
| 70 | `70_proxy_decision_builder.py` | Materialized rule state + engine-start state + event evidence + duration evidence + frozen registry | Apply final executable rules, support/pending semantics, confidence modifiers, margins, DTC attribution, and MAF/MAP routing. Script 70 must not read canonical or production-feature tables directly; any required fact must arrive through a versioned evidence schema from scripts 50/60/61. | `proxy_decisions.csv`, decision grain; optional proxy-level summary |

#### Offline/admin scripts

| Order | Script | Input | Responsibility | Output |
|---:|---|---|---|---|
| 90 | `90_calibration_registry_builder.py` | Approved healthy calibration cohort + binding pre-registrations/output artifacts + already frozen registry | Reproduce approved calibrations and validate cohort, weighting, parameters, bounds, provenance, and checksums against the manually reviewed versioned registry. It must stop on any mismatch and must never create or overwrite the authoritative registry. It is never called by the user-data production path. | Reproduction audit and comparison manifest only |
| 91 | `91_research_diagnostics_builder.py` | Approved research dataset + optional registry | Generate only explicitly approved, non-executed research diagnostics, candidate grids, and sensitivity/LOTO/Bootstrap material. Disabled by default. | `research_diagnostics/` artifacts only |

The integration group may later add a project-level orchestrator after every stage has an independent contract test. That orchestrator must call the public data-layer entry points, enforce their manifests, and must never invoke scripts 90 or 91 in normal user-data production mode.

### 3.2 Dependency flow

```text
formatted dataset
  -> cleaning pipeline
  -> operating-condition analysis
  -> 00 input contract validation
       ├──> 10 atomic features
       │      └──> 20 engine-start context
       │               └──> 30 window features
       └────────────────────> 40 calibrated features + frozen registry
                                 |
       10 + 20 + 30 + 40 --------> 41 production feature assembly
                                              |
canonical + condition + production features -> 50 rule state
                                              ├──> 60 event evidence
                                              └──> 61 duration evidence
50 + 60 + 61 + frozen registry -------------> 70 proxy decisions
```

Offline calibration is deliberately separate:

```text
approved census outputs + pre-registrations + provenance
  -> manual review and versioned calibration_registry.json freeze
  -> online scripts load the frozen version read-only

approved healthy cohort + frozen registry
  -> 90 calibration reproduction/audit
  -> stop on any mismatch; never overwrite the frozen registry
```

Research diagnostics are also separate:

```text
approved research run with research_diagnostics=true
  -> 91 research diagnostics builder
  -> audit artifacts only
  -> never merged into production_features.csv
```

### 3.3 Stage invariants

1. The production feature assembler must match the ordered versioned manifest: four sample keys, 16 delivered A-class context/raw fields, 24 B-class production features, and two explicit schema/calibration provenance fields. Schema v1 therefore contains 46 CSV columns while `feature_count` remains 24. Correctness is determined by field identity, order, type, unit, nullability, and version—not by either count alone.
2. Delivered A-class fields remain model context/raw inputs and are not counted as derived production features. Other upstream A-class quality-detail fields may be consumed by evidence builders 50, 60, and 61 but are not delivered unless separately contracted. Script 70 consumes only versioned materialized evidence and must not read canonical or production-feature tables directly.
3. C-class fields must not appear in `production_features.csv`.
4. D-class evidence and decisions must not appear in `production_features.csv`.
5. Fitting, quantile selection, candidate search, LOTO, and Bootstrap are forbidden in scripts 00–70. Any online script that consumes calibrated parameters must load them from the frozen registry read-only; scripts without calibrated parameters must not invent a calibration dependency.
6. A missing required table, column, key, unit, or incompatible schema is a contract failure and aborts the stage. Within a valid input contract, sample-level missing, quality-invalid, or out-of-domain inputs produce null feature values or `not_evaluable` with an explicit reason according to the owning layer; they must never be silently imputed into a result.
7. Every output manifest records `schema_version`, source dataset identity, script version, and creation time. It records `calibration_version` when calibration applies and the explicit value `not_applicable` otherwise.
8. Scripts 50–70 implement the following current-cycle checks with explicit output semantics:
   - Every runtime row uses `decision_role`, `result_state`, `decision_reason`, `dtc_candidate_label`, and `dtc_emitted`. A candidate label never by itself authorizes DTC emission.
   - Standard three-state executable checks use `decision_role = verdict`: `1-S1`, `1-S2`, `2-S2`, `2-S3b`, `3-S1a`, `3-S1b`, `4-S1`, `4-S3`, `5-S1`, and `5-S3`.
   - `1-S3` uses `decision_role = pending_precursor` and may output `pending`, `pass`, or `not_evaluable`; it must never output `triggered` or independently emit a DTC. Its input `ect_rate_180s` is a B3 production feature.
   - `1-S4` uses `decision_role = support`; it is executable low-confidence evidence and a sensor-trust guard for 1-S1, but `dtc_emitted` must always be false for P0116.
   - `4-S2` uses `decision_role = support`; `dtc_emitted` must always be false for P0111. Once activated at a qualified observed start, its low-confidence cap applies prospectively from that start through the end of the current continuity segment, never retroactively. Any later episode in the same segment cannot clear it; a continuity break clears it. It caps only IAT-dependent residual paths `2-S2` and `5-S2`, not `2-S3b`, `5-S1`, or `5-S3`.
   - `5-S2` uses `decision_role = arbitration_evidence`; it must not independently emit a DTC.
9. Research-only, removed, or documented-infeasible sub-checks (`2-S1`, `2-S3a`, `3-S2`, `3-S3`, `4-S4`, and failure 6) are excluded from scripts 50–70 and produce no runtime decision rows. `not_evaluable` is reserved for an executed check that cannot be evaluated on a particular input; it must not represent a non-executed design.
10. Before a versioned feature manifest or proxy contract is released or accepted by production scripts, the feature manifest, calibration-registry references, proxy execution contract, and evidence/decision schema must pass a cross-contract lint. The lint validates field identity and order, declared consumers and inputs, execution status, `decision_role`, DTC-emission permissions, and registry-parameter references.
11. For a fixed source-dataset identity, raw-file discovery order must not affect `trip_id` assignment or sample-row order. Contract tests must shuffle input-file discovery order and one-to-one join input order, then prove identical `trip_id` mappings and identical ordered sample keys in `production_features.csv`. They must also prove that source-file boundaries remain trip boundaries and that no model window crosses a trip or segment boundary.

### 3.4 Planned implementation order

1. Reconcile and freeze field names, units, quality requirements, keys, lifecycle semantics, and rule inputs across this schema, the authoritative proxy definition, and the research-support audit.
2. Create and validate the ordered versioned feature manifest for the four keys, 16 delivered A-class fields, 24 B-class schema-v1 features, and two provenance fields.
3. Manually assemble, review, and freeze the versioned calibration registry and its manifest from approved census outputs and provenance. Record exact operators and raw numeric values, including the 1-S1 heat-input guard `> 2800.6549999999997 g`, and preserve cohort, weighting, pre-registration/output paths, and checksums. The registry must exist before script 40 is implemented.
4. Implement shared `paths.py` and manifest utilities, then their contract tests.
5. Implement shared continuity/quality admission and boundary tests before temporal feature scripts.
6. Implement and test scripts 00, 10, 20, 30, 40, and 41. For script 40, migrate only registry-driven prediction logic; prove that user data cannot invoke fitting and that outputs reproduce frozen coefficients, domains, and clipping bounds.
7. Validate the versioned 46-column production-feature handoff, including sample-key one-to-one integrity, the 16 delivered A-class fields, the 24-field B-class feature count, episode foreign-key mapping, field order, dtype, unit, null semantics, schema version, and calibration provenance.
8. Implement scripts 50, 60, 61, and 70 against the authoritative proxy definitions and the versioned evidence/decision contracts.
9. Implement script 90 only as a reproduction/audit path after the manual registry freeze. It must compare against the frozen registry, stop on mismatch, and never create or overwrite the authoritative registry.
10. Put only explicitly approved research diagnostics behind script 91 and keep them disabled by default; legacy comparison is not a production contract or required golden artifact.
11. Hand the independently tested public stage entry points and manifests to the integration group; any project-wide orchestrator is integration-owned.
12. Remove obsolete feature scripts and generated artifacts only after the replacement pipeline reproduces the frozen rule inputs and passes end-to-end validation.
