# Data Layer

**Owner:** Data Team
**Status:** Active Development
**Last Updated:** 2026-07-27

---

## Overview

The Data Layer is the first stage in the Granite Lifeline predictive maintenance pipeline. It transforms raw KIT OBD-II CSV files into cleaned, quality-audited, condition labelled, feature-engineered data and frozen proxy decisions for Model Layer consumption.

```text
Raw OBD-II CSV → Cleaning → Operating Conditions → Feature Engineering → Proxy Decision Engine → Model Layer
```

The source corpus contains healthy driving rather than labelled component failures. Proxy rules are therefore derived from observable signal behaviour, anchored to physical and regulatory judgement forms, calibrated against the healthy baseline, reproduced through offline audit, and evaluated with controlled synthetic fault injection.

### Core Responsibilities

1. **Data Cleaning and Quality Auditing**: Align timestamps, resample to 1 Hz, treat short missing intervals, flag suspicious values, and report data quality
2. **Operating-Condition Classification**: Assign thermal and kinematic states with confidence and quality provenance
3. **Feature Engineering**: Produce atomic, engine-start, rolling-window, and calibrated features under a versioned schema
4. **Proxy Evidence Construction**: Convert row-level feature states into event and duration evidence
5. **Proxy Decision Generation**: Apply 14 executable sub-checks across five proxy families with typed decision roles and DTC routing
6. **Calibration Reproduction**: Re-derive frozen parameters and compare them with the read-only calibration registry
7. **Research Diagnostics**: Evaluate threshold stability with leave-one-trip-out analysis, candidate grids, and bootstrap summaries
8. **Synthetic Fault Injection**: Verify graded detectability, boundary behaviour, DTC identity, and emission semantics
9. **Artifact Governance**: Maintain explicit run layouts, manifests, checksums, provenance, and cross-stage contracts

### Proxy Failure Families

- **cooling_degradation**: slow warm-up, overheating, rising-temperature precursor, and cold-start ECT plausibility
- **air_intake_maf_anomaly**: high-load MAF under-read and zero MAF while firing
- **accelerator_pedal_sensor**: channel-mapping residual and extreme redundant-channel disagreement
- **intake_air_temperature_sensor_fault**: stuck/no-response IAT, cold-start plausibility, and physical-range violations
- **map_load_signal_plausibility_fault**: pedal-step response, shared steady-state residual evidence, and stuck MAP

---

## Current Implementation Status

### [COMPLETED]

| Component                         | Description                                                                                         |
| --------------------------------- | --------------------------------------------------------------------------------------------------- |
| Data Cleaning Pipeline            | Raw CSV to cleaned 1 Hz data with configurable validation, imputation limits, and quality auditing  |
| Operating-Condition State Machine | Hierarchical`thermal_state` and `child_state` classification with confidence and quality fields |
| Feature Engineering Pipeline      | Stages 00/10/20/30/40/41 producing 249,694 rows and 46 production columns                           |
| Feature Contract                  | Versioned 24-feature production manifest with schema and provenance requirements                    |
| Calibration Registry              | Frozen, read-only thresholds, model coefficients, guards, and routing rules                         |
| Calibration Audit                 | 48/48 reproduction checks passed                                                                    |
| Research Diagnostics              | LOTO, candidate-grid, and bootstrap stability outputs                                               |
| Proxy Decision Engine             | Stages 50/60/61/70; 14 executable sub-checks and 1,471 healthy decision rows                        |
| Synthetic Fault Injection         | 14 cases × 3 severities × 3 trips; 126 observations; 14/14 cases accepted                         |
| Research Documentation            | Proxy definition, support derivations, completed Stage-4 evidence, and formal injection methodology |
| Pipeline Infrastructure           | `RunLayout`, manifests, checksums, continuity helpers, and contract linting                       |
| Upload Intake Contract            | Single-file callable entry point with fail-fast KIT file-name, column, and row-count validation     |
| Automated Tests                   | Fixture, pipeline-contract, feature, proxy, upload-intake, and fault-injection regression tests      |

### [IN PROGRESS]

