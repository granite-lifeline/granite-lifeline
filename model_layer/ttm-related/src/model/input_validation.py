"""
Input validation for the Model Layer pipeline (Story 3).

Two-tier range semantics: PLAUSIBLE_RANGES below are sensor-physical
limits, deliberately wider than the healthy-baseline REFERENCE_RANGES
in kit_residual_detector.py. Rejecting inputs at healthy-range bounds
would blind the detector to the very anomalies it exists to flag
(01_user_story/failure_type_research.md, "Range consistency caveats").
Reused by Story 4 data-quality tests and Story 7 Group 1 CSV loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import pandas as pd

# Physically implausible beyond these bounds (sensor/electrical
# limits), not "unhealthy". Tunable as calibration evidence grows.
PLAUSIBLE_RANGES: dict[str, list[float]] = {
    "rpm": [0.0, 8000.0],
    "speed": [0.0, 300.0],
    "coolant_temp": [-40.0, 150.0],
    "map": [0.0, 400.0],
    "maf": [0.0, 500.0],
    "tps": [0.0, 100.0],
    "accel_pedal_d": [0.0, 100.0],
    "accel_pedal_e": [0.0, 100.0],
}

# Fraction of implausible rows per column above which the input is
# rejected instead of repaired.
DEFAULT_MAX_BAD_FRACTION = 0.05


@dataclass
class ValidationResult:
    """Outcome of range validation: cleaned frame plus audit trail."""

    df: pd.DataFrame
    repaired_counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def validate_required_columns(
    columns: Sequence[str],
    required: Sequence[str],
    source: str,
) -> None:
    """Raise ValueError naming every required column missing."""
    missing = [col for col in required if col not in columns]
    if missing:
        raise ValueError(
            f"Missing required columns in {source}: {missing}"
        )


def validate_sensor_ranges(
    df: pd.DataFrame,
    ranges: dict[str, list[float]] | None = None,
    max_bad_fraction: float = DEFAULT_MAX_BAD_FRACTION,
) -> ValidationResult:
    """Repair isolated implausible values; reject broken columns.

    Implausible cells (outside sensor-physical bounds) become NaN so
    the caller's interpolation step can repair them; each repair is
    counted and reported as a note. A column raises ValueError when
    it is entirely NaN or when more than ``max_bad_fraction`` of its
    rows are implausible. Only columns present in both ``df`` and
    ``ranges`` are checked, so frames with or without optional
    columns (e.g. pedal channels) validate the same way.
    """
    if ranges is None:
        ranges = PLAUSIBLE_RANGES

    cleaned = df.copy()
    repaired_counts: dict[str, int] = {}
    notes: list[str] = []

    for column, (low, high) in ranges.items():
        if column not in cleaned.columns:
            continue
        series = cleaned[column]
        if series.isna().all():
            raise ValueError(
                f"Column '{column}' contains no valid values "
                "(all missing or non-numeric)"
            )
        implausible = series.notna() & ((series < low) | (series > high))
        bad_count = int(implausible.sum())
        if bad_count == 0:
            continue
        bad_fraction = bad_count / len(series)
        if bad_fraction > max_bad_fraction:
            raise ValueError(
                f"Column '{column}' has {bad_count}/{len(series)} "
                f"values outside plausible range [{low}, {high}] "
                f"({bad_fraction:.1%} > {max_bad_fraction:.0%} "
                "threshold); input rejected"
            )
        cleaned.loc[implausible, column] = float("nan")
        repaired_counts[column] = bad_count
        notes.append(
            f"repaired {bad_count} implausible {column} value(s) "
            f"outside [{low}, {high}]"
        )

    return ValidationResult(
        df=cleaned, repaired_counts=repaired_counts, notes=notes
    )
