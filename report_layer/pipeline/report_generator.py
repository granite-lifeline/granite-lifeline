"""
Production pipeline for GL-241: connects Model Layer output to
RAG-grounded diagnostic report generation.

This module implements generate_report(), the main public function
that accepts a ModelLayerOutput-compatible dict, runs the three-layer
Granite prompt chain with RAG context, and returns a
ReportLayerOutput-compatible dict.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

# Resolve project root so imports work regardless of CWD
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.interface_models import (  # noqa: E402
    BatchModelLayerOutput,
    ModelLayerOutput,
)
from report_layer.pipeline.context_injection import (  # noqa: E402
    build_context_with_rag,
)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL = "granite4.1:8b"
TIMEOUT = 120
AUDIENCE = "non-technical vehicle owner"
MAX_RETRIES = 3

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_VALUES = {
    "fault_knowledge": (
        "No retrieved fault knowledge was available for this run."
    ),
    "actions_knowledge": (
        "No retrieved action guidance was available for this run."
    ),
    "certainty_guidance": (
        "Use careful wording and do not present predictions as "
        "confirmed faults."
    ),
}


# ---------------------------------------------------------------------------
# Helper functions (self-contained copies from scenario_evaluation.py)
# ---------------------------------------------------------------------------

def render_prompt(
    template: str, values: Dict[str, Any]
) -> str:
    """Replace prompt placeholders with available values."""
    prompt_values = DEFAULT_PROMPT_VALUES.copy()
    prompt_values.update(values)
    prompt = template
    for key, value in prompt_values.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    return prompt


def load_prompt_template(layer: int) -> str:
    """Load prompt template for the specified layer (1, 2, or 3)."""
    filename = f"layer{layer}_"
    if layer == 1:
        filename += "description.txt"
    elif layer == 2:
        filename += "cause.txt"
    elif layer == 3:
        filename += "action.txt"
    else:
        raise ValueError(f"Invalid layer: {layer}")

    template_path = (
        PROJECT_ROOT / "report_layer" / "prompts" / filename
    )
    with open(template_path, "r") as f:
        return f.read()


def extract_json(
    response_text: str,
) -> Optional[Dict[str, Any]]:
    """Extract JSON from response text with fallback."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def call_ollama(prompt: str) -> str:
    """Call Ollama API and return response text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(
        OLLAMA_API_URL,
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()
    return result.get("response", "")


# ---------------------------------------------------------------------------
# Fallback builder
# ---------------------------------------------------------------------------

def _build_empty_report(
    model_output_dict: Dict[str, Any],
    risk_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a ReportLayerOutput-compatible dict with empty generated
    fields.

    Used as a fallback when the pipeline fails. All pass-through
    fields from ModelLayerOutput are preserved. Generated fields
    (anomaly_description, possible_cause, recommended_action) are
    set to empty values.

    Args:
        model_output_dict: Raw ModelLayerOutput-compatible dict.
        risk_history: Optional batch-window trend entries.

    Returns:
        ReportLayerOutput-compatible dict with empty report content.
    """
    return {
        # Pass-through fields from ModelLayerOutput
        "timestamp": model_output_dict.get("timestamp", ""),
        "risk_score": model_output_dict.get("risk_score", 0.0),
        "risk_level": model_output_dict.get("risk_level"),
        "component": model_output_dict.get("component", ""),
        "prediction_confidence": model_output_dict.get(
            "prediction_confidence", 0.0
        ),
        "key_signals": model_output_dict.get("key_signals", []),
        "estimated_cycles_to_failure": model_output_dict.get(
            "estimated_cycles_to_failure"
        ),
        "estimated_failure_probability": model_output_dict.get(
            "estimated_failure_probability"
        ),
        "notes": model_output_dict.get("notes", []),
        # Report Layer maintained fields
        "risk_history": risk_history,
        # Generated fields — empty (fallback)
        "anomaly_description": "",
        "possible_cause": "",
        "recommended_action": [],
    }


def _extract_summary_payload(
    model_output: Dict[str, Any]
) -> Dict[str, Any]:
    """Return the single-window payload from either supported input shape."""
    if (
        isinstance(model_output, dict)
        and isinstance(model_output.get("summary"), dict)
        and isinstance(model_output.get("windows"), list)
    ):
        # Validate the full envelope so malformed batch outputs fail cleanly.
        BatchModelLayerOutput(**model_output)
        return model_output["summary"]
    return model_output