| Component                   | Status                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| Model Layer Handoff         | Feature contract frozen and output path exposed; consumer-side items tracked in Remaining Work |
| Dashboard Handoff           | Upload entry point delivered; interface details tracked in Remaining Work                   |
| Documentation Consolidation | Ongoing alignment of implementation, contract, audit, and research documents               |

### [PLANNED]

| Component                     | Priority | Description                                                                                  |
| ----------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| End-to-End Pipeline Tests     | P1       | Exercise raw input through Data Layer and Model Layer handoff                                |
| Runtime Performance Profiling | P1       | Measure stage-level memory, latency, and artifact-size costs, including single-upload latency |
| Upload Run Retention          | P1       | Define a cleanup policy for run directories accumulated by Dashboard uploads                 |

---

## Architecture

### Data Flow

```text
Raw KIT OBD-II CSV files
    ↓
Cleaning Pipeline
    ├─ timestamp normalization and 1 Hz resampling
    ├─ bounded missing-value treatment
    ├─ suspicious-value and provenance flags
    └─ cleaning quality/report artifacts
    ↓
Operating-Condition State Machine
    ├─ thermal_state
    ├─ child_state
    ├─ operating_state
    └─ condition_confidence / condition_quality_flags
    ↓
Feature Engineering
    ├─ 00 input-contract validation
    ├─ 10 atomic features
    ├─ 20 engine-start context
    ├─ 30 rolling-window features
    ├─ 40 calibrated transforms
    └─ 41 production feature assembly
    ↓
production_features.csv
    ↓
Proxy Evidence and Decisions
    ├─ 50 rule-state masks
    ├─ 60 event evidence
    ├─ 61 duration evidence
    └─ 70 final decisions and DTC routing
    ↓
proxy_decisions.csv
    ↓
Model Layer
```

### Offline Validation Flow

```text
Frozen calibration registry
    ├─ Script 90: parameter reproduction audit
    ├─ Script 91: LOTO / grid / bootstrap diagnostics
    └─ Stage 4: graded target-signal fault injection
                     ↓
              rerun stages 50/60/61/70
                     ↓
              scoped detection and contract checks
```

### Decision Roles

| Role                     | Purpose                               | Active state  | Independent DTC emission     |
| ------------------------ | ------------------------------------- | ------------- | ---------------------------- |
| `verdict`              | Executable diagnostic decision        | `triggered` | According to the frozen rule |
| `pending_precursor`    | Early condition awaiting confirmation | `pending`   | No                           |
| `support`              | Sensor-trust or confidence evidence   | `triggered` | No                           |
| `arbitration_evidence` | Shared evidence requiring attribution | `triggered` | No                           |

### Technology Stack

| Component            | Technology                                      | Purpose                                                                |
| -------------------- | ----------------------------------------------- | ---------------------------------------------------------------------- |
| Data Processing      | pandas, NumPy                                   | CSV processing, grouping, rolling statistics, deterministic transforms |
| Statistical Analysis | SciPy, scikit-learn                             | Distribution analysis and baseline linear models                       |
| Configuration        | YAML, JSON                                      | Cleaning rules, frozen calibration, fault-injection cases              |
| Contracts            | Python dataclasses, Pydantic-compatible schemas | Run layouts, manifests, artifact descriptors                           |
| Integrity            | SHA-256 manifests                               | Input/output verification and provenance                               |
| Testing              | pytest                                          | Unit, contract, fixture, integration, and regression tests             |

---

## Directory Structure

