"""Materialize duration-episode evidence for the executable sub-checks.

Script 61 consumes script 50's sample-grain rule-state table and the
frozen calibration registry.  For every executable sub-check whose
verdict, pending, or pass semantics depend on sustained conditions, it
materializes same-side/threshold condition runs and opportunity runs as
explicit episodes (duration-episode grain), so that script 70 applies
the frozen persistence comparisons without re-deriving any mask or
reading canonical/production tables.

Sub-checks covered: 1-S2, 1-S3, 2-S2, 2-S3b, 3-S1a, 3-S1b, 4-S1,
5-S2, 5-S3.  Excluded by grain: 1-S1/1-S4/4-S2 (episode evidence in
script 50), 4-S3 (instantaneous physical range), 5-S1 (event evidence
in script 60).

Output (under ``proxy/61_duration_evidence/``):

- ``duration_episodes.csv`` — one row per episode.
- ``duration_evidence_manifest.json`` — stage manifest with the
  explicit evidence schema.

The frozen registry is loaded read-only; no threshold is fitted,
selected, or modified here.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.continuity import (  # noqa: E402
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
STAGE_ID = "61"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]


class DurationEvidenceContractError(RuntimeError):
    """Raised when script 61 inputs violate the frozen contract."""


def _verify_input(path: Path, expected_sha: str, *, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected_sha:
        raise DurationEvidenceContractError(
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
        raise DurationEvidenceContractError(
            "Registry online policy must be read-only with fitting "
            "disabled."
        )
    return registry


@dataclass(frozen=True)
class EpisodeSpec:
    """One episode family: AND of rule-state columns plus requirement."""

    rule_id: str
    episode_kind: str
    condition_columns: tuple[str, ...]
    required_seconds: float | None


def build_episode_specs(
    registry: dict[str, Any],
) -> tuple[EpisodeSpec, ...]:
    """Derive the frozen episode inventory from the registry."""

    rules = registry["proxy_rules"]

    def seconds(rule_id: str, *keys: str) -> float:
        node: Any = rules[rule_id]
        for key in keys:
            node = node[key]
        if isinstance(node, dict):
            node = node["value"]
        return float(node)

    specs: list[EpisodeSpec] = []
    tier_columns = {
        "high": "s1s2_exceed_high",
        "critical_provisional": "s1s2_exceed_critical",
    }
    tier_kinds = {
        "high": "exceed_high",
        "critical_provisional": "exceed_critical",
    }
    for tier in rules["1-S2"]["tiers"]:
        specs.append(EpisodeSpec(
            "1-S2", tier_kinds[tier["name"]],
            ("s1s2_eligible", tier_columns[tier["name"]]),
            float(tier["persistence"]["value"]),
        ))
    specs += [
        EpisodeSpec(
            "1-S2", "eligible", ("s1s2_eligible",),
            seconds("1-S2", "minimum_evaluable_seconds"),
        ),
        EpisodeSpec(
            "1-S3", "precursor",
            ("s1s3_eligible", "s1s3_precursor_condition"),
            seconds("1-S3", "persistence"),
        ),
        EpisodeSpec(
            "1-S3", "eligible", ("s1s3_eligible",),
            seconds("1-S3", "minimum_evaluable_seconds"),
        ),
        EpisodeSpec(
            "2-S2", "residual_low",
            ("s2s2_eligible", "s2s2_residual_low"),
            seconds("2-S2", "persistence"),
        ),
        EpisodeSpec("2-S2", "eligible", ("s2s2_eligible",), None),
        EpisodeSpec(
            "2-S3b", "zero_maf_firing",
            ("s2s3b_eligible", "s2s3b_zero_maf_firing"),
            seconds("2-S3b", "persistence"),
        ),
        EpisodeSpec("2-S3b", "eligible", ("s2s3b_eligible",), None),
        EpisodeSpec(
            "3-S1a", "residual_low",
            ("s3s1a_eligible", "s3s1a_residual_low"),
            seconds("3-S1a", "same_side_persistence"),
        ),
        EpisodeSpec(
            "3-S1a", "residual_high",
            ("s3s1a_eligible", "s3s1a_residual_high"),
            seconds("3-S1a", "same_side_persistence"),
        ),
        EpisodeSpec(
            "3-S1a", "eligible", ("s3s1a_eligible",),
            seconds("3-S1a", "same_side_persistence"),
        ),
        EpisodeSpec(
            "3-S1b", "extreme_delta",
            ("s3s1b_eligible", "s3s1b_extreme_delta"),
            seconds("3-S1b", "persistence"),
        ),
        EpisodeSpec("3-S1b", "eligible", ("s3s1b_eligible",), None),
        EpisodeSpec(
            "4-S1", "flat_under_context",
            ("s4s1_eligible", "s4s1_context_opportunity", "s4s1_flat"),
            seconds("4-S1", "persistence"),
        ),
        EpisodeSpec(
            "4-S1", "context_opportunity",
            ("s4s1_eligible", "s4s1_context_opportunity"),
            None,
        ),
        EpisodeSpec(
            "4-S1", "eligible", ("s4s1_eligible",),
            seconds("4-S1", "minimum_evaluable_seconds"),
        ),
        EpisodeSpec(
            "5-S2", "residual_low",
            ("s5s2_eligible", "s5s2_residual_low"),
            seconds("5-S2", "same_side_persistence"),
        ),
        EpisodeSpec(
            "5-S2", "residual_high",
            ("s5s2_eligible", "s5s2_residual_high"),
            seconds("5-S2", "same_side_persistence"),
        ),
        EpisodeSpec(
            "5-S2", "eligible", ("s5s2_eligible",),
            seconds("5-S2", "same_side_persistence"),
        ),
        EpisodeSpec(
            "5-S3", "flat_under_context",
            ("s5s3_eligible", "s5s3_context_opportunity", "s5s3_flat"),
            seconds("5-S3", "persistence"),
        ),
        EpisodeSpec(
            "5-S3", "context_opportunity",
            ("s5s3_eligible", "s5s3_context_opportunity"),
            None,
        ),
        EpisodeSpec(
            "5-S3", "eligible", ("s5s3_eligible",),
            seconds("5-S3", "minimum_evaluable_seconds"),
        ),
    ]
    return tuple(specs)


def required_rule_state_columns(
    specs: tuple[EpisodeSpec, ...],
) -> list[str]:
    columns: list[str] = list(KEYS) + ["continuity_block_id"]
    for spec in specs:
        for column in spec.condition_columns:
            if column not in columns:
                columns.append(column)
    return columns


def load_rule_state(
    layout: RunLayout, specs: tuple[EpisodeSpec, ...]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load and checksum-verify the script 50 rule-state input."""

    rule_state_manifest = load_json_object(layout.rule_state_manifest)
    _verify_input(
        layout.rule_state,
        rule_state_manifest["artifact_sha256"][
            "proxy/50_rule_state/rule_state.csv"
        ],
        label="rule_state.csv",
    )
    frame = pd.read_csv(
        layout.rule_state,
        usecols=required_rule_state_columns(specs),
        low_memory=False,
    )
    return frame, {
        "source_dataset_identity": (
            rule_state_manifest["source_dataset_identity"]
        ),
    }


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype("boolean").fillna(False).astype(bool)


