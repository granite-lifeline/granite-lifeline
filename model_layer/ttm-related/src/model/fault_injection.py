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
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Story 7 scenario constants (user_stories.md acceptance criteria,
# corroborated by proxy_support.md Stage 4 — see module docstring).
COOLING_OFFSET_C = 15.0
MAF_GAIN = 0.7
MAP_GAIN = 1.25

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
