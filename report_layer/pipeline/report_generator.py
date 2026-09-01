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
import re
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
    ReportLayerOutput,
    RiskHistoryEntry,
)
from report_layer.pipeline.context_injection import (  # noqa: E402
    build_context_with_rag,
)
from report_layer.pipeline.prompt_chain_validator import (  # noqa: E402
    VALIDATOR_SCORE_THRESHOLD,
    ValidationResult,
    apply_high_risk_projection_consistency,
    format_validation_summary,
    validate_chain,
    validate_layer1,
    validate_layer2,
    validate_layer3,
)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL = "granite4.1:8b"
TIMEOUT = 120
AUDIENCE = "non-technical vehicle owner"
MAX_RETRIES = 3
MAX_CORRECTION_ATTEMPTS = 1

# Below this score, prompt_chain_validator has flagged two or more
# issues on a single layer (each check costs 0.2). Chosen from real
# score distribution across 10 generated reports spanning all 5
# current anomaly types (report_layer/evaluation/qa_cross_validation/
# cross_validation_raw.json and prompt_refinement's
# selected_window_reports/): every real layer scored 1.0 or 0.8,
# never lower, so this threshold blocks only clearly bad output and
# does not fire on any of the measured real reports. call_ollama()
# runs at temperature=0 (confirmed byte-identical across 5 repeated
# runs on the same input — see commit 73d4d81). A below-threshold layer
# therefore receives one different, feedback-driven correction prompt
# instead of a blind retry. If that corrected result still fails, the
# pipeline uses its existing empty-report fallback.
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

RAW_DTC_PATTERN = re.compile(r"\b(?:DTC\s*)?P\d{4}(?:-\d+)?\b", re.IGNORECASE)
INTERNAL_RULE_PATTERN = re.compile(r"\b\d+-S\d+\b", re.IGNORECASE)

OWNER_FACING_COMPONENT_REPLACEMENTS = {
    "cooling_degradation": "cooling system pattern",
    "air_intake_maf_anomaly": "mass airflow sensor pattern",
    "accelerator_pedal_sensor": "accelerator pedal sensor",
    "intake_air_temperature_sensor_fault": (
        "intake air temperature sensor issue"
    ),
    "map_load_signal_plausibility_fault": (
        "manifold pressure sensor plausibility issue"
    ),
}


def _normal_key_signals(model_output: ModelLayerOutput) -> bool:
    """Return true when every displayed key signal is within range."""
    for signal in model_output.key_signals:
        ref_lower = signal.reference_range[0]
        ref_upper = signal.reference_range[1]
        if signal.value < ref_lower or signal.value > ref_upper:
            return False
    return True


def _has_proxy_provenance(model_output: ModelLayerOutput) -> bool:
    """Return true when Model Layer notes identify proxy forwarding."""
    return any(
        "proxy_decisions.csv" in note or "Data Layer proxy decision" in note
        for note in model_output.notes
    )


def _is_low_projection(model_output: ModelLayerOutput) -> bool:
    """Return true when the model projection is very low."""
    probability = model_output.estimated_failure_probability
    return probability is not None and probability < 0.01


def _format_example_phrase(match: re.Match[str]) -> str:
    """Convert parenthetical e.g. phrases into natural wording."""
    phrase = match.group(1).strip()
    parts = [part.strip() for part in phrase.split(",") if part.strip()]
    if len(parts) == 0:
        return ""
    if len(parts) == 1:
        return f" such as {parts[0]}"
    return f" such as {', '.join(parts[:-1])} or {parts[-1]}"


