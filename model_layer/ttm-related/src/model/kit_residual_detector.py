"""
KIT residual detector using IBM Granite TTM.

Consumes the Data Layer's production feature handoff
(`production_features.csv`, INTERFACE.md v0.14 / feature_schema.v1)
directly: raw signals and production features are Data Layer
columns, no internal feature computation.
Pipeline: production feature CSV -> segment-safe window -> TTM forecast ->
residuals -> interface JSON.

Run from the repository root:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py

Optionally pass a specific feature CSV and segment:
    .venv/bin/python ttm-related/src/model/kit_residual_detector.py \
        path/to/production_features.csv --segment-id trip_0001_seg_001

The two anomaly types the Data Layer scores instead of us
(`intake_air_temperature_sensor_fault`,
`map_load_signal_plausibility_fault`) carry a 0.0 placeholder unless
`--proxy-decisions path/to/proxy_decisions.csv` is given, in which case
their already-computed verdicts are forwarded (GL-368, INTERFACE.md
2.4). See `proxy_decision_forwarding.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from tsfm_public.toolkit.get_model import get_model

try:
    from model.input_validation import (
        PRODUCTION_FEATURE_REQUIRED_COLUMNS,
        PLAUSIBLE_RANGES,
        validate_required_columns,
        validate_sensor_ranges,
    )
    from model.proxy_decision_forwarding import (
        ForwardedVerdict,
        forward_verdicts,
        load_proxy_decisions,
    )
    from model.risk_history import (
        DEFAULT_HISTORY_PATH,
        append_history,
        load_history,
    )
    from model.failure_estimation import (
        add_estimate_to_output,
        estimate_from_history,
    )
    from model.validate_output import validate_output
    from model.risk_level_calibration import risk_level
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import (
        PRODUCTION_FEATURE_REQUIRED_COLUMNS,
        PLAUSIBLE_RANGES,
        validate_required_columns,
        validate_sensor_ranges,
    )
    from proxy_decision_forwarding import (
        ForwardedVerdict,
        forward_verdicts,
        load_proxy_decisions,
    )
    from risk_history import (
        DEFAULT_HISTORY_PATH,
        append_history,
        load_history,
    )
    from failure_estimation import (
        add_estimate_to_output,
        estimate_from_history,
    )
    from validate_output import validate_output
    from risk_level_calibration import risk_level


_TTM_RELATED_DIR = Path(__file__).resolve().parents[2]

# Keep the upstream model id as the fine-tuning/zero-shot reference.
MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"
OFFICIAL_DETECTOR_MODEL_PATH = (
    _TTM_RELATED_DIR
    / "outputs" / "ttm_finetuned_e5_lr5e-5" / "model"
)
DEFAULT_INPUT_CSV = Path(
    "data_layer/tests/fixtures/production_features.v1.fixture.csv"
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
PRODUCTION_FEATURE_STRING_COLUMNS = {
    "timestamp",
    "trip_id",
    "segment_id",
    "thermal_state",
    "child_state",
    "operating_state",
    "condition_confidence",
    "condition_quality_flags",
    "engine_start_episode_id",
    "schema_version",
    "calibration_version",
}
PRODUCTION_FEATURE_NUMERIC_COLUMNS = [
    column
    for column in PRODUCTION_FEATURE_REQUIRED_COLUMNS
    if column not in PRODUCTION_FEATURE_STRING_COLUMNS
]

# Healthy reference ranges. Raw-signal ranges come from the Story 1
# baseline; ranges for the delivered engineered features (incl. the
# pending anomaly types' key signals) are healthy 5th-95th
# percentiles measured on delivered Data Layer feature handoffs.
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
    "ect_rate_180s": [0, 2],
    "intake_temp": [-3, 41],
    "ambient_temp": [-7, 25],
    "intake_ambient_delta": [0, 20],
    "speed_density_maf_residual": [-20, 20],
    "rpm_slope": [-120, 135],
    "pedal_mapping_residual": [-10, 10],
    "maf_integral_180s": [0, 2500],
    "intake_temp_stability": [0, 5],
    "map_range_60s": [0, 80],
    # Low-motion guard bound frozen in INTERFACE.md 2.4 for the pedal
    # residual path; also the healthy band for MAP plausibility.
    "pedal_slope": [-2.4, 2.4],
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
    "ect_rate_180s": "°C/min",
    "intake_temp": "°C",
    "ambient_temp": "°C",
    "intake_ambient_delta": "°C",
    "speed_density_maf_residual": "g/s",
    "rpm_slope": "RPM/s",
    "pedal_mapping_residual": "pp",
    "maf_integral_180s": "g",
    "intake_temp_stability": "°C",
    "map_range_60s": "kPa",
    "pedal_slope": "pp/s",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Data Layer's production_features.csv through Granite TTM "
            "residual detection."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help=(
            "Path to Data Layer's production-feature CSV "
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
    parser.add_argument(
        "--batch",
        action="store_true",
        help=(
            "Sweep every eligible segment/window in the input "
            "CSV and emit a summary+windows envelope JSON."
        ),
    )
    parser.add_argument(
        "--proxy-decisions",
        type=Path,
        help=(
            "Optional path to the Data Layer's proxy_decisions.csv "
            "(run summary key proxy_decisions_path). When given, the "
            "two Data-Layer-scored anomaly types carry their "
            "already-computed verdicts instead of a 0.0 placeholder."
        ),
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=DEFAULT_HISTORY_PATH,
        help=(
            "Risk-score history CSV appended per inference "
            f"call. Defaults to {DEFAULT_HISTORY_PATH}."
        ),
    )
    return parser.parse_args()


def load_group1_features(csv_path: Path) -> pd.DataFrame:
    """Load and validate Data Layer's production_features.csv.

    Raises ValueError naming the offending columns when required
    columns are missing, numeric columns contain non-numeric values,
    or fixed contract values drift. Policy NaNs in B-class features
    are by design and pass through untouched.
    """
    if not Path(csv_path).exists():
        raise ValueError(f"Input CSV not found: {csv_path}")
    # The production handoff contains policy-nullable boolean-like
    # columns; one-pass inference avoids chunk-wise mixed-dtype
    # warnings on the full CSV.
    raw = pd.read_csv(csv_path, low_memory=False)
    validate_required_columns(
        raw.columns, PRODUCTION_FEATURE_REQUIRED_COLUMNS, str(csv_path)
    )

    df = raw.copy()
    non_numeric = []
    for column in PRODUCTION_FEATURE_NUMERIC_COLUMNS:
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
    if df["dt_seconds"].isna().any() or not df["dt_seconds"].eq(1.0).all():
        raise ValueError(
            "production_features.csv requires non-null dt_seconds == 1.0"
        )
    if not df["schema_version"].eq("feature_schema.v1").all():
        raise ValueError(
            "production_features.csv schema_version must be feature_schema.v1"
        )
    if not df["calibration_version"].eq("calibration.v1").all():
        raise ValueError(
            "production_features.csv calibration_version must be "
            "calibration.v1"
        )
    bad_operating = (
        df["operating_state"].astype(str).str.startswith("post_warmup_")
        & ~df["operating_state"].astype(str).str.startswith("post_warmup__")
    )
    if bad_operating.any():
        raise ValueError(
            "operating_state must use the schema v1 double-underscore form"
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


def iter_windows(
    segment: pd.DataFrame,
    context_length: int,
    prediction_length: int,
):
    """Yield (index, window) non-overlapping windows in a segment.

    Stride equals the window size (context + forecast) so each
    row feeds exactly one window and windows never cross segment
    boundaries (caller passes one segment at a time).
    """
    window_rows = context_length + prediction_length
    for index in range(len(segment) // window_rows):
        start = index * window_rows
        yield index, segment.iloc[
            start:start + window_rows
        ].reset_index(drop=True)


def analyze_window(
    window: pd.DataFrame,
    context_length: int,
    prediction_length: int,
    model,
    notes: list[str],
    forwarded: dict[str, ForwardedVerdict] | None = None,
) -> dict[str, Any]:
    """Forecast -> residuals -> risk -> interface JSON for one
    window."""
    context, future = select_context_and_truth(
        window, context_length, prediction_length
    )
    prediction = run_ttm_forecast(
        context, context_length, prediction_length, model
    )
    residual = calculate_residuals(prediction, future)
    residual_summary = summarize_residuals(residual)
    ranked_risks, top_signals, notes = calculate_ranked_risks(
        residual_summary, future, notes, forwarded
    )
    return build_ranked_interface_json(
        future=future,
        residual_summary=residual_summary,
        ranked_risks=ranked_risks,
        top_residual_signals=top_signals,
        notes=notes,
    )


def segment_verdicts(
    decisions: pd.DataFrame | None,
    trip_id: str,
    segment_id: str,
) -> dict[str, ForwardedVerdict] | None:
    """Data Layer verdicts covering one segment, or None if unused."""
    if decisions is None:
        return None
    return forward_verdicts(decisions, trip_id, segment_id)


def run_batch(
    df: pd.DataFrame,
    context_length: int,
    prediction_length: int,
    model,
    trip_id: str | None = None,
    decisions: pd.DataFrame | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Sweep all eligible segments/windows; return
    (envelope, history_records).

    Envelope shape proposed to Group 3 (INTERFACE.md v0.10):
    `summary` is the worst window's interface JSON unchanged;
    `windows` carries every window's interface JSON plus
    trip/segment/window identity. Each window JSON is
    schema-validated before identity fields are merged.
    """
    frame = df
    if trip_id is not None:
        frame = frame[frame["trip_id"] == trip_id]
        if frame.empty:
            raise ValueError(
                f"trip_id not found in input: {trip_id}"
            )

    window_entries: list[dict[str, Any]] = []
    pure_results: list[dict[str, Any]] = []
    history_records: list[dict[str, Any]] = []
    for segment_id, segment in frame.groupby(
        "segment_id", sort=False
    ):
        if len(segment) < MIN_SEGMENT_ROWS:
            continue
        segment = segment.sort_values(
            "row_in_segment"
        ).reset_index(drop=True)
        segment, notes = prepare_segment(segment)
        segment_trip = segment["trip_id"].iloc[0]
        # One verdict lookup per segment: decisions are trip/segment
        # grain, so every window in a segment shares the same result.
        forwarded = segment_verdicts(
            decisions, segment_trip, str(segment_id)
        )
        for index, window in iter_windows(
            segment, context_length, prediction_length
        ):
            result = analyze_window(
                window, context_length, prediction_length,
                model, notes, forwarded,
            )
            errors = validate_output(result)
            if errors:
                raise ValueError(
                    f"Output validation failed for segment "
                    f"{segment_id} window {index}: "
                    + "; ".join(errors)
                )
            window_id = f"{segment_id}__w{index:03d}"
            print(
                f"{segment_id} w{index:03d} "
                f"risk={result['risk_score']:.4f} "
                f"{result['anomaly_type']}"
            )
            pure_results.append(result)
            window_entries.append({
                "trip_id": segment_trip,
                "segment_id": segment_id,
                "window_id": window_id,
                **result,
            })
            history_records.append({
                "trip_id": segment_trip,
                "window_id": window_id,
                "timestamp": result["timestamp"],
                "risk_score": result["risk_score"],
            })

    if not window_entries:
        raise ValueError(
            f"No segment with >= {MIN_SEGMENT_ROWS} rows found "
            "(INTERFACE.md 1.5 minimum for TTM windowing)"
        )
    worst = max(
        range(len(pure_results)),
        key=lambda i: pure_results[i]["risk_score"],
    )
    envelope = {
        "summary": pure_results[worst],
        "windows": window_entries,
    }
    return envelope, history_records


