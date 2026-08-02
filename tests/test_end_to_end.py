"""
End-to-end tests for dashboard data integration.

Tests the complete data flow from Report Layer output to Dashboard display.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dashboard.data_loader import load_dashboard_data  # noqa: E402
from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES  # noqa: E402
from dashboard.glossary import SIGNAL_DISPLAY_NAMES  # noqa: E402


REAL_SAMPLE_PATH = (
    project_root / "model_layer/ttm-related/outputs/kit_residual_sample.json"
)


def _current_real_sample() -> dict:
    return json.loads(REAL_SAMPLE_PATH.read_text(encoding="utf-8"))


def test_complete_data_flow():
    """Test complete data flow from JSON to dashboard-ready format."""
    # Load data as dashboard would
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    # _data_source is metadata; exclude it when counting components
    components = {k: v for k, v in data.items() if k != "_data_source"}
    assert len(components) == 5, "Should load 5 components"

    assert "cooling_degradation" in components
    assert "air_intake_maf_anomaly" in components
    assert "accelerator_pedal_sensor" in components
    assert "intake_air_temperature_sensor_fault" in components
    assert "map_load_signal_plausibility_fault" in components

    print("PASS: All components loaded successfully")


def test_cooling_system_data():
    """Test cooling system component data structure."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")
    cooling = data["cooling_degradation"]

    # Verify basic fields
    if data.get("_data_source", {}).get("cooling_degradation") == "real":
        assert cooling["risk_level"] == _current_real_sample()["risk_level"]
    else:
        assert cooling["risk_level"] in {"High", "Medium", "Low", None}
    assert isinstance(cooling["key_signals"], list)
    assert len(cooling["key_signals"]) >= 1

    # Verify at least one coolant signal is present
    features = [s["feature"] for s in cooling["key_signals"]]
    assert any("coolant" in f for f in features), (
        "Expected at least one coolant signal"
    )

    # Verify risk_history (None when loaded from real pipeline)
    rh = cooling.get("risk_history")
    if rh is not None:
        assert len(rh) == 5
        assert rh[-1]["risk_score"] == cooling["risk_score"]

    # Verify Granite LLM outputs (stub or real — just check types)
    assert isinstance(cooling["anomaly_description"], str)
    assert isinstance(cooling["possible_cause"], str)
    assert isinstance(cooling["recommended_action"], list)
    assert len(cooling["recommended_action"]) >= 1

    print("PASS: Cooling system data structure valid")


def test_air_intake_data():
    """Test air intake component data structure."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")
    air_intake = data["air_intake_maf_anomaly"]

    # Verify basic fields
    assert air_intake["risk_level"] == "Medium"
    assert air_intake["risk_score"] == 0.61

    # Verify key_signals
    assert len(air_intake["key_signals"]) == 2
    maf_signal = air_intake["key_signals"][0]
    assert maf_signal["feature"] == "maf"
    assert maf_signal["value"] == 28.5

    # Verify Granite LLM outputs
    assert isinstance(air_intake["recommended_action"], list)
    assert len(air_intake["recommended_action"]) == 3

    print("PASS: Air intake data structure valid")


def test_accelerator_pedal_data():
    """Test accelerator pedal component data structure."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")
    pedal = data["accelerator_pedal_sensor"]

    # Verify basic fields
    assert pedal["risk_level"] == "Low"
    assert pedal["risk_score"] == 0.22

    # Verify key_signals
    assert len(pedal["key_signals"]) == 2

    # Verify Granite LLM outputs
    assert isinstance(pedal["recommended_action"], list)
    assert len(pedal["recommended_action"]) == 2

    print("PASS: Accelerator pedal data structure valid")


def test_risk_history_trend_calculation():
    """Test that risk_history can be used for trend visualization."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    for component_name, component_data in data.items():
        if component_name == "_data_source":
            continue
        risk_history = component_data.get("risk_history")

        # risk_history is None for components loaded from the real pipeline
        # (history is not yet stored); only validate when a list is present.
        if risk_history is None:
            continue

        # Extract trend values (as dashboard would)
        trend = [entry["risk_score"] for entry in risk_history]

        # Verify trend is valid
        assert len(trend) == 5, \
            f"{component_name}: Should have 5 trend points"
        assert all(0 <= score <= 1 for score in trend), \
            f"{component_name}: All scores should be between 0 and 1"

        # Verify trend matches current risk_score
        assert trend[-1] == component_data["risk_score"], \
            f"{component_name}: Latest trend should match current risk_score"

    print("PASS: Risk history trend calculation valid")


def test_signal_status_calculation():
    """Test that signal status can be calculated from reference_range."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")
    cooling_key = (
        "cooling_degradation"
        if "cooling_degradation" in data
        else "cooling_degradation"
    )
    cooling = data[cooling_key]

    for signal in cooling["key_signals"]:
        ref_lower = signal["reference_range"][0]
        ref_upper = signal["reference_range"][1]
        value = signal["value"]

        # Calculate status (as dashboard would)
        is_abnormal = value < ref_lower or value > ref_upper
        status = "ABNORMAL" if is_abnormal else "NORMAL"

        # Verify calculation works
        if signal["feature"] == "coolant_temp":
            assert status == "ABNORMAL", "Coolant temp should be abnormal"
        elif signal["feature"] == "ect_rate_180s":
            assert status in {"ABNORMAL", "NORMAL"}

    print("PASS: Signal status calculation valid")


def test_display_name_mapping():
    """Test that component and signal IDs can be mapped to display names."""
    data = load_dashboard_data("dashboard/tests/ui_required_data.json")

    # Verify all components can be mapped (skip _data_source metadata key)
    for component_id in data.keys():
        if component_id == "_data_source":
            continue
        assert component_id in COMPONENT_DISPLAY_NAMES, \
            f"Missing display name mapping for: {component_id}"

    # Verify all signals can be mapped (skip _data_source metadata key)
    for key, component_data in data.items():
        if key == "_data_source":
            continue
        for signal in component_data["key_signals"]:
            signal_id = signal["feature"]
            assert signal_id in SIGNAL_DISPLAY_NAMES, \
                f"Missing display name mapping for signal: {signal_id}"

    print("PASS: Display name mapping valid")


if __name__ == "__main__":
    print("Running end-to-end tests...\n")

    test_complete_data_flow()
    test_cooling_system_data()
    test_air_intake_data()
    test_accelerator_pedal_data()
    test_risk_history_trend_calculation()
    test_signal_status_calculation()
    test_display_name_mapping()

    print("\nAll end-to-end tests passed!")
