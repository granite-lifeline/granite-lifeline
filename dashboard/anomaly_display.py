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

# GL-127 naming alignment table.
# interface_name and grounded_knowledge_key should stay the same because
# shared/interface_models.py and grounded_knowledge.yaml use the same keys.
ANOMALY_TYPE_MAPPING_TABLE = [
    {
        "interface_name": "cooling_degradation",
        "grounded_knowledge_key": "cooling_degradation",
        "dashboard_key": "cooling_degradation",
        "legacy_alias": "cooling_system_stress",
    },
    {
        "interface_name": "intake_air_temperature_sensor_or_heat_soak_fault",
        "grounded_knowledge_key":
            "intake_air_temperature_sensor_or_heat_soak_fault",
        "dashboard_key": "intake_air_temperature_sensor_or_heat_soak_fault",
        "legacy_alias": None,
    },
    {
        "interface_name": "air_intake_maf_anomaly",
        "grounded_knowledge_key": "air_intake_maf_anomaly",
        "dashboard_key": "air_intake_maf_anomaly",
        "legacy_alias": None,
    },
    {
        "interface_name": "map_load_signal_plausibility_fault",
        "grounded_knowledge_key": "map_load_signal_plausibility_fault",
        "dashboard_key": "map_load_signal_plausibility_fault",
        "legacy_alias": None,
    },
    {
        "interface_name": "electronic_throttle_tracking_fault",
        "grounded_knowledge_key": "electronic_throttle_tracking_fault",
        "dashboard_key": "electronic_throttle_tracking_fault",
        "legacy_alias": None,
    },
    {
        "interface_name": "accelerator_pedal_sensor",
        "grounded_knowledge_key": "accelerator_pedal_sensor",
        "dashboard_key": "accelerator_pedal_sensor",
        "legacy_alias": None,
    },
    {
        "interface_name": "idle_speed_control_or_surge_degradation",
        "grounded_knowledge_key": "idle_speed_control_or_surge_degradation",
        "dashboard_key": "idle_speed_control_or_surge_degradation",
        "legacy_alias": None,
    },
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
