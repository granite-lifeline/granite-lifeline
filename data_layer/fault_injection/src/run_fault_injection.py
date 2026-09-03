"""Run fault injection for proxy validation.

This script creates copied run directories under data/processed/runs,
injects one synthetic fault case at a time into production_features.csv,
updates the copied production manifest checksum, reruns proxy stages
50/60/61/70, and writes a small summary under data_layer/fault_injection.

It intentionally does not edit frozen rules or existing project files.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
FAULT_INJECTION_DIR = HERE.parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

from data_layer.pipeline_data.manifests import (  # noqa: E402
    sha256_file,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

DEFAULT_CONFIG = FAULT_INJECTION_DIR / "configs/fault_injection_cases.v1.json"
DEFAULT_OUTPUT_DIR = FAULT_INJECTION_DIR / "outputs"
PROXY_STAGE_FILES = (
    (
        "50",
        "50_rule_state_builder.py",
        "run_rule_state_builder",
    ),
    (
        "60",
        "60_event_evidence_builder.py",
        "run_event_evidence_builder",
    ),
    (
        "61",
        "61_duration_evidence_builder.py",
        "run_duration_evidence_builder",
    ),
    (
        "70",
        "70_proxy_decision_builder.py",
        "run_proxy_decision_builder",
    ),
)


class FaultInjectionError(RuntimeError):
    """Raised when the Stage 4 workflow cannot complete."""


@dataclass(frozen=True)
class Window:
    """Selected injection location in the production feature table."""

    indices: list[int]
    trip_id: str
    segment_id: str
    start_timestamp: str
    end_timestamp: str


REQUIRED_CASE_FIELDS = {
    "case_id", "proxy_id", "expected_sub_check_id", "target_signal",
    "selector", "strategy",
}
FIXED_STRATEGY_TARGETS = {
    "force_pedal_delta": "accel_pedal_e",
    "suppress_map_step_response": "map",
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def json_default(value: Any) -> Any:
    """Convert pandas/numpy scalars without weakening JSON validity."""

    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if pd.isna(value):
        return None
    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def parse_bool(value: Any, *, field: str, null_value: bool = False) -> bool:
    """Parse a persisted boolean without treating non-empty text as true."""

    if pd.isna(value):
        return null_value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(
        value, (int, float, np.integer, np.floating)
    ) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
    raise FaultInjectionError(
        f"Invalid boolean value for {field}: {value!r}"
    )


def load_calibration_registry() -> dict[str, Any]:
    """Load the same frozen registry consumed by the proxy stages."""

    path = REPO_ROOT / "data_layer/calibration/calibration_registry.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases(config_path: Path) -> list[dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cases = config.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise FaultInjectionError(f"No cases found in {config_path}.")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for raw_case in cases:
        case = dict(raw_case)
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            raise FaultInjectionError(
                f"Case is missing required fields {sorted(missing)}: {case}"
            )
        if case["case_id"] in seen:
            raise FaultInjectionError(f"Duplicate case_id: {case['case_id']}")
        seen.add(case["case_id"])
        if case.get("freeze_for_guard"):
            raise FaultInjectionError(
                f"{case['case_id']} modifies non-target guard signals; "
                "Stage 4 requires target-signal-only injection."
            )
        fixed_target = FIXED_STRATEGY_TARGETS.get(case["strategy"])
        if fixed_target and case["target_signal"] != fixed_target:
            raise FaultInjectionError(
                f"{case['case_id']} strategy {case['strategy']} modifies "
                f"{fixed_target}, not declared target {case['target_signal']}."
            )
        validated.append(case)
    return validated


def load_stage_module(filename: str) -> ModuleType:
    path = REPO_ROOT / "data_layer/proxy_failure/src" / filename
    name = f"fault_injection_{filename.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FaultInjectionError(f"Cannot load proxy stage: {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def copy_minimal_run(base: RunLayout, target: RunLayout) -> None:
    """Copy only the files needed by proxy stages 50/60/61/70."""

    if target.run_dir.exists():
        raise FaultInjectionError(
            f"Target run already exists: {target.run_dir}"
        )

    copies = [
        (base.cleaning_quality, target.cleaning_quality),
        (base.engine_start_episodes, target.engine_start_episodes),
        (
            base.engine_start_context_manifest,
            target.engine_start_context_manifest,
        ),
        (base.production_features, target.production_features),
        (
            base.production_feature_manifest,
            target.production_feature_manifest,
        ),
    ]
    for source, destination in copies:
        if not source.is_file():
            raise FaultInjectionError(f"Missing base-run file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def update_production_manifest(
        layout: RunLayout, case: dict[str, Any]) -> None:
    manifest = json.loads(
        layout.production_feature_manifest.read_text(encoding="utf-8")
    )
    artifact_path = "features/41_production/production_features.csv"
    digest = sha256_file(layout.production_features)
    size = layout.production_features.stat().st_size
    manifest["artifact_sha256"][artifact_path] = digest
    for item in manifest["ordered_output_artifacts"]:
        if item["path"] == artifact_path:
            item["sha256"] = digest
            item["size_bytes"] = size
    manifest.setdefault("stage4_fault_injection", {})
    manifest["stage4_fault_injection"] = {
        "case_id": case["case_id"],
        "expected_sub_check_id": case["expected_sub_check_id"],
        "target_signal": case["target_signal"],
        "note": "Synthetic Stage 4 validation run; not a healthy dataset.",
    }
    write_json_atomic(layout.production_feature_manifest, manifest)


def consecutive_window(mask: pd.Series, duration: int) -> list[int] | None:
    """Return the first same-trip/segment consecutive true window."""

    if duration <= 0:
        raise FaultInjectionError("duration_seconds must be positive.")
    positions = mask[mask].index.tolist()
    if not positions:
        return None
    position_set = set(positions)
    for start in positions:
        window = list(range(start, start + duration))
        if all(item in position_set for item in window):
            return window
    return None


def select_basic_windows(
    frame: pd.DataFrame,
    case: dict[str, Any],
    registry: dict[str, Any],
) -> list[Window]:
    selector = case["selector"]
    duration = int(case.get("duration_seconds", 1))
    base = pd.Series(True, index=frame.index)

    rules = registry["proxy_rules"]
    engine_on_rpm = float(
        registry["shared_constants"]["engine_on_rpm"]["value"]
    )

    if selector == "post_warmup":
        mask = base & frame["thermal_state"].eq("post_warmup")
        if case["expected_sub_check_id"] == "1-S2":
            ambient_max = rules["1-S2"]["guards"][
                "ambient_at_window_start_max_c"
            ]["value"]
            mask &= frame["ambient_temp"].le(float(ambient_max))
    elif selector == "post_warmup_high_load":
        mask = base & frame["operating_state"].eq("post_warmup__high_load")
    elif selector == "steady_driving":
        guards = rules["5-S2"]["guards"]
        mask = (
            base
            & frame["operating_state"].eq("post_warmup__steady_driving")
            & frame["pedal_slope"].eq(
                float(guards["pedal_slope_abs"]["value"])
            )
            & frame["rpm_slope"].abs().le(
                float(guards["rpm_slope_abs"]["value"])
            )
        )
    elif selector == "engine_firing":
        firing_rpm = rules["2-S3b"]["rpm"]["value"]
        mask = base & frame["rpm"].ge(float(firing_rpm))
    elif selector == "pedal_lowmotion":
        slope_max = rules["3-S1a"]["guards"]["pedal_slope_abs"]["value"]
        mask = (
            base
            & frame["rpm"].ge(engine_on_rpm)
            & frame["pedal_slope"].abs().le(float(slope_max))
            & frame["pedal_mapping_residual"].notna()
        )
    elif selector == "iat_context_change":
        thresholds = rules["4-S1"]["context_thresholds"]
        mask = (
            base
            & frame["rpm"].ge(engine_on_rpm)
            & (
                frame["speed_std_120s"].ge(
                    float(thresholds["speed_std_120s"]["raw_value"])
                )
                | frame["maf_std_120s"].ge(
                    float(thresholds["maf_std_120s"]["raw_value"])
                )
            )
            & frame["intake_temp_stability"].notna()
        )
    elif selector == "map_context_change":
        thresholds = rules["5-S3"]["context_thresholds"]
        mask = (
            base
            & frame["rpm"].ge(engine_on_rpm)
            & (
                frame["rpm_std_120s"].ge(
                    float(thresholds["rpm_std_120s"]["raw_value"])
                )
                | frame["speed_std_120s"].ge(
                    float(thresholds["speed_std_120s"]["raw_value"])
                )
                | frame["accel_pedal_mean_std_120s"].ge(
                    float(thresholds[
                        "accel_pedal_mean_std_120s"
                    ]["raw_value"])
                )
            )
            & frame["map_range_60s"].notna()
        )
    elif selector in {"cold_start_ect", "cold_start_iat"}:
        rule_id = "1-S4" if selector == "cold_start_ect" else "4-S2"
        guards = rules[rule_id]["guards"]
        first = frame["row_in_segment"].eq(1)
        later_start = frame.groupby(
            ["trip_id", "segment_id"], sort=False
        )["engine_start_observed"].transform(
            lambda values: values.map(
                lambda value: parse_bool(
                    value, field="engine_start_observed"
                )
            ).any()
        )
        mask = (
            base
            & first
            & frame["segment_gap_seconds"].ge(
                float(guards["segment_gap_seconds"]["value"])
            )
            & frame["rpm"].lt(
                float(guards["first_row_rpm"]["value"])
            )
            & later_start
            & frame[["coolant_temp", "intake_temp", "ambient_temp"]]
            .notna().all(axis=1)
        )
        if selector == "cold_start_ect":
            mask &= (
                frame["intake_temp"] - frame["ambient_temp"]
            ).abs().le(float(guards["iat_witness_abs_delta_c"]["value"]))
        else:
            mask &= (
                frame["coolant_temp"] - frame["ambient_temp"]
            ).abs().le(float(guards["ect_witness_abs_delta_c"]["value"]))
    else:
        raise FaultInjectionError(f"Unsupported selector: {selector}")

    # Keep windows inside one trip and one segment.
    windows: list[Window] = []
    used_trips: set[str] = set()
    for (_trip, _segment), group in frame[mask].groupby(
        ["trip_id", "segment_id"], sort=False
    ):
        if str(_trip) in used_trips:
            continue
        local_mask = pd.Series(False, index=frame.index)
        local_mask.loc[group.index] = True
        indices = consecutive_window(local_mask, duration)
        if indices:
            rows = frame.loc[indices]
            windows.append(Window(
                indices=indices,
                trip_id=str(rows["trip_id"].iloc[0]),
                segment_id=str(rows["segment_id"].iloc[0]),
                start_timestamp=str(rows["timestamp"].iloc[0]),
                end_timestamp=str(rows["timestamp"].iloc[-1]),
            ))
            used_trips.add(str(_trip))
    if windows:
        return windows
    raise FaultInjectionError(
        f"No injection window found for case {case['case_id']} "
        f"with selector {selector}."
    )


def select_warmup_windows(
    frame: pd.DataFrame,
    case: dict[str, Any],
    registry: dict[str, Any],
) -> list[Window]:
    """Return independent, injection-capable observed warm-up episodes."""

    minimum_followup = int(case.get("minimum_followup_seconds", 900))
    guards = registry["proxy_rules"]["1-S1"]["start_guards"]
    ect_start_max = float(guards["ect_start_max_c"]["value"])
    aat_start_min = float(guards["aat_start_min_c"]["value"])
    candidates = frame[
        frame["engine_start_episode_id"].notna()
        & frame["elapsed_since_engine_start"].notna()
    ]
    windows: list[Window] = []
    used_trips: set[str] = set()
    for episode_id, group in candidates.groupby(
        "engine_start_episode_id", sort=False
    ):
        group = group.sort_values("elapsed_since_engine_start")
        first = group.iloc[0]
        trip_id = str(first["trip_id"])
        if trip_id in used_trips:
            continue
        if not parse_bool(
            first.get("engine_start_observed", False),
            field="engine_start_observed",
        ):
            continue
        if (
            pd.isna(first["ect_start"])
            or float(first["ect_start"]) > ect_start_max
            or pd.isna(first["aat_start"])
            or float(first["aat_start"]) < aat_start_min
        ):
            continue
        eligible = group[
            group["elapsed_since_engine_start"].le(minimum_followup)
        ]
        if (
            group["elapsed_since_engine_start"].max() < minimum_followup
            or len(eligible) < minimum_followup
        ):
            continue
        rows = eligible
        windows.append(Window(
            indices=rows.index.tolist(),
            trip_id=trip_id,
            segment_id=str(first["segment_id"]),
            start_timestamp=str(rows["timestamp"].iloc[0]),
            end_timestamp=str(rows["timestamp"].iloc[-1]),
        ))
        used_trips.add(trip_id)
    if not windows:
        raise FaultInjectionError(
            f"No qualified warm-up episode found for {case['case_id']}."
        )
    return windows


def select_pedal_step_windows(
    frame: pd.DataFrame,
    case: dict[str, Any],
    registry: dict[str, Any],
) -> list[Window]:
    """Select events likely to be consumed by 5-S1."""

    needed = int(case.get("event_count", 4))
    state_parameters = registry["proxy_rules"]["5-S1"][
        "state_parameters"
    ]
    thresholds = {
        state: float(parameters["pedal_step_threshold"]["value"])
        for state, parameters in state_parameters.items()
    }
    step_threshold = frame["operating_state"].map(thresholds)
    mask = (
        frame["thermal_state"].eq("post_warmup")
        & frame["condition_confidence"].eq("high")
        & frame["pedal_slope"].ge(step_threshold)
        & frame["map"].notna()
    )
    # The low-magnitude steady-driving bin is explicitly non-separable.
    steady_low = (
        frame["operating_state"].eq("post_warmup__steady_driving")
        & frame["pedal_slope"].lt(float(
            state_parameters["post_warmup__steady_driving"]
            ["magnitude_split"]["value"]
        ))
    )
    mask &= ~steady_low
    windows: list[Window] = []
    for (_trip, _segment), group in frame[mask].groupby(
        ["trip_id", "segment_id"], sort=False
    ):
        event_indices = group.index.tolist()[:needed]
        if len(event_indices) < needed:
            continue
        touched: set[int] = set()
        for index in event_indices:
            touched.update([index - 1, index, index + 1, index + 2])
        touched = {
            item for item in touched
            if item in frame.index
            and frame.at[item, "trip_id"] == _trip
            and frame.at[item, "segment_id"] == _segment
        }
        rows = frame.loc[sorted(touched)]
        windows.append(Window(
            indices=event_indices,
            trip_id=str(_trip),
            segment_id=str(_segment),
            start_timestamp=str(rows["timestamp"].iloc[0]),
            end_timestamp=str(rows["timestamp"].iloc[-1]),
        ))
    if windows:
        return windows
    raise FaultInjectionError(
        f"No pedal-step window found for {case['case_id']}.")


def select_windows(
    frame: pd.DataFrame,
    case: dict[str, Any],
    count: int,
    registry: dict[str, Any],
) -> list[Window]:
    if case["selector"] == "pedal_step_events":
        windows = select_pedal_step_windows(frame, case, registry)
    elif case["selector"] == "warmup_episode":
        windows = select_warmup_windows(frame, case, registry)
    else:
        windows = select_basic_windows(frame, case, registry)
    if len(windows) < count:
        raise FaultInjectionError(
            f"{case['case_id']} severity {case.get('_severity_id')} needs "
            f"{count} independent trip windows, but only {len(windows)} "
            "are available."
        )
    return windows[:count]


def inject_case(frame: pd.DataFrame,
                case: dict[str, Any], window: Window) -> None:
    signal = case["target_signal"]
    strategy = case["strategy"]
    indices = window.indices

    if signal not in frame.columns:
        raise FaultInjectionError(f"Missing target signal column: {signal}")

    if strategy == "set_constant":
        frame.loc[indices, signal] = float(case["value"])
    elif strategy == "add_offset":
        frame.loc[indices, signal] = (
            frame.loc[indices, signal].astype(float) + float(case["offset"])
        )
    elif strategy == "multiply":
        frame.loc[indices, signal] = (
            frame.loc[indices, signal].astype(float) * float(case["factor"])
        )
    elif strategy == "freeze_to_first":
        frame.loc[indices, signal] = frame.loc[indices, signal].iloc[0]
    elif strategy == "linear_ramp":
        start = float(case["start_value"])
        rate_per_second = float(case["rate_per_min"]) / 60.0
        values = [start + i * rate_per_second for i in range(len(indices))]
        frame.loc[indices, signal] = values
    elif strategy == "cap_max":
        frame.loc[indices, signal] = frame.loc[indices, signal].clip(
            upper=float(case["value"])
        )
    elif strategy == "relative_offset":
        reference = case["reference_signal"]
        if reference not in frame.columns:
            raise FaultInjectionError(
                f"Missing reference signal column: {reference}"
            )
        frame.loc[indices, signal] = (
            frame.loc[indices, reference].astype(float)
            + float(case["offset"])
        )
    elif strategy == "force_pedal_delta":
        delta = float(case["delta"])
        frame.loc[indices, "accel_pedal_e"] = (
            frame.loc[indices, "accel_pedal_d"].astype(float) + delta
        )
    elif strategy == "suppress_map_step_response":
        for index in indices:
            baseline_index = index - 1
            if baseline_index not in frame.index:
                continue
            baseline_map = frame.at[baseline_index, "map"]
            for offset in (0, 1, 2):
                target_index = index + offset
                if target_index in frame.index:
                    frame.at[target_index, "map"] = baseline_map
    else:
        raise FaultInjectionError(
            f"Unsupported injection strategy: {strategy}")


def recompute_dependent_features(
    frame: pd.DataFrame, registry: dict[str, Any]
) -> None:
    """Refresh feature columns consumed by proxy stages after injection."""

    speed_density = registry["feature_transforms"]["speed_density_maf"]
    pedal_mapping = registry["feature_transforms"]["pedal_mapping"]

    frame["coolant_ambient_delta"] = (
        frame["coolant_temp"] - frame["ambient_temp"]
    )
    frame["intake_ambient_delta"] = (
        frame["intake_temp"] - frame["ambient_temp"]
    )
    frame["accel_pedal_mean"] = (
        frame["accel_pedal_d"] + frame["accel_pedal_e"]
    ) / 2.0
    frame["accel_pedal_channel_delta"] = (
        frame["accel_pedal_d"] - frame["accel_pedal_e"]
    ).abs()
    frame["pedal_mapping_residual"] = (
        frame["accel_pedal_e"]
        - (
            float(pedal_mapping["a"]) * frame["accel_pedal_d"]
            + float(pedal_mapping["b"])
        )
    )

    absolute_temperature = frame["intake_temp"] + 273.15
    invalid_temperature = frame["intake_temp"].notna() & (
        ~np.isfinite(frame["intake_temp"])
        | ~np.isfinite(absolute_temperature)
        | absolute_temperature.le(0)
    )
    if invalid_temperature.any():
        indices = frame.index[invalid_temperature].tolist()[:5]
        raise FaultInjectionError(
            "intake_temp must be finite and above absolute zero before "
            f"speed-density recomputation; invalid rows: {indices}"
        )
    hidden = frame["rpm"] * frame["map"] / absolute_temperature
    bounds = speed_density["prediction_clipping_bounds"]
    model_inputs = {
        "map_derived_air_load_raw": hidden.clip(
            bounds["map_derived_air_load_raw"]["lower"],
            bounds["map_derived_air_load_raw"]["upper"],
        ),
        "map": frame["map"].clip(
            bounds["map"]["lower"], bounds["map"]["upper"]
        ),
        "rpm": frame["rpm"].clip(
            bounds["rpm"]["lower"], bounds["rpm"]["upper"]
        ),
        "intake_temp": frame["intake_temp"].clip(
            bounds["intake_temp"]["lower"],
            bounds["intake_temp"]["upper"],
        ),
    }
    expected_maf = pd.Series(
        float(speed_density["intercept"]), index=frame.index
    )
    for name, values in model_inputs.items():
        expected_maf = (
            expected_maf
            + float(speed_density["coefficients"][name]) * values
        )
    frame["speed_density_maf_residual"] = frame["maf"] - expected_maf

    # Segment identifiers are not assumed globally unique across trips.
    group = frame.groupby(["trip_id", "segment_id"], sort=False)
    frame["pedal_slope"] = group["accel_pedal_mean"].diff()
    frame["rpm_slope"] = group["rpm"].diff()
    frame["ect_rate_180s"] = group["coolant_temp"].transform(
        lambda s: (s - s.shift(180)) / 3.0
    )
    frame["intake_temp_stability"] = group["intake_temp"].transform(
        lambda s: s.rolling(60, min_periods=60).std()
    )
    frame["speed_std_120s"] = group["speed"].transform(
        lambda s: s.rolling(120, min_periods=120).std()
    )
    frame["maf_std_120s"] = group["maf"].transform(
        lambda s: s.rolling(120, min_periods=120).std()
    )
    frame["rpm_std_120s"] = group["rpm"].transform(
        lambda s: s.rolling(120, min_periods=120).std()
    )
    frame["accel_pedal_mean_std_120s"] = group[
        "accel_pedal_mean"
    ].transform(lambda s: s.rolling(120, min_periods=120).std())
    frame["map_range_60s"] = group["map"].transform(
        lambda s: (
            s.rolling(60, min_periods=60).max()
            - s.rolling(60, min_periods=60).min()
        )
    )
    frame["maf_integral_180s"] = group["maf"].transform(
        lambda s: (
            s.rolling(181, min_periods=181).sum()
            - 0.5 * s
            - 0.5 * s.shift(180)
        )
    )


def run_proxy_stages(layout: RunLayout, creation_time_utc: str) -> None:
    for _stage_id, filename, function_name in PROXY_STAGE_FILES:
        module = load_stage_module(filename)
        function = getattr(module, function_name)
        function(layout, creation_time_utc=creation_time_utc)


def evaluate_case(
    layout: RunLayout,
    case: dict[str, Any],
    window: Window,
    *,
    baseline_layout: RunLayout | None = None,
) -> dict[str, Any]:
    decisions = pd.read_csv(layout.proxy_decisions, low_memory=False)
    target = decisions[
        decisions["sub_check_id"].eq(case["expected_sub_check_id"])
    ]
    target = target[target["trip_id"].astype(str).eq(window.trip_id)]
    if target["segment_id"].notna().any():
        target = target[
            target["segment_id"].astype(str).eq(window.segment_id)
        ]
    if target.empty:
        raise FaultInjectionError(
            f"No scoped decision row found for "
            f"{case['expected_sub_check_id']} in trip {window.trip_id}."
        )
    expected_state = case.get("expected_result_state", "triggered")
    hits = target[target["result_state"].eq(expected_state)]
    chosen = hits.iloc[0] if not hits.empty else target.iloc[0]
    baseline_state = None
    baseline_already_positive = False
    if baseline_layout is not None:
        baseline = pd.read_csv(
            baseline_layout.proxy_decisions, low_memory=False
        )
        baseline = baseline[
            baseline["sub_check_id"].eq(case["expected_sub_check_id"])
            & baseline["trip_id"].astype(str).eq(window.trip_id)
        ]
        if baseline["segment_id"].notna().any():
            baseline = baseline[
                baseline["segment_id"].astype(str).eq(window.segment_id)
            ]
        if not baseline.empty:
            baseline_state = str(baseline.iloc[0].get("result_state"))
            baseline_already_positive = bool(
                baseline["result_state"].eq(expected_state).any()
            )
    emitted = chosen.get("dtc_emitted")
    actual_dtc = chosen.get("dtc_candidate_label")
    expected_dtc = case.get("expected_dtc_candidate_label")
    dtc_matches = (
        expected_dtc is None
        or str(actual_dtc) == str(expected_dtc)
    )
    expected_emitted = case.get("expected_dtc_emitted")
    emitted_bool = parse_bool(emitted, field="dtc_emitted")
    emission_matches = (
        expected_emitted is None
        or emitted_bool == parse_bool(
            expected_emitted, field="expected_dtc_emitted"
        )
    )
    actual_routed_dtc = chosen.get("routed_dtc")
    if "expected_routed_dtc" in case:
        expected_routed_dtc = case["expected_routed_dtc"]
        routed_dtc_matches = (
            pd.isna(actual_routed_dtc)
            if expected_routed_dtc is None
            else str(actual_routed_dtc) == str(expected_routed_dtc)
        )
    elif expected_emitted is not None and not parse_bool(
        expected_emitted, field="expected_dtc_emitted"
    ):
        routed_dtc_matches = pd.isna(actual_routed_dtc)
    else:
        routed_dtc_matches = True
    return {
        "actual_result_state": chosen.get("result_state"),
        "baseline_result_state": baseline_state,
        "baseline_already_positive": baseline_already_positive,
        "decision_reason": chosen.get("decision_reason"),
        "decision_margin": chosen.get("decision_margin"),
        "dtc_candidate_label": actual_dtc,
        "dtc_matches_expected": dtc_matches,
        "dtc_emitted": emitted_bool,
        "emission_matches_expected": emission_matches,
        "routed_dtc": actual_routed_dtc,
        "routed_dtc_matches_expected": routed_dtc_matches,
        "confidence": chosen.get("confidence"),
        "passed": bool(
            not hits.empty
            and not baseline_already_positive
            and dtc_matches
            and emission_matches
            and routed_dtc_matches
        ),
    }


def run_batch_case(
    *,
    base_layout: RunLayout,
    case: dict[str, Any],
    run_id: str,
    creation_time_utc: str,
) -> list[dict[str, Any]]:
    """Inject one severity into several trips and run the pipeline once."""

    target_layout = RunLayout.for_run_id(run_id, repo_root=REPO_ROOT)
    copy_minimal_run(base_layout, target_layout)
    frame = pd.read_csv(target_layout.production_features, low_memory=False)
    registry = load_calibration_registry()
    windows = select_windows(
        frame, case, int(case.get("_replicates", 1)), registry
    )
    for window in windows:
        inject_case(frame, case, window)
    recompute_dependent_features(frame, registry)
    frame.to_csv(
        target_layout.production_features,
        index=False,
        float_format="%.15g",
        lineterminator="\n",
    )
    update_production_manifest(target_layout, {
        **case,
        "case_id": (
            f"{case['case_id']}__{case.get('_severity_id', 'single')}"
        ),
    })
    run_proxy_stages(target_layout, creation_time_utc)

    return collect_batch_case_results(
        base_layout=base_layout,
        target_layout=target_layout,
        case=case,
        windows=windows,
    )


def collect_batch_case_results(
    *,
    base_layout: RunLayout,
    target_layout: RunLayout,
    case: dict[str, Any],
    windows: list[Window] | None = None,
) -> list[dict[str, Any]]:
    """Collect results from an existing batch run (supports resumption)."""

    if windows is None:
        injected = pd.read_csv(
            target_layout.production_features, low_memory=False
        )
        registry = load_calibration_registry()
        windows = select_windows(
            injected, case, int(case.get("_replicates", 1)), registry
        )
    rows: list[dict[str, Any]] = []
    for replicate, window in enumerate(windows, start=1):
        result = evaluate_case(
            target_layout, case, window, baseline_layout=base_layout
        )
        rows.append({
            "case_id": case["case_id"],
            "run_id": target_layout.run_id,
            "proxy_id": case["proxy_id"],
            "expected_sub_check_id": case["expected_sub_check_id"],
            "expected_result_state": case.get(
                "expected_result_state", "triggered"
            ),
            "target_signal": case["target_signal"],
            "selector": case["selector"],
            "severity_id": case.get("_severity_id", "single"),
            "severity_rank": case.get("_severity_rank", 0),
            "replicate": replicate,
            "trip_id": window.trip_id,
            "segment_id": window.segment_id,
            "injection_start_timestamp": window.start_timestamp,
            "injection_end_timestamp": window.end_timestamp,
            **result,
            "decisions_path": target_layout.run_relative_posix(
                target_layout.proxy_decisions
            ),
        })
    return rows


def expand_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand registered severity grids and independent-trip replicates."""

    expanded: list[dict[str, Any]] = []
    for case in cases:
        severities = case.get("severity_grid") or [
            {"severity_id": "single", "parameters": {}}
        ]
        replicates = int(case.get("replicates", 1))
        if replicates <= 0:
            raise FaultInjectionError(
                f"{case['case_id']} replicates must be positive."
            )
        for rank, severity in enumerate(severities):
            parameters = severity.get("parameters", {})
            illegal = set(parameters) & {
                "case_id", "proxy_id", "expected_sub_check_id",
                "target_signal", "selector", "strategy",
            }
            if illegal:
                raise FaultInjectionError(
                    f"{case['case_id']} severity overrides identity fields: "
                    f"{sorted(illegal)}"
                )
            item = copy.deepcopy(case)
            item.update(parameters)
            item["_severity_id"] = severity["severity_id"]
            item["_severity_rank"] = rank
            item["_replicates"] = replicates
            item["_window_ordinal"] = 0
            expanded.append(item)
    return expanded


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (math.nan, math.nan)
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(
        p * (1 - p) / total + z * z / (4 * total * total)
    ) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def healthy_baseline(base_layout: RunLayout) -> list[dict[str, Any]]:
    """Measure frozen-rule outcomes on the configured healthy base run."""

    if not base_layout.proxy_decisions.is_file():
        raise FaultInjectionError(
            f"Base run has no proxy decisions: {base_layout.proxy_decisions}"
        )
    decisions = pd.read_csv(base_layout.proxy_decisions, low_memory=False)
    rows: list[dict[str, Any]] = []
    for sub_check_id, group in decisions.groupby("sub_check_id", sort=True):
        evaluable = group[group["result_state"].isin(
            ["pass", "triggered", "pending"]
        )]
        positives = evaluable["result_state"].isin(
            ["triggered", "pending"]
        ).sum()
        low, high = wilson_interval(int(positives), len(evaluable))
        rows.append({
            "sub_check_id": sub_check_id,
            "evaluable_units": int(len(evaluable)),
            "positive_units": int(positives),
            "positive_rate": (
                float(positives / len(evaluable)) if len(evaluable)
                else None
            ),
            "wilson_95_low": None if math.isnan(low) else low,
            "wilson_95_high": None if math.isnan(high) else high,
        })
    return rows


