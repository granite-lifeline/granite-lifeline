# Granite Lifeline

An end-to-end predictive maintenance system for engine
components, using OBD-II time-series data, IBM Granite TTM
for anomaly detection, and IBM Granite LLM for natural
language diagnostic report generation.

## Dashboard Demo

[![Open Dashboard](https://img.shields.io/badge/Open%20Dashboard-granite--lifeline.streamlit.app-19c8b9?style=for-the-badge&logo=streamlit&logoColor=white)](https://granite-lifeline.streamlit.app)

## Blog

Project updates and sprint reflections are documented on our team blog: https://granite-lifeline.github.io/granite-lifeline-blog/

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
    ▼  [anomaly_type, risk_score, risk_level,
        component, prediction_confidence, key_signals]
Report Layer
  (IBM Granite LLM — 3-layer prompt chain
   + RAG knowledge retrieval)
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

Run the dashboard locally:

```bash
uv run streamlit run dashboard/app.py
```
