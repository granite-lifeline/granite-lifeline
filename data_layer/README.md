# Data Layer

**Owner:** Data Team
**Status:** Active Development
**Last Updated:** 2026-07-24

---

## Overview

The Data Layer is the first stage in the Granite Lifeline predictive maintenance pipeline. It transforms raw OBD-II CSV data from the KIT dataset into cleaned, enriched, feature-engineered tabular data and proxy-fault training labels consumed by the Model Layer and downstream evaluation.

```
Raw CSV → Cleaning → Operating Conditions → Feature Engineering (00-41) → Proxy Decisions (50-70)
                                                                              ↓
                                               Offline tools: 90 (calibration audit), 91 (research diagnostics)
                                               Fault injection validation: run_fault_injection.py
```

There are no labelled fault data in the KIT dataset — all 81 trips are healthy driving. Proxy faults are therefore defined from physical principles, calibrated against normal-data statistics, and validated through three independent mechanisms:

1. **Script 90** — Calibration reproduction audit (48/48 PASS)
2. **Script 91** — LOTO stability tables, candidate grid scans, bootstrap confidence intervals
3. **Fault injection** — 11 synthetic cases covering all executable sub-checks (11/11 PASS)

### Core Responsibilities

1. **Data Cleaning & Quality Auditing**: Timestamp alignment, 1 Hz resampling, missing-value treatment, suspicious-value flagging, and per-segment quality reporting
2. **Operating Condition Classification**: Hierarchical state machine assigning thermal_state and child_state per row
3. **Feature Engineering**: 24 production features across 4 stages — atomic, engine-start context, window-level, and calibrated transforms
4. **Proxy Decision Engine**: 5 proxy failure types with 15 executable sub-checks, each with typed decision roles (verdict / pending_precursor / support / arbitration_evidence)
5. **Calibration Audit (script 90)**: Reproduce every frozen threshold from the healthy cohort and compare against the calibration registry
6. **Research Diagnostics (script 91)**: LOTO stability, candidate grid scans, bootstrap confidence intervals
7. **Fault Injection Validation**: 11 synthetic cases proving the proxy engine detects injected faults

### Proxy Failure Types (5)

- **cooling_degradation**: Slow warm-up (P0128), overheating (P0217), rising without plateau (pending), cold-start ECT plausibility (support)
- **air_intake_maf_anomaly**: High-load under-read (P0101), zero MAF while firing (P0102)
- **accelerator_pedal_sensor**: Channel-relation residual (P2138), extreme disagreement (P2138 high tier)
- **intake_air_temperature_sensor_fault**: Stuck/no-response IAT (P0111), cold-start IAT plausibility (support, P0111), physical range (P0112/P0113)
- **map_load_signal_plausibility_fault**: Step response (P0106), steady-state residual (arbitration), stuck MAP (P0106)

---

## Current Implementation Status

### [COMPLETED]

| Component | Description |
|---|---|
| Data Cleaning Pipeline | Raw CSV to cleaned 1 Hz dataset with config-based validation |
| Operating Condition State Machine | Hierarchical thermal + kinematic state machine, 96.5% high-confidence coverage |
| Feature Engineering Pipeline | 00-input contract → 10-atomic → 20-engine-start → 30-windows → 40-calibrated → 41-production (24 features, 46 columns) |
| Calibration Registry | Frozen calibration_registry.v1.json with all thresholds, model coefficients, routing rules |
| Script 90 — Calibration Audit | Reproduce every data-driven threshold from healthy cohort; 48/48 PASS |
| Script 91 — Research Diagnostics | LOTO stability tables (15 checks), grid scans (3), bootstrap CI (3) |
| Proxy Decision Engine | 50-rule-state → 60-events → 61-durations → 70-decisions; 1,471 rows, 0 triggered on healthy data |
| Fault Injection Validation | 11 synthetic cases covering all executable sub-checks; 11/11 PASS |
| Proxy Definition & Support Docs | Observability derivation, literature anchoring, calibration audit for all 5 proxies |
| Pipeline Infrastructure | RunLayout, manifests, continuity library, contract lint, test fixtures |

### [IN PROGRESS]

| Component | Status | Description |
|---|---|---|
| Dashboard Pipeline Integration | Planned | Wire final proxy outputs into the Dashboard pipeline end-to-end |

