"""
Zero-shot KIT residual detector using IBM Granite TTM.

Consumes the Data Layer's feature-engineered dataset
(`data_layer/feature_engineering/feature_dataset.csv`,
INTERFACE.md Section 1) directly: raw signals and engineered
features are Group 1's columns, no internal feature computation.
Pipeline: feature CSV -> segment-safe window -> TTM forecast ->
residuals -> interface JSON.

Run from the repository root:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py

Optionally pass a specific feature CSV and segment:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py \
        path/to/feature_dataset.csv --segment-id trip_0001_seg_001
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from tsfm_public.toolkit.get_model import get_model

try:
    from model.input_validation import (
        GROUP1_REQUIRED_COLUMNS,
        PLAUSIBLE_RANGES,
        validate_required_columns,
        validate_sensor_ranges,
    )
    from model.validate_output import validate_output
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import (
        GROUP1_REQUIRED_COLUMNS,
        PLAUSIBLE_RANGES,
        validate_required_columns,
        validate_sensor_ranges,
    )
    from validate_output import validate_output


MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"
DEFAULT_INPUT_CSV = Path(
    "data_layer/feature_engineering/feature_dataset.csv"
)
DEFAULT_CONTEXT_LENGTH = 512
DEFAULT_PREDICTION_LENGTH = 96
# INTERFACE.md 1.5: a usable segment must have >= 700 contiguous
# rows (512 context + 96 forecast + margin; windows never cross
# segment boundaries).
MIN_SEGMENT_ROWS = 700

MODEL_SIGNALS = ["rpm", "speed", "coolant_temp", "map", "maf", "tps"]

# Non-numeric identity/condition columns (INTERFACE.md 1.1); every
# other required Group 1 column must be numeric.
GROUP1_STRING_COLUMNS = {
    "timestamp",
    "trip_id",
    "segment_id",
    "thermal_state",
    "child_state",
    "operating_state",
    "condition_confidence",
    "condition_quality_flags",
}
GROUP1_NUMERIC_COLUMNS = [
    column
    for column in GROUP1_REQUIRED_COLUMNS
    if column not in GROUP1_STRING_COLUMNS
]

# Healthy reference ranges. Raw-signal ranges come from the Story 1
# baseline; ranges for the delivered engineered features (incl. the
# pending anomaly types' key signals) are healthy 5th-95th
# percentiles measured on `feature_dataset.csv` (2026-07-13).
REFERENCE_RANGES = {
    "coolant_temp": [90, 95],
    "map": [36, 237],
    "maf": [0, 123],
    "tps": [0, 89],
    "rpm": [0, 3682],
    "speed": [0, 218],
    "accel_pedal_d": [0, 100],
    "accel_pedal_e": [0, 100],
    "accel_pedal_channel_delta": [0, 10],
    # Healthy coolant plateaus below a 2 degC/min sustained rise
    # (INTERFACE.md 2.4) = 0.0333 degC/s in the delivered unit.
    "coolant_slope": [0, 0.0333],
    "coolant_stability": [0, 2],
    # Healthy 96-row window medians reach 2.50 (see calculate_risk).
    "maf_map_cohesion": [0.0, 2.6],
    "intake_temp": [-3, 41],
    "ambient_temp": [-7, 25],
    "intake_ambient_delta": [0, 20],
    "map_slope": [-14, 16],
    "idle_flag": [0, 1],
    "idle_rpm_stability": [0, 90],
    "rpm_slope": [-120, 135],
}

FEATURE_UNITS = {
    "coolant_temp": "°C",
    "map": "kPa",
    "maf": "g/s",
    "tps": "%",
    "rpm": "RPM",
    "speed": "km/h",
    "accel_pedal_d": "%",
    "accel_pedal_e": "%",
    "accel_pedal_channel_delta": "pp",
    "coolant_slope": "°C/s",
    "coolant_stability": "°C",
    "maf_map_cohesion": "z-score",
    "intake_temp": "°C",
    "ambient_temp": "°C",
    "intake_ambient_delta": "°C",
    "map_slope": "kPa/s",
    "idle_flag": "0/1",
    "idle_rpm_stability": "RPM",
    "rpm_slope": "RPM/s",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Group 1's feature_dataset.csv through Granite TTM "
            "zero-shot residual detection."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help=(
            "Path to Group 1's feature-engineered CSV "
            "(INTERFACE.md Section 1). Defaults to "
            f"{DEFAULT_INPUT_CSV}."
        ),
    )
    parser.add_argument(
        "--trip-id",
        help="Restrict segment selection to this trip_id.",
    )
    parser.add_argument(
        "--segment-id",
        help=(
            "Run on this segment_id. Defaults to the first "
            f"segment with >= {MIN_SEGMENT_ROWS} rows."
        ),
    )
    parser.add_argument(
        "--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH
    )
    parser.add_argument(
        "--prediction-length", type=int, default=DEFAULT_PREDICTION_LENGTH
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save the interface JSON.",
    )
    return parser.parse_args()


def load_group1_features(csv_path: Path) -> pd.DataFrame:
    """Load and validate Group 1's feature_dataset.csv.

    Raises ValueError naming the offending columns when required
    columns are missing or numeric columns contain non-numeric
    values. Policy NaNs (feature_dataset_metadata.json
    `missing_value_policy`: event-only features, rolling/slope
    warm-up rows, baseline availability) are by design and pass
    through untouched.
    """
    raw = pd.read_csv(csv_path)
    validate_required_columns(
        raw.columns, GROUP1_REQUIRED_COLUMNS, str(csv_path)
    )

    df = raw.copy()
    non_numeric = []
    for column in GROUP1_NUMERIC_COLUMNS:
        coerced = pd.to_numeric(df[column], errors="coerce")
        if (coerced.isna() & df[column].notna()).any():
            non_numeric.append(column)
        df[column] = coerced
    if non_numeric:
        raise ValueError(
            f"Non-numeric values in numeric columns of {csv_path}: "
            f"{non_numeric}"
        )

    # Delivered timestamps are ISO 8601 at 1 Hz (INTERFACE.md 1.1).
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        bad_count = int(df["timestamp"].isna().sum())
        raise ValueError(
            f"Could not parse {bad_count} timestamp values in {csv_path}"
        )
    return df


def select_segment(
    df: pd.DataFrame,
    trip_id: str | None = None,
    segment_id: str | None = None,
    min_rows: int = MIN_SEGMENT_ROWS,
) -> pd.DataFrame:
    """Return one segment so TTM windows never cross a boundary.

    With no selection flags, picks the first segment (file order)
    with at least ``min_rows`` rows (INTERFACE.md 1.5).
    """
    frame = df
    if trip_id is not None:
        frame = frame[frame["trip_id"] == trip_id]
        if frame.empty:
            raise ValueError(f"trip_id not found in input: {trip_id}")
    if segment_id is not None:
        segment = frame[frame["segment_id"] == segment_id]
        if segment.empty:
            raise ValueError(
                f"segment_id not found in input: {segment_id}"
            )
    else:
        segment = None
        for _, group in frame.groupby("segment_id", sort=False):
            if len(group) >= min_rows:
                segment = group
                break
        if segment is None:
            raise ValueError(
                f"No segment with >= {min_rows} rows found "
                "(INTERFACE.md 1.5 minimum for TTM windowing)"
            )
    return segment.sort_values("row_in_segment").reset_index(drop=True)


def prepare_segment(
    segment: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Plausibility-repair raw signals; return (frame, notes).

    Implausible raw-sensor values become NaN (Story 3 two-tier
    semantics) and raw-signal gaps are interpolated so the TTM
    context is dense. Engineered feature columns are left exactly
    as delivered — their policy NaNs are handled by NaN-safe
    window aggregations downstream.
    """
    validation = validate_sensor_ranges(segment)
    df = validation.df
    raw_columns = [
        column for column in PLAUSIBLE_RANGES if column in df.columns
    ]
    df[raw_columns] = df[raw_columns].interpolate(
        limit_direction="both"
    )
    return df, list(validation.notes)


