"""
Zero-shot KIT residual detector using IBM Granite TTM.

This script is an MVP integration check, not a training script. It verifies:
KIT CSV -> sensor frame -> TTM forecast -> residuals -> interface JSON.

Run from the repository root:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py

Optionally pass a specific KIT trip CSV:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py \
        path/to/trip.csv
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
        validate_required_columns,
        validate_sensor_ranges,
    )
    from model.validate_output import validate_output
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import (
        validate_required_columns,
        validate_sensor_ranges,
    )
    from validate_output import validate_output


MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"
DEFAULT_DATA_DIR = Path("dataset/10.35097-1130/data/dataset/OBD-II-Dataset")
DEFAULT_CONTEXT_LENGTH = 512
DEFAULT_PREDICTION_LENGTH = 96
DEFAULT_RESAMPLE_RULE = "1s"

KIT_COLUMN_MAP = {
    "Time": "timestamp",
    "Engine RPM [RPM]": "rpm",
    "Vehicle Speed Sensor [km/h]": "speed",
    "Engine Coolant Temperature [°C]": "coolant_temp",
    "Intake Manifold Absolute Pressure [kPa]": "map",
    "Air Flow Rate from Mass Flow Sensor [g/s]": "maf",
    "Absolute Throttle Position [%]": "tps",
    "Accelerator Pedal Position D [%]": "accel_pedal_d",
    "Accelerator Pedal Position E [%]": "accel_pedal_e",
}

MODEL_SIGNALS = ["rpm", "speed", "coolant_temp", "map", "maf", "tps"]
REQUIRED_KIT_COLUMNS = [
    "Time",
    "Engine RPM [RPM]",
    "Vehicle Speed Sensor [km/h]",
    "Engine Coolant Temperature [°C]",
    "Intake Manifold Absolute Pressure [kPa]",
    "Air Flow Rate from Mass Flow Sensor [g/s]",
    "Absolute Throttle Position [%]",
]

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
    "coolant_slope": [0, 2],
    "coolant_stability": [0, 2],
    "maf_map_cohesion": [0.0, 1.8],
    "load_stress": [0, 200000],
    "acceleration": [-3, 3],
    "rpm_variation": [0, 500],
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
    "coolant_slope": "°C/min",
    "coolant_stability": "°C",
    "maf_map_cohesion": "z-score",
    "load_stress": "rpm×%",
    "acceleration": "m/s²",
    "rpm_variation": "RPM",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run KIT CSV through Granite TTM zero-shot residual detection."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help=(
            "Path to one KIT OBD-II trip CSV. "
            "Defaults to the first CSV in the KIT data directory."
        ),
    )
    parser.add_argument(
        "--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH
    )
    parser.add_argument(
        "--prediction-length", type=int, default=DEFAULT_PREDICTION_LENGTH
    )
    parser.add_argument("--resample-rule", default=DEFAULT_RESAMPLE_RULE)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save the interface JSON.",
    )
    return parser.parse_args()


def find_default_csv() -> Path:
    csv_files = [
        path
        for path in sorted(DEFAULT_DATA_DIR.glob("*.csv"))
        if path.stem.strip()
    ]
    if not csv_files:
        raise FileNotFoundError(
            f"No KIT CSV files found under {DEFAULT_DATA_DIR}"
        )
    normal = [path for path in csv_files if "Normal" in path.name]
    preferred_files = normal + csv_files
    for path in preferred_files:
        header = pd.read_csv(path, nrows=0).columns
        if all(column in header for column in REQUIRED_KIT_COLUMNS):
            return path
    raise FileNotFoundError(
        "No KIT CSV file contains all required TTM input columns: "
        f"{REQUIRED_KIT_COLUMNS}"
    )


def load_and_resample_kit_csv(
    csv_path: Path, resample_rule: str
) -> tuple[pd.DataFrame, list[str]]:
    """Load one KIT trip CSV; return (frame, degradation notes)."""
    raw = pd.read_csv(csv_path)
    validate_required_columns(
        raw.columns, REQUIRED_KIT_COLUMNS, str(csv_path)
    )

    notes: list[str] = []
    available_column_map = {
        source: target
        for source, target in KIT_COLUMN_MAP.items()
        if source in raw.columns
    }
    pedal_columns = {"accel_pedal_d", "accel_pedal_e"}
    if not pedal_columns.issubset(available_column_map.values()):
        notes.append(
            "accel_pedal_d/accel_pedal_e unavailable in input; "
            "accelerator_pedal_sensor detection disabled"
        )
    df = raw.rename(columns=available_column_map)
    df = df[list(available_column_map.values())].copy()
    df["timestamp"] = parse_kit_time(df["timestamp"])

    numeric_columns = [
        col for col in df.columns if col != "timestamp"
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Repair before resampling so .mean() never blends
    # physically implausible values into neighbouring rows.
    validation = validate_sensor_ranges(df)
    df = validation.df
    notes.extend(validation.notes)

    df = df.sort_values("timestamp").set_index("timestamp")
    df = df.resample(resample_rule).mean()
    df = df.interpolate(
        method="time", limit_direction="both"
    ).ffill().bfill()
    df = df.reset_index()

    return add_derived_features(df), notes


def parse_kit_time(time_series: pd.Series) -> pd.Series:
    """Convert KIT time-of-day strings to a monotonic datetime index."""
    parsed = pd.to_datetime(
        "2026-01-01 " + time_series.astype(str),
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce",
    )
    if parsed.isna().any():
        parsed = pd.to_datetime(
            "2026-01-01 " + time_series.astype(str), errors="coerce"
        )
    if parsed.isna().any():
        bad_count = int(parsed.isna().sum())
        raise ValueError(f"Could not parse {bad_count} KIT Time values")

    # Some trips cross midnight; preserve monotonic time when clock wraps.
    parsed = pd.Series(parsed)
    day_offset = pd.Timedelta(days=0)
    adjusted = []
    previous = None
    for value in parsed:
        candidate = value + day_offset
        if previous is not None and candidate < previous:
            day_offset += pd.Timedelta(days=1)
            candidate = value + day_offset
        adjusted.append(candidate)
        previous = candidate
    return pd.Series(adjusted)


def zscore(series: pd.Series) -> pd.Series:
    """Z-score against current-trip stats (interim baseline).

    Story 6 will replace trip stats with a fitted healthy
    vehicle baseline (failure_type_research.md, B1 formula).
    """
    std = float(series.std())
    if not np.isfinite(std) or std < 1e-6:
        return series * 0.0
    return (series - series.mean()) / std


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["coolant_slope"] = df["coolant_temp"].diff().fillna(0) * 60.0
    df["coolant_stability"] = (
        df["coolant_temp"].rolling(window=30, min_periods=2).std().fillna(0)
    )
    df["acceleration"] = df["speed"].diff().fillna(0) / 3.6
    df["load_stress"] = df["rpm"] * df["tps"]
    # Air-load plausibility (INTERFACE.md 2.4, research note B1):
    # maf_derived_air_load = maf / (rpm / 60)  [g/rev]
    # map_derived_air_load ~ map (speed-density proxy;
    # intake_temp not yet forwarded by Data Layer).
    # Floor at 1 rev/s so engine-off rows do not explode.
    rev_per_s = (df["rpm"] / 60.0).clip(lower=1.0)
    maf_load = df["maf"] / rev_per_s
    map_load = df["map"]
    df["maf_map_cohesion"] = (
        zscore(maf_load) - zscore(map_load)
    ).abs()
    df["rpm_variation"] = (
        df["rpm"].rolling(window=10, min_periods=2).std().fillna(0)
    )
    # Dual-channel pedal disagreement (INTERFACE.md 2.4): the two
    # redundant pedal sensors should track each other; a sustained
    # gap indicates a pedal sensor fault. Only computable when the
    # input forwards both channels.
    if {"accel_pedal_d", "accel_pedal_e"}.issubset(df.columns):
        df["accel_pedal_channel_delta"] = (
            df["accel_pedal_d"] - df["accel_pedal_e"]
        ).abs()
    return df


def select_context_and_truth(
    df: pd.DataFrame, context_length: int, prediction_length: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_length = context_length + prediction_length
    if len(df) < required_length:
        raise ValueError(
            f"Need at least {required_length} resampled rows "
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


def calculate_risk(
    residual_summary: dict[str, dict[str, float]],
    future: pd.DataFrame,
    notes: list[str] | None = None,
) -> tuple[str, float, float, list[str], list[str]]:
    notes = list(notes) if notes else []
    scores = normalized_residual_scores(residual_summary)

    coolant_temp = float(future["coolant_temp"].max())
    coolant_slope = float(future["coolant_slope"].max())
    maf_map_cohesion = float(future["maf_map_cohesion"].mean())
    load_stress = float(future["load_stress"].max())

    cooling_score = max(
        scores["coolant_temp"],
        clipped_scale(coolant_temp, low=95.0, high=110.0),
        (
            clipped_scale(coolant_slope, low=2.0, high=8.0)
            if coolant_temp > 85.0
            else 0.0
        ),
    )
    intake_score = max(
        scores["maf"],
        scores["map"],
        # Cohesion is a z-score deviation, ~0 when MAF/MAP-side
        # air loads agree. Floor calibrated above the max healthy
        # future-window mean (1.56 across 36 Normal/Frei trips).
        clipped_scale(maf_map_cohesion, low=1.8, high=3.0),
    )
    _ = max(
        scores["rpm"],
        scores["tps"],
        clipped_scale(load_stress, low=120000.0, high=250000.0),
    )

    # Pedal fault = sustained dual-channel disagreement over the
    # window. Healthy mean delta is ~0.8pp with benign spikes
    # >10pp in ~1% of samples (INTERFACE.md 2.4), so score the
    # window mean between 2pp and 10pp (tunable calibration).
    if "accel_pedal_channel_delta" in future.columns:
        pedal_score = clipped_scale(
            float(future["accel_pedal_channel_delta"].mean()),
            low=2.0,
            high=10.0,
        )
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
        # Pending — Data Layer signals not yet forwarded
        # (INTERFACE.md 2.3/2.4, added 2026-06-29).
        "intake_air_temperature_sensor_or_heat_soak_fault": 0.0,
        "map_load_signal_plausibility_fault": 0.0,
        "electronic_throttle_tracking_fault": 0.0,
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


def build_interface_json(
    future: pd.DataFrame,
    residual_summary: dict[str, dict[str, float]],
    anomaly_type: str,
    risk_score: float,
    confidence: float,
    top_residual_signals: list[str],
    notes: list[str],
) -> dict[str, Any]:
    last_future_row = future.iloc[-1]
    feature_values = {
        "coolant_temp": float(last_future_row["coolant_temp"]),
        "coolant_slope": float(future["coolant_slope"].max()),
        "coolant_stability": float(future["coolant_stability"].max()),
        "map": float(last_future_row["map"]),
        "maf": float(last_future_row["maf"]),
        "maf_map_cohesion": float(future["maf_map_cohesion"].mean()),
        "tps": float(last_future_row["tps"]),
        "rpm": float(last_future_row["rpm"]),
        "speed": float(last_future_row["speed"]),
        "load_stress": float(future["load_stress"].max()),
        "acceleration": float(future["acceleration"].max()),
        "rpm_variation": float(future["rpm_variation"].max()),
    }
    for pedal_column in ("accel_pedal_d", "accel_pedal_e"):
        if pedal_column in future.columns:
            feature_values[pedal_column] = float(
                last_future_row[pedal_column]
            )
    if "accel_pedal_channel_delta" in future.columns:
        feature_values["accel_pedal_channel_delta"] = float(
            future["accel_pedal_channel_delta"].mean()
        )

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
        "electronic_throttle_tracking_fault": [
            "accel_pedal_d", "accel_pedal_e", "tps",
            "pedal_throttle_gap"
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

    ts = pd.Timestamp(last_future_row["timestamp"]).isoformat() + "Z"
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
    csv_path = args.csv_path or find_default_csv()

    print(f"Reading KIT CSV: {csv_path}")
    df, notes = load_and_resample_kit_csv(csv_path, args.resample_rule)
    print(f"Resampled rows: {len(df)} at rule={args.resample_rule}")

    context, future = select_context_and_truth(
        df, args.context_length, args.prediction_length
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
