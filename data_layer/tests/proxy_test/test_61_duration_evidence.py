"""Contract tests for script 61 duration-episode evidence."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.manifests import (  # noqa: E402
    load_json_object,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


def _load_script61():
    path = (
        REPO_ROOT
        / "data_layer/proxy_failure/src/61_duration_evidence_builder.py"
    )
    spec = importlib.util.spec_from_file_location("script61", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["script61"] = module
    spec.loader.exec_module(module)
    return module


script61 = _load_script61()
REGISTRY = load_json_object(
    RunLayout.for_run_id("t", repo_root=REPO_ROOT).calibration_registry
)

CONDITION_COLUMNS = sorted({
    column
    for spec in script61.build_episode_specs(REGISTRY)
    for column in spec.condition_columns
})


def make_frame(n: int = 400) -> pd.DataFrame:
    start = pd.Timestamp("2026-07-19T10:00:00Z")
    frame = pd.DataFrame(
        {
            "timestamp": [
                (start + pd.Timedelta(seconds=i)).isoformat()
                for i in range(n)
            ],
            "trip_id": "T1",
            "segment_id": "T1-S1",
            "row_in_segment": range(n),
            "continuity_block_id": 1.0,
        }
    )
    for column in CONDITION_COLUMNS:
        frame[column] = pd.Series(False, index=frame.index,
                                  dtype="boolean")
    return frame


def build(frame: pd.DataFrame) -> pd.DataFrame:
    return script61.build_duration_episodes(frame, REGISTRY)


def pick(episodes, rule_id, kind):
    return episodes[
        (episodes["rule_id"] == rule_id)
        & (episodes["episode_kind"] == kind)
    ].reset_index(drop=True)


def test_episode_inventory_covers_all_duration_gated_rules() -> None:
    specs = script61.build_episode_specs(REGISTRY)
    rule_ids = {spec.rule_id for spec in specs}
    assert rule_ids == {
        "1-S2", "1-S3", "2-S2", "2-S3b", "3-S1a", "3-S1b",
        "4-S1", "5-S2", "5-S3",
    }
    frozen = {
        ("1-S2", "exceed_high"): 180.0,
        ("1-S2", "exceed_critical"): 30.0,
        ("1-S3", "precursor"): 180.0,
        ("2-S2", "residual_low"): 10.0,
        ("2-S3b", "zero_maf_firing"): 10.0,
        ("3-S1a", "residual_low"): 30.0,
        ("3-S1a", "residual_high"): 30.0,
        ("3-S1b", "extreme_delta"): 2.0,
        ("4-S1", "flat_under_context"): 120.0,
        ("5-S2", "residual_low"): 30.0,
        ("5-S2", "residual_high"): 30.0,
        ("5-S3", "flat_under_context"): 120.0,
    }
    by_key = {
        (spec.rule_id, spec.episode_kind): spec.required_seconds
        for spec in specs
    }
    for key, value in frozen.items():
        assert by_key[key] == value


def test_condition_run_boundaries_and_margin() -> None:
    frame = make_frame()
    frame.loc[10:24, "s2s2_eligible"] = True
    frame.loc[12:21, "s2s2_residual_low"] = True

    episodes = build(frame)
    runs = pick(episodes, "2-S2", "residual_low")

    assert len(runs) == 1
    run = runs.iloc[0]
    assert run["start_row_in_segment"] == 12
    assert run["end_row_in_segment"] == 21
    assert run["sample_count"] == 10
    assert run["duration_seconds"] == 10.0
    assert run["elapsed_span_seconds"] == 9.0
    assert run["persistence_required_s"] == 10.0
    assert run["meets_persistence"]
    assert run["margin_seconds"] == 0.0


def test_ineligible_or_null_sample_breaks_the_run() -> None:
    frame = make_frame()
    frame.loc[10:29, "s2s2_eligible"] = True
    frame.loc[10:29, "s2s2_residual_low"] = True
    frame.loc[20, "s2s2_eligible"] = False
    frame.loc[24, "s2s2_residual_low"] = pd.NA

    episodes = build(frame)
    runs = pick(episodes, "2-S2", "residual_low")

    assert list(runs["start_row_in_segment"]) == [10, 21, 25]
    assert list(runs["sample_count"]) == [10, 3, 5]
    assert list(runs["meets_persistence"]) == [True, False, False]


def test_episodes_never_cross_continuity_blocks() -> None:
    frame = make_frame()
    frame.loc[10:29, "s3s1b_eligible"] = True
    frame.loc[10:29, "s3s1b_extreme_delta"] = True
    frame.loc[frame.index >= 20, "continuity_block_id"] = 2.0

    episodes = build(frame)
    runs = pick(episodes, "3-S1b", "extreme_delta")

    assert list(runs["start_row_in_segment"]) == [10, 20]
    assert list(runs["sample_count"]) == [10, 10]
    assert list(runs["continuity_block_id"]) == [1.0, 2.0]


def test_joint_context_flat_episode_requires_all_columns() -> None:
    frame = make_frame()
    frame.loc[10:300, "s5s3_eligible"] = True
    frame.loc[50:250, "s5s3_context_opportunity"] = True
    frame.loc[100:180, "s5s3_flat"] = True

    episodes = build(frame)

    joint = pick(episodes, "5-S3", "flat_under_context")
    assert len(joint) == 1
    assert joint.loc[0, "start_row_in_segment"] == 100
    assert joint.loc[0, "sample_count"] == 81
    assert not joint.loc[0, "meets_persistence"]
    assert joint.loc[0, "margin_seconds"] == -39.0

    context = pick(episodes, "5-S3", "context_opportunity")
    assert len(context) == 1
    assert context.loc[0, "sample_count"] == 201

    eligible = pick(episodes, "5-S3", "eligible")
    assert len(eligible) == 1
    assert eligible.loc[0, "sample_count"] == 291
    assert eligible.loc[0, "persistence_required_s"] == 240.0
    assert eligible.loc[0, "meets_persistence"]


def test_kinds_without_frozen_requirement_carry_nulls() -> None:
    frame = make_frame()
    frame.loc[10:60, "s2s3b_eligible"] = True

    episodes = build(frame)
    runs = pick(episodes, "2-S3b", "eligible")

    assert len(runs) == 1
    assert pd.isna(runs.loc[0, "persistence_required_s"])
    assert pd.isna(runs.loc[0, "meets_persistence"])
    assert pd.isna(runs.loc[0, "margin_seconds"])


def test_two_sided_residuals_stay_same_side() -> None:
    frame = make_frame()
    frame.loc[10:99, "s5s2_eligible"] = True
    frame.loc[20:54, "s5s2_residual_low"] = True
    frame.loc[60:94, "s5s2_residual_high"] = True

    episodes = build(frame)

    low = pick(episodes, "5-S2", "residual_low")
    high = pick(episodes, "5-S2", "residual_high")
    assert len(low) == 1 and len(high) == 1
    assert low.loc[0, "sample_count"] == 35
    assert high.loc[0, "sample_count"] == 35
    assert low.loc[0, "meets_persistence"]
    assert high.loc[0, "meets_persistence"]
    assert low.loc[0, "margin_seconds"] == 5.0


def test_empty_frame_yields_empty_typed_output() -> None:
    frame = make_frame(50)

    episodes = build(frame)

    assert episodes.empty
    assert "rule_id" in episodes.columns
    assert "meets_persistence" in episodes.columns


def test_determinism_under_row_shuffle() -> None:
    frame = make_frame()
    frame.loc[10:24, "s2s2_eligible"] = True
    frame.loc[12:21, "s2s2_residual_low"] = True
    frame.loc[30:80, "s1s2_eligible"] = True
    frame.loc[40:75, "s1s2_exceed_critical"] = True

    baseline = build(frame)
    shuffled = (
        frame.sample(frac=1.0, random_state=7)
        .sort_values(["trip_id", "segment_id", "row_in_segment"])
        .reset_index(drop=True)
    )
    again = build(shuffled)

    pd.testing.assert_frame_equal(baseline, again)
