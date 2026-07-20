"""CSV upload integration for the dashboard pipeline."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict

from data_loader import load_model_output_for_dashboard


_RUNNER_CANDIDATES = [
    "model_layer.pipeline",
    "model_layer.run_model",
    "model_layer.batch_runner",
]


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
    raise RuntimeError(
        "Model Layer batch runner is not available. Expected a "
        "run_model_batch(csv_path) function."
    )


def run_uploaded_csv_batch(csv_bytes: bytes) -> Dict[str, Any]:
    """
    Run uploaded CSV bytes through Model Layer batch inference.

    Returns dashboard-ready component data keyed by anomaly type, with
    ``_data_source`` marking the generated component as ``uploaded``.
    """
    runner = _resolve_run_model_batch()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write(csv_bytes)
            temp_path = Path(temp_file.name)

        model_output = runner(str(temp_path))
        return load_model_output_for_dashboard(model_output, "uploaded")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