def select_context_and_truth(
    df: pd.DataFrame, context_length: int, prediction_length: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_length = context_length + prediction_length
    if len(df) < required_length:
        raise ValueError(
            f"Need at least {required_length} rows "
            f"({context_length} context + {prediction_length} "
            f"future), got {len(df)}"
        )
    context = df.iloc[:context_length].copy()
    future = df.iloc[context_length:required_length].copy()
    return context, future


def load_model(context_length: int, prediction_length: int):
    model = get_model(
        MODEL_PATH,
        context_length=context_length,
        prediction_length=prediction_length,
    )
    model.eval()
    return model


def run_ttm_forecast(
    context: pd.DataFrame,
    context_length: int,
    prediction_length: int,
    model=None,
) -> pd.DataFrame:
    context_values = context[MODEL_SIGNALS].to_numpy(dtype=np.float32)
    mean = context_values.mean(axis=0, keepdims=True)
    std = context_values.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)

    normalized_context = (context_values - mean) / std
    past_values = torch.tensor(
        normalized_context, dtype=torch.float32
    ).unsqueeze(0)

    if model is None:
        model = load_model(context_length, prediction_length)
    model.eval()

    with torch.no_grad():
        output = model(past_values=past_values)

    prediction = extract_prediction_tensor(output).detach().cpu().numpy()
    prediction = np.squeeze(prediction)
    if prediction.ndim == 1:
        prediction = prediction.reshape(prediction_length, 1)
    if prediction.shape[0] != prediction_length:
        raise ValueError(
            f"Unexpected TTM prediction length: "
            f"expected {prediction_length}, got {prediction.shape}"
        )
    if prediction.shape[1] != len(MODEL_SIGNALS):
        raise ValueError(
            "Unexpected TTM signal count: "
            f"expected {len(MODEL_SIGNALS)}, "
            f"got prediction shape {prediction.shape}"
        )

    prediction = prediction * std + mean
    return pd.DataFrame(prediction, columns=MODEL_SIGNALS)


