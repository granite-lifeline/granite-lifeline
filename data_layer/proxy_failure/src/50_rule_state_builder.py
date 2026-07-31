"""Materialize per-sub-check rule state and engine-start decision state.

Script 50 consumes the validated production feature handoff, per-signal
cleaning quality, the engine-start episode table, and the frozen
calibration registry.  It materializes every eligibility mask, context
opportunity, physical-range condition, and engine-start evidence value
that scripts 60, 61, and 70 are allowed to consume, so that script 70
never reads canonical or production-feature tables directly.

Outputs (both under ``proxy/50_rule_state/``):

- ``rule_state.csv`` — sample grain.
- ``engine_start_rule_state.csv`` — episode grain (1-S1 evidence).
- ``rule_state_manifest.json`` — stage manifest with the explicit
  evidence schema.

The frozen registry is loaded read-only; no threshold is fitted,
selected, or modified here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.continuity import (  # noqa: E402
    build_continuity_blocks,
    build_quality_valid_mask,
    build_true_run_ids,
)
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    build_stage_manifest,
    load_json_object,
    sha256_file,
    validate_stage_manifest,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

SCRIPT_VERSION = "1.0.0"
SCHEMA_VERSION = "feature_schema.v1"
STAGE_ID = "50"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]

# Evidence values carried through so scripts 61/70 never read canonical
# or production-feature tables.
EVIDENCE_VALUE_COLUMNS = [
    "coolant_temp", "ambient_temp", "intake_temp", "maf", "rpm",
    "speed_density_maf_residual", "pedal_mapping_residual",
    "accel_pedal_channel_delta", "pedal_slope", "rpm_slope",
    "intake_temp_stability", "ect_rate_180s", "map_range_60s",
]

# Ordered episode-grain contract for engine_start_rule_state.csv.  An
# upload may legitimately contain no observed engine start (a mid-drive
# recording), and an empty record list would otherwise produce a
# zero-column frame whose CSV carries no header, which script 70 cannot
# parse.  Declaring the columns keeps the artifact readable at zero rows.
ENGINE_START_RULE_STATE_COLUMNS = [
    "engine_start_episode_id",
    "trip_id",
    "segment_id",
    "start_timestamp",
    "end_timestamp",
    "episode_duration_seconds",
    "termination_reason",
    "ect_start",
    "aat_start",
    "s1s1_start_quality_valid",
    "s1s1_eligible",
    "ambient_bin",
    "budget_seconds",
    "budget_in_domain",
    "time_to_target_79c",
    "time_to_target_79c_is_right_censored",
    "time_to_target_79c_censor_time_s",
    "maf_integral_at_expiry",
    "heat_guard_passed",
    "s1s4_evaluable",
    "s1s4_exceed",
    "s1s4_not_evaluable_reason",
]


class RuleStateContractError(RuntimeError):
    """Raised when script 50 inputs violate the frozen contract."""


def _verify_input(
    path: Path, expected_sha: str, *, label: str
) -> None:
    actual = sha256_file(path)
    if actual != expected_sha:
        raise RuleStateContractError(
            f"{label} checksum drift: expected {expected_sha}, "
            f"found {actual}."
        )


def load_registry(layout: RunLayout) -> dict[str, Any]:
    """Load the frozen registry after verifying its release checksum."""

    release = load_json_object(layout.calibration_release_manifest)
    _verify_input(
        layout.calibration_registry,
        release["registry"]["sha256"],
        label="calibration registry",
    )
    registry = load_json_object(layout.calibration_registry)
    policy = registry.get("online_policy", {})
    if not policy.get("read_only") or policy.get("fit_allowed"):
        raise RuleStateContractError(
            "Registry online policy must be read-only with fitting "
            "disabled."
        )
    return registry


def load_inputs(
    layout: RunLayout,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load and checksum-verify production, quality, episode inputs."""

    production_manifest = load_json_object(
        layout.production_feature_manifest
    )
    recorded = production_manifest["artifact_sha256"]
    _verify_input(
        layout.production_features,
        recorded["features/41_production/production_features.csv"],
        label="production_features.csv",
    )
    stage20_manifest = load_json_object(
        layout.engine_start_context_manifest
    )
    episode_sha = stage20_manifest["artifact_sha256"][
        "features/20_engine_start/engine_start_episodes.csv"
    ]
    _verify_input(
        layout.engine_start_episodes,
        episode_sha,
        label="engine_start_episodes.csv",
    )

    production = pd.read_csv(layout.production_features, low_memory=False)
    quality = pd.read_csv(layout.cleaning_quality, low_memory=False)
    episodes = pd.read_csv(layout.engine_start_episodes, low_memory=False)

    flag_columns = [
        column for column in quality.columns
        if column.endswith(
            ("_is_imputed", "_is_suspicious", "_had_hard_invalid_source")
        )
    ]
    merged = production.merge(
        quality[KEYS + flag_columns],
        on=KEYS,
        how="left",
        validate="one_to_one",
    )
    if len(merged) != len(production):
        raise RuleStateContractError(
            "Quality join changed the sample row count."
        )
    if merged[flag_columns].isna().any().any():
        raise RuleStateContractError(
            "Every sample must carry per-signal quality flags."
        )
    return merged, episodes, {
        "source_dataset_identity": (
            production_manifest["source_dataset_identity"]
        ),
        "production_manifest": production_manifest,
    }


