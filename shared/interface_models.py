"""
Pydantic models for Granite Lifeline cross-layer data contracts.
Based on INTERFACE.md v0.2.

This is an early-stage version with basic validation only.
Stricter validation will be added once all layers confirm field details.
"""

from typing import List, Optional
from pydantic import BaseModel


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
    rpm: float
    speed: float
    coolant_temp: float
    map: float
    maf: float
    tps: float
    accel_pedal_d: float
    accel_pedal_e: float

    # Engineered features
    coolant_rolling_avg: float
    rpm_rolling_avg: float
    coolant_slope: float
    acceleration: float
    load_stress: float
    maf_map_cohesion: float
    rpm_variation: float

    # Proxy labels (internal to Model Layer, marked Optional as TBD)
    failure_label: Optional[str] = None
    risk_class: Optional[str] = None
    condition_ratio: Optional[float] = None
    window_id: Optional[str] = None


class ModelLayerOutput(BaseModel):
    """Output from Model Layer, consumed by Report Layer."""

    timestamp: str
    anomaly_type: str
    risk_score: float
    risk_level: Optional[str] = None  # TBD - thresholds pending calibration
    component: str
    prediction_confidence: float
    key_signals: List[KeySignal]


class ReportLayerOutput(BaseModel):
    """Output from Report Layer, consumed by Dashboard."""

    # Pass-through fields from Model Layer
    timestamp: str
    risk_score: float
    risk_level: Optional[str] = None  # TBD
    component: str
    prediction_confidence: float
    key_signals: List[KeySignal]

    # Report Layer maintained fields
    # TBD - storage implementation pending
    risk_history: Optional[List[RiskHistoryEntry]] = None

    # Generated fields from Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]