def extract_prediction_tensor(output: Any) -> torch.Tensor:
    if hasattr(output, "prediction_outputs"):
        return output.prediction_outputs
    if hasattr(output, "last_hidden_state"):
        return output.last_hidden_state
    if isinstance(output, dict):
        for key in (
            "prediction_outputs", "predictions", "last_hidden_state"
        ):
            if key in output:
                return output[key]
    if isinstance(output, (tuple, list)) and output:
        return output[0]
    raise TypeError(
        f"Could not find prediction tensor in model output: {type(output)}"
    )


def calculate_residuals(
    prediction: pd.DataFrame, truth: pd.DataFrame
) -> pd.DataFrame:
    truth_values = truth[MODEL_SIGNALS].reset_index(drop=True)
    residual = (prediction[MODEL_SIGNALS] - truth_values).abs()
    return residual


def summarize_residuals(
    residual: pd.DataFrame,
) -> dict[str, dict[str, float]]:
    return {
        signal: {
            "mean": float(residual[signal].mean()),
            "max": float(residual[signal].max()),
        }
        for signal in MODEL_SIGNALS
    }


def normalized_residual_scores(
    residual_summary: dict[str, dict[str, float]],
) -> dict[str, float]:
    scores = {}
    for signal, stats in residual_summary.items():
        low, high = REFERENCE_RANGES[signal]
        scale = max(high - low, 1.0)
        scores[signal] = min(stats["mean"] / scale, 1.0)
    return scores


def finite_or(value: float, fallback: float = 0.0) -> float:
    """Guard window aggregates against all-NaN policy columns."""
    return value if np.isfinite(value) else fallback


