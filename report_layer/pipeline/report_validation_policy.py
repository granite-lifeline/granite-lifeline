"""Input-aware validation policies for generated report sections."""

import re
from typing import Any

from report_layer.negation_constants import find_unnegated_phrases
from report_layer.pipeline.owner_facing_cleanup import (
    _has_proxy_provenance,
    _normal_key_signals,
)
from report_layer.pipeline.prompt_chain_validator import (
    ValidationResult,
    apply_high_risk_projection_consistency,
    validate_layer1,
    validate_layer2,
    validate_layer3,
)
from shared.interface_models import ModelLayerOutput


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
    urgent_terms = find_unnegated_phrases(
        lower, ["prompt", "urgent", "immediate"]
    )
    if model_output.risk_level == "Medium" and urgent_terms:
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
        and any(
            re.search(r"\bpedals?\b|\bpedal response\b", item)
            for item in stop_items
        )
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