```text
data_layer/
├── README.md
├── run_pipeline.py                         # Public online pipeline and upload entry points
├── calibration/
│   ├── calibration_registry.v1.json        # Frozen thresholds and routing
│   ├── calibration_registry.v1.manifest.json
│   └── calibration_audit_manifest.json     # Script-90 reproduction result
├── contracts/
│   └── feature_manifest.v1.json            # Production feature contract
├── data_cleaning/
│   └── src/
│       ├── cleaning_config.yaml
│       ├── cleaning_core.py
│       ├── data_cleaning.py
│       ├── project_paths.py
│       └── quality_audit.py
├── operating_condition_statistics/
│   ├── operating_condition_analysis.md
│   └── src/
├── feature_engineering/
│   ├── feature_schema.md
│   └── src/
│       ├── 00_input_contract_validator.py
│       ├── 10_atomic_feature_builder.py
│       ├── 20_engine_start_context_builder.py
│       ├── 30_window_feature_builder.py
│       ├── 40_calibrated_feature_builder.py
│       ├── 41_production_feature_assembler.py
│       ├── 90_calibration_registry_builder.py
│       └── 91_research_diagnostics_builder.py
├── proxy_failure/
│   ├── proxy_failure_definition.md          # Authoritative executable rules
│   ├── proxy_support.md                     # Research and validation evidence
│   └── src/
│       ├── 50_rule_state_builder.py
│       ├── 60_event_evidence_builder.py
│       ├── 61_duration_evidence_builder.py
│       └── 70_proxy_decision_builder.py
├── fault_injection/
│   ├── fault_injection_methodology.md       # Formal experimental methodology
│   ├── configs/
│   │   └── fault_injection_cases.v1.json
│   ├── src/
│   │   └── run_fault_injection.py
│   └── outputs/
│       ├── fault_injection_summary_*.csv
│       └── fault_injection_summary_*.json
├── research_diagnostics/
│   ├── loto_*.csv
│   ├── grid_*.csv
│   └── bootstrap_*.json
├── pipeline_data/
│   ├── continuity.py
│   ├── contract_lint.py
│   ├── manifests.py
│   ├── paths.py
│   └── upload_contract.py                    # Single-file upload intake rules
└── tests/
    ├── condition_label_crosscheck/
    ├── feature_engineering_test/
    ├── fixture_tests/
    ├── pipeline_data_test/
    ├── proxy_test/
    └── fixtures/
```

Runtime artifacts are stored under:

```text
data/processed/runs/<run_id>/
```

---

## Completed Components

### 1. Data Cleaning (`data_cleaning/src/`)

**Purpose:** Convert heterogeneous raw OBD-II CSV files into a consistent
1 Hz dataset while preserving explicit quality provenance.

**Features:**

- normalizes timestamp and signal fields;
- resamples within segment boundaries;
- applies column-specific missing-value strategies;
- prevents imputation across excessive gaps;
- records suspicious and hard-invalid source conditions;
- emits cleaning quality and report artifacts.

### 2. Operating-Condition Classification (`operating_condition_statistics/`)

**Purpose:** Describe the physical context in which proxy evidence is
interpretable.

**States:**

- thermal: `engine_off`, `warmup`, `post_warmup`, `unknown`;
- child: `idle`, `steady_driving`, `acceleration`, `deceleration`,
  `high_load`, `inactive`, `unknown`.

Condition confidence and quality flags are retained as production inputs rather
than being discarded after classification.

### 3. Feature Engineering (`feature_engineering/src/`)

**Purpose:** Build the versioned feature table consumed by proxy stages.

| Stage | Output responsibility                                            |
| ----- | ---------------------------------------------------------------- |
| 00    | Validate input identity, keys, schema, continuity, and manifests |
| 10    | Calculate atomic features and simple deltas/slopes               |
| 20    | Identify observed engine starts and episode context              |
| 30    | Calculate rolling stability, rate, range, and integral features  |
| 40    | Apply frozen calibrated transforms                               |
| 41    | Assemble and validate the production feature contract            |

The reference run contains 249,694 rows, 118 segments, 81 trips, and 46
production columns.

### 4. Calibration and Research Diagnostics

**Script 90:** `feature_engineering/src/90_calibration_registry_builder.py`

- re-derives frozen data-driven quantities;
- compares them with the release registry;
- records value, tolerance, method, and status;
- current result: 48/48 PASS.

**Script 91:** `feature_engineering/src/91_research_diagnostics_builder.py`

- leave-one-trip-out stability analysis;
- registered candidate-grid scans;
- bootstrap distribution summaries;
- research-only execution that cannot modify the frozen online registry.

