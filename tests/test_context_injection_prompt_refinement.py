from shared.interface_models import KeySignal, ModelLayerOutput
from report_layer.pipeline import context_injection
from report_layer.pipeline.context_injection import (
    build_context,
    build_context_with_rag,
)


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


def test_build_context_suppresses_high_to_high_threshold_projection():
    context = build_context(
        _model_output(estimated_cycles_to_failure=4)
    )

    assert "High-risk threshold probability: 0.31%" not in context
    assert "Estimated cycles to the High-risk threshold: 4" not in context
    assert "already reached High risk" in context
    assert "Do not quote or describe either" in context
    assert "High-risk threshold probability: 0%" not in context


def test_build_context_preserves_small_probability_below_high_risk():
    context = build_context(
        _model_output(risk_level="Medium", risk_score=0.56)
    )

    assert "High-risk threshold probability: 0.31%" in context
    assert "not a calibrated probability of mechanical failure" in context


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
    assert "4-S3" not in context
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


def test_build_context_warns_low_rising_cooling_pattern_differently():
    """Low temp + abnormally fast rise is real correlated evidence, not
    the same ambiguous/weak pattern as low + falling temp — it must get
    the grounded-explanation caution, not the "avoid explaining
    mechanics" suppression, and must state the real risk level."""
    context = build_context(
        _model_output(
            anomaly_type="cooling_degradation",
            component="cooling_degradation",
            risk_score=1.0,
            risk_level="High",
            key_signals=[
                KeySignal(
                    feature="coolant_temp",
                    value=84.0,
                    unit="°C",
                    reference_range=[90.0, 95.0],
                ),
                KeySignal(
                    feature="ect_rate_180s",
                    value=5.5,
                    unit="°C/min",
                    reference_range=[0.0, 2.0],
                ),
            ],
        )
    )

    assert "Interpretation Caution:" in context
    assert "correlated evidence" in context
    assert "Connect the explanation directly to both values" in context
    assert "high-risk pattern" in context
    assert "low-risk pattern" not in context
    assert "Avoid explaining thermostat mechanics" not in context


def test_low_rising_cooling_rejects_overheating_only_retrieval(
    monkeypatch,
):
    """A metadata match must not force conflicting knowledge into context."""
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": "Thermostat stuck closed. Radiator blocked.",
            "actions": "Inspect the cooling system.",
        },
    )
    model = _model_output(
        anomaly_type="cooling_degradation",
        component="cooling_degradation",
        risk_level="High",
        risk_score=1.0,
        key_signals=[
            KeySignal(
                feature="coolant_temp",
                value=84.0,
                unit="°C",
                reference_range=[90.0, 95.0],
            ),
            KeySignal(
                feature="ect_rate_180s",
                value=5.5,
                unit="°C/min",
                reference_range=[0.0, 2.0],
            ),
        ],
    )

    context = build_context_with_rag(model)

    assert "No suitable retrieved fault knowledge" in (
        context["fault_knowledge"]
    )
    assert "Thermostat stuck closed" not in context["fault_knowledge"]
    assert "No retrieved procedure passed the relevance gate" in (
        context["actions_knowledge"]
    )


def test_low_rising_cooling_accepts_direction_neutral_retrieval(monkeypatch):
    """Relevant component knowledge remains available after the gate."""
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": (
                "A temperature-sensor reading issue or unusual cooling "
                "behaviour may produce this pattern."
            ),
            "actions": "Verify the temperature signal against the vehicle.",
        },
    )
    model = _model_output(
        anomaly_type="cooling_degradation",
        component="cooling_degradation",
        risk_level="High",
        risk_score=1.0,
        key_signals=[
            KeySignal(
                feature="coolant_temp",
                value=84.0,
                unit="°C",
                reference_range=[90.0, 95.0],
            ),
            KeySignal(
                feature="ect_rate_180s",
                value=5.5,
                unit="°C/min",
                reference_range=[0.0, 2.0],
            ),
        ],
    )

    context = build_context_with_rag(model)

    assert "temperature-sensor reading issue" in context["fault_knowledge"]
    assert "Verify the temperature signal" in context["actions_knowledge"]


def test_build_context_with_rag_governs_workshop_actions(monkeypatch):
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": "Fault knowledge text.",
            "actions": "Action guidance text.",
        },
    )

    context = build_context_with_rag(_model_output())

    assert context["fault_knowledge"] == "Fault knowledge text."
    assert "Owner decision-support policy:" in context["actions_knowledge"]
    assert "Technician evidence:" in context["actions_knowledge"]
    assert "technician-only evidence" in context["actions_knowledge"]
    assert "Action guidance text." in context["actions_knowledge"]


def test_low_cooling_rag_filters_overheating_fault_list(monkeypatch):
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": "Thermostat stuck closed. Radiator blocked.",
            "actions": "Inspect the cooling system.",
        },
    )
    model = _model_output(
        anomaly_type="cooling_degradation",
        component="cooling_degradation",
        risk_level="Low",
        risk_score=0.18,
        key_signals=[
            KeySignal(
                feature="coolant_temp",
                value=89.0,
                unit="°C",
                reference_range=[90.0, 95.0],
            )
        ],
    )

    context = build_context_with_rag(model)

    assert "No suitable retrieved fault knowledge" in (
        context["fault_knowledge"]
    )
    assert "Thermostat stuck closed" not in context["fault_knowledge"]


def test_action_governance_removes_replacement_only_guidance(monkeypatch):
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": "Fault knowledge text.",
            "actions": "Replace the mass airflow sensor\nReplace the ECM",
        },
    )

    context = build_context_with_rag(_model_output())

    assert "Replace the mass airflow sensor" not in (
        context["actions_knowledge"]
    )
    assert "action-safety and relevance filtering" in (
        context["actions_knowledge"]
    )


def test_action_governance_removes_vehicle_specific_turbo_procedure(
    monkeypatch,
):
    monkeypatch.setattr(
        context_injection,
        "retrieve_all",
        lambda anomaly_type, risk_level: {
            "description_causes": "Fault knowledge text.",
            "actions": (
                "In turbo engines, inspect the boost-pressure path and "
                "turbocharger."
            ),
        },
    )

    context = build_context_with_rag(
        _model_output(
            anomaly_type="map_load_signal_plausibility_fault",
            component="map_load_signal_plausibility_fault",
        )
    )

    assert "turbo engines" not in context["actions_knowledge"]
    assert "action-safety and relevance filtering" in (
        context["actions_knowledge"]
    )
