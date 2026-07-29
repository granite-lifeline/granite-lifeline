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
Data Layer's feature_dataset.csv
  -> segment-safe 512-step context window
  -> Granite TTM forecast (96 steps)
  -> residuals vs actual future window
  -> per-signal risk scoring + anomaly-type attribution
  -> interface JSON (risk_score, risk_level, anomaly_type, key_signals, ...)
```

Forecast/residual signals: `rpm`, `speed`, `coolant_temp`, `map`,
`maf`, `tps`.

## Layout

```
ttm-related/
  src/model/
    kit_residual_detector.py       zero-shot detector, CLI entrypoint
    input_validation.py            Data Layer input contract checks
    validate_output.py             interface JSON schema validator
    prepare_finetune_split.py      healthy-segment eligibility + train/val split
    finetune_ttm.py                fine-tuning entrypoint (tsfm_public Trainer)
    compare_finetune_residuals.py  zero-shot vs fine-tuned residual comparison
    data_simulator.py, download_ttm.py
  tests/                           pytest suite, Group 1 fixture builders
  outputs/                         committed sample outputs and manifests
  requirements.txt
```

## Setup

Install dependencies (a dedicated virtual environment is
recommended, since these pin specific `torch`/`transformers`
versions):

```
pip install -r model_layer/ttm-related/requirements.txt
```

## Running the zero-shot detector

From the repository root:

```
python model_layer/ttm-related/src/model/kit_residual_detector.py
```

Optionally pass a specific feature CSV and segment:

```
python model_layer/ttm-related/src/model/kit_residual_detector.py \
    path/to/feature_dataset.csv --segment-id trip_0001_seg_001 \
    --output model_layer/ttm-related/outputs/kit_residual_sample.json
```

## Fine-tuning on healthy KIT data

1. Build the train/validation split manifest (`prepare_finetune_split.py`) —
   segments need >= 700 contiguous rows and must be entirely
   healthy per `proxy_training_labels.csv`.
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
modest evidence, not a validated win.

## Output format

Interface JSON required fields: `timestamp`, `anomaly_type`,
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
