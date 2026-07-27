"""Contract tests for script 60 pedal-step event evidence."""
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


def _load_script60():
    path = (
        REPO_ROOT
        / "data_layer/proxy_failure/src/60_event_evidence_builder.py"
    )
    spec = importlib.util.spec_from_file_location("script60", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script60 = _load_script60()
REGISTRY = load_json_object(
    RunLayout.for_run_id("t", repo_root=REPO_ROOT).calibration_registry
)

QUALITY_SIGNALS = ["map", "rpm", "accel_pedal_d", "accel_pedal_e"]
FLAG_SUFFIXES = [
    "is_imputed", "is_suspicious", "had_hard_invalid_source",
]


def make_frame(n: int = 30) -> pd.DataFrame:
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
            "thermal_state": "post_warmup",
            "condition_confidence": "high",
            "operating_state": "post_warmup__steady_driving",
            "map": 30.0,
            "rpm": 1500.0,
            "accel_pedal_d": 20.0,
            "accel_pedal_e": 20.0,
            "pedal_slope": 0.0,
        }
    )
    for signal in QUALITY_SIGNALS:
        for suffix in FLAG_SUFFIXES:
            frame[f"{signal}_{suffix}"] = False
    return frame


def build(frame: pd.DataFrame) -> pd.DataFrame:
    return script60.build_pedal_step_events(frame, REGISTRY)


def test_detection_uses_per_state_frozen_thresholds() -> None:
    frame = make_frame()
    frame.loc[5, "pedal_slope"] = 11.4
    frame.loc[10, "pedal_slope"] = 11.3
    frame.loc[15, "pedal_slope"] = 9.2
    frame.loc[20, "operating_state"] = "post_warmup__idle"
    frame.loc[20, "pedal_slope"] = 9.2

    events = build(frame)

    assert list(events["row_in_segment"]) == [5, 20]
    assert list(events["operating_state"]) == [
        "post_warmup__steady_driving", "post_warmup__idle",
    ]


def test_domain_guards_suppress_detection() -> None:
    frame = make_frame()
    frame.loc[5, "pedal_slope"] = 20.0
    frame.loc[5, "condition_confidence"] = "medium"
    frame.loc[10, "pedal_slope"] = 20.0
    frame.loc[10, "thermal_state"] = "warming"
    frame.loc[15, "pedal_slope"] = 20.0
    frame.loc[15, "map_is_suspicious"] = True

    events = build(frame)

    assert events.empty


def test_neighborhood_must_stay_in_one_block() -> None:
    frame = make_frame()
    frame.loc[0, "pedal_slope"] = 20.0
    frame.loc[28, "pedal_slope"] = 20.0
    frame.loc[10, "pedal_slope"] = 20.0
    frame.loc[frame.index >= 20, "continuity_block_id"] = 2.0

    events = build(frame)

    by_row = events.set_index("row_in_segment")
    assert not by_row.loc[0, "window_complete"]
    assert by_row.loc[0, "window_incomplete_reason"] == (
        "neighborhood_outside_block"
    )
    assert not by_row.loc[28, "window_complete"]
    assert by_row.loc[28, "window_incomplete_reason"] == (
        "neighborhood_outside_block"
    )
    assert by_row.loc[10, "window_complete"]
    assert pd.isna(by_row.loc[10, "window_incomplete_reason"])


def test_neighborhood_quality_gates_validity() -> None:
    frame = make_frame()
    frame.loc[10, "pedal_slope"] = 20.0
    frame.loc[12, "rpm_is_suspicious"] = True

    events = build(frame)

    row = events.iloc[0]
    assert row["row_in_segment"] == 10
    assert not row["window_complete"]
    assert row["window_incomplete_reason"] == "neighborhood_quality"
    assert pd.isna(row["response_kpa"])
    assert pd.isna(row["event_result"])
    assert pd.isna(row["complete_event_ordinal"])


def test_response_and_boundary_follow_frozen_operators() -> None:
    frame = make_frame()
    frame.loc[5, "pedal_slope"] = 16.0
    frame.loc[10, "pedal_slope"] = 16.0
    frame.loc[11, "map"] = 33.0

    events = build(frame)

    by_row = events.set_index("row_in_segment")
    flat = by_row.loc[5]
    assert flat["magnitude_bin"] == "hi"
    assert flat["response_kpa"] == 0.0
    assert flat["event_result"] == "no_response"
    boundary = by_row.loc[10]
    assert boundary["response_kpa"] == 3.0
    assert boundary["event_result"] == "response"


def test_steady_driving_low_bin_is_not_evaluable() -> None:
    frame = make_frame()
    frame.loc[10, "pedal_slope"] = 11.4

    events = build(frame)

    row = events.iloc[0]
    assert row["window_complete"]
    assert row["magnitude_bin"] == "lo"
    assert pd.isna(row["no_response_threshold_kpa"])
    assert not row["evaluable"]
    assert row["event_result"] == "not_evaluable"
    assert row["complete_event_ordinal"] == 1
    assert row["no_response_count_recent_n"] == 0
    assert not row["m_of_n_triggered"]


def test_rolling_window_counts_recent_valid_events() -> None:
    frame = make_frame(40)
    for row in (5, 10, 15, 20, 25):
        frame.loc[row, "pedal_slope"] = 16.0

    events = build(frame)

    assert list(events["complete_event_ordinal"]) == [1, 2, 3, 4, 5]
    assert list(events["recent_window_size"]) == [1, 2, 3, 4, 4]
    assert list(events["no_response_count_recent_n"]) == [1, 2, 3, 4, 4]
    assert list(events["m_of_n_triggered"]) == [
        False, False, True, True, True,
    ]
    assert list(events["decision_margin"]) == [-2, -1, 0, 1, 1]


def test_window_slots_include_not_evaluable_without_counting() -> None:
    frame = make_frame(40)
    for row in (5, 10, 15):
        frame.loc[row, "pedal_slope"] = 16.0
    frame.loc[20, "pedal_slope"] = 11.4
    frame.loc[25, "pedal_slope"] = 16.0

    events = build(frame)

    assert list(events["no_response_count_recent_n"]) == [1, 2, 3, 3, 3]
    assert list(events["m_of_n_triggered"]) == [
        False, False, True, True, True,
    ]


def test_incomplete_window_events_never_enter_the_window() -> None:
    frame = make_frame(40)
    for row in (5, 10, 20, 25):
        frame.loc[row, "pedal_slope"] = 16.0
    frame.loc[15, "pedal_slope"] = 16.0
    frame.loc[16, "map_is_imputed"] = True

    events = build(frame)

    by_row = events.set_index("row_in_segment")
    assert not by_row.loc[15, "window_complete"]
    assert list(events["complete_event_ordinal"].dropna()) == [
        1, 2, 3, 4,
    ]
    assert list(events["no_response_count_recent_n"].dropna()) == [
        1, 2, 3, 4,
    ]


def test_determinism_under_row_shuffle() -> None:
    frame = make_frame(40)
    for row in (5, 10, 15, 20):
        frame.loc[row, "pedal_slope"] = 16.0

    baseline = build(frame)
    shuffled = (
        frame.sample(frac=1.0, random_state=7)
        .sort_values(["trip_id", "segment_id", "row_in_segment"])
        .reset_index(drop=True)
    )
    again = build(shuffled)

    pd.testing.assert_frame_equal(baseline, again)
