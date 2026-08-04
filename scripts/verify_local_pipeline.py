"""Fail-fast readiness check for the local CSV-to-dashboard pipeline."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = REPO_ROOT / "model_layer" / "ttm-related"
MODEL_SCRIPT = MODEL_ROOT / "src" / "model" / "kit_residual_detector.py"
MODEL_PYTHON = (
    MODEL_ROOT / ".venv" / "Scripts" / "python.exe"
    if os.name == "nt"
    else MODEL_ROOT / ".venv" / "bin" / "python"
)
OLLAMA_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = "granite4.1:8b"


def passed(message: str) -> None:
    print(f"[PASS] {message}")


def failed(message: str, fixes: list[str]) -> None:
    print(f"[FAIL] {message}")
    for fix in fixes:
        print(f"       {fix}")


def check_main_environment() -> bool:
    if not ((3, 11) <= sys.version_info[:2] <= (3, 13)):
        failed(
            f"Unsupported Python {sys.version_info.major}.{sys.version_info.minor}.",
            ["Use Python 3.11, 3.12, or 3.13 for TTM compatibility."],
        )
        return False
    required = {
        "streamlit": "streamlit",
        "pandas": "pandas",
        "pydantic": "pydantic",
        "requests": "requests",
        "yaml": "PyYAML",
        "chromadb": "chromadb",
    }
    missing = []
    for module, package in required.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        failed(
            "Main application environment is incomplete.",
            ["Missing: " + ", ".join(missing), "Re-run setup.sh/setup.ps1."],
        )
        return False
    passed(f"Main Python environment ({sys.executable})")
    return True


def check_model_environment() -> bool:
    if not MODEL_PYTHON.is_file() or not MODEL_SCRIPT.is_file():
        failed(
            "Dedicated Model Layer runtime is missing.",
            ["Re-run setup.sh/setup.ps1 from the repository root."],
        )
        return False
    command = [
        str(MODEL_PYTHON),
        str(MODEL_ROOT / "src" / "model" / "download_ttm.py"),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        failed(
            "Granite TTM did not load within five minutes.",
            ["Check the Hugging Face connection, then re-run setup."],
        )
        return False
    if result.returncode != 0:
        failed(
            "Granite TTM could not be downloaded and loaded.",
            [
                (result.stderr or result.stdout).strip(),
                "Re-run setup.sh/setup.ps1.",
            ],
        )
        return False
    resolved = os.environ.get("MODEL_LAYER_PYTHON", str(MODEL_PYTHON))
    passed(f"Model Layer runtime and cached Granite TTM ({resolved})")
    return True


def check_rag() -> bool:
    try:
        import chromadb

        path = REPO_ROOT / "report_layer" / "rag" / "chroma_db"
        client = chromadb.PersistentClient(path=str(path))
        fault_count = client.get_collection("fault_knowledge").count()
    except Exception as exc:
        failed(
            "Production RAG knowledge index is unavailable.",
            [str(exc), "Run: python -m report_layer.rag.knowledge_indexer"],
        )
        return False
    if fault_count != 20:
        failed(
            f"RAG index has {fault_count} documents; expected 20.",
            ["Run: python -m report_layer.rag.knowledge_indexer"],
        )
        return False
    passed("RAG fault_knowledge collection (20 documents)")
    return True


def check_ollama() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=5) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        failed(
            "Ollama is not reachable on localhost:11434.",
            [str(exc), "Start it with: ollama serve"],
        )
        return False
    names = {model.get("name") for model in payload.get("models", [])}
    if OLLAMA_MODEL not in names:
        failed(
            f"Ollama model {OLLAMA_MODEL} is not installed.",
            [f"Run: ollama pull {OLLAMA_MODEL}"],
        )
        return False
    passed(f"Ollama API and {OLLAMA_MODEL}")
    return True


def main() -> int:
    print("Granite Lifeline local pipeline readiness check")
    checks = [
        check_main_environment(),
        check_model_environment(),
        check_rag(),
        check_ollama(),
    ]
    if all(checks):
        print("\nREADY: CSV upload can use the full local pipeline.")
        return 0
    print("\nNOT READY: fix the failed checks before starting Streamlit.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