class _QualityMaskCache:
    """Per-signal quality masks computed once and AND-combined."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame
        self._masks: dict[str, pd.Series] = {}

    def __call__(self, *signals: str) -> pd.Series:
        result = pd.Series(True, index=self._frame.index, dtype=bool)
        for signal in signals:
            if signal not in self._masks:
                self._masks[signal] = build_quality_valid_mask(
                    self._frame, [signal]
                )
            result &= self._masks[signal]
        return result


def _persistence_mask(
    condition: pd.Series,
    block_ids: pd.Series,
    minimum_samples: int,
) -> pd.Series:
    """True where ``condition`` has held for >= N consecutive samples."""

    run_ids = build_true_run_ids(condition.fillna(False), block_ids)
    position = run_ids.groupby(run_ids, dropna=True, sort=False).cumcount()
    mask = run_ids.notna() & position.add(1).ge(minimum_samples)
    return mask.fillna(False).astype(bool)


def _threshold(rule: dict[str, Any], *keys: str) -> float:
    node: Any = rule
    for key in keys:
        node = node[key]
    if isinstance(node, dict):
        node = node.get("raw_value", node.get("value"))
    return float(node)


def build_rule_state(
    frame: pd.DataFrame,
    registry: dict[str, Any],
    *,
    quality_cache: "_QualityMaskCache | None" = None,
) -> pd.DataFrame:
    """Materialize the sample-grain rule-state evidence table."""

    rules = registry["proxy_rules"]
    engine_on_rpm = float(
        registry["shared_constants"]["engine_on_rpm"]["value"]
    )

    structural = build_continuity_blocks(frame)
    blocks = structural.block_id

    q = quality_cache or _QualityMaskCache(frame)

    rpm_valid = q("rpm")
    engine_on = frame["rpm"].ge(engine_on_rpm).where(rpm_valid, pd.NA)
    engine_on_bool = engine_on.astype("boolean").fillna(
        False).astype(bool)
    post_warmup = frame["thermal_state"].eq("post_warmup")
    confidence_high = frame["condition_confidence"].eq("high")

    out = frame[KEYS + EVIDENCE_VALUE_COLUMNS].copy()
    out.insert(4, "continuity_block_id", blocks)
    out["engine_on"] = engine_on.astype("boolean")

    # --- shared masks -------------------------------------------------
    r3a = rules["3-S1a"]["guards"]
    pedal_quality = q("accel_pedal_d", "accel_pedal_e")
    lowmotion_instant = (
        engine_on_bool
        & pedal_quality
        & frame["pedal_slope"].abs().le(
            _threshold(r3a, "pedal_slope_abs"))
    )
    out["pedal_lowmotion_mask"] = _persistence_mask(
        lowmotion_instant, blocks,
        int(_threshold(r3a, "mask_persistence")),
    )

    r5b = rules["5-S2"]["guards"]
    steady_instant = (
        pedal_quality
        & rpm_valid
        & frame["pedal_slope"].abs().eq(
            _threshold(r5b, "pedal_slope_abs"))
        & frame["rpm_slope"].abs().le(_threshold(r5b, "rpm_slope_abs"))
    )
    out["steady_state_mask"] = _persistence_mask(
        steady_instant, blocks,
        int(_threshold(r5b, "steady_mask_persistence")),
    )

    r41 = rules["4-S1"]
    out["s4s1_material_context"] = (
        frame["speed_std_120s"].ge(
            _threshold(r41, "context_thresholds", "speed_std_120s"))
        | frame["maf_std_120s"].ge(
            _threshold(r41, "context_thresholds", "maf_std_120s"))
    ).fillna(False)

    r53 = rules["5-S3"]
    out["s5s3_material_context"] = (
        frame["rpm_std_120s"].ge(
            _threshold(r53, "context_thresholds", "rpm_std_120s"))
        | frame["speed_std_120s"].ge(
            _threshold(r53, "context_thresholds", "speed_std_120s"))
        | frame["accel_pedal_mean_std_120s"].ge(
            _threshold(
                r53, "context_thresholds", "accel_pedal_mean_std_120s"))
    ).fillna(False)

    # --- 1-S2 overheating --------------------------------------------
    r12 = rules["1-S2"]
    s1s2_eligible = (
        engine_on_bool
        & post_warmup
        & q("coolant_temp", "ambient_temp")
        & frame["ambient_temp"].le(
            _threshold(r12, "guards", "ambient_at_window_start_max_c"))
    )
    out["s1s2_eligible"] = s1s2_eligible
    tiers = {tier["name"]: tier for tier in r12["tiers"]}
    out["s1s2_exceed_high"] = frame["coolant_temp"].ge(
        _threshold(tiers["high"], "temperature")
    ).where(s1s2_eligible, pd.NA).astype("boolean")
    out["s1s2_exceed_critical"] = frame["coolant_temp"].ge(
        _threshold(tiers["critical_provisional"], "temperature")
    ).where(s1s2_eligible, pd.NA).astype("boolean")

    # --- 1-S3 pending precursor --------------------------------------
    r13 = rules["1-S3"]
    s1s3_eligible = (
        post_warmup
        & q("coolant_temp")
        & frame["ect_rate_180s"].notna()
    )
    out["s1s3_eligible"] = s1s3_eligible
    out["s1s3_precursor_condition"] = (
        frame["ect_rate_180s"].ge(_threshold(r13, "rate"))
        & frame["coolant_temp"].ge(_threshold(r13, "level"))
    ).where(s1s3_eligible, pd.NA).astype("boolean")

    # --- 2-S2 high-load under-read -----------------------------------
    r22 = rules["2-S2"]
    s2s2_eligible = (
        frame["operating_state"].eq(r22["guards"]["operating_state"])
        & confidence_high
        & frame["speed_density_maf_residual"].notna()
    )
    out["s2s2_eligible"] = s2s2_eligible
    out["s2s2_residual_low"] = frame["speed_density_maf_residual"].lt(
        _threshold(r22, "residual")
    ).where(s2s2_eligible, pd.NA).astype("boolean")

    # --- 2-S3b zero MAF while firing ---------------------------------
    r23 = rules["2-S3b"]
    s2s3b_eligible = q("maf", "rpm")
    out["s2s3b_eligible"] = s2s3b_eligible
    out["s2s3b_zero_maf_firing"] = (
        frame["maf"].eq(_threshold(r23, "maf"))
        & frame["rpm"].ge(_threshold(r23, "rpm"))
    ).where(s2s3b_eligible, pd.NA).astype("boolean")

    # --- 3-S1a channel-relation residual -----------------------------
    s3s1a_eligible = (
        out["pedal_lowmotion_mask"]
        & frame["pedal_mapping_residual"].notna()
    )
    out["s3s1a_eligible"] = s3s1a_eligible
    band = rules["3-S1a"]["residual_band"]
    out["s3s1a_residual_low"] = frame["pedal_mapping_residual"].lt(
        float(band["low"]["raw_value"])
    ).where(s3s1a_eligible, pd.NA).astype("boolean")
    out["s3s1a_residual_high"] = frame["pedal_mapping_residual"].gt(
        float(band["high"]["raw_value"])
    ).where(s3s1a_eligible, pd.NA).astype("boolean")

    # --- 3-S1b extreme disagreement ----------------------------------
    r31b = rules["3-S1b"]
    s3s1b_eligible = frame["accel_pedal_channel_delta"].notna()
    out["s3s1b_eligible"] = s3s1b_eligible
    out["s3s1b_extreme_delta"] = frame["accel_pedal_channel_delta"].ge(
        _threshold(r31b, "channel_delta")
    ).where(s3s1b_eligible, pd.NA).astype("boolean")

    # --- 4-S1 stuck IAT ----------------------------------------------
    s4s1_eligible = engine_on_bool & q(
        *rules["4-S1"]["guards"]["required_quality_valid_signals"]
    )
    out["s4s1_eligible"] = s4s1_eligible
    out["s4s1_context_opportunity"] = (
        s4s1_eligible & out["s4s1_material_context"]
    )
    out["s4s1_flat"] = frame["intake_temp_stability"].le(
        _threshold(r41, "stability")
    ).where(
        s4s1_eligible & frame["intake_temp_stability"].notna(), pd.NA
    ).astype("boolean")

    # --- 4-S3 physical range -----------------------------------------
    r43 = rules["4-S3"]
    s4s3_evaluable = q("intake_temp")
    out["s4s3_evaluable"] = s4s3_evaluable
    out["s4s3_below_range"] = frame["intake_temp"].lt(
        _threshold(r43, "low")
    ).where(s4s3_evaluable, pd.NA).astype("boolean")
    out["s4s3_above_range"] = frame["intake_temp"].gt(
        _threshold(r43, "high")
    ).where(s4s3_evaluable, pd.NA).astype("boolean")

    # --- 5-S1 step-response domain -----------------------------------
    out["s5s1_domain"] = (
        post_warmup
        & confidence_high
        & q(*rules["5-S1"]["guards"]["required_quality_valid_signals"])
    )

    # --- 5-S2 steady-state residual ----------------------------------
    r52 = rules["5-S2"]
    s5s2_eligible = (
        out["steady_state_mask"]
        & frame["operating_state"].eq(r52["guards"]["operating_state"])
        & frame["speed_density_maf_residual"].notna()
    )
    out["s5s2_eligible"] = s5s2_eligible
    band52 = r52["residual_band"]
    out["s5s2_residual_low"] = frame["speed_density_maf_residual"].lt(
        float(band52["low"]["raw_value"])
    ).where(s5s2_eligible, pd.NA).astype("boolean")
    out["s5s2_residual_high"] = frame["speed_density_maf_residual"].gt(
        float(band52["high"]["raw_value"])
    ).where(s5s2_eligible, pd.NA).astype("boolean")

    # --- 5-S3 stuck MAP ----------------------------------------------
    s5s3_eligible = engine_on_bool & q(
        *rules["5-S3"]["guards"]["required_quality_valid_signals"]
    )
    out["s5s3_eligible"] = s5s3_eligible
    out["s5s3_context_opportunity"] = (
        s5s3_eligible & out["s5s3_material_context"]
    )
    out["s5s3_flat"] = frame["map_range_60s"].eq(
        _threshold(r53, "flatness")
    ).where(
        s5s3_eligible & frame["map_range_60s"].notna(), pd.NA
    ).astype("boolean")

    return out


def build_cold_start_state(
    frame: pd.DataFrame,
    rule_state: pd.DataFrame,
    registry: dict[str, Any],
    *,
    quality_cache: "_QualityMaskCache | None" = None,
) -> pd.DataFrame:
    """Attach 1-S4 / 4-S2 segment-first-row evidence and the 4-S2 cap."""

    rules = registry["proxy_rules"]
    r14 = rules["1-S4"]
    r42 = rules["4-S2"]

    q = quality_cache or _QualityMaskCache(frame)
    rpm_valid = q("rpm")
    rpm_blocks = build_continuity_blocks(frame, valid_mask=rpm_valid)
    rpm_block_id = rpm_blocks.block_id

    out = rule_state
    n = len(frame)
    first_row = frame["row_in_segment"].eq(1)
    out["coldstart_first_row"] = first_row

    reason = pd.Series(pd.NA, index=frame.index, dtype="string")
    gap_ok = frame["segment_gap_seconds"].ge(
        _threshold(r14, "guards", "segment_gap_seconds")
    ).fillna(False)
    rpm_below = (
        rpm_valid
        & frame["rpm"].lt(_threshold(r14, "guards", "first_row_rpm"))
    )
    sensors_valid = q(
        *r14["guards"]["required_quality_valid_signals"]
    )

    # First observed start in the same rpm-continuity block as the
    # segment first row.
    starts = frame["engine_start_observed"].astype("boolean").fillna(
        False).astype(bool)
    start_positions = frame.index[starts]
    first_positions = frame.index[first_row]
    start_block = rpm_block_id[start_positions]
    qualifying_start_position: dict[int, int] = {}
    starts_by_block: dict[Any, int] = {}
    for position, block in sorted(
        zip(start_positions, start_block.tolist())
    ):
        if pd.notna(block) and block not in starts_by_block:
            starts_by_block[block] = position
    for position in first_positions:
        block = rpm_block_id.iloc[position]
        if pd.isna(block):
            continue
        candidate = starts_by_block.get(block)
        if candidate is not None and candidate > position:
            qualifying_start_position[position] = candidate

    has_later_start = pd.Series(False, index=frame.index)
    has_later_start.loc[list(qualifying_start_position)] = True
    qualifying_start = pd.Series(False, index=frame.index)
    qualifying_start.loc[
        list(qualifying_start_position.values())
    ] = True
    out["coldstart_qualifying_start"] = qualifying_start

    base_eligible = (
        first_row & gap_ok & rpm_below & has_later_start & sensors_valid
    )
    reason.loc[first_row & ~gap_ok] = "cold_soak_gap_unavailable"
    reason.loc[first_row & gap_ok & ~rpm_below] = "first_row_engine_on"
    reason.loc[
        first_row & gap_ok & rpm_below & ~has_later_start
    ] = "no_observed_start_in_block"
    reason.loc[
        first_row & gap_ok & rpm_below & has_later_start & ~sensors_valid
    ] = "signal_quality"
    out["coldstart_not_evaluable_reason"] = reason

    iat_aat = (frame["intake_temp"] - frame["ambient_temp"]).abs()
    ect_aat = (frame["coolant_temp"] - frame["ambient_temp"]).abs()

    iat_witness_ok = iat_aat.le(
        _threshold(r14, "guards", "iat_witness_abs_delta_c")
    )
    s1s4_eligible = base_eligible & iat_witness_ok.fillna(False)
    out["s1s4_eligible"] = s1s4_eligible
    out["s1s4_ect_aat_abs_delta"] = ect_aat.where(first_row)
    out["s1s4_exceed"] = ect_aat.gt(
        _threshold(r14, "ect_abs_delta_c")
    ).where(s1s4_eligible, pd.NA).astype("boolean")
    out.loc[
        base_eligible & ~iat_witness_ok.fillna(False),
        "coldstart_not_evaluable_reason",
    ] = "iat_witness_failed"

    ect_witness_ok = ect_aat.le(
        _threshold(r42, "guards", "ect_witness_abs_delta_c")
    )
    s4s2_eligible = base_eligible & ect_witness_ok.fillna(False)
    out["s4s2_eligible"] = s4s2_eligible
    out["s4s2_iat_aat_abs_delta"] = iat_aat.where(first_row)
    out["s4s2_exceed"] = iat_aat.gt(
        _threshold(r42, "iat_abs_delta_c")
    ).where(s4s2_eligible, pd.NA).astype("boolean")

    # 4-S2 prospective confidence cap: active from the qualifying
    # observed start row through the end of that rpm continuity block.
    cap = pd.Series(False, index=frame.index)
    exceeding_first_rows = frame.index[
        (out["s4s2_exceed"].fillna(False).astype(bool))
    ]
    block_last_position = {}
    non_null = rpm_block_id.notna()
    positions = pd.Series(range(n), index=frame.index)
    grouped = positions[non_null].groupby(
        rpm_block_id[non_null], sort=False
    )
    for block, group in grouped:
        block_last_position[block] = int(group.max())
    for position in exceeding_first_rows:
        start_pos = qualifying_start_position.get(position)
        if start_pos is None:
            continue
        block = rpm_block_id.iloc[start_pos]
        end_pos = block_last_position.get(block)
        if end_pos is not None:
            cap.iloc[start_pos:end_pos + 1] = True
    out["s4s2_cap_active"] = cap
    return out


def build_engine_start_rule_state(
    frame: pd.DataFrame,
    rule_state: pd.DataFrame,
    episodes: pd.DataFrame,
    registry: dict[str, Any],
    *,
    quality_cache: "_QualityMaskCache | None" = None,
) -> pd.DataFrame:
    """Materialize per-episode 1-S1 evidence (episode grain)."""

    r11 = registry["proxy_rules"]["1-S1"]
    budget = r11["warmup_budget"]
    target_c = _threshold(r11, "target_temperature")
    band_edges = [float(x) for x in budget["temperature_band_upper_edges_c"]]
    band_labels = ["<30", "30-50", "50-65", "65-79"]
    ambient_split = float(budget["ambient_split"]["value"])
    low_label = budget["ambient_split"]["low_label"]
    high_label = budget["ambient_split"]["high_label"]
    safety = float(budget["safety_factor"])
    max_budget_s = float(
        budget["maximum_deployable_budget"]["value"]) * 60.0
    heat = r11["heat_input_guard"]
    heat_threshold = float(heat["raw_value"])

    q = quality_cache or _QualityMaskCache(frame)
    ect_valid = q("coolant_temp")
    start_quality = q(
        *r11["start_guards"]["required_quality_valid_signals"]
    )
    by_episode = {
        episode_id: group
        for episode_id, group in frame.groupby(
            frame["engine_start_episode_id"], sort=False
        )
    }

    first_row_evidence = rule_state[
        rule_state["coldstart_first_row"]
    ].set_index("segment_id")

    records: list[dict[str, Any]] = []
    for episode in episodes.itertuples(index=False):
        episode_id = episode.engine_start_episode_id
        group = by_episode.get(episode_id)
        record: dict[str, Any] = {
            "engine_start_episode_id": episode_id,
            "trip_id": episode.trip_id,
            "segment_id": episode.segment_id,
            "start_timestamp": episode.start_timestamp,
            "end_timestamp": episode.end_timestamp,
            "episode_duration_seconds": float(
                episode.episode_duration_seconds
            ),
            "termination_reason": episode.termination_reason,
            "ect_start": episode.ect_start,
            "aat_start": episode.aat_start,
        }
        ect_start = episode.ect_start
        aat_start = episode.aat_start

        crossing = (
            group[
                group["engine_start_observed"]
                .astype("boolean").fillna(False).astype(bool)
            ]
            if group is not None else None
        )
        crossing_ok = crossing is not None and len(crossing) == 1
        crossing_quality = bool(
            crossing_ok
            and start_quality.loc[crossing.index[0]]
        )
        guards = r11["start_guards"]
        ect_ok = (
            pd.notna(ect_start)
            and ect_start <= _threshold(guards, "ect_start_max_c")
            and ect_start < target_c
        )
        aat_ok = (
            pd.notna(aat_start)
            and aat_start >= _threshold(guards, "aat_start_min_c")
        )
        record["s1s1_start_quality_valid"] = crossing_quality
        record["s1s1_eligible"] = bool(
            crossing_quality and ect_ok and aat_ok
        )

        budget_seconds: float | None = None
        ambient_bin: str | None = None
        if record["s1s1_eligible"]:
            ambient_bin = (
                low_label if aat_start <= ambient_split else high_label
            )
            rates = budget["selected_rate_lookup_c_per_min"][ambient_bin]
            minutes = 0.0
            lower = float(ect_start)
            previous_edge = None
            for label, edge in zip(band_labels, band_edges):
                band_low = -float("inf") if previous_edge is None \
                    else previous_edge
                previous_edge = edge
                if lower >= edge:
                    continue
                effective_low = max(lower, band_low)
                delta = min(edge, target_c) - effective_low
                if delta > 0:
                    minutes += delta / float(rates[label])
            budget_seconds = minutes * safety * 60.0
        record["ambient_bin"] = ambient_bin
        record["budget_seconds"] = budget_seconds
        record["budget_in_domain"] = (
            bool(budget_seconds is not None
                 and budget_seconds <= max_budget_s)
            if budget_seconds is not None else None
        )

        time_to_target = None
        censor_time = float(episode.episode_duration_seconds)
        if group is not None:
            reached = group[
                ect_valid.loc[group.index]
                & group["coolant_temp"].ge(target_c)
            ]
            if len(reached):
                time_to_target = float(
                    reached["elapsed_since_engine_start"].iloc[0]
                )
        record["time_to_target_79c"] = time_to_target
        in_domain = bool(record["budget_in_domain"])
        censored = None
        if record["s1s1_eligible"] and in_domain:
            censored = bool(
                time_to_target is None
                and censor_time < float(budget_seconds)
            )
        record["time_to_target_79c_is_right_censored"] = censored
        record["time_to_target_79c_censor_time_s"] = (
            censor_time if censored else None
        )

        maf_at_expiry = None
        heat_guard_passed = None
        if record["s1s1_eligible"] and in_domain and group is not None:
            expiry_rows = group[
                group["elapsed_since_engine_start"].ge(budget_seconds)
            ]
            if len(expiry_rows):
                maf_at_expiry = expiry_rows["maf_integral_180s"].iloc[0]
                if pd.notna(maf_at_expiry):
                    heat_guard_passed = bool(
                        maf_at_expiry > heat_threshold
                    )
                else:
                    maf_at_expiry = None
        record["maf_integral_at_expiry"] = maf_at_expiry
        record["heat_guard_passed"] = heat_guard_passed

        is_qualifying_start = bool(
            crossing_ok
            and rule_state["coldstart_qualifying_start"].loc[
                crossing.index[0]
            ]
        )
        segment_evidence = (
            first_row_evidence.loc[episode.segment_id]
            if is_qualifying_start
            and episode.segment_id in first_row_evidence.index
            else None
        )
        s1s4_evaluable = False
        s1s4_exceed = None
        s1s4_reason = "cold_soak_unavailable"
        if segment_evidence is not None:
            if bool(segment_evidence["s1s4_eligible"]):
                s1s4_evaluable = True
                s1s4_exceed = bool(segment_evidence["s1s4_exceed"])
                s1s4_reason = None
            else:
                recorded_reason = segment_evidence[
                    "coldstart_not_evaluable_reason"
                ]
                if pd.notna(recorded_reason):
                    s1s4_reason = str(recorded_reason)
        record["s1s4_evaluable"] = s1s4_evaluable
        record["s1s4_exceed"] = s1s4_exceed
        record["s1s4_not_evaluable_reason"] = s1s4_reason
        records.append(record)

    if not records:
        return pd.DataFrame(columns=ENGINE_START_RULE_STATE_COLUMNS)
    return pd.DataFrame.from_records(records)


def _column_names(frame: pd.DataFrame) -> list[str]:
    return [str(name) for name in frame.columns]


def run_rule_state_builder(
    layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> dict[str, Any]:
    """Execute script 50 and write both outputs plus the manifest."""

    registry = load_registry(layout)
    frame, episodes, meta = load_inputs(layout)

    cache = _QualityMaskCache(frame)
    rule_state = build_rule_state(
        frame, registry, quality_cache=cache
    )
    rule_state = build_cold_start_state(
        frame, rule_state, registry, quality_cache=cache
    )
    episode_state = build_engine_start_rule_state(
        frame, rule_state, episodes, registry, quality_cache=cache
    )

    layout.rule_state_dir.mkdir(parents=True, exist_ok=True)
    rule_state.to_csv(
        layout.rule_state, index=False, float_format="%.15g",
        lineterminator="\n",
    )
    episode_state.to_csv(
        layout.engine_start_rule_state, index=False,
        float_format="%.15g", lineterminator="\n",
    )

    def run_descriptor(path: Path, artifact_id: str) -> ArtifactDescriptor:
        return ArtifactDescriptor.from_file(
            path, artifact_id=artifact_id,
            manifest_path=layout.run_relative_posix(path),
            path_base="run_dir",
        )

    registry_descriptor = ArtifactDescriptor.from_file(
        layout.calibration_registry,
        artifact_id="calibration_registry",
        manifest_path=(
            "data_layer/calibration/calibration_registry.v1.json"
        ),
        path_base="repo_root",
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=SCHEMA_VERSION,
        script_version=SCRIPT_VERSION,
        source_dataset_identity=meta["source_dataset_identity"],
        input_artifacts=[
            run_descriptor(
                layout.production_features, "production_features"),
            run_descriptor(layout.cleaning_quality, "cleaning_quality"),
            run_descriptor(
                layout.engine_start_episodes, "engine_start_episodes"),
            registry_descriptor,
        ],
        output_artifacts=[
            run_descriptor(layout.rule_state, "rule_state"),
            run_descriptor(
                layout.engine_start_rule_state,
                "engine_start_rule_state",
            ),
        ],
        calibration_version=registry["calibration_version"],
        creation_time_utc=creation_time_utc,
    )
    manifest["evidence_schema"] = {
        "rule_state": {
            "grain": "sample",
            "ordered_columns": _column_names(rule_state),
            "row_count": len(rule_state),
        },
        "engine_start_rule_state": {
            "grain": "engine_start_episode",
            "ordered_columns": _column_names(episode_state),
            "row_count": len(episode_state),
        },
        "mask_semantics": {
            "persistence_masks": (
                "true where the instantaneous condition has held for at "
                "least N consecutive valid 1 Hz samples within one "
                "continuity block; N from the frozen registry"
            ),
            "condition_columns": (
                "boolean where the sub-check is eligible, null otherwise"
            ),
        },
    }
    validate_stage_manifest(manifest)
    write_json_atomic(layout.rule_state_manifest, manifest)
    return {
        "rule_state_rows": len(rule_state),
        "episode_rows": len(episode_state),
        "manifest": layout.run_relative_posix(layout.rule_state_manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    layout = RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT)
    summary = run_rule_state_builder(layout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
