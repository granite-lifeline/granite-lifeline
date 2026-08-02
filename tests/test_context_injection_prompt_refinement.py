from shared.interface_models import KeySignal, ModelLayerOutput
from report_layer.pipeline.context_injection import build_context


def _model_output(**overrides):
    data = {
        "timestamp": "2026-08-01T12:00:00Z",
        "anomaly_type": "intake_air_temperature_sensor_fault",
        "risk_score": 0.9,
        "risk_level": "High",
        "component": "intake_air_temperature_sensor_fault",
        "prediction_confidence": 0.9,
        "key_signals": [
            KeySignal(
                feature="intake_temp",
                value=19.0,
                unit="°C",
                reference_range=[-3.0, 41.0],
            )
        ],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": 0.0031,
        "notes": [],
    }
    data.update(overrides)
    return ModelLayerOutput(**data)


def test_build_context_does_not_round_small_probability_to_zero():
    context = build_context(_model_output())

    assert "Failure probability: 0.31%" in context
    assert "not a calibrated probability of mechanical failure" in context
    assert "Estimated cycles to failure: unavailable" in context
    assert "Failure probability: 0%" not in context


def test_build_context_adds_proxy_detection_provenance():
    context = build_context(
        _model_output(notes=[
            "intake_air_temperature_sensor_fault forwarded from "
            "Data Layer proxy_decisions.csv: 4-S3 triggered"
        ])
    )

    assert "Detection Provenance:" in context
    assert "rule-based proxy evidence" in context
    assert "proxy_decisions.csv" not in context
    assert "not native TTM residual scoring" in context


def test_build_context_warns_against_overheating_for_low_cooling_pattern():
    context = build_context(
        _model_output(
            anomaly_type="cooling_degradation",
            component="cooling_degradation",
            risk_score=0.18,
            risk_level="Low",
            key_signals=[
                KeySignal(
                    feature="coolant_temp",
                    value=89.0,
                    unit="°C",
                    reference_range=[90.0, 95.0],
                ),
                KeySignal(
                    feature="ect_rate_180s",
                    value=-0.29,
                    unit="°C/min",
                    reference_range=[0.0, 2.0],
                ),
            ],
        )
    )

    assert "Interpretation Caution:" in context
    assert "without high-temperature evidence" in context
    assert "insufficient evidence for a specific cause" in context
    assert "Avoid explaining thermostat mechanics" in context
