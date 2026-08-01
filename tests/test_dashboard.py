"""
Automated tests for Dashboard logic functions and Pydantic model validation.
Task: GL-100 (Sub-task of GL-97: Dashboard Testing)

Tests cover:
- Risk level sorting logic
- Signal sorting logic
- Risk score formatting
- Trend data validation
- Pydantic model validation
"""

import pytest
from pydantic import ValidationError
from shared.interface_models import (
    ModelLayerOutput,
    ReportLayerOutput,
    KeySignal,
    RiskHistoryEntry
)


def model_output_payload(**overrides):
    """Build a current INTERFACE.md ModelLayerOutput payload."""
    payload = {
        "timestamp": "2026-06-16T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": [],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
    }
    payload.update(overrides)
    return payload


# ============================================================================
# Helper Functions for Dashboard Logic
# ============================================================================

def sort_by_risk_level(components):
    """Sort components by risk level: High → Medium → Low."""
    risk_priority = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(
        components,
        key=lambda x: risk_priority.get(x.get("risk_level", "Low"), 2)
    )


def sort_signals_by_status(signals):
    """Sort signals with ABNORMAL first, then NORMAL."""
    status_priority = {"ABNORMAL": 0, "NORMAL": 1}
    return sorted(
        signals,
        key=lambda x: status_priority.get(x.get("status", "NORMAL"), 1)
    )


def format_risk_score(score):
    """Format risk score to one decimal place."""
    return f"{score:.1f}"


def validate_trend_sequence(trend_data):
    """Validate that time_index values are sequential."""
    if not trend_data:
        return True

    time_indices = [entry["time_index"] for entry in trend_data]
    expected = list(range(len(time_indices)))

    if time_indices != expected:
        raise ValueError(
            f"Non-sequential time_index: expected {expected}, "
            f"got {time_indices}"
        )
    return True


# ============================================================================
# Risk Level Sorting Tests
# ============================================================================

def test_risk_level_sort_order_high_medium_low():
    """
    TC-AT-001: Verify components are sorted High → Medium → Low.

    Tests that when given components with mixed risk levels,
    they are correctly ordered with High risk first, Medium second,
    and Low last.
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Low", "risk_score": 25.0},
        {"name": "Component B", "risk_level": "High", "risk_score": 85.0},
        {"name": "Component C", "risk_level": "Medium", "risk_score": 55.0},
        {"name": "Component D", "risk_level": "High", "risk_score": 90.0},
    ]

    # Act
    sorted_components = sort_by_risk_level(components)

    # Assert
    assert sorted_components[0]["risk_level"] == "High"
    assert sorted_components[1]["risk_level"] == "High"
    assert sorted_components[2]["risk_level"] == "Medium"
    assert sorted_components[3]["risk_level"] == "Low"
    assert sorted_components[0]["name"] == "Component B"
    assert sorted_components[3]["name"] == "Component A"


def test_risk_level_sort_order_all_same_level():
    """
    TC-AT-002: Verify sorting handles all components with same risk level.

    Tests that when all components have the same risk level,
    sorting completes without errors and returns all components.
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Medium", "risk_score": 50.0},
        {"name": "Component B", "risk_level": "Medium", "risk_score": 60.0},
        {"name": "Component C", "risk_level": "Medium", "risk_score": 55.0},
    ]

    # Act
    sorted_components = sort_by_risk_level(components)

    # Assert
    assert len(sorted_components) == 3
    assert all(c["risk_level"] == "Medium" for c in sorted_components)


