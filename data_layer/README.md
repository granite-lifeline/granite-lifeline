# Data Layer

**Owner:** Data Team
**Status:** Active Development
**Last Updated:** 2026-07-18

---

## Overview

The Data Layer is the first stage in the Granite Lifeline predictive maintenance pipeline. It transforms raw OBD-II CSV data from the KIT dataset into cleaned, enriched, feature-engineered tabular data and proxy-fault training labels consumed by the Model Layer and downstream evaluation.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Core Responsibilities

1. **Data Cleaning & Quality Auditing**: Timestamp alignment, 1 Hz resampling, missing-value treatment, suspicious-value flagging, and per-segment quality reporting
2. **Operating Condition Classification**: Hierarchical state machine assigning `thermal_state` (engine_off/warmup/post_warmup/unknown) and `child_state` (idle/steady_driving/acceleration/deceleration/high_load/inactive_engine_off/unknown) per row
3. **Feature Engineering**: 21 derived features across three stages — deterministic (rolling statistics, temperature deltas, slopes), event-based (pedal-to-throttle delay), and baseline-model cross-estimates (MAF/MAP cohesion, speed-density residuals, pedal-throttle gap)
4. **Baseline Design**: Five-step process defining normal-operating-condition reference ranges for every feature under every physically meaningful operating state
5. **Proxy Fault Design**: 5 proxy failure definitions with physical rationale, condition-stratified detection thresholds, and training labels (row-level flags + duration-window voting)

There are no labelled fault data in the KIT dataset — all 81 trips are healthy driving. Proxy faults are therefore defined from physical principles, calibrated against normal-data statistics, and validated through iterative tightening to ensure zero false positives on normal data.

### Proxy Failure Types (5)

- **cooling_degradation**: Sustained overheating after warm-up, coolant temperature rising without plateau, abnormally slow warm-up, or coolant temperature implausible relative to ambient after cold soak
- **air_intake_maf_anomaly**: MAF/MAP air-load disagreement ? MAF sensor drift, contamination, or response delay in the intake measurement chain
- **accelerator_pedal_sensor**: D/E channel disagreement ? drift, desync, or redundancy-monitoring failure in the dual-channel pedal position sensors
- **intake_air_temperature_sensor_fault**: IAT signal fails rationality check against ambient temperature after cold soak, or remains unresponsive despite sustained airflow
- **map_load_signal_plausibility_fault**: MAP unresponsive to pedal demand, steady-state MAP/MAF cross-inconsistency, or stuck MAP signal

---

## Current Implementation Status

### [COMPLETED]

