from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.data_cleaning.src.cleaning_core import (  # noqa: E402
    UTC_TIMESTAMP_FORMAT,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

CLEANING_DIR = PROJECT_ROOT / "data_layer" / "data_cleaning" / "src"
CONFIG_PATH = CLEANING_DIR / "cleaning_config.yaml"

KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
CORE_MISSING_COLUMNS = ["coolant_temp", "maf", "rpm", "speed"]
SIGNAL_COLUMNS = [
    "coolant_temp",
    "map",
    "rpm",
    "speed",
    "intake_temp",
    "maf",
    "tps",
    "ambient_temp",
    "accel_pedal_d",
    "accel_pedal_e",
]

# Constants come from the objective standards.
ENGINE_OFF_RPM_MAX = 50.0
POST_WARMUP_ECT_MIN = 75.0
POST_WARMUP_CUMULATIVE_AIR_MIN_G = 1500.0
POST_WARMUP_IAT_AAT_DELTA_MIN = 8.0
HOT_IDLE_RPM_MAX = 850.0
IDLE_SPEED_MAX_KMH = 1.0
MOVING_SPEED_MIN_KMH = 1.0
ACCEL_ABS_DEADBAND_MS2 = 0.15
HIGH_LOAD_VSP_MIN_KW_PER_T = 20.0
HIGH_LOAD_ACCEL_MIN_MS2 = 1.2
SPEED_SMOOTHING_WINDOW_SECONDS = 3
MIN_STATE_DURATION_SECONDS = 3


def load_config(path: Path) -> dict[str, Any]:
    # Read the cleaning config for later statistics.
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def require_inputs(data_path: Path, config_path: Path) -> None:
    # Check that inputs exist before running the calculation.
    missing = [path for path in [data_path, config_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required input files: "
            f"{[str(path) for path in missing]}"
        )


def load_cleaned_data(
    fields: dict[str, Any], data_path: Path
) -> pd.DataFrame:
    # Read only the columns needed by the state machine and signal statistics.
    expected_signals = [
        signal for signal in fields if signal in SIGNAL_COLUMNS
    ]
    required_columns = [*KEY_COLUMNS, *expected_signals]
    df = pd.read_csv(data_path, usecols=lambda col: col in required_columns)

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            "Cleaned dataset is missing required columns: "
            f"{missing_columns}"
        )

    # Convert time to UTC; coerce invalid sensor values to NaN.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True, errors="coerce"
    )
    for signal in expected_signals:
        df[signal] = pd.to_numeric(df[signal], errors="coerce")

    # Preserve original order; calculate in in-segment time order.
    df["_original_row_order"] = np.arange(len(df), dtype=np.int64)
    df = df.sort_values(
        ["segment_id", "row_in_segment", "timestamp"]
    ).reset_index(drop=True)
    return df


def compute_dt_seconds(df: pd.DataFrame) -> pd.Series:
    # Calculate sampling intervals within each segment.
    dt = df.groupby("segment_id")["timestamp"].diff().dt.total_seconds()
    dt = dt.where(dt.gt(0) & dt.le(5), 1.0).fillna(1.0)
    return dt.astype(float)


