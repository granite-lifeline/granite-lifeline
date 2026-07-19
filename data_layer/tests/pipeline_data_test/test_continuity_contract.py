from __future__ import annotations

import pandas as pd
import pytest

from data_layer.pipeline_data.continuity import (
    ContinuityContractError,
    build_continuity_blocks,
    build_quality_valid_mask,
    build_true_run_ids,
    strict_elapsed_span_mask,
    strict_event_neighborhood_mask,
    strict_window_mask,
)


def _frame(
    timestamps: list[str],
    trips: list[str],
    segments: list[str],
    rows: list[int],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "trip_id": trips,
            "segment_id": segments,
            "row_in_segment": rows,
        }
    )


def test_gap_segment_and_trip_boundaries_create_new_blocks() -> None:
    frame = _frame(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:01Z",
            "2026-01-01T00:00:03Z",
            "2026-01-01T00:00:04Z",
            "2026-01-01T00:00:05Z",
        ],
        ["trip-1", "trip-1", "trip-1", "trip-1", "trip-2"],
        ["seg-1", "seg-1", "seg-1", "seg-2", "seg-1"],
        [1, 2, 3, 1, 1],
    )

    result = build_continuity_blocks(frame)

    assert result.block_id.tolist() == [1, 1, 2, 3, 4]
    assert result.continues_previous.tolist() == [
        False, True, False, False, False]
    assert result.break_reason.tolist() == [
        "dataset_start",
        "continuous",
        "timestamp_not_consecutive",
        "segment_boundary",
        "trip_boundary",
    ]


def test_row_number_gap_breaks_even_when_time_is_consecutive() -> None:
    frame = _frame(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:01Z",
        ],
        ["trip-1", "trip-1"],
        ["seg-1", "seg-1"],
        [1, 3],
    )

    result = build_continuity_blocks(frame)

    assert result.block_id.tolist() == [1, 2]
    assert result.break_reason.tolist() == [
        "dataset_start",
        "row_not_consecutive",
    ]


def test_invalid_sample_is_outside_blocks_and_breaks_both_sides() -> None:
    frame = _frame(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:01Z",
            "2026-01-01T00:00:02Z",
            "2026-01-01T00:00:03Z",
        ],
        ["trip-1"] * 4,
        ["seg-1"] * 4,
        [1, 2, 3, 4],
    )

    result = build_continuity_blocks(
        frame,
        valid_mask=pd.Series([True, False, True, True]),
    )

    assert result.block_id.tolist() == [1, pd.NA, 2, 2]
    assert result.break_reason.tolist() == [
        "dataset_start",
        "invalid_sample",
        "previous_sample_invalid",
        "continuous",
    ]


def test_quality_admission_requires_value_and_three_false_flags() -> None:
    frame = pd.DataFrame(
        {
            "rpm": [800.0, 800.0, None, 800.0, 800.0, 800.0],
            "rpm_is_imputed": [False, True, False, False, False, False],
            "rpm_is_suspicious": [False, False, False, True, False, False],
            "rpm_had_hard_invalid_source": [
                False,
                False,
                False,
                False,
                True,
                pd.NA,
            ],
        }
    )

    valid = build_quality_valid_mask(frame, ["rpm"])

    assert valid.tolist() == [True, False, False, False, False, False]


def test_quality_admission_accepts_explicit_string_booleans() -> None:
    frame = pd.DataFrame(
        {
            "rpm": [800.0, 800.0],
            "rpm_is_imputed": ["false", "true"],
            "rpm_is_suspicious": ["0", "0"],
            "rpm_had_hard_invalid_source": [0, 0],
        }
    )

    assert build_quality_valid_mask(frame, ["rpm"]).tolist() == [True, False]


def test_quality_admission_rejects_missing_or_malformed_contract() -> None:
    frame = pd.DataFrame({"rpm": [800.0], "rpm_is_imputed": ["maybe"]})

    with pytest.raises(
        ContinuityContractError, match="missing required columns"
    ):
        build_quality_valid_mask(frame, ["rpm"])
    with pytest.raises(ContinuityContractError, match="without duplicates"):
        build_quality_valid_mask(frame, ["rpm", "rpm"])


def test_strict_sample_window_restarts_after_invalid_boundary() -> None:
    blocks = pd.Series([1, 1, 1, pd.NA, 2, 2, 2, 2], dtype="Int64")

    admitted = strict_window_mask(blocks, 3)

    assert admitted.tolist() == [
        False,
        False,
        True,
        False,
        False,
        False,
        True,
        True]


def test_elapsed_span_requires_both_endpoints_in_same_block() -> None:
    blocks = pd.Series([1, 1, 1, 2, 2, 2], dtype="Int64")
    timestamps = pd.Series(
        pd.to_datetime(
            [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:01Z",
                "2026-01-01T00:00:02Z",
                "2026-01-01T00:00:04Z",
                "2026-01-01T00:00:05Z",
                "2026-01-01T00:00:06Z",
            ],
            utc=True,
        )
    )

    admitted = strict_elapsed_span_mask(blocks, timestamps, 2)

    assert admitted.tolist() == [False, False, True, False, False, True]


def test_180_second_span_requires_181_endpoints() -> None:
    timestamps = pd.Series(
        pd.date_range("2026-01-01T00:00:00Z", periods=182, freq="s")
    )
    blocks = pd.Series([1] * 182, dtype="Int64")

    admitted = strict_elapsed_span_mask(blocks, timestamps, 180)

    assert int(admitted.sum()) == 2
    assert admitted.iloc[179] == False  # noqa: E712
    assert admitted.iloc[180] == True  # noqa: E712


def test_event_neighborhood_never_crosses_a_block_boundary() -> None:
    blocks = pd.Series([1, 1, 1, 1, 1, 2, 2, 2, 2], dtype="Int64")

    admitted = strict_event_neighborhood_mask(
        blocks,
        before_samples=1,
        after_samples=2,
    )

    assert admitted.tolist() == [
        False,
        True,
        True,
        False,
        False,
        False,
        True,
        False,
        False,
    ]


def test_duration_runs_restart_after_false_invalid_or_new_block() -> None:
    condition = pd.Series([True, True, True, True, True, True, False, True])
    blocks = pd.Series([1, 1, pd.NA, 2, 2, 3, 3, 3], dtype="Int64")

    run_ids = build_true_run_ids(condition, blocks)

    assert run_ids.tolist() == [1, 1, pd.NA, 2, 2, 3, pd.NA, 4]


def test_invalid_parameters_and_misaligned_indexes_are_rejected() -> None:
    blocks = pd.Series([1, 1], dtype="Int64")
    timestamps = pd.Series(
        pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"]),
        index=[1, 2],
    )

    with pytest.raises(ContinuityContractError, match="positive integer"):
        strict_window_mask(blocks, 0)
    with pytest.raises(ContinuityContractError, match="identical indexes"):
        strict_elapsed_span_mask(blocks, timestamps, 1)
    with pytest.raises(ContinuityContractError, match="non-negative integers"):
        strict_event_neighborhood_mask(
            blocks, before_samples=-1, after_samples=2
        )
