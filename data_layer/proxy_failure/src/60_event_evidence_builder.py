"""Materialize pedal-step event evidence for sub-check 5-S1.

Script 60 consumes the validated production feature handoff, per-signal
cleaning quality, script 50's rule-state continuity blocks, and the
frozen calibration registry.  It detects driver-demand pedal steps
inside the frozen 5-S1 domain, applies the event-validity neighborhood
gate, computes the MAP response and per (state x magnitude-bin)
no-response label, and maintains the per-trip rolling window counts
that script 70 consumes for the 3-of-4 verdict — so that script 70
never reads canonical or production-feature tables directly.

Output (under ``proxy/60_event_evidence/``):

- ``pedal_step_events.csv`` — one row per detected event (event grain).
- ``event_evidence_manifest.json`` — stage manifest with the explicit
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
    build_quality_valid_mask,
    strict_event_neighborhood_mask,
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
STAGE_ID = "60"
RULE_ID = "5-S1"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]


class EventEvidenceContractError(RuntimeError):
    """Raised when script 60 inputs violate the frozen contract."""


def _verify_input(path: Path, expected_sha: str, *, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected_sha:
        raise EventEvidenceContractError(
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
        raise EventEvidenceContractError(
            "Registry online policy must be read-only with fitting "
            "disabled."
        )
    return registry


def load_inputs(layout: RunLayout) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load and checksum-verify production, quality, rule-state inputs."""

    production_manifest = load_json_object(
        layout.production_feature_manifest
    )
    recorded = production_manifest["artifact_sha256"]
    _verify_input(
        layout.production_features,
        recorded["features/41_production/production_features.csv"],
        label="production_features.csv",
    )
    rule_state_manifest = load_json_object(layout.rule_state_manifest)
    _verify_input(
        layout.rule_state,
        rule_state_manifest["artifact_sha256"][
            "proxy/50_rule_state/rule_state.csv"
        ],
        label="rule_state.csv",
    )

    production = pd.read_csv(layout.production_features, low_memory=False)
    quality = pd.read_csv(layout.cleaning_quality, low_memory=False)
    blocks = pd.read_csv(
        layout.rule_state,
        usecols=KEYS + ["continuity_block_id"],
        low_memory=False,
    )

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
    merged = merged.merge(
        blocks, on=KEYS, how="left", validate="one_to_one",
    )
    if len(merged) != len(production):
        raise EventEvidenceContractError(
            "Quality or rule-state join changed the sample row count."
        )
    if merged[flag_columns].isna().any().any():
        raise EventEvidenceContractError(
            "Every sample must carry per-signal quality flags."
        )
    return merged, {
        "source_dataset_identity": (
            production_manifest["source_dataset_identity"]
        ),
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


def _lookup(
    parameters: dict[str, Any], path: tuple[str, ...]
) -> "dict[str, float | None]":
    """Per-operating-state numeric lookup from the registry node."""
    values: dict[str, float | None] = {}
    for state, node in parameters.items():
        value: Any = node
        for key in path:
            value = value[key]
        if isinstance(value, dict):
            value = value.get("raw_value", value.get("value"))
        values[state] = None if value is None else float(value)
    return values


def build_pedal_step_events(
    frame: pd.DataFrame,
    registry: dict[str, Any],
    *,
    quality_cache: "_QualityMaskCache | None" = None,
) -> pd.DataFrame:
    """Detect, validate, and label pedal-step events (event grain)."""

    rule = registry["proxy_rules"][RULE_ID]
    guards = rule["guards"]
    parameters = rule["state_parameters"]
    offsets = [int(value) for value in rule["event_offsets_seconds"]]
    response_offsets = [
        int(value) for value in rule["response_offsets_seconds"]
    ]
    before = -min(offsets)
    after = max(offsets)
    baseline_offset = min(offsets)
    m_required = int(rule["m_of_n"]["m"])
    n_window = int(rule["m_of_n"]["n"])

    q = quality_cache or _QualityMaskCache(frame)
    required = list(guards["required_quality_valid_signals"])
    quality_valid = q(*required)

    domain = (
        frame["thermal_state"].eq(guards["thermal_state"])
        & frame["condition_confidence"].eq(
            guards["condition_confidence"])
        & quality_valid
    )

    step_thresholds = _lookup(
        parameters, ("pedal_step_threshold", "value"))
    split_thresholds = _lookup(
        parameters, ("magnitude_split", "value"))
    lo_thresholds = _lookup(
        parameters, ("no_response_threshold_kpa", "bin_lo"))
    hi_thresholds = _lookup(
        parameters, ("no_response_threshold_kpa", "bin_hi"))

    state = frame["operating_state"]
    step_threshold = state.map(step_thresholds)
    detected = domain & frame["pedal_slope"].ge(step_threshold)

    blocks = frame["continuity_block_id"]
    neighborhood_in_block = strict_event_neighborhood_mask(
        blocks, before_samples=before, after_samples=after,
    )
    neighborhood_quality = quality_valid.copy()
    for offset in offsets:
        if offset:
            neighborhood_quality &= (
                quality_valid.astype("boolean").shift(-offset)
                .fillna(False).astype(bool)
            )
    window_complete = detected & neighborhood_in_block & neighborhood_quality

    baseline_map = frame["map"].shift(-baseline_offset)
    response = pd.concat(
        [
            (frame["map"].shift(-offset) - baseline_map).abs()
            for offset in response_offsets
        ],
        axis=1,
    ).max(axis=1)

    split_threshold = state.map(split_thresholds)
    high_bin = frame["pedal_slope"].ge(split_threshold)
    magnitude_bin = high_bin.map({True: "hi", False: "lo"})
    no_response_threshold = pd.Series(
        pd.NA, index=frame.index, dtype="Float64"
    )
    no_response_threshold[high_bin] = state[high_bin].map(hi_thresholds)
    no_response_threshold[~high_bin] = state[~high_bin].map(lo_thresholds)

    events = frame.loc[detected, KEYS].copy()
    events["continuity_block_id"] = blocks[detected]
    events["operating_state"] = state[detected]
    events["pedal_slope"] = frame.loc[detected, "pedal_slope"]
    events["pedal_step_threshold"] = step_threshold[detected]
    events["magnitude_bin"] = magnitude_bin[detected]
    events["magnitude_split_threshold"] = split_threshold[detected]
    events["window_complete"] = window_complete[detected]
    reason = pd.Series(pd.NA, index=events.index, dtype="string")
    outside = detected & ~neighborhood_in_block
    quality_fail = (
        detected & neighborhood_in_block & ~neighborhood_quality
    )
    reason[outside[detected]] = "neighborhood_outside_block"
    reason[quality_fail[detected]] = "neighborhood_quality"
    events["window_incomplete_reason"] = reason
    events["baseline_map"] = (
        baseline_map[detected].where(window_complete[detected])
    )
    events["response_kpa"] = (
        response[detected].where(window_complete[detected])
    )
    events["no_response_threshold_kpa"] = (
        no_response_threshold[detected].astype("Float64")
    )
    events["evaluable"] = (
        events["window_complete"]
        & events["no_response_threshold_kpa"].notna()
    )

    result = pd.Series(pd.NA, index=events.index, dtype="string")
    result[events["window_complete"] & ~events["evaluable"]] = (
        "not_evaluable"
    )
    is_no_response = (
        events["evaluable"]
        & events["response_kpa"].lt(events["no_response_threshold_kpa"])
    )
    result[events["evaluable"] & is_no_response] = "no_response"
    result[events["evaluable"] & ~is_no_response] = "response"
    events["event_result"] = result

    events["event_index_in_trip"] = (
        events.groupby("trip_id", sort=False).cumcount() + 1
    )

    complete_events = events[events["window_complete"]]
    ordinal = (
        complete_events.groupby("trip_id", sort=False).cumcount() + 1
    )
    no_response_flag = (
        complete_events["event_result"].eq("no_response").astype(float)
    )
    rolling_count = (
        no_response_flag.groupby(complete_events["trip_id"], sort=False)
        .rolling(window=n_window, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )
    window_size = ordinal.clip(upper=n_window)

    events["complete_event_ordinal"] = pd.Series(
        ordinal, index=complete_events.index
    ).reindex(events.index).astype("Int64")
    events["recent_window_size"] = pd.Series(
        window_size, index=complete_events.index
    ).reindex(events.index).astype("Int64")
    events["no_response_count_recent_n"] = (
        rolling_count.reindex(events.index).astype("Int64")
    )
    events["m_of_n_triggered"] = (
        events["no_response_count_recent_n"].ge(m_required)
        .astype("boolean")
        .where(events["window_complete"])
    )
    events["decision_margin"] = (
        events["no_response_count_recent_n"] - m_required
    ).astype("Int64")

    return events.reset_index(drop=True)


def _column_names(frame: pd.DataFrame) -> list[str]:
    return [str(column) for column in frame.columns]


def run_event_evidence_builder(
    layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> dict[str, Any]:
    """Execute script 60 and write the output plus the manifest."""

    registry = load_registry(layout)
    frame, meta = load_inputs(layout)

    events = build_pedal_step_events(frame, registry)

    layout.event_evidence_dir.mkdir(parents=True, exist_ok=True)
    events.to_csv(
        layout.pedal_step_events, index=False, float_format="%.15g",
        lineterminator="\n",
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
            run_descriptor(layout.rule_state, "rule_state"),
            registry_descriptor,
        ],
        output_artifacts=[
            run_descriptor(layout.pedal_step_events, "pedal_step_events"),
        ],
        calibration_version=registry["calibration_version"],
        creation_time_utc=creation_time_utc,
    )
    rule = registry["proxy_rules"][RULE_ID]
    manifest["evidence_schema"] = {
        "pedal_step_events": {
            "grain": "pedal_step_event",
            "ordered_columns": _column_names(events),
            "row_count": len(events),
        },
        "event_semantics": {
            "rule_id": RULE_ID,
            "detection": (
                "one row per sample inside the frozen 5-S1 domain "
                "(post_warmup, high confidence, quality-valid "
                "map/rpm/accel_pedal_d/accel_pedal_e) whose "
                "pedal_slope meets the per-operating-state frozen "
                "step threshold"
            ),
            "window_completeness": (
                "window_complete requires the full t0-1..t0+2 "
                "neighborhood in one continuity block with every "
                "neighborhood sample quality-valid; incomplete events "
                "carry window_incomplete_reason and never enter the "
                "rolling window. This is a structural gate on whether "
                "the response can be measured at all, distinct from "
                "evaluable below."
            ),
            "response": (
                "max abs(map[t] - map[t0-1]) over t0..t0+2; "
                "no_response when response < the frozen per "
                "(state x magnitude-bin) threshold; "
                "steady_driving bin_lo is non-separable and yields "
                "event_result = not_evaluable"
            ),
            "evaluable": (
                "window_complete AND the event's (state x magnitude-bin) "
                "has a defined no_response_threshold_kpa (excludes the "
                "non-separable steady_driving low bin). This is the "
                "column that corresponds to 'valid events' as used in "
                "proxy_support.md's 5-S1 calibration evidence (942/1176) "
                "-- not window_complete, which is a near-100% structural "
                "gate on this dataset's clean quality flags."
            ),
            "rolling_window": (
                "per trip, over window_complete events in time order: "
                "no_response_count_recent_n counts no_response "
                "results among the trip's most recent "
                f"{rule['m_of_n']['n']} window_complete events "
                "(not_evaluable events occupy window slots but never "
                "count); "
                f"m_of_n_triggered = count >= {rule['m_of_n']['m']}; "
                "decision_margin = count - "
                f"{rule['m_of_n']['m']}"
            ),
        },
    }
    validate_stage_manifest(manifest)
    write_json_atomic(layout.event_evidence_manifest, manifest)
    return {
        "event_rows": len(events),
        "window_complete_events": int(events["window_complete"].sum()),
        "evaluable_events": int(events["evaluable"].sum()),
        "manifest": layout.run_relative_posix(
            layout.event_evidence_manifest
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    layout = RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT)
    summary = run_event_evidence_builder(layout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