def build_duration_episodes(
    frame: pd.DataFrame,
    registry: dict[str, Any],
) -> pd.DataFrame:
    """Materialize every episode family (duration-episode grain)."""

    specs = build_episode_specs(registry)
    blocks = frame["continuity_block_id"]
    pieces: list[pd.DataFrame] = []
    for spec in specs:
        condition = pd.Series(True, index=frame.index, dtype=bool)
        for column in spec.condition_columns:
            condition &= _as_bool(frame[column])
        run_ids = build_true_run_ids(condition, blocks)
        mask = run_ids.notna()
        if not mask.any():
            continue
        sub = frame.loc[mask, KEYS + ["continuity_block_id"]].copy()
        sub["_run"] = run_ids[mask]
        grouped = sub.groupby("_run", sort=False)
        episodes = grouped.agg(
            trip_id=("trip_id", "first"),
            segment_id=("segment_id", "first"),
            continuity_block_id=("continuity_block_id", "first"),
            start_timestamp=("timestamp", "first"),
            end_timestamp=("timestamp", "last"),
            start_row_in_segment=("row_in_segment", "first"),
            end_row_in_segment=("row_in_segment", "last"),
            sample_count=("timestamp", "size"),
        ).reset_index(drop=True)
        episodes.insert(0, "rule_id", spec.rule_id)
        episodes.insert(1, "episode_kind", spec.episode_kind)
        episodes["duration_seconds"] = (
            episodes["sample_count"].astype(float)
        )
        episodes["elapsed_span_seconds"] = (
            episodes["sample_count"].astype(float) - 1.0
        )
        if spec.required_seconds is None:
            episodes["persistence_required_s"] = pd.Series(
                pd.NA, index=episodes.index, dtype="Float64"
            )
            episodes["meets_persistence"] = pd.Series(
                pd.NA, index=episodes.index, dtype="boolean"
            )
            episodes["margin_seconds"] = pd.Series(
                pd.NA, index=episodes.index, dtype="Float64"
            )
        else:
            episodes["persistence_required_s"] = pd.Series(
                float(spec.required_seconds), index=episodes.index,
                dtype="Float64",
            )
            episodes["meets_persistence"] = (
                episodes["duration_seconds"]
                .ge(spec.required_seconds)
                .astype("boolean")
            )
            episodes["margin_seconds"] = (
                episodes["duration_seconds"] - spec.required_seconds
            ).astype("Float64")
        episodes["episode_index"] = range(1, len(episodes) + 1)
        pieces.append(episodes)

    if not pieces:
        columns = [
            "rule_id", "episode_kind", "trip_id", "segment_id",
            "continuity_block_id", "start_timestamp", "end_timestamp",
            "start_row_in_segment", "end_row_in_segment",
            "sample_count", "duration_seconds", "elapsed_span_seconds",
            "persistence_required_s", "meets_persistence",
            "margin_seconds", "episode_index",
        ]
        return pd.DataFrame(columns=columns)
    return pd.concat(pieces, ignore_index=True)