### [PLANNED]

| Component | Priority | Description |
|---|---|---|
| Stage 4 Graded Detectability | P2 | Multi-severity injection for detectability curves (TBD-2) |
| Stage 4 Held-Out FP Rate | P2 | False-positive rate on held-out healthy trips (TBD-3) |
| Dashboard Integration | P1 | Wire proxy outputs into the Dashboard |

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
  — child_state: idle / steady_driving / acceleration / deceleration / high_load / inactive / unknown
    ↓
operating_condition_enriched.csv
    ↓
Feature Engineering Pipeline (run_pipeline.py → 00 → 10 → 20 → 30 → 40 → 41)
  00: Input contract validation (key equality, schema, 1 Hz continuity)
  10: Atomic features — segment_gap, engine_on_flag, temperature deltas, pedal slopes
  20: Engine-start context — episode detection, start values, elapsed time
  30: Window features — rolling std, MAF integral, ECT rate, MAP range
  40: Calibrated features — speed-density residual, pedal-mapping residual
  41: Production feature assembly — 46 columns, 24 B-class features
    ↓
production_features.csv (249,694 rows, 46 columns)
    ↓
Proxy Decision Pipeline (50 → 60 → 61 → 70)
  50: Rule-state builder — eligibility masks, context opportunities, physical-range evidence
  60: Event evidence builder — pedal-step events, response/no-response labels
  61: Duration evidence builder — threshold/same-side run episodes
  70: Proxy decision builder — final verdict, support, pending, arbitration, DTC routing
    ↓
proxy_decisions.csv (decision-grain: proxy_id × sub_check × trip_id × decision_id)

--- Offline / Admin Tools ---

90_calibration_registry_builder.py
  Load healthy cohort → re-derive every frozen threshold → compare with registry
  Output: calibration_audit_manifest.json

91_research_diagnostics_builder.py
  Load production features → LOTO / grid scans / bootstrap
  Output: LOTO tables, grid scans, bootstrap CI → research_diagnostics/

run_fault_injection.py
  Load healthy run → inject signal fault → rerun 50-70 → compare result
  Output: fault_injection_summary_*.json, run directories under data/processed/runs/
```

### Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Data Processing | pandas, numpy, scipy | CSV loading, resampling, rolling statistics, groupby aggregations |
| Data Cleaning | Python + YAML config | Config-driven cleaning rules (column-specific, per strategy) |
| Baseline Modeling | scikit-learn (LinearRegression) | Speed-density baseline, pedal-throttle regression |
| Data Validation | Pydantic (pipeline_data/manifests.py) | Type-safe manifest and artifact descriptor contracts |
| Pipeline Infrastructure | Python dataclasses + pathlib | RunLayout, manifest I/O, continuity library |
| Testing | pytest | Contract tests, fixture validation, stage integration tests |

---

## Directory Structure

```
data_layer/
├── README.md                           # This file
├── run_pipeline.py                     # Public entry point (cleaning → 00-41)
├── calibration/                        # Frozen calibration registry
│   ├── calibration_registry.v1.json    # All thresholds, coefficients, routing rules
│   ├── calibration_registry.v1.manifest.json
│   └── calibration_audit_manifest.json # Script 90 output (48/48 PASS)
├── contracts/
│   └── feature_manifest.v1.json        # Production feature contract
├── data_cleaning/src/
│   ├── cleaning_config.yaml            # Column-specific cleaning strategies
│   ├── cleaning_core.py                # Core cleaning logic
│   ├── data_cleaning.py                # Cleaning orchestrator
│   ├── quality_audit.py                # Per-segment quality reporting
│   └── project_paths.py                # Path resolution helpers
├── operating_condition_statistics/
│   ├── operating_condition_analysis.md # State machine methodology
│   ├── src/operating_condition_analysis.py
│   └── ...
├── feature_engineering/
│   ├── feature_schema.md               # Authoritative field definitions (A/B/C/D classes)
│   └── src/
│       ├── 00_input_contract_validator.py
│       ├── 10_atomic_feature_builder.py
│       ├── 20_engine_start_context_builder.py
│       ├── 30_window_feature_builder.py
│       ├── 40_calibrated_feature_builder.py
│       ├── 41_production_feature_assembler.py
│       ├── 90_calibration_registry_builder.py  # Offline: calibration audit
│       └── 91_research_diagnostics_builder.py  # Offline: LOTO + grid + bootstrap
├── proxy_failure/
│   ├── proxy_failure_definition.md      # Executable proxy rules (consumes A+B, frozen C2)
│   ├── proxy_support.md                # Research + calibration audit companion
│   ├── proxy_stage4_report.md          # Fault injection validation results
│   └── src/
│       ├── 50_rule_state_builder.py
│       ├── 60_event_evidence_builder.py
│       ├── 61_duration_evidence_builder.py
│       └── 70_proxy_decision_builder.py
├── fault_injection/                    # Stage 4 validation
│   ├── experimental_design.md          # Bilingual experimental design document
│   ├── configs/fault_injection_cases.v1.json
│   ├── src/run_fault_injection.py
│   └── outputs/fault_injection_summary_*.json
├── research_diagnostics/               # Script 91 outputs (in git)
│   ├── loto_*.csv                      # LOTO stability tables (15 checks)
│   ├── grid_*.csv                      # Candidate grid scans (3)
│   └── bootstrap_*.json                # Bootstrap confidence intervals (3)
├── pipeline_data/                      # Shared infrastructure
│   ├── paths.py                        # RunLayout, repo path contracts
│   ├── manifests.py                    # Stage manifest I/O
│   ├── continuity.py                   # Continuity block library
│   ├── contract_lint.py                # Cross-contract validation
│   └── __init__.py
└── tests/
    ├── fixture_tests/
    ├── pipeline_data_test/
    ├── feature_engineering_test/
    ├── proxy_test/
    └── fixtures/                       # production_features.v1.fixture.csv
