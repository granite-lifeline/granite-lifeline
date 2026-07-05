"""
Context injection utilities for Report Layer.

Formats Model Layer output into structured text for Granite LLM prompts.
"""

from typing import Dict

from report_layer.rag.rag_retriever import retrieve_all
from shared.interface_models import ModelLayerOutput


KNOWN_CORRELATIONS = {
    frozenset(["coolant_temp", "coolant_slope"]):
        "thermal_stress_pattern",
    frozenset(["coolant_temp", "coolant_ambient_delta"]):
        "thermal_stress_pattern",
    frozenset(["maf", "map"]): "air_intake_issue",
    frozenset(["maf", "maf_map_cohesion"]): "air_intake_issue",
    frozenset(["accel_pedal_d", "accel_pedal_e"]):
        "dual_channel_pedal_divergence",
    frozenset(["accel_pedal_d", "accel_pedal_channel_delta"]):
        "dual_channel_pedal_divergence",
    frozenset(["intake_temp", "intake_ambient_delta"]):
        "heat_soak_pattern",
    frozenset(["map", "rpm"]): "map_load_plausibility_issue",
    frozenset(["accel_pedal_d", "tps"]): "throttle_tracking_issue",
    frozenset(["accel_pedal_e", "tps"]): "throttle_tracking_issue",
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
    "heat_soak_pattern": (
        "Heat soak pattern detected — intake temperature signals "
        "are abnormal, suggesting elevated underbonnet temperatures "
        "affecting sensor readings."
    ),
    "map_load_plausibility_issue": (
        "MAP load plausibility issue detected — MAP and RPM signals "
        "are both abnormal, suggesting a manifold pressure or engine "
        "load calculation fault."
    ),
    "throttle_tracking_issue": (
        "Throttle tracking issue detected — pedal and throttle "
        "position signals are both abnormal, suggesting a "
        "drive-by-wire tracking fault."
    ),
}


def build_context(ttm_output: ModelLayerOutput) -> str:
    """
    Format ModelLayerOutput into structured text for LLM prompt injection.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Formatted context string with vehicle status, key signals, and
        Signal Correlation section when abnormal signals are detected.
        The Signal Correlation section uses known automotive fault
        correlation patterns where available.
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

        # Build signal line
        signal_line = (
            f"- {signal.feature}: {signal.value}{unit_str} "
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
            feature_names = ", ".join(s.feature for s in abnormal_signals)
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
            context_lines.append(
                f"- Single abnormal signal detected: "
                f"{abnormal_signals[0].feature}"
            )

    return "\n".join(context_lines)


def build_context_with_rag(ttm_output: ModelLayerOutput) -> Dict[str, str]:
    """
    Build context with RAG-retrieved fault knowledge from ChromaDB.

    Extends build_context() by retrieving grounded fault knowledge and
    risk-level-appropriate recommended actions from the ChromaDB
    knowledge base.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Dictionary with four keys:
        - "context": Structured vehicle status and key signals
        - "fault_knowledge": Description and causes grounded in
          automotive references
        - "actions_knowledge": Risk-level-appropriate recommended
          actions
        - "certainty_guidance": Language strength guideline based on
          prediction_confidence for controlling LLM output certainty
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
            "Use definitive language: 'indicates', 'shows', "
            "'demonstrates'"
        )
    elif prediction_confidence > 0.5:
        certainty_guidance = (
            "Use moderate language: 'suggests', 'may indicate', "
            "'could be'"
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
    }
