"""Display labels for dashboard anomaly types."""

# The seven canonical anomaly types are copied from
# shared/ground_knowledge/grounded_knowledge.yaml proxy_failures.
GROUND_KNOWLEDGE_ANOMALY_TYPES = [
    "cooling_degradation",
    "intake_air_temperature_sensor_or_heat_soak_fault",
    "air_intake_maf_anomaly",
    "map_load_signal_plausibility_fault",
    "electronic_throttle_tracking_fault",
    "accelerator_pedal_sensor",
    "idle_speed_control_or_surge_degradation",
]

# Keep the previous dashboard key as a display alias so older mock/report data
# still renders instead of falling back to a raw technical label.
LEGACY_COMPONENT_ALIASES = {
    "cooling_system_stress": "cooling_degradation",
}

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