def load_model(
    context_length: int,
    prediction_length: int,
):
    model = get_model(
        str(OFFICIAL_DETECTOR_MODEL_PATH),
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


def calculate_ranked_risks(
    residual_summary: dict[str, dict[str, float]],
    future: pd.DataFrame,
    notes: list[str] | None = None,
    forwarded: dict[str, ForwardedVerdict] | None = None,
) -> tuple[
    list[tuple[str, float, float]],
    list[str],
    list[str],
]:
    """Return the two highest-scoring distinct component risks.

    Entries are ``(anomaly_type, risk_score, confidence)`` tuples in
    descending risk order. Python's stable sort preserves the existing
    component priority when scores tie, so the former ``max`` winner
    remains the primary risk while the other high-risk component is no
    longer discarded.
    """
    notes = list(notes) if notes else []
    scores = normalized_residual_scores(residual_summary)

    # pandas aggregations skip NaN, so Data Layer policy NaNs do not
    # poison window stats; finite_or covers the all-NaN-window case.
    coolant_temp = finite_or(float(future["coolant_temp"].max()))
    ect_rate = finite_or(float(future["ect_rate_180s"].mean()))
    maf_residual = finite_or(
        float(future["speed_density_maf_residual"].median())
    )

    # Schema v1 replaces the old coolant_slope/coolant_stability
    # handoff with B-class ect_rate_180s. It is already in degC/min.
    cooling_score = max(
        scores["coolant_temp"],
        clipped_scale(coolant_temp, low=95.0, high=110.0),
        (
            clipped_scale(ect_rate, low=2.0, high=8.0)
            if coolant_temp > 85.0
            else 0.0
        ),
    )
    # Schema v1 keeps the frozen speed-density residual as the
    # reusable MAF/MAP disagreement feature; the old maf_map_cohesion
    # research diagnostic is no longer a production handoff column.
    intake_score = max(
        scores["maf"],
        scores["map"],
        clipped_scale(abs(maf_residual), low=18.0, high=35.0),
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

    # The Data Layer owns DTC scoring for these two types (GL-294/295
    # retirement). Without a decisions file they keep their historical
    # 0.0 placeholder; with one, we relay its already-computed verdict.
    forwarded = forwarded or {}
    anomaly_scores = {
        "cooling_degradation": cooling_score,
        "air_intake_maf_anomaly": intake_score,
        "accelerator_pedal_sensor": pedal_score,
        "intake_air_temperature_sensor_fault": _forwarded_score(
            forwarded, "intake_air_temperature_sensor_fault"
        ),
        "map_load_signal_plausibility_fault": _forwarded_score(
            forwarded, "map_load_signal_plausibility_fault"
        ),
    }
    # Confidence and top signals stay residual-based (TTM channels
    # only); the rule-based pedal score is deliberately excluded.
    top_residual_signals = sorted(scores, key=scores.get, reverse=True)[:3]
    std = float(np.std(list(scores.values())))
    residual_confidence = float(max(0.35, min(0.95, 1.0 - std)))

    ranked_scores = sorted(
        anomaly_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:2]
    ranked_risks: list[tuple[str, float, float]] = []
    for anomaly_type, score in ranked_scores:
        risk_score = float(score)
        confidence = residual_confidence

        # A forwarded verdict carries the Data Layer's own confidence:
        # the residual spread describes a forecast that had no part in it.
        verdict = forwarded.get(anomaly_type)
        if verdict is not None and risk_score > 0.0:
            confidence = float(verdict.confidence)
            if verdict.note and verdict.note not in notes:
                notes.append(verdict.note)
        ranked_risks.append((anomaly_type, risk_score, confidence))

    return ranked_risks, top_residual_signals, notes


def calculate_risk(
    residual_summary: dict[str, dict[str, float]],
    future: pd.DataFrame,
    notes: list[str] | None = None,
    forwarded: dict[str, ForwardedVerdict] | None = None,
) -> tuple[str, float, float, list[str], list[str]]:
    """Backward-compatible view of the highest-ranked component."""
    ranked_risks, top_signals, result_notes = calculate_ranked_risks(
        residual_summary, future, notes, forwarded
    )
    anomaly_type, risk_score, confidence = ranked_risks[0]
    return (
        anomaly_type,
        risk_score,
        confidence,
        top_signals,
        result_notes,
    )


def _forwarded_score(
    forwarded: dict[str, ForwardedVerdict], anomaly_type: str
) -> float:
    verdict = forwarded.get(anomaly_type)
    return float(verdict.score) if verdict is not None else 0.0


def clipped_scale(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return float((value - low) / (high - low))


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
        "ect_rate_180s": lambda: window("ect_rate_180s", "mean"),
        "maf_integral_180s": lambda: window("maf_integral_180s", "mean"),
        "map": lambda: last("map"),
        "maf": lambda: last("maf"),
        "speed_density_maf_residual": lambda: window(
            "speed_density_maf_residual", "median"
        ),
        "tps": lambda: last("tps"),
        "rpm": lambda: last("rpm"),
        "speed": lambda: last("speed"),
        "accel_pedal_d": lambda: last("accel_pedal_d"),
        "accel_pedal_e": lambda: last("accel_pedal_e"),
        "accel_pedal_channel_delta": lambda: window(
            "accel_pedal_channel_delta", "mean"
        ),
        # Pending-type key signals retained in production_features v1.
        "intake_temp": lambda: last("intake_temp"),
        "ambient_temp": lambda: last("ambient_temp"),
        "intake_ambient_delta": lambda: last("intake_ambient_delta"),
        "pedal_slope": lambda: window("pedal_slope", "mean"),
        "rpm_slope": lambda: window("rpm_slope", "mean"),
        "map_range_60s": lambda: window("map_range_60s", "max"),
        "rpm_std_120s": lambda: window("rpm_std_120s", "mean"),
        "speed_std_120s": lambda: window("speed_std_120s", "mean"),
        "accel_pedal_mean_std_120s": lambda: window(
            "accel_pedal_mean_std_120s", "mean"
        ),
        "intake_temp_stability": lambda: window(
            "intake_temp_stability", "mean"
        ),
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
            "coolant_temp", "ect_rate_180s", "maf_integral_180s",
        ],
        "air_intake_maf_anomaly": [
            "maf", "map", "speed_density_maf_residual",
        ],
        "accelerator_pedal_sensor": [
            "accel_pedal_d", "accel_pedal_e",
            "accel_pedal_channel_delta", "pedal_mapping_residual",
        ],
        # Both lists follow INTERFACE.md 2.4's key_signals order,
        # restricted to signals delivered in production_features.csv.
        "intake_air_temperature_sensor_fault": [
            "intake_temp", "intake_temp_stability",
            "intake_ambient_delta", "ambient_temp", "coolant_temp",
        ],
        "map_load_signal_plausibility_fault": [
            "map", "pedal_slope", "speed_density_maf_residual",
            "map_range_60s", "rpm_slope",
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


def build_ranked_interface_json(
    future: pd.DataFrame,
    residual_summary: dict[str, dict[str, float]],
    ranked_risks: list[tuple[str, float, float]],
    top_residual_signals: list[str],
    notes: list[str],
) -> dict[str, Any]:
    """Build the primary interface JSON plus its second-ranked risk.

    The established top-level fields remain the highest risk for
    backwards compatibility. ``secondary_risk`` is itself a complete
    Model Layer single-risk object, allowing a consumer to process it
    with the same field semantics without changing the primary path.
    """
    if len(ranked_risks) < 2:
        raise ValueError("At least two component risks are required")

    outputs = [
        build_interface_json(
            future=future,
            residual_summary=residual_summary,
            anomaly_type=anomaly_type,
            risk_score=score,
            confidence=confidence,
            top_residual_signals=top_residual_signals,
            notes=notes,
        )
        for anomaly_type, score, confidence in ranked_risks[:2]
    ]
    primary, secondary = outputs
    primary["secondary_risk"] = secondary
    return primary


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


def run_single(
    df: pd.DataFrame,
    args: argparse.Namespace,
    decisions: pd.DataFrame | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Original one-window flow; returns (result, history records)."""
    segment = select_segment(
        df, trip_id=args.trip_id, segment_id=args.segment_id
    )
    trip_id_value = segment["trip_id"].iloc[0]
    segment_id = segment["segment_id"].iloc[0]
    print(
        f"Selected trip={trip_id_value} "
        f"segment={segment_id} "
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

    ranked_risks, top_signals, notes = calculate_ranked_risks(
        residual_summary,
        future,
        notes,
        segment_verdicts(decisions, trip_id_value, str(segment_id)),
    )
    result = build_ranked_interface_json(
        future=future,
        residual_summary=residual_summary,
        ranked_risks=ranked_risks,
        top_residual_signals=top_signals,
        notes=notes,
    )
    validation_errors = validate_output(result)
    if validation_errors:
        raise ValueError(
            "Output validation failed: "
            + "; ".join(validation_errors)
        )
    history_records = [{
        "trip_id": trip_id_value,
        "window_id": f"{segment_id}__w000",
        "timestamp": result["timestamp"],
        "risk_score": result["risk_score"],
    }]
    return result, history_records


def run_detector(args: argparse.Namespace) -> None:
    csv_path = args.csv_path or DEFAULT_INPUT_CSV
    print(f"Reading Group 1 feature dataset: {csv_path}")
    print(f"Loading TTM model: {OFFICIAL_DETECTOR_MODEL_PATH}")
    df = load_group1_features(csv_path)

    decisions = None
    if args.proxy_decisions is not None:
        decisions = load_proxy_decisions(args.proxy_decisions)
        print(
            f"Forwarding Data Layer proxy decisions: "
            f"{len(decisions)} row(s) from {args.proxy_decisions}"
        )

    if args.batch:
        if args.segment_id is not None:
            raise ValueError(
                "--segment-id cannot be combined with --batch "
                "(use --trip-id to restrict the sweep)"
            )
        model = load_model(
            args.context_length, args.prediction_length
        )
        result, history_records = run_batch(
            df, args.context_length, args.prediction_length,
            model, trip_id=args.trip_id, decisions=decisions,
        )
    else:
        result, history_records = run_single(df, args, decisions)

    written = append_history(history_records, args.history_file)
    print(
        f"\nRisk history: {written} new record(s) -> "
        f"{args.history_file}"
    )

    estimate = estimate_from_history(load_history(args.history_file))
    if args.batch:
        result["summary"] = add_estimate_to_output(
            result["summary"], estimate
        )
        result["windows"] = [
            {
                **window,
                **add_estimate_to_output(window, estimate),
            }
            for window in result["windows"]
        ]
        for window in result["windows"]:
            errors = validate_output(window)
            if errors:
                raise ValueError(
                    "Output validation failed after failure estimation: "
                    + "; ".join(errors)
                )
    else:
        result = add_estimate_to_output(result, estimate)
        errors = validate_output(result)
        if errors:
            raise ValueError(
                "Output validation failed after failure estimation: "
                + "; ".join(errors)
            )

    print("\nInterface JSON")
    print("-" * 44)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        args.output.write_text(text)
        print(f"\nSaved JSON to {args.output}")


def main() -> int:
    """CLI entry point with dashboard-friendly failures.

    Group 3's dashboard shows stderr to the user, so expected
    failures must be one clear line and a non-zero exit, never
    a traceback (Story 8).
    """
    args = parse_args()
    try:
        run_detector(args)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
