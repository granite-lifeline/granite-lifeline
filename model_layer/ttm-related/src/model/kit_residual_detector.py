"""
Zero-shot KIT residual detector using IBM Granite TTM.

This script is an MVP integration check, not a training script. It verifies:
KIT CSV -> fixed-step sensor frame -> TTM forecast -> residuals -> interface JSON.

Run from the repository root:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py

Optionally pass a specific KIT trip CSV:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py \
        dataset/10.35097-1130/data/dataset/OBD-II-Dataset/2018-03-01_Seat_Leon_RT_S_Normal.csv
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
    "coolant_slope": [0, 2],
    "maf_map_cohesion": [0.1, 0.3],
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
    "coolant_slope": "°C/min",
    "maf_map_cohesion": "ratio",
    "load_stress": "rpm×%",
    "acceleration": "m/s²",
    "rpm_variation": "RPM",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run KIT CSV through Granite TTM zero-shot residual detection."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help="Path to one KIT OBD-II trip CSV. Defaults to the first CSV in the KIT data directory.",
    )
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--prediction-length", type=int, default=DEFAULT_PREDICTION_LENGTH)
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
        raise FileNotFoundError(f"No KIT CSV files found under {DEFAULT_DATA_DIR}")
    preferred_files = [path for path in csv_files if "Normal" in path.name] + csv_files
    for path in preferred_files:
        header = pd.read_csv(path, nrows=0).columns
        if all(column in header for column in REQUIRED_KIT_COLUMNS):
            return path
    raise FileNotFoundError(
        "No KIT CSV file contains all required TTM input columns: "
        f"{REQUIRED_KIT_COLUMNS}"
    )


def load_and_resample_kit_csv(csv_path: Path, resample_rule: str) -> pd.DataFrame:
    raw = pd.read_csv(csv_path)
    missing = [col for col in REQUIRED_KIT_COLUMNS if col not in raw.columns]
    if missing:
        raise ValueError(f"Missing expected KIT columns in {csv_path}: {missing}")

    available_column_map = {
        source: target for source, target in KIT_COLUMN_MAP.items() if source in raw.columns
    }
    df = raw.rename(columns=available_column_map)[list(available_column_map.values())].copy()
    df["timestamp"] = parse_kit_time(df["timestamp"])

    numeric_columns = [column for column in df.columns if column != "timestamp"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.sort_values("timestamp").set_index("timestamp")
    df = df.resample(resample_rule).mean()
    df = df.interpolate(method="time", limit_direction="both").ffill().bfill()
    df = df.reset_index()

    return add_derived_features(df)


def parse_kit_time(time_series: pd.Series) -> pd.Series:
    """Convert KIT time-of-day strings to a monotonic datetime index."""
    parsed = pd.to_datetime(
        "2026-01-01 " + time_series.astype(str),
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce",
    )
    if parsed.isna().any():
        parsed = pd.to_datetime("2026-01-01 " + time_series.astype(str), errors="coerce")
    if parsed.isna().any():
        bad_count = int(parsed.isna().sum())
        raise ValueError(f"Could not parse {bad_count} KIT Time values")

    # Some trips can cross midnight. Preserve monotonic time if clock time wraps.
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


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["coolant_slope"] = df["coolant_temp"].diff().fillna(0) * 60.0
    df["acceleration"] = df["speed"].diff().fillna(0) / 3.6
    df["load_stress"] = df["rpm"] * df["tps"]
    df["maf_map_cohesion"] = df["maf"] / df["map"].replace(0, np.nan)
    df["maf_map_cohesion"] = df["maf_map_cohesion"].replace([np.inf, -np.inf], np.nan)
    df["maf_map_cohesion"] = df["maf_map_cohesion"].interpolate(limit_direction="both")
    df["rpm_variation"] = df["rpm"].rolling(window=10, min_periods=2).std().fillna(0)
    return df


def select_context_and_truth(
    df: pd.DataFrame, context_length: int, prediction_length: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_length = context_length + prediction_length
    if len(df) < required_length:
        raise ValueError(
            f"Need at least {required_length} resampled rows "
            f"({context_length} context + {prediction_length} future), got {len(df)}"
        )
    return df.iloc[:context_length].copy(), df.iloc[context_length:required_length].copy()


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
    past_values = torch.tensor(normalized_context, dtype=torch.float32).unsqueeze(0)

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
            f"Unexpected TTM prediction length: expected {prediction_length}, got {prediction.shape}"
        )
    if prediction.shape[1] != len(MODEL_SIGNALS):
        raise ValueError(
            "Unexpected TTM signal count: "
            f"expected {len(MODEL_SIGNALS)}, got prediction shape {prediction.shape}"
        )

    prediction = prediction * std + mean
    return pd.DataFrame(prediction, columns=MODEL_SIGNALS)


def extract_prediction_tensor(output: Any) -> torch.Tensor:
    if hasattr(output, "prediction_outputs"):
        return output.prediction_outputs
    if hasattr(output, "last_hidden_state"):
        return output.last_hidden_state
    if isinstance(output, dict):
        for key in ("prediction_outputs", "predictions", "last_hidden_state"):
            if key in output:
                return output[key]
    if isinstance(output, (tuple, list)) and output:
        return output[0]
    raise TypeError(f"Could not find prediction tensor in model output: {type(output)}")


def calculate_residuals(prediction: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    truth_values = truth[MODEL_SIGNALS].reset_index(drop=True)
    residual = (prediction[MODEL_SIGNALS] - truth_values).abs()
    return residual


def summarize_residuals(residual: pd.DataFrame) -> dict[str, dict[str, float]]:
    return {
        signal: {
            "mean": float(residual[signal].mean()),
            "max": float(residual[signal].max()),
        }
        for signal in MODEL_SIGNALS
    }


def normalized_residual_scores(residual_summary: dict[str, dict[str, float]]) -> dict[str, float]:
    scores = {}
    for signal, stats in residual_summary.items():
        low, high = REFERENCE_RANGES[signal]
        scale = max(high - low, 1.0)
        scores[signal] = min(stats["mean"] / scale, 1.0)
    return scores


def calculate_risk(
    residual_summary: dict[str, dict[str, float]],
    future: pd.DataFrame,
) -> tuple[str, float, float, list[str]]:
    scores = normalized_residual_scores(residual_summary)

    coolant_temp = float(future["coolant_temp"].max())
    coolant_slope = float(future["coolant_slope"].max())
    maf_map_cohesion = float(future["maf_map_cohesion"].mean())
    load_stress = float(future["load_stress"].max())

    cooling_score = max(
        scores["coolant_temp"],
        clipped_scale(coolant_temp, low=95.0, high=110.0),
        clipped_scale(coolant_slope, low=2.0, high=8.0) if coolant_temp > 85.0 else 0.0,
    )
    intake_score = max(
        scores["maf"],
        scores["map"],
        clipped_scale(abs(maf_map_cohesion - 0.2), low=0.15, high=0.45),
    )
    load_score = max(
        scores["rpm"],
        scores["tps"],
        clipped_scale(load_stress, low=120000.0, high=250000.0),
    )

    anomaly_scores = {
        "cooling_system_stress": cooling_score,
        "air_intake_maf_anomaly": intake_score,
        # accel_pedal_d/e not yet forwarded by Group 1 — detection disabled until Story 5
        "accelerator_pedal_sensor": 0.0,
    }
    anomaly_type = max(anomaly_scores, key=anomaly_scores.get)
    risk_score = float(anomaly_scores[anomaly_type])

    top_residual_signals = sorted(scores, key=scores.get, reverse=True)[:3]
    confidence = float(max(0.35, min(0.95, 1.0 - np.std(list(scores.values())))))
    return anomaly_type, risk_score, confidence, top_residual_signals


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
) -> dict[str, Any]:
    last_future_row = future.iloc[-1]
    feature_values = {
        "coolant_temp": float(last_future_row["coolant_temp"]),
        "coolant_slope": float(future["coolant_slope"].max()),
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

    priority = {
        "cooling_system_stress": ["coolant_temp", "coolant_slope"],
        "air_intake_maf_anomaly": ["maf", "map", "maf_map_cohesion"],
        "accelerator_pedal_sensor": ["accel_pedal_d", "accel_pedal_e"],
    }[anomaly_type]

    features = []
    for feature in priority + top_residual_signals:
        if feature in feature_values and feature not in features:
            features.append(feature)
        if len(features) >= 5:
            break

    return {
        "timestamp": pd.Timestamp(last_future_row["timestamp"]).isoformat() + "Z",
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
    }


def print_residual_summary(residual_summary: dict[str, dict[str, float]]) -> None:
    print("\nResidual summary by signal")
    print("-" * 44)
    for signal, stats in sorted(
        residual_summary.items(), key=lambda item: item[1]["mean"], reverse=True
    ):
        print(f"{signal:14s} mean={stats['mean']:10.4f} max={stats['max']:10.4f}")


def main() -> None:
    args = parse_args()
    csv_path = args.csv_path or find_default_csv()

    print(f"Reading KIT CSV: {csv_path}")
    df = load_and_resample_kit_csv(csv_path, args.resample_rule)
    print(f"Resampled rows: {len(df)} at rule={args.resample_rule}")

    context, future = select_context_and_truth(
        df, args.context_length, args.prediction_length
    )
    print(
        f"Using context={len(context)} steps and forecast target={len(future)} steps "
        f"for signals={MODEL_SIGNALS}"
    )

    model = load_model(args.context_length, args.prediction_length)
    prediction = run_ttm_forecast(context, args.context_length, args.prediction_length, model)
    residual = calculate_residuals(prediction, future)
    residual_summary = summarize_residuals(residual)
    print_residual_summary(residual_summary)

    anomaly_type, score, confidence, top_signals = calculate_risk(
        residual_summary, future
    )
    result = build_interface_json(
        future=future,
        residual_summary=residual_summary,
        anomaly_type=anomaly_type,
        risk_score=score,
        confidence=confidence,
        top_residual_signals=top_signals,
    )

    print("\nInterface JSON")
    print("-" * 44)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"\nSaved JSON to {args.output}")


if __name__ == "__main__":
    main()
