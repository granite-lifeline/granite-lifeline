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

## Setup

**Dashboard only (mock/demo data, no CSV analysis):**

```bash
uv run streamlit run dashboard/app.py
```

**Full local pipeline (real CSV upload → live Model Layer + Report Layer analysis):**

`requirements.txt` includes torch/transformers for TTM inference, and report
generation needs a local [Ollama](https://ollama.com) instance with the
Granite LLM pulled. On macOS/Linux, `setup.sh` does all of this in one step
(installs Python deps, installs Ollama if missing, pulls the model, starts
the dashboard):

```bash
./setup.sh
```

Windows users: install dependencies with `pip install -r requirements.txt`,
install [Ollama](https://ollama.com/download) and run `ollama pull
granite4.1:8b`, then start the dashboard as above.
