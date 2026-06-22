"""
Context injection utilities for Report Layer.

Formats Model Layer output into structured text for Granite LLM prompts.
"""

from shared.interface_models import ModelLayerOutput


def build_context(ttm_output: ModelLayerOutput) -> str:
    """
    Format ModelLayerOutput into structured text for LLM prompt injection.

    Args:
        ttm_output: Model Layer output containing predictions and signals

    Returns:
        Formatted context string with vehicle status and key signals
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
    for signal in ttm_output.key_signals:
        # Determine if signal is abnormal
        ref_lower = signal.reference_range[0]
        ref_upper = signal.reference_range[1]
        is_abnormal = (
            signal.value < ref_lower or signal.value > ref_upper
        )
        status = "ABNORMAL" if is_abnormal else "NORMAL"

        # Format unit (omit if empty or None)
        unit_str = signal.unit if signal.unit else ""

        # Build signal line
        signal_line = (
            f"- {signal.feature}: {signal.value}{unit_str} "
            f"(reference: {ref_lower}-{ref_upper}{unit_str}) [{status}]"
        )
        context_lines.append(signal_line)

    return "\n".join(context_lines)