### 5. Proxy Decision Engine (`proxy_failure/src/`)

**Purpose:** Convert production features into typed diagnostic decisions.

The four-stage design separates instantaneous state, event evidence, duration
evidence, and final policy:

1. stage 50 creates eligibility and threshold states;
2. stage 60 constructs pedal-step event evidence;
3. stage 61 constructs persistent run episodes;
4. stage 70 applies result-state, confidence, DTC, sensor-trust, and routing
   rules.

The healthy reference run produces 1,471 decision rows across 14 executable
sub-checks with zero `triggered` or `pending` rows.

### 6. Synthetic Fault Injection (`fault_injection/`)

**Purpose:** Evaluate empirical response to controlled fault-like signal
perturbations without modifying frozen rules.

**Campaign:**

- 14 executable cases;
- three ordered severity points per case;
- three independent trips per severity;
- 42 end-to-end injected runs;
- 126 scoped observations;
- 14/14 cases satisfy the registered campaign acceptance criteria.

The runner verifies target-signal isolation, window eligibility, paired healthy
state, decision role, candidate DTC, emission semantics, severity monotonicity,
and strongest-point response.

**Documentation:** See
`fault_injection/fault_injection_methodology.md` and the Stage-4 sections of `proxy_failure/proxy_support.md`.

### 7. Pipeline Infrastructure (`pipeline_data/`)

**Purpose:** Provide shared artifact and continuity contracts across stages.

**Components:**

- `RunLayout`: canonical paths for every run artifact;
- manifests: ordered inputs/outputs, checksums, schema, and provenance;
- continuity helpers: trip/segment-safe grouping;
- contract lint: cross-document and cross-stage consistency checks;
- upload intake: fail-fast validation of one user-supplied CSV.

**Upload intake** (`upload_contract.py`) accepts a single uploaded file from the Dashboard and rejects unusable input before any run directory or pipeline stage is created. `run_pipeline.run_data_pipeline_for_upload(csv_path, ...)` is the callable entry point: it validates the upload, stages the file into a temporary directory, delegates to `run_data_pipeline`, and removes the staging directory afterwards. The returned summary carries `production_features_path` as an absolute path for downstream consumers.

Intake rules are evaluated in order and derived from `cleaning_config.yaml` so they cannot drift from the cleaning contract:

| Rule | Reason | Rejection code |
| ---- | ------ | -------------- |
| File keeps its original KIT name | The recording date exists only in the file name; the cleaned CSV carries time-of-day alone | `bad_filename` |
| All KIT source columns present | Cleaning cannot map absent signals | `missing_columns` |
| At least 700 data rows | Model window is 512 context + 96 forecast plus margin (INTERFACE.md §1.5) | `too_few_rows` |
| File parses as CSV | Empty, unreadable, or absent file | `unreadable_csv` |

Failures raise `UploadRejected` with a stable `code` and a user-readable message. Because validation precedes run creation, a rejected upload leaves no run artifacts behind.

---

## Dependencies

### Input

The online pipeline consumes raw KIT OBD-II CSV files containing timestamped
signals such as:

- coolant, intake, and ambient temperature;
- MAF and MAP;
- RPM and vehicle speed;
- accelerator-pedal channels;
- throttle-position context.

Signal availability, names, units, and cleaning policies are governed by the
cleaning configuration and feature contract.

### Output

The Data Layer produces two separate deliveries with different consumers.

**1. Production features — the principal Model Layer input.**

```text
data/processed/runs/<run_id>/features/41_production/production_features.csv
```

This is the artifact the Model Layer reads for TTM windowing and inference
(46 columns: 4 sample keys, 16 context/raw fields, 24 production features,
2 provenance fields; see `docs/INTERFACE.md` §1.1–1.3). Both pipeline entry
points return its absolute path as `production_features_path`.

**2. Proxy decisions — a separate offline delivery.**

```text
data/processed/runs/<run_id>/proxy/70_decisions/proxy_decisions.csv
```