| Component                               | Ticket                | Description                                                                                                                                            |
| --------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Data Cleaning Pipeline                  | GL-80                 | Raw CSV cleaned 1 Hz dataset with config-based validation, 0.1% missing rate after alignment                                                          |
| Upload Cleaned Data                     | GL-81                 | Version-controlled cleaned CSV delivery                                                                                                                |
| Data Availability & Quality Statistics  | GL-82                 | Per-segment quality report: missing values by column, suspicious-value counts, segment summary                                                         |
| Operating Condition State Machine       | GL-89, GL-103, GL-106 | Hierarchical thermal + kinematic state machine, 99.6% row coverage (high-confidence), rule-based with auditable intermediate variables                 |
| Deterministic Features                  | GL-91                 | Slope, delta, rolling-stability features for coolant, intake temperature, MAP, accelerator pedal (21 engineered features total)                        |
| Event Response Features                 | GL-92                 | Pedal-step event detection, pedal-to-throttle delay calculation with 3 s max delay boundary                                                            |
| Baseline Features & References          | GL-93, GL-173         | MAF/MAP dual-estimator baseline, speed-density model, pedal-throttle regression gap ? cross-validation passed                                          |
| Exploratory Data Analysis               | GL-172                | Feature-level summary statistics, condition-feature range tables, distribution plots                                                                   |
| Baseline Design                         | GL-173                | 5-step process: data scope check, feature availability check, baseline eligibility table, condition-stratified range analysis, baseline rule proposals |
| Proxy Threshold Calibration             | GL-175                | Revise proxy threshold definitions based on condition-stratified baseline reference table                                                              |
| Proxy Decision Boundary Optimization    | GL-176                | Optimize and tighten detection thresholds through iterative calibration                                                                                |
| Windowing Strategy Refactoring          | GL-177                | Proxy-specific physical-duration windows (3 s / 10 s / 30 s / 300 s / 600 s)                                                                           |
| Baseline & Proxy Documentation          | GL-174                | Supplement documentation for baseline design flow and proxy definitions                                                                                |
| Proxy Rule Verification                 | GL-205                | Verify proxy rules with simulated fault data ? baseline all-clear, injection triggers each proxy correctly                                             |
| Operating Condition Pipeline Supplement | GL-204                | Supplementary operating condition analysis pipeline refinements                                                                                        |
| Feature Overview Table                  | GL-154                | Model engineering feature overview table                                                                                                               |
| Subsequent Pipeline Re-run              | GL-155                | Rerun downstream feature pipelines after updates                                                                                                       |
| Reference & Knowledge Update            | GL-218                | Update reference.md and grounded_knowledge.yaml                                                                                                        |
| Interface Test Script                   | GL-219                | Modify interface test script for updated contracts                                                                                                     |
| Interface Table Update                  | GL-220                | Update the interface table in INTERFACE.md                                                                                                             |
| Feature Dataset Output                  | GL-221                | Rerun script and output final feature_dataset.csv                                                                                                      |

### [IN PROGRESS]

| Component                         | Ticket | Status | Description                                                                                                                                       |
| --------------------------------- | ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Proxy Definition Framework Update | GL-228 | Active | Update proxy_support.md document framework with Stage 1 (Observability Derivation), Stage 2 (Literature Anchoring), and Stage 3 (Detection Rules) |
| Observability Derivation          | GL-229 | Active | Supplementary Observability Derivation for all 5 proxies based on Bosch Automotive Handbook and SAE standards                                     |
| Literature Anchoring              | GL-230 | Active | Supplement and improve Literature Anchoring section for all 5 proxies with CARB Title 13, SAE J2012, ISO 26262 references                         |
| Decision Rule Calibration         | GL-231 | Active | Calibrated Decision Rules against project baseline ? threshold tuning, enable-window verification, sliding-window voting                          |
| Final Proxy Output & Interface    | GL-232 | Active | Output final proxy failure list and interface contract ? 5 proxy types with validated training labels                                             |

### [PLANNED]

| Component                            | Priority | Description                                                                   |
| ------------------------------------ | -------- | ----------------------------------------------------------------------------- |
| Feature Implementation               | P1       | Generate new features based on the updated proxy rules                        |
| Dashboard Pipeline Integration       | P1       | Wire final proxy outputs into the Dashboard pipeline end-to-end               |
| Baseline Rebuild                     | P1       | Rebuild baseline after new features are implemented                          |
| Proxy Re-train After Feature Updates | P1       | Re-run build_proxy_training_labels.py after any new features are implemented |

---

## Architecture

### Data Flow