def _clean_owner_facing_text(text: str) -> str:
    """Remove owner-facing prompt artifacts that Granite may copy through."""
    cleaned = text.replace(
        "Data Layer proxy_decisions.csv",
        "Data Layer rule-based evidence",
    )
    cleaned = cleaned.replace(
        "proxy_decisions.csv",
        "rule-based evidence",
    )
    cleaned = cleaned.replace(
        "rule-based proxy evidence",
        "rule-based diagnostic evidence",
    )
    cleaned = cleaned.replace("**", "")
    cleaned = cleaned.replace("*", "")
    cleaned = RAW_DTC_PATTERN.sub("a diagnostic flag", cleaned)
    cleaned = INTERNAL_RULE_PATTERN.sub(
        "a rule-based diagnostic flag", cleaned
    )
    cleaned = re.sub(r"\bDTCs?\b", "diagnostic codes", cleaned)
    cleaned = re.sub(
        r"\b(?:air intake\s+)?MAF sensor\b",
        "mass airflow sensor",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bMAF Integral Over 180 Seconds\b|"
        r"\bmass airflow sensor integral\b",
        "accumulated mass airflow reading",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:MAF sensor |mass airflow sensor )?"
        r"Parameter Identification Data \(PID\)",
        "mass airflow sensor data",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bPID\b",
        "sensor data",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bmass airflow \(MAF\) sensor mass airflow sensor data\b|"
        r"\bmass airflow sensor \(MAF\) data\b",
        "mass airflow sensor data",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bSpeed-Density MAF Residual\b",
        "airflow consistency reading",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*\(e\.g\.,?\s*([^)]+)\)",
        _format_example_phrase,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\bi\.e\.,?\s*", "that is, ", cleaned)
    cleaned = cleaned.replace("this window", "this short driving period")
    cleaned = cleaned.replace(
        "in the near future",
        "within the stated prediction horizon",
    )
    cleaned = cleaned.replace(
        "near future",
        "stated prediction horizon",
    )
    cleaned = cleaned.replace("IAT sensor", "intake air temperature sensor")
    for raw_name, display_name in OWNER_FACING_COMPONENT_REPLACEMENTS.items():
        cleaned = cleaned.replace(raw_name, display_name)
    return cleaned


def _clean_model_aware_text(
    text: str,
    model_output: ModelLayerOutput,
) -> str:
    """Clean generated text using the current signal-status context."""
    cleaned = _clean_owner_facing_text(text)
    cleaned = re.sub(
        r"\bwithin (?:the )?(?:next )?(?:few|several|couple of) "
        r"(?:drive cycles|trips|days|weeks|months)\b",
        "soon",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not _normal_key_signals(model_output):
        cleaned = re.sub(
            r"Because the current readings still look normal,?\s*",
            "Because at least one key signal is outside its normal range, ",
            cleaned,
            flags=re.IGNORECASE,
        )
    else:
        cleaned = re.sub(
            r"\ball (?:displayed )?(?:key )?signals(?: are)?(?: currently)? "
            r"showing normal operation\b",
            "all displayed key signals are within their reference ranges",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"Although current readings [^,.]*normal,?\s*",
            "Because at least one key signal is outside its normal range, ",
            cleaned,
            flags=re.IGNORECASE,
        )
    if model_output.risk_level == "Medium":
        cleaned = re.sub(
            r"\b(?:warrants?|requires?|needs?) prompt professional "
            r"(?:inspection|verification|attention)\b",
            "should be checked soon by a professional",
            cleaned,
            flags=re.IGNORECASE,
        )
    return cleaned


def _split_sentences(text: str) -> List[str]:
    """Split owner-facing prose into sentences for conservative cleanup."""
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]


