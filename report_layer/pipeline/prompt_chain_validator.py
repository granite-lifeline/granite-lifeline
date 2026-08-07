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

NEGATION_WORDS = {"no", "not", "never", "without", "n't", "unconfirmed"}
CLAUSE_BOUNDARY = re.compile(r"[.,;:]|\bbut\b|\bhowever\b|\balthough\b")


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
    phrase. This instead scans back to the start of the current
    clause (the nearest preceding ./,/;/:/but/however/although) and
    checks that whole span for a negation cue. Word-boundary matching
    also means a phrase embedded in a larger word (e.g. "confirmed"
    inside "unconfirmed") is not matched at all.
    """
    lower = text.lower()
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
    - Minimum length of 30 words

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
    raw_fields = [
        "coolant_temp", "maf", "map", "accel_pedal_d",
        "accel_pedal_e", "tps"
    ]
    for field in raw_fields:
        # Check if field appears without nearby explanation
        if field in output.lower():
            # Simple heuristic: check if there's a parenthetical nearby
            pattern = rf'{field}\s*\([^)]+\)'
            if not re.search(pattern, output.lower()):
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

    # Check minimum length
    word_count = len(output.split())
    if word_count < 30:
        warnings.append(
            f"Output is too short: {word_count} words (minimum 30)"
        )
        score -= 0.2

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
    # though it doesn't match the phrase list below.
    hedging_phrases = [
        "may indicate", "could suggest", "could be related to",
        "might", "possibly", "could be"
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

    # Check list length
    if len(actions) < 2:
        warnings.append(
            f"Too few actions: {len(actions)} (should be 2-4)"
        )
        score -= 0.2
    elif len(actions) > 4:
        warnings.append(
            f"Too many actions: {len(actions)} (should be 2-4)"
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
    actions_text = " ".join(str(a) for a in actions).lower()
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