```
Raw OBD-II CSV (KIT dataset, 81 trips, 118 segments)
    ↓
Cleaning Pipeline (cleaning_core.py)
  — Timestamp alignment & 1 Hz resampling
  — Missing-value imputation (forward-fill within gap limits)
  — Suspicious-value flagging
    ↓
Cleaned 1 Hz dataset + cleaning_quality.csv + cleaning_report.json
    ↓
Operating Condition State Machine
  — thermal_state: engine_off / warmup / post_warmup / unknown
  — child_state: idle / steady_driving / acceleration  deceleration / high_load / inactive_engine_off / unknown
  — condition_confidence: high / medium / low
    ↓
operating_condition_enriched.csv
    ↓
Feature Engineering (3 stages)
  Stage 1: Deterministic features — slopes, deltas, rolling stability (coolant, IAT, MAP, pedal, RPM)
  Stage 2: Event features — pedal step detection, pedal-to-throttle delay
  Stage 3: Baseline models — MAF/MAP cohesion, speed-density residual, pedal-throttle gap
    ↓
feature_dataset.csv (41 columns, 249,694 rows)
    ↓
Baseline Design
  — Feature availability check → eligibility table → condition-stratified range analysis
    ↓
condition_stratified_range_analysis.csv (per-feature, per-condition reference thresholds)
    ↓
Proxy Design
  — 5 proxy definitions with calibrated thresholds
  — Row-level proxy_flag → duration-window majority vote → final_label
    ↓
proxy_training_labels.csv (row-level flags) + proxy_duration_tables/*.csv (window-level labels)
```

### Technology Stack

| Component           | Technology                            | Purpose                                                           |
| ------------------- | ------------------------------------- | ----------------------------------------------------------------- |
| Data Processing     | pandas, numpy, scipy                  | CSV loading, resampling, rolling statistics, groupby aggregations |
| Data Cleaning       | Python + YAML config                  | Config-driven cleaning rules (column-specific, per strategy)      |
| Baseline Modeling   | scikit-learn (LinearRegression)       | Speed-density baseline, pedal-throttle regression                 |
| Data Validation     | Pydantic (shared/interface_models.py) | Type-safe DataLayerOutput contract                                |
| Visualization (EDA) | matplotlib, seaborn                   | Distribution plots, heatmaps, condition-feature range plots       |
| Testing             | pytest                                | Fault injection, null-robustness, contract validation             |

---

## Directory Structure

```
data_layer/
├── README.md                                   # This file
├── cleaning_and_profiling/                     # Stage 1: Raw data → cleaned 1 Hz
│   ├── data_cleaning/
│   │   ├── cleaning_config.yaml                # Column-specific cleaning strategies
│   │   ├── project_paths.py                    # Path resolution helpers
│   │   ├── data_cleaning.py                    # Main cleaning orchestrator
│   │   ├── cleaning_core.py                    # Core cleaning logic (alignment, imputation, flagging)
│   │   ├── quality_audit.py                    # Per-segment quality reporting
│   │   ├── cleaning_enriched.csv               # Final cleaned output
│   │   └── cleaning_report.json                # Per-segment quality metrics
│   └── quality_assessment_report.ipynb         # Visual quality assessment
├── operating_condition_statistics/             # Stage 2: State machine
│   ├── operating_condition_analysis.md         # State machine methodology & rule definitions
│   ├── operating_condition_rules.csv           # Rule-table for each condition transition
│   ├── operating_condition_enriched.csv        # Row-level condition labels
│   ├── operating_condition_counts_overall.csv  # Aggregate condition distribution
│   └── operating_condition_signal_summary.csv  # Per-condition signal statistics
├── exploratory_data_analysis/                  # EDA outputs
│   ├── global_feature_summary.csv              # Global statistics per feature
│   ├── condition_feature_ranges.csv            # Per-condition statistics
│   └── plots/
│       ├── global/                             # Global distribution plots
│       └── condition/                          # Condition-stratified comparison plots
├── feature_engineering/                        # Stage 3: Feature computation
│   ├── feature_dataset.csv                     # Primary output — 41 columns
│   ├── feature_dataset_metadata.json           # Schema, missing rates, validation results
│   ├── deterministic_features.csv              # Stage 1 intermediate (slopes, deltas, stability)
│   ├── baseline_features.csv                   # Stage 3 intermediate (MAF/MAP cohesion, residuals)
│   ├── event_feature_summary.csv               # Stage 2 intermediate (pedal event summary)
│   ├── feature_baselines.json                  # Baseline model parameters (speed-density fit)
│   └── feature_reference_summary.csv           # Per-feature reference thresholds (882 rows)
├── baseline_design/                            # Stage 4: Baseline reference
│   ├── baseline_design.md                      # Full methodology document
│   ├── data_scope_check.csv                    # Filtering effect on row count
│   ├── feature_availability_check.csv          # Per-feature availability classification
│   ├── baseline_eligibility_table.csv          # Baseline eligibility per feature
│   └── condition_stratified_range_analysis.csv # Primary reference table — per-feature, per-condition p05/p50/p95/p99
├── proxy_design/                               # Stage 5: Proxy fault labels
│   ├── proxy_support.md                        # Proxy definitions with detection rules & literature anchoring
│   ├── proxy_standard.md                       # Proxy detection methodology & general procedure
│   ├── build_proxy_training_labels.py          # Label generator — builds proxy_flag + final_label
│   ├── build_proxy_duration_tables.py          # Duration-window aggregator
│   ├── proxy_training_labels.csv               # Row-level + window-level training labels
│   └── proxy_duration_tables/                  # Duration-split window results
│       ├── proxy_windows_003s.csv
│       ├── proxy_windows_010s.csv
│       ├── proxy_windows_030s.csv
│       ├── proxy_windows_300s.csv
│       └── proxy_windows_600s.csv
└── tests/
    ├── .gitkeep
    └── test_fault_injection_all_proxies.py     # Synthetic fault injection for all 5 proxy types
```