def _clean_possible_cause_text(text: str) -> str:
    """Keep possible_cause distinct from the description/projection."""
    sentences = _split_sentences(text)
    filtered = []
    dropped: List[str] = []
    # Numeric-restatement markers: only drop the sentence when it also
    # contains a digit. "risk score" in particular is also used for
    # legitimate qualitative clarification the prompts explicitly ask
    # for (e.g. "risk_score indicates severity, not a failure
    # probability") — stripping every mention of it regardless of
    # content silently deleted that clarification.
    numeric_projection_markers = (
        "failure probability",
        "probability of crossing",
        "high-risk threshold within",
        "within the next",
        "cycles to failure",
        "risk score",
    )
    # Risk-level restatement markers: dropped regardless of digits,
    # since these restate the categorical risk_level in words rather
    # than a number ("do not reclassify risk in this section").
    risk_level_markers = (
        "risk level is",
        "risk level remains",
        "overall risk level",
    )
    monitoring_markers = (
        "warrants monitoring",
        "monitoring is advisable",
        "should be monitored",
        "monitor to ensure",
    )
    has_digit = re.compile(r"\d")
    for sentence in sentences:
        lower = sentence.lower()
        if any(
            marker in lower for marker in numeric_projection_markers
        ) and has_digit.search(sentence):
            dropped.append(sentence)
            continue
        if any(marker in lower for marker in risk_level_markers):
            dropped.append(sentence)
            continue
        if any(marker in lower for marker in monitoring_markers):
            dropped.append(sentence)
            continue
        filtered.append(sentence)
    if dropped:
        logger.debug(
            "possible_cause: dropped %d redundant sentence(s): %s",
            len(dropped), dropped,
        )
    return " ".join(filtered) if filtered else text


def _clean_recommended_actions(
    actions: Any,
    model_output: ModelLayerOutput,
) -> Any:
    """Clean generated action items without changing the report schema."""
    if not isinstance(actions, list):
        return actions

    proxy_normal_low_projection = (
        _has_proxy_provenance(model_output)
        and _normal_key_signals(model_output)
        and _is_low_projection(model_output)
    )
    cleaned_actions = []
    service_timing = {
        "Low": (
            "Service timing: Continue routine monitoring and arrange an "
            "inspection if the pattern persists or worsens."
        ),
        "Medium": (
            "Service timing: Arrange a professional inspection soon to "
            "verify the reported pattern."
        ),
        "High": (
            "Service timing: Arrange a prompt professional inspection to "
            "verify the reported pattern."
        ),
    }
    for action in actions:
        if not isinstance(action, str):
            cleaned_actions.append(action)
            continue
        cleaned = _clean_owner_facing_text(action)
        if cleaned.strip().lower().startswith("service timing:"):
            cleaned_actions.append(
                service_timing.get(model_output.risk_level, cleaned)
            )
            continue
        cleaned = re.sub(
            r"\bwithin (?:the )?(?:next )?(?:few|several|couple of) "
            r"(?:drive cycles|trips|days|weeks|months)\b",
            "soon",
            cleaned,
            flags=re.IGNORECASE,
        )
        if proxy_normal_low_projection:
            cleaned = re.sub(
                r"\boutside (?:of )?its normal range\b",
                "needing verification against live sensor readings",
                cleaned,
                flags=re.IGNORECASE,
            )
            if re.match(
                r"^\s*Avoid (?:heavy|long-distance|prolonged|sustained|"
                r"towing|high-speed)",
                cleaned,
                flags=re.IGNORECASE,
            ):
                cleaned = (
                    "Drive normally while watching for warning lights or "
                    "unusual engine behavior until the sensor is verified."
                )
        cleaned_actions.append(cleaned)
    return cleaned_actions


def _clean_notes_for_dashboard(notes: Any) -> Any:
    """Clean dashboard-visible Model Layer notes while preserving shape."""
    if not isinstance(notes, list):
        return notes
    return [
        _clean_owner_facing_text(note) if isinstance(note, str) else note
        for note in notes
    ]


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
        "format": "json",
        "options": {
            "temperature": 0,
        },
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
        "notes": _clean_notes_for_dashboard(
            model_output_dict.get("notes", [])
        ),
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
# Layer call with retry
# ---------------------------------------------------------------------------

