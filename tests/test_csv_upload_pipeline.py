"""Tests for dashboard CSV upload validation and pipeline glue."""

from __future__ import annotations

import json
import subprocess
import sys
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


dashboard_dir = str(Path("dashboard").resolve())
if dashboard_dir not in sys.path:
    sys.path.insert(0, dashboard_dir)


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


class _FakeUpload:
    def __init__(self, data: bytes, name: str = "trip.csv"):
        self._data = data
        self.name = name

    def getvalue(self) -> bytes:
        return self._data


class _FakeSpinner:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def _capture_overview_markdown(monkeypatch):
    import dashboard.pages.overview as overview
    from dashboard.theme import THEME_TOKENS

    rendered: list[str] = []
    monkeypatch.setattr(
        overview.st,
        "markdown",
        lambda body, **kwargs: rendered.append(str(body)),
    )
    monkeypatch.setattr(
        overview.st,
        "warning",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("bare st.warning should not be used")
        ),
    )
    monkeypatch.setattr(overview.st, "session_state", {})
    return overview, THEME_TOKENS["light"], rendered


def test_csv_upload_ui_no_file_uses_polished_empty_state(monkeypatch):
    overview, tokens, rendered = _capture_overview_markdown(monkeypatch)

    overview._handle_uploaded_csv_submit(None, tokens)

    html = "".join(rendered)
    assert "Choose a CSV file first" in html
    assert "gl-empty-state" in html


def test_csv_upload_ui_empty_file_uses_danger_card(monkeypatch):
    overview, tokens, rendered = _capture_overview_markdown(monkeypatch)

    overview._handle_uploaded_csv_submit(_FakeUpload(b" \n "), tokens)

    html = "".join(rendered)
    assert "Empty File" in html
    assert "valid OBD-II CSV file" in html


def test_csv_upload_ui_missing_columns_lists_required_fields(monkeypatch):
    overview, tokens, rendered = _capture_overview_markdown(monkeypatch)
    csv_data = b"Time,Engine RPM [RPM]\n0,900\n"

    overview._handle_uploaded_csv_submit(_FakeUpload(csv_data), tokens)

    html = "".join(rendered)
    assert "Missing Required Columns" in html
    assert "Vehicle Speed Sensor [km/h]" in html


def test_csv_upload_ui_success_stores_dashboard_data_and_reruns(monkeypatch):
    overview, tokens, rendered = _capture_overview_markdown(monkeypatch)
    upload_df = pd.DataFrame(
        [
            {column: row_idx for column in REQUIRED_COLUMNS}
            for row_idx in range(700)
        ]
    )
    csv_bytes = upload_df.to_csv(index=False).encode("utf-8")
    dashboard_result = {
        "cooling_degradation": {
            **_model_output(),
            "anomaly_description": "Cooling readings show rising stress.",
        },
        "_data_source": {"cooling_degradation": "uploaded"},
    }
    calls: dict[str, object] = {}
    rerun_calls: list[bool] = []

    def fake_run_uploaded_csv_batch(body: bytes, file_name: str) -> dict:
        calls["body"] = body
        calls["file_name"] = file_name
        return dashboard_result

    monkeypatch.setattr(
        overview, "run_uploaded_csv_batch", fake_run_uploaded_csv_batch
    )
    monkeypatch.setattr(
        overview.st, "spinner", lambda label: _FakeSpinner(label)
    )
    monkeypatch.setattr(
        overview.st,
        "progress",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("fake progress bar should not be used")
        ),
    )
    monkeypatch.setattr(overview.st, "rerun", lambda: rerun_calls.append(True))

    overview._handle_uploaded_csv_submit(
        _FakeUpload(csv_bytes, "valid-drive.csv"), tokens
    )

    assert calls == {"body": csv_bytes, "file_name": "valid-drive.csv"}
    assert overview.st.session_state["dashboard_data"] == dashboard_result
    assert len(overview.st.session_state["validated_df"]) == 700
    assert overview.st.session_state["dashboard_mode"] == "dashboard"
    assert overview.st.session_state["csv_analysis_running"] is False
    assert rerun_calls == [True]
    assert "Analysing your CSV..." in "".join(rendered)
    assert "Data Layer, Model Layer, and Report Layer" in "".join(rendered)
    assert "Analysis Unavailable" not in "".join(rendered)


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

    def fake_load_model_output_for_dashboard(model_output: dict, source: str):
        assert source == "uploaded"
        return {
            "cooling_degradation": {
                **model_output["summary"],
                "risk_history": [
                    {
                        "timestamp": "2026-07-20T12:00:00Z",
                        "risk_score": 0.7,
                    }
                ],
            },
            "_data_source": {"cooling_degradation": "uploaded"},
        }

    monkeypatch.setattr(csv_pipeline, "_run_data_layer", fake_data_layer)
    monkeypatch.setattr(
        csv_pipeline, "_run_model_layer", fake_run_model_layer
    )
    monkeypatch.setattr(
        csv_pipeline,
        "load_model_output_for_dashboard",
        fake_load_model_output_for_dashboard,
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
