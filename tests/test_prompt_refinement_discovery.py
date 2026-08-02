from pathlib import Path

import pandas as pd

from report_layer.evaluation.prompt_refinement.discovery import (
    FeatureProxyPair,
    discover_feature_proxy_pairs,
    extract_risk_history_count,
    extract_summary,
    feature_proxy_pair_from_run_dir,
    has_proxy_provenance_note,
    mark_selected_eval_cases,
    mark_selected_window_cases,
    parse_feature_proxy_pair,
    summarize_model_output,
    summarize_proxy_decisions,
    summarize_window_candidates,
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
    assert row["source_kind"] == "real_csv"
    assert row["anomaly_type"] == "intake_air_temperature_sensor_fault"
    assert row["projection_is_null"] is True
    assert row["risk_history_count"] == 1
    assert row["has_proxy_decisions_path"] is True
    assert row["has_proxy_provenance_note"] is True


def test_summarize_window_candidates_records_proxy_forwarded_windows(
    tmp_path: Path,
):
    proxy_path = tmp_path / "proxy_decisions.csv"
    output = {
        "summary": {
            **_model_summary(),
            "anomaly_type": "cooling_degradation",
            "risk_score": 1.0,
        },
        "windows": [
            {
                **_model_summary(
                    notes=[
                        "intake_air_temperature_sensor_fault forwarded from "
                        "Data Layer proxy_decisions.csv: 4-S3 triggered"
                    ]
                ),
                "trip_id": "trip_0003",
                "segment_id": "trip_0003_seg_001",
                "window_id": "trip_0003_seg_001__w000",
                "timestamp": "2026-08-01T12:00:00Z",
                "key_signals": [{"feature": "intake_temp"}],
            }
        ],
    }

    rows = summarize_window_candidates(
        tmp_path / "iat_case.csv", output, proxy_path
    )

    assert len(rows) == 1
    assert rows[0]["anomaly_type"] == "intake_air_temperature_sensor_fault"
    assert rows[0]["window_id"] == "trip_0003_seg_001__w000"
    assert rows[0]["key_signal_count"] == 1
    assert rows[0]["has_proxy_provenance_note"] is True


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
        "source_kind"
    ] == "real_csv"
    assert by_type["intake_air_temperature_sensor_fault"][
        "has_positive_proxy_evidence"
    ]
    assert by_type["intake_air_temperature_sensor_fault"][
        "triggered_rows"
    ] == 1
    assert by_type["map_load_signal_plausibility_fault"][
        "has_positive_proxy_evidence"
    ] is False


def test_mark_selected_eval_cases_selects_native_risk_examples():
    rows = [
        {
            "csv_path": "high_low_conf.csv",
            "output_shape": "batch",
            "anomaly_type": "cooling_degradation",
            "risk_level": "High",
            "risk_score": 0.9,
            "prediction_confidence": 0.6,
            "risk_history_count": 5,
            "has_proxy_provenance_note": False,
            "selected_for_eval": False,
            "selection_reason": "",
        },
        {
            "csv_path": "high_best_conf.csv",
            "output_shape": "batch",
            "anomaly_type": "cooling_degradation",
            "risk_level": "High",
            "risk_score": 0.8,
            "prediction_confidence": 0.8,
            "risk_history_count": 4,
            "has_proxy_provenance_note": False,
            "selected_for_eval": False,
            "selection_reason": "",
        },
        {
            "csv_path": "medium.csv",
            "output_shape": "batch",
            "anomaly_type": "air_intake_maf_anomaly",
            "risk_level": "Medium",
            "risk_score": 0.5,
            "prediction_confidence": 0.9,
            "risk_history_count": 3,
            "has_proxy_provenance_note": False,
            "selected_for_eval": False,
            "selection_reason": "",
        },
    ]

    mark_selected_eval_cases(rows, [])

    selected = {
        row["csv_path"]: row["selection_reason"]
        for row in rows
        if row["selected_for_eval"]
    }
    assert selected == {
        "high_best_conf.csv": (
            "representative_cooling_degradation_high"
        ),
        "medium.csv": (
            "representative_air_intake_maf_anomaly_medium"
        ),
    }


def test_mark_selected_eval_cases_requires_positive_proxy_evidence():
    rows = [
        {
            "csv_path": "proxy.csv",
            "output_shape": "batch",
            "anomaly_type": "intake_air_temperature_sensor_fault",
            "risk_level": "High",
            "risk_score": 0.9,
            "prediction_confidence": 0.9,
            "risk_history_count": 2,
            "has_proxy_provenance_note": True,
            "selected_for_eval": False,
            "selection_reason": "",
        }
    ]

    mark_selected_eval_cases(rows, [])
    assert rows[0]["selected_for_eval"] is False

    proxy_rows = [
        {
            "csv_path": "proxy.csv",
            "anomaly_type": "intake_air_temperature_sensor_fault",
            "has_positive_proxy_evidence": True,
        }
    ]
    mark_selected_eval_cases(rows, proxy_rows)

    assert rows[0]["selected_for_eval"] is True
    assert rows[0]["selection_reason"] == (
        "proxy_forwarded_positive_intake_air_temperature_sensor_fault"
    )


