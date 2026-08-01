from pathlib import Path

import pandas as pd

from model.failure_estimation import (
    add_estimate_to_output,
    estimate_from_history,
)


FIXTURE = Path(__file__).parent / "fixtures" / "risk_history_rising.csv"


def history(scores):
    return pd.DataFrame([
        {
            "trip_id": f"trip_{index:04d}",
            "window_id": f"trip_{index:04d}_seg_001__w000",
            "timestamp": f"2026-01-{index:02d}T10:00:00Z",
            "risk_score": score,
        }
        for index, score in enumerate(scores, start=1)
    ])


def test_rising_fixture_projects_threshold_crossing():
    estimate = estimate_from_history(pd.read_csv(FIXTURE))

    assert estimate.estimated_cycles_to_failure == 4
    assert estimate.estimated_failure_probability is not None
    assert estimate.estimated_failure_probability > 0.9
    assert estimate.slope_per_cycle > 0
    assert len(estimate.trip_risks) == 6


def test_flat_healthy_history_has_no_crossing_cycle():
    estimate = estimate_from_history(history([0.2] * 5))

    assert estimate.estimated_cycles_to_failure is None
    assert estimate.estimated_failure_probability == 0.0
    assert any("No positive" in note for note in estimate.notes)


def test_history_below_minimum_returns_null_fields():
    estimate = estimate_from_history(history([0.1, 0.2, 0.3, 0.4]))

    assert estimate.estimated_cycles_to_failure is None
    assert estimate.estimated_failure_probability is None
    assert any("at least 5" in note for note in estimate.notes)


def test_current_high_risk_is_zero_cycles():
    estimate = estimate_from_history(history([0.3, 0.45, 0.6, 0.8, 0.95]))

    assert estimate.estimated_cycles_to_failure == 0
    assert estimate.estimated_failure_probability == 1.0


def test_estimate_fields_and_notes_are_added_to_interface_output():
    estimate = estimate_from_history(pd.read_csv(FIXTURE))
    output = add_estimate_to_output({"notes": ["existing note"]}, estimate)

    assert output["estimated_cycles_to_failure"] == 4
    assert output["estimated_failure_probability"] is not None
    assert output["notes"][0] == "existing note"
