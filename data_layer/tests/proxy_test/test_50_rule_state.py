"""Contract tests for script 50 rule-state materialization."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.manifests import (  # noqa: E402
    load_json_object,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


def _load_script50():
    path = (
        REPO_ROOT
        / "data_layer/proxy_failure/src/50_rule_state_builder.py"
    )
    spec = importlib.util.spec_from_file_location("script50", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script50 = _load_script50()
REGISTRY = load_json_object(
    RunLayout.for_run_id("t", repo_root=REPO_ROOT).calibration_registry
)

SIGNALS = [
    "coolant_temp", "map", "rpm", "speed", "intake_temp", "maf", "tps",
    "ambient_temp", "accel_pedal_d", "accel_pedal_e",
]
FEATURES = [
    "segment_gap_seconds", "engine_on_flag", "coolant_ambient_delta",
    "intake_ambient_delta", "accel_pedal_mean",
    "accel_pedal_channel_delta", "pedal_slope", "rpm_slope",
    "speed_density_maf_residual", "pedal_mapping_residual",
    "engine_start_observed", "engine_start_episode_id",
    "elapsed_since_engine_start", "ect_start", "aat_start", "iat_start",
    "maf_integral_180s", "ect_rate_180s", "intake_temp_stability",
    "speed_std_120s", "maf_std_120s", "rpm_std_120s",
    "accel_pedal_mean_std_120s", "map_range_60s",
]


def make_frame(n: int = 40) -> pd.DataFrame:
    """A quality-valid post-warm-up baseline sequence in one segment."""

    frame = pd.DataFrame({
        "timestamp": pd.date_range(
            "2026-01-01T08:00:00Z", periods=n, freq="1s"
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trip_id": "trip_0001",
        "segment_id": "trip_0001_seg_001",
        "row_in_segment": range(1, n + 1),
    })
    frame["thermal_state"] = "post_warmup"
    frame["child_state"] = "steady_driving"
    frame["operating_state"] = "post_warmup__steady_driving"
    frame["condition_confidence"] = "high"
    frame["condition_quality_flags"] = "OK"
    frame["dt_seconds"] = 1.0
    defaults = {
        "coolant_temp": 90.0, "map": 100.0, "rpm": 1500.0,
        "speed": 60.0, "intake_temp": 20.0, "maf": 15.0, "tps": 20.0,
        "ambient_temp": 15.0, "accel_pedal_d": 15.0,
        "accel_pedal_e": 15.4,
    }
    for name, value in defaults.items():
        frame[name] = value
    for feature in FEATURES:
        frame[feature] = pd.NA
    frame["pedal_slope"] = 0.0
    frame["rpm_slope"] = 0.0
    frame["speed_density_maf_residual"] = 1.0
    frame["pedal_mapping_residual"] = 0.0
    frame["accel_pedal_channel_delta"] = 0.4
    frame["engine_start_observed"] = False
    for signal in SIGNALS:
        frame[f"{signal}_is_imputed"] = False
        frame[f"{signal}_is_suspicious"] = False
        frame[f"{signal}_had_hard_invalid_source"] = False
    return frame


def test_masks_require_registry_persistence() -> None:
    frame = make_frame(12)
    state = script50.build_rule_state(frame, REGISTRY)

    # steady mask needs >= 10 consecutive seconds.
    assert not state["steady_state_mask"].iloc[:9].any()
    assert state["steady_state_mask"].iloc[9:].all()
    # low-motion mask needs >= 3 consecutive seconds.
    assert not state["pedal_lowmotion_mask"].iloc[:2].any()
    assert state["pedal_lowmotion_mask"].iloc[2:].all()


def test_quality_invalid_sample_breaks_masks_and_conditions() -> None:
    frame = make_frame(25)
    frame.loc[12, "rpm_is_suspicious"] = True
    state = script50.build_rule_state(frame, REGISTRY)

    assert not state["steady_state_mask"].iloc[12]
    # run restarts after the invalid sample: needs 10 fresh samples.
    assert not state["steady_state_mask"].iloc[13:22].any()
    assert state["steady_state_mask"].iloc[22:].all()
    # 2-S3b needs valid MAF and RPM.
    assert not state["s2s3b_eligible"].iloc[12]


def test_conditions_are_null_when_not_eligible() -> None:
    frame = make_frame(10)
    frame["thermal_state"] = "warmup"
    frame["operating_state"] = "warmup__steady_driving"
    state = script50.build_rule_state(frame, REGISTRY)

    assert state["s1s2_eligible"].eq(False).all()
    assert state["s1s2_exceed_high"].isna().all()
    assert state["s2s2_eligible"].eq(False).all()
    assert state["s2s2_residual_low"].isna().all()


def test_threshold_boundaries_follow_frozen_operators() -> None:
    frame = make_frame(30)
    frame["coolant_temp"] = 105.0        # >= 105 -> exceed high
    frame["intake_temp"] = 216.0         # > 215 -> above range
    frame.loc[frame.index[:15], "maf"] = 0.0
    frame.loc[frame.index[:15], "rpm"] = 500.0   # >= 500 with maf == 0
    state = script50.build_rule_state(frame, REGISTRY)

    assert state["s1s2_exceed_high"].fillna(False).all()
    assert state["s4s3_above_range"].fillna(False).all()
    assert state["s2s3b_zero_maf_firing"].iloc[0]
    assert not state["s2s3b_zero_maf_firing"].iloc[20]


def test_cold_start_first_row_evidence_and_reasons() -> None:
    frame = make_frame(30)
    # Segment first row: engine off, long gap, cold sensors.
    frame.loc[0, "segment_gap_seconds"] = 25000.0
    frame.loc[0, "rpm"] = 0.0
    frame.loc[0, "coolant_temp"] = 40.0   # |ECT-AAT| = 25 > 15
    frame.loc[0, "intake_temp"] = 16.0    # |IAT-AAT| = 1 <= 7 witness ok
    frame.loc[0, "ambient_temp"] = 15.0
    frame.loc[5, "engine_start_observed"] = True
    state = script50.build_rule_state(frame, REGISTRY)
    state = script50.build_cold_start_state(frame, state, REGISTRY)

    assert bool(state["s1s4_eligible"].iloc[0])
    assert bool(state["s1s4_exceed"].iloc[0])
    assert state["s1s4_eligible"].iloc[1:].eq(False).all()
    # 4-S2 witness is ECT: |ECT-AAT| = 25 > 15 -> not eligible.
    assert not bool(state["s4s2_eligible"].iloc[0])


def test_cold_start_gap_unavailable_reason() -> None:
    frame = make_frame(10)
    frame.loc[0, "rpm"] = 0.0
    state = script50.build_rule_state(frame, REGISTRY)
    state = script50.build_cold_start_state(frame, state, REGISTRY)

    assert (
        state["coldstart_not_evaluable_reason"].iloc[0]
        == "cold_soak_gap_unavailable"
    )
    assert not bool(state["s1s4_eligible"].iloc[0])


def test_s4s2_cap_activates_prospectively_from_start() -> None:
    frame = make_frame(30)
    frame.loc[0, "segment_gap_seconds"] = 25000.0
    frame.loc[0, "rpm"] = 0.0
    frame.loc[0, "coolant_temp"] = 16.0   # ECT witness ok (|delta|=1)
    frame.loc[0, "intake_temp"] = 30.0    # |IAT-AAT| = 15 > 7 -> exceed
    frame.loc[0, "ambient_temp"] = 15.0
    frame.loc[7, "engine_start_observed"] = True
    state = script50.build_rule_state(frame, REGISTRY)
    state = script50.build_cold_start_state(frame, state, REGISTRY)

    assert bool(state["s4s2_exceed"].iloc[0])
    assert not state["s4s2_cap_active"].iloc[:7].any()
    assert state["s4s2_cap_active"].iloc[7:].all()


def test_episode_budget_and_censoring() -> None:
    n = 120
    frame = make_frame(n)
    frame["thermal_state"] = "warmup"
    frame["coolant_temp"] = 30.0          # never reaches 79
    frame.loc[10, "engine_start_observed"] = True
    frame.loc[frame.index[10:], "engine_start_episode_id"] = "e1"
    frame.loc[frame.index[10:], "elapsed_since_engine_start"] = [
        float(x) for x in range(n - 10)
    ]
    episodes = pd.DataFrame([{
        "trip_id": "trip_0001",
        "engine_start_episode_id": "e1",
        "segment_id": "trip_0001_seg_001",
        "continuity_block_id": 1,
        "start_timestamp": frame["timestamp"].iloc[10],
        "start_row_in_segment": 11,
        "end_timestamp": frame["timestamp"].iloc[-1],
        "end_row_in_segment": n,
        "episode_sample_count": n - 10,
        "episode_duration_seconds": float(n - 11),
        "termination_reason": "end_of_data",
        "ect_start": 30.0,
        "aat_start": 10.0,
    }])
    state = script50.build_rule_state(frame, REGISTRY)
    state = script50.build_cold_start_state(frame, state, REGISTRY)
    episode_state = script50.build_engine_start_rule_state(
        frame, state, episodes, REGISTRY
    )

    row = episode_state.iloc[0]
    assert bool(row["s1s1_eligible"])
    assert row["ambient_bin"] == ">5"
    # 30->50 @5.0, 50->65 @4.583..., 65->79 @4.791666..., x1.3, x60
    expected = (
        (20 / 5.0) + (15 / 4.583333333333334)
        + (14 / 4.791666666666667)
    ) * 1.3 * 60.0
    assert row["budget_seconds"] == pytest.approx(expected)
    assert bool(row["budget_in_domain"])
    # Episode (109 s) ends before budget expiry and never hits target.
    assert row["time_to_target_79c"] is None or pd.isna(
        row["time_to_target_79c"]
    )
    assert bool(row["time_to_target_79c_is_right_censored"])
    assert row["time_to_target_79c_censor_time_s"] == pytest.approx(
        float(n - 11)
    )
    # No cold-soak evidence for this segment -> 1-S4 unavailable.
    assert not bool(row["s1s4_evaluable"])
    assert (
        row["s1s4_not_evaluable_reason"] == "cold_soak_gap_unavailable"
    )


def test_episode_time_to_target_when_reached() -> None:
    n = 60
    frame = make_frame(n)
    frame["thermal_state"] = "warmup"
    frame["coolant_temp"] = 70.0
    frame.loc[frame.index[40:], "coolant_temp"] = 80.0
    frame.loc[5, "engine_start_observed"] = True
    frame.loc[frame.index[5:], "engine_start_episode_id"] = "e1"
    frame.loc[frame.index[5:], "elapsed_since_engine_start"] = [
        float(x) for x in range(n - 5)
    ]
    episodes = pd.DataFrame([{
        "trip_id": "trip_0001",
        "engine_start_episode_id": "e1",
        "segment_id": "trip_0001_seg_001",
        "continuity_block_id": 1,
        "start_timestamp": frame["timestamp"].iloc[5],
        "start_row_in_segment": 6,
        "end_timestamp": frame["timestamp"].iloc[-1],
        "end_row_in_segment": n,
        "episode_sample_count": n - 5,
        "episode_duration_seconds": float(n - 6),
        "termination_reason": "end_of_data",
        "ect_start": 45.0,
        "aat_start": 2.0,
    }])
    state = script50.build_rule_state(frame, REGISTRY)
    state = script50.build_cold_start_state(frame, state, REGISTRY)
    episode_state = script50.build_engine_start_rule_state(
        frame, state, episodes, REGISTRY
    )

    row = episode_state.iloc[0]
    assert row["ambient_bin"] == "<=5"
    assert row["time_to_target_79c"] == pytest.approx(35.0)
    assert not bool(row["time_to_target_79c_is_right_censored"])


def test_determinism_under_row_shuffle() -> None:
    frame = make_frame(30)
    frame.loc[0, "segment_gap_seconds"] = 25000.0
    frame.loc[0, "rpm"] = 0.0
    frame.loc[5, "engine_start_observed"] = True
    baseline = script50.build_rule_state(frame, REGISTRY)
    baseline = script50.build_cold_start_state(
        frame, baseline, REGISTRY
    )

    shuffled = frame.sample(frac=1.0, random_state=7)
    shuffled = shuffled.sort_values(
        ["timestamp", "trip_id", "segment_id", "row_in_segment"],
        kind="stable",
    ).reset_index(drop=True)
    result = script50.build_rule_state(shuffled, REGISTRY)
    result = script50.build_cold_start_state(shuffled, result, REGISTRY)

    pd.testing.assert_frame_equal(baseline, result)
