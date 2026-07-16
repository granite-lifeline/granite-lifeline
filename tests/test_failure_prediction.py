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


def test_failure_prediction_text_with_one_missing_value():
    """Test placeholder when only one prediction field is missing."""
    component_data = {
        "estimated_failure_probability": 0.72,
        "estimated_cycles_to_failure": None,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert text == PENDING_FAILURE_PREDICTION_TEXT
    assert has_value is False


def test_failure_prediction_text_with_missing_fields():
    """Test placeholder when prediction fields are not in the data."""
    text, has_value = format_failure_prediction_text({})

    assert text == PENDING_FAILURE_PREDICTION_TEXT
    assert has_value is False


def test_failure_prediction_text_with_empty_string():
    """Test placeholder when a prediction field is an empty string."""
    component_data = {
        "estimated_failure_probability": "",
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert text == PENDING_FAILURE_PREDICTION_TEXT
    assert has_value is False


def test_failure_prediction_text_zero_probability_is_value():
    """Test that 0% is still treated as a real estimate."""
    component_data = {
        "estimated_failure_probability": 0.0,
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert text == "0% probability of failure within the next 15 trips"
    assert has_value is True
