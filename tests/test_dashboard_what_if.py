"""Tests for dashboard What-If scenario projections."""

from __future__ import annotations

from dashboard.pages.what_if import (
    ScenarioInputs,
    project_component_risk,
)


ANOMALY_TYPES = [
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault",
]


def _inputs(style: str = "Normal") -> ScenarioInputs:
    return ScenarioInputs(
        driving_style=style,
        coolant_temp_offset=5.0,
        rpm_multiplier=1.15,
        load_stress_multiplier=1.20,
        intake_temp_offset=4.0,
    )


def test_project_component_risk_stays_in_unit_range():
    high_stress = ScenarioInputs(
        driving_style="Aggressive",
        coolant_temp_offset=20.0,
        rpm_multiplier=1.4,
        load_stress_multiplier=1.5,
        intake_temp_offset=20.0,
    )

    for anomaly_type in ANOMALY_TYPES:
        projected = project_component_risk(
            anomaly_type, baseline_score=0.95, inputs=high_stress
        )
        assert 0.0 <= projected <= 1.0


def test_aggressive_style_projects_higher_than_normal_for_all_types():
    normal = _inputs("Normal")
    aggressive = _inputs("Aggressive")

    for anomaly_type in ANOMALY_TYPES:
        normal_score = project_component_risk(anomaly_type, 0.4, normal)
        aggressive_score = project_component_risk(
            anomaly_type, 0.4, aggressive
        )
        assert aggressive_score >= normal_score


def test_conservative_style_does_not_raise_low_stress_baseline():
    conservative = ScenarioInputs(
        driving_style="Conservative",
        coolant_temp_offset=0.0,
        rpm_multiplier=1.0,
        load_stress_multiplier=1.0,
        intake_temp_offset=0.0,
    )

    for anomaly_type in ANOMALY_TYPES:
        projected = project_component_risk(
            anomaly_type, baseline_score=0.5, inputs=conservative
        )
        assert projected <= 0.5


def test_unknown_component_uses_generic_style_sensitivity():
    normal = _inputs("Normal")
    aggressive = _inputs("Aggressive")

    assert project_component_risk("unknown", 0.3, aggressive) > (
        project_component_risk("unknown", 0.3, normal)
    )
