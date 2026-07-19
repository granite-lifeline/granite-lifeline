"""Shared temporal-continuity and strict quality-admission contracts.

Feature and proxy stages must use this module instead of implementing local
gap, boundary, rolling-window, event-neighborhood, or duration-run rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


class ContinuityContractError(ValueError):
    """Raised when continuity inputs or parameters violate the contract."""


@dataclass(frozen=True, slots=True)
class ContinuityResult:
    """Index-aligned continuity metadata for a canonical sample table."""

    block_id: pd.Series
    continues_previous: pd.Series
    break_reason: pd.Series
    valid_sample: pd.Series

    def as_frame(self) -> pd.DataFrame:
        """Return a defensive tabular copy of the continuity metadata."""

        return pd.DataFrame(
            {
                "continuity_block_id": self.block_id.copy(),
                "continues_previous": self.continues_previous.copy(),
                "continuity_break_reason": self.break_reason.copy(),
                "continuity_valid_sample": self.valid_sample.copy(),
            }
        )


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ContinuityContractError(
            f"Continuity input is missing required columns: {missing}."
        )


def _as_bool_mask(
    values: pd.Series | Iterable[bool],
    *,
    index: pd.Index,
    label: str,
) -> pd.Series:
    series = values if isinstance(values, pd.Series) else pd.Series(values)
    if len(series) != len(index):
        raise ContinuityContractError(
            f"{label} length {len(series)} does not match frame length "
            f"{len(index)}."
        )
    if isinstance(values, pd.Series) and not values.index.equals(index):
        raise ContinuityContractError(
            f"{label} index must exactly match the sample-table index."
        )
    series = pd.Series(series.array, index=index)
    try:
        return series.astype("boolean").fillna(False).astype(bool)
    except (TypeError, ValueError) as exc:
        raise ContinuityContractError(
            f"{label} must contain boolean-compatible values."
        ) from exc


def _quality_flag_is_false(series: pd.Series, *, label: str) -> pd.Series:
    mapping = {
        True: True,
        False: False,
        1: True,
        0: False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    normalized = series.map(
        lambda value: mapping.get(
            value.strip().casefold() if isinstance(value, str) else value,
            pd.NA,
        )
    ).astype("boolean")
    unknown = series.notna() & normalized.isna()
    if unknown.any():
        examples = series.loc[unknown].astype(str).drop_duplicates().head(3).tolist()
        raise ContinuityContractError(
            f"{label} contains non-boolean values: {examples}."
        )
    return normalized.eq(False).fillna(False).astype(bool)


def build_quality_valid_mask(
    frame: pd.DataFrame,
    required_signals: Iterable[str],
) -> pd.Series:
    """Admit rows where every required signal and quality flag is valid.

    A signal is valid only when its value is present and its imputed,
    suspicious, and hard-invalid-source flags are all explicitly false.
    Missing flag values are conservatively treated as invalid.
    """

    signals = list(required_signals)
    if not signals or len(signals) != len(set(signals)):
        raise ContinuityContractError(
            "required_signals must be a non-empty sequence without duplicates."
        )

    suffixes = (
        "is_imputed",
        "is_suspicious",
        "had_hard_invalid_source",
    )
    required_columns = [
        column
        for signal in signals
        for column in (signal, *(f"{signal}_{suffix}" for suffix in suffixes))
    ]
    _require_columns(frame, required_columns)

    valid = pd.Series(True, index=frame.index, dtype=bool)
    for signal in signals:
        valid &= frame[signal].notna()
        for suffix in suffixes:
            flag = f"{signal}_{suffix}"
            valid &= _quality_flag_is_false(frame[flag], label=flag)
    return valid


def build_continuity_blocks(
    frame: pd.DataFrame,
    *,
    valid_mask: pd.Series | Iterable[bool] | None = None,
    expected_interval_seconds: float = 1.0,
    timestamp_column: str = "timestamp",
    trip_column: str = "trip_id",
    segment_column: str = "segment_id",
    row_column: str = "row_in_segment",
) -> ContinuityResult:
    """Construct deterministic valid blocks without sorting the input rows.

    A row continues its predecessor only when both rows are valid, trip and
    segment identities match, row numbers differ by one, and UTC timestamps
    differ by exactly ``expected_interval_seconds``. Invalid rows receive a
    null block ID and break continuity on both sides.
    """

    if expected_interval_seconds <= 0:
        raise ContinuityContractError(
            "expected_interval_seconds must be positive."
        )
    required = [timestamp_column, trip_column, segment_column, row_column]
    _require_columns(frame, required)
    if frame[[trip_column, segment_column, row_column]].isna().any().any():
        raise ContinuityContractError(
            "Trip, segment, and row keys must be non-null."
        )

    timestamps = pd.to_datetime(
        frame[timestamp_column], utc=True, errors="coerce"
    )
    if timestamps.isna().any():
        raise ContinuityContractError(
            "Timestamps must be non-null, parseable, and timezone-aware."
        )
    row_numbers = pd.to_numeric(frame[row_column], errors="coerce")
    if row_numbers.isna().any():
        raise ContinuityContractError(
            "row_in_segment values must be numeric and non-null."
        )

    valid = (
        pd.Series(True, index=frame.index, dtype=bool)
        if valid_mask is None
        else _as_bool_mask(valid_mask, index=frame.index, label="valid_mask")
    )
    previous_exists = pd.Series(range(len(frame)), index=frame.index).gt(0)
    same_trip = frame[trip_column].eq(frame[trip_column].shift())
    same_segment = frame[segment_column].eq(frame[segment_column].shift())
    row_consecutive = row_numbers.sub(row_numbers.shift()).eq(1)
    time_consecutive = timestamps.sub(timestamps.shift()).dt.total_seconds().eq(
        float(expected_interval_seconds)
    )
    previous_valid = valid.shift(fill_value=False)

    continues = (
        previous_exists
        & valid
        & previous_valid
        & same_trip
        & same_segment
        & row_consecutive
        & time_consecutive
    ).astype(bool)
    starts_valid_block = valid & ~continues
    numeric_id = starts_valid_block.cumsum().astype("Int64")
    block_id = numeric_id.where(valid, pd.NA)
    block_id.name = "continuity_block_id"

    reason = pd.Series("continuous", index=frame.index, dtype="string")
    reason.loc[~valid] = "invalid_sample"
    valid_start = valid & ~continues
    reason.loc[valid_start & ~previous_exists] = "dataset_start"
    reason.loc[valid_start & previous_exists & ~same_trip] = "trip_boundary"
    reason.loc[
        valid_start & previous_exists & same_trip & ~same_segment
    ] = "segment_boundary"
    reason.loc[
        valid_start & previous_exists & same_trip & same_segment & ~previous_valid
    ] = "previous_sample_invalid"
    reason.loc[
        valid_start
        & previous_exists
        & same_trip
        & same_segment
        & previous_valid
        & ~row_consecutive
    ] = "row_not_consecutive"
    reason.loc[
        valid_start
        & previous_exists
        & same_trip
        & same_segment
        & previous_valid
        & row_consecutive
        & ~time_consecutive
    ] = "timestamp_not_consecutive"
    reason.name = "continuity_break_reason"
    continues.name = "continues_previous"
    valid.name = "continuity_valid_sample"

    return ContinuityResult(block_id, continues, reason, valid)


def strict_window_mask(
    block_ids: pd.Series,
    window_samples: int,
) -> pd.Series:
    """Admit windows ending at rows with exactly N valid block endpoints."""

    if not isinstance(window_samples, int) or window_samples <= 0:
        raise ContinuityContractError("window_samples must be a positive integer.")
    positions = block_ids.groupby(block_ids, dropna=True, sort=False).cumcount()
    admitted = block_ids.notna() & positions.add(1).ge(window_samples)
    admitted.name = f"strict_window_{window_samples}_samples"
    return admitted.astype(bool)


def strict_elapsed_span_mask(
    block_ids: pd.Series,
    timestamps: pd.Series,
    span_seconds: int,
) -> pd.Series:
    """Admit N-second endpoint spans requiring N+1 valid 1 Hz endpoints."""

    if not isinstance(span_seconds, int) or span_seconds < 0:
        raise ContinuityContractError(
            "span_seconds must be a non-negative integer."
        )
    if not block_ids.index.equals(timestamps.index):
        raise ContinuityContractError(
            "block_ids and timestamps must have identical indexes."
        )
    parsed = pd.to_datetime(timestamps, utc=True, errors="coerce")
    if parsed.isna().any():
        raise ContinuityContractError("timestamps contain invalid values.")
    same_block = block_ids.notna() & block_ids.eq(block_ids.shift(span_seconds))
    elapsed = parsed.sub(parsed.shift(span_seconds)).dt.total_seconds()
    admitted = (same_block & elapsed.eq(float(span_seconds))).fillna(False)
    admitted.name = f"strict_elapsed_span_{span_seconds}_seconds"
    return admitted.fillna(False).astype(bool)


def strict_event_neighborhood_mask(
    block_ids: pd.Series,
    *,
    before_samples: int,
    after_samples: int,
) -> pd.Series:
    """Admit anchor rows whose full event neighborhood stays in one block."""

    if (
        not isinstance(before_samples, int)
        or not isinstance(after_samples, int)
        or before_samples < 0
        or after_samples < 0
    ):
        raise ContinuityContractError(
            "before_samples and after_samples must be non-negative integers."
        )
    admitted = block_ids.notna()
    if before_samples:
        admitted &= block_ids.eq(block_ids.shift(before_samples))
    if after_samples:
        admitted &= block_ids.eq(block_ids.shift(-after_samples))
    admitted.name = (
        f"strict_event_neighborhood_{before_samples}_before_"
        f"{after_samples}_after"
    )
    return admitted.fillna(False).astype(bool)


def build_true_run_ids(
    condition: pd.Series | Iterable[bool],
    block_ids: pd.Series,
) -> pd.Series:
    """Assign IDs to true runs, never extending across a continuity break."""

    condition_mask = _as_bool_mask(
        condition,
        index=block_ids.index,
        label="condition",
    )
    active = condition_mask & block_ids.notna()
    same_run_as_previous = (
        active
        & active.shift(fill_value=False)
        & block_ids.eq(block_ids.shift())
    )
    run_starts = active & ~same_run_as_previous
    run_ids = run_starts.cumsum().astype("Int64").where(active, pd.NA)
    run_ids.name = "true_run_id"
    return run_ids