def test_risk_level_sort_order_high_and_low_only():
    """
    TC-AT-003: Verify sorting with only High and Low risk levels.

    Tests that when no Medium risk components exist,
    High components still appear before Low components.
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Low", "risk_score": 20.0},
        {"name": "Component B", "risk_level": "High", "risk_score": 85.0},
        {"name": "Component C", "risk_level": "Low", "risk_score": 30.0},
    ]

    # Act
    sorted_components = sort_by_risk_level(components)

    # Assert
    assert sorted_components[0]["risk_level"] == "High"
    assert sorted_components[1]["risk_level"] == "Low"
    assert sorted_components[2]["risk_level"] == "Low"


# ============================================================================
# Signal Sorting Tests
# ============================================================================

def test_signal_sort_order_abnormal_first():
    """
    TC-AT-004: Verify ABNORMAL signals appear before NORMAL signals.

    Tests that when given signals with mixed statuses,
    ABNORMAL signals are sorted to appear first.
    """
    # Arrange
    signals = [
        {"signal_name": "coolant_temp", "value": 95.0, "status": "NORMAL"},
        {"signal_name": "maf", "value": 28.5, "status": "ABNORMAL"},
        {"signal_name": "map", "value": 85.0, "status": "NORMAL"},
        {"signal_name": "coolant_slope", "value": 5.2, "status": "ABNORMAL"},
    ]

    # Act
    sorted_signals = sort_signals_by_status(signals)

    # Assert
    assert sorted_signals[0]["status"] == "ABNORMAL"
    assert sorted_signals[1]["status"] == "ABNORMAL"
    assert sorted_signals[2]["status"] == "NORMAL"
    assert sorted_signals[3]["status"] == "NORMAL"
    assert sorted_signals[0]["signal_name"] == "maf"
    assert sorted_signals[1]["signal_name"] == "coolant_slope"


def test_signal_sort_order_all_normal():
    """
    TC-AT-005: Verify sorting handles all NORMAL signals without errors.

    Tests that when all signals have NORMAL status,
    sorting completes successfully and returns all signals.
    """
    # Arrange
    signals = [
        {"signal_name": "coolant_temp", "value": 92.0, "status": "NORMAL"},
        {"signal_name": "maf", "value": 18.0, "status": "NORMAL"},
        {"signal_name": "map", "value": 80.0, "status": "NORMAL"},
    ]

    # Act
    sorted_signals = sort_signals_by_status(signals)

    # Assert
    assert len(sorted_signals) == 3
    assert all(s["status"] == "NORMAL" for s in sorted_signals)


# ============================================================================
# Risk Score Formatting Tests
# ============================================================================

def test_risk_score_format_one_decimal():
    """
    TC-AT-006: Verify risk score is formatted to one decimal place.

    Tests that a risk score with multiple decimal places
    is correctly formatted to exactly one decimal place.
    """
    # Arrange
    risk_score = 86.7234

    # Act
    formatted_score = format_risk_score(risk_score)

    # Assert
    assert formatted_score == "86.7"
    assert isinstance(formatted_score, str)


@pytest.mark.parametrize("input_score,expected_output", [
    (86.7234, "86.7"),
    (50.0, "50.0"),
    (99.99, "100.0"),
    (0.12, "0.1"),
    (100.0, "100.0"),
    (0.0, "0.0"),
    (45.56, "45.6"),  # Test rounding up
    (45.54, "45.5"),  # Test rounding down
])
def test_risk_score_format_parametrized(input_score, expected_output):
    """
    TC-AT-007: Verify risk score formatting with multiple inputs.

    Tests that various risk score values are correctly formatted
    to one decimal place, including edge cases and rounding.
    """
    # Act
    formatted_score = format_risk_score(input_score)

    # Assert
    assert formatted_score == expected_output


# ============================================================================
# Trend Data Validation Tests
# ============================================================================

def test_trend_data_sequential_time_index_valid():
    """
    TC-AT-008: Verify trend data with sequential time_index passes.

    Tests that trend data with properly sequential time_index values
    (0, 1, 2, 3, 4) passes validation without errors.
    """
    # Arrange
    trend_data = [
        {"time_index": 0, "risk_score": 45.0},
        {"time_index": 1, "risk_score": 52.0},
        {"time_index": 2, "risk_score": 61.0},
        {"time_index": 3, "risk_score": 70.0},
        {"time_index": 4, "risk_score": 86.0},
    ]

    # Act
    is_valid = validate_trend_sequence(trend_data)

    # Assert
    assert is_valid is True


def test_trend_data_non_sequential_time_index_invalid():
    """
    TC-AT-009: Verify trend data with non-sequential time_index fails.

    Tests that trend data with out-of-order time_index values
    raises a ValueError with appropriate error message.
    """
    # Arrange
    trend_data = [
        {"time_index": 0, "risk_score": 45.0},
        {"time_index": 2, "risk_score": 61.0},  # Out of sequence
        {"time_index": 1, "risk_score": 52.0},  # Out of sequence
        {"time_index": 3, "risk_score": 70.0},
    ]

    # Act & Assert
    with pytest.raises(ValueError, match="Non-sequential"):
        validate_trend_sequence(trend_data)


def test_trend_data_empty_list_valid():
    """
    Test that empty trend data list is considered valid.

    Tests edge case where no trend data is provided.
    """
    # Arrange
    trend_data = []

    # Act
    is_valid = validate_trend_sequence(trend_data)

    # Assert
    assert is_valid is True


# ============================================================================
# Pydantic Model Validation Tests
# ============================================================================

def test_model_layer_output_valid_input():
    """
    TC-AT-010: Verify ModelLayerOutput accepts valid input.

    Tests that a ModelLayerOutput instance can be created
    with all required fields and correct types.
    """
    # Arrange
    valid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 104.0,
                "unit": "°C",
                "reference_range": [90.0, 95.0]
            }
        ],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
    }

    # Act
    model = ModelLayerOutput(**valid_data)

    # Assert
    assert model.timestamp == "2026-06-16T12:00:00Z"
    assert model.risk_score == 0.86
    assert model.risk_level == "High"
    assert model.component == "cooling_degradation"
    assert model.prediction_confidence == 0.88
    assert len(model.key_signals) == 1
    assert model.key_signals[0].feature == "coolant_temp"


def test_model_layer_output_missing_required_field():
    """
    TC-AT-011: Verify ModelLayerOutput rejects missing required field.

    Tests that attempting to create a ModelLayerOutput without
    the required 'timestamp' field raises a ValidationError.
    """
    # Arrange
    invalid_data = model_output_payload()
    del invalid_data["timestamp"]

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelLayerOutput(**invalid_data)

    # Verify error mentions missing field
    assert "timestamp" in str(exc_info.value).lower()


def test_model_layer_output_wrong_type():
    """
    TC-AT-012: Verify ModelLayerOutput handles wrong type for risk_score.

    Tests that Pydantic either coerces string to float or raises
    ValidationError for risk_score field.
    """
    # Arrange
    invalid_data = model_output_payload(risk_score="not_a_number")

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelLayerOutput(**invalid_data)

    # Verify error mentions risk_score
    assert "risk_score" in str(exc_info.value).lower()


def test_model_layer_output_risk_score_out_of_range():
    """
    TC-AT-013: Verify ModelLayerOutput rejects risk_score > 1.0.

    Tests behavior when risk_score exceeds valid range (0-1).
    """
    # Arrange
    data_out_of_range = model_output_payload(risk_score=1.5)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelLayerOutput(**data_out_of_range)
    assert "risk_score" in str(exc_info.value).lower()


def test_report_layer_output_valid_input():
    """
    TC-AT-014: Verify ReportLayerOutput accepts valid input.

    Tests that a ReportLayerOutput instance can be created
    with all required fields including Granite LLM outputs.
    """
    # Arrange
    valid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 104.0,
                "unit": "°C",
                "reference_range": [90.0, 95.0]
            }
        ],
        "anomaly_description": "Coolant temperature is rising",
        "possible_cause": "Cooling system stress",
        "recommended_action": ["Check coolant level", "Inspect radiator"],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
        "risk_history": [],
    }

    # Act
    model = ReportLayerOutput(**valid_data)

    # Assert
    assert model.timestamp == "2026-06-16T12:00:00Z"
    assert model.risk_score == 0.86
    assert model.anomaly_description == "Coolant temperature is rising"
    assert len(model.recommended_action) == 2
    assert "Check coolant level" in model.recommended_action


def test_key_signal_invalid_reference_range():
    """
    TC-AT-015: Verify KeySignal rejects invalid reference_range type.

    Tests that KeySignal raises ValidationError when reference_range
    is provided as a string instead of a list of floats.
    """
    # Arrange
    invalid_data = {
        "feature": "coolant_temp",
        "value": 104.0,
        "unit": "°C",
        "reference_range": "90-95"  # String instead of list
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        KeySignal(**invalid_data)

    # Verify error mentions reference_range
    assert "reference_range" in str(exc_info.value).lower()


def test_key_signal_valid_input():
    """
    Test that KeySignal accepts valid input with all required fields.

    Tests successful creation of KeySignal with proper types.
    """
    # Arrange
    valid_data = {
        "feature": "coolant_temp",
        "value": 104.0,
        "unit": "°C",
        "reference_range": [90.0, 95.0]
    }

    # Act
    signal = KeySignal(**valid_data)

    # Assert
    assert signal.feature == "coolant_temp"
    assert signal.value == 104.0
    assert signal.unit == "°C"
    assert signal.reference_range == [90.0, 95.0]


def test_risk_history_entry_valid_input():
    """
    Test that RiskHistoryEntry accepts valid input.

    Tests successful creation of RiskHistoryEntry with timestamp
    and risk_score.
    """
    # Arrange
    valid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86
    }

    # Act
    entry = RiskHistoryEntry(**valid_data)

    # Assert
    assert entry.timestamp == "2026-06-16T12:00:00Z"
    assert entry.risk_score == 0.86


@pytest.mark.parametrize("missing_field", [
    "timestamp",
    "anomaly_type",
    "risk_score",
    "component",
    "prediction_confidence",
    "key_signals"
])
def test_model_layer_output_missing_each_required_field(missing_field):
    """
    Test that ModelLayerOutput rejects input missing any required field.

    Parametrized test that verifies each required field is validated.
    """
    # Arrange
    complete_data = model_output_payload()

    # Remove one field
    invalid_data = {k: v for k, v in complete_data.items()
                    if k != missing_field}

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelLayerOutput(**invalid_data)

    # Verify error mentions the missing field
    assert missing_field in str(exc_info.value).lower()


# Made with Bob
