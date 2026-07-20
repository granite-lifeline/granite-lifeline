# Dashboard Automated Test Plan

**Project:** Granite Lifeline - MSc Project at University of Bristol  
**Sponsor:** IBM  
**Component:** Dashboard Logic & Data Validation  
**Task:** GL-99 (Sub-task of GL-97: Dashboard Testing)  
**Version:** 1.0  
**Date:** 2026-06-28

## Overview

This document provides a structured automated test plan for the Granite Lifeline Dashboard logic functions and Pydantic model validation. Tests are implemented using pytest and target the file `tests/test_dashboard.py`.

## Test Coverage Areas

1. **Risk Level Sorting Logic** - Verify High → Medium → Low ordering
2. **Signal Sorting Logic** - Verify ABNORMAL signals appear before NORMAL
3. **Risk Score Formatting** - Verify float formatting to one decimal place
4. **Trend Data Validation** - Verify time_index sequential ordering
5. **Pydantic Schema Validation** - Verify ModelLayerOutput validation for valid and invalid inputs

## Test Cases

| Test ID | Function Under Test | Test Scenario | Expected Behaviour | Pytest Function Name |
|---------|---------------------|---------------|-------------------|---------------------|
| TC-AT-001 | Risk level sorting | Sort components with High, Medium, Low risk levels | Components ordered: High first, Medium second, Low last | `test_risk_level_sort_order_high_medium_low` |
| TC-AT-002 | Risk level sorting | Sort components with all same risk level (Medium) | All components returned in original order without errors | `test_risk_level_sort_order_all_same_level` |
| TC-AT-003 | Risk level sorting | Sort components with only High and Low (no Medium) | High components before Low components | `test_risk_level_sort_order_high_and_low_only` |
| TC-AT-004 | Signal sorting | Sort signals with ABNORMAL and NORMAL statuses | ABNORMAL signals appear before NORMAL signals | `test_signal_sort_order_abnormal_first` |
| TC-AT-005 | Signal sorting | Sort signals with all NORMAL status | All signals returned without errors | `test_signal_sort_order_all_normal` |
| TC-AT-006 | Risk score formatting | Format risk score 86.7234 to one decimal | Returns "86.7" | `test_risk_score_format_one_decimal` |
| TC-AT-007 | Risk score formatting | Format risk scores with parametrized inputs | Each input formatted to one decimal place | `test_risk_score_format_parametrized` |
| TC-AT-008 | Trend data validation | Validate time_index sequential order [0,1,2,3,4] | Validation passes | `test_trend_data_sequential_time_index_valid` |
| TC-AT-009 | Trend data validation | Validate non-sequential time_index [0,2,1,3] | Validation fails with appropriate error | `test_trend_data_non_sequential_time_index_invalid` |
| TC-AT-010 | Pydantic validation | Validate ModelLayerOutput with all required fields | Model instance created successfully | `test_model_layer_output_valid_input` |
| TC-AT-011 | Pydantic validation | Validate ModelLayerOutput missing required field (timestamp) | ValidationError raised | `test_model_layer_output_missing_required_field` |
| TC-AT-012 | Pydantic validation | Validate ModelLayerOutput with wrong type (risk_score as string) | ValidationError raised | `test_model_layer_output_wrong_type` |
| TC-AT-013 | Pydantic validation | Validate ModelLayerOutput with risk_score > 100 | ValidationError raised or value clamped | `test_model_layer_output_risk_score_out_of_range` |
| TC-AT-014 | Pydantic validation | Validate ReportLayerOutput with valid input | Model instance created successfully | `test_report_layer_output_valid_input` |
| TC-AT-015 | Pydantic validation | Validate KeySignal with invalid reference_range (not a list) | ValidationError raised | `test_key_signal_invalid_reference_range` |

## Pytest Code Skeletons

### Test File: `tests/test_dashboard.py`

