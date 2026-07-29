"""Tests for dashboard CSV upload validation and pipeline glue."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from dashboard.csv_pipeline import (
    ModelBatchRunnerUnavailable,
    UploadedCsvPipelineError,
    run_uploaded_csv_batch,
)
from dashboard.csv_validator import (
    REQUIRED_COLUMNS,
    validate_csv_columns,
    validate_csv_min_rows,
)


def _model_output() -> dict:
    return {
        "timestamp": "2026-07-20T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 0.7,
        "risk_level": "Medium",
        "component": "cooling_degradation",
        "prediction_confidence": 0.8,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 101.0,
                "unit": "degC",
                "reference_range": [90, 95],
            }
        ],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
    }


def test_csv_validator_accepts_required_columns_and_aliases():
    columns = [
        col.replace("°", "Â°")
        if col == "Engine Coolant Temperature [°C]"
        else col
        for col in REQUIRED_COLUMNS
    ]
    df = pd.DataFrame([{col: 1 for col in columns}])

    assert validate_csv_columns(df) == (True, [])


def test_csv_validator_lists_missing_columns():
    df = pd.DataFrame(columns=["Time", "Engine RPM [RPM]"])

    ok, missing = validate_csv_columns(df)

    assert not ok
    assert "Vehicle Speed Sensor [km/h]" in missing
    assert "Engine RPM [RPM]" not in missing


def test_csv_validator_enforces_minimum_rows():
    assert validate_csv_min_rows(pd.DataFrame(index=range(699))) is False
    assert validate_csv_min_rows(pd.DataFrame(index=range(700))) is True


def test_run_uploaded_csv_batch_rejects_empty_bytes():
    with pytest.raises(UploadedCsvPipelineError, match="empty"):
        run_uploaded_csv_batch(b"   \n", "trip.csv")


def test_run_model_layer_raises_when_script_missing(monkeypatch, tmp_path):
    import dashboard.csv_pipeline as csv_pipeline

    monkeypatch.setattr(
        csv_pipeline, "MODEL_LAYER_SCRIPT", tmp_path / "missing_detector.py"
    )

    with pytest.raises(ModelBatchRunnerUnavailable):
        csv_pipeline._run_model_layer(tmp_path / "production_features.csv")


def test_run_model_layer_parses_error_contract(monkeypatch, tmp_path):
    """Non-zero exit + stderr ``ERROR: <message>`` (INTERFACE.md §2.5)."""
    import dashboard.csv_pipeline as csv_pipeline

    script = tmp_path / "detector.py"
    script.write_text("# stub")
    monkeypatch.setattr(csv_pipeline, "MODEL_LAYER_SCRIPT", script)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="ERROR: bad input\n"
        )

    monkeypatch.setattr(csv_pipeline.subprocess, "run", fake_run)

    with pytest.raises(UploadedCsvPipelineError, match="bad input"):
        csv_pipeline._run_model_layer(tmp_path / "production_features.csv")


def test_run_model_layer_times_out(monkeypatch, tmp_path):
    import dashboard.csv_pipeline as csv_pipeline

    script = tmp_path / "detector.py"
    script.write_text("# stub")
    monkeypatch.setattr(csv_pipeline, "MODEL_LAYER_SCRIPT", script)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 0))

    monkeypatch.setattr(csv_pipeline.subprocess, "run", fake_run)

    with pytest.raises(TimeoutError):
        csv_pipeline._run_model_layer(tmp_path / "production_features.csv")


def test_run_model_layer_reads_output_json(monkeypatch, tmp_path):
    import dashboard.csv_pipeline as csv_pipeline

    script = tmp_path / "detector.py"
    script.write_text("# stub")
    monkeypatch.setattr(csv_pipeline, "MODEL_LAYER_SCRIPT", script)
    envelope = {"summary": _model_output(), "windows": []}

    def fake_run(cmd, **kwargs):
        # Simulate the detector writing its --output file.
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text(json.dumps(envelope))
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(csv_pipeline.subprocess, "run", fake_run)

    result = csv_pipeline._run_model_layer(
        tmp_path / "production_features.csv"
    )

    assert result == envelope


def test_run_uploaded_csv_batch_passes_production_features_to_model(
    monkeypatch, tmp_path: Path
):
    import dashboard.csv_pipeline as csv_pipeline

    calls: dict[str, str] = {}
    production_features = tmp_path / "production_features.csv"
    production_features.write_text("timestamp,rpm\n2026-07-20T12:00:00Z,900\n")

    def fake_data_layer(input_path: Path) -> Path:
        calls["data_input"] = str(input_path)
        return production_features

    def fake_run_model_layer(csv_path: Path) -> dict:
        calls["model_input"] = str(csv_path)
        return {
            "summary": _model_output(),
            "windows": [
                {
                    **_model_output(),
                    "trip_id": "trip_0001",
                    "segment_id": "trip_0001_seg_001",
                    "window_id": "w000001",
                }
            ],
        }

    monkeypatch.setattr(csv_pipeline, "_run_data_layer", fake_data_layer)
    monkeypatch.setattr(
        csv_pipeline, "_run_model_layer", fake_run_model_layer
    )

    dashboard_data = run_uploaded_csv_batch(
        b"Time\n12:00:00.000\n",
        "2018-03-01_Seat_Leon_RT_S_Normal.csv",
    )

    # Data Layer requires the original KIT file name to parse the
    # recording date; a renamed temp file would be rejected.
    assert calls["data_input"].endswith(
        "2018-03-01_Seat_Leon_RT_S_Normal.csv"
    )
    assert calls["model_input"] == str(production_features)
    assert "cooling_degradation" in dashboard_data
    assert dashboard_data["_data_source"]["cooling_degradation"] == "uploaded"
    assert dashboard_data["cooling_degradation"]["risk_history"] == [
        {"timestamp": "2026-07-20T12:00:00Z", "risk_score": 0.7}
    ]
