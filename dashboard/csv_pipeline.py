"""CSV upload integration for the dashboard pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import pandas as pd

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
_MODEL_VENV = _REPO_ROOT / "model_layer" / "ttm-related" / ".venv"
MODEL_LAYER_VENV_PYTHON = (
    _MODEL_VENV / "Scripts" / "python.exe"
    if os.name == "nt"
    else _MODEL_VENV / "bin" / "python"
)
# Matches report_layer/pipeline/report_generator.py's Ollama TIMEOUT —
# both are the pipeline's "slow AI call" thresholds. Estimated, not
# measured; tune once real TTM batch-run timings are available.
MODEL_LAYER_TIMEOUT_SECONDS = 120
ProgressCallback = Callable[[int, str], None]
UploadedCsvTrip = tuple[bytes, str]
HISTORY_MIN_TRIPS = 5
CSV_PROGRESS_STAGES = {
    "checking_upload": (5, "Checking uploaded CSV..."),
    "preparing_upload": (10, "Preparing drive data..."),
    "processing_signals": (35, "Processing vehicle signals..."),
    "estimating_risk": (65, "Estimating component risk..."),
    "generating_report": (90, "Generating diagnostic report..."),
    "preparing_dashboard": (100, "Preparing dashboard results..."),
}
CSV_PROGRESS_STAGE_KEYS = tuple(CSV_PROGRESS_STAGES)


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


def _run_model_layer(
    production_features_path: Path,
    proxy_decisions_path: Path | None,
    output_path: Path,
) -> Dict[str, Any]:
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
    command = [
        python, str(MODEL_LAYER_SCRIPT),
        str(production_features_path),
        "--batch",
        "--output", str(output_path),
        # Each upload is an independent analysis run. Reusing the Model
        # Layer's repository-wide default history would mix unrelated
        # ``trip_0001`` identifiers and can make a later upload appear to
        # move backwards in time.
        "--history-file", str(output_path.parent / "risk_history.csv"),
    ]
    if proxy_decisions_path is not None:
        command.extend(["--proxy-decisions", str(proxy_decisions_path)])

    try:
        result = subprocess.run(
            command,
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


def _run_data_layer(raw_csv_path: Path) -> tuple[Path, Path | None]:
    """Run Data Layer and return feature/proxy output paths.

    ``raw_csv_path`` must keep its original KIT file name — Data Layer
    parses the recording date from it (data_layer/run_pipeline.py
    ``run_data_pipeline_for_upload`` docstring; data_layer/README.md D3).

    Returns:
        ``(production_features_path, proxy_decisions_path)``.  The proxy
        path is ``None`` when the Data Layer summary does not include
        ``proxy_decisions_path``.
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

    proxy_path = None
    proxy_path_value = summary.get("proxy_decisions_path")
    if proxy_path_value:
        proxy_path = Path(proxy_path_value)
        if not proxy_path.is_file():
            raise UploadedCsvPipelineError(
                "Data Layer reported proxy_decisions.csv but the file "
                "was not created."
            )

    return production_path, proxy_path


def _emit_progress(
    progress_callback: Optional[ProgressCallback],
    percent: int,
    message: str,
) -> None:
    if progress_callback is not None:
        progress_callback(percent, message)


def get_csv_progress_stage(stage_key: str) -> tuple[int, str]:
    try:
        return CSV_PROGRESS_STAGES[stage_key]
    except KeyError as exc:
        raise ValueError(f"Unknown CSV progress stage: {stage_key}") from exc


def _emit_progress_stage(
    progress_callback: Optional[ProgressCallback],
    stage_key: str,
) -> None:
    percent, message = get_csv_progress_stage(stage_key)
    _emit_progress(progress_callback, percent, message)


