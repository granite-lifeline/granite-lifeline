"""Pydantic models for Granite Lifeline cross-layer data contracts.

Based on INTERFACE.md v1.6 (updated 2026-08-15).

DataLayerOutput now follows the versioned production_features.csv contract:
4 sample keys + 16 A-class context/raw fields + 24 B-class production features
+ 2 provenance fields (46 columns total; production feature count remains 24).
Internal-only proxy label fields (INTERFACE.md 1.4) are kept optional.

ModelLayerOutput supports a primary risk plus an optional second-ranked
component risk. BatchModelLayerOutput supports the v1.6
`{summary, windows}` envelope emitted by Model Layer batch inference.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

# Anomaly type enum based on INTERFACE.md v1.6.
AnomalyType = Literal[
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault"
]

RiskLevel = Literal["Low", "Medium", "High"]


class KeySignal(BaseModel):
    """Individual key signal contributing to risk prediction."""
    feature: str
    value: float
    unit: str
    reference_range: List[float]

    @field_validator("reference_range")
    @classmethod
    def _reference_range_has_two_values(
        cls, value: List[float]
    ) -> List[float]:
        if len(value) != 2:
            raise ValueError("reference_range must contain exactly 2 values")
        return value


class RiskHistoryEntry(BaseModel):
    """Single entry in risk history timeline."""
    timestamp: str
    risk_score: float

    @field_validator("risk_score")
    @classmethod
    def _risk_score_in_unit_range(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("risk_score must be between 0 and 1")
        return value


class DataLayerOutput(BaseModel):
    """Output from Data Layer, consumed by Model Layer.

    Follows the production_features.csv contract (INTERFACE.md v1.5):
    46 ordered columns = 4 sample keys + 16 A-class context/raw fields
    + 24 B-class production features + 2 provenance fields.
    Nullable columns are typed Optional but remain required keys.
    """

    # Sample keys (4)
    timestamp: str = Field(...)
    trip_id: str = Field(...)
    segment_id: str = Field(...)
    row_in_segment: int = Field(...)

    # A-class context/raw (16): operating condition (A1/A4)
    dt_seconds: Optional[float] = Field(...)
    thermal_state: str = Field(...)
    child_state: str = Field(...)
    operating_state: str = Field(...)
    condition_confidence: str = Field(...)
    condition_quality_flags: str = Field(...)

    # A-class context/raw (16): cleaned raw signals (A2)
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

    # B-class production features (24): sample-level atomic (B1a)
    segment_gap_seconds: Optional[float] = Field(...)
    engine_on_flag: Optional[bool] = Field(...)
    coolant_ambient_delta: Optional[float] = Field(...)
    intake_ambient_delta: Optional[float] = Field(...)
    accel_pedal_mean: Optional[float] = Field(...)
    accel_pedal_channel_delta: Optional[float] = Field(...)
    pedal_slope: Optional[float] = Field(...)
    rpm_slope: Optional[float] = Field(...)

    # B-class production features (24): frozen-calibration transforms (B1b)
    speed_density_maf_residual: Optional[float] = Field(...)
    pedal_mapping_residual: Optional[float] = Field(...)

    # B-class production features (24): engine-start context (B2)
    engine_start_observed: Optional[bool] = Field(...)
    engine_start_episode_id: Optional[str] = Field(...)
    elapsed_since_engine_start: Optional[float] = Field(...)
    ect_start: Optional[float] = Field(...)
    aat_start: Optional[float] = Field(...)
    iat_start: Optional[float] = Field(...)

    # B-class production features (24): window-level (B3)
    maf_integral_180s: Optional[float] = Field(...)
    ect_rate_180s: Optional[float] = Field(...)
    intake_temp_stability: Optional[float] = Field(...)
    speed_std_120s: Optional[float] = Field(...)
    maf_std_120s: Optional[float] = Field(...)
    rpm_std_120s: Optional[float] = Field(...)
    accel_pedal_mean_std_120s: Optional[float] = Field(...)
    map_range_60s: Optional[float] = Field(...)

    # Provenance (2)
    schema_version: str = Field(...)
    calibration_version: str = Field(...)

    # Proxy labels, row grain (internal to Model Layer only).
    # The decision-level delivery proxy_decisions.csv (INTERFACE.md
    # §1.4, Master Field Table rows 50a-50e) is a separate table at
    # decision grain and is deliberately not modelled here.
    failure_label: Optional[str] = None
    risk_class: Optional[str] = None
    condition_ratio: Optional[float] = None
    window_id: Optional[str] = None


class ComponentRiskOutput(BaseModel):
    """One ranked component risk emitted by Model Layer."""

    timestamp: str
    anomaly_type: AnomalyType
    risk_score: float
    risk_level: Optional[RiskLevel] = None
    component: AnomalyType  # Mirrors anomaly_type
    prediction_confidence: float
    key_signals: List[KeySignal]
    estimated_cycles_to_failure: Optional[int] = Field(...)
    estimated_failure_probability: Optional[float] = Field(...)
    notes: List[str] = Field(default_factory=list)

    @field_validator("risk_score", "prediction_confidence")
    @classmethod
    def _score_in_unit_range(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("score fields must be between 0 and 1")
        return value

    @field_validator("estimated_failure_probability")
    @classmethod
    def _failure_probability_in_unit_range(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError(
                "estimated_failure_probability must be between 0 and 1"
            )
        return value

    @model_validator(mode="after")
    def _component_mirrors_anomaly_type(self) -> "ComponentRiskOutput":
        if self.component != self.anomaly_type:
            raise ValueError("component must mirror anomaly_type")
        return self


class ModelLayerOutput(ComponentRiskOutput):
    """Primary Model Layer risk plus an optional second-ranked risk."""

    secondary_risk: Optional[ComponentRiskOutput] = None

    @model_validator(mode="after")
    def _secondary_risk_is_distinct_and_ranked(self) -> "ModelLayerOutput":
        secondary = self.secondary_risk
        if secondary is None:
            return self
        if secondary.anomaly_type == self.anomaly_type:
            raise ValueError(
                "secondary_risk must represent a different anomaly_type"
            )
        if secondary.risk_score > self.risk_score:
            raise ValueError(
                "secondary_risk.risk_score must not exceed primary "
                "risk_score"
            )
        return self


class BatchWindowOutput(ModelLayerOutput):
    """Model Layer batch window output with identity fields."""

    trip_id: str
    segment_id: str
    window_id: str


class BatchModelLayerOutput(BaseModel):
    """Model Layer v1.5 batch output envelope."""

    summary: ModelLayerOutput
    windows: List[BatchWindowOutput]


class ReportLayerOutput(BaseModel):
    """Output from Report Layer, consumed by Dashboard."""

    # Pass-through fields from Model Layer
    timestamp: str
    risk_score: float
    risk_level: Optional[RiskLevel] = None
    component: AnomalyType  # Mirrors anomaly_type from Model Layer
    prediction_confidence: float
    key_signals: List[KeySignal]
    estimated_cycles_to_failure: Optional[int] = Field(...)
    estimated_failure_probability: Optional[float] = Field(...)
    notes: List[str] = Field(default_factory=list)

    # Report Layer maintained fields
    # TBD - storage implementation pending
    risk_history: Optional[List[RiskHistoryEntry]] = None

    # Generated fields from Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]

    @field_validator("risk_score", "prediction_confidence")
    @classmethod
    def _score_in_unit_range(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("score fields must be between 0 and 1")
        return value

    @field_validator("estimated_failure_probability")
    @classmethod
    def _report_failure_probability_in_unit_range(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is not None and not 0 <= value <= 1:
            raise ValueError(
                "estimated_failure_probability must be between 0 and 1"
            )
        return value
