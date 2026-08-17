"""Small helpers for the Failure Prediction UI card."""


PENDING_FAILURE_PREDICTION_TEXT = (
    "A High-risk threshold projection is not available from the current "
    "trip history."
)

ALREADY_HIGH_RISK_TEXT = (
    "This component has already reached the High-risk threshold based "
    "on the current pattern. Arrange a professional inspection soon."
)

# estimated_failure_probability is the model's probability of crossing the
# High-risk threshold within this fixed horizon. It is computed
# independently from estimated_cycles_to_failure (a separate linear trend
# extrapolation with no fixed horizon) — the two numbers are not two views
# of the same estimate, and must not be phrased as if one derives from the
# other. See docs/adr for the Model Layer's confirmed field definitions.
PROBABILITY_HORIZON_TRIPS = 10


def is_missing_value(value) -> bool:
    """Check if a value should use the pending placeholder."""
    return value is None or value == ""


def _format_percentage(value: float) -> str:
    """Format a unit probability as a percentage, keeping small values
    visible."""
    percent = value * 100
    if 0 < percent < 1:
        return f"{percent:.2f}%"
    if percent == round(percent):
        return f"{int(round(percent))}%"
    return f"{percent:.1f}%"


def format_failure_prediction_text(component_data: dict) -> tuple[str, bool]:
    """Return failure prediction text and whether it is real data.

    estimated_cycles_to_failure and estimated_failure_probability are
    independent estimates (confirmed with Model Layer) and are shown as
    two separate statements, each naming its own horizon, so neither
    reads as if it were derived from the other.

    "Chance of crossing into High risk" and "High risk expected around
    trip N" are both statements about *reaching* High risk — neither
    makes sense once risk_level is already High. Model Layer output can
    still carry a small non-null residual probability even at High risk
    (real data has scored e.g. a High-risk case at 0.001), so this must
    be checked explicitly rather than assumed away by the fields being
    null. Mirrors context_injection.py's build_context(), which already
    suppresses the same threshold-crossing language in the LLM prompt
    for this exact reason ("Threshold-crossing probability is not shown
    because the current classification is already High risk").
    """
    risk_level = str(component_data.get("risk_level") or "").lower()
    if risk_level == "high":
        return ALREADY_HIGH_RISK_TEXT, True

    cycles = component_data.get("estimated_cycles_to_failure")
    probability = component_data.get("estimated_failure_probability")
    has_cycles = not is_missing_value(cycles)
    has_probability = not is_missing_value(probability)

    if not has_cycles and not has_probability:
        return PENDING_FAILURE_PREDICTION_TEXT, False

    sentences = []
    if has_probability:
        sentences.append(
            f"About {_format_percentage(probability)} chance of crossing "
            f"into High risk within the next {PROBABILITY_HORIZON_TRIPS} "
            f"trips."
        )
    if has_cycles:
        trip_word = "trip" if cycles == 1 else "trips"
        if has_probability:
            sentences.append(
                f"If the current trend continues, High risk is "
                f"expected around trip {cycles}."
            )
        else:
            sentences.append(
                f"If the current trend continues, High risk is "
                f"expected in about {cycles} {trip_word}."
            )

    return " ".join(sentences), True


def get_data_quality_notes(component_data: dict) -> list[str]:
    """Return non-empty data quality notes for display."""
    notes = component_data.get("notes", [])
    if not isinstance(notes, list):
        return []

    clean_notes = []
    for note in notes:
        note_text = str(note).strip()
        if note_text:
            clean_notes.append(note_text)
    return clean_notes
