"""Deterministically slice the tracked schema-v1 production fixture."""
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
from data_layer.pipeline_data.manifests import (  # noqa: E402
    load_json_object,
    ordered_column_contract_from_feature_manifest,
    sha256_file,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

FIXTURE_CSV = HERE / "production_features.v1.fixture.csv"
FIXTURE_MANIFEST = HERE / "production_features.v1.fixture.manifest.json"
EPISODE_ID = "trip_0061_start_002"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
BOUNDARY_KEY = {
    "timestamp": "2017-07-05T17:17:19Z",
    "trip_id": "trip_0002",
    "segment_id": "trip_0002_seg_001",
    "row_in_segment": 1,
}
RAW = [
    "coolant_temp", "map", "rpm", "speed", "intake_temp", "maf", "tps",
    "ambient_temp", "accel_pedal_d", "accel_pedal_e",
]


def _key(row: pd.Series) -> dict[str, Any]:
    return {
        **{name: str(row[name]) for name in KEYS[:3]},
        "row_in_segment": int(row["row_in_segment"]),
    }


def generate_fixture(
    layout: RunLayout,
    *,
    output_csv: Path = FIXTURE_CSV,
    output_manifest: Path = FIXTURE_MANIFEST,
):
    source_manifest = load_json_object(layout.production_feature_manifest)
    verify_manifest_artifacts(
        source_manifest, run_dir=layout.run_dir, repo_root=layout.repo_root
    )
    contract = load_json_object(layout.feature_contract)
    fields = [
        dict(x)
        for x in ordered_column_contract_from_feature_manifest(contract)
    ]
    columns = [x["name"] for x in fields]
    production = pd.read_csv(layout.production_features, low_memory=False)
    if list(production.columns) != columns:
        raise ValueError(
            "Source production CSV violates the frozen column contract.")
    episodes = pd.read_csv(layout.engine_start_episodes, low_memory=False)
    episode = episodes[episodes.engine_start_episode_id.eq(EPISODE_ID)]
    indexes = production.index[
        production.engine_start_episode_id.eq(EPISODE_ID)
    ].tolist()
    expected_episode_rows = (
        int(episode.iloc[0].episode_sample_count)
        if len(episode) == 1
        else None
    )
    if len(episode) != 1 or len(indexes) != expected_episode_rows:
        raise ValueError("The fixed source episode is missing or incomplete.")
    chosen = set(indexes + [min(indexes) - 1, max(indexes) + 1])
    mask = pd.Series(True, index=production.index)
    for name, value in BOUNDARY_KEY.items():
        mask &= production[name].eq(value)
    boundary_indexes = production.index[mask].tolist()
    if len(boundary_indexes) != 1:
        raise ValueError(
            "The fixed boundary witness is missing or duplicated.")
    chosen.add(boundary_indexes[0])
    fixture = production.loc[sorted(chosen)].sort_values(
        KEYS, kind="stable").reset_index(drop=True)
    if len(fixture) > 300:
        raise ValueError("Fixture exceeds the few-hundred-row limit.")

    flags = [
        "is_imputed_any", "is_suspicious_any", "had_hard_invalid_source_any",
    ]
    quality = pd.read_csv(layout.cleaning_quality, low_memory=False)
    joined = fixture[KEYS + RAW].merge(
        quality[KEYS + flags], on=KEYS, how="left", validate="one_to_one"
    )
    invalid = (
        joined[flags].fillna(True).astype(bool).any(axis=1)
        | joined[RAW].isna().any(axis=1)
    )
    if not invalid.any() or not (~invalid).any():
        raise ValueError(
            "Both quality-valid and quality-invalid rows are required.")
    if not fixture.maf_integral_180s.notna().any():
        raise ValueError("A complete MAF window is required.")
    if not fixture[
        ["accel_pedal_d", "accel_pedal_e"]
    ].isna().any(axis=1).any():
        raise ValueError("A missing pedal-channel row is required.")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fixture.to_csv(
        output_csv, index=False, float_format="%.15g", lineterminator="\n"
    )
    outside = fixture[fixture.engine_start_episode_id.isna()].iloc[0]
    incomplete = fixture[
        fixture.engine_start_episode_id.eq(EPISODE_ID)
        & fixture.maf_integral_180s.isna()
    ].iloc[0]
    complete = fixture[fixture.maf_integral_180s.notna()].iloc[0]
    pedal_null = fixture[
        fixture[["accel_pedal_d", "accel_pedal_e"]].isna().any(axis=1)
    ].iloc[0]
    expected_count = int(episode.iloc[0].episode_sample_count)
    production_features_path = layout.run_relative_posix(
        layout.production_features
    )
    production_manifest_path = layout.run_relative_posix(
        layout.production_feature_manifest
    )
    manifest = {
        "manifest_type": "production_feature_fixture_manifest",
        "manifest_version": "1.0.0",
        "schema_version": "feature_schema.v1",
        "calibration_version": "calibration.v1",
        "row_count": len(fixture),
        "fixture_artifact": {
            "path": output_csv.name,
            "sha256": sha256_file(output_csv),
            "size_bytes": output_csv.stat().st_size,
        },
        "ordered_column_contract": fields,
        "source_provenance": {
            "run_id": layout.run_id,
            "source_dataset_identity": (
                source_manifest["source_dataset_identity"]
            ),
            "production_features_path": production_features_path,
            "production_features_sha256": sha256_file(
                layout.production_features
            ),
            "production_manifest_path": production_manifest_path,
            "production_manifest_sha256": sha256_file(
                layout.production_feature_manifest
            ),
        },
        "selection_policy": {
            "algorithm": (
                "fixed_complete_episode_plus_neighbors_and_boundary_witness"
            ),
            "engine_start_episode_id": EPISODE_ID,
            "include_full_episode": True,
            "include_immediate_global_neighbors": True,
            "additional_fixed_sample_key": BOUNDARY_KEY,
            "final_order": KEYS,
        },
        "coverage": {
            "complete_engine_start_episode": {
                "episode_id": EPISODE_ID,
                "source_episode_sample_count": expected_count,
                "fixture_episode_sample_count": int(
                    fixture.engine_start_episode_id.eq(EPISODE_ID).sum()
                ),
                "termination_reason": str(episode.iloc[0].termination_reason),
            },
            "episode_outside_sample": _key(outside),
            "segment_first_with_gap": BOUNDARY_KEY,
            "incomplete_window_sample": _key(incomplete),
            "complete_maf_window_sample": _key(complete),
            "missing_pedal_channel_sample": _key(pedal_null),
            "quality_valid_sample": _key(fixture.loc[(~invalid).idxmax()]),
            "quality_invalid_samples": [
                _key(fixture.loc[i]) for i in invalid.index[invalid]
            ],
        },
    }
    write_json_atomic(output_manifest, manifest)
    return fixture, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-csv", type=Path, default=FIXTURE_CSV)
    parser.add_argument(
        "--output-manifest", type=Path, default=FIXTURE_MANIFEST
    )
    args = parser.parse_args()
    fixture, manifest = generate_fixture(
        RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT),
        output_csv=args.output_csv.resolve(),
        output_manifest=args.output_manifest.resolve(),
    )
    print(json.dumps({
        "rows": len(fixture),
        "sha256": manifest["fixture_artifact"]["sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