---

## Completed Components

### 1. Data Cleaning Pipeline (`cleaning_and_profiling/data_cleaning/`)

**Purpose:** Transform raw per-trip OBD-II CSV dumps into a single cleaned, aligned, quality-audited 1 Hz dataset.

**Config-driven cleaning (`cleaning_config.yaml`):**

- Column-specific cleaning strategies (forward-fill, drop, interpolation)
- Gap tolerance: max 3 s consecutive NaN per signal before marking degraded
- Suspicious-value rules: e.g., coolant_temp > 150 °C flagged

**Core pipeline (`cleaning_core.py`):**

- Timestamp alignment and 1 Hz resampling per segment_id
- Missing-value imputation with configurable forwarding strategy
- Suspicious-value detection and flagging

**Quality audit (`quality_audit.py`):**

- Per-segment report: total rows, per-column missing count, suspicious-value count
- JSON output for automated downstream consumption

**Key metrics:**

- Raw 81 trips → cleaned 249,694 rows (at 1 Hz)
- Overall missing rate: < 0.1% after cleaning
- 118 segments across 81 trips

### 2. Operating Condition State Machine (`operating_condition_statistics/`)

**Purpose:** Assign physically meaningful operating-condition labels per row — the foundation for all condition-specific feature engineering and baseline design.

**Primary state (thermal_state):**

- `engine_off`: rpm < 50
- `warmup`: engine on, not yet post_warmup
- `post_warmup`: coolant_temp >= 75 °C AND (idle rpm < 850 OR cumulative_air_mass > 1500 g OR intake_temp - ambient_temp > 8 °C)
- `unknown`: critical fields missing

**Child state (child_state):**

- `idle`: speed_smooth < 1 km/h AND |accel| < 0.15 m/s²
- `acceleration`: moving, accel >= 0.15 m/s², not high-load
- `deceleration`: moving, accel <= -0.15 m/s²
- `high_load`: VSP >= 20 kW/t OR accel >= 1.2 m/s²
- `steady_driving`: moving but none of the above
- `inactive_engine_off`: engine off child state
- `unknown`: unreliable inference

**Key metrics:** 240,903 / 249,694 rows (96.5%) high-confidence classification.

### 3. Feature Engineering (`feature_engineering/`)

**Purpose:** Compute 21 derived features that encode vehicle-domain physical relationships, enabling proxy-fault detection and model-layer anomaly scoring.

**Three engineering stages:**

