"""
Prompt chain quality validator for GL-148.

This module validates output quality for each layer of the three-layer
prompt chain. It checks outputs after each LLM call and returns validation
results with warnings. Does not raise exceptions — always returns a result
so the pipeline can continue.

Task: GL-148 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

import re
from dataclasses import dataclass
from typing import Any, List

from report_layer.negation_constants import (
    CLAUSE_BOUNDARY,
    NEGATION_WORDS,
    PSEUDO_NEGATIONS,
)


def _find_unnegated_phrases(text: str, phrases: List[str]) -> List[str]:
    """
    Return the phrases from `phrases` that appear in `text` without a
    negation word earlier in the same clause.

    A bare substring/word match on a phrase like "confirmed" flags
    negated wording such as "not confirmed" or "no confirmed fault
    yet" as if it were an unhedged claim, which is the opposite of
    what it means. A fixed word-count window before the match is not
    reliable for this: real sentences such as "no specific fault has
    been confirmed yet" put four words between the negation and the
    phrase (NegEx's own tuned scope is a 0-5 token window — this
    scans back to the current clause instead, so it isn't sensitive
    to exact word count at all). Word-boundary matching also means a
    phrase embedded in a larger word (e.g. "confirmed" inside
    "unconfirmed") is not matched at all. Pseudo-negation phrases
    (PSEUDO_NEGATIONS) are masked out first, so "no doubt this is
    confirmed" is correctly read as an unhedged claim rather than a
    negated one.
    """
    lower = text.lower()
    for pseudo in PSEUDO_NEGATIONS:
        lower = lower.replace(pseudo, " " * len(pseudo))
    hits: List[str] = []
    for phrase in phrases:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
        found_unnegated = False
        for match in pattern.finditer(lower):
            preceding = lower[:match.start()]
            boundaries = list(CLAUSE_BOUNDARY.finditer(preceding))
            clause_start = boundaries[-1].end() if boundaries else 0
            clause_words = re.findall(
                r"[a-z']+", preceding[clause_start:]
            )
            negated = any(
                neg in word
                for word in clause_words
                for neg in NEGATION_WORDS
            )
            if not negated:
                found_unnegated = True
                break
        if found_unnegated:
            hits.append(phrase)
    return hits


@dataclass
class ValidationResult:
    """Validation result for a single prompt layer."""

    layer: int
    passed: bool
    warnings: List[str]
    score: float  # 0.0-1.0


def validate_layer1(output: str) -> ValidationResult:
    """
    Validate Layer 1 (anomaly_description) output.

    Checks:
    - Output is not empty or error string
    - No unexplained raw field names
    - No confirmed fault language
    - Length between 20 and 60 words

    Args:
        output: Layer 1 output string

    Returns:
        ValidationResult with layer=1
    """
    warnings = []
    passed = True
    score = 1.0

    # Check for empty or error output
    if not output or not output.strip():
        warnings.append("Layer 1 output is empty")
        passed = False
        score = 0.0
        return ValidationResult(
            layer=1,
            passed=passed,
            warnings=warnings,
            score=score
        )

    if output.strip().startswith("Error:"):
        warnings.append("Layer 1 output is an error string")
        passed = False
        score = 0.0
        return ValidationResult(
            layer=1,
            passed=passed,
            warnings=warnings,
            score=score
        )

    # Check for unexplained raw field names
    raw_field_explanations = {
        "coolant_temp": (),
        "maf": ("mass airflow", "mass air flow"),
        "map": ("manifold pressure", "manifold absolute pressure"),
        "accel_pedal_d": ("accelerator pedal",),
        "accel_pedal_e": ("accelerator pedal",),
        "tps": ("throttle position",),
    }
    lower_output = output.lower()
    for field, explanations in raw_field_explanations.items():
        # Word boundaries prevent short acronyms such as MAP from matching
        # ordinary words such as "mapping". An acronym is owner-readable when
        # its expanded component name appears in the same report section.
        if not re.search(rf"\b{re.escape(field)}\b", lower_output):
            continue
        has_explanation = any(
            explanation in lower_output for explanation in explanations
        )
        if not has_explanation:
            warnings.append(
                f"Contains unexplained raw field name: {field}"
            )
            score -= 0.2

    # Check for confirmed fault language (skipping negated wording such
    # as "not confirmed" or "no confirmed fault yet")
    confirmed_phrases = [
        "confirmed", "is definitely", "has failed", "is broken"
    ]
    unnegated_hits = _find_unnegated_phrases(output, confirmed_phrases)
    if unnegated_hits:
        warnings.append(
            f"Contains confirmed fault language: '{unnegated_hits[0]}'"
        )
        score -= 0.2

    # The Dashboard already presents detailed measurements in a separate
    # Key Signals table. Layer 1 should therefore be a short interpretation,
    # not a prose copy of every value.
    word_count = len(output.split())
    if word_count < 20:
        warnings.append(
            f"Output is too short: {word_count} words (minimum 20)"
        )
        score -= 0.2
    elif word_count > 60:
        warnings.append(
            f"Output is too long: {word_count} words (maximum 60)"
        )
        score -= 0.4

    # Owner-facing summaries should interpret the separate Key Signals table,
    # not reproduce machine precision or enumerate a second set of metrics.
    numeric_tokens = re.findall(r"-?\d+(?:\.\d+)?%?", output)
    over_precise = [
        token for token in numeric_tokens
        if re.search(r"\.\d{2,}", token)
    ]
    if over_precise:
        warnings.append(
            "Uses unnecessary numerical precision; round or describe the "
            "comparison in plain language"
        )
        score -= 0.2
    if len(numeric_tokens) > 3:
        warnings.append(
            "Repeats too many measurements; keep detailed values in Key "
            "Signals and summarise only the decision-relevant change"
        )
        score -= 0.2
    if re.search(
        r"\b(?:risk score|% score)\b|\brisk\s*\(\s*\d+(?:\.\d+)?\s*%\s*\)",
        output.lower(),
    ):
        warnings.append(
            "Restates the internal risk score; use the risk category instead"
        )
        score -= 0.4

    if re.search(
        r"\bwithin (?:the )?(?:next )?(?:few|several|couple of) "
        r"(?:drive cycles|trips|days|weeks|months)\b",
        output.lower(),
    ):
        warnings.append("Introduces an unsupported service interval")
        score -= 0.4

    # Ensure score is within bounds
    score = max(0.0, min(1.0, score))

    return ValidationResult(
        layer=1,
        passed=passed,
        warnings=warnings,
        score=score
    )


def validate_layer2(output: str, layer1_output: str) -> ValidationResult:
    """
    Validate Layer 2 (possible_cause) output.

    Checks:
    - Output is not empty or error string
    - Presence of hedging phrases
    - Absence of confirmed fault language
    - Minimum length of 20 words

    Args:
        output: Layer 2 output string
        layer1_output: Layer 1 output (for context, not currently used)

    Returns:
        ValidationResult with layer=2
    """
    warnings = []
    passed = True
    score = 1.0

    # Check for empty or error output
    if not output or not output.strip():
        warnings.append("Layer 2 output is empty")
        passed = False
        score = 0.0
        return ValidationResult(
            layer=2,
            passed=passed,
            warnings=warnings,
            score=score
        )

    if output.strip().startswith("Error:"):
        warnings.append("Layer 2 output is an error string")
        passed = False
        score = 0.0
        return ValidationResult(
            layer=2,
            passed=passed,
            warnings=warnings,
            score=score
        )

    # Check for hedging phrases. Negated-certainty wording ("not
    # confirmed", "unconfirmed") is also a valid form of hedging, even
    # though it doesn't match the phrase list below. "possible
    # explanation" is layer2_cause.txt's own canonical hedging opener
    # — it appears in five of the prompt's "Good example" blocks — but
    # was missing from this list, found via the perturbation
    # regression test on real generated output that used exactly this
    # phrasing.
    hedging_phrases = [
        "may indicate", "could suggest", "could be related to",
        "might", "possibly", "could be", "possible explanation"
    ]
    has_hedging = any(
        phrase in output.lower() for phrase in hedging_phrases
    )
    certainty_markers = ["confirmed", "definite", "certain"]
    lower_output = output.lower()
    has_negated_certainty = any(
        marker in lower_output for marker in certainty_markers
    ) and not _find_unnegated_phrases(lower_output, certainty_markers)
    if not (has_hedging or has_negated_certainty):
        warnings.append(
            "Missing hedging language (may indicate, could suggest, etc.)"
        )
        score -= 0.2

    # Check for confirmed fault language (skipping negated wording such
    # as "not confirmed" or "no confirmed fault yet")
    confirmed_phrases = [
        "confirmed", "is definitely", "has failed", "is broken"
    ]
    unnegated_hits = _find_unnegated_phrases(output, confirmed_phrases)
    if unnegated_hits:
        warnings.append(
            f"Contains confirmed fault language: '{unnegated_hits[0]}'"
        )
        score -= 0.2

    # Raised from 70: layer2_cause.txt now asks for reasoning tied to
    # specific signal values (not just a component name) and for naming
    # more than one cause when the evidence supports it, which
    # legitimately needs more room than a single terse sentence. The old
    # 70-word cap combined with this check's -0.4 penalty meant a single
    # violation alone dropped the score below VALIDATOR_SCORE_THRESHOLD
    # every time, triggering a correction that pushed length back down —
    # actively fighting the richer explanation the prompt now asks for.
    word_count = len(output.split())
    if word_count > 130:
        warnings.append(
            f"Output is too long: {word_count} words (maximum 130)"
        )
        score -= 0.4

    # Check minimum length
    word_count = len(output.split())
    if word_count < 20:
        warnings.append(
            f"Output is too short: {word_count} words (minimum 20)"
        )
        score -= 0.2

    # Ensure score is within bounds
    score = max(0.0, min(1.0, score))

    return ValidationResult(
        layer=2,
        passed=passed,
        warnings=warnings,
        score=score
    )


def validate_layer3(output: Any, risk_level: str) -> ValidationResult:
    """
    Validate Layer 3 (recommended_action) output.

    Checks:
    - If list, length is 2-4 items
    - Each item is at least 8 words
    - High risk has urgency language
    - Low risk avoids panic language

    Args:
        output: Layer 3 output (list or string)
        risk_level: Risk level string (High/Medium/Low)

    Returns:
        ValidationResult with layer=3
    """
    warnings = []
    passed = True
    score = 1.0

    # Convert to list if string
    if isinstance(output, str):
        if not output or output.strip().startswith("Error:"):
            warnings.append("Layer 3 output is empty or error string")
            passed = False
            score = 0.0
            return ValidationResult(
                layer=3,
                passed=passed,
                warnings=warnings,
                score=score
            )
        # Treat as single-item list
        actions = [output]
    elif isinstance(output, list):
        actions = output
    else:
        warnings.append(
            f"Layer 3 output has unexpected type: {type(output)}"
        )
        passed = False
        score = 0.0
        return ValidationResult(
            layer=3,
            passed=passed,
            warnings=warnings,
            score=score
        )

    # The Dashboard contract remains a list, while stable prefixes preserve
    # the four distinct decisions the owner needs from the report.
    if len(actions) < 4:
        warnings.append(
            f"Too few actions: {len(actions)} (should be exactly 4)"
        )
        score -= 0.2
    elif len(actions) > 4:
        warnings.append(
            f"Too many actions: {len(actions)} (should be exactly 4)"
        )
        score -= 0.2

    required_prefixes = (
        "now:",
        "service timing:",
        "stop driving and seek help if:",
        "tell the mechanic:",
    )
    normalized_actions = [str(action).strip().lower() for action in actions]
    for prefix in required_prefixes:
        if not any(action.startswith(prefix) for action in normalized_actions):
            warnings.append(f"Missing owner-decision action: '{prefix}'")
            score -= 0.1

    actions_text = " ".join(str(a) for a in actions).lower()
    invented_interval = re.search(
        r"\b(?:within|after|in|next)\s+(?:the\s+)?(?:\d+|few|several|"
        r"couple of)\s+"
        r"(?:days?|weeks?|months?|miles?|trips?)\b",
        actions_text,
    )
    if invented_interval:
        warnings.append(
            "Actions contain an unsupported numeric service interval"
        )
        score -= 0.4

    if re.search(r"\breplac(?:e|ing|ement)\b", actions_text):
        warnings.append(
            "Actions recommend replacement before professional verification"
        )
        score -= 0.2

    owner_actions_text = " ".join(normalized_actions[:3])
    if re.search(
        r"\b(?:inspect|check|test|clean)\b[^.]{0,45}"
        r"\b(?:sensor|wiring|connector|harness|hose)\b",
        owner_actions_text,
    ):
        warnings.append(
            "Owner actions assign a technical component check to the driver"
        )
        score -= 0.2

    # Check each action length
    for i, action in enumerate(actions, 1):
        word_count = len(str(action).split())
        if word_count < 8:
            warnings.append(
                f"Action {i} is too short: {word_count} words (minimum 8)"
            )
            score -= 0.2

    # Check urgency language for high risk
    risk_level_lower = risk_level.lower()

    if risk_level_lower == "high":
        urgency_keywords = [
            "soon", "prompt", "immediately", "avoid", "urgent"
        ]
        has_urgency = any(kw in actions_text for kw in urgency_keywords)
        if not has_urgency:
            warnings.append(
                "High risk actions lack urgency language "
                "(soon, prompt, immediately, avoid, urgent)"
            )
            score -= 0.2

    # Check for panic language in low risk
    if risk_level_lower == "low":
        panic_keywords = ["immediately", "urgent", "emergency"]
        has_panic = any(kw in actions_text for kw in panic_keywords)
        if has_panic:
            warnings.append(
                "Low risk actions contain panic language "
                "(immediately, urgent, emergency)"
            )
            score -= 0.2

    # Ensure score is within bounds
    score = max(0.0, min(1.0, score))

    return ValidationResult(
        layer=3,
        passed=passed,
        warnings=warnings,
        score=score
    )


def validate_chain(
    layer1: str,
    layer2: str,
    layer3: Any,
    risk_level: str
) -> List[ValidationResult]:
    """
    Validate all three layers of the prompt chain.

    Args:
        layer1: Layer 1 output (anomaly_description)
        layer2: Layer 2 output (possible_cause)
        layer3: Layer 3 output (recommended_action)
        risk_level: Risk level string (High/Medium/Low)

    Returns:
        List of three ValidationResult objects
    """
    result1 = validate_layer1(layer1)
    result2 = validate_layer2(layer2, layer1)
    result3 = validate_layer3(layer3, risk_level)

    return [result1, result2, result3]


def format_validation_summary(results: List[ValidationResult]) -> str:
    """
    Format validation results as a human-readable summary.

    Args:
        results: List of ValidationResult objects

    Returns:
        Formatted string suitable for console output
    """
    lines = []
    lines.append("=" * 60)
    lines.append("PROMPT CHAIN VALIDATION SUMMARY")
    lines.append("=" * 60)

    # Overall pass/fail
    all_passed = all(r.passed for r in results)
    overall_status = "PASSED" if all_passed else "FAILED"
    lines.append(f"\nOverall Status: {overall_status}")

    # Per-layer scores
    lines.append("\nLayer Scores:")
    for result in results:
        status = "✓" if result.passed else "✗"
        lines.append(
            f"  Layer {result.layer}: {status} "
            f"(score: {result.score:.2f})"
        )

    # Warnings
    total_warnings = sum(len(r.warnings) for r in results)
    lines.append(f"\nTotal Warnings: {total_warnings}")

    if total_warnings > 0:
        lines.append("\nDetailed Warnings:")
        for result in results:
            if result.warnings:
                lines.append(f"\n  Layer {result.layer}:")
                for warning in result.warnings:
                    lines.append(f"    - {warning}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage
    print("Testing prompt chain validator...\n")

    # Test case 1: Good outputs
    layer1_good = (
        "The engine cooling system is showing signs of stress. "
        "The coolant temperature (coolant_temp) has been running "
        "higher than normal, reaching 105°C when the typical range "
        "is 85-95°C. This suggests the cooling system may not be "
        "operating at full efficiency."
    )
    layer2_good = (
        "This pattern could suggest a partially blocked radiator or "
        "a failing thermostat. The elevated temperatures may indicate "
        "that coolant flow is restricted, preventing proper heat "
        "dissipation from the engine."
    )
    layer3_good = [
        "Schedule an inspection of the cooling system soon, "
        "focusing on the radiator and thermostat components.",
        "Check coolant levels and top up if necessary, using the "
        "manufacturer-recommended coolant type.",
        "Avoid extended highway driving or towing until the issue "
        "is resolved to prevent engine damage."
    ]

    results_good = validate_chain(
        layer1_good, layer2_good, layer3_good, "High"
    )
    print(format_validation_summary(results_good))

    # Test case 2: Poor outputs
    print("\n\nTesting with poor outputs...\n")
    layer1_bad = "The coolant_temp is high. The engine has failed."
    layer2_bad = "The thermostat is broken."
    layer3_bad = ["Check it"]

    results_bad = validate_chain(
        layer1_bad, layer2_bad, layer3_bad, "High"
    )
    print(format_validation_summary(results_bad))
