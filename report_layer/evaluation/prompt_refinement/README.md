# Prompt Refinement Evaluation Set

This folder builds a prompt-refinement set from real CSV pipeline runs.
It is intentionally not a hand-written collection of `ModelLayerOutput`
fixtures: cases are selected only after a real OBD-II CSV has passed through
the current Data Layer and Model Layer.

## Goal

Use real pipeline outputs to evaluate whether Report Layer prompts:

- stay grounded in the Model Layer JSON;
- explain risk in owner-friendly language;
- calibrate wording to `risk_level` and `prediction_confidence`;
- describe Story 8 failure projections as model projections, not guaranteed
  mechanical failure;
- avoid inventing projection values when
  `estimated_cycles_to_failure` or `estimated_failure_probability` is `null`;
- preserve provenance for proxy-forwarded detections.

The owner-facing quality rules used during manual review are maintained in
`report_regression_checklist.md`.

The current five-case regression set is registered in
`golden_report_set.json`. It covers all five supported anomaly types and marks
which cases are native real-CSV windows versus Data Layer fault-injection
proxy-forwarded windows.

## Real-CSV Discovery

Run a small discovery pass first:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.discovery --limit 3
```

Run a specific CSV:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.discovery --csv data/raw/OBD-II-Dataset/2018-03-01_Seat_Leon_RT_S_Normal.csv
```

Generate Report Layer outputs as well as raw Model Layer outputs:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.discovery --limit 3 --generate-reports
```

`--generate-reports` calls the Granite/Ollama Report Layer pipeline, so it
requires local Ollama with `granite4.1:8b`. Without that flag, discovery runs
only Data Layer + Model Layer and is suitable for selecting candidate cases.

Run existing feature/proxy artifacts directly through the Model Layer:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.discovery --run-dir data/processed/runs/<fault_injection_run_id> --output-dir report_layer/evaluation/prompt_refinement/fault_injection_candidates
```

Equivalent explicit pair form:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.discovery --feature-proxy-pair iat_case=data/processed/runs/<run_id>/features/41_production/production_features.csv:data/processed/runs/<run_id>/proxy/70_decisions/proxy_decisions.csv --output-dir report_layer/evaluation/prompt_refinement/fault_injection_candidates
```

This direct mode is intended for Data Layer fault-injection evidence: it skips
CSV upload/Data Layer execution and verifies that the Model Layer forwards an
existing `proxy_decisions.csv` into the interface JSON.

## Outputs

The script writes:

```text
report_layer/evaluation/prompt_refinement/
  real_csv_manifest.csv
  window_candidate_manifest.csv
  proxy_forwarding_audit.csv
  raw_model_outputs/
  generated_reports/
```

`real_csv_manifest.csv` records one row per CSV run, including anomaly type,
risk score, risk level, confidence, projection fields, notes, whether batch
history exists, whether proxy-provenance notes were emitted, and whether the
row was selected as a representative prompt-evaluation case. Native Model Layer
types are selected by anomaly type and risk level using the highest available
`prediction_confidence`. Proxy-forwarded IAT/MAP rows are selected only when
the model output includes proxy provenance and the proxy audit has positive
evidence for that same CSV/type pair.

`window_candidate_manifest.csv` records one row per Model Layer batch window.
It is the preferred manifest for prompt refinement because batch summaries can
be dominated by a higher-risk anomaly while still containing valid
proxy-forwarded IAT/MAP windows. Selected window rows cover the five current
anomaly types when evidence is available.

`proxy_forwarding_audit.csv` records the Data Layer `proxy_decisions.csv`
summary for the two proxy-forwarded anomaly types:

- `intake_air_temperature_sensor_fault`
- `map_load_signal_plausibility_fault`

## Proxy-Forwarded Cases

Positive proxy-forwarded report cases must come from real CSV output. The
evaluation set should not manually insert provenance notes. A valid proxy case
requires the Model Layer output itself to contain a note showing that the result
came from Data Layer proxy decisions rather than TTM residual scoring.

Current forwarding notes are expected to resemble:

```text
<anomaly_type> forwarded from Data Layer proxy_decisions.csv: ...
```

If no real CSV produces a positive IAT or MAP forwarded top anomaly, those
cases should be marked unavailable in the manifest rather than fabricated.
Use fault-injection feature/proxy pairs to cover these two required types when
the original healthy KIT CSVs do not contain positive proxy evidence.

## Selected Window Report Inputs

After `window_candidate_manifest.csv` exists, write one
`ModelLayerOutput`-shaped JSON file for each selected window:

```bash
uv run python -m report_layer.evaluation.prompt_refinement.window_reports
```

This writes:

```text
report_layer/evaluation/prompt_refinement/fault_injection_candidates/
  selected_window_model_outputs/
```

To also generate Report Layer outputs, first start Ollama and make sure
`granite4.1:8b` is available:

```bash
ollama serve
ollama pull granite4.1:8b
uv run python -m report_layer.evaluation.prompt_refinement.window_reports --generate-reports
```

The report-generation mode writes:

```text
report_layer/evaluation/prompt_refinement/fault_injection_candidates/
  selected_window_reports/
```

## Suggested Selection Criteria

After discovery, choose a compact set covering:

- highest available `risk_score`;
- one non-null Story 8 projection;
- one `null` projection;
- one low-confidence report;
- one report with Model Layer `notes`;
- one batch output with `risk_history`;
- any real positive proxy-forwarded IAT or MAP case, if present.
