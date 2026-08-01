"""Schema-v1 synthetic faults for the Story 7/GL-322 evaluation.

Faults begin at the context/future boundary and are propagated through every
delivered feature that is an exact function of the changed raw signal.  The
injectors deliberately do not encode the detector thresholds: they simulate
sensor/process changes, while scoring remains an independent operation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

COOLING_OFFSET_C = 15.0
MAF_GAIN = 0.7
MAP_GAIN = 1.25
KELVIN_OFFSET = 273.15
ECT_RATE_WINDOW_ROWS = 180
ECT_RATE_DIVISOR_MIN = 3.0
PEDAL_STD_WINDOW_ROWS = 120

DEFAULT_CALIBRATION_REGISTRY = Path(
    "data_layer/calibration/calibration_registry.v1.json"
)


def load_feature_transforms(
    path: Path = DEFAULT_CALIBRATION_REGISTRY,
) -> dict[str, dict[str, object]]:
    """Load the two frozen transforms required for propagation."""
    with open(path) as handle:
        transforms = json.load(handle)["feature_transforms"]
    speed = transforms["speed_density_maf"]
    pedal = transforms["pedal_mapping"]
    return {
        "speed_density_maf": {
            "coefficients": dict(speed["coefficients"]),
            "intercept": float(speed["intercept"]),
            "ordered_input_features": list(
                speed["ordered_input_features"]
            ),
            "prediction_clipping_bounds": {
                name: dict(bounds)
                for name, bounds in
                speed["prediction_clipping_bounds"].items()
            },
        },
        "pedal_mapping": {
            "a": float(pedal["a"]),
            "b": float(pedal["b"]),
        },
    }


def load_speed_density_transform(
    path: Path = DEFAULT_CALIBRATION_REGISTRY,
) -> dict[str, object]:
    """Backward-compatible loader for the active MAF injector."""
    return load_feature_transforms(path)["speed_density_maf"]


def masked_assign(
    df: pd.DataFrame,
    rows: pd.Index,
    column: str,
    values: pd.Series,
) -> None:
    """Assign values while preserving policy NaNs from the delivery."""
    original = df.loc[rows, column]
    df.loc[rows, column] = values.where(original.notna())


def recompute_ect_rate_180s(df: pd.DataFrame, rows: pd.Index) -> None:
    rate = (
        df["coolant_temp"]
        - df["coolant_temp"].shift(ECT_RATE_WINDOW_ROWS)
    ) / ECT_RATE_DIVISOR_MIN
    masked_assign(df, rows, "ect_rate_180s", rate.loc[rows])


def recompute_speed_density_maf_residual(
    df: pd.DataFrame,
    rows: pd.Index,
    transform: dict[str, object],
) -> None:
    sub = df.loc[rows]
    model_inputs = {
        "map_derived_air_load_raw": (
            sub["map"] * sub["rpm"]
            / (sub["intake_temp"] + KELVIN_OFFSET)
        ),
        "map": sub["map"],
        "rpm": sub["rpm"],
        "intake_temp": sub["intake_temp"],
    }
    predicted = pd.Series(
        float(transform["intercept"]), index=rows, dtype=float
    )
    for name in transform["ordered_input_features"]:
        bounds = transform["prediction_clipping_bounds"][name]
        predicted += float(transform["coefficients"][name]) * (
            model_inputs[name].clip(bounds["lower"], bounds["upper"])
        )
    masked_assign(
        df, rows, "speed_density_maf_residual", sub["maf"] - predicted
    )


def inject_cooling_fault(
    df: pd.DataFrame,
    start_row: int = 0,
    offset_c: float = COOLING_OFFSET_C,
) -> pd.DataFrame:
    """Add a sustained coolant-temperature offset."""
    injected = df.copy()
    rows = injected.index[start_row:]
    injected["coolant_temp"] = injected["coolant_temp"].astype(float)
    injected.loc[rows, "coolant_temp"] += offset_c
    if "coolant_ambient_delta" in injected:
        injected.loc[rows, "coolant_ambient_delta"] += offset_c
    if "ect_rate_180s" in injected:
        recompute_ect_rate_180s(injected, rows)
    return injected


def inject_intake_maf_fault(
    df: pd.DataFrame,
    variant: str,
    transform: dict[str, object],
    start_row: int = 0,
    gain: float | None = None,
) -> pd.DataFrame:
    """Inject a MAF under-read or a MAP attribution control."""
    if variant == "low_maf":
        signal, selected_gain = "maf", MAF_GAIN
    elif variant == "map_bias":
        signal, selected_gain = "map", MAP_GAIN
    else:
        raise ValueError(
            f"Unknown intake fault variant: {variant!r} "
            "(expected 'low_maf' or 'map_bias')"
        )
    selected_gain = selected_gain if gain is None else gain
    injected = df.copy()
    rows = injected.index[start_row:]
    injected[signal] = injected[signal].astype(float)
    injected.loc[rows, signal] *= selected_gain
    recompute_speed_density_maf_residual(injected, rows, transform)
    return injected


def _recompute_pedal_features(
    df: pd.DataFrame,
    rows: pd.Index,
    transform: dict[str, object],
) -> None:
    d = pd.to_numeric(df["accel_pedal_d"], errors="coerce")
    e = pd.to_numeric(df["accel_pedal_e"], errors="coerce")
    mean = (d + e) / 2.0
    masked_assign(df, rows, "accel_pedal_mean", mean.loc[rows])
    masked_assign(
        df, rows, "accel_pedal_channel_delta", (d - e).abs().loc[rows]
    )

    timestamps = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    elapsed = timestamps.diff().dt.total_seconds()
    slope = mean.diff().div(elapsed).where(elapsed.gt(0))
    masked_assign(df, rows, "pedal_slope", slope.loc[rows])

    residual = e - (
        float(transform["a"]) * d + float(transform["b"])
    )
    masked_assign(df, rows, "pedal_mapping_residual", residual.loc[rows])

    rolling = mean.rolling(
        PEDAL_STD_WINDOW_ROWS,
        min_periods=PEDAL_STD_WINDOW_ROWS,
    ).std(ddof=1)
    masked_assign(
        df, rows, "accel_pedal_mean_std_120s", rolling.loc[rows]
    )


def inject_pedal_sensor_fault(
    df: pd.DataFrame,
    transform: dict[str, object],
    start_row: int = 0,
    *,
    channel: str = "d",
    mode: str = "offset",
    magnitude: float = 10.0,
) -> pd.DataFrame:
    """Perturb one redundant pedal channel and propagate its features.

    ``offset`` uses percentage points; ``gain`` multiplies the channel.
    Values are clipped to the physical 0..100 percent range.
    """
    if channel not in {"d", "e"}:
        raise ValueError("channel must be 'd' or 'e'")
    if mode not in {"offset", "gain"}:
        raise ValueError("mode must be 'offset' or 'gain'")

    injected = df.copy()
    rows = injected.index[start_row:]
    signal = f"accel_pedal_{channel}"
    injected[signal] = injected[signal].astype(float)
    values = injected.loc[rows, signal]
    changed = values + magnitude if mode == "offset" else values * magnitude
    injected.loc[rows, signal] = changed.clip(0.0, 100.0)
    _recompute_pedal_features(injected, rows, transform)
    return injected
