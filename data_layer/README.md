# Data Layer

**Owner:** Data Team
**Status:** Completed
**Last Updated:** 2026-09-02

---

## Overview

The Data Layer is the first stage in the Granite Lifeline predictive maintenance pipeline. It transforms raw KIT OBD-II CSV files into cleaned, quality-audited, condition-labelled, feature-engineered data and versioned proxy-decision artifacts for Model Layer consumption.

```text
Raw OBD-II CSV → Cleaning → Operating Conditions → Feature Engineering → Proxy Decision Engine → Model Layer
```

The source corpus contains healthy driving rather than labelled component failures. Proxy rules are therefore derived from observable signal behaviour, anchored to physical and regulatory judgement forms, and calibrated against the healthy baseline. The repository also records an offline calibration audit and a controlled synthetic fault-injection campaign. Those artifacts test implementation behaviour under defined perturbations; they do not establish real-vehicle diagnostic accuracy.

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

## Delivery Status

All Data Layer components in the agreed repository scope are implemented. Here, **Completed** means that the code, versioned contracts, frozen reference artifacts, callable handoff interfaces, and repository tests are present. It does not imply validation against labelled real-world component failures.

| Component | Delivered result |
| --------- | ---------------- |
| Data cleaning and quality audit | Raw KIT CSV ingestion, timestamp normalization, 1 Hz output, bounded missing-value treatment, and quality/provenance artifacts |
| Operating-condition classification | Hierarchical `thermal_state` and `child_state` classification with confidence and quality fields |
| Feature engineering | Stages 00/10/20/30/40/41 and the frozen 46-column production schema |
| Calibration | Read-only registry plus a recorded 48/48 PASS reproduction audit |
| Research diagnostics | Recorded leave-one-trip-out, candidate-grid, and bootstrap artifacts |
| Proxy decision engine | Stages 50/60/61/70, covering 14 executable sub-checks and typed decision/DTC semantics |
| Synthetic fault injection | Recorded 14-case, 126-observation campaign with 14/14 conditional case acceptances |
| Artifact governance | Explicit `RunLayout`, stage manifests, SHA-256 verification, provenance, continuity helpers, and contract linting |
| Upload adapters | Single-file and multi-file callable entry points, fail-fast validation, unique-name protection, and post-cleaning usable-segment validation |
| Cross-layer handoff | Absolute production-feature and proxy-decision paths returned for the Model Layer and Dashboard integration |
| Automated verification | 148 collected Data Layer tests covering feature, pipeline-contract, proxy, upload, and fault-injection behaviour |
| Documentation | Data contracts, proxy definitions/support, injection methodology, operating-condition analysis, and the executable quality-assessment notebook |

Performance benchmarking, deployment sizing, and retention policy are operational concerns outside the completed functional Data Layer baseline; no latency, throughput, or production-scale claim is made here.

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

In this table, `pending` is a runtime decision state, not an implementation status.

### Technology Stack

| Component            | Technology                                      | Purpose                                             |
| -------------------- | ----------------------------------------------- | --------------------------------------------------- |
| Data Processing      | pandas, NumPy                                   | CSV processing, grouping, rolling statistics, deterministic transforms |
| Statistical Analysis | SciPy, scikit-learn                             | Distribution analysis and baseline linear models                       |
| Configuration        | YAML, JSON                                      | Cleaning rules, frozen calibration, fault-injection cases              |
| Contracts            | Python dataclasses and explicit JSON/CSV validation | Run layouts, manifests, artifact descriptors                        |
| Integrity            | SHA-256 manifests                               | Input/output verification and provenance                               |
| Testing              | pytest                                          | Unit, contract, fixture, integration, and regression tests             |

---

## Directory Structure

