"""
Pydantic models for Granite Lifeline cross-layer data contracts.
Based on INTERFACE.md v0.3 (updated 2026-06-29).

This is an early-stage version with basic validation only.
Stricter validation will be added once all layers confirm field details.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel

# Anomaly type enum based on grounded_knowledge.yaml proxy_failures
AnomalyType = Literal[
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_or_heat_soak_fault",
    "map_load_signal_plausibility_fault",
    "electronic_throttle_tracking_fault",
    "idle_speed_control_or_surge_degradation"
]


class KeySignal(BaseModel):
    """Individual key signal contributing to risk prediction."""
    feature: str
    value: float
    unit: str
    reference_range: List[float]


class RiskHistoryEntry(BaseModel):
    """Single entry in risk history timeline."""
    timestamp: str
    risk_score: float


class DataLayerOutput(BaseModel):
    """Output from Data Layer, consumed by Model Layer."""

    # Raw signals
    timestamp: str
    rpm: Optional[float] = None
    speed: Optional[float] = None
    coolant_temp: Optional[float] = None
    map: Optional[float] = None
    maf: Optional[float] = None
    tps: Optional[float] = None
    intake_temp: Optional[float] = None
    ambient_temp: Optional[float] = None
    accel_pedal_d: Optional[float] = None
    accel_pedal_e: Optional[float] = None

    # Engineered features
    coolant_slope: Optional[float] = None
    coolant_ambient_delta: Optional[float] = None
    coolant_stability: Optional[float] = None
    intake_ambient_delta: Optional[float] = None
    intake_temp_slope: Optional[float] = None
    maf_derived_air_load_raw: Optional[float] = None
    map_derived_air_load_raw: Optional[float] = None
    maf_map_cohesion: Optional[float] = None
    speed_density_maf_residual: Optional[float] = None
    map_slope: Optional[float] = None
    accel_pedal_mean: Optional[float] = None
    pedal_throttle_gap: Optional[float] = None
    pedal_to_throttle_delay: Optional[float] = None
    tps_slope: Optional[float] = None
    accel_pedal_channel_delta: Optional[float] = None
    accel_pedal_channel_ratio: Optional[float] = None
    pedal_slope: Optional[float] = None
    engine_on_flag: Optional[float] = None
    rpm_slope: Optional[float] = None
    idle_flag: Optional[float] = None
    idle_rpm_stability: Optional[float] = None

    # Proxy labels (internal to Model Layer, marked Optional as TBD)
    failure_label: Optional[str] = None
    risk_class: Optional[str] = None
    condition_ratio: Optional[float] = None
    window_id: Optional[str] = None


class ModelLayerOutput(BaseModel):
    """Output from Model Layer, consumed by Report Layer."""

    timestamp: str
    anomaly_type: AnomalyType
    risk_score: float
    risk_level: Optional[str] = None  # TBD - thresholds pending calibration
    component: AnomalyType  # Mirrors anomaly_type
    prediction_confidence: float
    key_signals: List[KeySignal]


class ReportLayerOutput(BaseModel):
    """Output from Report Layer, consumed by Dashboard."""

    # Pass-through fields from Model Layer
    timestamp: str
    risk_score: float
    risk_level: Optional[str] = None  # TBD
    component: AnomalyType  # Mirrors anomaly_type from Model Layer
    prediction_confidence: float
    key_signals: List[KeySignal]

    # Report Layer maintained fields
    # TBD - storage implementation pending
    risk_history: Optional[List[RiskHistoryEntry]] = None

    # Generated fields from Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]