def _call_layer_with_retry(
    layer_num: int,
    prompt: str,
    response_key: str,
) -> Optional[Any]:
    """
    Call Ollama for one prompt-chain layer, retrying on request failure
    or JSON parse/key failure.

    Args:
        layer_num: Layer number (1, 2, or 3), used only for log messages.
        prompt: Rendered prompt text for this layer.
        response_key: JSON key expected in the parsed response
            (e.g. "anomaly_description").

    Returns:
        The value at response_key once obtained, or None if every
        retry failed.
    """
    value: Optional[Any] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = call_ollama(prompt)
            parsed = extract_json(response)
            if parsed is not None and response_key in parsed:
                value = parsed[response_key]
                break
        except requests.RequestException as exc:
            # Covers Timeout/ConnectionError as well as HTTPError from
            # call_ollama()'s raise_for_status() (e.g. a transient 5xx
            # while the model is still loading) — these are just as
            # retryable as a timeout, and previously skipped retries
            # entirely, propagating straight to the empty fallback report.
            logger.warning(
                "Layer %d attempt %d/%d failed (%s): %s",
                layer_num, attempt, MAX_RETRIES, type(exc).__name__, exc,
            )
        else:
            if value is None:
                logger.warning(
                    "Layer %d attempt %d/%d: JSON parse failed",
                    layer_num, attempt, MAX_RETRIES,
                )
        if value is None and attempt < MAX_RETRIES:
            time.sleep(2)
    return value


def _build_correction_prompt(
    layer_num: int,
    original_prompt: str,
    response_key: str,
    current_value: Any,
    validation: ValidationResult,
) -> str:
    """Build a targeted prompt from one layer's validator feedback."""
    feedback = "\n".join(
        f"- {warning}" for warning in validation.warnings
    )
    current_json = json.dumps(
        {response_key: current_value},
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"You are correcting Layer {layer_num} of a vehicle-owner report.\n"
        "The original task below contains the authoritative vehicle "
        "evidence, retrieved knowledge, safety boundaries, and output "
        "format.\n\n"
        "ORIGINAL TASK\n"
        f"{original_prompt}\n\n"
        "CURRENT OUTPUT\n"
        f"{current_json}\n\n"
        "VALIDATOR FEEDBACK\n"
        f"{feedback}\n\n"
        "Correct only the listed problems. Preserve supported facts and "
        "uncertainty. Do not add a diagnosis, measurement, cause, or action "
        "that is absent from the original task. Return valid JSON only, "
        f"with exactly the key \"{response_key}\"."
    )


def _clean_layer_value(
    layer_num: int,
    value: Any,
    model_output: ModelLayerOutput,
) -> Any:
    """Apply the production owner-facing cleanup for one layer."""
    if layer_num == 1:
        return _clean_model_aware_text(str(value), model_output)
    if layer_num == 2:
        cleaned = _clean_model_aware_text(str(value), model_output)
        return _clean_possible_cause_text(cleaned)
    return _clean_recommended_actions(value, model_output)


def _validate_layer_value(
    layer_num: int,
    value: Any,
    layer1_output: str,
    risk_level: str,
) -> ValidationResult:
    """Run the relevant live quality checks for one generated layer."""
    if layer_num == 1:
        validation = validate_layer1(str(value))
    elif layer_num == 2:
        validation = validate_layer2(str(value), layer1_output)
    else:
        validation = validate_layer3(value, risk_level)
    return apply_high_risk_projection_consistency(
        validation, value, risk_level
    )