```text
data_layer/
├── README.md
├── run_pipeline.py                         # Batch, single-upload, and multi-upload entry points
├── calibration/
│   ├── calibration_registry.v1.json        # Frozen thresholds and routing
│   ├── calibration_registry.v1.manifest.json
│   └── calibration_audit_manifest.json     # Recorded Script-90 audit
├── contracts/
│   └── feature_manifest.v1.json            # Frozen production-feature contract
├── data_cleaning/
│   ├── quality_assessment_report.ipynb     # Read-only audit of the reference run
│   └── src/
├── operating_condition_statistics/
│   ├── operating_condition_analysis.md
│   └── src/
├── feature_engineering/
│   ├── feature_schema.md
│   └── src/                                # Stages 00/10/20/30/40/41 and Scripts 90/91
├── proxy_failure/
│   ├── proxy_failure_definition.md         # Authoritative executable rules
│   ├── proxy_support.md                     # Derivation and validation evidence
│   └── src/                                # Stages 50/60/61/70
├── fault_injection/
│   ├── fault_injection_methodology.md
│   ├── configs/fault_injection_cases.v1.json
│   ├── outputs/fault_injection_summary_20260903T051231Z.{csv,json}
│   └── src/run_fault_injection.py
├── research_diagnostics/                   # Recorded LOTO, grid, and bootstrap outputs
├── pipeline_data/                          # Paths, manifests, continuity, lint, upload contract
└── tests/
    ├── condition_label_crosscheck/
    ├── feature_engineering_test/
    ├── fixtures/
    ├── pipeline_data_test/
    └── proxy_test/
```

Runtime artifacts are stored under:

```text
data/processed/runs/<run_id>/
```

---

## Completed Components

### 1. Data Cleaning (`data_cleaning/src/`)

**Purpose:** Convert heterogeneous raw OBD-II CSV files into a consistent 1 Hz dataset while preserving explicit quality provenance.

**Features:**

- normalizes timestamp and signal fields;
- resamples within segment boundaries;
- applies column-specific missing-value strategies;
- prevents imputation across excessive gaps;
- records suspicious and hard-invalid source conditions;
- emits cleaning quality and report artifacts.

### 2. Operating-Condition Classification (`operating_condition_statistics/`)

**Purpose:** Describe the physical context in which proxy evidence is interpretable.

**States:**

- thermal: `engine_off`, `warmup`, `post_warmup`, `unknown`;
- child: `idle`, `steady_driving`, `acceleration`, `deceleration`,
  `high_load`, `inactive`, `unknown`.

Condition confidence and quality flags are retained as production inputs rather than being discarded after classification.

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

The four-stage design separates instantaneous state, event evidence, duration evidence, and final policy:

1. stage 50 creates eligibility and threshold states;
2. stage 60 constructs pedal-step event evidence;
3. stage 61 constructs persistent run episodes;
4. stage 70 applies result-state, confidence, DTC, sensor-trust, and routing
   rules.

The healthy reference run produces 1,471 decision rows across 14 executable sub-checks with zero `triggered` or `pending` rows.

### 6. Synthetic Fault Injection (`fault_injection/`)

**Purpose:** Evaluate empirical response to controlled fault-like signal perturbations without modifying frozen rules.

**Campaign:**

- 14 executable cases;
- three ordered severity points per case;
- three independent trips per severity;
- 42 end-to-end injected runs;
- 126 scoped observations;
- 14/14 cases satisfy the registered campaign acceptance criteria.

The runner verifies target-signal isolation, window eligibility, paired healthy state, decision role, candidate DTC, emission semantics, severity monotonicity, and strongest-point response.

**Documentation:** See
`fault_injection/fault_injection_methodology.md` and the Stage-4 sections of `proxy_failure/proxy_support.md`.

### 7. Pipeline Infrastructure (`pipeline_data/`)

**Purpose:** Provide shared artifact and continuity contracts across stages.

**Components:**

- `RunLayout`: canonical paths for every run artifact;
- manifests: ordered inputs/outputs, checksums, schema, and provenance;
- continuity helpers: trip/segment-safe grouping;
- contract lint: cross-document and cross-stage consistency checks;
- upload intake: fail-fast validation for single-file and multi-file requests.

**Upload intake** (`upload_contract.py`) validates each uploaded file before the pipeline starts. `run_data_pipeline_for_upload(csv_path, ...)` handles one recording, while `run_data_pipeline_for_uploads(csv_paths, ...)` validates a set of recordings and combines them into one run. The normal pipeline assigns trip order chronologically and preserves trip boundaries. By default, both upload paths enable proxy stages and return absolute `production_features_path` and `proxy_decisions_path` values.