def campaign_summary(
    rows: list[dict[str, Any]], healthy_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    curves: list[dict[str, Any]] = []
    monotonicity: list[dict[str, Any]] = []
    for (case_id, rank, severity_id), group in frame.groupby(
        ["case_id", "severity_rank", "severity_id"], sort=True
    ):
        detected = int(group["passed"].sum())
        low, high = wilson_interval(detected, len(group))
        curves.append({
            "case_id": case_id,
            "severity_rank": int(rank),
            "severity_id": severity_id,
            "injected_trip_count": int(len(group)),
            "detected_trip_count": detected,
            "detection_rate": float(detected / len(group)),
            "wilson_95_low": low,
            "wilson_95_high": high,
        })
    curve_frame = pd.DataFrame(curves)
    acceptance_rows: list[dict[str, Any]] = []
    for case_id, group in curve_frame.groupby("case_id", sort=True):
        ordered = group.sort_values("severity_rank")
        rates = ordered["detection_rate"].tolist()
        monotonic = all(
            right >= left for left, right in zip(rates, rates[1:])
        )
        monotonicity.append({
            "case_id": case_id,
            "nondecreasing_detection_rate": monotonic,
            "severity_point_count": len(rates),
        })
        strongest = ordered.iloc[-1]
        enough_points = len(ordered) >= 3
        enough_replicates = bool(
            ordered["injected_trip_count"].ge(3).all()
        )
        strong_rate_ok = strongest["detection_rate"] >= 0.8
        acceptance_rows.append({
            "case_id": case_id,
            "severity_points_at_least_3": enough_points,
            "replicates_per_point_at_least_3": enough_replicates,
            "nondecreasing_detection_rate": monotonic,
            "strongest_detection_rate": float(
                strongest["detection_rate"]
            ),
            "strongest_detection_rate_at_least_0_8": strong_rate_ok,
            "conditional_acceptance": bool(
                enough_points
                and enough_replicates
                and monotonic
                and strong_rate_ok
            ),
        })
    conditional_complete = bool(acceptance_rows) and all(
        row["conditional_acceptance"] for row in acceptance_rows
    )
    return {
        "protocol_status": {
            "tbd_1_target_signal_only": True,
            "tbd_2_graded_detectability": bool(
                curve_frame.groupby("case_id").size().max() > 1
            ) if len(curve_frame) else False,
            "acceptance_decision": (
                "conditional_detection_acceptance_pass"
                if conditional_complete
                else "conditional_detection_acceptance_fail"
            ),
            "acceptance_scope": (
                "synthetic target-signal injection, graded severity, "
                "independent-trip replicates, decision/DTC contract checks"
            ),
        },
        "detectability_curves": curves,
        "monotonicity_checks": monotonicity,
        "conditional_acceptance": acceptance_rows,
        "healthy_baseline": healthy_rows,
    }


def write_summary(
    rows: list[dict[str, Any]],
    healthy_rows: list[dict[str, Any]],
    stamp: str,
) -> None:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DEFAULT_OUTPUT_DIR / f"fault_injection_summary_{stamp}.csv"
    json_path = DEFAULT_OUTPUT_DIR / f"fault_injection_summary_{stamp}.json"
    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False, lineterminator="\n")
    json_path.write_text(
        json.dumps({
            "case_results": rows,
            **campaign_summary(rows, healthy_rows),
        }, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "case_count": len(rows),
        "passed_count": int(frame["passed"].sum()) if len(frame) else 0,
        "summary_csv": str(csv_path),
        "summary_json": str(json_path),
    }, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-run-id", default="recalibrate_20260723")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--only-case")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument(
        "--run-prefix",
        help="Optional prefix for generated run IDs. Default: stage4_<UTC>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=False)
    cases = load_cases(config_path)
    if args.only_case:
        cases = [case for case in cases if case["case_id"] == args.only_case]
        if not cases:
            raise FaultInjectionError(f"Unknown case_id: {args.only_case}")
    if args.max_cases is not None:
        cases = cases[:args.max_cases]
    if args.list_cases:
        print(json.dumps([
            {
                "case_id": case["case_id"],
                "expected_sub_check_id": case["expected_sub_check_id"],
                "target_signal": case["target_signal"],
                "selector": case["selector"],
            }
            for case in cases
        ], ensure_ascii=False, indent=2))
        return 0

    cases = expand_cases(cases)
    stamp = utc_stamp()
    prefix = args.run_prefix or f"fault_injection_{stamp}"
    base_layout = RunLayout.for_run_id(args.base_run_id, repo_root=REPO_ROOT)
    if not base_layout.production_features.is_file():
        raise FaultInjectionError(
            f"Base run is missing production_features.csv: "
            f"{base_layout.production_features}"
        )

    creation_time = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_copy = copy.deepcopy(case)
        suffix = f"{case_copy['case_id']}__{case_copy['_severity_id']}"
        run_id = f"{prefix}__{suffix}"
        print(f"[Stage4] Running {suffix} -> {run_id}")
        rows.extend(
            run_batch_case(
                base_layout=base_layout,
                case=case_copy,
                run_id=run_id,
                creation_time_utc=creation_time,
            )
        )
    write_summary(rows, healthy_baseline(base_layout), stamp)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FaultInjectionError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
