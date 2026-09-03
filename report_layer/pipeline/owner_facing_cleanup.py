"""Owner-facing text cleanup for generated diagnostic reports."""

import logging
import re
from typing import Any, List

from shared.interface_models import ModelLayerOutput


logger = logging.getLogger(__name__)

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
    cleaned = re.sub(
        r"rule[-\u2010-\u2015]based proxy evidence",
        "rule-based diagnostic evidence",
        cleaned,
        flags=re.IGNORECASE,
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
            r"\bdespite all displayed key signals are within their "
            r"reference ranges\b",
            "although all displayed key signals are within their reference "
            "ranges",
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
        cleaned = re.sub(
            r"\bprompt\b",
            "timely",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(?:promptly|urgently|immediately)\b",
            "soon",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(
        r"\b(?:with|at)\s+\d+(?:\.\d+)?%\s+(?:prediction\s+)?"
        r"confidence\b,?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:prediction\s+)?confidence\s+(?:of|is|was)\s+"
        r"\d+(?:\.\d+)?%\b,?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:this result\s+)?(?:has|had)\s+\d+(?:\.\d+)?%\s+"
        r"(?:prediction\s+)?confidence\b,?\s*(?:and\s+)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*\(\s*\d+(?:\.\d+)?%\s+(?:prediction\s+)?confidence\s*\)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned
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
    numeric_projection_markers = (
        "failure probability",
        "probability of crossing",
        "high-risk threshold within",
        "within the next",
        "cycles to failure",
        "risk score",
    )
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
        if (
            model_output.anomaly_type != "accelerator_pedal_sensor"
            and cleaned.strip().lower().startswith(
                "stop driving and seek help if:"
            )
            and re.search(
                r"\bpedals?\b|\bpedal response\b",
                cleaned,
                flags=re.IGNORECASE,
            )
        ):
            cleaned = (
                "Stop driving and seek help if: A warning indicates "
                "immediate danger or the vehicle becomes unsafe to control."
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
