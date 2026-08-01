from model.synthetic_evaluation_metrics import compute_metrics


def row(truth, prediction, score, family, scenario="case"):
    return {
        "evaluation_role": "primary",
        "expected_anomaly_type": truth,
        "anomaly_type": prediction,
        "risk_score": score,
        "fault_family": family,
        "scenario": scenario,
        "severity": 1.0,
        "severity_unit": "test",
        "segment_id": "segment",
    }


def test_hit_requires_alarm_and_correct_attribution():
    records = [
        row(None, "cooling_degradation", 0.2, "healthy", "healthy"),
        row("cooling_degradation", "cooling_degradation", 0.8, "cooling"),
        row("air_intake_maf_anomaly", "air_intake_maf_anomaly", 0.2, "maf"),
        row("accelerator_pedal_sensor", "cooling_degradation", 0.9, "pedal"),
    ]
    result = compute_metrics(records)
    assert result["per_type"]["cooling_degradation"]["tp"] == 1
    assert result["per_type"]["cooling_degradation"]["fp"] == 1
    assert result["per_type"]["air_intake_maf_anomaly"]["fn"] == 1
    assert result["per_type"]["accelerator_pedal_sensor"]["fn"] == 1
    assert result["healthy_false_positive_rate"] == 0.0
    assert result["exact_hit_rate"] == 1 / 3
    assert result["attribution_accuracy_ignoring_threshold"] == 2 / 3


def test_controls_are_excluded_from_primary_metrics():
    control = row(
        "air_intake_maf_anomaly", "air_intake_maf_anomaly", 0.9,
        "map_attribution_control", "map_control",
    )
    control["evaluation_role"] = "control"
    result = compute_metrics([control])
    assert result["completed_primary_runs"] == 0
    assert len(result["controls"]) == 1
