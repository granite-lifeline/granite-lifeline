#!/usr/bin/env bash
# One-command local setup + launch for Granite Lifeline (macOS/Linux).
#
# Installs Python dependencies (including torch/transformers for the
# Model Layer), installs Ollama if missing, pulls the Granite LLM, and
# starts the dashboard. Safe to re-run — every step is idempotent.
#
# Windows users: follow the manual steps in README.md instead.
set -euo pipefail

cd "$(dirname "$0")"

OLLAMA_MODEL="granite4.1:8b"

echo "==> Installing Python dependencies (includes torch — this can take a few minutes on first run)..."
python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt

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
    sleep 3
fi

echo "==> Pulling ${OLLAMA_MODEL} (~5.3GB on first run; skips if already present)..."
ollama pull "${OLLAMA_MODEL}"

echo "==> Setup complete. Starting the dashboard..."
streamlit run dashboard/app.py
