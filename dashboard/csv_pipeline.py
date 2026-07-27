"""CSV upload integration for the dashboard pipeline."""

from __future__ import annotations

import importlib
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

try:
    from data_loader import load_model_output_for_dashboard
except ImportError:  # package import during tests
    from dashboard.data_loader import load_model_output_for_dashboard


_RUNNER_CANDIDATES = [
    "model_layer.pipeline",
    "model_layer.run_model",
    "model_layer.batch_runner",
]


class UploadedCsvPipelineError(RuntimeError):
    """Base class for CSV upload pipeline failures shown in the UI."""


class ModelBatchRunnerUnavailable(UploadedCsvPipelineError):
    """Raised when Model Layer has not exposed run_model_batch yet."""


def _resolve_run_model_batch() -> Callable[[str], Dict[str, Any]]:
    """Find the Model Layer batch runner exposed by GL-259."""
    for module_name in _RUNNER_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        runner = getattr(module, "run_model_batch", None)
        if callable(runner):
            return runner
    raise ModelBatchRunnerUnavailable(
        "Model Layer batch runner is not available. Expected a "
        "run_model_batch(csv_path) function."
    )


def _build_upload_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"dashboard_upload_{timestamp}_{uuid4().hex[:8]}"


def _run_data_layer(raw_csv_path: Path) -> Path:
    """Run Data Layer on an uploaded raw CSV and return production features."""
    try:
        from data_layer.pipeline_data.paths import RunLayout
        from data_layer.run_pipeline import REPO_ROOT, run_data_pipeline
    except Exception as exc:
        raise UploadedCsvPipelineError(
            "Data Layer pipeline is not available for uploaded CSV files."
        ) from exc

    layout = RunLayout.for_run_id(_build_upload_run_id(), repo_root=REPO_ROOT)
    summary = run_data_pipeline(layout, input_dir=raw_csv_path.parent)
    production_rel = summary.get("production_features")
    production_path = (
        layout.run_dir / production_rel
        if production_rel
        else layout.production_features
    )
    if not production_path.is_file():
        raise UploadedCsvPipelineError(
            "Data Layer did not produce production_features.csv."
        )
    return production_path


def run_uploaded_csv_batch(csv_bytes: bytes) -> Dict[str, Any]:
    """
    Run uploaded raw CSV bytes through Data Layer and Model Layer.

    Returns dashboard-ready component data keyed by anomaly type, with
    ``_data_source`` marking the generated component as ``uploaded``.
    """
    runner = _resolve_run_model_batch()
    if not csv_bytes.strip():
        raise UploadedCsvPipelineError("The uploaded CSV file is empty.")

    with tempfile.TemporaryDirectory(prefix="granite_upload_") as temp_dir:
        raw_path = Path(temp_dir) / "uploaded_obd.csv"
        raw_path.write_bytes(csv_bytes)
        # Keep the uploaded file name predictable because Data Layer treats
        # one source CSV as one drive cycle.
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir()
        input_path = input_dir / raw_path.name
        shutil.copy2(raw_path, input_path)

        production_features = _run_data_layer(input_path)
        model_output = runner(str(production_features))
        return load_model_output_for_dashboard(model_output, "uploaded")
