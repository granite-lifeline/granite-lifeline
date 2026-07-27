"""Plain-language glossary for dashboard signal names and tooltips."""

from __future__ import annotations

try:
    from report_layer.pipeline.context_injection import SIGNAL_DISPLAY_NAMES
except Exception:
    # Keep the dashboard safe if Report Layer local RAG data is not ready.
    SIGNAL_DISPLAY_NAMES = {
        "coolant_temp": "Coolant Temperature",
        "ect_start": "Coolant Temperature at Engine Start",
        "aat_start": "Ambient Temperature at Engine Start",
        "maf_integral_180s": "MAF Integral Over 180 Seconds",
        "ect_rate_180s": "Coolant Temperature Rise Rate",
        "maf": "Mass Airflow",
        "map": "Manifold Air Pressure",
        "intake_temp": "Intake Air Temperature",
        "intake_temp_stability": "Intake Temperature Stability",
        "ambient_temp": "Ambient Temperature",
        "intake_ambient_delta": "Intake-Ambient Temperature Difference",
        "segment_gap_seconds": "Segment Gap",
        "speed_std_120s": "Vehicle Speed Variation",
        "maf_std_120s": "Mass Airflow Variation",
        "accel_pedal_d": "Accelerator Pedal Position (Channel D)",
        "accel_pedal_e": "Accelerator Pedal Position (Channel E)",
        "pedal_mapping_residual": "Pedal Channel Mapping Residual",
        "pedal_slope": "Pedal Demand Rate of Change",
        "accel_pedal_channel_delta": (
            "Accelerator Pedal Channel Difference"
        ),
        "engine_on_flag": "Engine Running Indicator",
        "tps": "Throttle Position",
        "rpm": "Engine RPM",
        "rpm_slope": "RPM Rate of Change",
        "rpm_std_120s": "RPM Variation",
        "accel_pedal_mean_std_120s": "Pedal Demand Variation",
        "map_range_60s": "Manifold Pressure Range",
        "speed": "Vehicle Speed",
        "speed_density_maf_residual": "Speed-Density MAF Residual",
    }


SIGNAL_TOOLTIPS = {
    "coolant_temp": (
        "Engine coolant temperature - shows how hot the engine cooling "
        "liquid is."
    ),
    "ect_start": (
        "Coolant temperature at engine start - helps compare engine warm-up "
        "from the beginning of a trip."
    ),
    "aat_start": (
        "Ambient temperature at engine start - outside air temperature when "
        "the trip began."
    ),
    "maf_integral_180s": (
        "Mass airflow total over 180 seconds - shows the recent amount of "
        "air going into the engine."
    ),
    "ect_rate_180s": (
        "Coolant temperature rise rate - shows how quickly the engine "
        "temperature is increasing."
    ),
    "maf": (
        "Mass airflow sensor - measures how much air the engine is "
        "breathing in."
    ),
    "map": (
        "Manifold air pressure - measures air pressure inside the engine "
        "intake area."
    ),
    "intake_temp": (
        "Intake air temperature - measures the temperature of air entering "
        "the engine."
    ),
    "intake_temp_stability": (
        "Intake temperature stability - shows whether intake air temperature "
        "is changing smoothly or unusually."
    ),
    "ambient_temp": (
        "Ambient temperature - outside air temperature around the vehicle."
    ),
    "intake_ambient_delta": (
        "Intake-ambient temperature difference - compares intake air "
        "temperature with outside air temperature."
    ),
    "segment_gap_seconds": (
        "Segment gap - time gap between two usable parts of the trip data."
    ),
    "speed_std_120s": (
        "Vehicle speed variation - shows how much the vehicle speed changed "
        "recently."
    ),
    "maf_std_120s": (
        "Mass airflow variation - shows how much airflow changed recently."
    ),
    "accel_pedal_d": (
        "Accelerator pedal position channel D - one sensor reading for how "
        "far the pedal is pressed."
    ),
    "accel_pedal_e": (
        "Accelerator pedal position channel E - a second pedal sensor reading "
        "used to check consistency."
    ),
    "pedal_mapping_residual": (
        "Pedal mapping residual - shows the gap between expected and actual "
        "pedal or throttle behaviour."
    ),
    "pedal_slope": (
        "Pedal demand rate of change - shows how quickly the driver is "
        "pressing or releasing the accelerator."
    ),
    "accel_pedal_channel_delta": (
        "Accelerator pedal channel difference - compares the two pedal sensor "
        "readings."
    ),
    "engine_on_flag": (
        "Engine running indicator - shows whether the engine appears to be on."
    ),
    "tps": (
        "Throttle position - shows how open the throttle is."
    ),
    "rpm": (
        "Engine RPM - shows how fast the engine is spinning."
    ),
    "rpm_slope": (
        "RPM rate of change - shows how quickly engine speed is rising or "
        "falling."
    ),
    "rpm_std_120s": (
        "RPM variation - shows how much engine speed changed recently."
    ),
    "accel_pedal_mean_std_120s": (
        "Pedal demand variation - shows how much accelerator pedal demand "
        "changed recently."
    ),
    "map_range_60s": (
        "Manifold pressure range - shows how much intake pressure changed "
        "recently."
    ),
    "speed": (
        "Vehicle speed - how fast the vehicle is moving."
    ),
    "speed_density_maf_residual": (
        "Speed-density airflow difference - compares measured airflow with "
        "airflow estimated from pressure and engine speed."
    ),
}

DEFAULT_SIGNAL_TOOLTIP = "No extra explanation available for this signal."


def get_signal_display_name(signal_id: str) -> str:
    """Return the plain signal name used in the dashboard."""
    return SIGNAL_DISPLAY_NAMES.get(signal_id, signal_id)


def get_signal_tooltip(signal_id: str) -> str:
    """Return the plain-language tooltip for one signal."""
    return SIGNAL_TOOLTIPS.get(signal_id, DEFAULT_SIGNAL_TOOLTIP)