def calculate_risk(
    residual_summary: dict[str, dict[str, float]],
    future: pd.DataFrame,
    notes: list[str] | None = None,
) -> tuple[str, float, float, list[str], list[str]]:
    notes = list(notes) if notes else []
    scores = normalized_residual_scores(residual_summary)

    # pandas aggregations skip NaN, so Group 1 policy NaNs
    # (slope/rolling warm-up rows) do not poison window stats;
    # finite_or covers the all-NaN-window case.
    coolant_temp = finite_or(float(future["coolant_temp"].max()))
    coolant_slope = finite_or(float(future["coolant_slope"].mean()))
    maf_map_cohesion = finite_or(
        float(future["maf_map_cohesion"].median())
    )

    # coolant_slope is delivered in degC/s (INTERFACE.md 1.3). A
    # sustained rise of 2-3 degC/min instead of a post-warm-up
    # plateau marks cooling degradation (INTERFACE.md 2.4), so the
    # window MEAN slope is scored between 2 degC/min (0.0333 degC/s)
    # and 8 degC/min (0.1333 degC/s). The window max would misfire:
    # the delivered slope is quantised to whole-degree steps, so any
    # 1 degC tick reads 1.0 degC/s and the max exceeds the floor in
    # 75% of healthy gated windows. Healthy gated 96-row window
    # means measured on feature_dataset.csv (2026-07-13):
    # p95 0.031, p99 0.115, max 0.25 degC/s.
    cooling_score = max(
        scores["coolant_temp"],
        clipped_scale(coolant_temp, low=95.0, high=110.0),
        (
            clipped_scale(coolant_slope, low=0.0333, high=0.1333)
            if coolant_temp > 85.0
            else 0.0
        ),
    )
    # maf_map_cohesion is the Data Layer's z-scored MAF/MAP air-load
    # disagreement (INTERFACE.md 1.3), ~0 when both sides agree. The
    # window MEDIAN is scored, not the mean: engine-off rows (rpm=0)
    # inflate the delivered column past 1e6, so healthy window means
    # reach 1.5e6 while medians stay bounded. Floor set from healthy
    # 96-row window medians across all 83 usable segments of
    # feature_dataset.csv (2026-07-13): mean 0.64, p95 1.62,
    # p99 2.28, max 2.50 -> floor 2.6 sits just above the healthy
    # max. (The old 1.8 floor was calibrated on the internal
    # z-score's window mean, max healthy 1.56 — clearly wrong for
    # the delivered column, whose healthy p95 alone is 2.24.)
    intake_score = max(
        scores["maf"],
        scores["map"],
        clipped_scale(maf_map_cohesion, low=2.6, high=4.0),
    )

    # Pedal fault = sustained dual-channel disagreement over the
    # window. Healthy mean delta is ~0.8pp with benign spikes
    # >10pp in ~1% of samples (INTERFACE.md 2.4), so score the
    # window mean between 2pp and 10pp (tunable calibration).
    pedal_delta = float("nan")
    if "accel_pedal_channel_delta" in future.columns:
        pedal_delta = float(future["accel_pedal_channel_delta"].mean())
    if np.isfinite(pedal_delta):
        pedal_score = clipped_scale(pedal_delta, low=2.0, high=10.0)
    else:
        pedal_score = 0.0
        notes.append(
            "accelerator_pedal_sensor score forced to 0.0 "
            "(pedal channels unavailable); anomaly_type falls "
            "back to next-highest score"
        )

    anomaly_scores = {
        "cooling_degradation": cooling_score,
        "air_intake_maf_anomaly": intake_score,
        "accelerator_pedal_sensor": pedal_score,
        # Pending — Data Layer defined, Model Layer scoring TBD
        # (INTERFACE.md 2.3/2.4); key signals are delivered but
        # scoring is out of Story 5 scope.
        "intake_air_temperature_sensor_or_heat_soak_fault": 0.0,
        "map_load_signal_plausibility_fault": 0.0,
        "idle_speed_control_or_surge_degradation": 0.0,
    }
    anomaly_type = max(anomaly_scores, key=anomaly_scores.get)
    risk_score = float(anomaly_scores[anomaly_type])

    # Confidence and top signals stay residual-based (TTM channels
    # only); the rule-based pedal score is deliberately excluded.
    top_residual_signals = sorted(scores, key=scores.get, reverse=True)[:3]
    std = float(np.std(list(scores.values())))
    confidence = float(max(0.35, min(0.95, 1.0 - std)))
    return anomaly_type, risk_score, confidence, top_residual_signals, notes