def build_quality_flags(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    # Generate pipe-separated quality flags from missing core fields.
    missing_core = df[CORE_MISSING_COLUMNS].isna()
    flags = np.full(len(df), "OK", dtype=object)
    for column, flag in [
        ("coolant_temp", "MISSING_ECT"),
        ("maf", "MISSING_MAF"),
        ("rpm", "MISSING_RPM"),
        ("speed", "MISSING_SPEED"),
    ]:
        mask = missing_core[column].to_numpy()
        flags = np.where(
            mask & (flags == "OK"),
            flag,
            np.where(mask, flags + "|" + flag, flags),
        )

    fatal_missing = missing_core["speed"] | missing_core["rpm"]
    any_core_missing = missing_core.any(axis=1)

    confidence = pd.Series("high", index=df.index, dtype="string")
    confidence[any_core_missing & ~fatal_missing] = "medium"
    confidence[fatal_missing] = "low"
    return pd.Series(flags, index=df.index, dtype="string"), confidence


def ffill_within_segment(
        values: pd.Series, segment_id: pd.Series
) -> pd.Series:
    # Forward-fill only within each segment.
    return values.groupby(segment_id).ffill()


def cleanup_short_state_runs(
    states: pd.Series,
    segment_id: pd.Series,
    min_duration: int,
    protected_states: set[str] | None = None,
) -> pd.Series:
    # Remove short state fragments by merging them into neighboring states.
    protected_states = protected_states or set()
    cleaned_parts: list[pd.Series] = []

    for _, group in states.groupby(segment_id, sort=False):
        values = group.astype("string").to_numpy(dtype=object)
        if len(values) == 0:
            cleaned_parts.append(group)
            continue

        # Multiple passes remove new short fragment created by earlier merges.
        for _ in range(5):
            changed = False
            starts: list[int] = []
            ends: list[int] = []
            current_start = 0
            for pos in range(1, len(values)):
                if values[pos] != values[pos - 1]:
                    starts.append(current_start)
                    ends.append(pos)
                    current_start = pos
            starts.append(current_start)
            ends.append(len(values))

            for start, end in zip(starts, ends):
                run_length = end - start
                state = str(values[start])
                if run_length >= min_duration or state in protected_states:
                    continue

                prev_state = values[start - 1] if start > 0 else None
                next_state = values[end] if end < len(values) else None
                if prev_state in protected_states:
                    prev_state = None
                if next_state in protected_states:
                    next_state = None
                if (
                    prev_state is not None
                    and next_state is not None
                    and prev_state == next_state
                ):
                    replacement = prev_state
                elif prev_state is not None:
                    replacement = prev_state
                elif next_state is not None:
                    replacement = next_state
                else:
                    continue

                values[start:end] = replacement
                changed = True

            if not changed:
                break

        cleaned_parts.append(
            pd.Series(values, index=group.index, dtype="string")
        )

    return pd.concat(cleaned_parts).sort_index()


def add_operating_conditions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Generate quality flags and confidence before running the state machine.
    df["condition_quality_flags"], df["condition_confidence"] = (
        build_quality_flags(df)
    )
    df["dt_seconds"] = compute_dt_seconds(df)

    # Smooth speed before calculating acceleration and VSP.
    df["speed_smooth_kmh"] = df.groupby("segment_id")["speed"].transform(
        lambda series: series.rolling(
            window=SPEED_SMOOTHING_WINDOW_SECONDS,
            center=True,
            min_periods=1,
        ).mean()
    )
    speed_smooth_ms = df["speed_smooth_kmh"] / 3.6
    df["accel_ms2_smooth"] = (
        speed_smooth_ms.groupby(df["segment_id"]).diff() / df["dt_seconds"]
    ).fillna(0.0)

    # Calculate the high-load criterion with the VSP formula, in kW/t.
    df["vsp_kw_per_t"] = (
        speed_smooth_ms * (1.1 * df["accel_ms2_smooth"] + 0.132)
        + 0.000302 * (speed_smooth_ms**3)
    )

    # Reset cumulative intake air mass for each segment.
    engine_known_on = df["rpm"].ge(ENGINE_OFF_RPM_MAX)
    maf_contribution = df["maf"].clip(lower=0).fillna(0.0) * df["dt_seconds"]
    maf_contribution = maf_contribution.where(
        engine_known_on.fillna(False), 0.0
    )
    df["cumulative_air_mass_g"] = maf_contribution.groupby(
        df["segment_id"]
    ).cumsum()

    # First build the main thermal state: Engine_Off / Warmup / Post-warmup.
    engine_off = df["rpm"].lt(ENGINE_OFF_RPM_MAX)
    engine_on = df["rpm"].ge(ENGINE_OFF_RPM_MAX)
    speed_for_state = df["speed_smooth_kmh"]
    iat_aat_delta = df["intake_temp"] - df["ambient_temp"]

    post_warmup_base = engine_on & df["coolant_temp"].ge(POST_WARMUP_ECT_MIN)
    post_warmup_idle_confirm = (
        speed_for_state.lt(IDLE_SPEED_MAX_KMH)
        & df["rpm"].lt(HOT_IDLE_RPM_MAX)
    )
    post_warmup_moving_confirm = speed_for_state.ge(MOVING_SPEED_MIN_KMH) & df[
        "cumulative_air_mass_g"
    ].gt(POST_WARMUP_CUMULATIVE_AIR_MIN_G)
    post_warmup_heat_soak_confirm = iat_aat_delta.gt(
        POST_WARMUP_IAT_AAT_DELTA_MIN
    )

    post_warmup_trigger = post_warmup_base & (
        post_warmup_idle_confirm
        | post_warmup_moving_confirm
        | post_warmup_heat_soak_confirm
    )

    # Infer post-warmup with fallback signals when ECT is missing.
    degraded_post_warmup_trigger = (
        engine_on
        & df["coolant_temp"].isna()
        & (post_warmup_moving_confirm | post_warmup_heat_soak_confirm)
    )
    post_warmup_seen = (
        post_warmup_trigger | degraded_post_warmup_trigger
    ).groupby(df["segment_id"]).cummax()

    thermal_state = pd.Series("unknown", index=df.index, dtype="string")
    thermal_state[engine_off.fillna(False)] = "engine_off"
    thermal_state[engine_on.fillna(False) & ~post_warmup_seen] = "warmup"
    thermal_state[engine_on.fillna(False) & post_warmup_seen] = "post_warmup"

    # Missing RPM inherits the previous thermal state within the segment.
    rpm_missing = df["rpm"].isna()
    thermal_state[rpm_missing] = pd.NA
    thermal_state = ffill_within_segment(
        thermal_state, df["segment_id"]
    ).fillna("unknown")
    df["thermal_state"] = thermal_state

    # Child-state priority: Idle > High_Load > Acc > Dec > Steady.
    active = ~df["thermal_state"].isin(["engine_off", "unknown"])
    idle = (
        active
        & speed_for_state.lt(IDLE_SPEED_MAX_KMH)
        & df["accel_ms2_smooth"].abs().lt(ACCEL_ABS_DEADBAND_MS2)
    )
    high_load = (
        active
        & speed_for_state.ge(MOVING_SPEED_MIN_KMH)
        & (
            df["vsp_kw_per_t"].ge(HIGH_LOAD_VSP_MIN_KW_PER_T)
            | df["accel_ms2_smooth"].ge(HIGH_LOAD_ACCEL_MIN_MS2)
        )
    )
    acceleration = (
        active
        & speed_for_state.ge(MOVING_SPEED_MIN_KMH)
        & df["accel_ms2_smooth"].ge(ACCEL_ABS_DEADBAND_MS2)
        & ~high_load
    )
    deceleration = (
        active
        & speed_for_state.ge(MOVING_SPEED_MIN_KMH)
        & df["accel_ms2_smooth"].le(-ACCEL_ABS_DEADBAND_MS2)
        & ~high_load
        & ~acceleration
    )
    steady_driving = active & ~(idle | high_load | acceleration | deceleration)

    child_state = pd.Series("unknown", index=df.index, dtype="string")
    child_state[df["thermal_state"].eq("engine_off")] = "inactive_engine_off"
    child_state[idle] = "idle"
    child_state[high_load] = "high_load"
    child_state[acceleration] = "acceleration"
    child_state[deceleration] = "deceleration"
    child_state[steady_driving] = "steady_driving"

    # Forward-fill child state within the segment when speed or RPM is missing.
    fatal_missing = df["speed"].isna() | df["rpm"].isna()
    child_state[fatal_missing] = pd.NA
    child_state = ffill_within_segment(
        child_state, df["segment_id"]
    ).fillna("unknown")

    # Remove isolated state transitions without merging across segments.
    child_state = cleanup_short_state_runs(
        child_state,
        df["segment_id"],
        min_duration=MIN_STATE_DURATION_SECONDS,
        protected_states={"inactive_engine_off", "unknown"},
    )
    invalid_running_inactive = (
        ~df["thermal_state"].eq("engine_off")
        & child_state.eq("inactive_engine_off")
    )
    child_state[invalid_running_inactive] = "unknown"
    df["child_state"] = child_state

    # Combine the main state and child state for later window aggregation.
    operating_state = pd.Series("unknown", index=df.index, dtype="string")
    operating_state[df["thermal_state"].eq("engine_off")] = "engine_off"
    known_running = ~df["thermal_state"].isin(["engine_off", "unknown"]) & ~df[
        "child_state"
    ].eq("unknown")
    operating_state[known_running] = (
        df.loc[known_running, "thermal_state"]
        + "__"
        + df.loc[known_running, "child_state"]
    )
    df["operating_state"] = operating_state

    return df


def build_counts(df: pd.DataFrame) -> pd.DataFrame:
    # Generate distributions and split multi-label quality flags.
    rows: list[dict[str, Any]] = []
    total_duration = float(df["dt_seconds"].sum())
    total_rows = int(len(df))

    for state_type, column in [
        ("thermal_state", "thermal_state"),
        ("child_state", "child_state"),
        ("operating_state", "operating_state"),
        ("condition_confidence", "condition_confidence"),
    ]:
        grouped = df.groupby(column, dropna=False)["dt_seconds"].agg(
            ["count", "sum"]
        )
        for state, values in grouped.iterrows():
            rows.append(
                {
                    "state_type": state_type,
                    "state": state,
                    "row_count": int(values["count"]),
                    "duration_seconds": float(values["sum"]),
                    "row_rate": (
                        int(values["count"]) / total_rows
                        if total_rows
                        else np.nan
                    ),
                    "duration_rate": float(values["sum"]) / total_duration
                    if total_duration
                    else np.nan,
                }
            )

    flags_df = df[["condition_quality_flags", "dt_seconds"]].copy()
    flags_df["flag"] = (
        flags_df["condition_quality_flags"].astype("string").str.split("|")
    )
    flags_df = flags_df.explode("flag")
    flag_grouped = flags_df.groupby("flag", dropna=False)["dt_seconds"].agg(
        ["count", "sum"]
    )
    for flag, values in flag_grouped.iterrows():
        rows.append(
            {
                "state_type": "condition_quality_flags",
                "state": flag,
                "row_count": int(values["count"]),
                "duration_seconds": float(values["sum"]),
                "row_rate": (
                    int(values["count"]) / total_rows
                    if total_rows
                    else np.nan
                ),
                "duration_rate": float(values["sum"]) / total_duration
                if total_duration
                else np.nan,
            }
        )

    return pd.DataFrame(rows)


def summarize_signal_group(
    df: pd.DataFrame,
    group_type: str,
    group_value: str,
    signal: str,
    unit: str | None,
) -> dict[str, Any]:
    # Calculate descriptive statistics for one signal in one condition subset.
    series = pd.to_numeric(df[signal], errors="coerce")
    row_count = int(len(series))
    non_null_count = int(series.notna().sum())
    missing_count = row_count - non_null_count
    missing_rate = missing_count / row_count if row_count else np.nan
    valid = series.dropna()
    quantiles = (
        valid.quantile([0.01, 0.05, 0.50, 0.95, 0.99])
        if not valid.empty
        else pd.Series(dtype=float)
    )

    return {
        "group_type": group_type,
        "group_value": group_value,
        "signal": signal,
        "unit": unit,
        "row_count": row_count,
        "non_null_count": non_null_count,
        "missing_count": missing_count,
        "missing_rate": missing_rate,
        "mean": float(valid.mean()) if not valid.empty else np.nan,
        "std": float(valid.std()) if not valid.empty else np.nan,
        "min": float(valid.min()) if not valid.empty else np.nan,
        "p1": float(quantiles.get(0.01, np.nan)),
        "p5": float(quantiles.get(0.05, np.nan)),
        "p50": float(quantiles.get(0.50, np.nan)),
        "p95": float(quantiles.get(0.95, np.nan)),
        "p99": float(quantiles.get(0.99, np.nan)),
        "max": float(valid.max()) if not valid.empty else np.nan,
    }


def build_signal_summary(
    df: pd.DataFrame, fields: dict[str, Any]
) -> pd.DataFrame:
    # Summarize signals by state and confidence.
    rows: list[dict[str, Any]] = []
    group_columns = [
        ("thermal_state", "thermal_state"),
        ("child_state", "child_state"),
        ("operating_state", "operating_state"),
        ("condition_confidence", "condition_confidence"),
    ]

    for group_type, column in group_columns:
        for group_value, subset in df.groupby(column, dropna=False, sort=True):
            for signal in SIGNAL_COLUMNS:
                if signal not in df.columns:
                    continue
                rows.append(
                    summarize_signal_group(
                        subset,
                        group_type=group_type,
                        group_value=str(group_value),
                        signal=signal,
                        unit=fields.get(signal, {}).get("unit"),
                    )
                )

    return pd.DataFrame(rows)


def build_rules() -> pd.DataFrame:
    # Write objective standards to an auditable rules table.
    rows = [
        {
            "rule_name": "engine_off_rpm_max",
            "value": ENGINE_OFF_RPM_MAX,
            "unit": "rpm",
            "description": (
                "Classify the engine as Engine_Off when engine speed is "
                "below this threshold."
            ),
        },
        {
            "rule_name": "post_warmup_ect_min",
            "value": POST_WARMUP_ECT_MIN,
            "unit": "degC",
            "description": (
                "Minimum coolant temperature baseline for Post-warmup "
                "classification."
            ),
        },
        {
            "rule_name": "post_warmup_cumulative_air_min",
            "value": POST_WARMUP_CUMULATIVE_AIR_MIN_G,
            "unit": "g",
            "description": (
                "Cumulative intake air mass proxy used to infer catalyst "
                "warm-up when catalyst temperature is unavailable."
            ),
        },
        {
            "rule_name": "post_warmup_iat_aat_delta_min",
            "value": POST_WARMUP_IAT_AAT_DELTA_MIN,
            "unit": "degC",
            "description": (
                "Minimum intake-air-to-ambient temperature delta used as an "
                "auxiliary heat-soak indicator."
            ),
        },
        {
            "rule_name": "hot_idle_rpm_max",
            "value": HOT_IDLE_RPM_MAX,
            "unit": "rpm",
            "description": (
                "Maximum hot-idle RPM used to support Post-warmup "
                "confirmation during idle."
            ),
        },
        {
            "rule_name": "idle_speed_max",
            "value": IDLE_SPEED_MAX_KMH,
            "unit": "km/h",
            "description": (
                "Maximum smoothed vehicle speed for Idle classification."
            ),
        },
        {
            "rule_name": "moving_speed_min",
            "value": MOVING_SPEED_MIN_KMH,
            "unit": "km/h",
            "description": (
                "Minimum smoothed vehicle speed for moving child-state "
                "classification."
            ),
        },
        {
            "rule_name": "accel_abs_deadband",
            "value": ACCEL_ABS_DEADBAND_MS2,
            "unit": "m/s2",
            "description": (
                "Acceleration deadband used to separate steady driving from "
                "acceleration and deceleration."
            ),
        },
        {
            "rule_name": "high_load_vsp_min",
            "value": HIGH_LOAD_VSP_MIN_KW_PER_T,
            "unit": "kW/t",
            "description": (
                "Vehicle Specific Power threshold for High_Load "
                "classification."
            ),
        },
        {
            "rule_name": "high_load_accel_min",
            "value": HIGH_LOAD_ACCEL_MIN_MS2,
            "unit": "m/s2",
            "description": (
                "Acceleration threshold that directly classifies a moving "
                "sample as High_Load."
            ),
        },
        {
            "rule_name": "speed_smoothing_window",
            "value": SPEED_SMOOTHING_WINDOW_SECONDS,
            "unit": "s",
            "description": (
                "Centered moving-average window applied to vehicle speed "
                "before acceleration calculation."
            ),
        },
        {
            "rule_name": "min_state_duration",
            "value": MIN_STATE_DURATION_SECONDS,
            "unit": "s",
            "description": (
                "Minimum child-state duration used to remove isolated short "
                "state fragments."
            ),
        },
        {
            "rule_name": "vsp_formula",
            "value": "v*(1.1*a+0.132)+0.000302*v^3",
            "unit": "kW/t",
            "description": (
                "Vehicle Specific Power formula; v is in m/s and a is in "
                "m/s2."
            ),
        },
    ]
    return pd.DataFrame(rows)


def write_outputs(
    df: pd.DataFrame,
    fields: dict[str, Any],
    run_layout: RunLayout,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Output audit, distribution, signal-statistics, and rules tables.
    run_layout.operating_conditions_dir.mkdir(parents=True, exist_ok=True)
    output_df = df.sort_values("_original_row_order").copy()
    enriched_columns = [
        *KEY_COLUMNS,
        *[signal for signal in SIGNAL_COLUMNS if signal in output_df.columns],
        "dt_seconds",
        "speed_smooth_kmh",
        "accel_ms2_smooth",
        "vsp_kw_per_t",
        "cumulative_air_mass_g",
        "thermal_state",
        "child_state",
        "operating_state",
        "condition_quality_flags",
        "condition_confidence",
    ]
    enriched_df = output_df[enriched_columns].copy()
    enriched_df["timestamp"] = enriched_df["timestamp"].dt.strftime(
        UTC_TIMESTAMP_FORMAT
    )
    enriched_df.to_csv(
        run_layout.operating_condition_enriched,
        index=False,
        encoding="utf-8",
    )

    counts_df = build_counts(output_df)
    counts_df.to_csv(
        run_layout.operating_condition_counts,
        index=False,
        encoding="utf-8",
    )

    signal_summary_df = build_signal_summary(output_df, fields)
    signal_summary_df.to_csv(
        run_layout.operating_condition_signal_summary,
        index=False,
        encoding="utf-8",
    )

    rules_df = build_rules()
    rules_df.to_csv(
        run_layout.operating_condition_rules,
        index=False,
        encoding="utf-8",
    )
    return enriched_df, counts_df, signal_summary_df, rules_df


def run_operating_condition_analysis(
    run_layout: RunLayout,
    *,
    config_path: Path = CONFIG_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Generate all operating-condition outputs inside one explicit run."""

    data_path = run_layout.cleaned_dataset
    require_inputs(data_path, config_path)
    config = load_config(config_path)
    fields = config["fields"]

    df = load_cleaned_data(fields, data_path)
    df = add_operating_conditions(df)
    enriched, counts_df, signal_summary_df, rules_df = write_outputs(
        df, fields, run_layout
    )

    summary = {
        "dataset": run_layout.run_relative_posix(data_path),
        "rows": int(len(enriched)),
        "enriched_csv": run_layout.run_relative_posix(
            run_layout.operating_condition_enriched
        ),
        "counts_csv": run_layout.run_relative_posix(
            run_layout.operating_condition_counts
        ),
        "signal_summary_csv": run_layout.run_relative_posix(
            run_layout.operating_condition_signal_summary
        ),
        "rules_csv": run_layout.run_relative_posix(
            run_layout.operating_condition_rules
        ),
        "counts_rows": int(len(counts_df)),
        "signal_summary_rows": int(len(signal_summary_df)),
        "rules_rows": int(len(rules_df)),
    }
    return enriched, summary


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate operating-condition outputs for one Data Layer run."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Explicit run directory under data/processed/runs/<run_id>.",
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="Path to the cleaning/field configuration file.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        run_layout = RunLayout.from_run_dir(
            args.run_dir,
            repo_root=PROJECT_ROOT,
        )
        _, summary = run_operating_condition_analysis(
            run_layout,
            config_path=Path(args.config).expanduser().resolve(),
        )
    except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