Pre-run rules are derived from `cleaning_config.yaml` where applicable:

| Rule | Reason | Rejection code |
| --- | --- | --- |
| File keeps its original KIT name | The recording date exists only in the file name; the CSV contains time-of-day values | `bad_filename` |
| All required KIT source columns are present | Cleaning cannot map absent signals | `missing_columns` |
| At least 700 raw data rows are present | This is the intake contract's inexpensive size floor before cleaning | `too_few_rows` |
| Recording spans at least 700 seconds | Raw sampling varies, so row count alone does not establish usable duration | `too_few_rows` |
| File can be read as CSV | Missing, empty, unreadable, or invalidly encoded input cannot be processed | `unreadable_csv` |
| File names are unique within a multi-file request | Duplicate names would collide in the staging directory | `duplicate_upload_filenames` |

After cleaning, each upload run must contain at least one contiguous `segment_id` with 700 rows. Failure raises `no_usable_segment`; unlike a pre-run rejection, the run directory is retained for inspection. Missing or unparsable time values are left to the cleaning stage so it can report them with full context.

---

## Dependencies

### Input

The online pipeline consumes raw KIT OBD-II CSV files containing timestamped signals such as:

- coolant, intake, and ambient temperature;
- MAF and MAP;
- RPM and vehicle speed;
- accelerator-pedal channels;
- throttle-position context.

Signal availability, names, units, and cleaning policies are governed by the cleaning configuration and feature contract.

### Output

The Data Layer produces two separate deliveries with different consumers.

**1. Production features — the principal Model Layer input.**

```text
data/processed/runs/<run_id>/features/41_production/production_features.csv
```

This is the artifact the Model Layer reads for TTM windowing and inference (46 columns: 4 sample keys, 16 context/raw fields, 24 production features, 2 provenance fields; see `docs/INTERFACE.md` §1.1–1.3). The batch, single-upload, and multi-upload entry points return its absolute path as `production_features_path`.

**2. Proxy decisions — a decision-level delivery.**

```text
data/processed/runs/<run_id>/proxy/70_decisions/proxy_decisions.csv
```

Produced by the stage 50/60/61/70 chain. These stages run inside `run_pipeline.py` when `include_proxy` is set: the upload path enables them by default and returns `proxy_decisions_path`, while the batch and CLI paths stay feature-only unless `--include-proxy` is passed. The chain can still be rerun standalone against an existing run directory, which is how `run_fault_injection.py` uses it.

This decision-grain table is distinct from the superseded row-level proxy-label tables documented historically in `docs/INTERFACE.md` §1.4. The current Model Layer can consume it through its optional `--proxy-decisions` input and forward the already-computed verdicts for the two anomaly types it does not score itself. The decisions are not TTM training targets and do not flow to the Report Layer or Dashboard as labels.

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

# Install the core and local live-pipeline dependencies
pip install -r requirements.txt -r requirements-local.txt
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

The batch entry point stops at stage 41. Add `--include-proxy` to continue through the proxy stages in the same run:

```powershell
python data_layer/run_pipeline.py --run-id run_20260724 --include-proxy
```

### Run the Pipeline for Uploaded CSV Files

The upload APIs accept filesystem paths, not framework-specific upload objects. A Dashboard or other caller must save each upload first and retain its original KIT file name.

```python
from data_layer.run_pipeline import (
    UploadRejected,
    run_data_pipeline_for_upload,
    run_data_pipeline_for_uploads,
)

try:
    single = run_data_pipeline_for_upload(
        "2019-05-06_Seat_Leon_Karlsruhe_Stuttgart_Normal.csv"
    )
    history = run_data_pipeline_for_uploads(
        [
            "2019-05-06_Seat_Leon_Karlsruhe_Stuttgart_Normal.csv",
            "2019-05-07_Seat_Leon_Stuttgart_Karlsruhe_Normal.csv",
        ]
    )
    print(single["production_features_path"])
    print(single["proxy_decisions_path"])
except UploadRejected as exc:
    print(exc.code, str(exc))
```

Pass `include_proxy=False` to either adapter to stop at stage 41. Pipeline-stage failures surface as `DataPipelineError`, with the original exception retained as the cause.