def test_mark_selected_window_cases_selects_proxy_window_when_summary_differs():
    rows = [
        {
            "csv_path": "iat_case",
            "anomaly_type": "intake_air_temperature_sensor_fault",
            "risk_level": "High",
            "risk_score": 0.9,
            "prediction_confidence": 0.9,
            "has_proxy_provenance_note": True,
            "selected_for_eval": False,
            "selection_reason": "",
        },
        {
            "csv_path": "iat_case",
            "anomaly_type": "cooling_degradation",
            "risk_level": "High",
            "risk_score": 1.0,
            "prediction_confidence": 0.7,
            "has_proxy_provenance_note": False,
            "selected_for_eval": False,
            "selection_reason": "",
        },
    ]
    proxy_rows = [
        {
            "csv_path": "iat_case",
            "anomaly_type": "intake_air_temperature_sensor_fault",
            "has_positive_proxy_evidence": True,
        }
    ]

    mark_selected_window_cases(rows, proxy_rows)

    selected = {
        row["anomaly_type"]: row["selection_reason"]
        for row in rows
        if row["selected_for_eval"]
    }
    assert selected["intake_air_temperature_sensor_fault"] == (
        "window_representative_intake_air_temperature_sensor_fault"
    )
    assert selected["cooling_degradation"] == (
        "window_representative_cooling_degradation"
    )


def test_parse_feature_proxy_pair_accepts_named_pair():
    pair = parse_feature_proxy_pair(
        "iat_case=/tmp/features.csv:/tmp/proxy_decisions.csv"
    )

    assert pair.source_id == "iat_case"
    assert pair.production_features_path == Path("/tmp/features.csv")
    assert pair.proxy_decisions_path == Path("/tmp/proxy_decisions.csv")


def test_feature_proxy_pair_from_run_dir_uses_standard_layout():
    pair = feature_proxy_pair_from_run_dir(Path("data/processed/runs/run_1"))

    assert pair.source_id == "run_1"
    assert pair.production_features_path == Path(
        "data/processed/runs/run_1/features/41_production/"
        "production_features.csv"
    )
    assert pair.proxy_decisions_path == Path(
        "data/processed/runs/run_1/proxy/70_decisions/"
        "proxy_decisions.csv"
    )


def test_discover_feature_proxy_pairs_runs_model_directly(
    tmp_path: Path,
    monkeypatch,
):
    features = tmp_path / "production_features.csv"
    features.write_text("timestamp,trip_id\n2026-08-01T12:00:00Z,t1\n")
    proxy = tmp_path / "proxy_decisions.csv"
    pd.DataFrame(
        [
            {
                "proxy_id": "intake_air_temperature_sensor_fault",
                "sub_check_id": "4-S1",
                "result_state": "triggered",
                "dtc_emitted": True,
                "confidence": "high",
            },
            {
                "proxy_id": "map_load_signal_plausibility_fault",
                "sub_check_id": "5-S1",
                "result_state": "pass",
                "dtc_emitted": False,
                "confidence": "high",
            },
        ]
    ).to_csv(proxy, index=False)
    calls = {}

    def fake_run_model_layer(production_path, proxy_path, output_path):
        calls["production_path"] = production_path
        calls["proxy_path"] = proxy_path
        output = {
            "summary": _model_summary(
                notes=[
                    "intake_air_temperature_sensor_fault forwarded from "
                    "Data Layer proxy_decisions.csv: 4-S1 triggered"
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
        output_path.write_text("{}")
        return output

    monkeypatch.setattr(
        "report_layer.evaluation.prompt_refinement.discovery."
        "_run_model_layer",
        fake_run_model_layer,
    )

    manifest_rows, proxy_rows = discover_feature_proxy_pairs(
        [
            FeatureProxyPair(
                "iat_case",
                features,
                proxy,
            )
        ],
        output_dir=tmp_path / "out",
    )

    assert calls["production_path"] == features
    assert calls["proxy_path"] == proxy
    assert manifest_rows[0]["source_kind"] == "feature_proxy_pair"
    assert manifest_rows[0]["selected_for_eval"] is True
    assert proxy_rows[0]["source_kind"] == "feature_proxy_pair"
