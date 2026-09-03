"""
Context injection utilities for Report Layer.

Formats Model Layer output into structured text for Granite LLM prompts.
Raw OBD-II field names are mapped to human-readable names before being
passed to the LLM.
"""

import re
from typing import Dict, List, Optional, Union

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
    "intake_air_temp": "Intake Air Temperature",
    "intake_temp_stability": "Intake Temperature Stability",
    "ambient_temp": "Ambient Temperature",
    "ambient_air_temp": "Ambient Air Temperature",
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
    "throttle_position": "Throttle Position",
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
        "signals are abnormal simultaneously. Interpret this together "
        "with the risk level before describing it as degradation."
    ),
    "air_intake_issue": (
        "Air intake anomaly pattern detected — MAF and MAP signals "
        "are both abnormal and may indicate an air intake or "
        "sensor plausibility issue."
    ),
    "dual_channel_pedal_divergence": (
        "Dual-channel pedal divergence detected — both accelerator "
        "pedal sensor channels are abnormal simultaneously. This may "
        "indicate a sensor or wiring issue."
    ),
    "intake_temperature_sensor_pattern": (
        "Intake temperature sensor pattern detected — intake temperature "
        "signals are abnormal together. This may indicate an intake-air "
        "temperature sensor plausibility issue."
    ),
    "map_load_plausibility_issue": (
        "MAP load plausibility issue detected — MAP and RPM signals "
        "are both abnormal. This may indicate a manifold pressure or engine "
        "load calculation fault."
    ),
}


PROXY_PROVENANCE_MARKERS = (
    "forwarded from Data Layer proxy_decisions.csv",
    "Data Layer proxy decision",
)

RAW_DTC_PATTERN = re.compile(r"\b(?:DTC\s*)?P\d{4}(?:-\d+)?\b", re.IGNORECASE)
INTERNAL_RULE_PATTERN = re.compile(r"\b\d+-S\d+\b", re.IGNORECASE)


