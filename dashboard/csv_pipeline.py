"""CSV upload integration for the dashboard pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

try:
    from data_loader import load_model_output_for_dashboard
except ImportError:  # package import during tests
    from dashboard.data_loader import load_model_output_for_dashboard


# dashboard/csv_pipeline.py -> dashboard/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_LAYER_SCRIPT = (
    _REPO_ROOT
    / "model_layer" / "ttm-related" / "src" / "model"
    / "kit_residual_detector.py"
)
# Recommended per model_layer/ttm-related/README.md: a dedicated venv,
# since the detector pins specific torch/transformers versions.
MODEL_LAYER_VENV_PYTHON = (
    _REPO_ROOT / "model_layer" / "ttm-related" / ".venv" / "bin" / "python"
)
# Matches report_layer/pipeline/report_generator.py's Ollama TIMEOUT —
# both are the pipeline's "slow AI call" thresholds. Estimated, not
# measured; tune once real TTM batch-run timings are available.
MODEL_LAYER_TIMEOUT_SECONDS = 120


class UploadedCsvPipelineError(RuntimeError):
    """Base class for CSV upload pipeline failures shown in the UI."""


class ModelBatchRunnerUnavailable(UploadedCsvPipelineError):
    """Raised when the Model Layer detector script cannot be found."""


def _resolve_model_layer_python() -> str:
    """Resolve which Python interpreter runs the Model Layer detector.

    Resolution order: ``MODEL_LAYER_PYTHON`` env override, the Model
    Layer's own dedicated venv, then this process's own interpreter
    as a last resort (e.g. before that venv has been created).
    """
    override = os.environ.get("MODEL_LAYER_PYTHON")
    if override:
        return override
    if MODEL_LAYER_VENV_PYTHON.is_file():
        return str(MODEL_LAYER_VENV_PYTHON)
    return sys.executable


def _extract_error_message(stderr: str) -> str:
    """Pull the ``ERROR: <message>`` line from the detector's stderr.

    Per INTERFACE.md §2.5's dashboard error contract: expected failures
    exit non-zero with a single ``ERROR: <message>`` line, no traceback.
    """
    for line in stderr.splitlines():
        if line.startswith("ERROR:"):
            return line[len("ERROR:"):].strip()
    return (
        "The Model Layer analysis failed. "
        + (stderr.strip() or "No error details were returned.")
    )


def _run_model_layer(production_features_path: Path) -> Dict[str, Any]:
    """Run the Model Layer's TTM batch detector as a subprocess.

    Invokes ``kit_residual_detector.py --batch`` per INTERFACE.md
    §2.5's documented CLI contract, rather than importing a Python
    function — that contract was never part of the interface (its own
    ``main()`` docstring: "Group 3's dashboard shows stderr to the
    user, so expected failures must be one clear line and a non-zero
    exit, never a traceback").
    """
    if not MODEL_LAYER_SCRIPT.is_file():
        raise ModelBatchRunnerUnavailable(
            f"Model Layer detector script not found at {MODEL_LAYER_SCRIPT}."
        )

    python = _resolve_model_layer_python()
    with tempfile.TemporaryDirectory(
        prefix="granite_model_output_"
    ) as out_dir:
        output_path = Path(out_dir) / "model_output.json"
        try:
            result = subprocess.run(
                [
                    python, str(MODEL_LAYER_SCRIPT),
                    str(production_features_path),
                    "--batch",
                    "--output", str(output_path),
                ],
                # The detector's --history-file default is relative to
                # model_layer/ (its own docstring's "repository root");
                # without this, it writes to the caller's cwd instead.
                cwd=str(_REPO_ROOT / "model_layer"),
                capture_output=True,
                text=True,
                timeout=MODEL_LAYER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Model Layer analysis timed out after "
                f"{MODEL_LAYER_TIMEOUT_SECONDS}s."
            ) from exc

        if result.returncode != 0:
            raise UploadedCsvPipelineError(
                _extract_error_message(result.stderr)
            )
        if not output_path.is_file():
            raise UploadedCsvPipelineError(
                "Model Layer did not produce an output file."
            )
        try:
            return json.loads(output_path.read_text())
        except json.JSONDecodeError as exc:
            raise UploadedCsvPipelineError(
                "Model Layer output could not be parsed as JSON."
            ) from exc


def _build_upload_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"dashboard_upload_{timestamp}_{uuid4().hex[:8]}"


def _run_data_layer(raw_csv_path: Path) -> Path:
    """Run Data Layer on an uploaded raw CSV and return production features.

    ``raw_csv_path`` must keep its original KIT file name — Data Layer
    parses the recording date from it (data_layer/run_pipeline.py
    ``run_data_pipeline_for_upload`` docstring; data_layer/README.md D3).
    """
    try:
        from data_layer.run_pipeline import (
            UploadRejected,
            run_data_pipeline_for_upload,
        )
    except Exception as exc:
        raise UploadedCsvPipelineError(
            "Data Layer pipeline is not available for uploaded CSV files."
        ) from exc

    try:
        summary = run_data_pipeline_for_upload(
            raw_csv_path, run_id=_build_upload_run_id()
        )
    except UploadRejected as exc:
        raise UploadedCsvPipelineError(str(exc)) from exc

    production_path = Path(summary["production_features_path"])
    if not production_path.is_file():
        raise UploadedCsvPipelineError(
            "Data Layer did not produce production_features.csv."
        )
    return production_path


def run_uploaded_csv_batch(
    csv_bytes: bytes, original_filename: str
) -> Dict[str, Any]:
    """
    Run uploaded raw CSV bytes through Data Layer and Model Layer.

    ``original_filename`` must be the file's original KIT name (e.g.
    Streamlit's ``UploadedFile.name``) — Data Layer rejects renamed
    files because the recording date lives only in the file name.

    Returns dashboard-ready component data keyed by anomaly type, with
    ``_data_source`` marking the generated component as ``uploaded``.
    """
    if not csv_bytes.strip():
        raise UploadedCsvPipelineError("The uploaded CSV file is empty.")

    with tempfile.TemporaryDirectory(prefix="granite_upload_") as temp_dir:
        raw_path = Path(temp_dir) / original_filename
        raw_path.write_bytes(csv_bytes)

        production_features = _run_data_layer(raw_path)
        model_output = _run_model_layer(production_features)
        return load_model_output_for_dashboard(model_output, "uploaded")
