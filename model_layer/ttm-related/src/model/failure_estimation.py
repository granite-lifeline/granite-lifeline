"""Story 8 risk-trend projection for the Model Layer output.

The estimator projects when the detector's *risk score* may cross the
configured High-risk line.  It is deliberately not a remaining-useful-life
model and does not claim an empirically calibrated probability of mechanical
failure: KIT supplies no labelled failure times.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from model.risk_history import load_history, validate_history
    from model.risk_level_calibration import load_risk_level_calibration
except ImportError:  # direct script run
    from risk_history import load_history, validate_history
    from risk_level_calibration import load_risk_level_calibration


MINIMUM_TRIPS = 5
PROBABILITY_HORIZON_CYCLES = 10
MAXIMUM_PROJECTION_CYCLES = 50
DEFAULT_INPUT = Path("ttm-related/outputs/risk_history.csv")
DEFAULT_JSON = Path("ttm-related/outputs/failure_estimation.json")
DEFAULT_MD = Path("ttm-related/outputs/failure_estimation.md")


@dataclass(frozen=True)
class FailureEstimate:
    """A threshold-crossing projection and its audit values."""

    estimated_cycles_to_failure: int | None
    estimated_failure_probability: float | None
    notes: list[str]
    trip_risks: list[dict[str, Any]]
    slope_per_cycle: float | None
    intercept: float | None
    high_risk_threshold: float
    probability_horizon_cycles: int

    def interface_fields(self) -> dict[str, Any]:
        return {
            "estimated_cycles_to_failure": self.estimated_cycles_to_failure,
            "estimated_failure_probability": (
                self.estimated_failure_probability
            ),
        }

    def audit_dict(self) -> dict[str, Any]:
        return {
            **self.interface_fields(),
            "notes": self.notes,
            "trip_risks": self.trip_risks,
            "slope_per_cycle": self.slope_per_cycle,
            "intercept": self.intercept,
            "high_risk_threshold": self.high_risk_threshold,
            "probability_horizon_cycles": self.probability_horizon_cycles,
            "probability_definition": (
                "Model-based probability that the linear risk projection "
                "crosses the High-risk threshold within the fixed horizon; "
                "not a calibrated probability of mechanical failure."
            ),
        }


def high_risk_threshold() -> float:
    policy = load_risk_level_calibration()
    return float(policy["risk_level_thresholds"]["high_min_inclusive"])


def aggregate_trip_risks(history: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert many detector windows into one mean risk per trip.

    A trip-level mean avoids making an entire cycle's estimate depend on a
    single noisy window. Trips are ordered by their first recorded timestamp,
    which is the contracted chronological cycle order.
    """
    validate_history(history)
    frame = history.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["risk_score"] = pd.to_numeric(frame["risk_score"])
    grouped = (
        frame.groupby("trip_id", sort=False)
        .agg(
            timestamp=("timestamp", "min"),
            mean_risk_score=("risk_score", "mean"),
            window_count=("risk_score", "size"),
        )
        .reset_index()
        .sort_values(["timestamp", "trip_id"], kind="stable")
        .reset_index(drop=True)
    )
    return [
        {
            "cycle_index": int(index + 1),
            "trip_id": str(row.trip_id),
            "timestamp": row.timestamp.isoformat().replace("+00:00", "Z"),
            "mean_risk_score": float(row.mean_risk_score),
            "window_count": int(row.window_count),
        }
        for index, row in grouped.iterrows()
    ]


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def estimate_from_history(
    history: pd.DataFrame,
    *,
    threshold: float | None = None,
    minimum_trips: int = MINIMUM_TRIPS,
    probability_horizon: int = PROBABILITY_HORIZON_CYCLES,
    maximum_cycles: int = MAXIMUM_PROJECTION_CYCLES,
) -> FailureEstimate:
    """Project a linear trip-risk trend to the configured High-risk line.

    The probability is the normal-error-model probability that the *projected
    risk score* crosses the threshold within ``probability_horizon`` trips.
    It is only an uncertainty summary for this simple trend model.
    """
    if minimum_trips < 3:
        raise ValueError("minimum_trips must be at least 3")
    if probability_horizon < 1 or maximum_cycles < 1:
        raise ValueError("projection horizons must be positive")

    high_threshold = high_risk_threshold() if threshold is None else threshold
    if not 0.0 < high_threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")

    trip_risks = aggregate_trip_risks(history)
    if len(trip_risks) < minimum_trips:
        return FailureEstimate(
            estimated_cycles_to_failure=None,
            estimated_failure_probability=None,
            notes=[
                "Failure estimate unavailable: need at least "
                f"{minimum_trips} chronological trips; "
                f"found {len(trip_risks)}."
            ],
            trip_risks=trip_risks,
            slope_per_cycle=None,
            intercept=None,
            high_risk_threshold=high_threshold,
            probability_horizon_cycles=probability_horizon,
        )

    x = np.arange(len(trip_risks), dtype=float)
    y = np.array([row["mean_risk_score"] for row in trip_risks])
    x_mean = float(x.mean())
    y_mean = float(y.mean())
    centered_x = x - x_mean
    sxx = float(np.sum(centered_x**2))
    slope = float(np.sum(centered_x * (y - y_mean)) / sxx)
    intercept = float(y_mean - slope * x_mean)
    fitted = intercept + slope * x
    residuals = y - fitted
    residual_standard_error = float(
        math.sqrt(float(np.sum(residuals**2)) / (len(x) - 2))
    )
    latest_risk = float(y[-1])
    future_x = float(x[-1] + probability_horizon)
    future_mean_risk = intercept + slope * future_x
    prediction_standard_error = residual_standard_error * math.sqrt(
        1.0 + 1.0 / len(x) + (future_x - x_mean) ** 2 / sxx
    )
    if prediction_standard_error < 1e-12:
        probability = float(future_mean_risk >= high_threshold)
    else:
        z = (high_threshold - future_mean_risk) / prediction_standard_error
        probability = 1.0 - normal_cdf(z)
    probability = float(min(max(probability, 0.0), 1.0))

    notes = [
        "Failure estimate is a linear projection of trip-level mean risk to "
        f"the High-risk threshold ({high_threshold:.4f}); it is not a "
        "calibrated probability of mechanical failure.",
        "estimated_failure_probability is the model-based probability of "
        f"crossing that threshold within the next {probability_horizon} "
        "trips.",
    ]
    if latest_risk >= high_threshold:
        cycles = 0
        probability = 1.0
        notes.append("Current trip-level mean risk is already High.")
    elif slope <= 0.0:
        cycles = None
        notes.append(
            "No positive trip-level risk trend was observed; no threshold "
            "crossing cycle is projected."
        )
    else:
        raw_cycles = (high_threshold - latest_risk) / slope
        cycles = int(math.ceil(raw_cycles - 1e-12))
        if cycles > maximum_cycles:
            cycles = None
            notes.append(
                "Projected threshold crossing is beyond the configured "
                f"{maximum_cycles}-trip maximum horizon."
            )

    return FailureEstimate(
        estimated_cycles_to_failure=cycles,
        estimated_failure_probability=round(probability, 4),
        notes=notes,
        trip_risks=trip_risks,
        slope_per_cycle=round(slope, 8),
        intercept=round(intercept, 8),
        high_risk_threshold=high_threshold,
        probability_horizon_cycles=probability_horizon,
    )


