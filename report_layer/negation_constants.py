"""
Shared negation-detection constants for
report_layer.pipeline.prompt_chain_validator and
report_layer.evaluation.report_quality_evaluator.

These two modules each implement their own _find_unnegated_phrases()
(deliberately not sharing that function itself — one is production
pipeline code, one is a standalone offline evaluation script, and
keeping the detection logic independent means either can be modified
or deployed without touching the other). The constants below are pure
data, not logic, and were previously duplicated verbatim in both
files. That duplication already caused one real bug: a raw-field-name
list drifted between the two modules ("rpm" was excluded in one but
not the other), found only because a cross-validation run happened to
score the same report with both. Sharing this data — while keeping
the two _find_unnegated_phrases() implementations and each module's
own confirmed_phrases/hedging_phrases/raw_fields lists independent —
removes that specific class of drift for negation detection without
forcing the two modules' other, already-divergent phrase lists to be
merged (a separate, bigger design decision not made here).
"""

import re
from typing import List

NEGATION_WORDS = {"no", "not", "never", "without", "n't", "unconfirmed"}

CLAUSE_BOUNDARY = re.compile(r"[.,;:]|\bbut\b|\bhowever\b|\balthough\b")

# Phrases that contain a NEGATION_WORDS trigger ("no", "without") but do
# not semantically negate what follows — some intensify certainty instead
# ("no doubt", "without question"). Masked out of the clause text before
# scanning for negation cues, the same role NegEx's pseudo-negation
# phrase list plays for clinical-note negation (Chapman et al., 2001) —
# adapted here for certainty/hedging rather than finding-presence.
PSEUDO_NEGATIONS = (
    "no doubt", "without doubt", "without question", "no question"
)


def find_unnegated_phrases(text: str, phrases: List[str]) -> List[str]:
    """Return candidate phrases that are not negated in their clause.

    Negation cues are matched as complete tokens. Substring matching would
    incorrectly treat words such as ``normal`` and ``notable`` as the cues
    ``no`` and ``not``. English contractions ending in ``n't`` are handled
    separately because they are single tokens rather than standalone words.
    """
    lower = text.lower()
    for pseudo in PSEUDO_NEGATIONS:
        lower = lower.replace(pseudo, " " * len(pseudo))

    hits: List[str] = []
    for phrase in phrases:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
        for match in pattern.finditer(lower):
            preceding = lower[:match.start()]
            boundaries = list(CLAUSE_BOUNDARY.finditer(preceding))
            clause_start = boundaries[-1].end() if boundaries else 0
            clause_words = re.findall(
                r"[a-z]+(?:['’][a-z]+)?", preceding[clause_start:]
            )
            negated = any(
                word in NEGATION_WORDS or word.endswith("n't")
                for word in clause_words
            )
            if not negated:
                hits.append(phrase)
                break
    return hits
