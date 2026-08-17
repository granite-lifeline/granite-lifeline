"""Small helpers for the Failure Prediction UI card."""


PENDING_FAILURE_PREDICTION_TEXT = (
    "A High-risk threshold projection is not available from the current "
    "trip history."
)

def is_missing_value(value) -> bool:
    """Check if a value should use the pending placeholder."""
    return value is None or value == ""


def format_failure_prediction_text(component_data: dict) -> tuple[str, bool]:
    """Return failure prediction text and whether it is real data."""
    cycles = component_data.get("estimated_cycles_to_failure")

    if is_missing_value(cycles):
        return PENDING_FAILURE_PREDICTION_TEXT, False

    trip_word = "trip" if cycles == 1 else "trips"
    return (
        f"Current trend: High risk in about {cycles} {trip_word}.",
        True,
    )


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
