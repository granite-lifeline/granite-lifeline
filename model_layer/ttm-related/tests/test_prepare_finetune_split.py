"""
Story 6 tests: healthy-trip length verification and train/validation
split (Lucca subtasks). Synthetic frames only — no real CSV needed.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.prepare_finetune_split import (  # noqa: E402
    build_manifest,
    partition_trips,
    split_trips,
    trip_row_counts,
)


def make_combined_df(trip_rows: dict) -> pd.DataFrame:
    """Combined-CSV-shaped frame: `source_file` marks each trip."""
    frames = [
        pd.DataFrame({"source_file": [trip] * rows, "rpm": [1500.0] * rows})
        for trip, rows in trip_rows.items()
    ]
    return pd.concat(frames, ignore_index=True)


class TestTripRowCounts:
    def test_counts_rows_per_trip(self):
        df = make_combined_df({"a.csv": 3, "b.csv": 5})
        assert trip_row_counts(df) == {"a.csv": 3, "b.csv": 5}

    def test_missing_source_file_column_raises(self):
        df = pd.DataFrame({"rpm": [1500.0]})
        with pytest.raises(ValueError, match="source_file"):
            trip_row_counts(df)


class TestPartitionTrips:
    def test_700_row_trip_is_eligible_699_is_excluded(self):
        counts = {"short.csv": 699, "exact.csv": 700, "long.csv": 900}
        eligible, excluded = partition_trips(counts, min_rows=700)
        assert eligible == ["exact.csv", "long.csv"]
        assert excluded == [
            {
                "source_file": "short.csv",
                "rows": 699,
                "reason": "below minimum length 700",
            }
        ]

    def test_all_eligible_gives_empty_excluded(self):
        eligible, excluded = partition_trips({"a.csv": 800}, min_rows=700)
        assert eligible == ["a.csv"]
        assert excluded == []


class TestSplitTrips:
    def test_floor_based_80_20_proportions(self):
        trips = [f"t{i:02d}.csv" for i in range(10)]
        train, validation = split_trips(trips, 0.8, seed=42)
        assert len(train) == 8
        assert len(validation) == 2

    def test_disjoint_and_complete(self):
        trips = [f"t{i:02d}.csv" for i in range(13)]
        train, validation = split_trips(trips, 0.8, seed=42)
        assert set(train).isdisjoint(validation)
        assert sorted(train + validation) == sorted(trips)

    def test_same_seed_same_split(self):
        trips = [f"t{i:02d}.csv" for i in range(10)]
        assert split_trips(trips, 0.8, 42) == split_trips(trips, 0.8, 42)

    def test_split_independent_of_input_order(self):
        trips = [f"t{i:02d}.csv" for i in range(10)]
        assert split_trips(trips, 0.8, 42) == split_trips(
            list(reversed(trips)), 0.8, 42
        )

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="[Nn]o eligible trips"):
            split_trips([], 0.8, 42)

    def test_empty_validation_side_raises(self):
        with pytest.raises(ValueError, match="empty"):
            split_trips(["a.csv", "b.csv"], 1.0, 42)

    def test_empty_train_side_raises(self):
        with pytest.raises(ValueError, match="empty"):
            split_trips(["a.csv"], 0.8, 42)


class TestBuildManifest:
    def test_manifest_schema_and_values(self):
        trip_rows = {f"t{i:02d}.csv": 700 + i for i in range(10)}
        trip_rows["short.csv"] = 100
        df = make_combined_df(trip_rows)
        manifest = build_manifest(
            df, "input.csv", min_rows=700, train_fraction=0.8, seed=42
        )
        assert manifest["input_file"] == "input.csv"
        assert manifest["min_rows"] == 700
        assert manifest["train_fraction"] == 0.8
        assert manifest["seed"] == 42
        assert manifest["n_trips_total"] == 11
        assert manifest["n_trips_eligible"] == 10
        assert manifest["trip_row_counts"]["short.csv"] == 100
        assert len(manifest["train_trips"]) == 8
        assert len(manifest["validation_trips"]) == 2
        assert manifest["excluded_trips"] == [
            {
                "source_file": "short.csv",
                "rows": 100,
                "reason": "below minimum length 700",
            }
        ]
        assert "generated_at" in manifest

    def test_manifest_is_json_serialisable(self):
        df = make_combined_df(
            {
                "a.csv": 700,
                "b.csv": 700,
                "c.csv": 700,
                "d.csv": 700,
                "e.csv": 700,
            }
        )
        manifest = build_manifest(df, "input.csv")
        json.dumps(manifest)

    def test_no_eligible_trips_raises(self):
        df = make_combined_df({"a.csv": 10, "b.csv": 20})
        with pytest.raises(ValueError, match="[Nn]o eligible trips"):
            build_manifest(df, "input.csv")
