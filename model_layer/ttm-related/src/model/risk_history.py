"""
Risk-score-history collection and validation (Story 8, Lucca).

Every detector inference call appends one record per analysed
window (`{trip_id, window_id, timestamp, risk_score}`) to an
append-only CSV. The file is the input contract for the Story 8
trend estimator, so `validate_history` enforces the structure the
estimator relies on — ordered, non-empty, valid ranges — with
errors that name the offending field.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from model.input_validation import validate_required_columns
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import validate_required_columns


HISTORY_COLUMNS = ["trip_id", "window_id", "timestamp", "risk_score"]
DEFAULT_HISTORY_PATH = Path("ttm-related/outputs/risk_history.csv")


def append_history(records: list[dict], history_path: Path) -> int:
    """Append window records to the history CSV; return rows written.

    Records whose (trip_id, window_id) already exist in the file
    are skipped, so re-running the detector on the same input does
    not duplicate history rows.
    """
    new = pd.DataFrame(list(records), columns=HISTORY_COLUMNS)
    file_exists = history_path.exists()
    if file_exists:
        existing = load_history(history_path)
        seen = set(
            zip(existing["trip_id"], existing["window_id"])
        )
        fresh = [
            (trip, window) not in seen
            for trip, window in zip(
                new["trip_id"], new["window_id"]
            )
        ]
        new = new[fresh]
    if new.empty:
        return 0
    history_path.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(
        history_path, mode="a", header=not file_exists, index=False
    )
    return len(new)


def load_history(history_path: Path) -> pd.DataFrame:
    """Load the history CSV with a clear error when absent."""
    if not history_path.exists():
        raise ValueError(
            f"Risk history file not found: {history_path}"
        )
    return pd.read_csv(history_path)


def validate_history(
    df: pd.DataFrame, source: str = "risk history"
) -> None:
    """Raise ValueError unless df is a valid ordered history.

    Checks (Story 8): non-empty, required columns, non-blank
    identities, risk_score numeric in [0, 1], parseable
    timestamps, and timestamps non-decreasing within each trip.
    """
    if df.empty:
        raise ValueError(f"{source} is empty: no risk records")
    validate_required_columns(df.columns, HISTORY_COLUMNS, source)

    for column in ("trip_id", "window_id"):
        values = df[column].astype("string")
        blank = values.isna() | (values.str.strip() == "")
        if blank.any():
            raise ValueError(
                f"{source} has {int(blank.sum())} blank "
                f"{column} value(s)"
            )

    scores = pd.to_numeric(df["risk_score"], errors="coerce")
    if scores.isna().any():
        raise ValueError(
            f"{source} has {int(scores.isna().sum())} "
            "non-numeric risk_score value(s)"
        )
    out_of_range = (scores < 0.0) | (scores > 1.0)
    if out_of_range.any():
        raise ValueError(
            f"{source} has {int(out_of_range.sum())} risk_score "
            "value(s) outside [0, 1]"
        )

    timestamps = pd.to_datetime(
        df["timestamp"], errors="coerce", utc=True
    )
    if timestamps.isna().any():
        raise ValueError(
            f"{source} has {int(timestamps.isna().sum())} "
            "unparseable timestamp value(s)"
        )
    for trip_id, group in df.groupby("trip_id", sort=False):
        if not timestamps[group.index].is_monotonic_increasing:
            raise ValueError(
                f"{source} is not ordered: timestamps within "
                f"trip '{trip_id}' must be non-decreasing"
            )
