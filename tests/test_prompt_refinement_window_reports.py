import csv
import json
from pathlib import Path

from report_layer.evaluation.prompt_refinement.window_reports import (
    build_selected_window_cases,
)


def test_build_selected_window_cases_writes_model_inputs(tmp_path: Path):
    candidate_dir = tmp_path / "candidates"
    raw_dir = candidate_dir / "raw_model_outputs"
    raw_dir.mkdir(parents=True)

    manifest_path = candidate_dir / "window_candidate_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "csv_path",
                "window_id",
                "anomaly_type",
                "risk_level",
                "selected_for_eval",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "csv_path": "iat_case",
            "window_id": "trip_0003_seg_001__w000",
            "anomaly_type": "intake_air_temperature_sensor_fault",
            "risk_level": "High",
            "selected_for_eval": "True",
        })
        writer.writerow({
            "csv_path": "iat_case",
            "window_id": "trip_0003_seg_001__w001",
            "anomaly_type": "cooling_degradation",
            "risk_level": "Low",
            "selected_for_eval": "False",
        })

    raw_output = {
        "summary": {
            "timestamp": "2026-08-01T12:00:00Z",
            "anomaly_type": "cooling_degradation",
            "risk_score": 1.0,
        },
        "windows": [
            {
                "trip_id": "trip_0003",
                "segment_id": "trip_0003_seg_001",
                "window_id": "trip_0003_seg_001__w000",
                "timestamp": "2026-08-01T12:00:00Z",
                "anomaly_type": "intake_air_temperature_sensor_fault",
                "risk_score": 0.9,
                "risk_level": "High",
                "component": "intake_air_temperature_sensor_fault",
                "prediction_confidence": 0.9,
                "key_signals": [],
                "estimated_cycles_to_failure": None,
                "estimated_failure_probability": None,
                "notes": [
                    "intake_air_temperature_sensor_fault forwarded from "
                    "Data Layer proxy_decisions.csv"
                ],
            }
        ],
    }
    (raw_dir / "iat_case.json").write_text(json.dumps(raw_output))

    rows = build_selected_window_cases(candidate_dir)

    assert len(rows) == 1
    assert rows[0]["anomaly_type"] == "intake_air_temperature_sensor_fault"
    model_input = json.loads(
        Path(rows[0]["model_input_path"]).read_text(encoding="utf-8")
    )
    assert model_input["window_id"] == "trip_0003_seg_001__w000"
    assert model_input["anomaly_type"] == (
        "intake_air_temperature_sensor_fault"
    )
