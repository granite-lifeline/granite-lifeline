"""
Context injection utilities for Report Layer.

Formats Model Layer output into structured text for Granite LLM prompts.
Raw OBD-II field names are mapped to human-readable names before being
passed to the LLM.
"""

from typing import Dict, List, Union

from report_layer.rag.rag_retriever import retrieve_all
from shared.interface_models import ModelLayerOutput


SIGNAL_DISPLAY_NAMES = {
    "coolant_temp": "Coolant Temperature",
    "ect_start": "Coolant Temperature at Engine Start",
    "aat_start": "Ambient Temperature at Engine Start",
    "maf_integral_180s": "MAF Integral Over 180 Seconds",
    "ect_rate_180s": "Coolant Temperature Rise Rate",
    "maf": "Mass Airflow",
    "map": "Manifold Air Pressure",
    "intake_temp": "Intake Air Temperature",
    "intake_temp_stability": "Intake Temperature Stability",
    "ambient_temp": "Ambient Temperature",
    "intake_ambient_delta": "Intake-Ambient Temperature Difference",
    "segment_gap_seconds": "Segment Gap",
    "speed_std_120s": "Vehicle Speed Variation",
    "maf_std_120s": "Mass Airflow Variation",
    "accel_pedal_d": "Accelerator Pedal Position (Channel D)",
    "accel_pedal_e": "Accelerator Pedal Position (Channel E)",
    "pedal_mapping_residual": "Pedal Channel Mapping Residual",
    "pedal_slope": "Pedal Demand Rate of Change",
    "accel_pedal_channel_delta": (
        "Accelerator Pedal Channel Difference"
    ),
    "engine_on_flag": "Engine Running Indicator",
    "tps": "Throttle Position",
    "rpm": "Engine RPM",
    "rpm_slope": "RPM Rate of Change",
    "rpm_std_120s": "RPM Variation",
    "accel_pedal_mean_std_120s": "Pedal Demand Variation",
    "map_range_60s": "Manifold Pressure Range",
    "speed": "Vehicle Speed",
    "speed_density_maf_residual": "Speed-Density MAF Residual",
}


def _get_signal_display_name(feature: str) -> str:
    """Return the human-readable signal name when one is configured."""
    return SIGNAL_DISPLAY_NAMES.get(feature, feature)


KNOWN_CORRELATIONS = {
    frozenset(["coolant_temp", "ect_rate_180s"]):
        "thermal_stress_pattern",
    frozenset(["coolant_temp", "ect_start"]):
        "thermal_stress_pattern",
    frozenset(["maf", "map"]): "air_intake_issue",
    frozenset(["maf", "speed_density_maf_residual"]): "air_intake_issue",
    frozenset(["accel_pedal_d", "accel_pedal_e"]):
        "dual_channel_pedal_divergence",
    frozenset(["accel_pedal_d", "accel_pedal_channel_delta"]):
        "dual_channel_pedal_divergence",
    frozenset(["pedal_mapping_residual", "accel_pedal_channel_delta"]):
        "dual_channel_pedal_divergence",
    frozenset(["intake_temp", "intake_ambient_delta"]):
        "intake_temperature_sensor_pattern",
    frozenset(["intake_temp", "intake_temp_stability"]):
        "intake_temperature_sensor_pattern",
    frozenset(["map", "rpm"]): "map_load_plausibility_issue",
    frozenset(["map", "map_range_60s"]): "map_load_plausibility_issue",
    frozenset(["map", "speed_density_maf_residual"]):
        "map_load_plausibility_issue",
}

CORRELATION_DESCRIPTIONS = {
    "thermal_stress_pattern": (
        "Thermal stress pattern detected — multiple cooling system "
        "signals are abnormal simultaneously, suggesting systemic "
        "cooling system degradation."
    ),
    "air_intake_issue": (
        "Air intake anomaly pattern detected — MAF and MAP signals "
        "are both abnormal, suggesting a systemic air intake or "
        "sensor plausibility issue."
    ),
    "dual_channel_pedal_divergence": (
        "Dual-channel pedal divergence detected — both accelerator "
        "pedal sensor channels are abnormal simultaneously, "
        "suggesting a sensor or wiring fault."
    ),
    "intake_temperature_sensor_pattern": (
        "Intake temperature sensor pattern detected — intake temperature "
        "signals are abnormal together, suggesting an intake-air "
        "temperature sensor plausibility issue."
    ),
    "map_load_plausibility_issue": (
        "MAP load plausibility issue detected — MAP and RPM signals "
        "are both abnormal, suggesting a manifold pressure or engine "
        "load calculation fault."
    ),
}