def _apply_signal_direction_check(
    validation: ValidationResult,
    text: str,
    model_output: ModelLayerOutput,
) -> ValidationResult:
    """Block a plain-language comparison that reverses supplied evidence."""
    lower = text.lower()
    if model_output.risk_level == "Medium" and re.search(
        r"\b(?:prompt|urgent|immediate)\b", lower
    ):
        validation.warnings.append(
            "Overstates Medium risk urgency; say it should be checked soon, "
            "not promptly or urgently"
        )
        validation.score = max(0.0, validation.score - 0.4)
        validation.passed = False
    for signal in model_output.key_signals:
        if signal.feature != "coolant_temp":
            continue
        low, high = signal.reference_range
        if signal.value < low and re.search(
            r"(?:coolant temperature.{0,45}(?:higher|above|elevated)|"
            r"(?:high|elevated) coolant temperature)",
            lower,
        ):
            validation.warnings.append(
                "Reverses the supplied evidence: coolant temperature is "
                "below, not above, its reference range"
            )
            validation.score = max(0.0, validation.score - 0.4)
            validation.passed = False
        elif signal.value > high and re.search(
            r"coolant temperature.{0,45}(?:lower|below)", lower
        ):
            validation.warnings.append(
                "Reverses the supplied evidence: coolant temperature is "
                "above, not below, its reference range"
            )
            validation.score = max(0.0, validation.score - 0.4)
            validation.passed = False
    return validation


def _apply_evidence_relationship_check(
    validation: ValidationResult,
    text: str,
    model_output: ModelLayerOutput,
) -> ValidationResult:
    """Check claims that depend on signal status and detection provenance."""
    lower = text.lower()
    if _normal_key_signals(model_output) and re.search(
        r"(?:\b(?:system|component|sensor|vehicle)\b.{0,35}"
        r"\b(?:operat(?:es|ing)|function(?:s|ing))\b.{0,12}"
        r"\b(?:normally|as expected|within expected limits|correctly|"
        r"adequately)\b)",
        lower,
    ):
        validation.warnings.append(
            "Normal displayed signals do not establish that the whole "
            "system or component is operating normally; state that the "
            "listed signals are within range"
        )
        validation.score = max(0.0, validation.score - 0.4)
        validation.passed = False

    if (
        _has_proxy_provenance(model_output)
        and _normal_key_signals(model_output)
        and (
            re.search(r"\b(?:high-risk\s+)?fault\b", lower)
            or re.search(
                r"\bstrongly suggest(?:s|ing)?\b.{0,45}"
                r"\b(?:sensor|mechanical)\b",
                lower,
            )
        )
    ):
        validation.warnings.append(
            "Rule-based evidence with normal displayed signals must be "
            "described as a pattern or flag requiring verification, not as "
            "a fault or strong evidence of a sensor fault"
        )
        validation.score = max(0.0, validation.score - 0.4)
        validation.passed = False
    return validation


def _apply_action_relevance_check(
    validation: ValidationResult,
    value: Any,
    model_output: ModelLayerOutput,
) -> ValidationResult:
    """Block escalation conditions copied from an unrelated component."""
    if not isinstance(value, list):
        return validation
    stop_items = [
        item.lower()
        for item in value
        if isinstance(item, str)
        and item.strip().lower().startswith(
            "stop driving and seek help if:"
        )
    ]
    if (
        model_output.anomaly_type != "accelerator_pedal_sensor"
        and any(re.search(r"\bpedals?\b|\bpedal response\b", item)
                for item in stop_items)
    ):
        validation.warnings.append(
            "The stopping condition mentions pedal response, but the current "
            "anomaly is not the accelerator pedal sensor"
        )
        validation.score = max(0.0, validation.score - 0.4)
        validation.passed = False
    return validation


def _apply_controlled_baseline_check(
    validation: ValidationResult,
    layer_num: int,
    value: Any,
    original_prompt: str,
) -> ValidationResult:
    """Enforce the evidence-only boundary in the no-retrieval condition."""
    text = " ".join(value) if isinstance(value, list) else str(value)
    lower = text.lower()
    if layer_num == 2 and (
        "No retrieved fault knowledge was supplied in this controlled "
        "condition." in original_prompt
    ):
        has_boundary = re.search(
            r"\b(?:cannot|can't|not enough|insufficient|unable to)\b.{0,45}"
            r"\b(?:identify|determine|evidence|specific cause)\b",
            lower,
        )
        if not has_boundary:
            validation.warnings.append(
                "Controlled no-retrieval output must state that the supplied "
                "evidence cannot identify a specific cause"
            )
            validation.score = max(0.0, validation.score - 0.4)
            validation.passed = False
    if layer_num == 3 and (
        "No retrieved action guidance was supplied in this controlled "
        "condition." in original_prompt
    ):
        specialist_terms = re.search(
            r"\b(?:scan tool|diagnostic scan|thermostat|radiator|cooling fan|"
            r"wiring|connector|air filter|calibrat(?:e|ion)|replace)\b",
            lower,
        )
        if specialist_terms:
            validation.warnings.append(
                "Controlled no-retrieval output invents a component test or "
                "repair target"
            )
            validation.score = max(0.0, validation.score - 0.4)
            validation.passed = False
    return validation