Produced by the independent stage 50/60/61/70 chain, which is not part of `run_pipeline.py`. Per `docs/INTERFACE.md` §1.4 these labels are internal to the Model Layer and used only for (1) healthy-training-data filtering and (2) detection-evaluation ground truth. They are **not** used to train TTM and **do not** flow to the Report Layer or Dashboard.

Each executed decision carries:

- proxy and sub-check identity;
- trip/segment/episode scope;
- evidence timestamps;
- direction and decision role;
- result state and reason;
- decision margin;
- candidate DTC and emission flag;
- routing attribution and confidence.

### External Dependencies

- **Python packages:** pandas, NumPy, SciPy, scikit-learn, PyYAML, pytest
- **Project contracts:** `data_layer/contracts/feature_manifest.v1.json`
- **Frozen calibration:** `data_layer/calibration/calibration_registry.v1.json`
- **Shared interface:** project-level Model Layer handoff definitions

---

## How to Run

All commands must be executed from the repository root.

### Prerequisites

```powershell
# Activate the project environment if used
.\.venv\Scripts\Activate.ps1

# Install project dependencies
pip install -r requirements.txt
```

### Run the Online Data Pipeline

```powershell
python data_layer/run_pipeline.py --run-id run_20260724
```

Optional raw-input override:

```powershell
python data_layer/run_pipeline.py `
  --run-id run_20260724 `
  --input-dir D:\path\to\raw\csv
```

### Run the Pipeline for One Uploaded CSV

Called by the Dashboard rather than from the command line. The caller passes a path to a CSV already saved on disk; the file must keep its original KIT name.

```python
from data_layer.run_pipeline import (
    UploadRejected,
    run_data_pipeline_for_upload,
)

try:
    summary = run_data_pipeline_for_upload(
        "2019-05-06_Seat_Leon_Karlsruhe_Stuttgart_Normal.csv"
    )
    features_path = summary["production_features_path"]
except UploadRejected as exc:
    show_to_user(exc.code, str(exc))
```

### Rerun Proxy Stages for an Existing Run

```powershell
$runDir = "data/processed/runs/run_20260724"

python data_layer/proxy_failure/src/50_rule_state_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/60_event_evidence_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/61_duration_evidence_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/70_proxy_decision_builder.py --run-dir $runDir
```

### Run the Calibration Audit

```powershell
python data_layer/feature_engineering/src/90_calibration_registry_builder.py `
  --run-dir data/processed/runs/recalibrate_20260723
```

### Run Research Diagnostics

```powershell
python data_layer/feature_engineering/src/91_research_diagnostics_builder.py `
  --run-dir data/processed/runs/recalibrate_20260723 `
  --grid-scans `
  --bootstrap
```

### Run Synthetic Fault Injection

List configured cases:

```powershell
python data_layer/fault_injection/src/run_fault_injection.py --list-cases
```

Run the complete campaign:

```powershell
python data_layer/fault_injection/src/run_fault_injection.py `
  --base-run-id recalibrate_20260723
```

Run one case:

```powershell
python data_layer/fault_injection/src/run_fault_injection.py `
  --base-run-id recalibrate_20260723 `
  --only-case 1s2_coolant_overheat_high
```

### Run Tests

```powershell
# Data Layer tests
python -m pytest data_layer/tests -q

# Proxy and Stage-4 regression tests
python -m pytest `
  data_layer/tests/proxy_test/test_70_proxy_decisions.py `
  data_layer/tests/proxy_test/test_fault_injection_campaign.py `
  -q

# Style check
python -m flake8 data_layer
```

---

## Quality Assurance

### Validation Summary

| Check                                    | Result     |
| ---------------------------------------- | ---------- |
| Production rows                          | 249,694    |
| Trips / segments                         | 81 / 118   |
| Production columns                       | 46         |
| Executable proxy sub-checks              | 14         |
| Healthy decision rows                    | 1,471      |
| Healthy positive decisions               | 0          |
| Calibration reproduction                 | 48/48 PASS |
| Stage-4 observations                     | 126        |
| Stage-4 case acceptance                  | 14/14      |
| Proxy + Stage-4 focused regression tests | 20 passed  |
| Full Data Layer test suite               | 139 passed |

