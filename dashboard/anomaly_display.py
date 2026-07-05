"""Display labels for dashboard anomaly types."""

from shared.anomaly_mapping import (
    GROUND_KNOWLEDGE_ANOMALY_TYPES,
    LEGACY_COMPONENT_ALIASES,
)

__all__ = [
    "COMPONENT_DISPLAY_NAMES",
    "GROUND_KNOWLEDGE_ANOMALY_TYPES",
    "LEGACY_COMPONENT_ALIASES",
]

COMPONENT_DISPLAY_NAMES = {
    "cooling_degradation": "Cooling System",
    "cooling_system_stress": "Cooling System",
    "intake_air_temperature_sensor_or_heat_soak_fault":
        "Intake Air Temperature",
    "air_intake_maf_anomaly": "Air Intake System",
    "map_load_signal_plausibility_fault": "MAP Load Signal",
    "electronic_throttle_tracking_fault": "Electronic Throttle",
    "accelerator_pedal_sensor": "Accelerator Pedal",
    "idle_speed_control_or_surge_degradation": "Idle Speed Control",
}