def _enforce_controlled_baseline_boundary(
    layer_num: int,
    value: Any,
    original_prompt: str,
    model_output: ModelLayerOutput,
) -> Any:
    """Prevent parametric model knowledge entering the no-RAG stimulus."""
    if layer_num == 2 and (
        "No retrieved fault knowledge was supplied in this controlled "
        "condition." in original_prompt
    ):
        return (
            "The supplied driving data shows an unusual pattern, but it "
            "cannot identify a specific mechanical cause. A qualified "
            "mechanic would need to compare the readings with the vehicle's "
            "actual condition before deciding what, if anything, requires "
            "work."
        )
    if layer_num == 3 and isinstance(value, list) and (
        "No retrieved action guidance was supplied in this controlled "
        "condition." in original_prompt
    ):
        service_timing = {
            "Low": (
                "Service timing: Continue routine monitoring and arrange an "
                "inspection if the pattern persists or worsens."
            ),
            "Medium": (
                "Service timing: Arrange a professional inspection soon to "
                "verify the reported pattern."
            ),
            "High": (
                "Service timing: Arrange a prompt professional inspection "
                "to verify the reported pattern."
            ),
        }
        return [
            "Now: Continue normal observation and note warning lights or "
            "changes in vehicle behaviour.",
            service_timing[model_output.risk_level or "Low"],
            "Stop driving and seek help if: A warning indicates immediate "
            "danger or the vehicle becomes unsafe to control.",
            "Tell the mechanic: Investigate the reported signal pattern and "
            "verify whether it reflects a real vehicle problem before "
            "recommending any work.",
        ]
    return value


