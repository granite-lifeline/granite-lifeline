"""Tests for dashboard CSV upload validation and pipeline glue."""

from __future__ import annotations

import sys
import types
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


def test_run_uploaded_csv_batch_requires_model_batch_runner(monkeypatch):
    import dashboard.csv_pipeline as csv_pipeline

    monkeypatch.setattr(csv_pipeline, "_RUNNER_CANDIDATES", [])

    with pytest.raises(ModelBatchRunnerUnavailable):
        run_uploaded_csv_batch(b"Time\n12:00:00.000\n")


def test_run_uploaded_csv_batch_rejects_empty_bytes(monkeypatch):
    import dashboard.csv_pipeline as csv_pipeline

    fake_module = types.SimpleNamespace(run_model_batch=lambda path: {})
    monkeypatch.setitem(sys.modules, "fake_model_runner", fake_module)
    monkeypatch.setattr(
        csv_pipeline, "_RUNNER_CANDIDATES", ["fake_model_runner"]
    )

    with pytest.raises(UploadedCsvPipelineError, match="empty"):
        run_uploaded_csv_batch(b"   \n")


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

    def fake_runner(csv_path: str) -> dict:
        calls["model_input"] = csv_path
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

    fake_module = types.SimpleNamespace(run_model_batch=fake_runner)
    monkeypatch.setitem(sys.modules, "fake_model_runner", fake_module)
    monkeypatch.setattr(
        csv_pipeline, "_RUNNER_CANDIDATES", ["fake_model_runner"]
    )
    monkeypatch.setattr(csv_pipeline, "_run_data_layer", fake_data_layer)

    dashboard_data = run_uploaded_csv_batch(b"Time\n12:00:00.000\n")

    assert calls["data_input"].endswith("uploaded_obd.csv")
    assert calls["model_input"] == str(production_features)
    assert "cooling_degradation" in dashboard_data
    assert dashboard_data["_data_source"]["cooling_degradation"] == "uploaded"
    assert dashboard_data["cooling_degradation"]["risk_history"] == [
        {"timestamp": "2026-07-20T12:00:00Z", "risk_score": 0.7}
    ]