| Stage                             | Feature Type | Features                                                                                                                |
| --------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Deterministic (row-level or diff) | Slopes       | `coolant_slope`, `intake_temp_slope`, `map_slope`, `pedal_slope`, `rpm_slope`                                 |
| Deterministic (row-level)         | Deltas       | `coolant_ambient_delta`, `intake_ambient_delta`                                                                     |
| Deterministic (row-level)         | Fused        | `accel_pedal_mean`, `accel_pedal_channel_delta`, `accel_pedal_channel_ratio`                                      |
| Deterministic (rolling)           | Stability    | `coolant_stability` (60 s), `idle_rpm_stability` (10 s), `map_stability` (60 s), `intake_temp_stability` (60 s) |
| Deterministic (per-row)           | Flags        | `engine_on_flag`, `idle_flag`                                                                                       |
| Deterministic (segment-first)     | Gap          | `segment_gap_seconds`, `cold_soak_candidate_flag`                                                                   |
| Deterministic (raw proxy)         | Air load     | `maf_derived_air_load_raw`, `map_derived_air_load_raw`                                                              |
| Baseline model                    | Cohesion     | `maf_map_cohesion` (z-score abs diff)                                                                                 |
| Baseline model                    | Residual     | `speed_density_maf_residual` (g/s)                                                                                    |
| Event-based                       | Delay        | `pedal_to_throttle_delay` (s, pedal step events only)                                                                 |

**Feature dataset assembly:**

- 41 columns total: 10 identity/condition fields, 10 raw signals, 21 engineered features
- 249,694 rows, 1 Hz sampling
- Baseline models fitted on `post_warmup__steady_driving` golden reference (78,707 rows), applied to all high-confidence engine-running rows

### 4. Baseline Design (`baseline_design/`)

**Purpose:** Establish statistically grounded normal-operating reference ranges for every feature under every relevant operating condition, forming the threshold foundation for all 5 proxy definitions.

**Five-step process:**

1. **Data Scope Check**: Define eligible population (`condition_confidence == high` AND `engine_on_flag == 1`, 240,903 rows)
2. **Feature Availability Check**: Per-feature missing rate analysis and physical-meaning boundary conditions
3. **Baseline Eligibility Table**: Eligibility classification, recommended baselines, and modeling algorithms per feature
4. **Condition-Stratified Range Analysis**: Per-feature, per-condition p05/p50/p95/p99 reference table — 882 rows covering 52 distinct condition-feature combinations
5. **Baseline Rule Proposal**: Engineering-guardrail thresholds and detection rule drafts for each proxy

The final threshold configuration (V2) uses p95 for sensitivity, preserves physically meaningful lower bounds, and controls false positives through temporal voting rather than tighter thresholds.

### 5. Proxy Design (`proxy_design/`)

**Purpose:** Define 5 proxy failure types with physical rationale, detection rules, and executable label-generation code. Since the KIT dataset contains no explicit fault labels, proxy failures are constructed from physical plausibility constraints, condition-stratified statistical baselines, and iterative calibration.

**General detection pipeline (per proxy):**

1. **Pre-condition filter**: `condition_confidence == high` AND `engine_on_flag == 1`
2. **Condition filtering**: Enable window restricts detection to physically meaningful operating states (e.g., steady_driving for MAF/MAP comparison, idle for idle stability)
3. **Threshold comparison**: Per-feature p95 (with safety multipliers) from `condition_stratified_range_analysis.csv`
4. **Row-level candidate detection**: `proxy_flag_*` — relaxed thresholds to avoid premature filtering of genuine anomalies
5. **Duration-window majority voting**: A window is labelled anomalous only if ≥ 70% of rows within the window satisfy the proxy condition

**Proxy definitions:** See proxy_support.md

**Proxy training labels (`build_proxy_training_labels.py`):**

- Reads row-level proxy flags from existing proxy_training_labels.csv
- Applies all 5 proxy detection rules using thresholds from `condition_stratified_range_analysis.csv`
- Generates both row-level `proxy_flag_*` and duration-window `final_label_*` columns
- Each proxy uses its own physical-duration voting window (e.g., MAF 30 s, pedal 10 s, MAP 3 s, idle 30 s)