### Data-Integrity Controls

- key uniqueness and schema validation;
- trip/segment continuity isolation;
- manifest checksum verification;
- frozen-registry read-only policy;
- explicit `not_evaluable` reasons for guard/domain failures;
- no runtime fitting or candidate search;
- typed decision-role and emission semantics;
- target-signal-only fault intervention;
- healthy/injected paired comparison.

### Interpretation Controls

- candidate labels do not automatically authorize DTC emission;
- support and arbitration evidence remain non-emitting;
- non-executed research designs produce no runtime rows;
- synthetic detectability does not remove physical attribution ambiguity;
- decisions outside calibration or signal-quality domains remain
  `not_evaluable`.

---

## Remaining Work

Cross-layer items are recorded here so that decisions taken unilaterally by the Data Layer, and decisions still open, are visible to the other groups. Items marked **[blocking]** prevent the current end-to-end target.

### 1. Model Layer Handoff

The feature contract is frozen and its absolute path is exposed; the outstanding items are consumer-side.

| # | Item |
| - | ---- |
| M1 | **[blocking] Required-column contract.** `input_validation.GROUP1_REQUIRED_COLUMNS` still validates the 41-column INTERFACE v0.6 set. Thirteen of those columns were superseded by schema v1 and are no longer produced: `coolant_slope`, `coolant_stability`, `intake_temp_slope`, `maf_derived_air_load_raw`, `map_derived_air_load_raw`, `maf_map_cohesion`, `map_slope`, `pedal_throttle_gap`, `pedal_to_throttle_delay`, `tps_slope`, `accel_pedal_channel_ratio`, `idle_flag`, `idle_rpm_stability`. Feeding `production_features.csv` therefore fails validation. *Data Layer decision: the superseded columns are not reinstated (INTERFACE.md §1.3 is frozen); the Model Layer updates its required set to the v1 contract.* |
| M2 | **Cooling threshold migration.** The retired `coolant_slope` is scored in `calculate_risk` with hard-coded bounds `0.0333`/`0.1333`, derived specifically for its **°C/s** unit. Schema v1 provides no per-row coolant slope; its only ECT rate field, `ect_rate_180s`, uses a different window (180 s) **and** a different unit (**°C/min**). Choosing a replacement input is a Model Layer decision, but the existing bounds cannot be carried over unchanged — a direct substitution is a 60× scale error. The same applies to `maf_map_cohesion` and its `2.6` floor once intake scoring is in scope. |
| M3 | **[blocking] Default input path.** `kit_residual_detector.DEFAULT_INPUT_CSV` still points at the retired `data_layer/feature_engineering/feature_dataset.csv`. |
| M4 | **`run_model()` ownership.** The Data Layer exposes `production_features_path` only; wrapping inference in a callable `run_model()` belongs to the Model Layer. Any orchestrator should sit outside `data_layer/` so the Data Layer keeps no dependency on the Model Layer. *Inferred from the sprint specification; not yet confirmed cross-group.* |
| M5 | **No action needed.** The six TTM signals `rpm`, `speed`, `coolant_temp`, `map`, `maf`, `tps` are all present in the 46-column output, so forecasting itself is unaffected. |
| M6 | **Proxy delivery contract.** `docs/INTERFACE.md` §1.4 still describes the superseded `proxy_training_labels.csv` and duration window tables. The current delivery is `proxy_decisions.csv` from stages 50–70. Requires a cross-group contract update. |

### 2. Dashboard Handoff

| # | Item |
| - | ---- |
| D1 | **Entry point signature.** `run_data_pipeline_for_upload(csv_path, ...)` takes a filesystem path, not a Streamlit `UploadedFile`, so the Data Layer keeps no dependency on Streamlit. The Dashboard persists the uploaded object first and passes the path. *Data Layer design; awaiting Dashboard confirmation.* |
| D2 | **Rejection codes.** `UploadRejected.code` is one of `bad_filename`, `missing_columns`, `too_few_rows`, `unreadable_csv`; the exception message is already user-facing and may be displayed directly. *Data Layer design; awaiting Dashboard confirmation.* |
| D3 | **Original KIT file name required.** The recording date is parsed from the file name because the CSV carries time-of-day only, so a renamed file cannot be processed. The upload UI must state this. *Data Layer decision; not covered by the sprint specification, which constrains column names only.* |
| D4 | **Delivered.** KIT column and ≥700-row checks run fail-fast inside the Data Layer before any run directory is created. |