def run_uploaded_csv_batch(
    csv_bytes: bytes,
    original_filename: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    """
    Run uploaded raw CSV bytes through Data Layer and Model Layer.

    ``original_filename`` must be the file's original KIT name (e.g.
    Streamlit's ``UploadedFile.name``) — Data Layer rejects renamed
    files because the recording date lives only in the file name.

    Returns dashboard-ready component data keyed by anomaly type, with
    ``_data_source`` marking the generated component as ``uploaded``.
    """
    _emit_progress_stage(progress_callback, "checking_upload")
    if not csv_bytes.strip():
        raise UploadedCsvPipelineError("The uploaded CSV file is empty.")

    with tempfile.TemporaryDirectory(prefix="granite_upload_") as temp_dir:
        raw_path = Path(temp_dir) / original_filename
        _emit_progress_stage(progress_callback, "preparing_upload")
        raw_path.write_bytes(csv_bytes)

        _emit_progress_stage(progress_callback, "processing_signals")
        production_features, proxy_decisions = _run_data_layer(raw_path)
        _emit_progress_stage(progress_callback, "estimating_risk")
        output_path = Path(temp_dir) / "model_output.json"
        model_output = _run_model_layer(
            production_features,
            proxy_decisions,
            output_path,
        )
        _emit_progress_stage(progress_callback, "generating_report")
        dashboard_data = load_model_output_for_dashboard(
            model_output, "uploaded"
        )
        _emit_progress_stage(progress_callback, "preparing_dashboard")
        return dashboard_data


def _first_dashboard_component(
    dashboard_data: Dict[str, Any],
) -> tuple[str, Dict[str, Any]]:
    for component_key, component_data in dashboard_data.items():
        if component_key == "_data_source":
            continue
        if isinstance(component_data, dict):
            return component_key, component_data
    raise UploadedCsvPipelineError(
        "The analysis did not return any component report."
    )


def _trip_timestamp_from_name(original_filename: str) -> str:
    try:
        trip_date = datetime.strptime(original_filename[:10], "%Y-%m-%d")
    except ValueError:
        return ""
    return trip_date.replace(tzinfo=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _trip_progress_callback(
    progress_callback: Optional[ProgressCallback],
    trip_number: int,
    trip_count: int,
) -> ProgressCallback:
    def update(percent: int, message: str) -> None:
        overall = int(
            round(((trip_number - 1) + (percent / 100.0)) / trip_count * 100)
        )
        overall = max(0, min(100, overall))
        _emit_progress(
            progress_callback,
            overall,
            f"Analysing trip {trip_number} of {trip_count}: {message}",
        )

    return update


def _build_risk_history(
    trip_results: list[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    return [
        {
            "trip_id": trip["trip_id"],
            "window_id": f'{trip["trip_id"]}_w000',
            "timestamp": trip["timestamp"],
            "risk_score": trip["risk_score"],
        }
        for trip in trip_results
    ]


def _load_failure_estimation_helpers():
    model_src = _REPO_ROOT / "model_layer" / "ttm-related" / "src"
    model_src_text = str(model_src)
    if model_src_text not in sys.path:
        sys.path.insert(0, model_src_text)
    try:
        from model.failure_estimation import (
            add_estimate_to_output,
            estimate_from_history,
        )
    except Exception as exc:
        raise UploadedCsvPipelineError(
            "Failure estimation is not available for uploaded history."
        ) from exc
    return estimate_from_history, add_estimate_to_output


def _add_failure_estimate_to_latest_report(
    latest_dashboard_data: Dict[str, Any],
    risk_history: list[Dict[str, Any]],
) -> Dict[str, Any]:
    component_key, component_data = _first_dashboard_component(
        latest_dashboard_data
    )
    estimate_from_history, add_estimate_to_output = (
        _load_failure_estimation_helpers()
    )
    try:
        estimate = estimate_from_history(pd.DataFrame(risk_history))
    except Exception as exc:
        raise UploadedCsvPipelineError(
            "Failure estimation could not complete for uploaded history."
        ) from exc
    annotated_component = add_estimate_to_output(component_data, estimate)
    annotated_component["risk_history"] = risk_history

    updated = dict(latest_dashboard_data)
    updated[component_key] = annotated_component
    data_source = dict(updated.get("_data_source", {}))
    data_source[component_key] = "uploaded_history"
    updated["_data_source"] = data_source
    return updated


def run_uploaded_csv_history_batch(
    csv_trips: list[UploadedCsvTrip],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    """
    Run an ordered set of uploaded CSV trips through the existing pipeline.

    The caller is responsible for sorting by filename date before calling this
    function.  The returned dashboard data uses the last trip as the current
    report, with the full trip history and failure-estimation fields attached.
    """
    if len(csv_trips) < HISTORY_MIN_TRIPS:
        raise UploadedCsvPipelineError(
            "Failure prediction needs at least five chronological trips."
        )

    trip_results: list[Dict[str, Any]] = []
    latest_dashboard_data: Dict[str, Any] | None = None
    trip_count = len(csv_trips)

    for index, (csv_bytes, original_filename) in enumerate(csv_trips, start=1):
        dashboard_data = run_uploaded_csv_batch(
            csv_bytes,
            original_filename,
            progress_callback=_trip_progress_callback(
                progress_callback, index, trip_count
            ),
        )
        component_key, component_data = _first_dashboard_component(
            dashboard_data
        )
        risk_score = component_data.get("risk_score")
        if risk_score is None:
            raise UploadedCsvPipelineError(
                f"{original_filename} did not return a risk_score."
            )

        trip_results.append(
            {
                "trip_id": f"trip_{index:04d}",
                "file_name": original_filename,
                "component": component_key,
                "timestamp": (
                    component_data.get("timestamp")
                    or _trip_timestamp_from_name(original_filename)
                ),
                "risk_score": risk_score,
                "risk_level": component_data.get("risk_level"),
            }
        )
        latest_dashboard_data = dashboard_data

    risk_history = _build_risk_history(trip_results)
    dashboard_data = _add_failure_estimate_to_latest_report(
        latest_dashboard_data or {}, risk_history
    )
    _emit_progress(progress_callback, 100, "Preparing dashboard results...")
    return {
        "dashboard_data": dashboard_data,
        "trip_results": trip_results,
        "risk_history": risk_history,
    }