def _column_names(frame: pd.DataFrame) -> list[str]:
    return [str(column) for column in frame.columns]


def run_duration_evidence_builder(
    layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> dict[str, Any]:
    """Execute script 61 and write the output plus the manifest."""

    registry = load_registry(layout)
    specs = build_episode_specs(registry)
    frame, meta = load_rule_state(layout, specs)

    episodes = build_duration_episodes(frame, registry)

    layout.duration_evidence_dir.mkdir(parents=True, exist_ok=True)
    episodes.to_csv(
        layout.duration_episodes, index=False, float_format="%.15g",
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
            run_descriptor(layout.rule_state, "rule_state"),
            registry_descriptor,
        ],
        output_artifacts=[
            run_descriptor(layout.duration_episodes, "duration_episodes"),
        ],
        calibration_version=registry["calibration_version"],
        creation_time_utc=creation_time_utc,
    )
    episode_counts = {
        f"{spec.rule_id}:{spec.episode_kind}": int(
            (
                (episodes["rule_id"] == spec.rule_id)
                & (episodes["episode_kind"] == spec.episode_kind)
            ).sum()
        )
        for spec in specs
    }
    manifest["evidence_schema"] = {
        "duration_episodes": {
            "grain": "duration_episode",
            "ordered_columns": _column_names(episodes),
            "row_count": len(episodes),
        },
        "episode_semantics": {
            "episode_definition": (
                "maximal run of consecutive 1 Hz samples inside one "
                "continuity block where every condition column is "
                "true; a null (ineligible) or false sample breaks the "
                "run on both sides, and episodes never cross "
                "continuity blocks"
            ),
            "duration_convention": (
                "duration_seconds equals sample_count (N consecutive "
                "samples = N seconds at 1 Hz), matching script 50's "
                "frozen persistence-mask semantics; "
                "elapsed_span_seconds = sample_count - 1 is also "
                "recorded for span-convention consumers"
            ),
            "requirement": (
                "persistence_required_s comes from the frozen "
                "registry (tier/persistence/same_side_persistence for "
                "condition kinds; minimum_evaluable_seconds or the "
                "frozen opportunity length for eligible kinds); "
                "meets_persistence and margin_seconds are null where "
                "the registry defines no duration requirement for "
                "that kind"
            ),
            "episode_inventory": {
                f"{spec.rule_id}:{spec.episode_kind}": list(
                    spec.condition_columns
                )
                for spec in specs
            },
        },
        "episode_counts": episode_counts,
    }
    validate_stage_manifest(manifest)
    write_json_atomic(layout.duration_evidence_manifest, manifest)
    return {
        "episode_rows": len(episodes),
        "manifest": layout.run_relative_posix(
            layout.duration_evidence_manifest
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    layout = RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT)
    summary = run_duration_evidence_builder(layout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
