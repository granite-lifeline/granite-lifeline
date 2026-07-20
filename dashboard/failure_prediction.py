"""Small helpers for the Failure Prediction UI card."""


PENDING_FAILURE_PREDICTION_TEXT = (
    "Failure probability estimate pending — awaiting more drive cycles"
)


def is_missing_value(value) -> bool:
    """Check if a value should use the pending placeholder."""
    return value is None or value == ""


def format_failure_prediction_text(component_data: dict) -> tuple[str, bool]:
    """Return failure prediction text and whether it is real data."""
    probability = component_data.get("estimated_failure_probability")
    cycles = component_data.get("estimated_cycles_to_failure")

    if is_missing_value(probability) or is_missing_value(cycles):
        return PENDING_FAILURE_PREDICTION_TEXT, False

    probability_pct = int(round(probability * 100))
    trip_word = "trip" if cycles == 1 else "trips"
    return (
        f"{probability_pct}% probability of failure within the next "
        f"{cycles} {trip_word}",
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
