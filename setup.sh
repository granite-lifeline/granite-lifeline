#!/usr/bin/env bash
# One-command local setup + launch for Granite Lifeline (macOS/Linux).
#
# Installs dashboard dependencies, installs the Model Layer's dedicated
# dependencies, installs Ollama if missing, pulls the Granite LLM, and
# starts the dashboard. Safe to re-run — every step is idempotent.
#
# Windows users: run setup.ps1 instead.
set -euo pipefail

cd "$(dirname "$0")"

OLLAMA_MODEL="granite4.1:8b"

if ! python3 -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] <= (3, 13)))'; then
    echo "Python 3.11, 3.12, or 3.13 is required (TTM compatibility)."
    exit 1
fi

echo "==> Installing dashboard Python dependencies..."
python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt
pip install -r requirements-local.txt

echo "==> Installing Model Layer Python dependencies (includes torch — this can take a few minutes on first run)..."
python3 -m venv model_layer/ttm-related/.venv 2>/dev/null || true
model_layer/ttm-related/.venv/bin/python -m pip install --upgrade pip --quiet
model_layer/ttm-related/.venv/bin/python -m pip install -r model_layer/ttm-related/requirements.txt

echo "==> Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo "Ollama not found — installing via Homebrew..."
        brew install ollama
    else
        echo "Ollama not found and Homebrew is unavailable."
        echo "Install it manually first: https://ollama.com/download"
        exit 1
    fi
fi

echo "==> Starting Ollama server (if not already running)..."
if ! curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    nohup ollama serve >/tmp/granite_lifeline_ollama.log 2>&1 &
    disown
    for _ in {1..15}; do
        curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1 && break
        sleep 1
    done
fi
if ! curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama did not become ready. See /tmp/granite_lifeline_ollama.log"
    exit 1
fi

echo "==> Pulling ${OLLAMA_MODEL} (~5.3GB on first run; skips if already present)..."
ollama pull "${OLLAMA_MODEL}"

echo "==> Building the production RAG knowledge index..."
python -m report_layer.rag.knowledge_indexer

export MODEL_LAYER_PYTHON="$PWD/model_layer/ttm-related/.venv/bin/python"

echo "==> Verifying the complete local runtime..."
python scripts/verify_local_pipeline.py

echo "==> All checks passed. Starting the dashboard..."
streamlit run dashboard/app.py
