"""Load the versioned Model Layer risk-level policy.

This policy is intentionally separate from the Data Layer's frozen
``calibration_registry.v1.json``.  That registry owns physical proxy rules
and feature transforms; this file owns the Model Layer's presentation and
alarm cut-offs for the final normalised ``risk_score``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "config" / "risk_level_calibration.v1.json"
)


def load_risk_level_calibration(
    path: Path = DEFAULT_CALIBRATION_PATH,
) -> dict[str, Any]:
    """Return a validated, versioned Low/Medium/High policy."""
    with open(path) as handle:
        payload = json.load(handle)

    thresholds = payload.get("risk_level_thresholds", {})
    medium_min = float(thresholds["medium_min_inclusive"])
    high_min = float(thresholds["high_min_inclusive"])
    if not 0.0 <= medium_min <= 1.0:
        raise ValueError("medium_min_inclusive must be between 0 and 1")
    if not medium_min < high_min <= 1.0:
        raise ValueError(
            "high_min_inclusive must be above medium_min_inclusive "
            "and at most 1"
        )
    return payload


def risk_level(
    risk_score: float,
    calibration: dict[str, Any] | None = None,
) -> str:
    """Map a normalised score to the shared Low/Medium/High labels."""
    policy = calibration or load_risk_level_calibration()
    thresholds = policy["risk_level_thresholds"]
    if risk_score < float(thresholds["medium_min_inclusive"]):
        return "Low"
    if risk_score < float(thresholds["high_min_inclusive"]):
        return "Medium"
    return "High"


def alarm_threshold() -> float:
    """Return the lowest score that should produce an alarm (Medium)."""
    return float(
        load_risk_level_calibration()["risk_level_thresholds"]
        ["medium_min_inclusive"]
    )