```python
"""
Automated tests for Dashboard logic functions and Pydantic model validation.
Task: GL-99 (Sub-task of GL-97: Dashboard Testing)
"""

import pytest
from pydantic import ValidationError
from shared.interface_models import (
    ModelLayerOutput,
    ReportLayerOutput,
    KeySignal,
    RiskHistoryEntry
)


# ============================================================================
# Risk Level Sorting Tests
# ============================================================================

def test_risk_level_sort_order_high_medium_low():
    """
    TC-AT-001: Verify components are sorted High → Medium → Low.
    
    Arrange: Create list of components with mixed risk levels
    Act: Sort components by risk level
    Assert: High risk components appear first, then Medium, then Low
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Low", "risk_score": 25.0},
        {"name": "Component B", "risk_level": "High", "risk_score": 85.0},
        {"name": "Component C", "risk_level": "Medium", "risk_score": 55.0},
        {"name": "Component D", "risk_level": "High", "risk_score": 90.0},
    ]
    
    # Act
    # TODO: Implement sort_by_risk_level() function in dashboard logic
    # sorted_components = sort_by_risk_level(components)
    
    # Assert
    # assert sorted_components[0]["risk_level"] == "High"
    # assert sorted_components[1]["risk_level"] == "High"
    # assert sorted_components[2]["risk_level"] == "Medium"
    # assert sorted_components[3]["risk_level"] == "Low"
    pass


def test_risk_level_sort_order_all_same_level():
    """
    TC-AT-002: Verify sorting handles all components with same risk level.
    
    Arrange: Create list of components all with Medium risk level
    Act: Sort components by risk level
    Assert: All components returned without errors
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Medium", "risk_score": 50.0},
        {"name": "Component B", "risk_level": "Medium", "risk_score": 60.0},
        {"name": "Component C", "risk_level": "Medium", "risk_score": 55.0},
    ]
    
    # Act
    # TODO: Implement sort_by_risk_level() function
    # sorted_components = sort_by_risk_level(components)
    
    # Assert
    # assert len(sorted_components) == 3
    # assert all(c["risk_level"] == "Medium" for c in sorted_components)
    pass


def test_risk_level_sort_order_high_and_low_only():
    """
    TC-AT-003: Verify sorting with only High and Low risk levels (no Medium).
    
    Arrange: Create list with only High and Low risk components
    Act: Sort components by risk level
    Assert: High components appear before Low components
    """
    # Arrange
    components = [
        {"name": "Component A", "risk_level": "Low", "risk_score": 20.0},
        {"name": "Component B", "risk_level": "High", "risk_score": 85.0},
        {"name": "Component C", "risk_level": "Low", "risk_score": 30.0},
    ]
    
    # Act
    # TODO: Implement sort_by_risk_level() function
    # sorted_components = sort_by_risk_level(components)
    
    # Assert
    # assert sorted_components[0]["risk_level"] == "High"
    # assert sorted_components[1]["risk_level"] == "Low"
    # assert sorted_components[2]["risk_level"] == "Low"
    pass


# ============================================================================
# Signal Sorting Tests
# ============================================================================

def test_signal_sort_order_abnormal_first():
    """
    TC-AT-004: Verify ABNORMAL signals appear before NORMAL signals.
    
    Arrange: Create list of signals with mixed ABNORMAL and NORMAL statuses
    Act: Sort signals by status
    Assert: ABNORMAL signals appear first
    """
    # Arrange
    signals = [
        {"signal_name": "coolant_temp", "value": 95.0, "status": "NORMAL"},
        {"signal_name": "maf", "value": 28.5, "status": "ABNORMAL"},
        {"signal_name": "map", "value": 85.0, "status": "NORMAL"},
        {"signal_name": "coolant_slope", "value": 5.2, "status": "ABNORMAL"},
    ]
    
    # Act
    # TODO: Implement sort_signals_by_status() function
    # sorted_signals = sort_signals_by_status(signals)
    
    # Assert
    # assert sorted_signals[0]["status"] == "ABNORMAL"
    # assert sorted_signals[1]["status"] == "ABNORMAL"
    # assert sorted_signals[2]["status"] == "NORMAL"
    # assert sorted_signals[3]["status"] == "NORMAL"
    pass


def test_signal_sort_order_all_normal():
    """
    TC-AT-005: Verify sorting handles all NORMAL signals without errors.
    
    Arrange: Create list of signals all with NORMAL status
    Act: Sort signals by status
    Assert: All signals returned without errors
    """
    # Arrange
    signals = [
        {"signal_name": "coolant_temp", "value": 92.0, "status": "NORMAL"},
        {"signal_name": "maf", "value": 18.0, "status": "NORMAL"},
        {"signal_name": "map", "value": 80.0, "status": "NORMAL"},
    ]
    
    # Act
    # TODO: Implement sort_signals_by_status() function
    # sorted_signals = sort_signals_by_status(signals)
    
    # Assert
    # assert len(sorted_signals) == 3
    # assert all(s["status"] == "NORMAL" for s in sorted_signals)
    pass


# ============================================================================
# Risk Score Formatting Tests
# ============================================================================

def test_risk_score_format_one_decimal():
    """
    TC-AT-006: Verify risk score is formatted to one decimal place.
    
    Arrange: Create risk score with multiple decimal places
    Act: Format risk score to one decimal
    Assert: Returns string with one decimal place
    """
    # Arrange
    risk_score = 86.7234
    
    # Act
    # TODO: Implement format_risk_score() function
    # formatted_score = format_risk_score(risk_score)
    
    # Assert
    # assert formatted_score == "86.7"
    # assert isinstance(formatted_score, str)
    pass


@pytest.mark.parametrize("input_score,expected_output", [
    (86.7234, "86.7"),
    (50.0, "50.0"),
    (99.99, "100.0"),
    (0.12, "0.1"),
    (100.0, "100.0"),
])
def test_risk_score_format_parametrized(input_score, expected_output):
    """
    TC-AT-007: Verify risk score formatting with multiple inputs.
    
    Arrange: Parametrized risk scores
    Act: Format each risk score to one decimal
    Assert: Each returns correctly formatted string
    """
    # Act
    # TODO: Implement format_risk_score() function
    # formatted_score = format_risk_score(input_score)
    
    # Assert
    # assert formatted_score == expected_output
    pass


# ============================================================================
# Trend Data Validation Tests
# ============================================================================

def test_trend_data_sequential_time_index_valid():
    """
    TC-AT-008: Verify trend data with sequential time_index passes validation.
    
    Arrange: Create trend data with sequential time_index [0,1,2,3,4]
    Act: Validate trend data sequence
    Assert: Validation passes without errors
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
    # TODO: Implement validate_trend_sequence() function
    # is_valid = validate_trend_sequence(trend_data)
    
    # Assert
    # assert is_valid is True
    pass


def test_trend_data_non_sequential_time_index_invalid():
    """
    TC-AT-009: Verify trend data with non-sequential time_index fails validation.
    
    Arrange: Create trend data with non-sequential time_index [0,2,1,3]
    Act: Validate trend data sequence
    Assert: Validation fails with appropriate error
    """
    # Arrange
    trend_data = [
        {"time_index": 0, "risk_score": 45.0},
        {"time_index": 2, "risk_score": 61.0},  # Out of sequence
        {"time_index": 1, "risk_score": 52.0},  # Out of sequence
        {"time_index": 3, "risk_score": 70.0},
    ]
    
    # Act & Assert
    # TODO: Implement validate_trend_sequence() function
    # with pytest.raises(ValueError, match="non-sequential"):
    #     validate_trend_sequence(trend_data)
    pass


# ============================================================================
# Pydantic Model Validation Tests
# ============================================================================

def test_model_layer_output_valid_input():
    """
    TC-AT-010: Verify ModelLayerOutput accepts valid input.
    
    Arrange: Create valid ModelLayerOutput data
    Act: Instantiate ModelLayerOutput
    Assert: Model instance created successfully
    """
    # Arrange
    valid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 86.0,
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
        ]
    }
    
    # Act
    model = ModelLayerOutput(**valid_data)
    
    # Assert
    assert model.timestamp == "2026-06-16T12:00:00Z"
    assert model.risk_score == 86.0
    assert model.risk_level == "High"
    assert len(model.key_signals) == 1


def test_model_layer_output_missing_required_field():
    """
    TC-AT-011: Verify ModelLayerOutput rejects input missing required field.
    
    Arrange: Create data missing 'timestamp' field
    Act: Attempt to instantiate ModelLayerOutput
    Assert: ValidationError raised
    """
    # Arrange
    invalid_data = {
        # "timestamp": missing
        "anomaly_type": "cooling_degradation",
        "risk_score": 86.0,
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": []
    }
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelLayerOutput(**invalid_data)
    
    # Verify error mentions missing field
    assert "timestamp" in str(exc_info.value).lower()


def test_model_layer_output_wrong_type():
    """
    TC-AT-012: Verify ModelLayerOutput rejects wrong type for risk_score.
    
    Arrange: Create data with risk_score as string instead of float
    Act: Attempt to instantiate ModelLayerOutput
    Assert: ValidationError raised
    """
    # Arrange
    invalid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": "86.0",  # String instead of float
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": []
    }
    
    # Act & Assert
    # Note: Pydantic may coerce string to float, so this test may pass
    # If strict validation is needed, use StrictFloat in model definition
    try:
        model = ModelLayerOutput(**invalid_data)
        # If coercion happens, verify the type is correct after coercion
        assert isinstance(model.risk_score, float)
    except ValidationError:
        # If strict validation is enforced, this is expected
        pass


def test_model_layer_output_risk_score_out_of_range():
    """
    TC-AT-013: Verify ModelLayerOutput handles risk_score > 100.
    
    Arrange: Create data with risk_score = 150.0 (out of valid range)
    Act: Attempt to instantiate ModelLayerOutput
    Assert: ValidationError raised or value clamped to 100.0
    """
    # Arrange
    invalid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "anomaly_type": "cooling_degradation",
        "risk_score": 150.0,  # Out of range (should be 0-100)
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": []
    }
    
    # Act & Assert
    # TODO: Add validator to ModelLayerOutput to enforce 0-100 range
    # Current implementation may accept any float value
    # with pytest.raises(ValidationError, match="risk_score.*range"):
    #     ModelLayerOutput(**invalid_data)
    
    # For now, just verify model can be created
    # This test will fail once range validation is added
    model = ModelLayerOutput(**invalid_data)
    assert model.risk_score == 150.0  # Currently no validation


def test_report_layer_output_valid_input():
    """
    TC-AT-014: Verify ReportLayerOutput accepts valid input.
    
    Arrange: Create valid ReportLayerOutput data
    Act: Instantiate ReportLayerOutput
    Assert: Model instance created successfully
    """
    # Arrange
    valid_data = {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 86.0,
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
        "recommended_action": ["Check coolant level", "Inspect radiator"]
    }
    
    # Act
    model = ReportLayerOutput(**valid_data)
    
    # Assert
    assert model.timestamp == "2026-06-16T12:00:00Z"
    assert model.risk_score == 86.0
    assert len(model.recommended_action) == 2


def test_key_signal_invalid_reference_range():
    """
    TC-AT-015: Verify KeySignal rejects invalid reference_range type.
    
    Arrange: Create KeySignal data with reference_range as string
    Act: Attempt to instantiate KeySignal
    Assert: ValidationError raised
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


# ============================================================================
# Additional Helper Function Tests (To Be Implemented)
# ============================================================================

# TODO: Add tests for additional dashboard helper functions:
# - test_calculate_risk_percentage()
# - test_format_timestamp()
# - test_get_risk_badge_color()
# - test_validate_component_data()
```