**Proxy duration tables (`build_proxy_duration_tables.py`):**

- 5 physical duration windows per proxy: 3 s, 10 s, 30 s, 300 s, 600 s
- Each window reports: `proxy_support_count` (rows with proxy_flag=1), `condition_ratio` (support_count / window_length)
- A window is flagged when `condition_ratio >= 0.7`

**Key validation:** All 5 proxies produce zero false positives on normal KIT data (final_label all zero across all 249,694 rows). This was verified through 3 rounds of iterative tightening — stricter thresholds, longer windows, and proxy-specific (not fixed) voting durations.

### 6. Fault Injection Test (`tests/test_fault_injection_all_proxies.py`)

**Purpose:** Verify that the proxy detection pipeline correctly identifies all 5 fault types when synthetic fault signals are injected into a real segment.

**Test phases:**

- **Phase 1 (Baseline):** Run the pipeline on clean segment `trip_0079_seg_003` — confirm all proxy final_labels are 0 (no false positives)
- **Phase 2 (Injection):** Inject synthetic fault features for each of the 5 proxy types into the same segment — re-run pipeline and verify each proxy detects its injected fault

**Injection methods:**

- `cooling_degradation`: Set `coolant_ambient_delta` to 100 °C
- `intake_heat_soak`: Set `intake_ambient_delta` to 50 °C and `abs(intake_temp_slope)` to 5 °C/s
- `maf_anomaly`: Set `maf_map_cohesion` to 20.0 and `abs(speed_density_maf_residual)` to 100.0
- `map_plausibility`: Set `map_slope` to 0.0 with high pedal delta, and `abs(speed_density_maf_residual)` to 50.0
- `pedal_sensor`: Set `accel_pedal_channel_delta` to 20.0, `accel_pedal_channel_ratio` to 2.0

---

## Dependencies

### Input: Raw OBD-II CSV

Consumes raw per-trip CSV files from the KIT Automotive OBD-II dataset (81 trips, 118 segments). Each CSV contains raw OBD-II signals recorded at varying sample rates, then resampled to 1 Hz during cleaning. Required raw signals:

| Signal            | Unit | Source    |
| ----------------- | ---- | --------- |
| `coolant_temp`  | °C  | PID 0x05  |
| `map`           | kPa  | PID 0x0B  |
| `rpm`           | rpm  | PID 0x0C  |
| `speed`         | km/h | PID 0x0D  |
| `intake_temp`   | °C  | PID 0x0F  |
| `maf`           | g/s  | PID 0x10  |
| `tps`           | %    | PID 0x11  |
| `ambient_temp`  | °C  | PID 0x46  |
| `accel_pedal_d` | %    | Channel D |
| `accel_pedal_e` | %    | Channel E |

### Output: Data Layer Output

Produces `DataLayerOutput` for Model Layer consumption — the 41-column `feature_dataset.csv`:

