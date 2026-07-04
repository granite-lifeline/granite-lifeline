"""
Context injection utilities for Report Layer.

Formats Model Layer output into structured text for Granite LLM prompts.
"""

from typing import Dict

from report_layer.rag.rag_retriever import retrieve_all
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
