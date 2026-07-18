"""
Pydantic models for Granite Lifeline cross-layer data contracts.
Based on INTERFACE.md v0.9 (updated 2026-07-14).

This is an early-stage version with basic validation only.
Stricter validation will be added once all layers confirm field details.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Anomaly type enum based on grounded_knowledge.yaml proxy_failures
AnomalyType = Literal[
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_or_heat_soak_fault",
    "map_load_signal_plausibility_fault",
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

    # Key / time
    timestamp: str = Field(...)
    trip_id: str = Field(...)
    segment_id: str = Field(...)
    row_in_segment: int = Field(...)
    dt_seconds: Optional[float] = Field(...)

    # Operating condition
    thermal_state: str = Field(...)
    child_state: str = Field(...)
    operating_state: str = Field(...)
    condition_confidence: str = Field(...)
    condition_quality_flags: str = Field(...)

    # Raw signals
    coolant_temp: Optional[float] = Field(...)
    map: Optional[float] = Field(...)
    rpm: Optional[float] = Field(...)
    speed: Optional[float] = Field(...)
    intake_temp: Optional[float] = Field(...)
    maf: Optional[float] = Field(...)
    tps: Optional[float] = Field(...)
    ambient_temp: Optional[float] = Field(...)
    accel_pedal_d: Optional[float] = Field(...)
    accel_pedal_e: Optional[float] = Field(...)

    # Engineered features
    coolant_slope: Optional[float] = Field(...)
    coolant_ambient_delta: Optional[float] = Field(...)
    coolant_stability: Optional[float] = Field(...)
    intake_ambient_delta: Optional[float] = Field(...)
    intake_temp_slope: Optional[float] = Field(...)
    maf_derived_air_load_raw: Optional[float] = Field(...)
    map_derived_air_load_raw: Optional[float] = Field(...)
    maf_map_cohesion: Optional[float] = Field(...)
    speed_density_maf_residual: Optional[float] = Field(...)
    map_slope: Optional[float] = Field(...)
    accel_pedal_mean: Optional[float] = Field(...)
    accel_pedal_channel_delta: Optional[float] = Field(...)
    accel_pedal_channel_ratio: Optional[float] = Field(...)
    pedal_slope: Optional[float] = Field(...)
    engine_on_flag: Optional[float] = Field(...)
    rpm_slope: Optional[float] = Field(...)
    idle_flag: Optional[float] = Field(...)
    idle_rpm_stability: Optional[float] = Field(...)
    segment_gap_seconds: Optional[float] = Field(...)
    cold_soak_candidate_flag: Optional[float] = Field(...)
    intake_temp_stability: Optional[float] = Field(...)
    map_stability: Optional[float] = Field(...)

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
    risk_level: Optional[str] = None  # TBD - thresholds pending
    component: AnomalyType  # Mirrors anomaly_type
    prediction_confidence: float
    key_signals: List[KeySignal]
    estimated_cycles_to_failure: Optional[int] = None
    estimated_failure_probability: Optional[float] = None
    notes: List[str] = Field(default_factory=list)


class ReportLayerOutput(BaseModel):
    """Output from Report Layer, consumed by Dashboard."""

    # Pass-through fields from Model Layer
    timestamp: str
    risk_score: float
    risk_level: Optional[str] = None  # TBD
    component: AnomalyType  # Mirrors anomaly_type from Model Layer
    prediction_confidence: float
    key_signals: List[KeySignal]
    estimated_cycles_to_failure: Optional[int] = None
    estimated_failure_probability: Optional[float] = None
    notes: List[str] = Field(default_factory=list)

    # Report Layer maintained fields
    # TBD - storage implementation pending
    risk_history: Optional[List[RiskHistoryEntry]] = None

    # Generated fields from Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]