def _correct_and_validate_layer(
    layer_num: int,
    original_prompt: str,
    response_key: str,
    value: Any,
    model_output: ModelLayerOutput,
    layer1_output: str = "",
) -> Any:
    """Validate a layer and make one feedback-driven correction if needed."""
    cleaned = _clean_layer_value(layer_num, value, model_output)
    cleaned = _enforce_controlled_baseline_boundary(
        layer_num, cleaned, original_prompt, model_output
    )
    validation = _validate_layer_value(
        layer_num,
        cleaned,
        layer1_output,
        model_output.risk_level or "Low",
    )
    if layer_num in {1, 2}:
        validation = _apply_signal_direction_check(
            validation, str(cleaned), model_output
        )
    if layer_num == 1:
        validation = _apply_evidence_relationship_check(
            validation, str(cleaned), model_output
        )
    if layer_num == 3:
        validation = _apply_action_relevance_check(
            validation, cleaned, model_output
        )
    validation = _apply_controlled_baseline_check(
        validation, layer_num, cleaned, original_prompt
    )
    if validation.score >= VALIDATOR_SCORE_THRESHOLD:
        return cleaned

    logger.warning(
        "Layer %d scored %.2f; requesting one targeted correction: %s",
        layer_num,
        validation.score,
        "; ".join(validation.warnings),
    )
    corrected = cleaned
    for _ in range(MAX_CORRECTION_ATTEMPTS):
        correction_prompt = _build_correction_prompt(
            layer_num,
            original_prompt,
            response_key,
            corrected,
            validation,
        )
        corrected_response = _call_layer_with_retry(
            layer_num,
            correction_prompt,
            response_key,
        )
        if corrected_response is None:
            break
        corrected = _clean_layer_value(
            layer_num,
            corrected_response,
            model_output,
        )
        corrected = _enforce_controlled_baseline_boundary(
            layer_num, corrected, original_prompt, model_output
        )
        validation = _validate_layer_value(
            layer_num,
            corrected,
            layer1_output,
            model_output.risk_level or "Low",
        )
        if layer_num in {1, 2}:
            validation = _apply_signal_direction_check(
                validation, str(corrected), model_output
            )
        if layer_num == 1:
            validation = _apply_evidence_relationship_check(
                validation, str(corrected), model_output
            )
        if layer_num == 3:
            validation = _apply_action_relevance_check(
                validation, corrected, model_output
            )
        validation = _apply_controlled_baseline_check(
            validation, layer_num, corrected, original_prompt
        )
        if validation.score >= VALIDATOR_SCORE_THRESHOLD:
            logger.info(
                "Layer %d passed after targeted correction (score %.2f)",
                layer_num,
                validation.score,
            )
            return corrected

    raise RuntimeError(
        f"Layer {layer_num} remained below the validation threshold after "
        f"targeted correction (score {validation.score:.2f}): "
        f"{'; '.join(validation.warnings)}"
    )


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
        if risk_history is not None:
            try:
                validated_history = [
                    RiskHistoryEntry(**entry).model_dump()
                    for entry in risk_history
                ]
            except Exception:
                risk_history = None
                raise
            risk_history = validated_history

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
        anomaly_description_raw = _call_layer_with_retry(
            1, prompt1, "anomaly_description"
        )

        if anomaly_description_raw is None:
            raise RuntimeError(
                f"Layer 1 failed after {MAX_RETRIES} retries"
            )
        anomaly_description = _correct_and_validate_layer(
            1,
            prompt1,
            "anomaly_description",
            anomaly_description_raw,
            validated,
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
        possible_cause_raw = _call_layer_with_retry(
            2, prompt2, "possible_cause"
        )

        if possible_cause_raw is None:
            raise RuntimeError(
                f"Layer 2 failed after {MAX_RETRIES} retries"
            )
        possible_cause = _correct_and_validate_layer(
            2,
            prompt2,
            "possible_cause",
            possible_cause_raw,
            validated,
            anomaly_description,
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
        recommended_action_raw = _call_layer_with_retry(
            3, prompt3, "recommended_action"
        )

        if recommended_action_raw is None:
            raise RuntimeError(
                f"Layer 3 failed after {MAX_RETRIES} retries"
            )
        recommended_action = _correct_and_validate_layer(
            3,
            prompt3,
            "recommended_action",
            recommended_action_raw,
            validated,
            anomaly_description,
        )

        # Step 4b: Revalidate the complete cleaned chain as a final
        # defence-in-depth check after the sequential per-layer gates.
        validation_results = validate_chain(
            anomaly_description,
            possible_cause,
            recommended_action,
            validated.risk_level or "Low",
        )
        if not all(result.passed for result in validation_results):
            logger.warning(
                "Prompt chain validation flagged issues:\n%s",
                format_validation_summary(validation_results),
            )
        failing_layers = [
            result.layer
            for result in validation_results
            if result.score < VALIDATOR_SCORE_THRESHOLD
        ]
        if failing_layers:
            raise RuntimeError(
                f"Prompt chain validation blocked the report: "
                f"layer(s) {failing_layers} scored below "
                f"{VALIDATOR_SCORE_THRESHOLD}.\n"
                f"{format_validation_summary(validation_results)}"
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
            "notes": _clean_notes_for_dashboard(
                summary_payload.get("notes", [])
            ),
            # Report Layer maintained fields
            "risk_history": risk_history,
            # Generated fields
            "anomaly_description": anomaly_description,
            "possible_cause": possible_cause,
            "recommended_action": recommended_action,
        }
        return ReportLayerOutput(**result).model_dump()

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