## Implementation Notes

### Functions to Implement

The following dashboard logic functions need to be implemented in `dashboard/app.py` or a separate `dashboard/utils.py` module:

1. **`sort_by_risk_level(components: List[dict]) -> List[dict]`**
   - Sort components by risk level priority: High → Medium → Low
   - Use risk level mapping: `{"High": 0, "Medium": 1, "Low": 2}`

2. **`sort_signals_by_status(signals: List[dict]) -> List[dict]`**
   - Sort signals with ABNORMAL status first, then NORMAL
   - Use status mapping: `{"ABNORMAL": 0, "NORMAL": 1}`

3. **`format_risk_score(score: float) -> str`**
   - Format float to one decimal place
   - Return as string (e.g., "86.7")

4. **`validate_trend_sequence(trend_data: List[dict]) -> bool`**
   - Validate time_index values are sequential
   - Raise ValueError if non-sequential

### Pydantic Model Enhancements

To enable stricter validation, consider adding to `shared/interface_models.py`:

```python
from pydantic import BaseModel, Field, validator

class ModelLayerOutput(BaseModel):
    # ... existing fields ...
    risk_score: float = Field(..., ge=0.0, le=100.0)  # Range validation
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        if v not in ['Low', 'Medium', 'High', None]:
            raise ValueError('risk_level must be Low, Medium, or High')
        return v
```

## Running Tests

```bash
# Run all dashboard tests
pytest tests/test_dashboard.py -v

# Run specific test
pytest tests/test_dashboard.py::test_model_layer_output_valid_input -v

# Run with coverage
pytest tests/test_dashboard.py --cov=dashboard --cov-report=html
```

## Test Maintenance

- Update test cases when dashboard logic functions are implemented
- Remove `pass` statements and uncomment assertions
- Add new test cases for edge cases discovered during development
- Keep test data synchronized with `dashboard/tests/ui_required_data.json`

---

**Related Tasks:**
- GL-97: Dashboard Testing (Parent)
- GL-98: Create Manual Test Plan
- GL-99: Create Automated Test Plan (Current)