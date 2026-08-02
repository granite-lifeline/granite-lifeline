from pathlib import Path

import pandas as pd

from report_layer.evaluation.prompt_refinement.discovery import (
    extract_risk_history_count,
    extract_summary,
    has_proxy_provenance_note,
    summarize_model_output,
    summarize_proxy_decisions,
)


def _model_summary(notes=None):
    return {
        "timestamp": "2026-08-01T12:00:00Z",
        "anomaly_type": "intake_air_temperature_sensor_fault",
        "risk_score": 0.6,
        "risk_level": "Medium",
        "component": "intake_air_temperature_sensor_fault",
        "prediction_confidence": 0.6,
        "key_signals": [],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": notes or [],
    }


def test_extract_summary_accepts_single_and_batch_outputs():
    single = _model_summary()
    batch = {"summary": single, "windows": [{**single, "risk_score": 0.5}]}

    assert extract_summary(single) == single
    assert extract_summary(batch) == single


def test_extract_risk_history_count_uses_batch_windows():
    output = {
        "summary": _model_summary(),
        "windows": [
            {"timestamp": "2026-08-01T12:00:00Z", "risk_score": 0.4},
            {"timestamp": "2026-08-01T12:01:00Z", "risk_score": 0.6},
            {"timestamp": "2026-08-01T12:02:00Z"},
        ],
    }

    assert extract_risk_history_count(output) == 2


def test_proxy_provenance_note_detection():
    notes = [
        "intake_air_temperature_sensor_fault forwarded from Data Layer "
        "proxy_decisions.csv: 4-S1 triggered, confidence provisional"
    ]

    assert has_proxy_provenance_note(notes)


def test_summarize_model_output_records_proxy_provenance(tmp_path: Path):
    proxy_path = tmp_path / "proxy_decisions.csv"
    output = {
        "summary": _model_summary(
            notes=[
                "Detection based on Data Layer proxy decision rules, "
                "not TTM residual scoring"
            ]
        ),
        "windows": [
            {
                **_model_summary(),
                "timestamp": "2026-08-01T12:00:00Z",
                "risk_score": 0.6,
            }
        ],
    }

    row = summarize_model_output(tmp_path / "trip.csv", output, proxy_path)

    assert row["output_shape"] == "batch"
    assert row["anomaly_type"] == "intake_air_temperature_sensor_fault"
    assert row["projection_is_null"] is True
    assert row["risk_history_count"] == 1
    assert row["has_proxy_decisions_path"] is True
    assert row["has_proxy_provenance_note"] is True


def test_summarize_proxy_decisions_for_forwarded_types(tmp_path: Path):
    proxy_path = tmp_path / "proxy_decisions.csv"
    pd.DataFrame(
        [
            {
                "proxy_id": "intake_air_temperature_sensor_fault",
                "sub_check_id": "4-S1",
                "result_state": "triggered",
                "dtc_emitted": True,
                "confidence": "provisional",
            },
            {
                "proxy_id": "map_load_signal_plausibility_fault",
                "sub_check_id": "5-S1",
                "result_state": "pass",
                "dtc_emitted": False,
                "confidence": "high",
            },
        ]
    ).to_csv(proxy_path, index=False)

    rows = summarize_proxy_decisions(tmp_path / "trip.csv", proxy_path)

    by_type = {row["anomaly_type"]: row for row in rows}
    assert by_type["intake_air_temperature_sensor_fault"][
        "has_positive_proxy_evidence"
    ]
    assert by_type["intake_air_temperature_sensor_fault"][
        "triggered_rows"
    ] == 1
    assert by_type["map_load_signal_plausibility_fault"][
        "has_positive_proxy_evidence"
    ] is False