### 3. Performance and Storage

- profile memory and runtime for full-corpus stages;
- measure single-upload latency, which determines whether the interactive
  flow is viable as designed;
- reduce repeated CSV loading where contract-safe;
- define retention policy for large injected run directories.

---

## Troubleshooting

### Missing Run Artifact

**Error:** A stage reports a missing production feature, manifest, or upstream
evidence file.

**Solution:**

```powershell
# Confirm the run exists
Get-ChildItem data/processed/runs/<run_id>

# Run the complete online pipeline if required
python data_layer/run_pipeline.py --run-id <run_id>
```

Stages 50–70 require a completed feature run and verified manifests.

### Checksum Drift

**Error:** A stage reports that an artifact checksum differs from its manifest.

**Explanation:** The artifact was changed after its manifest was written, or files from different runs were mixed.

**Solution:** Two kinds of checksum exist and are handled differently.

*Run-artifact checksums* are written automatically by each stage. Never replace these by hand — regenerate the affected stage from its verified upstream artifact.

*Release checksums* in `calibration/calibration_registry.v1.manifest.json` freeze the authoritative documents (`feature_schema.md`, `proxy_failure_definition.md`, `proxy_support.md`, the registry, and the feature contract). When one of those documents legitimately changes, its hash **must** be refreshed in the same change, or `test_cross_contract_lint` fails:

```powershell
python -c "from data_layer.pipeline_data.manifests import sha256_file; print(sha256_file('data_layer/proxy_failure/proxy_support.md'))"
```

This refresh is deliberately manual: the frozen bundle exists so that a change to a controlled document is always acknowledged explicitly. Confirm the file uses LF line endings before hashing, otherwise the value will not match other platforms or CI.

### No Eligible Fault-Injection Window

**Error:** The Stage-4 runner reports fewer eligible independent windows than
the configured replicate count.

**Explanation:** The target rule's guard conditions are not sufficiently
represented in the selected base run.

**Solution:** Use a base run with the required operating opportunities or
reduce the registered replicate requirement explicitly. Do not alter unrelated
signals to manufacture eligibility.

### Target Run Already Exists

**Error:** `Target run already exists`.

**Explanation:** Fault-injection run IDs are immutable to prevent accidental
overwrite.

**Solution:** Supply a new `--run-prefix` or retain the existing run and
collect its recorded results.

### Import Error

**Error:** `ModuleNotFoundError` for a project package.

**Solution:**

```powershell
Set-Location <repository root>
$env:PYTHONPATH = "."
python data_layer/run_pipeline.py --run-id test_run
```

---

## Team & Contact

**Data Team:**

- Lei Pei
- Qiuting Fu

**Project:** Granite Lifeline
**Institution:** University of Bristol MSc Computer Science
**Sponsor:** IBM

For questions or contributions, refer to the main project README or the
authoritative Data Layer documents.

---

## References

- [Project README](../README.md) — overall system architecture
- [Feature schema](feature_engineering/feature_schema.md) — production feature definitions
- [Proxy failure definition](proxy_failure/proxy_failure_definition.md) — authoritative runtime rules
- [Proxy support](proxy_failure/proxy_support.md) — observability, calibration, and Stage-4 evidence
- [Fault-injection methodology](fault_injection/fault_injection_methodology.md) — formal experimental design
- [SAE J2012](https://www.sae.org/standards/content/j2012_201603/) — diagnostic trouble-code definitions
- [SAE J1979](https://www.sae.org/standards/content/j1979_201702/) — OBD-II PID definitions and bounds
- [CARB OBD II Regulations](https://ww2.arb.ca.gov/) — regulatory monitoring forms and enable-condition precedents
