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


def test_build_selected_window_cases_skips_complete_existing_reports(
    tmp_path: Path,
    monkeypatch,
):
    candidate_dir = tmp_path / "candidates"
    raw_dir = candidate_dir / "raw_model_outputs"
    report_dir = candidate_dir / "selected_window_reports"
    raw_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)

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
            "csv_path": "cooling_case",
            "window_id": "trip_0001_seg_001__w000",
            "anomaly_type": "cooling_degradation",
            "risk_level": "Low",
            "selected_for_eval": "True",
        })

    raw_output = {
        "windows": [
            {
                "window_id": "trip_0001_seg_001__w000",
                "timestamp": "2026-08-01T12:00:00Z",
                "anomaly_type": "cooling_degradation",
                "risk_score": 0.2,
                "risk_level": "Low",
                "component": "cooling_degradation",
                "prediction_confidence": 0.7,
                "key_signals": [],
                "estimated_cycles_to_failure": None,
                "estimated_failure_probability": None,
                "notes": [],
            }
        ],
    }
    (raw_dir / "cooling_case.json").write_text(json.dumps(raw_output))
    existing_report = (
        report_dir
        / "cooling_degradation__trip_0001_seg_001__w000.json"
    )
    existing_report.write_text(json.dumps({
        "anomaly_description": "Existing description",
        "possible_cause": "Existing cause",
        "recommended_action": ["Existing action"],
    }))

    def fail_generate_report(*_args, **_kwargs):
        raise AssertionError("generate_report should not be called")

    monkeypatch.setattr(
        "report_layer.evaluation.prompt_refinement.window_reports."
        "generate_report",
        fail_generate_report,
    )

    rows = build_selected_window_cases(
        candidate_dir,
        generate_reports=True,
    )

    assert rows[0]["report_path"] == str(existing_report)


def test_build_selected_window_cases_filters_by_anomaly_type(
    tmp_path: Path,
):
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
            "csv_path": "cooling_case",
            "window_id": "cooling_w000",
            "anomaly_type": "cooling_degradation",
            "risk_level": "Low",
            "selected_for_eval": "True",
        })
        writer.writerow({
            "csv_path": "maf_case",
            "window_id": "maf_w000",
            "anomaly_type": "air_intake_maf_anomaly",
            "risk_level": "Low",
            "selected_for_eval": "True",
        })

    for source_id, anomaly_type, window_id in [
        ("cooling_case", "cooling_degradation", "cooling_w000"),
        ("maf_case", "air_intake_maf_anomaly", "maf_w000"),
    ]:
        (raw_dir / f"{source_id}.json").write_text(json.dumps({
            "windows": [
                {
                    "window_id": window_id,
                    "timestamp": "2026-08-01T12:00:00Z",
                    "anomaly_type": anomaly_type,
                    "risk_score": 0.2,
                    "risk_level": "Low",
                    "component": anomaly_type,
                    "prediction_confidence": 0.7,
                    "key_signals": [],
                    "estimated_cycles_to_failure": None,
                    "estimated_failure_probability": None,
                    "notes": [],
                }
            ],
        }))

    rows = build_selected_window_cases(
        candidate_dir,
        anomaly_types={"cooling_degradation"},
    )

    assert len(rows) == 1
    assert rows[0]["anomaly_type"] == "cooling_degradation"
