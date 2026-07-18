# Model Layer

**Owner:** Model Team
**Status:** Active Development
**Last Updated:** 2026-07-18

---

## Overview

The Model Layer is the second stage in the Granite Lifeline predictive
maintenance pipeline. It consumes the Data Layer's feature-engineered
CSV, runs it through IBM Granite TTM (Tiny Time Mixer) zero-shot
forecasting, and turns the gap between predicted and actual sensor
behavior into a scored, named anomaly for the Report Layer.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Core Responsibilities

1. **Input Validation**: Load and validate Data Layer's `feature_dataset.csv` against the agreed column contract
2. **Zero-Shot Forecasting**: Predict 96 seconds of six engine signals from 512 seconds of context using Granite TTM, with no fault examples required
3. **Residual Scoring**: Turn forecast-vs-actual gaps into normalized, healthy-baseline-calibrated risk scores
4. **Anomaly Attribution**: Combine residuals with physically-grounded rules to name the most likely anomaly type
5. **Output Contract**: Emit `ModelLayerOutput` JSON validated against `docs/INTERFACE.md`

There is no labelled fault data in the KIT dataset — all 81 trips are
healthy driving. Rather than training a fault classifier, the detector
learns what *normal* looks like (zero-shot, pre-trained) and flags
sustained drift away from that as the anomaly signal. See
`docs/viva/model_challenge.md` for the full rationale, evaluation plan,
and Q&A.

### Anomaly Types

- **cooling_degradation**: Elevated or steadily rising coolant temperature
- **air_intake_maf_anomaly**: MAF/MAP air-load disagreement (dirty filter, vacuum leak, sensor drift)
- **accelerator_pedal_sensor**: Disagreement between the two redundant pedal-position channels
- **intake_air_temperature_sensor_or_heat_soak_fault**, **map_load_signal_plausibility_fault**, **idle_speed_control_or_surge_degradation**: Data Layer-defined (theory delivered in `data_layer/proxy_failure/proxy_support.md` §4–6); registered as 0.0-score placeholders pending scoring logic. Their synthetic injection scenarios are already implemented and swept (see Story 7 below)

---

## Current Implementation Status

Tracked internally as Stories 1–8 (Story 9 is group-report writing, not
pipeline work, and is omitted here). Story 7 is tracked in Jira as
GL-234 with per-subtask tickets (GL-235–239, GL-292–298).

### [COMPLETED]

| Component | Story | Description |
|-----------|-------|--------------|
| Proxy Failure Research & Healthy Baseline | Story 1 (GL-31) | Define the 3 confirmed anomaly types with physical rationale; per-signal healthy baseline statistics from KIT normal trips |
| Zero-Shot TTM Detector MVP | Story 2 (GL-67) | End-to-end Granite TTM forecast → residual → risk score → interface JSON, first working on raw KIT CSVs |
| Standard JSON output hardening | Story 3 (GL-142) | Two-tier input validation, `notes` field, `accelerator_pedal_sensor` graceful fallback, committed sample output, `validate_output.py` |
| Automated data quality checks | Story 4 (GL-149) | Mock Group 1 fixtures, CSV consumption tests, model-input contract tests (41-column schema, TTM window length) |
| Pipeline Switch to `feature_dataset.csv` | Story 5 (GL-160) | Detector consumes Data Layer's output directly; internal feature computation removed; `electronic_throttle_tracking_fault` dropped; `coolant_slope` rescaled °C/min → °C/s; INTERFACE.md updated to v0.8/v0.9 |

### [IN PROGRESS]

