# Granite Lifeline

An end-to-end predictive maintenance system for engine
components, using OBD-II time-series data, IBM Granite TTM
for anomaly detection, and IBM Granite LLM for natural
language diagnostic report generation.

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

`requirements.txt` contains the lightweight dashboard dependencies used by the
hosted demo. The full local CSV pipeline also needs `requirements-local.txt`,
the Model Layer's dedicated TTM environment, and a local
[Ollama](https://ollama.com) instance with the Granite LLM pulled. On
macOS/Linux, `setup.sh` does all of this in one step (installs dashboard deps,
local pipeline deps, Model Layer deps, installs Ollama if missing, pulls the
model, starts the dashboard):

```bash
./setup.sh
```

On Windows, `setup.ps1` does the same (installs Python deps, installs Ollama
via `winget` if missing, pulls the model, starts the dashboard):

```powershell
.\setup.ps1
```

If script execution is blocked, run once as administrator:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Run the Full Pipeline Locally

Use this mode when you want the Dashboard CSV uploader to run the real
local pipeline:

```text
OBD-II CSV upload -> Data Layer -> Model Layer -> Report Layer -> Dashboard
```

**Prerequisites:**

- Python 3.11+
- `uv`
- Ollama
- Data Layer and Model Layer dependencies installed locally
- Enough disk space and time for the first install; `torch`, `transformers`,
  `granite-tsfm`, `chromadb`, and related packages are large

**Install and run:**

If you already cloned the repository, start from `cd granite-lifeline`.

```bash
git clone https://github.com/granite-lifeline/granite-lifeline.git
```

```bash
cd granite-lifeline
```

```bash
uv sync
```

Install Ollama from <https://ollama.com/download>, then start Ollama in a
separate terminal and keep it running:

```bash
ollama serve
```

Pull the Granite model:

```bash
ollama pull granite4.1:8b
```

Build the ChromaDB knowledge bases:

```bash
uv run python -m report_layer.rag.knowledge_indexer
```

```bash
uv run python -m report_layer.rag.symptom_knowledge_indexer
```

Start the Dashboard:

```bash
uv run streamlit run dashboard/app.py
```

Then open the local Streamlit URL, upload an OBD-II CSV file from the
Dashboard, and wait for the analysis to complete.

If you have already activated the local virtual environment, the equivalent
commands are:

```bash
python -m report_layer.rag.knowledge_indexer
```

```bash
python -m report_layer.rag.symptom_knowledge_indexer
```

```bash
streamlit run dashboard/app.py
```

**Expected first-run time:**

The first `uv sync` can reasonably take 10-30 minutes on a normal laptop,
depending on internet speed and whether Python wheels are cached. Pulling
`granite4.1:8b` with Ollama can also take several minutes because the model
is large. Later runs are usually much faster because dependencies, the
model, and the ChromaDB files are already cached locally.

**Operating system notes:**

The `uv sync`, `uv run python -m ...`, `ollama serve`, `ollama pull ...`,
and `uv run streamlit run dashboard/app.py` commands work on macOS, Linux,
and Windows when Python, uv, and Ollama are installed and available on
`PATH`. The Ollama installation step itself is OS-specific: use the official
installer for macOS or Windows, and the official Linux install instructions
for Linux. On Windows PowerShell, use the same runtime commands; only
shell-specific virtual-environment activation commands differ, which is why
the recommended commands use `uv run`.
