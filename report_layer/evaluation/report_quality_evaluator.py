"""
Automated report quality evaluator for GL-140.

This module evaluates generated diagnostic reports across four dimensions:
factual_grounding, readability, hedging_appropriateness, and actionability.

Task: GL-140 (sub-task of GL-110: RAG-Enhanced Diagnostic Report Generation)
Project: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import List, Tuple

NEGATION_WORDS = {"no", "not", "never", "without", "n't", "unconfirmed"}
CLAUSE_BOUNDARY = re.compile(r"[.,;:]|\bbut\b|\bhowever\b|\balthough\b")

# Phrases that contain a NEGATION_WORDS trigger ("no", "without") but do
# not semantically negate what follows — some intensify certainty instead
# ("no doubt", "without question"). Masked out of the clause text before
# scanning for negation cues, the same role NegEx's pseudo-negation
# phrase list plays for clinical-note negation (Chapman et al., 2001) —
# adapted here for certainty/hedging rather than finding-presence.
PSEUDO_NEGATIONS = ("no doubt", "without doubt", "without question", "no question")


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
class ReportQualityScore:
    """Quality score for a diagnostic report."""

    anomaly_type: str
    risk_level: str
    factual_grounding: float  # 0.0-1.0
    readability: float  # 0.0-1.0
    hedging_appropriateness: float  # 0.0-1.0
    actionability: float  # 0.0-1.0
    overall_score: float  # 0.0-1.0
    notes: List[str]


def evaluate_factual_grounding(
    report: dict,
    context: str
) -> Tuple[float, List[str]]:
    """
    Evaluate whether report is grounded in the input context.

    Checks:
    - anomaly_description references specific signal values
    - possible_cause connects to signals in context
    - recommended_action is consistent with risk_level

    Score boundaries (only the extremes are described in detail here,
    following Yamauchi et al.'s finding that precisely defining the
    top and bottom of a rubric matters far more than describing every
    intermediate point):
    - Highest (1.0): anomaly_description quotes a number that also
      appears in the input context, possible_cause uses at least one
      signal-related word (signal/reading/sensor/temperature/
      pressure/value/measurement), and recommended_action contains at
      least one risk-appropriate urgency word for any risk level.
    - Lowest (0.2, the floor given the three -0.3/-0.3/-0.2
      deductions below — this function cannot return 0.0):
      anomaly_description has no digits at all, possible_cause has
      none of the signal-related words, and recommended_action has no
      urgency wording at all.

    Args:
        report: Report dict with anomaly_description, possible_cause,
                recommended_action
        context: Input context string with signal values

    Returns:
        Tuple of (score 0.0-1.0, list of notes)
    """
    score = 1.0
    notes = []

    # Extract numbers from context (likely signal values)
    context_numbers = re.findall(r'\d+\.?\d*', context)

    # Check if anomaly_description references signal values
    desc = report.get("anomaly_description", "")
    desc_numbers = re.findall(r'\d+\.?\d*', desc)
    if not desc_numbers:
        score -= 0.3
        notes.append(
            "anomaly_description does not reference specific signal values"
        )
    elif any(num in context_numbers for num in desc_numbers):
        notes.append(
            "anomaly_description references specific signal values from "
            "context"
        )

    # Check if possible_cause connects to signals
    cause = report.get("possible_cause", "")
    signal_keywords = [
        "signal", "reading", "sensor", "temperature", "pressure",
        "value", "measurement"
    ]
    if not any(keyword in cause.lower() for keyword in signal_keywords):
        score -= 0.3
        notes.append(
            "possible_cause does not clearly connect to signal readings"
        )

    # Check if recommended_action mentions risk level appropriately
    actions = report.get("recommended_action", [])
    if isinstance(actions, list):
        actions_text = " ".join(actions).lower()
    else:
        actions_text = str(actions).lower()

    risk_keywords = {
        "high": ["prompt", "soon", "immediately", "urgent", "avoid"],
        "medium": ["soon", "check", "inspect", "schedule"],
        "low": ["monitor", "next service", "when convenient", "observe"]
    }

    # This check requires risk_level to be passed separately
    # For now, we check if any urgency language is present
    has_urgency = any(
        keyword in actions_text
        for keywords in risk_keywords.values()
        for keyword in keywords
    )
    if not has_urgency:
        score -= 0.2
        notes.append(
            "recommended_action lacks risk-appropriate urgency language"
        )

    return max(0.0, score), notes


def evaluate_readability(report: dict) -> Tuple[float, List[str]]:
    """
    Evaluate readability for non-technical vehicle owners.

    Checks:
    - Absence of unexplained raw field names
    - Absence of unexplained acronyms
    - Average sentence length in anomaly_description

    Score boundaries (extremes only, see evaluate_factual_grounding
    for why):
    - Highest (1.0): no raw field name (coolant_temp, maf, map,
      accel_pedal_d/e, tps, rpm, throttle_pos) appears anywhere in
      anomaly_description + possible_cause, no acronym
      (OBD/ECM/PCM/DTC/MAF/MAP/TPS/IAT) appears without a nearby
      parenthetical explanation, and anomaly_description's average
      sentence length is 30 words or fewer.
    - Lowest (0.2, the floor given the three -0.3/-0.3/-0.2
      deductions below — this function cannot return 0.0): at least
      one raw field name is present, at least one acronym is present
      unexplained, and the average sentence length exceeds 30 words.

    Args:
        report: Report dict with anomaly_description, possible_cause,
                recommended_action

    Returns:
        Tuple of (score 0.0-1.0, list of notes)
    """
    score = 1.0
    notes = []

    full_text = (
        report.get("anomaly_description", "") + " " +
        report.get("possible_cause", "")
    )

    # Check for unexplained raw field names. "rpm" is deliberately
    # excluded — unlike coolant_temp/maf/map/etc., "RPM" is
    # commonly-understood plain English for a car owner, not an
    # internal snake_case field name. prompt_chain_validator.py's
    # equivalent list already excludes it for the same reason; found
    # via qa_cross_validation, where this list flagged "engine RPM"
    # as unexplained jargon while the validator correctly did not.
    raw_fields = [
        "coolant_temp", "maf", "map", "accel_pedal_d",
        "accel_pedal_e", "tps", "throttle_pos"
    ]
    found_raw_fields = [
        field for field in raw_fields if field in full_text.lower()
    ]
    if found_raw_fields:
        score -= 0.3
        notes.append(
            f"Contains unexplained raw field names: "
            f"{', '.join(found_raw_fields)}"
        )

    # Check for unexplained acronyms
    acronyms = ["OBD", "ECM", "PCM", "DTC", "MAF", "MAP", "TPS", "IAT"]
    found_acronyms = []
    for acronym in acronyms:
        # Check if acronym appears without nearby explanation
        pattern = rf'\b{acronym}\b'
        if re.search(pattern, full_text):
            # Simple heuristic: if acronym appears, check if there's
            # a parenthetical explanation nearby
            context_pattern = (
                rf'{acronym}\s*\([^)]+\)|'
                rf'\([^)]*{acronym}[^)]*\)'
            )
            if not re.search(context_pattern, full_text):
                found_acronyms.append(acronym)

    if found_acronyms:
        score -= 0.3
        notes.append(
            f"Contains unexplained acronyms: {', '.join(found_acronyms)}"
        )

    # Check average sentence length in anomaly_description
    desc = report.get("anomaly_description", "")
    sentences = re.split(r'[.!?]+', desc)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_length = mean(len(s.split()) for s in sentences)
        if avg_length > 30:
            score -= 0.2
            notes.append(
                f"Average sentence length is {avg_length:.1f} words "
                f"(above 30 word threshold)"
            )
        else:
            notes.append(
                f"Average sentence length is {avg_length:.1f} words "
                f"(acceptable)"
            )

    return max(0.0, score), notes


def evaluate_hedging_appropriateness(
    report: dict
) -> Tuple[float, List[str]]:
    """
    Evaluate appropriate use of hedging language.

    Checks:
    - Presence of hedging phrases in possible_cause
    - Absence of confirmed fault language
    - anomaly_description avoids claiming confirmed fault

    Score boundaries (extremes only, see evaluate_factual_grounding
    for why):
    - Highest (1.0): possible_cause contains a hedging phrase (may
      indicate / could suggest / might / possibly / etc.) or
      negated-certainty wording (not confirmed, unconfirmed), neither
      possible_cause nor anomaly_description contains an unnegated
      confirmed/is-definitely/has-failed/is-broken/is-faulty/
      has-malfunctioned/is-damaged phrase, and anomaly_description
      contains no unnegated the-fault-is/the-problem-is/has-failed/
      is-broken/is-faulty claim.
    - Lowest (0.0, this function can reach the true floor): none of
      the above hold — no hedging anywhere, and an unnegated
      confirmed-fault claim in both possible_cause/
      anomaly_description and a separate fault claim in
      anomaly_description.

    Args:
        report: Report dict with anomaly_description, possible_cause

    Returns:
        Tuple of (score 0.0-1.0, list of notes)
    """
    score = 1.0
    notes = []

    cause = report.get("possible_cause", "").lower()
    desc = report.get("anomaly_description", "").lower()

    # Check for hedging phrases in possible_cause. Negated-certainty
    # wording ("not confirmed", "unconfirmed") is also a valid form of
    # hedging, even though it doesn't match the phrase list below —
    # without this, rephrasing "may indicate X" as "X is not
    # confirmed" was scored as if it had no hedging at all.
    hedging_phrases = [
        "may indicate", "could suggest", "could be related to",
        "might", "possibly", "may be", "could be", "suggests"
    ]
    found_hedging = [
        phrase for phrase in hedging_phrases if phrase in cause
    ]
    certainty_markers = ["confirmed", "definite", "certain"]
    has_negated_certainty = bool(
        cause
    ) and any(
        marker in cause for marker in certainty_markers
    ) and not _find_unnegated_phrases(cause, certainty_markers)
    if found_hedging or has_negated_certainty:
        if not found_hedging:
            notes.append(
                "Uses appropriate hedging via negated certainty "
                "language (e.g. 'not confirmed')"
            )
        else:
            notes.append(
                f"Uses appropriate hedging: {', '.join(found_hedging[:2])}"
            )
    else:
        score -= 0.4
        notes.append(
            "possible_cause lacks hedging language (may indicate, "
            "could suggest, etc.)"
        )

    # Check for confirmed fault language (skipping negated wording
    # such as "not confirmed" or "no confirmed fault yet" — a bare
    # substring match previously flagged "no confirmed fault yet" as
    # an unhedged claim, which is the opposite of what it says)
    confirmed_phrases = [
        "confirmed", "is definitely", "has failed", "is broken",
        "is faulty", "has malfunctioned", "is damaged"
    ]
    found_confirmed = sorted(set(
        _find_unnegated_phrases(cause, confirmed_phrases)
        + _find_unnegated_phrases(desc, confirmed_phrases)
    ))
    if found_confirmed:
        score -= 0.4
        notes.append(
            f"Contains confirmed fault language: "
            f"{', '.join(found_confirmed)}"
        )

    # Check if anomaly_description avoids claiming confirmed fault
    fault_claims = [
        "the fault is", "the problem is", "has failed",
        "is broken", "is faulty"
    ]
    if _find_unnegated_phrases(desc, fault_claims):
        score -= 0.2
        notes.append(
            "anomaly_description claims confirmed fault"
        )

    return max(0.0, score), notes


def evaluate_actionability(
    report: dict,
    risk_level: str
) -> Tuple[float, List[str]]:
    """
    Evaluate whether recommended actions are concrete and appropriate.

    Checks:
    - recommended_action has 2-4 items
    - Each action is at least 10 words
    - Urgency language matches risk_level

    Score boundaries (extremes only, see evaluate_factual_grounding
    for why):
    - Highest (1.0): recommended_action has 2 to 4 items, every item
      is at least 10 words, and at least one item contains a wording
      cue matching risk_level (High: soon/prompt/immediately/avoid/
      urgent; Medium: soon/check/inspect/schedule; Low: monitor/
      next service/when convenient/observe).
    - Lowest (0.1, the floor given the -0.3/-0.3/-0.3 deductions
      below when combined with the too-few-items case — this
      function cannot return 0.0): fewer than 2 items, at least one
      item under 10 words, and no risk-appropriate wording cue
      anywhere in the actions.

    Args:
        report: Report dict with recommended_action
        risk_level: Risk level string (Low/Medium/High)

    Returns:
        Tuple of (score 0.0-1.0, list of notes)
    """
    score = 1.0
    notes = []

    actions = report.get("recommended_action", [])
    if not isinstance(actions, list):
        actions = [str(actions)]

    # Check number of actions
    if len(actions) < 2:
        score -= 0.3
        notes.append(
            f"Only {len(actions)} action(s) provided (should be 2-4)"
        )
    elif len(actions) > 4:
        score -= 0.2
        notes.append(
            f"{len(actions)} actions provided (should be 2-4)"
        )
    else:
        notes.append(f"{len(actions)} actions provided (appropriate)")

    # Check action length
    short_actions = [
        action for action in actions if len(action.split()) < 10
    ]
    if short_actions:
        score -= 0.3
        notes.append(
            f"{len(short_actions)} action(s) are too short "
            f"(less than 10 words)"
        )

    # Check urgency language matches risk level
    actions_text = " ".join(actions).lower()
    risk_level_lower = risk_level.lower()

    urgency_keywords = {
        "high": ["soon", "prompt", "immediately", "avoid", "urgent"],
        "medium": ["soon", "check", "inspect", "schedule"],
        "low": ["monitor", "next service", "when convenient", "observe"]
    }

    expected_keywords = urgency_keywords.get(risk_level_lower, [])
    found_keywords = [
        kw for kw in expected_keywords if kw in actions_text
    ]

    if found_keywords:
        notes.append(
            f"Contains {risk_level} risk urgency language: "
            f"{', '.join(found_keywords[:2])}"
        )
    else:
        score -= 0.3
        notes.append(
            f"Lacks {risk_level} risk urgency language "
            f"(expected: {', '.join(expected_keywords[:3])})"
        )

    return max(0.0, score), notes


def evaluate_report(
    report: dict,
    context: str,
    anomaly_type: str,
    risk_level: str
) -> ReportQualityScore:
    """
    Evaluate a diagnostic report across all quality dimensions.

    Args:
        report: Report dict with anomaly_description, possible_cause,
                recommended_action
        context: Input context string
        anomaly_type: Anomaly type identifier
        risk_level: Risk level string (Low/Medium/High)

    Returns:
        ReportQualityScore dataclass instance
    """
    # Evaluate each dimension
    factual_score, factual_notes = evaluate_factual_grounding(
        report, context
    )
    readability_score, readability_notes = evaluate_readability(report)
    hedging_score, hedging_notes = evaluate_hedging_appropriateness(report)
    actionability_score, actionability_notes = evaluate_actionability(
        report, risk_level
    )

    # Compute overall score
    overall = mean([
        factual_score,
        readability_score,
        hedging_score,
        actionability_score
    ])

    # Combine all notes
    all_notes = (
        [f"Factual Grounding: {factual_score:.2f}"] + factual_notes +
        [f"Readability: {readability_score:.2f}"] + readability_notes +
        [f"Hedging: {hedging_score:.2f}"] + hedging_notes +
        [f"Actionability: {actionability_score:.2f}"] +
        actionability_notes
    )

    return ReportQualityScore(
        anomaly_type=anomaly_type,
        risk_level=risk_level,
        factual_grounding=factual_score,
        readability=readability_score,
        hedging_appropriateness=hedging_score,
        actionability=actionability_score,
        overall_score=overall,
        notes=all_notes
    )


def write_quality_report(
    scores: List[ReportQualityScore],
    output_path: Path
) -> None:
    """
    Write quality scores to a markdown file.

    Args:
        scores: List of ReportQualityScore instances
        output_path: Path to output markdown file
    """
    with open(output_path, "w") as f:
        f.write("# Report Quality Evaluation - GL-140\n\n")
        f.write("Automated quality assessment of generated diagnostic ")
        f.write("reports.\n\n")
        f.write("---\n\n")

        # Summary table
        f.write("## Summary\n\n")
        f.write("| Anomaly Type | Risk Level | Factual Grounding | ")
        f.write("Readability | Hedging | Actionability | Overall |\n")
        f.write("|--------------|------------|-------------------|")
        f.write("-------------|---------|---------------|----------|\n")

        for score in scores:
            f.write(f"| {score.anomaly_type} | {score.risk_level} | ")
            f.write(f"{score.factual_grounding:.2f} | ")
            f.write(f"{score.readability:.2f} | ")
            f.write(f"{score.hedging_appropriateness:.2f} | ")
            f.write(f"{score.actionability:.2f} | ")
            f.write(f"{score.overall_score:.2f} |\n")

        f.write("\n---\n\n")

        # Detailed sections
        f.write("## Detailed Evaluation\n\n")
        for score in scores:
            f.write(f"### {score.anomaly_type} ({score.risk_level} risk)\n\n")
            f.write(f"**Overall Score:** {score.overall_score:.2f}\n\n")
            f.write("**Notes:**\n\n")
            for note in score.notes:
                f.write(f"- {note}\n")
            f.write("\n")


if __name__ == "__main__":
    # Load scenario files
    eval_dir = Path(__file__).parent
    scenario_files = [
        "typical_cooling_stress.json",
        "atypical_cooling_stress.json",
        "contradictory_cooling_stress.json"
    ]

    scores = []
    for filename in scenario_files:
        filepath = eval_dir / filename
        with open(filepath, "r") as f:
            data = json.load(f)

        # Extract necessary fields
        anomaly_type = data.get("anomaly_type", "unknown")
        risk_level = data.get("risk_level", "Unknown")

        # Build context string (simplified)
        context = f"Risk Level: {risk_level}\n"
        for signal in data.get("key_signals", []):
            context += (
                f"{signal['feature']}: {signal['value']} "
                f"(reference: {signal['reference_range']})\n"
            )

        # Create mock report (in real usage, this would be generated)
        # For now, we'll create a placeholder
        report = {
            "anomaly_description": (
                f"Scenario {filename}: Risk level is {risk_level}"
            ),
            "possible_cause": "This is a test evaluation",
            "recommended_action": [
                "Action 1 placeholder text",
                "Action 2 placeholder text"
            ]
        }

        # Evaluate
        score = evaluate_report(report, context, anomaly_type, risk_level)
        scores.append(score)

    # Write report
    output_path = eval_dir / "report_quality_scores.md"
    write_quality_report(scores, output_path)
    print(f"Quality report written to: {output_path}")