def build_context(ttm_output: ModelLayerOutput) -> str:
    """
    Format ModelLayerOutput into structured text for LLM prompt injection.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Formatted context string with vehicle status, key signals,
        Signal Correlation section when abnormal signals are detected,
        Failure Projection section when estimated_cycles_to_failure or
        estimated_failure_probability is not None, and Model Layer Notes
        section when input validation or degradation messages are
        present. The Signal Correlation section uses known automotive
        fault correlation patterns where available.
    """
    # Format risk_level with fallback for None
    risk_level = ttm_output.risk_level if ttm_output.risk_level else "Unknown"

    # Convert scores to percentages
    risk_pct = round(ttm_output.risk_score * 100)
    confidence_pct = round(ttm_output.prediction_confidence * 100)

    # Build vehicle status section
    context_lines = [
        "Vehicle Status:",
        f"- Component: {ttm_output.component}",
        f"- Risk Level: {risk_level}",
        f"- Risk Score: {risk_pct}%",
        f"- Prediction Confidence: {confidence_pct}%",
        "",
        "Key Signals:",
    ]

    # Add each key signal with abnormality check
    abnormal_signals = []
    for signal in ttm_output.key_signals:
        # Determine if signal is abnormal
        ref_lower = signal.reference_range[0]
        ref_upper = signal.reference_range[1]
        is_abnormal = (
            signal.value < ref_lower or signal.value > ref_upper
        )
        status = "ABNORMAL" if is_abnormal else "NORMAL"

        # Collect abnormal signals for correlation analysis
        if is_abnormal:
            abnormal_signals.append(signal)

        # Format unit (omit if empty or None)
        unit_str = signal.unit if signal.unit else ""
        display_name = _get_signal_display_name(signal.feature)

        # Build signal line
        signal_line = (
            f"- {display_name}: {signal.value}{unit_str} "
            f"(reference: {ref_lower}-{ref_upper}{unit_str}) [{status}]"
        )
        context_lines.append(signal_line)

    # Add signal correlation analysis
    if len(abnormal_signals) > 0:
        # Compute set of abnormal feature names
        abnormal_feature_names = set(s.feature for s in abnormal_signals)

        # Check for known correlation patterns
        matched_patterns = []
        for pattern_features, pattern_name in KNOWN_CORRELATIONS.items():
            if pattern_features.issubset(abnormal_feature_names):
                matched_patterns.append(pattern_name)

        if matched_patterns:
            # Known correlation pattern(s) detected
            context_lines.append("")
            context_lines.append("Signal Correlation:")
            for pattern_name in matched_patterns:
                description = CORRELATION_DESCRIPTIONS[pattern_name]
                context_lines.append(f"- {description}")
        elif len(abnormal_signals) > 1:
            # Multiple abnormal but no known pattern
            context_lines.append("")
            context_lines.append("Signal Correlation:")
            feature_names = ", ".join([
                _get_signal_display_name(s.feature)
                for s in abnormal_signals
            ])
            context_lines.append(
                f"- Multiple abnormal signals detected: {feature_names}"
            )
            context_lines.append(
                "- This pattern may indicate a systemic issue affecting "
                "multiple components simultaneously."
            )
        elif len(abnormal_signals) == 1:
            # Single abnormal signal
            context_lines.append("")
            context_lines.append("Signal Correlation:")
            feature_name = _get_signal_display_name(
                abnormal_signals[0].feature
            )
            context_lines.append(
                f"- Single abnormal signal detected: "
                f"{feature_name}"
            )

    # Add Failure Projection section if prediction fields are present
    failure_prob = ttm_output.estimated_failure_probability
    cycles_to_failure = ttm_output.estimated_cycles_to_failure
    if failure_prob is not None or cycles_to_failure is not None:
        context_lines.append("")
        context_lines.append("Failure Projection:")
        if failure_prob is not None:
            prob_pct = round(failure_prob * 100)
            context_lines.append(
                f"- Failure probability: {prob_pct}%"
            )
        if cycles_to_failure is not None:
            context_lines.append(
                f"- Estimated cycles to failure: "
                f"{cycles_to_failure} drive cycles"
            )

    # Add Model Layer Notes section if notes are present
    if ttm_output.notes:
        context_lines.append("")
        context_lines.append("Model Layer Notes:")
        context_lines.append(
            "- These notes describe input data quality, repaired "
            "values, or disabled detections. They are not mechanical "
            "fault causes by themselves."
        )
        for note in ttm_output.notes:
            context_lines.append(f"- {note}")

    return "\n".join(context_lines)


def build_context_with_rag(
    ttm_output: ModelLayerOutput
) -> Dict[str, Union[str, List[str]]]:
    """
    Build context with RAG-retrieved fault knowledge from ChromaDB.

    Extends build_context() by retrieving grounded fault knowledge and
    risk-level-appropriate recommended actions from the ChromaDB
    knowledge base.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Dictionary with five keys:
        - "context": Structured vehicle status and key signals
        - "fault_knowledge": Description and causes grounded in
          automotive references
        - "actions_knowledge": Risk-level-appropriate recommended
          actions
        - "certainty_guidance": Language strength guideline based on
          prediction_confidence for controlling LLM output certainty
        - "notes": List of input validation and degradation messages
          from Model Layer
    """
    # Get existing context
    context = build_context(ttm_output)

    # Normalize risk level to lowercase, default to "low" if None
    risk_level = ttm_output.risk_level
    if risk_level is None:
        risk_level_normalized = "low"
    else:
        risk_level_normalized = risk_level.lower()

    # Retrieve fault knowledge from ChromaDB
    rag_knowledge = retrieve_all(
        anomaly_type=ttm_output.anomaly_type,
        risk_level=risk_level_normalized
    )

    # Determine certainty guidance based on prediction confidence
    prediction_confidence = ttm_output.prediction_confidence
    if prediction_confidence > 0.8:
        certainty_guidance = (
            "Use stronger but still predictive language: 'strongly "
            "suggests', 'is consistent with', 'shows signs of'. Do "
            "not say the fault is confirmed."
        )
    elif prediction_confidence > 0.5:
        certainty_guidance = (
            "Use moderate language: 'suggests', 'may indicate', "
            "'could be related to'"
        )
    else:
        certainty_guidance = (
            "Use cautious language: 'might suggest', 'could possibly', "
            "'requires further monitoring'"
        )

    return {
        "context": context,
        "fault_knowledge": rag_knowledge["description_causes"],
        "actions_knowledge": rag_knowledge["actions"],
        "certainty_guidance": certainty_guidance,
        "notes": ttm_output.notes if ttm_output.notes else [],
    }
