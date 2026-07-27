"""
Story 8 (Lucca): risk-score-history persistence and validation
tests. History records are `{trip_id, window_id, timestamp,
risk_score}` per analysed window; the CSV is the input contract
for the Story 8 trend estimator.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.risk_history import (  # noqa: E402
    HISTORY_COLUMNS,
    append_history,
    load_history,
    validate_history,
)


def record(trip="trip_0001", window="trip_0001_seg_001__w000",
           ts="2026-06-16T10:10:07Z", score=0.12):
    return {
        "trip_id": trip,
        "window_id": window,
        "timestamp": ts,
        "risk_score": score,
    }


class TestAppendAndLoad:
    def test_append_creates_file_with_header(self, tmp_path):
        path = tmp_path / "risk_history.csv"
        written = append_history([record()], path)
        assert written == 1
        df = load_history(path)
        assert list(df.columns) == HISTORY_COLUMNS
        assert len(df) == 1

    def test_append_accumulates_across_calls(self, tmp_path):
        path = tmp_path / "risk_history.csv"
        append_history([record()], path)
        append_history(
            [record(window="trip_0001_seg_001__w001",
                    ts="2026-06-16T10:20:15Z", score=0.2)],
            path,
        )
        df = load_history(path)
        assert len(df) == 2
        assert df["window_id"].is_unique

    def test_rerun_does_not_duplicate_rows(self, tmp_path):
        path = tmp_path / "risk_history.csv"
        append_history([record()], path)
        written = append_history([record(score=0.99)], path)
        assert written == 0
        df = load_history(path)
        assert len(df) == 1
        assert float(df["risk_score"].iloc[0]) == 0.12

    def test_append_creates_parent_directory(self, tmp_path):
        path = tmp_path / "outputs" / "risk_history.csv"
        append_history([record()], path)
        assert path.exists()

    def test_load_missing_file_is_clear_error(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            load_history(tmp_path / "nope.csv")


class TestValidateHistory:
    def make_df(self, rows):
        return pd.DataFrame(rows, columns=HISTORY_COLUMNS)

    def test_valid_history_passes(self):
        df = self.make_df([
            record(),
            record(window="trip_0001_seg_001__w001",
                   ts="2026-06-16T10:20:15Z", score=0.2),
            record(trip="trip_0002",
                   window="trip_0002_seg_001__w000",
                   ts="2026-06-17T09:00:00Z", score=0.3),
        ])
        validate_history(df)

    def test_empty_history_rejected(self):
        df = pd.DataFrame(columns=HISTORY_COLUMNS)
        with pytest.raises(ValueError, match="empty"):
            validate_history(df)

    def test_missing_column_rejected(self):
        df = self.make_df([record()]).drop(columns=["risk_score"])
        with pytest.raises(ValueError, match="risk_score"):
            validate_history(df)

    def test_out_of_range_risk_score_rejected(self):
        df = self.make_df([record(score=1.5)])
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            validate_history(df)

    def test_non_numeric_risk_score_rejected(self):
        df = self.make_df([record(score="high")])
        with pytest.raises(ValueError, match="non-numeric"):
            validate_history(df)

    def test_unparseable_timestamp_rejected(self):
        df = self.make_df([record(ts="not-a-time")])
        with pytest.raises(ValueError, match="timestamp"):
            validate_history(df)

    def test_unordered_within_trip_rejected(self):
        df = self.make_df([
            record(ts="2026-06-16T10:20:15Z"),
            record(window="trip_0001_seg_001__w001",
                   ts="2026-06-16T10:10:07Z"),
        ])
        with pytest.raises(ValueError, match="ordered"):
            validate_history(df)

    def test_blank_identity_rejected(self):
        df = self.make_df([record(trip="")])
        with pytest.raises(ValueError, match="trip_id"):
            validate_history(df)