```python
class IdentityTimeColumns:
    timestamp: str              # ISO 8601
    trip_id: str                # KIT trip identifier
    segment_id: str             # Segment within trip
    row_in_segment: int         # Row position
    dt_seconds: float           # Seconds since segment start

class OperatingConditionColumns:
    thermal_state: str          # engine_off | warmup | post_warmup | unknown
    child_state: str            # idle | steady_driving | acceleration | deceleration | high_load | inactive_engine_off | unknown
    operating_state: str        # Combined: {thermal_state}__{child_state}
    condition_confidence: str   # high | medium | low
    condition_quality_flags: str  # Binary-encoded quality flags

class RawSignalColumns:
    coolant_temp: float          # °C
    map: float                   # kPa
    rpm: float                   # rpm
    speed: float                 # km/h
    intake_temp: float           # °C
    maf: float                   # g/s
    tps: float                   # %
    ambient_temp: float          # °C
    accel_pedal_d: float         # %
    accel_pedal_e: float         # %

class EngineeredFeatureColumns:
    # Slopes
    coolant_slope: float         # °C/s
    intake_temp_slope: float     # °C/s
    map_slope: float             # kPa/s
    pedal_slope: float           # %/s
    rpm_slope: float             # rpm/s
    # Deltas
    coolant_ambient_delta: float  # °C
    intake_ambient_delta: float   # °C
    # Channel fusion
    accel_pedal_mean: float      # %
    accel_pedal_channel_delta: float  # %
    accel_pedal_channel_ratio: float  # dimensionless
    # Rolling stability
    coolant_stability: float     # °C
    idle_rpm_stability: float    # rpm
    map_stability: float         # kPa
    # Air load proxies
    maf_derived_air_load_raw: float  # g/rev
    map_derived_air_load_raw: float  # rpm*kPa/K
    # Baseline-model outputs
    maf_map_cohesion: float      # z-score abs diff
    speed_density_maf_residual: float  # g/s
    pedal_throttle_gap: float    # %
    # Event features
    pedal_to_throttle_delay: float    # s (NaN for non-event rows)
    # Flags
    engine_on_flag: int           # 0 | 1
    idle_flag: int                # 0 | 1
```

The secondary output `proxy_training_labels.csv` contains for each row:

- 5 `proxy_flag_*` columns: row-level candidate anomalies (0/1)
- 5 `final_label_*` columns: window-level labels after 70% majority voting (0/1)

### External Dependencies

- **Python Packages (root `requirements.txt`):** `pandas>=2.0.0`, `numpy>=1.24.0`, `scipy>=1.10.0`, `scikit-learn>=1.2.0`, `pydantic>=2.0.0,<3.0.0`, `pytest>=7.4.0`, `PyYAML>=6.0`
- **Input Data:** KIT Automotive OBD-II dataset (81 raw trips, 118 segments) — stored under `data/` (LFS-tracked)
- **Config:** `cleaning_config.yaml` defines column-specific cleaning strategies

---

## How to Run

All commands assume the root `requirements.txt` dependencies are installed.

### Prerequisites

```bash
# From repository root
cd D:\OBD-II\granite-lifeline
pip install -r requirements.txt
```

### Generate Feature Dataset

```bash
# Run the full feature engineering pipeline
# (Cleaning → Operating Condition → Feature Engineering)
python data_layer/feature_engineering/assemble_feature_dataset.py
# Output: data_layer/feature_engineering/feature_dataset.csv
```

### Generate Proxy Training Labels

```bash
# From data_layer
python data_layer/proxy_design/build_proxy_training_labels.py
# Output: data_layer/proxy_design/proxy_training_labels.csv
```

### Generate Proxy Duration Tables

```bash
python data_layer/proxy_design/build_proxy_duration_tables.py
# Output: data_layer/proxy_design/proxy_duration_tables/proxy_windows_*.csv
```

### Run Fault Injection Tests

```bash
# From repository root
pytest data_layer/tests/test_fault_injection_all_proxies.py -v
```

---

## Quality Assurance

### Validation Results

| Check                            | Result                                                                                                                                                                        |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Feature dataset row count        | 249,694 rows (matches raw cleaning output)                                                                                                                                    |
| All feature CSV row counts match | ✓ (operating: 249,694, deterministic: 249,694, event: 249,694, baseline: 249,694)                                                                                            |
| Key column uniqueness            | ✓ (timestamp + trip_id + segment_id + row_in_segment) — 0 duplicates                                                                                                        |
| Missing rates                    | All < 1% except intentional:`pedal_to_throttle_delay` (99.6% — event-only), `idle_rpm_stability` (98.6% — idle-only), `coolant_stability` (28.8% — post-warmup-only) |
| Proxy labels on normal data      | All 5 proxies — 0 false positives (249,694 rows of all-zero final_labels)                                                                                                    |
| Condition confidence             | 240,903 / 249,694 rows (96.5%) high-confidence                                                                                                                                |