| Component | Story | Status |
|-----------|-------|--------|
| Fine-Tuning on Healthy KIT Data | Story 6 | Data prep done (segment eligibility check, seeded 80/20 train/validation split by trip); fine-tuning script, training run, and zero-shot-vs-fine-tuned comparison table not yet started |
| Failure Estimation | Story 8 | `trip_id`/cycle-index column agreed with Data Layer; risk-history collection/persistence, batch-mode sweep, trend extrapolation, and probability mapping not yet implemented — `estimated_cycles_to_failure`/`estimated_failure_probability` still emit as `null` |
| Planted-Fault Evaluation | Story 7 | Injection functions for all six anomaly types and the evaluation runner are done; zero-shot sweep recorded in `outputs/synthetic_eval_results.json` (16 validation segments × healthy control + 6 fault scenarios, plus an idle-targeted window pair). Implemented-type results: cooling 16/16 detected at risk 1.0, `maf × 0.7` 1/16, `map × 1.25` 7/16 at current thresholds. The three pending-type scenarios (frozen `intake_temp`, frozen `map`, idle rpm offset+oscillation) are recorded as a pre-scoring baseline — they cannot fire until their scoring logic lands. Precision/recall table, `risk_level` threshold calibration, pending-type scoring, and the evaluation note remain; sweep to be re-run after scoring lands and again on the Story 6 fine-tuned model |

### [PLANNED]

| Component | Priority | Description |
|-----------|----------|-------------|
| Pending Anomaly Type Scoring | P1 | Score the 3 placeholder types from the Data Layer's delivered decision rules (`proxy_failure/proxy_support.md` §4–6 Stage 3); their synthetic scenarios are already in the evaluation sweep. Note: the rules reference `intake_temp_stability`/`map_stability`, which are not delivered columns — compute in-window rolling stds or request them from the Data Layer |
| CI Integration | P1 | `model_layer/ttm-related/tests/` is not yet wired into CI (CI currently only runs root `tests/test_interface.py`) |
| `AnomalyType` Enum Drift Fix | P2 | `shared/interface_models.py`'s enum still has the old short name `intake_air_temperature_sensor_fault` and hasn't dropped `electronic_throttle_tracking_fault` — see Known Issues |

---

## Architecture

### Data Flow

```
feature_dataset.csv (from Data Layer)
    ↓
load_group1_features() — required-column + numeric-type validation
    ↓
select_segment() — pick one segment, ≥700 rows, never crosses a boundary
    ↓
prepare_segment() — two-tier plausibility repair + interpolation
    ↓
select_context_and_truth() — split into 512-step context / 96-step future
    ↓
run_ttm_forecast() — Granite TTM zero-shot forecast (6 signals, z-score normalized)
    ↓
calculate_residuals() / summarize_residuals() — |prediction − actual| per signal
    ↓
calculate_risk() — normalize residuals vs healthy baseline + rule-based attribution
    ↓
build_interface_json() — assemble ModelLayerOutput
    ↓
validate_output() — check against docs/INTERFACE.md contract
    ↓
ModelLayerOutput (to Report Layer)
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Forecasting Model | IBM Granite TTM (`ibm-granite/granite-timeseries-ttm-r2`) | Zero-shot multivariate time-series forecasting |
| Model Toolkit | `granite-tsfm` (`tsfm_public`) | Loads/configures the TTM checkpoint |
| ML Framework | PyTorch, `transformers` | Model execution |
| Data Handling | pandas, numpy | CSV loading, windowing, residual math |
| Data Contracts | Pydantic (`shared/interface_models.py`) | Type-safe `ModelLayerOutput` |

---

## Directory Structure

```
model_layer/
├── identify_anomoly/                      # Proxy anomaly-type research (Story 1, GL-31)
│   ├── failure_type_research.md           # Healthy-baseline stats + anomaly-type definitions
│   └── image/                              # Supporting plots (coolant warm-up, correlation heatmap)
└── ttm-related/                            # Pipeline code
    ├── requirements.txt                    # ML-specific dependencies (torch, granite-tsfm, ...)
    ├── outputs/
    │   ├── kit_residual_sample.json        # Committed sample ModelLayerOutput
    │   └── synthetic_eval_results.json     # Story 7 planted-fault sweep results (zero-shot)
    ├── src/model/
    │   ├── data_simulator.py               # OBDDataSimulator — synthetic fault sequences for offline testing
    │   ├── download_ttm.py                 # One-off script to cache the TTM checkpoint from Hugging Face
    │   ├── fault_injection.py              # Story 7 synthetic fault perturbations, all six anomaly types (raw signals + derived-feature propagation)
    │   ├── input_validation.py             # Two-tier range validation + Group 1 required-column contract
    │   ├── kit_residual_detector.py        # Main pipeline: CSV → TTM forecast → residuals → risk scoring → JSON
    │   ├── prepare_finetune_split.py       # Story 6 data prep: eligibility check + seeded train/val split manifest
    │   ├── run_synthetic_evaluation.py     # Story 7 sweep: validation segments × (healthy + 6 faults, incl. idle-targeted window pair) → results JSON
    │   └── validate_output.py              # Validates output JSON against docs/INTERFACE.md
    └── tests/
        ├── group1_fixtures.py               # Shared pytest fixtures — mock Group 1 feature_dataset.csv builder
        ├── test_basic.py                    # Import/data-simulator/model-loading smoke tests
        ├── test_fault_injection.py          # Injection math, cohesion recomputation, plausibility survival
        ├── test_group1_consumption.py       # CSV loading, segment selection, bad-input handling
        ├── test_input_validation.py         # Range validation, pedal fallback, build_interface_json
        ├── test_model_input_contract.py     # Story 4 model-input contract checks
        ├── test_prepare_finetune_split.py   # Trip row counts, partitioning, seeded split, manifest
        └── test_validate_output.py          # Output-schema validator correctness