def clipped_scale(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return float((value - low) / (high - low))


def risk_level(risk_score: float) -> str:
    if risk_score < 0.3:
        return "Low"
    if risk_score <= 0.7:
        return "Medium"
    return "High"


def window_feature_values(future: pd.DataFrame) -> dict[str, float]:
    """NaN-safe key_signal values for the report window.

    Aggregations mirror calculate_risk where a feature drives a
    score. Features absent from the frame or all-NaN in the window
    (policy NaNs) are dropped so no NaN reaches the output JSON.
    """
    last_row = future.iloc[-1]

    def last(column: str) -> float:
        return float(last_row[column])

    def window(column: str, how: str) -> float:
        return float(getattr(future[column], how)())

    aggregations = {
        "coolant_temp": lambda: last("coolant_temp"),
        "coolant_slope": lambda: window("coolant_slope", "mean"),
        "coolant_stability": lambda: window("coolant_stability", "max"),
        "map": lambda: last("map"),
        "maf": lambda: last("maf"),
        "maf_map_cohesion": lambda: window("maf_map_cohesion", "median"),
        "tps": lambda: last("tps"),
        "rpm": lambda: last("rpm"),
        "speed": lambda: last("speed"),
        "accel_pedal_d": lambda: last("accel_pedal_d"),
        "accel_pedal_e": lambda: last("accel_pedal_e"),
        "accel_pedal_channel_delta": lambda: window(
            "accel_pedal_channel_delta", "mean"
        ),
        # Pending-type key signals (INTERFACE.md 2.4), forwarded by
        # Group 1 since v0.6.
        "intake_temp": lambda: last("intake_temp"),
        "ambient_temp": lambda: last("ambient_temp"),
        "intake_ambient_delta": lambda: last("intake_ambient_delta"),
        "map_slope": lambda: window("map_slope", "mean"),
        "idle_flag": lambda: last("idle_flag"),
        "idle_rpm_stability": lambda: window(
            "idle_rpm_stability", "mean"
        ),
        "rpm_slope": lambda: window("rpm_slope", "mean"),
    }

    values: dict[str, float] = {}
    for feature, aggregate in aggregations.items():
        if feature not in future.columns:
            continue
        value = aggregate()
        if np.isfinite(value):
            values[feature] = value
    return values


def build_interface_json(
    future: pd.DataFrame,
    residual_summary: dict[str, dict[str, float]],
    anomaly_type: str,
    risk_score: float,
    confidence: float,
    top_residual_signals: list[str],
    notes: list[str],
) -> dict[str, Any]:
    feature_values = window_feature_values(future)

    priority = {
        "cooling_degradation": [
            "coolant_temp", "coolant_slope", "coolant_stability",
        ],
        "air_intake_maf_anomaly": ["maf", "map", "maf_map_cohesion"],
        "accelerator_pedal_sensor": [
            "accel_pedal_d", "accel_pedal_e",
            "accel_pedal_channel_delta",
        ],
        "intake_air_temperature_sensor_or_heat_soak_fault": [
            "intake_temp", "ambient_temp", "intake_ambient_delta"
        ],
        "map_load_signal_plausibility_fault": [
            "map", "maf", "tps", "map_slope"
        ],
        "idle_speed_control_or_surge_degradation": [
            "rpm", "idle_flag", "idle_rpm_stability", "rpm_slope"
        ],
    }[anomaly_type]

    features = []
    for feature in priority + top_residual_signals:
        if feature in feature_values and feature not in features:
            features.append(feature)
        if len(features) >= 5:
            break

    timestamp = pd.Timestamp(future.iloc[-1]["timestamp"])
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    ts = timestamp.isoformat().replace("+00:00", "Z")
    return {
        "timestamp": ts,
        "anomaly_type": anomaly_type,
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level(risk_score),
        "component": anomaly_type,
        "prediction_confidence": round(confidence, 4),
        "key_signals": [
            {
                "feature": feature,
                "value": round(feature_values[feature], 4),
                "unit": FEATURE_UNITS[feature],
                "reference_range": REFERENCE_RANGES[feature],
            }
            for feature in features
        ],
        # Null placeholders until Story 8 implements the
        # risk-history estimator (INTERFACE.md 2.2, v0.4).
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": notes,
    }


def print_residual_summary(
    residual_summary: dict[str, dict[str, float]],
) -> None:
    print("\nResidual summary by signal")
    print("-" * 44)
    for signal, stats in sorted(
        residual_summary.items(),
        key=lambda item: item[1]["mean"],
        reverse=True,
    ):
        mean_val = stats["mean"]
        max_val = stats["max"]
        print(f"{signal:14s} mean={mean_val:10.4f} max={max_val:10.4f}")


def main() -> None:
    args = parse_args()
    csv_path = args.csv_path or DEFAULT_INPUT_CSV

    print(f"Reading Group 1 feature dataset: {csv_path}")
    df = load_group1_features(csv_path)
    segment = select_segment(
        df, trip_id=args.trip_id, segment_id=args.segment_id
    )
    print(
        f"Selected trip={segment['trip_id'].iloc[0]} "
        f"segment={segment['segment_id'].iloc[0]} "
        f"rows={len(segment)}"
    )
    segment, notes = prepare_segment(segment)

    context, future = select_context_and_truth(
        segment, args.context_length, args.prediction_length
    )
    print(
        f"Context={len(context)} steps, "
        f"target={len(future)} steps, "
        f"signals={MODEL_SIGNALS}"
    )

    model = load_model(args.context_length, args.prediction_length)
    prediction = run_ttm_forecast(
        context, args.context_length, args.prediction_length, model
    )
    residual = calculate_residuals(prediction, future)
    residual_summary = summarize_residuals(residual)
    print_residual_summary(residual_summary)

    anomaly_type, score, confidence, top_signals, notes = calculate_risk(
        residual_summary, future, notes
    )
    result = build_interface_json(
        future=future,
        residual_summary=residual_summary,
        anomaly_type=anomaly_type,
        risk_score=score,
        confidence=confidence,
        top_residual_signals=top_signals,
        notes=notes,
    )
    validation_errors = validate_output(result)
    if validation_errors:
        print("\nOutput validation failed")
        print("-" * 44)
        for error in validation_errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("\nInterface JSON")
    print("-" * 44)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        args.output.write_text(text)
        print(f"\nSaved JSON to {args.output}")


if __name__ == "__main__":
    main()
