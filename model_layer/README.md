# Model Layer

The Model Layer loads IBM Granite TTM (`ibm-granite/granite-timeseries-ttm-r2`),
forecasts short-term future sensor behaviour from a window of KIT
OBD-II history, compares the forecast against what actually
happened, and turns the resulting residuals into a risk score and
anomaly classification. Its output is the interface JSON consumed
by the Report Layer.

Shared field-definition contract with the Data Layer and Report
Layer: [`docs/INTERFACE.md`](../docs/INTERFACE.md).

## Pipeline

```
Data Layer's production_features.csv (schema v1, 46 columns)
  -> segment-safe 512-step context window
  -> Granite TTM forecast (96 steps, fine-tuned or zero-shot)
  -> residuals vs actual future window
  -> per-signal risk scoring + anomaly-type attribution
  -> calibrated risk_level (Low / Medium / High)
  -> risk-score history appended per window
  -> trend projection -> estimated_cycles_to_failure / _failure_probability
  -> interface JSON
```

Forecast/residual signals: `rpm`, `speed`, `coolant_temp`, `map`,
`maf`, `tps`.

**Anomaly types the Model Layer scores itself:**
`cooling_degradation`, `air_intake_maf_anomaly`,
`accelerator_pedal_sensor`.

**Anomaly types the Model Layer forwards, never scores:**
`intake_air_temperature_sensor_fault` and
`map_load_signal_plausibility_fault` are decided by the Data Layer's
proxy engine (scripts 50–70). When the detector is given
`--proxy-decisions`, it relays their already-computed verdicts into
the output JSON; without it they stay at `0.0`. That is forwarding,
not scoring — see `proxy_decision_forwarding.py` and INTERFACE.md
§2.4.

## Layout

```
identify_anomoly/
  failure_type_research.md          proxy failure definitions + healthy baseline
  image/                            baseline and correlation figures

ttm-related/
  config/
    risk_level_calibration.v1.json  versioned Low/Medium/High policy
  src/model/
    kit_residual_detector.py        detector, CLI entrypoint
    input_validation.py             Data Layer input contract checks
    validate_output.py              interface JSON schema validator
    risk_level_calibration.py       loads the risk-level policy above
    risk_history.py                 append-only risk-score history + validation
    failure_estimation.py           risk-trend projection to the two estimate fields
    proxy_decision_forwarding.py    relays Data Layer verdicts for two anomaly types
    prepare_finetune_split.py       segment eligibility + train/val split manifest
    finetune_ttm.py                 fine-tuning entrypoint (tsfm_public Trainer)
    compare_finetune_residuals.py   zero-shot vs fine-tuned residual comparison
    fault_injection.py              schema-v1 synthetic fault injectors
    run_synthetic_evaluation.py     sweeps injected scenarios through the detector
    synthetic_evaluation_metrics.py precision/recall from the sweep results
    risk_threshold_calibration.py   reproduces the calibrated alarm threshold
    data_simulator.py, download_ttm.py
  tests/                            pytest suite, fixtures, Group 1 fixture builders
  outputs/                          committed sample outputs, reports, model artifact
  requirements.txt
```

Key files under `outputs/`:

| File | What it is |
|---|---|
| `kit_residual_sample.json` | committed contract sample for Report Layer integration |
| `evaluation_note.md` | detection results per anomaly type + limitations statement |
| `risk_threshold_calibration_e5_lr5e-5.{json,md}` | evidence behind the calibrated alarm line |
| `synthetic_eval_results_e5_lr5e-5.json` | raw per-window synthetic sweep results |
| `synthetic_eval_metrics_e5_lr5e-5_calibrated.{json,md}` | precision/recall at the calibrated line |
| `failure_estimation_demo.{json,md}` | worked failure-estimation demonstration |
| `finetune_split_manifest.json` | train/validation segment split record |
| `ttm_finetuned_e5_lr5e-5/` | fine-tuned model artifact + training config |

## Setup

Install dependencies (a dedicated virtual environment is
recommended, since these pin specific `torch`/`transformers`
versions):

```
pip install -r model_layer/ttm-related/requirements.txt
```

## Running the detector

From the repository root, pointing at a feature CSV produced by the
Data Layer pipeline:

```
python model_layer/ttm-related/src/model/kit_residual_detector.py \
    path/to/production_features.csv --segment-id trip_0001_seg_001 \
    --output model_layer/ttm-related/outputs/kit_residual_sample.json
```

The input path defaults to the Data Layer's committed schema fixture
(`data_layer/tests/fixtures/production_features.v1.fixture.csv`),
which is only 187 rows — enough to check the column contract, but
below the 700-row window minimum, so a bare run exits with
`ERROR: No segment with >= 700 rows found`. Always pass a real
feature CSV for an actual inference run.

Useful flags:

| Flag | Effect |
|---|---|
| `--batch` | sweep every eligible segment with non-overlapping 512+96 windows; emits a `{summary, windows}` envelope (INTERFACE.md §2.5) |
| `--trip-id` / `--segment-id` | restrict the run to one trip or segment |
| `--proxy-decisions` | path to the Data Layer's `proxy_decisions.csv`; activates verdict forwarding for the two Data-Layer-scored types |
| `--history-file` | where the risk-score history is appended (default `outputs/risk_history.csv`) |
| `--output` | save the interface JSON to a file |

