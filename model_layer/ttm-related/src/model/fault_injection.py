"""
Synthetic fault injection for Story 7 detector evaluation (Lucca).

Perturbs healthy Group 1 `feature_dataset.csv` segments with the
three agreed scenarios (user_stories.md Story 7):

- `inject_cooling_fault`: `coolant_temp + 15 degC` — the Data
  Layer's Stage 4 cooling design, "sustained positive offset above
  critical band" (proxy_support.md section 2). Ground truth:
  `cooling_degradation`.
- `inject_intake_maf_fault("low_maf")`: `maf x 0.7` — inside the
  Stage 4 MAF design "multiplicative gain drift (0.7...0.95x) ...
  on `maf` only" (proxy_support.md section 3). Ground truth:
  `air_intake_maf_anomaly`.
- `inject_intake_maf_fault("map_bias")`: `map x 1.25` — our own
  cohesion-attribution test. proxy_support.md scopes MAP injection
  to the pending `map_load_signal_plausibility_fault`, so this
  scenario deviates from the Data Layer design; the expected
  detector label remains `air_intake_maf_anomaly` (recorded for
  the Story 7 evaluation note). Ground truth:
  `air_intake_maf_anomaly`.

Injection happens at the raw-sensor level and is then propagated
into the engineered columns that are exact functions of the
perturbed signal, because Group 1 computes those columns from the
raw signals — a frame with a faulty `maf` but a healthy
`maf_map_cohesion` could never come out of their pipeline.
Verified against the delivered dataset (reconstruction error
<= 5e-7):

    maf_derived_air_load_raw = 60 * maf / rpm
    map_derived_air_load_raw = map * rpm / (intake_temp + 273.15)
    maf_map_cohesion = |z(maf_load) - z(map_load)|

with z-score parameters published in feature_baselines.json
(`standardization_parameters.maf_map_cohesion`). Both intermediates
are linear in the perturbed signal, so a gain on `maf`/`map` is a
gain on the corresponding air load, and cohesion is recomputed from
the scaled loads. Other engineered columns (`coolant_slope`,
`map_slope`, `speed_density_maf_residual`, ...) are left as
delivered: the detector does not score them and a constant
offset/gain barely changes a slope.

The pending-three-types scenarios (user_stories.md Story 7,
proxy_support.md section 4-6 Stage 4 TBD-1) follow the same
raw-signal + exact-propagation approach:

- `inject_intake_air_temp_fault`: `intake_temp` frozen at its
  fault-onset value (stuck IAT sensor, F1). Ground truth:
  `intake_air_temperature_sensor_or_heat_soak_fault` (INTERFACE.md
  naming; proxy_support.md section 4's heading is a naming drift).
- `inject_map_plausibility_fault`: `map` frozen at its fault-onset
  value (stuck MAP, F3; also suppresses any step response across
  pedal-step events in the window, F1). Injection on `map` only —
  distinct from the `map x 1.25` cohesion-attribution scenario.
  Ground truth: `map_load_signal_plausibility_fault`.
- `inject_idle_speed_fault`: steady positive `rpm` offset plus a
  low-frequency sine (0.125 Hz, inside the <= 0.5 Hz aliasing
  bound) applied to idle rows only (`idle_flag == 1`) — the
  vehicle is still genuinely idling, so `idle_flag` stays as
  delivered. Ground truth:
  `idle_speed_control_or_surge_degradation`.

Because Ray's pending-type scoring reads the engineered columns
these signals feed, the same "could never come out of Group 1's
pipeline" argument applies. Additional propagation formulas
verified on the delivered dataset (reconstruction error <= 5e-7):

    intake_ambient_delta = intake_temp - ambient_temp
    <sig>_slope          = diff(<sig>) / dt_seconds  (per segment)
    speed_density_maf_residual
        = maf - speed_density_model(map_load, map, rpm, intake_temp)
          (linear regression published in feature_baselines.json
          `models.speed_density_model`; inputs clipped to its
          winsorize_bounds before prediction)
    idle_rpm_stability
        = rolling std (30 samples, min_periods=1) of rpm restricted
          to idle rows, reported on idle rows only

Recomputed columns keep the delivered NaN mask (policy NaNs stay
NaN), and recomputation on unaffected rows reproduces the
delivered values to within the error above.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Story 7 scenario constants (user_stories.md acceptance criteria,
# corroborated by proxy_support.md Stage 4 — see module docstring).
COOLING_OFFSET_C = 15.0
MAF_GAIN = 0.7
MAP_GAIN = 1.25

# Idle-speed fault constants (proxy_support.md section 6 Stage 4
# TBD-1: offsets +/-50..300 rpm, oscillation <= 0.5 Hz with
# 30..300 rpm amplitude). The offset sits above CARB's +200 rpm
# tolerance band so the S1 steady-state check sees a true fault;
# 0.125 Hz respects the 1 Hz sampling aliasing bound.
IDLE_OFFSET_RPM = 250.0
IDLE_OSC_AMPLITUDE_RPM = 100.0
IDLE_OSC_PERIOD_S = 8.0

# Group 1's idle_rpm_stability window: 30-sample rolling std of rpm
# restricted to idle rows (reconstruction verified <= 5e-7).
IDLE_STABILITY_WINDOW_ROWS = 30

KELVIN_OFFSET = 273.15

SPEED_DENSITY_INPUTS = [
    "map_derived_air_load_raw",
    "map",
    "rpm",
    "intake_temp",
]

# Same repo-root-relative convention as the detector's
# DEFAULT_INPUT_CSV.
DEFAULT_BASELINES_JSON = Path(
    "data_layer/feature_engineering/feature_baselines.json"
)

MAF_LOAD = "maf_derived_air_load_raw"
MAP_LOAD = "map_derived_air_load_raw"


def load_cohesion_params(
    path: Path = DEFAULT_BASELINES_JSON,
) -> dict[str, dict[str, float]]:
    """Load the cohesion z-score parameters from Group 1's
    feature_baselines.json: mean/std of both air-load intermediates
    on the golden post-warm-up steady-driving reference."""
    with open(path) as handle:
        baselines = json.load(handle)
    params = baselines["standardization_parameters"]["maf_map_cohesion"]
    return {
        MAF_LOAD: dict(params[MAF_LOAD]),
        MAP_LOAD: dict(params[MAP_LOAD]),
    }


def inject_cooling_fault(
    df: pd.DataFrame,
    start_row: int = 0,
    offset_c: float = COOLING_OFFSET_C,
) -> pd.DataFrame:
    """Sustained positive coolant offset from ``start_row`` on.

    Adds ``offset_c`` to `coolant_temp` and, consistently, to
    `coolant_ambient_delta` (= coolant_temp - ambient_temp).
    Returns a copy; the input frame is not modified.
    """
    injected = df.copy()
    rows = injected.index[start_row:]
    injected.loc[rows, "coolant_temp"] += offset_c
    if "coolant_ambient_delta" in injected.columns:
        injected.loc[rows, "coolant_ambient_delta"] += offset_c
    return injected


def inject_intake_maf_fault(
    df: pd.DataFrame,
    variant: str,
    cohesion_params: dict[str, dict[str, float]],
    start_row: int = 0,
    gain: float | None = None,
) -> pd.DataFrame:
    """Air-intake gain fault from ``start_row`` on.

    ``variant="low_maf"``: `maf` (and its air load) scaled by
    ``gain`` (default MAF_GAIN = 0.7).
    ``variant="map_bias"``: `map` (and its air load) scaled by
    ``gain`` (default MAP_GAIN = 1.25).

    `maf_map_cohesion` is recomputed on the affected rows from the
    scaled air loads with ``cohesion_params`` (see
    ``load_cohesion_params``). Policy NaNs propagate: a NaN input
    cell stays NaN in the signal, its air load, and cohesion.
    Returns a copy; the input frame is not modified.
    """
    if variant == "low_maf":
        signal, load = "maf", MAF_LOAD
        gain = MAF_GAIN if gain is None else gain
    elif variant == "map_bias":
        signal, load = "map", MAP_LOAD
        gain = MAP_GAIN if gain is None else gain
    else:
        raise ValueError(
            f"Unknown intake fault variant: {variant!r} "
            "(expected 'low_maf' or 'map_bias')"
        )

    injected = df.copy()
    rows = injected.index[start_row:]
    injected.loc[rows, signal] *= gain
    injected.loc[rows, load] *= gain

    z_maf = zscore(injected.loc[rows, MAF_LOAD], cohesion_params[MAF_LOAD])
    z_map = zscore(injected.loc[rows, MAP_LOAD], cohesion_params[MAP_LOAD])
    injected.loc[rows, "maf_map_cohesion"] = (z_maf - z_map).abs()
    return injected


def zscore(
    values: pd.Series, params: dict[str, float]
) -> pd.Series:
    return (values - params["mean"]) / params["std"]


def load_speed_density_model(
    path: Path = DEFAULT_BASELINES_JSON,
) -> dict[str, object]:
    """Load Group 1's published speed-density regression from
    feature_baselines.json (`models.speed_density_model`):
    coefficients, intercept, and the winsorize bounds applied to
    the inputs at prediction time."""
    with open(path) as handle:
        baselines = json.load(handle)
    model = baselines["models"]["speed_density_model"]
    return {
        "coefficients": dict(model["coefficients"]),
        "intercept": float(model["intercept"]),
        "winsorize_bounds": {
            name: dict(bounds)
            for name, bounds in model["winsorize_bounds"].items()
        },
    }


def masked_assign(
    df: pd.DataFrame,
    rows: pd.Index,
    column: str,
    values: pd.Series,
) -> None:
    """Assign recomputed ``values`` on ``rows``, keeping the
    delivered NaN mask: cells that were policy-NaN stay NaN."""
    original = df.loc[rows, column]
    df.loc[rows, column] = values.where(original.notna())


def recompute_slope(
    df: pd.DataFrame, source: str, target: str, rows: pd.Index
) -> None:
    """Recompute ``target`` = diff(source)/dt_seconds on ``rows``.

    The frame is a single segment, so a plain diff matches
    Group 1's per-segment slope convention; rows before the fault
    onset only depend on earlier (unchanged) samples and are left
    as delivered.
    """
    slope = df[source].diff() / df["dt_seconds"]
    masked_assign(df, rows, target, slope.loc[rows])


def recompute_maf_air_load(df: pd.DataFrame, rows: pd.Index) -> None:
    sub = df.loc[rows]
    masked_assign(df, rows, MAF_LOAD, 60.0 * sub["maf"] / sub["rpm"])


def recompute_map_air_load(df: pd.DataFrame, rows: pd.Index) -> None:
    sub = df.loc[rows]
    load = (
        sub["map"] * sub["rpm"] / (sub["intake_temp"] + KELVIN_OFFSET)
    )
    masked_assign(df, rows, MAP_LOAD, load)


def recompute_cohesion(
    df: pd.DataFrame,
    rows: pd.Index,
    cohesion_params: dict[str, dict[str, float]],
) -> None:
    z_maf = zscore(df.loc[rows, MAF_LOAD], cohesion_params[MAF_LOAD])
    z_map = zscore(df.loc[rows, MAP_LOAD], cohesion_params[MAP_LOAD])
    masked_assign(df, rows, "maf_map_cohesion", (z_maf - z_map).abs())


def recompute_speed_density_residual(
    df: pd.DataFrame,
    rows: pd.Index,
    sd_model: dict[str, object],
) -> None:
    """maf minus the speed-density model prediction, with the
    model's winsorize bounds applied to the inputs first (this is
    how Group 1 computes the delivered column — reconstruction
    error <= 5e-7)."""
    coefficients = sd_model["coefficients"]
    bounds = sd_model["winsorize_bounds"]
    predicted = pd.Series(
        float(sd_model["intercept"]), index=rows, dtype=float
    )
    for name in SPEED_DENSITY_INPUTS:
        clipped = df.loc[rows, name].clip(
            bounds[name]["lower"], bounds[name]["upper"]
        )
        predicted = predicted + coefficients[name] * clipped
    residual = df.loc[rows, "maf"] - predicted
    masked_assign(df, rows, "speed_density_maf_residual", residual)


def recompute_idle_rpm_stability(
    df: pd.DataFrame, rows: pd.Index
) -> None:
    """Rolling std of rpm restricted to idle rows (Group 1's
    delivered definition), reassigned on ``rows`` only — stability
    at a row depends on the trailing window, so rows before the
    fault onset are unaffected."""
    idle_rpm = df["rpm"].where(df["idle_flag"] == 1)
    stability = idle_rpm.rolling(
        IDLE_STABILITY_WINDOW_ROWS, min_periods=1
    ).std()
    masked_assign(df, rows, "idle_rpm_stability", stability.loc[rows])


def frozen_value_at(df: pd.DataFrame, signal: str, start_row: int):
    value = float(df[signal].iloc[start_row])
    if not np.isfinite(value):
        raise ValueError(
            f"cannot freeze {signal!r}: value at start_row "
            f"{start_row} is not finite"
        )
    return value


def inject_intake_air_temp_fault(
    df: pd.DataFrame,
    cohesion_params: dict[str, dict[str, float]],
    sd_model: dict[str, object],
    start_row: int = 0,
) -> pd.DataFrame:
    """Frozen-value IAT fault from ``start_row`` on (stuck sensor,
    proxy_support.md section 4 Stage 4 TBD-1, F1).

    `intake_temp` is held at its ``start_row`` value; NaN cells
    stay NaN. Propagated: `intake_ambient_delta`,
    `intake_temp_slope` (0 inside the frozen region),
    `map_derived_air_load_raw` (nonlinear in `intake_temp` —
    recomputed), `maf_map_cohesion`, `speed_density_maf_residual`.
    Returns a copy; the input frame is not modified.
    """
    injected = df.copy()
    rows = injected.index[start_row:]
    frozen = frozen_value_at(injected, "intake_temp", start_row)

    values = injected.loc[rows, "intake_temp"]
    injected.loc[rows, "intake_temp"] = values.where(
        values.isna(), frozen
    )
    masked_assign(
        injected,
        rows,
        "intake_ambient_delta",
        injected.loc[rows, "intake_temp"]
        - injected.loc[rows, "ambient_temp"],
    )
    recompute_slope(injected, "intake_temp", "intake_temp_slope", rows)
    recompute_map_air_load(injected, rows)
    recompute_cohesion(injected, rows, cohesion_params)
    recompute_speed_density_residual(injected, rows, sd_model)
    return injected


def inject_map_plausibility_fault(
    df: pd.DataFrame,
    cohesion_params: dict[str, dict[str, float]],
    sd_model: dict[str, object],
    start_row: int = 0,
) -> pd.DataFrame:
    """Frozen-value MAP fault from ``start_row`` on
    (proxy_support.md section 5 Stage 4 TBD-1: stuck signal F3,
    and any pedal-step response inside the window is suppressed,
    F1). Injection on `map` only — distinct from the `map x 1.25`
    cohesion-attribution scenario.

    `map` is held at its ``start_row`` value; NaN cells stay NaN.
    Propagated: `map_slope` (0 inside the frozen region),
    `map_derived_air_load_raw`, `maf_map_cohesion`,
    `speed_density_maf_residual`. Returns a copy; the input frame
    is not modified.
    """
    injected = df.copy()
    rows = injected.index[start_row:]
    frozen = frozen_value_at(injected, "map", start_row)

    values = injected.loc[rows, "map"]
    injected.loc[rows, "map"] = values.where(values.isna(), frozen)
    recompute_slope(injected, "map", "map_slope", rows)
    recompute_map_air_load(injected, rows)
    recompute_cohesion(injected, rows, cohesion_params)
    recompute_speed_density_residual(injected, rows, sd_model)
    return injected


def inject_idle_speed_fault(
    df: pd.DataFrame,
    cohesion_params: dict[str, dict[str, float]],
    sd_model: dict[str, object],
    start_row: int = 0,
    offset_rpm: float = IDLE_OFFSET_RPM,
    osc_amplitude_rpm: float = IDLE_OSC_AMPLITUDE_RPM,
    osc_period_s: float = IDLE_OSC_PERIOD_S,
) -> pd.DataFrame:
    """Idle-speed control fault from ``start_row`` on
    (proxy_support.md section 6 Stage 4 TBD-1: steady offset for
    S1 plus low-frequency oscillation for S2, on `rpm` only).

    The offset + sine is applied to rows with `idle_flag == 1`
    only: the vehicle is still genuinely idling, so `idle_flag`
    and `operating_state` stay as delivered. Propagated:
    `rpm_slope`, `idle_rpm_stability`,
    `maf_derived_air_load_raw` (nonlinear in `rpm` — recomputed),
    `map_derived_air_load_raw`, `maf_map_cohesion`,
    `speed_density_maf_residual`. Returns a copy; the input frame
    is not modified.
    """
    injected = df.copy()
    rows = injected.index[start_row:]
    idle = injected.loc[rows, "idle_flag"] == 1
    idle_rows = idle.index[idle]

    seconds = pd.Series(
        np.arange(len(rows), dtype=float), index=rows
    )
    wave = offset_rpm + osc_amplitude_rpm * np.sin(
        2.0 * np.pi * seconds / osc_period_s
    )
    injected.loc[idle_rows, "rpm"] += wave.loc[idle_rows]

    recompute_slope(injected, "rpm", "rpm_slope", rows)
    recompute_idle_rpm_stability(injected, rows)
    recompute_maf_air_load(injected, idle_rows)
    recompute_map_air_load(injected, idle_rows)
    recompute_cohesion(injected, idle_rows, cohesion_params)
    recompute_speed_density_residual(injected, idle_rows, sd_model)
    return injected
