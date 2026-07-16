"""Tests for Failure Prediction UI text."""

from dashboard.failure_prediction import (
    PENDING_FAILURE_PREDICTION_TEXT,
    format_failure_prediction_text,
)


def test_failure_prediction_text_with_value():
    """Test card text when prediction fields have values."""
    component_data = {
        "estimated_failure_probability": 0.72,
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert text == "72% probability of failure within the next 15 trips"
    assert has_value is True


def test_failure_prediction_text_with_null_value():
    """Test placeholder text when prediction estimate is pending."""
    component_data = {
        "estimated_failure_probability": None,
        "estimated_cycles_to_failure": None,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert text == PENDING_FAILURE_PREDICTION_TEXT
    assert has_value is False