The detector, Dashboard, and formal synthetic evaluation always use the
committed epoch-5 fine-tuned artefact. Zero-shot inference is retained only
inside the separate model-comparison tooling and is not selectable through
the production detector CLI. This keeps deployed inference aligned with the
model used for threshold calibration and formal evaluation.

A segment needs at least 700 contiguous rows (512 context + 96
forecast + margin) and windows never cross segment boundaries, per
INTERFACE.md §1.5. Expected failures (bad input, no usable segment,
schema violations) print a single `ERROR: <message>` line to stderr
and exit non-zero, so the dashboard can display them directly
instead of a traceback.

## Risk levels and calibration

`risk_level` comes from `config/risk_level_calibration.v1.json`, not
from hard-coded numbers: Medium at `risk_score >= 0.4129`, High at
`>= 0.90`. The alarm line was selected by maximising macro F1 subject
to a healthy false-positive rate of at most 10% on a deterministic
calibration subset, and reconciled against the Data Layer's frozen
`calibration_registry.v1.json` (read only, never modified).

Reproduce the selection:

```
python model_layer/ttm-related/src/model/risk_threshold_calibration.py
```

It re-scores the committed synthetic evaluation results and fails if
the selected line disagrees with the policy file. The policy is
provisional and synthetic-only — one held-out healthy segment still
scores 1.0, so it must not be presented as real-fault validation.

## Fine-tuning on healthy KIT data

1. Build the train/validation split manifest. Segments need >= 700
   contiguous rows and must pass the schema-v1 eligibility gate on
   `condition_quality_flags` / `condition_confidence` (Group 1 ships
   no fault-label file, so all delivered data is treated as healthy):

```
python model_layer/ttm-related/src/model/prepare_finetune_split.py
```

2. Fine-tune (dry-run by default; add `--train` to actually train):

```
python model_layer/ttm-related/src/model/finetune_ttm.py --train
```

3. Compare the fine-tuned model against zero-shot on the held-out
   validation segments:

```
python model_layer/ttm-related/src/model/compare_finetune_residuals.py
```

A fine-tuning run is only reported as a clear improvement if overall
validation MAE drops by at least 5% and at least 4 of the 6 model
signals do not get worse; smaller improvements are reported as
modest evidence, not a validated win. The committed artifact
(`epochs=5`, `lr=5e-5`) improved overall validation MAE from 58.0004
to 54.9666, a 5.2% gain over 12 validation segments — see
[`ttm-related/outputs/finetune_residual_comparison_e5_lr5e-5.md`](ttm-related/outputs/finetune_residual_comparison_e5_lr5e-5.md).

## Synthetic-fault evaluation

There are no real fault labels in the KIT dataset, so detection is
measured by injecting known faults into healthy held-out segments and
checking whether the detector raises the right anomaly type. Faults
start at the context/future boundary and are propagated through every
delivered feature that is an exact function of the changed raw
signal; the injectors deliberately do not encode detector thresholds.

```
python model_layer/ttm-related/src/model/run_synthetic_evaluation.py
python model_layer/ttm-related/src/model/synthetic_evaluation_metrics.py
```

Results, per-type precision/recall and the limitations statement are
in [`ttm-related/outputs/evaluation_note.md`](ttm-related/outputs/evaluation_note.md).
These numbers describe synthetic perturbations on one vehicle's data;
they are not evidence of performance on real vehicle faults.

## Failure estimation

`estimated_cycles_to_failure` and `estimated_failure_probability` are
projected from the accumulated risk-score history. Detector-window
risk scores are aggregated into per-trip means, a least-squares line
is fitted across chronological trips, and the crossing point with the
High-risk threshold is reported.

```
python model_layer/ttm-related/src/model/failure_estimation.py \
    model_layer/ttm-related/tests/fixtures/risk_history_rising.csv \
    --json-output /tmp/estimate.json --markdown-output /tmp/estimate.md
```

Both fields are `null` when fewer than five trips of history exist,
when the trend is flat or falling, or when the projection exceeds 50
cycles. Neither is a remaining-useful-life estimate or a calibrated
probability of mechanical failure — KIT supplies no labelled failure
times, so nothing here is fitted to observed failures. Every emitted
estimate carries that statement in the output `notes`.

## Output format

Interface JSON keeps the highest-ranked component in the established
top-level fields and emits the next-highest distinct component as a full
single-risk object in `secondary_risk`. Required single-risk fields are
`timestamp`, `anomaly_type`,
`risk_score`, `risk_level`, `component`, `prediction_confidence`,
`key_signals`, `estimated_cycles_to_failure`,
`estimated_failure_probability`, `notes`. Full field definitions,
enum values, and ranges are in
[`docs/INTERFACE.md`](../docs/INTERFACE.md); validate any output
against the schema with:

```
python model_layer/ttm-related/src/model/validate_output.py \
    model_layer/ttm-related/outputs/kit_residual_sample.json
```

## Tests

```
python -m pytest model_layer/ttm-related/tests/
```

Some tests skip by design: the pre-schema-v1 fault-injection
scenarios retired under GL-322, and the checks that need the GL-366
proxy verification run directory, which is not committed.
