"""Shared anomaly type naming tables."""

# The five current anomaly types follow docs/INTERFACE.md v1.0.
GROUND_KNOWLEDGE_ANOMALY_TYPES = [
    "cooling_degradation",
    "intake_air_temperature_sensor_fault",
    "air_intake_maf_anomaly",
    "map_load_signal_plausibility_fault",
    "accelerator_pedal_sensor",
]

# GL-127 naming alignment table.
# interface_name and grounded_knowledge_key should stay the same because
# shared/interface_models.py and Dashboard use the same current keys.
ANOMALY_TYPE_MAPPING_TABLE = [
    {
        "interface_name": "cooling_degradation",
        "grounded_knowledge_key": "cooling_degradation",
        "dashboard_key": "cooling_degradation",
        "legacy_alias": "cooling_system_stress",
    },
    {
        "interface_name": "intake_air_temperature_sensor_fault",
        "grounded_knowledge_key": "intake_air_temperature_sensor_fault",
        "dashboard_key": "intake_air_temperature_sensor_fault",
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
        "interface_name": "accelerator_pedal_sensor",
        "grounded_knowledge_key": "accelerator_pedal_sensor",
        "dashboard_key": "accelerator_pedal_sensor",
        "legacy_alias": None,
    },
]

# Keep the previous dashboard key as an alias so older mock/report data can
# still be displayed instead of falling back to a raw technical label.
LEGACY_COMPONENT_ALIASES = {
    "cooling_system_stress": "cooling_degradation",
}
