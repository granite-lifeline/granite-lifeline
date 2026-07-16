"""Small helpers for the Failure Prediction UI card."""


PENDING_FAILURE_PREDICTION_TEXT = (
    "Failure probability estimate pending — awaiting more drive cycles"
)


def format_failure_prediction_text(component_data: dict) -> tuple[str, bool]:
    """Return failure prediction text and whether it is real data."""
    probability = component_data.get("estimated_failure_probability")
    cycles = component_data.get("estimated_cycles_to_failure")

    if probability is None or cycles is None:
        return PENDING_FAILURE_PREDICTION_TEXT, False

    probability_pct = int(round(probability * 100))
    trip_word = "trip" if cycles == 1 else "trips"
    return (
        f"{probability_pct}% probability of failure within the next "
        f"{cycles} {trip_word}",
        True,
    )