### Compliance Checklist

All generated outputs must satisfy:

- ✅ **Interface compliance**: 41-column feature_dataset.csv matches `docs/INTERFACE.md` Section 1 contract
- ✅ **Segment safety**: Rolling windows never cross segment_id boundaries
- ✅ **Condition awareness**: All engineered features validate `condition_confidence == high` before computation
- ✅ **Proxy label stability**: All-zero on normal data (3 rounds of iterative tightening)
- ✅ **Proxy detection reproducibility**: `build_proxy_training_labels.py` is deterministic with fixed thresholds
- ⬜ **CI integration**: `data_layer/tests/` is not yet wired into CI

---

## Remaining Work

**1. Documentation Refinements** (P1)

- Complete all 5 proxies in proxy_support.md

**2. Feature Implementation** (P1)

**3. Proxy Detection Code Updates** (P1)

**4. CI Integration** (P1)

- Wire `data_layer/tests/` into the project's CI pipeline

### Future Enhancements

- Cross-trip baseline adaptation — recalibrate thresholds per trip to capture vehicle-specific variance
- Transfer-test pipeline against a second vehicle's OBD dataset

---

## Troubleshooting

### Feature Dataset Missing Rates Unexpected

**Issue:** A derived feature shows >5% missing rate outside its expected scope.

**Explanation:** Most engineered features have intentional missing rows:

- Rolling features (`coolant_stability`, `idle_rpm_stability`, `map_stability`) are valid only in specific operating windows and after sufficient warm-up time
- Event features (`pedal_to_throttle_delay`) are recorded only when a pedal-step event is detected
- Check `feature_dataset_metadata.json` for the full missing-rate breakdown

**Solution:** If a derived feature is unexpectedly sparse, verify the condition filters in `feature_engineering/` assembly logic — a pre-condition may be too restrictive.

### Proxy Labels All Zero After Detection

**Explanation:** This is the expected behaviour on the normal KIT dataset (all 81 trips are healthy). Zero false positives across 249,694 rows is a validated quality target. To verify detection logic, use the synthetic fault injection test (`test_fault_injection_all_proxies.py`).

### `ModuleNotFoundError: No module named 'shared'`

**Solution:**

```bash
# Ensure you're running from repository root
cd D:\OBD-II\granite-lifeline
python -c "from shared.interface_models import DataLayerOutput; print('OK')"
```

### Condition Classification Produces Too Many `unknown` Rows

**Explanation:** The operating-condition state machine requires both `coolant_temp` and either `maf` or a vehicle-speed-related signal. Missing sensor readings during logging gaps produce unknown classification.

**Solution:** Check `cleaning_quality.csv` for per-segment sensor availability. Segments with < 50% signal coverage may need to be excluded from downstream analysis.

---

## Team & Contact

**Data Team:**

- Lei Pei — Cleaning / Operating Condition /Feature Engineering
- Qiuting Fu — EDA / Baseline Design / Proxy Design

**Project:** Granite Lifeline
**Institution:** University of Bristol MSc Computer Science
**Sponsor:** IBM

For questions or contributions, please refer to the main project README or create a Jira ticket.

---

## References

- [KIT Automotive OBD-II Dataset](https://www.kaggle.com/datasets/jahnjohannes/automotive-vehicle-engine-obd2-data) — Source dataset
- [SAE J2012](https://www.sae.org/standards/content/j2012_201603/) — DTC definitions
- [SAE J1979](https://www.sae.org/standards/content/j1979_201702/) — OBD-II PID specifications and measurement bounds
- [Bosch Automotive Handbook, 10th Edition](https://www.bosch-automotive.com/) — Physical principles and sensor characteristics
- [CARB Title 13 CCR §1968.2](https://ww2.arb.ca.gov/) — On-board diagnostic II regulations
- [Project INTERFACE.md](../docs/INTERFACE.md) — Data contracts (DataLayerOutput schema)