### Run Proxy Stages for an Existing Feature Run

These stages write into the selected run directory. Use a non-frozen run; do not point exploratory commands at the committed reference run.

```powershell
$runDir = "data/processed/runs/run_20260724"

python data_layer/proxy_failure/src/50_rule_state_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/60_event_evidence_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/61_duration_evidence_builder.py --run-dir $runDir
python data_layer/proxy_failure/src/70_proxy_decision_builder.py --run-dir $runDir
```

### Reproduce the Calibration Audit

The committed audit is already frozen. Run this only when intentionally reproducing it; use `--output` to avoid replacing the tracked manifest during an exploratory check.

```powershell
python data_layer/feature_engineering/src/90_calibration_registry_builder.py `
  --run-dir data/processed/runs/recalibrate_20260723 `
  --output path/to/calibration_audit_manifest.json
```

### Reproduce Research Diagnostics

Script 91 writes to the tracked `data_layer/research_diagnostics/` location. Do not rerun it merely to consume the committed results; use it only for an intentional regeneration.

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
| Healthy `triggered` / `pending` decisions | 0 / 0      |
| Calibration reproduction                 | 48/48 PASS |
| Stage-4 observations                     | 126        |
| Stage-4 conditional case acceptance      | 14/14      |
| Proxy + Stage-4 focused regression tests | 20 passed  |
| Full Data Layer test suite               | 148 passed |

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

## Delivered Interfaces and Scope Boundaries

The Data Layer handoff is complete at the repository interfaces defined in
`docs/INTERFACE.md`:

| Boundary | Completed Data Layer responsibility |
| --- | --- |
| Model Layer | Produce the frozen 46-column `production_features.csv` contract and, when proxy stages are enabled, the separate decision-grain `proxy_decisions.csv`; expose both as absolute paths in the run summary |
| Dashboard | Provide single-file and multi-file path-based upload adapters with stable `UploadRejected.code` values; the Dashboard persists uploads and calls these adapters |
| Report Layer | Supply data through the Model Layer boundary; proxy labels are not sent directly to the Report Layer or Dashboard as training labels |

The Dashboard integration calls both upload adapters and forwards `proxy_decisions_path` when present. The Model Layer interface records the
46-column production schema and forwarding of the two proxy-scored anomaly types. These downstream implementations remain owned by their respective layers; they are evidence that the Data Layer handoff is connected, not additional Data Layer functionality.

Completion does not change the evidence limits: the reference corpus is healthy driving, proxy thresholds are frozen engineering rules, and the
fault-injection campaign uses synthetic target-signal perturbations. Results must therefore be described as contract and detectability checks within the registered protocol, not as measured field failure rates or certified vehicle diagnostics.

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

### Upload Rejected as `no_usable_segment`

**Error:** An upload completes the pipeline but is rejected because no contiguous segment reaches 700 rows.

**Explanation:** The recording was interrupted repeatedly, so the cleaning stage split it into short segments. Forecast windows never cross a segment boundary, so total length does not help — one uninterrupted stretch must be long enough. This is expected behaviour, not a fault: one trip in the reference corpus (731 s over 7 segments, longest 593 rows) fails exactly this way.

**Solution:** Use a recording with a longer continuous drive. The run directory is kept and named in the message, so the segment layout can be inspected:

```powershell
python -c "import pandas as pd; d=pd.read_csv(r'data/processed/runs/<run_id>/features/41_production/production_features.csv', usecols=['segment_id']); print(d.groupby('segment_id').size())"
```

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

**Error:** The Stage-4 runner reports fewer eligible independent windows than the configured replicate count.

**Explanation:** The target rule's guard conditions are not sufficiently represented in the selected base run.

**Solution:** Use a base run with the required operating opportunities or reduce the registered replicate requirement explicitly. Do not alter unrelated signals to manufacture eligibility.

### Target Run Already Exists

**Error:** `Target run already exists`.

**Explanation:** Fault-injection run IDs are immutable to prevent accidental overwrite.

**Solution:** Supply a new `--run-prefix` or retain the existing run and collect its recorded results.

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

For questions or contributions, refer to the main project README or the authoritative Data Layer documents.

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