```

---

## How to Run

All commands assume root dependencies are installed. Run from the repository root.

### Full Production Pipeline (cleaning → features → proxy decisions)

```bash
# Step 1: Feature engineering (cleaning → conditions → 00-41)
$env:PYTHONPATH = "."
python data_layer/run_pipeline.py --run-id run_20260724

# Step 2: Proxy decision engine (50 → 60 → 61 → 70)
python data_layer/proxy_failure/src/50_rule_state_builder.py --run-id ...
python data_layer/proxy_failure/src/60_event_evidence_builder.py --run-id ...
python data_layer/proxy_failure/src/61_duration_evidence_builder.py --run-id ...
python data_layer/proxy_failure/src/70_proxy_decision_builder.py --run-id ...
```

### Offline Audit Tools

```bash
# Calibration audit (script 90)
python data_layer/feature_engineering/src/90_calibration_registry_builder.py \
  --run-dir data/processed/runs/run_20260724

# Research diagnostics (script 91)
python data_layer/feature_engineering/src/91_research_diagnostics_builder.py \
  --run-dir data/processed/runs/run_20260724

# With optional grid scans and bootstrap
python 91_research_diagnostics_builder.py \
  --run-dir data/processed/runs/run_20260724 --grid-scans --bootstrap

# Fault injection validation
python data_layer/fault_injection/src/run_fault_injection.py \
  --base-run-id run_20260724
```

---

## Quality Assurance

### Validation Summary

| Check | Result |
|---|---|
| Production features row count | 249,694 rows (matches raw cleaning output) |
| Feature count per row | 46 columns (4 keys + 16 A-class + 24 B-class + 2 provenance) |
| Key uniqueness | 0 duplicates on (timestamp + trip_id + segment_id + row_in_segment) |
| Proxy decisions on healthy data | 1,471 decision rows, 0 triggered (all 5 proxies) |
| Script 90 calibration audit | 48/48 PASS |
| Script 91 LOTO stability | All 15 checks PASS, max deviation varies by threshold type |
| Fault injection validation | 11/11 synthetic cases PASS |

---

## Team & Contact

**Data Team:**

- Lei Pei — Cleaning / Operating Condition / Feature Engineering / Proxy Engine
- Qiuting Fu — EDA / Baseline Design / Proxy Support / Calibration Audit / Research Diagnostics / Fault Injection

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
- [CARB Title 13 CCR section 1968.2](https://ww2.arb.ca.gov/) — On-board diagnostic II regulations