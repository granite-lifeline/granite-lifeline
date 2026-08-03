# GL-384 Demo Readiness Check

**Owner:** Report / Dashboard Layer  
**Date:** 2026-07-30  
**Scope:** Final dashboard demonstration readiness for Sprint 4 / Sprint 5 handoff.

## Goal

Confirm that the Dashboard presents a stable, understandable demo of the
Report Layer output:

- Overview page shows all five current monitored components.
- Detail page explains risk, evidence, failure prediction, and actions clearly.
- What-If page can show scenario impact without layout problems.
- PDF and CSV export are visible and downloadable.
- Empty and error states look intentional, not like raw Streamlit failures.

## Automated Check

Run this before demo or before marking GL-384 / GL-416 complete:

```bash
python -m pytest \
  tests/test_dashboard.py \
  tests/test_export_helper.py \
  tests/test_csv_upload_pipeline.py \
  tests/test_failure_prediction_ui_states.py \
  tests/test_dashboard_ui_consistency.py \
  tests/test_dashboard_what_if.py \
  tests/test_demo_readiness.py
```

Expected result:

- Tests pass.
- One PDF text extraction test may be skipped when `pypdf` is not installed.
- The LibreSSL warning from `urllib3` is acceptable on the local macOS venv.

## Manual Demo Route

Start the dashboard:

```bash
streamlit run dashboard/app.py --server.port 8502
```

Open `http://localhost:8502`, then check:

| Step | Area | What to verify | Expected output |
|------|------|----------------|-----------------|
| 1 | Landing | Click `Explore with demo data` | Overview opens using curated demo data |
| 2 | Overview | Component cards are sorted by risk | High risk appears first, then Medium, then Low |
| 3 | Overview | There are five monitored components | Cooling, Air Intake, Manifold Pressure, Intake Air Temperature, Accelerator Pedal |
| 4 | Detail | Open `Cooling System` | Failure prediction, notes, trend, key signals, and report text are visible |
| 5 | Detail | Hover key signal names | Plain-language tooltips appear |
| 6 | What-If | Open What-If page and choose a scenario | Cards do not overlap; selected chip is readable; component breakdown updates |
| 7 | Export | Return to overview and use PDF / CSV buttons | Single or ZIP downloads are generated without external services |
| 8 | Empty state | Try running analysis without a CSV file | Polished empty state appears instead of a raw warning |
| 9 | CSV upload | Upload a valid KIT CSV and click `Run Analysis` | Button changes to `Analysing...` and the loading card appears immediately |
| 10 | CSV loading | Watch the loading card while the pipeline runs | A percentage progress ring is visible with `Analyzing data...`; no bottom Streamlit progress bar is shown |

## CSV Loading State Demo Checklist

Use this checklist when demonstrating the local live CSV flow for GL-388:

| Check | Expected result |
|-------|-----------------|
| Valid CSV selected | File name is visible; no duplicate file-row `Upload` button appears |
| `Run Analysis` clicked | Button is disabled and relabelled to `Analysing...` |
| Pipeline is running | Loading card shows `Analysing your CSV...`, a percentage progress ring, and `Analyzing data...` |
| Pipeline succeeds | Dashboard result loads and the loading state disappears |
| Pipeline fails or times out | Loading card disappears, the existing polished error card appears, and the button becomes usable again |
| Browser refresh during loading | Any stale loading state is cleared on the next render |

## Demo Talking Points

- The public hosted demo uses curated ReportLayerOutput-shaped data.
- Local live CSV upload needs the Data Layer, Model Layer, Report Layer, and local Ollama, but the user-facing loading text stays simple.
- The current dashboard supports five current anomaly types from `docs/INTERFACE.md`.
- Three anomaly types have live Model Layer scoring; two remain placeholder scores
  in the current Model Layer and should be presented as integration limitations.
- Failure probability and cycles-to-failure can be shown from demo data, but live
  mode still depends on the upstream estimator being implemented.
- PDF and CSV export run locally and do not depend on an external service.

## Demo Outputs

By the end of the demo, the audience should have seen:

- A prioritized vehicle health overview.
- A component-level diagnostic explanation.
- Evidence signals with readable names and normal ranges.
- A simple what-if comparison.
- A downloadable diagnostic report and key signal table.

## Readiness Status

| Item | Status |
|------|--------|
| UI consistency refinements | Done |
| IBM Carbon-inspired theme polish | Done |
| What-If layout improvement | Done |
| Export workflow simplification | Done |
| Export panel polish | Done |
| Empty/error state polish | Done |
| Dashboard regression test expansion | Done |
| Final demo route/checklist | Done |
| CSV loading state tests/checklist | Done |
| CSV loading regression tests | Done |