def add_estimate_to_output(
    output: dict[str, Any], estimate: FailureEstimate
) -> dict[str, Any]:
    """Add the two contract fields and audit note to one interface JSON."""
    annotated = dict(output)
    annotated.update(estimate.interface_fields())
    notes = list(annotated.get("notes", []))
    if estimate.estimated_failure_probability is not None:
        notes = [
            note for note in notes
            if not str(note).startswith("Failure estimate unavailable:")
        ]
    for note in estimate.notes:
        if note not in notes:
            notes.append(note)
    annotated["notes"] = notes
    return annotated


def markdown_report(estimate: FailureEstimate, source: Path) -> str:
    cycles = estimate.estimated_cycles_to_failure
    probability = estimate.estimated_failure_probability
    lines = [
        "# Failure-estimation result",
        "",
        f"Source risk history: `{source}`.",
        "",
        "## Result",
        "",
        f"- Estimated cycles to High-risk threshold: `{cycles}`.",
        f"- Threshold-crossing probability within the next "
        f"{estimate.probability_horizon_cycles} trips: `{probability}`.",
        f"- High-risk threshold: `{estimate.high_risk_threshold:.4f}`.",
        f"- Estimated trend slope: `{estimate.slope_per_cycle}` "
        "risk score per trip.",
        "",
        "## Method",
        "",
        "Each trip is represented by the mean of its detector-window risk "
        "scores. A least-squares line is fitted across chronological trips:",
        "",
        "```text",
        "r_i = a + b i",
        "```",
        "",
        "where `r_i` is trip-level mean risk and `b` is average risk change "
        "per trip. If `b > 0`, the point estimate is:",
        "",
        "```text",
        "cycles = ceil((High threshold - latest trip risk) / b)",
        "```",
        "",
        "The probability is the normal-error-model probability that the "
        "linear projection crosses the High threshold within the next 10 "
        "trips. It is not a real failure probability.",
        "",
        "## Trip-level history",
        "",
        "| Cycle | Trip | Mean risk | Windows |",
        "|---:|---|---:|---:|",
    ]
    for row in estimate.trip_risks:
        lines.append(
            f"| {row['cycle_index']} | {row['trip_id']} | "
            f"{row['mean_risk_score']:.4f} | {row['window_count']} |"
        )
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in estimate.notes)
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project risk-score history to the High-risk threshold."
    )
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    estimate = estimate_from_history(load_history(args.input))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(estimate.audit_dict(), indent=2) + "\n"
    )
    args.markdown_output.write_text(markdown_report(estimate, args.input))
    print(f"Wrote {args.json_output} and {args.markdown_output}")


if __name__ == "__main__":
    main()