def _sanitize_owner_facing_prompt_text(text: str) -> str:
    """
    Remove technical artifacts before sending context/RAG text to prompts.

    The raw ModelLayerOutput remains unchanged in the final report object.
    This sanitizer only prevents owner-facing generated sections from copying
    internal filenames or raw diagnostic trouble codes out of prompt context.
    """
    sanitized = text.replace(
        "Data Layer proxy_decisions.csv",
        "Data Layer rule-based evidence",
    )
    sanitized = sanitized.replace(
        "proxy_decisions.csv",
        "rule-based evidence",
    )
    sanitized = RAW_DTC_PATTERN.sub("a diagnostic flag", sanitized)
    sanitized = INTERNAL_RULE_PATTERN.sub(
        "a rule-based diagnostic flag", sanitized
    )
    sanitized = re.sub(
        r"\bDTCs?\b",
        "diagnostic codes",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"\bfault code\b",
        "diagnostic flag",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def _sanitize_prompt_text(text: str) -> str:
    """Sanitize a retrieved RAG string before prompt injection."""
    return _sanitize_owner_facing_prompt_text(text)


NO_USABLE_FAULT_KNOWLEDGE = (
    "No suitable retrieved fault knowledge matched the current signal "
    "pattern. Do not use general model knowledge to name a specific "
    "mechanical cause; preserve the evidence boundary."
)


def _retrieved_knowledge_is_usable(
    ttm_output: ModelLayerOutput,
    fault_knowledge: str,
) -> bool:
    """Return whether retrieved fault text may enter the generation prompt.

    Retrieval is attempted for traceability, but a metadata match alone is
    not enough to justify injection. The current knowledge base is largely
    component-level. Its cooling entry is dominated by overheating faults, so
    it must not anchor a report whose measured coolant temperature is below
    range. Other supported types retain their exact anomaly-type match until
    richer signal-direction metadata is available.
    """
    candidate = fault_knowledge.strip()
    if not candidate or candidate.startswith("No specific fault knowledge"):
        return False

    cooling_pattern = _cooling_direction_pattern(ttm_output)
    if cooling_pattern in {"ambiguous", "low_rising"} and re.search(
        r"\b(?:overheat(?:ing|ed)?|high coolant temperature|"
        r"thermostat stuck closed|radiator blocked)\b",
        candidate,
        flags=re.IGNORECASE,
    ):
        return False
    return True


def _owner_decision_policy(anomaly_type: str, risk_level: str) -> str:
    """Return deterministic owner guidance for one component and risk."""
    timing = {
        "low": "routine monitoring; arrange service if the pattern persists",
        "medium": "arrange professional inspection soon",
        "high": "arrange prompt professional inspection",
    }.get(risk_level, "routine monitoring")
    component_policy = {
        "cooling_degradation": (
            "observe the temperature gauge and visible warning lights; a "
            "coolant-level check is allowed only at the marked reservoir "
            "when the engine is fully cool",
            "a red temperature warning, steam, overheating, or sudden loss "
            "of power appears",
        ),
        "air_intake_maf_anomaly": (
            "observe warning lights, idle quality, acceleration response and "
            "unexpected loss of power",
            "the engine stalls, runs very roughly, or loses power in a way "
            "that makes continued driving unsafe",
        ),
        "accelerator_pedal_sensor": (
            "observe whether acceleration response feels normal; do not "
            "inspect or manipulate sensor wiring",
            "acceleration becomes delayed, inconsistent or uncontrolled, or "
            "the vehicle enters reduced-power mode",
        ),
        "intake_air_temperature_sensor_fault": (
            "observe warning lights, idle quality, acceleration response and "
            "unexpected loss of power; do not inspect sensor wiring",
            "the engine stalls, runs very roughly, overheats, or loses power "
            "in a way that makes continued driving unsafe",
        ),
        "map_load_signal_plausibility_fault": (
            "observe warning lights, idle quality, acceleration response and "
            "unexpected loss of power; do not inspect sensor wiring or hoses",
            "the engine stalls, runs very roughly, or loses power in a way "
            "that makes continued driving unsafe",
        ),
    }
    observation, stop_conditions = component_policy.get(
        anomaly_type,
        (
            "observe warning lights and any change in vehicle behaviour",
            "a red warning or unsafe change in drivability appears",
        ),
    )
    return (
        f"Owner observation: {observation}. Service timing: {timing}. "
        f"Stop conditions: {stop_conditions}."
    )


def _govern_action_knowledge(
    actions: str, anomaly_type: str, risk_level: str
) -> str:
    """Separate owner decisions from retrieved workshop procedures.

    The source knowledge contains workshop-manual procedures. Keeping those
    passages is useful because they tell the report what a technician could
    verify, but presenting them directly to a non-technical owner can imply
    self-repair. This compatibility layer keeps the existing string field
    while assigning the retrieved material an explicit technician-only role.
    """
    sanitized = _sanitize_prompt_text(actions).strip()
    owner_policy = _owner_decision_policy(anomaly_type, risk_level)
    if not sanitized or sanitized.startswith("No specific action guidance"):
        technician_evidence = (
            "No component-specific workshop procedure was retrieved. Do not "
            "invent one; ask for general professional diagnosis if needed."
        )
    else:
        safe_lines = [
            line.strip()
            for line in sanitized.splitlines()
            if line.strip()
            and not re.search(
                r"\b(?:replace|replacement|clear (?:the )?(?:fault|"
                r"diagnostic)|relearn|in turbo engines)\b",
                line,
                flags=re.IGNORECASE,
            )
        ]
        filtered = "\n".join(safe_lines)
        if not filtered:
            filtered = (
                "No suitable verification procedure remains after action-"
                "safety and relevance filtering."
            )
        technician_evidence = (
            "The following retrieved material is technician-only evidence. "
            "Never instruct the owner to perform it, buy tools, dismantle a "
            "component, clear codes, or replace a part. Convert only relevant "
            "material into a request the owner can give a qualified "
            "mechanic:\n"
            f"{filtered}"
        )
    return (
        "Owner decision-support policy:\n"
        f"{owner_policy}\n\n"
        "Technician evidence:\n"
        f"{technician_evidence}"
    )


def _format_probability(value: float) -> str:
    """Format a unit probability without rounding small values to zero."""
    percent = value * 100
    if 0 < percent < 1:
        return f"{percent:.2f}%"
    if percent == round(percent):
        return f"{int(round(percent))}%"
    return f"{percent:.1f}%"


def _cooling_direction_pattern(
    ttm_output: ModelLayerOutput,
) -> Optional[str]:
    """Classify a low coolant-temperature reading for cooling_degradation.

    A low coolant_temp reading was previously treated as one uniform
    "ambiguous, say little" case regardless of the rise-rate signal. That
    conflated two different situations:

    - "ambiguous": temperature is low and the rise rate is not abnormally
      high (falling or within its normal range). This is genuinely weak,
      non-correlated evidence that does not match the overheating-focused
      knowledge base — keep interpretation short and cautious.
    - "low_rising": temperature is low AND the rise rate is abnormally
      high. These are two correlated abnormal signals, not one weak
      reading — real evidence that deserves a clear, grounded
      explanation connected to both values, not the same blanket
      suppression as the ambiguous case.

    Returns None when the component isn't cooling_degradation or the
    temperature reading isn't low.
    """
    if ttm_output.component != "cooling_degradation":
        return None
    coolant_temp = None
    rate = None
    for signal in ttm_output.key_signals:
        if signal.feature == "coolant_temp":
            coolant_temp = signal
        elif signal.feature == "ect_rate_180s":
            rate = signal
    is_low = (
        coolant_temp is not None
        and coolant_temp.value < coolant_temp.reference_range[0]
    )
    if not is_low:
        return None
    is_rising_fast = (
        rate is not None and rate.value > rate.reference_range[1]
    )
    return "low_rising" if is_rising_fast else "ambiguous"


def build_context(ttm_output: ModelLayerOutput) -> str:
    """
    Format ModelLayerOutput into structured text for LLM prompt injection.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Formatted context string with vehicle status, key signals,
        Signal Correlation section when abnormal signals are detected,
        Failure Projection section when estimated_cycles_to_failure or
        estimated_failure_probability is not None, Detection Provenance
        when Model Layer notes identify proxy forwarding, and Model
        Layer Notes when input validation or degradation messages are
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

    cooling_pattern = _cooling_direction_pattern(ttm_output)
    if cooling_pattern == "ambiguous":
        context_lines.append("")
        context_lines.append("Interpretation Caution:")
        context_lines.append(
            "- Cooling evidence is lower-than-expected or falling "
            "coolant temperature without high-temperature evidence. "
            "Limit interpretation to cautious possibilities such as "
            "sensor reading issue, cooling fan behavior, or insufficient "
            "evidence for a specific cause. Avoid explaining thermostat "
            f"mechanics for this {risk_level.lower()}-risk pattern."
        )
    elif cooling_pattern == "low_rising":
        context_lines.append("")
        context_lines.append("Interpretation Caution:")
        context_lines.append(
            "- Coolant temperature is below its reference range while "
            "the temperature rise rate is abnormally high — these two "
            "signals together are real, correlated evidence, not a "
            "weak or ambiguous reading. Connect the explanation "
            "directly to both values. If more than one plausible "
            "explanation applies, state each as its own short, clear "
            "point rather than one vague catch-all sentence. Do not "
            f"confirm a single mechanical diagnosis for this "
            f"{risk_level.lower()}-risk pattern."
        )

    # Add projection evidence only while the component is below High risk.
    # The fields remain in the interface for audit, but a later crossing of
    # the High threshold is not meaningful owner guidance once the current
    # classification has already reached High.
    failure_prob = ttm_output.estimated_failure_probability
    cycles_to_failure = ttm_output.estimated_cycles_to_failure
    if failure_prob is not None or cycles_to_failure is not None:
        context_lines.append("")
        if risk_level.lower() == "high":
            context_lines.append("Current Risk Context:")
            context_lines.append(
                "- The current classification has already reached High "
                "risk. Base owner guidance on the current state and ask "
                "for professional verification."
            )
            context_lines.append(
                "- Do not quote or describe either future High-threshold "
                "projection field in the owner-facing report."
            )
        else:
            context_lines.append("Risk Projection:")
            if failure_prob is not None:
                context_lines.append(
                    f"- High-risk threshold probability: "
                    f"{_format_probability(failure_prob)}"
                )
                context_lines.append(
                    "- Probability meaning: model-estimated probability of "
                    "crossing the High-risk threshold within the configured "
                    "prediction horizon; not a calibrated probability of "
                    "mechanical failure."
                )
            if cycles_to_failure is not None:
                context_lines.append(
                    f"- Estimated cycles to the High-risk threshold: "
                    f"{cycles_to_failure} drive cycles"
                )
            else:
                context_lines.append(
                    "- Estimated cycles to the High-risk threshold: "
                    "unavailable for this window."
                )

    has_proxy_provenance = any(
        any(marker in note for marker in PROXY_PROVENANCE_MARKERS)
        for note in ttm_output.notes
    )
    if has_proxy_provenance:
        context_lines.append("")
        context_lines.append("Detection Provenance:")
        context_lines.append(
            "- This detection was forwarded from Data Layer rule-based "
            "proxy evidence, not native TTM residual "
            "scoring."
        )

    # Add Model Layer Notes section if notes are present
    if ttm_output.notes:
        context_lines.append("")
        context_lines.append("Model Layer Notes:")
        context_lines.append(
            "- These notes describe input data quality, repaired values, "
            "disabled detections, or detection provenance. They are not "
            "mechanical fault causes by themselves."
        )
        for note in ttm_output.notes:
            context_lines.append(
                f"- {_sanitize_owner_facing_prompt_text(note)}"
            )

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

    candidate_fault_knowledge = _sanitize_prompt_text(
        rag_knowledge["description_causes"]
    )
    use_retrieved_knowledge = _retrieved_knowledge_is_usable(
        ttm_output, candidate_fault_knowledge
    )

    if not use_retrieved_knowledge:
        fault_knowledge = NO_USABLE_FAULT_KNOWLEDGE
        owner_policy = _owner_decision_policy(
            ttm_output.anomaly_type, risk_level_normalized
        )
        actions_knowledge = (
            "Owner decision-support policy:\n"
            f"{owner_policy}\n\n"
            "Technician evidence:\nNo retrieved procedure passed the "
            "relevance gate for this signal pattern. Ask a qualified mechanic "
            "to verify the reported signals and the vehicle's actual "
            "condition before deciding what, if anything, requires work."
        )
    else:
        fault_knowledge = candidate_fault_knowledge
        actions_knowledge = _govern_action_knowledge(
            rag_knowledge["actions"],
            ttm_output.anomaly_type,
            risk_level_normalized,
        )

    return {
        "context": _sanitize_owner_facing_prompt_text(context),
        "fault_knowledge": fault_knowledge,
        "actions_knowledge": actions_knowledge,
        "certainty_guidance": certainty_guidance,
        "notes": ttm_output.notes if ttm_output.notes else [],
    }