```

No `docs/adr/`, `evaluation/`, or trained-model `artifacts/` directory
exists yet under `model_layer/` (`artifacts/*` is gitignored, reserved
for a future fine-tuned checkpoint from Story 6).

---

## Completed Components

### 1. Zero-Shot Residual Detector (`ttm-related/src/model/kit_residual_detector.py`)

**Purpose:** Consume Data Layer's `feature_dataset.csv` directly and produce a `ModelLayerOutput`-shaped JSON with no internal feature engineering.

**Key constants:** `MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"`, `DEFAULT_CONTEXT_LENGTH = 512`, `DEFAULT_PREDICTION_LENGTH = 96`, `MIN_SEGMENT_ROWS = 700`, `MODEL_SIGNALS = ["rpm", "speed", "coolant_temp", "map", "maf", "tps"]`, `REFERENCE_RANGES` (healthy 5th–95th percentile bands per feature).

**Pipeline functions:**
- `load_group1_features(csv_path) -> pd.DataFrame` — required-column + numeric-type validation
- `select_segment(df, trip_id=None, segment_id=None, min_rows=700) -> pd.DataFrame` — one contiguous segment so TTM windows never cross a boundary
- `prepare_segment(segment) -> (df, notes)` — two-tier plausibility repair + interpolation
- `select_context_and_truth(df, context_length, prediction_length) -> (context, future)` — splits into 512-row context + 96-row ground truth
- `run_ttm_forecast(context, context_length, prediction_length, model=None) -> pd.DataFrame` — z-score normalizes the 6 model signals, runs the TTM forward pass, de-normalizes
- `calculate_residuals(prediction, truth) -> pd.DataFrame` — absolute error per signal
- `calculate_risk(residual_summary, future, notes) -> (anomaly_type, risk_score, confidence, top_signals, notes)` — rule-based scoring/attribution across all 6 anomaly types
- `build_interface_json(...) -> dict` — assembles the final `docs/INTERFACE.md`-shaped JSON

**Risk scoring rules** (`calculate_risk`):
- **cooling_degradation**: coolant temp residual, coolant temp > 95–110°C, or sustained coolant slope 0.0333–0.1333°C/s (2–8°C/min) once warmed past 85°C
- **air_intake_maf_anomaly**: MAF/MAP residuals, or window-median `maf_map_cohesion` z-score 2.6–4.0
- **accelerator_pedal_sensor**: window-mean `accel_pedal_channel_delta` 2–10 percentage points; forced to 0.0 with a note when pedal channels are unavailable
- Three pending types are fixed at 0.0 pending Data Layer's theory write-up for their key signals

**Confidence:** `max(0.35, min(0.95, 1 − std(normalized_residual_scores)))` — a heuristic spread measure, not a model-native probability.

**CLI:**
```bash
python model_layer/ttm-related/src/model/kit_residual_detector.py \
    [csv_path] [--trip-id ID] [--segment-id ID] \
    [--context-length 512] [--prediction-length 96] [--output PATH]
```
Defaults to `data_layer/feature_engineering/feature_dataset.csv` and the first segment with ≥700 rows.

**Sample output** (`ttm-related/outputs/kit_residual_sample.json`):
```json
{
  "timestamp": "2017-07-05T05:26:37Z",
  "anomaly_type": "cooling_degradation",
  "risk_score": 1.0,
  "risk_level": "High",
  "component": "cooling_degradation",
  "prediction_confidence": 0.6534,
  "key_signals": [
    {"feature": "coolant_temp", "value": 80.0, "unit": "°C", "reference_range": [90, 95]},
    {"feature": "coolant_slope", "value": 0.0729, "unit": "°C/s", "reference_range": [0, 0.0333]}
  ],
  "estimated_cycles_to_failure": null,
  "estimated_failure_probability": null,
  "notes": []
}
```

### 2. Input Validation (`ttm-related/src/model/input_validation.py`)

**Purpose:** Two-tier range checking so obviously broken sensor data is caught early, without deleting the very anomalies the detector is designed to find.

**`PLAUSIBLE_RANGES`**: wide, sensor-physical-limit bounds (e.g. `coolant_temp: [-40, 150]`, `rpm: [0, 8000]`) — deliberately wider than the healthy-baseline `REFERENCE_RANGES` in the detector, so merely *unusual* values pass through untouched.

**`GROUP1_REQUIRED_COLUMNS`**: the full 41-column Data Layer contract (10 identity/condition fields, 10 raw signals, 21 engineered features) matching `docs/INTERFACE.md` Section 1.

**Functions:**
- `validate_required_columns(columns, required, source)` — raises `ValueError` naming every missing column
- `validate_sensor_ranges(df, ranges=None, max_bad_fraction=0.05) -> ValidationResult` — implausible cells become `NaN` + a repair note; a column is rejected outright if more than 5% of its rows are implausible or it is entirely `NaN`

### 3. Output Validation (`ttm-related/src/model/validate_output.py`)

**Purpose:** Schema/type/enum/range linter for `docs/INTERFACE.md` — checks the output contract only, not whether a reading is healthy.

Checks: all required fields present; `timestamp` ISO-8601 parseable; `anomaly_type` in the 6-value enum; `risk_score`/`prediction_confidence` in `[0, 1]`; `component == anomaly_type`; `key_signals` shape (`feature`, `value`, `unit`, `reference_range` with low ≤ high); `estimated_cycles_to_failure` null or non-negative int; `estimated_failure_probability` null or `[0, 1]`; `notes` is a list of strings.

```bash
python model_layer/ttm-related/src/model/validate_output.py \
    model_layer/ttm-related/outputs/kit_residual_sample.json
```

### 4. Synthetic Data Simulator (`ttm-related/src/model/data_simulator.py`)

**Purpose:** `OBDDataSimulator(sequence_length=100, sampling_rate=1.0)` generates synthetic OBD-II sequences for offline testing, independent of the real KIT data.

**Generators:** `generate_normal_sequence()`, `generate_cooling_degradation()` (sustained coolant rise post-warmup), `generate_air_intake_maf_anomaly(variant="low_maf"|"map_bias")`, `generate_pedal_sensor_fault()` (sustained channel-E drop).

### 5. Planted-Fault Injection & Evaluation Runner (`fault_injection.py`, `run_synthetic_evaluation.py`)

**Purpose:** Story 7 evaluation — plant known faults in healthy segments and record whether the detector names them. Covers all six anomaly types.

**Implemented-type scenarios** (per the Data Layer's `proxy_failure/proxy_support.md` Stage 4 designs): `inject_cooling_fault()` = `coolant_temp + 15°C` sustained offset → `cooling_degradation`; `inject_intake_maf_fault("low_maf")` = `maf × 0.7` gain drift → `air_intake_maf_anomaly`; `inject_intake_maf_fault("map_bias")` = `map × 1.25` — a cohesion-attribution test outside the Stage 4 MAF design (which injects on `maf` only), expected label still `air_intake_maf_anomaly`.

**Pending-type scenarios** (per `proxy_support.md` §4–6 Stage 4 TBD-1): `inject_intake_air_temp_fault()` = `intake_temp` frozen at fault onset → `intake_air_temperature_sensor_or_heat_soak_fault`; `inject_map_plausibility_fault()` = `map` frozen at onset (stuck signal; also suppresses any pedal-step response in the window) → `map_load_signal_plausibility_fault`; `inject_idle_speed_fault()` = `rpm + 250` offset plus a 100 rpm sine at 0.125 Hz, applied to `idle_flag == 1` rows only → `idle_speed_control_or_surge_degradation`.

**Design:** perturbations are applied to the raw signals and propagated into the engineered columns that are exact functions of them — verified on the delivered dataset (reconstruction error ≤ 5e-7): `maf_derived_air_load_raw = 60·maf/rpm`, `map_derived_air_load_raw = map·rpm/(intake_temp + 273.15)`, `maf_map_cohesion = |z(maf_load) − z(map_load)|` with the z-parameters from `data_layer/feature_engineering/feature_baselines.json`, `intake_ambient_delta = intake_temp − ambient_temp`, slopes as per-segment `diff/dt_seconds`, `speed_density_maf_residual` from the linear regression published in `feature_baselines.json` (`models.speed_density_model`, inputs clipped to its winsorize bounds), and `idle_rpm_stability` as a 30-sample rolling std of rpm restricted to idle rows. Recomputed columns keep the delivered NaN mask. A frame with a faulty `maf` but healthy cohesion could never come out of the Data Layer pipeline.

**Runner:** sweeps the Story 6 validation split (17 segments; one skipped — never reaches `post_warmup`) × healthy control + 6 fault scenarios on the zero-shot model. Each segment is evaluated on its first 512+96 window starting at the first `post_warmup` row (the proxy conditions are defined post-warm-up; cold-start windows saturate cooling risk even on healthy data), with fault onset at the context/future boundary so the fault is unseen in the TTM context. The idle scenario is the exception: its injection only touches idle rows, so it runs (with a paired `healthy_idle_window` control) on the first window whose future rows hold ≥ 10 idle rows — 15/16 segments qualify; the rest get a per-scenario skip record. Each record carries `window_start_row`, `future_idle_rows`, and `future_sustained_flow_rows` for the analysis half.

```bash
# From the repository root
python model_layer/ttm-related/src/model/run_synthetic_evaluation.py \
    [--segments validation|all] [--output outputs/synthetic_eval_results.json]
```

**Current results** (zero-shot, pre-calibration): cooling 16/16 at risk 1.0 (High); `maf × 0.7` 1/16 and `map × 1.25` 7/16 — the ~0.8 cohesion shift stays below the current 2.6 trigger floor, which is the direct input to the pending threshold-calibration work; healthy controls mean risk 0.29 (5/16 read Medium). The three pending-type scenarios record 0 detections by construction — their types still score 0.0 in `calculate_risk` — so this sweep is the pre-scoring baseline to re-run once their scoring logic lands.

### 6. Fine-Tune Data Prep (`ttm-related/src/model/prepare_finetune_split.py`)

**Purpose:** Story 6 data-prep utility — builds the healthy-trip train/validation split manifest that the (not-yet-written) fine-tuning trainer will consume.

**Functions:** `trip_row_counts(df)`, `partition_trips(counts, min_rows=700)`, `split_trips(trip_names, train_fraction=0.8, seed=42)` (deterministic), `build_manifest(df, ...)`.

### 7. Proxy Anomaly-Type Research (`identify_anomoly/failure_type_research.md`)

**Purpose:** Documents the physical rationale for the 3 confirmed anomaly types and validates the "all 81 trips are healthy" assumption underlying zero-shot training.

Includes: per-type signal-deviation tables and physical logic; a Data Health Validation Summary (81 raw files → 66 healthy Normal/Frei baseline trips, 2,089,290 rows); a Healthy Baseline Reference Table (mean/std/P5/P95/median/P99/min/max per signal, checked against SAE J1979 and manufacturer ranges); references to the Bosch Automotive Handbook, SAE J1979, and supporting academic literature.

### 8. Test Suite (`ttm-related/tests/`)

104 tests across 7 modules:

| File | Coverage |
|------|----------|
| `test_basic.py` | Import smoke test, data-simulator smoke test, TTM model-loading smoke test |
| `test_fault_injection.py` | All six injectors: offsets/gains/frozen values from fault onset only, propagation math (cohesion, slopes, air loads, speed-density residual, idle rpm stability), idle-rows-only application, NaN policy preservation, no input mutation, injected values survive plausibility repair, runner helpers (post-warmup trim, manifest segment selection, idle-window search) |
| `test_group1_consumption.py` | CSV loading/consumption, segment selection across multi-segment/multi-trip frames, segment-safe windowing, bad trip/segment-id handling |
| `test_input_validation.py` | Range validation (repair, rejection, all-NaN, plausible-vs-healthy guard), pedal fallback, `build_interface_json` shape |
| `test_model_input_contract.py` | All 41 required columns present, model signals numeric/non-null, engineered features within contract ranges, sufficient rows for the 512+96 window |
| `test_prepare_finetune_split.py` | Trip row counts, eligible/excluded partitioning, seeded deterministic split, manifest building |
| `test_validate_output.py` | Valid output passes; missing field, bad enum, `component != anomaly_type`, out-of-range scores, key_signals/notes shape all caught |

```bash
cd model_layer/ttm-related
../../.venv/bin/python -m pytest tests -v
```

---

## Dependencies

### Input: Data Layer Output

Consumes `DataLayerOutput` (`shared/interface_models.py`) — 41 columns: identity/time/operating-condition fields (`timestamp`, `trip_id`, `segment_id`, `row_in_segment`, `dt_seconds`, `thermal_state`, `child_state`, `operating_state`, `condition_confidence`, `condition_quality_flags`), 10 raw signals (`coolant_temp`, `map`, `rpm`, `speed`, `intake_temp`, `maf`, `tps`, `ambient_temp`, `accel_pedal_d`, `accel_pedal_e`), and engineered features (`coolant_slope`, `coolant_ambient_delta`, `coolant_stability`, `intake_ambient_delta`, `intake_temp_slope`, `maf_map_cohesion`, `map_slope`, `accel_pedal_channel_delta`, `rpm_slope`, `idle_flag`, `idle_rpm_stability`, and others). See `docs/INTERFACE.md` Section 1 for complete field definitions.

### Output: Model Layer Output

Produces `ModelLayerOutput` for Report Layer consumption:

```python
class ModelLayerOutput(BaseModel):
    timestamp: str
    anomaly_type: AnomalyType           # Literal enum, 6 values
    risk_score: float                   # 0.0 - 1.0
    risk_level: Optional[str]           # "Low" | "Medium" | "High"
    component: AnomalyType              # Mirrors anomaly_type
    prediction_confidence: float        # 0.0 - 1.0
    key_signals: List[KeySignal]        # {feature, value, unit, reference_range}
    estimated_cycles_to_failure: Optional[int]         # None until Story 8
    estimated_failure_probability: Optional[float]     # None until Story 8
    notes: List[str]                    # Empty list if no messages
```

See `docs/INTERFACE.md` Section 2 for complete field definitions.

> **Known issue:** the `AnomalyType` enum in `shared/interface_models.py` has drifted from `docs/INTERFACE.md` v0.9 and `validate_output.py` — it still uses the short name `intake_air_temperature_sensor_fault` (should be `intake_air_temperature_sensor_or_heat_soak_fault`) and has not dropped `electronic_throttle_tracking_fault`, which was removed from the interface on 2026-07-13. Needs a follow-up fix so the shared Pydantic model matches the actual contract.

### External Dependencies

- **Python Packages (`model_layer/ttm-related/requirements.txt`):** `torch==2.10.0`, `transformers==4.57.6`, `granite-tsfm==0.3.6`, `accelerate`, `pandas`, `numpy`, `scikit-learn`, `datasets`, `huggingface_hub`
- **Root `requirements.txt`** (what CI actually installs): `pydantic>=2.0.0,<3.0.0`, `pytest>=7.4.0`, `flake8>=6.1.0`
- **Hugging Face:** Granite TTM checkpoint is downloaded once (`download_ttm.py`) and cached locally; no committed model artifact

---

## How to Run

All commands assume the ML-specific dependencies are installed.

### Prerequisites

```bash
# Python 3.11-3.13 recommended (TTM/granite-tsfm compatibility)
cd model_layer/ttm-related
pip install -r requirements.txt

# One-time: download and cache the Granite TTM checkpoint
python src/model/download_ttm.py
```

### Run the Detector

```bash
# From model_layer/ttm-related, against the default Data Layer output
python src/model/kit_residual_detector.py

# Or explicitly choose a CSV / segment / output path
python src/model/kit_residual_detector.py \
    ../../data_layer/feature_engineering/feature_dataset.csv \
    --segment-id trip_0001_seg_001 \
    --output outputs/result.json
```

### Validate an Output JSON

```bash
python src/model/validate_output.py outputs/kit_residual_sample.json
```

### Prepare the Fine-Tune Split Manifest (Story 6)

```bash
python src/model/prepare_finetune_split.py --input path/to/combined_healthy.csv --output outputs/finetune_split_manifest.json
```

### Run Tests

```bash
# From model_layer/ttm-related
../../.venv/bin/python -m pytest tests -v
```

---

## Quality Assurance

There is no weighted evaluation framework yet comparable to Report
Layer's `model_comparison.py` — Story 7's planted-fault evaluation
now has a recorded zero-shot sweep (`outputs/synthetic_eval_results.json`);
the precision/recall table and threshold calibration on top of it are
pending; see Remaining Work below.

### Compliance Checklist

All generated outputs must satisfy:

- ✅ **Interface compliance**: `validate_output.py` passes against `docs/INTERFACE.md`
- ✅ **Segment safety**: TTM windows never cross a `segment_id` boundary
- ✅ **Two-tier validation**: implausible values repaired/rejected; merely unusual values pass through untouched
- ✅ **Flake8 clean**: CI lints the whole repo including `model_layer/`
- ⬜ **Precision/recall on planted faults**: raw sweep recorded (Story 7); table + threshold calibration pending

---

## Remaining Work

**1. Fine-Tuning Trainer** (Story 6, P0)
- Write the fine-tuning script using the `tsfm_public` trainer API
- Run training on the healthy-segment split, save the model artifact + config
- Produce a zero-shot-vs-fine-tuned residual comparison table on held-out trips

**2. Planted-Fault Evaluation — analysis half** (Story 7, P0)
- Compute the precision/recall table from `outputs/synthetic_eval_results.json`, extended to all six anomaly types once their scoring lands
- Calibrate final `risk_level` thresholds (the recorded intake under-detection is the calibration input)
- Write the evaluation note stating the synthetic-only and single-vehicle-calibration limitations explicitly
- Re-run the sweep once the pending-type scoring lands, and again once the Story 6 fine-tuned artifact lands

**3. Failure Estimation** (Story 8, P1)
- Implement risk-score-history collection/persistence (`{trip_id, window_id, timestamp, risk_score}`)
- Add input validation for the history structure
- Add a batch mode that sweeps all eligible segments/windows in one invocation (needed for Dashboard integration)
- Implement trend extrapolation → `estimated_cycles_to_failure`, and probability mapping → `estimated_failure_probability`
- Refresh the committed sample output and validator with real (non-null) values

**4. Pending Anomaly Types** (P1)
- Score `intake_air_temperature_sensor_or_heat_soak_fault`, `map_load_signal_plausibility_fault`, `idle_speed_control_or_surge_degradation` from the Data Layer's delivered decision rules (`proxy_failure/proxy_support.md` §4–6 Stage 3); their synthetic scenarios are already implemented and swept as the pre-scoring baseline
- The Stage 3 rules reference `intake_temp_stability`/`map_stability`, which are not delivered columns — compute in-window rolling stds from raw `intake_temp`/`map` (analogous to `coolant_stability`) or request the columns from the Data Layer

**5. CI Integration** (P1)
- Wire `model_layer/ttm-related/tests/` into CI (currently only `tests/test_interface.py` runs)

**6. Known Issue Fix** (P2)
- Reconcile the `AnomalyType` enum in `shared/interface_models.py` with `docs/INTERFACE.md` v0.9

### Future Enhancements

- Report ranked scores for all anomaly types, not just the top one (raised in viva Q&A; deferred to keep the output contract stable mid-project)
- Test against a genuinely labelled external fault dataset
- Gradual, realistic fault injection instead of step-change perturbations
- Transfer-test on a second vehicle's data

---

## Troubleshooting

### TTM Model Download Fails

**Issue:** `download_ttm.py` cannot fetch or load the checkpoint.

**Solution:**
```bash
# Verify Python version (3.11-3.13 recommended)
python --version

# Reinstall granite-tsfm and transformers
pip install --force-reinstall granite-tsfm transformers

# Retry the download/cache step
python model_layer/ttm-related/src/model/download_ttm.py
```

### `ModuleNotFoundError: No module named 'torch'` (or `pandas`/`numpy`)

**Solution:**
```bash
# Ensure the ML-specific requirements are installed, not just the root ones
cd model_layer/ttm-related
pip install -r requirements.txt
```

### `ValueError: Missing required columns in <csv>`

**Explanation:** The input CSV doesn't match the Data Layer's `feature_dataset.csv` contract (`docs/INTERFACE.md` Section 1). Confirm you're pointing at the real Data Layer output, not a partial or hand-edited CSV.

### `ValueError: No segment with >= 700 rows found`

**Explanation:** INTERFACE.md §1.5 requires a contiguous segment of at least 700 rows for the 512+96 TTM window. Pass `--trip-id`/`--segment-id` to target a specific segment, or check that the input CSV has enough eligible segments (83 of 118 in the current delivered dataset).

---

## Team & Contact

**Model Team:**
- Ray Wang — model / scoring / training (TTM integration, residual scoring, fine-tuning)
- Lucca Zhou — data interface / validation / fault injection (input contracts, output hardening, evaluation data prep)

**Project:** Granite Lifeline
**Institution:** University of Bristol MSc Computer Science
**Sponsor:** IBM

For questions or contributions, please refer to the main project README or create a Jira ticket.

---

## References

- [IBM Granite Time Series Models](https://www.ibm.com/granite)
- Ekambaram et al. (2024) — *Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series* (NeurIPS 2024)
- [Project INTERFACE.md](../docs/INTERFACE.md) - Data contracts
- [Model Layer Viva Notes](../docs/viva/model_challenge.md) - Approach rationale, evaluation plan, Q&A
- [Report Layer README](../report_layer/README.md) - Downstream consumer of Model Layer output
- [Project README.md](../README.md) - Overall architecture
