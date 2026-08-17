"""Tests for Failure Prediction UI text."""

from dashboard.failure_prediction import (
    PENDING_FAILURE_PREDICTION_TEXT,
    format_failure_prediction_text,
    get_data_quality_notes,
)


def test_failure_prediction_text_with_value():
    """Test card text when prediction fields have values."""
    component_data = {
        "estimated_failure_probability": 0.72,
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert "High risk in about 15 trips" in text
    assert "72%" not in text
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


def test_failure_prediction_text_ignores_hidden_probability():
    """A missing hidden probability does not suppress a cycles estimate."""
    component_data = {
        "estimated_failure_probability": "",
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert "High risk in about 15 trips" in text
    assert has_value is True


def test_failure_prediction_text_zero_probability_is_value():
    """Test that 0% is still treated as a real estimate."""
    component_data = {
        "estimated_failure_probability": 0.0,
        "estimated_cycles_to_failure": 15,
    }

    text, has_value = format_failure_prediction_text(component_data)

    assert "High risk in about 15 trips" in text
    assert "0%" not in text
    assert has_value is True


def test_data_quality_notes_with_values():
    """Test non-empty notes are kept for the notes area."""
    component_data = {
        "notes": [
            " Coolant readings include repaired sensor gaps. ",
            "",
            "Failure estimate may change after more drive cycles.",
        ]
    }

    notes = get_data_quality_notes(component_data)

    assert notes == [
        "Coolant readings include repaired sensor gaps.",
        "Failure estimate may change after more drive cycles.",
    ]


def test_data_quality_notes_empty_list():
    """Test empty notes list renders nothing."""
    assert get_data_quality_notes({"notes": []}) == []


def test_data_quality_notes_missing_field():
    """Test missing notes field renders nothing."""
    assert get_data_quality_notes({}) == []


def test_data_quality_notes_non_list_value():
    """Test non-list notes value renders nothing."""
    assert get_data_quality_notes({"notes": "not a list"}) == []