def _extract_risk_history_payload(
    model_output: Dict[str, Any]
) -> Optional[List[Dict[str, Any]]]:
    """Return risk history entries from a batch input envelope."""
    if not (
        isinstance(model_output, dict)
        and isinstance(model_output.get("summary"), dict)
        and isinstance(model_output.get("windows"), list)
    ):
        return None

    history = []
    for window in model_output["windows"]:
        if not isinstance(window, dict):
            continue
        if "timestamp" not in window or "risk_score" not in window:
            continue
        history.append({
            "timestamp": window["timestamp"],
            "risk_score": window["risk_score"],
        })
    return history


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_report(
    model_output: Dict[str, Any],
    risk_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate a diagnostic report from Model Layer output.

    Runs the full RAG-grounded three-layer Granite prompt chain and
    returns a ReportLayerOutput-compatible dict.  This function never
    raises — any failure activates the graceful fallback path with empty
    generated report fields.

    Args:
        model_output: ModelLayerOutput-compatible dict from the
            Model Layer.
        risk_history: Optional batch-window trend entries maintained
            for Dashboard visualization.

    Returns:
        ReportLayerOutput-compatible dict with generated diagnostic
        content, or empty generated fields when fallback was used.
    """
    try:
        if risk_history is None:
            risk_history = _extract_risk_history_payload(model_output)

        # Step 0: Normalize and validate input
        try:
            summary_payload = _extract_summary_payload(model_output)
            validated = ModelLayerOutput(**summary_payload)
        except Exception as exc:
            raise ValueError(
                f"Invalid model_output: {exc}"
            ) from exc

        # Step 1: Build RAG context
        context_dict = build_context_with_rag(validated)

        # Step 2: Load prompt templates
        templates = {
            1: load_prompt_template(1),
            2: load_prompt_template(2),
            3: load_prompt_template(3),
        }

        # Step 3 + 4: Call Ollama for each layer with retry logic

        # --- Layer 1: anomaly_description ---
        prompt1 = render_prompt(
            templates[1],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "fault_knowledge": context_dict["fault_knowledge"],
                "certainty_guidance": (
                    context_dict["certainty_guidance"]
                ),
            },
        )
        anomaly_description: Optional[str] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response1 = call_ollama(prompt1)
                parsed1 = extract_json(response1)
                if (
                    parsed1 is not None
                    and "anomaly_description" in parsed1
                ):
                    anomaly_description = (
                        parsed1["anomaly_description"]
                    )
                    break
            except (
                requests.Timeout, requests.ConnectionError
            ) as exc:
                logger.warning(
                    "Layer 1 attempt %d/%d failed (%s): %s",
                    attempt, MAX_RETRIES, type(exc).__name__, exc,
                )
            else:
                if anomaly_description is None:
                    logger.warning(
                        "Layer 1 attempt %d/%d: JSON parse failed",
                        attempt, MAX_RETRIES,
                    )
            if (
                anomaly_description is None
                and attempt < MAX_RETRIES
            ):
                time.sleep(2)

        if anomaly_description is None:
            raise RuntimeError(
                f"Layer 1 failed after {MAX_RETRIES} retries"
            )

        # --- Layer 2: possible_cause ---
        prompt2 = render_prompt(
            templates[2],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_description,
                "fault_knowledge": context_dict["fault_knowledge"],
                "certainty_guidance": (
                    context_dict["certainty_guidance"]
                ),
            },
        )
        possible_cause: Optional[str] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response2 = call_ollama(prompt2)
                parsed2 = extract_json(response2)
                if (
                    parsed2 is not None
                    and "possible_cause" in parsed2
                ):
                    possible_cause = parsed2["possible_cause"]
                    break
            except (
                requests.Timeout, requests.ConnectionError
            ) as exc:
                logger.warning(
                    "Layer 2 attempt %d/%d failed (%s): %s",
                    attempt, MAX_RETRIES, type(exc).__name__, exc,
                )
            else:
                if possible_cause is None:
                    logger.warning(
                        "Layer 2 attempt %d/%d: JSON parse failed",
                        attempt, MAX_RETRIES,
                    )
            if (
                possible_cause is None
                and attempt < MAX_RETRIES
            ):
                time.sleep(2)

        if possible_cause is None:
            raise RuntimeError(
                f"Layer 2 failed after {MAX_RETRIES} retries"
            )

        # --- Layer 3: recommended_action ---
        prompt3 = render_prompt(
            templates[3],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_description,
                "possible_cause": possible_cause,
                "fault_knowledge": context_dict["fault_knowledge"],
                "actions_knowledge": (
                    context_dict["actions_knowledge"]
                ),
                "certainty_guidance": (
                    context_dict["certainty_guidance"]
                ),
            },
        )
        recommended_action: Optional[Any] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response3 = call_ollama(prompt3)
                parsed3 = extract_json(response3)
                if (
                    parsed3 is not None
                    and "recommended_action" in parsed3
                ):
                    recommended_action = (
                        parsed3["recommended_action"]
                    )
                    break
            except (
                requests.Timeout, requests.ConnectionError
            ) as exc:
                logger.warning(
                    "Layer 3 attempt %d/%d failed (%s): %s",
                    attempt, MAX_RETRIES, type(exc).__name__, exc,
                )
            else:
                if recommended_action is None:
                    logger.warning(
                        "Layer 3 attempt %d/%d: JSON parse failed",
                        attempt, MAX_RETRIES,
                    )
            if (
                recommended_action is None
                and attempt < MAX_RETRIES
            ):
                time.sleep(2)

        if recommended_action is None:
            raise RuntimeError(
                f"Layer 3 failed after {MAX_RETRIES} retries"
            )

        # Step 5: Assemble successful output
        result = {
            # Pass-through fields
            "timestamp": summary_payload.get("timestamp", ""),
            "risk_score": summary_payload.get("risk_score", 0.0),
            "risk_level": summary_payload.get("risk_level"),
            "component": summary_payload.get("component", ""),
            "prediction_confidence": summary_payload.get(
                "prediction_confidence", 0.0
            ),
            "key_signals": summary_payload.get("key_signals", []),
            "estimated_cycles_to_failure": summary_payload.get(
                "estimated_cycles_to_failure"
            ),
            "estimated_failure_probability": summary_payload.get(
                "estimated_failure_probability"
            ),
            "notes": summary_payload.get("notes", []),
            # Report Layer maintained fields
            "risk_history": risk_history,
            # Generated fields
            "anomaly_description": anomaly_description,
            "possible_cause": possible_cause,
            "recommended_action": recommended_action,
        }
        return result

    except Exception as exc:
        logger.error(
            "generate_report pipeline failed — returning empty "
            "fallback report. Error: %s",
            exc,
            exc_info=True,
        )
        fallback_source = model_output
        if isinstance(model_output, dict) and isinstance(
            model_output.get("summary"), dict
        ):
            fallback_source = model_output["summary"]
        return _build_empty_report(fallback_source, risk_history)
