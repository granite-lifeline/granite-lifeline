# Granite Lifeline

A local decision-support prototype that analyses logged OBD-II journeys,
uses IBM Granite TTM and rule-based evidence to identify unusual component
behaviour, and uses an IBM Granite LLM to explain the result to a vehicle
owner. Its outputs describe anomaly risk and require professional confirmation;
they are not confirmed mechanical diagnoses.

## Dashboard Demo

[![Open Dashboard](https://img.shields.io/badge/Open%20Dashboard-granite--lifeline.streamlit.app-19c8b9?style=for-the-badge&logo=streamlit&logoColor=white)](https://granite-lifeline.streamlit.app)

## Viva Presentation

[![View Viva Slides](https://img.shields.io/badge/View%20Viva%20Slides-GitHub%20Pages-0f62fe?style=for-the-badge&logo=github&logoColor=white)](https://granite-lifeline.github.io/granite-lifeline/viva/slides/)

## Blog

Project updates and sprint reflections are documented on our team blog:
[![Team Blog](https://img.shields.io/badge/Team%20Blog-granite--lifeline.github.io-19c8b9?style=for-the-badge&logo=jekyll&logoColor=white)](https://granite-lifeline.github.io/granite-lifeline-blog/)


## Architecture

```text
KIT OBD-II CSV
    │
    ▼
Data Layer
  (cleaning, feature engineering, reference ranges)
    │
    ▼  [engineered features]
Model Layer
  (IBM Granite TTM — anomaly detection)
    │
    ▼  [anomaly_type, risk_score, risk_level, component,
        prediction_confidence, key_signals,
        estimated_failure_probability, estimated_cycles_to_failure, notes]
Report Layer
  (IBM Granite LLM — 3-layer prompt chain
   + RAG knowledge base with ChromaDB)
    │
    ▼  [anomaly_description, possible_cause,
        recommended_action, risk_history]
Dashboard
  (Streamlit — vehicle owner interface)
```

Full field definitions for each arrow are in `docs/INTERFACE.md`.

## Structure

- `data_layer/` — data ingestion, cleaning, feature engineering
- `model_layer/` — Granite TTM anomaly detection
- `report_layer/` — Granite LLM diagnostic report generation, RAG knowledge base
- `dashboard/` — Streamlit application
- `shared/` — cross-layer Pydantic interface models
- `docs/INTERFACE.md` — field definitions across all layers
- `docs/adr/` — architecture decision records
- `docs/viva/slides/` — interactive viva presentation and visual assets

## Data Setup

This project uses the KIT Automotive OBD-II Dataset.

**Download:**
KIT Dataset (RADAR repository): <https://radar.kit.edu/radar/en/dataset/bCtGxdTklQlfQcAq>

**Setup:**
Place the downloaded file(s) under:

```text
data/raw/
```

The repository does not track the dataset itself (see `.gitignore`). Each team member must download it independently before running the Data Layer pipeline.

## Quick Start

**Dashboard only (mock/demo data, no CSV analysis):**

```bash
uv run streamlit run dashboard/app.py
```

**Full local pipeline (real CSV upload → live Model Layer + Report Layer analysis):**

Run the setup command from the repository root. It installs both Python
environments, starts Ollama, pulls `granite4.1:8b`, downloads and tests Granite
TTM, builds the 20-document production RAG index, runs a readiness check, and
only then starts Streamlit.

macOS/Linux:

```bash
./setup.sh
```

Windows PowerShell:

```powershell
.\setup.ps1
```

If script execution is blocked, run once as administrator:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

The first run downloads several large dependencies and the approximately
5.3 GB Ollama model. Do not close the terminal while setup is running.

## Full Local Pipeline

The local uploader executes this real path:

```text
OBD-II CSV upload -> Data Layer -> Model Layer -> Report Layer -> Dashboard
```

### Prerequisites

- Python 3.11+
- Internet access during first-time setup
- Enough disk space for PyTorch, Granite TTM, ChromaDB dependencies, and the
  approximately 5.3 GB Granite LLM
- macOS/Linux: Homebrew is needed only when Ollama is not already installed
- Windows: `winget` is needed only when Ollama is not already installed

If automatic Ollama installation is unavailable, install it from
<https://ollama.com/download>, then run the setup command again.

### First-time setup

```bash
git clone https://github.com/granite-lifeline/granite-lifeline.git
cd granite-lifeline
./setup.sh
```

Use `.\setup.ps1` instead of `./setup.sh` on Windows. Both scripts are safe to
re-run after an interrupted install. A successful run prints all four checks:

```text
[PASS] Main Python environment
[PASS] Model Layer runtime
[PASS] RAG fault_knowledge collection (20 documents)
[PASS] Ollama API and granite4.1:8b
READY: CSV upload can use the full local pipeline.
```

### Daily start after setup

Start Ollama if it is not already running, then run the readiness check before
Streamlit.

macOS/Linux:

```bash
ollama serve
```

In a second terminal:

```bash
source .venv/bin/activate
export MODEL_LAYER_PYTHON="$PWD/model_layer/ttm-related/.venv/bin/python"
python scripts/verify_local_pipeline.py
streamlit run dashboard/app.py
```

Windows PowerShell:

```powershell
ollama serve
```

In a second PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
$env:MODEL_LAYER_PYTHON = (Resolve-Path ".\model_layer\ttm-related\.venv\Scripts\python.exe").Path
python scripts\verify_local_pipeline.py
streamlit run dashboard\app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`).
The public Streamlit Cloud URL is demo-only and cannot access models installed
on your laptop.

### CSV accepted by the live uploader

Use an original KIT OBD-II CSV, for example:
`2018-03-01_Seat_Leon_RT_S_Normal.csv`.

The upload must:

- keep its original KIT filename because the date is parsed from the name;
- contain all 11 raw OBD-II columns checked in `dashboard/csv_validator.py`;
- contain at least one continuous segment of 700 rows or more (roughly 70
  seconds after 10 Hz resampling).

After selecting the file, click **Run Analysis**. A successful run performs
Data cleaning and feature generation, TTM/proxy anomaly analysis, three local
Granite LLM report calls with RAG context, and Dashboard rendering. The first
analysis is slower because model caches are cold.

### Troubleshooting

Run this first; it reports the exact missing runtime component and exits
non-zero until all live-pipeline dependencies are ready:

```bash
python scripts/verify_local_pipeline.py
```

- **Ollama is not reachable:** keep `ollama serve` running in another terminal.
- **Granite model is missing:** run `ollama pull granite4.1:8b`.
- **RAG index is missing or stale:** activate `.venv`, then run
  `python -m report_layer.rag.knowledge_indexer`.
- **Model runtime is missing:** re-run `./setup.sh` or `.\setup.ps1`; do not
  install TTM into only the Dashboard environment.
- **CSV is rejected:** restore the original KIT filename and confirm the 11
  required headers and a continuous 700-row segment.
- **Generated report fields are empty:** inspect the terminal log. The Report
  Layer deliberately returns empty generated fields if Ollama or one of its
  three prompt calls fails; this is not a successful diagnosis.
