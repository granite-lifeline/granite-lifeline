"""
Story 6 tests: per-segment eligibility (length + final_label_*
health) and trip-grouped train/validation split on Group 1's data
(Lucca subtasks). Synthetic frames only — no real CSV needed.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import write_group1_csv  # noqa: E402
from model.prepare_finetune_split import (  # noqa: E402
    KEY_COLUMNS,
    build_manifest,
    find_label_columns,
    load_key_columns,
    load_segment_labels,
    partition_segments,
    segment_summary,
    split_trips,
    unhealthy_segments,
    validate_label_alignment,
)

LABEL_A = "final_label_cooling_degradation"
LABEL_B = "final_label_air_intake_maf_anomaly"


def make_key_frame(segments: dict) -> pd.DataFrame:
    """Key-columns frame: {segment_id: (trip_id, rows)}.

    Timestamps are globally unique across the whole frame, matching
    the real dataset (one vehicle, chronological trips at 1 Hz).
    """
    frames = [
        pd.DataFrame(
            {
                "trip_id": [trip] * rows,
                "segment_id": [segment] * rows,
                "row_in_segment": list(range(1, rows + 1)),
            }
        )
        for segment, (trip, rows) in segments.items()
    ]
    combined = pd.concat(frames, ignore_index=True)
    timestamps = pd.date_range(
        "2026-06-16 10:00:00", periods=len(combined), freq="1s"
    )
    combined["timestamp"] = timestamps.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return combined


def make_labels_frame(
    features: pd.DataFrame, unhealthy_rows: dict | None = None
) -> pd.DataFrame:
    """Labels frame mirroring a key frame's rows, all healthy.

    Loader-shaped: timestamp + label columns only (the labels CSV's
    own trip/segment ids are untrusted and never read).
    ``unhealthy_rows`` = {segment_id: [row_in_segment, ...]} sets
    LABEL_A to 1 on the rows at the matching timestamps.
    """
    labels = features[["timestamp"]].copy()
    labels[LABEL_A] = 0
    labels[LABEL_B] = 0
    for segment, rows in (unhealthy_rows or {}).items():
        mask = (features["segment_id"] == segment) & (
            features["row_in_segment"].isin(rows)
        )
        labels.loc[mask.to_numpy(), LABEL_A] = 1
    return labels


def merge_on_timestamp(
    features: pd.DataFrame, labels: pd.DataFrame
) -> pd.DataFrame:
    """Merged frame shape that unhealthy_segments expects."""
    return features.merge(labels, on="timestamp")


class TestSegmentSummary:
    def test_counts_rows_per_segment(self):
        df = make_key_frame(
            {
                "trip_0001_seg_001": ("trip_0001", 3),
                "trip_0001_seg_002": ("trip_0001", 5),
                "trip_0002_seg_001": ("trip_0002", 4),
            }
        )
        summary = segment_summary(df)
        assert len(summary) == 3
        by_segment = summary.set_index("segment_id")
        assert by_segment.loc["trip_0001_seg_002", "rows"] == 5
        assert (
            by_segment.loc["trip_0002_seg_001", "trip_id"]
            == "trip_0002"
        )

    def test_missing_key_column_raises(self):
        df = pd.DataFrame({"trip_id": ["trip_0001"]})
        with pytest.raises(ValueError, match="segment_id"):
            segment_summary(df)

    def test_segment_under_two_trips_raises(self):
        df = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 3)}
        )
        conflicting = df.copy()
        conflicting["trip_id"] = "trip_0002"
        with pytest.raises(ValueError, match="more than one trip"):
            segment_summary(
                pd.concat([df, conflicting], ignore_index=True)
            )


class TestFindLabelColumns:
    def test_discovers_by_prefix_sorted(self):
        columns = ["segment_id", LABEL_B, LABEL_A, "proxy_flag_x"]
        assert find_label_columns(columns) == sorted(
            [LABEL_A, LABEL_B]
        )

    def test_no_label_columns_raises(self):
        with pytest.raises(ValueError, match="final_label_"):
            find_label_columns(["segment_id", "proxy_flag_x"])


class TestUnhealthySegments:
    def test_all_healthy_gives_empty_dict(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        joined = merge_on_timestamp(
            features, make_labels_frame(features)
        )
        assert unhealthy_segments(joined) == {}

    def test_flagged_rows_counted_per_segment(self):
        features = make_key_frame(
            {
                "trip_0001_seg_001": ("trip_0001", 5),
                "trip_0002_seg_001": ("trip_0002", 5),
            }
        )
        labels = make_labels_frame(
            features, {"trip_0002_seg_001": [2, 4]}
        )
        joined = merge_on_timestamp(features, labels)
        assert unhealthy_segments(joined) == {
            "trip_0002_seg_001": 2
        }

    def test_nan_label_counts_as_unhealthy(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        labels = make_labels_frame(features)
        labels.loc[0, LABEL_B] = np.nan
        joined = merge_on_timestamp(features, labels)
        assert unhealthy_segments(joined) == {
            "trip_0001_seg_001": 1
        }


class TestValidateLabelAlignment:
    def test_matching_frames_pass(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        validate_label_alignment(
            features, make_labels_frame(features)
        )

    def test_row_count_mismatch_raises(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        labels = make_labels_frame(features).iloc[:-1]
        with pytest.raises(ValueError, match="[Rr]ow count"):
            validate_label_alignment(features, labels)

    def test_key_set_mismatch_raises(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        labels = make_labels_frame(features)
        labels.loc[0, "timestamp"] = "1999-01-01T00:00:00Z"
        with pytest.raises(ValueError, match="timestamps differ"):
            validate_label_alignment(features, labels)

    def test_duplicate_keys_raise(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        labels = make_labels_frame(features)
        duplicated = pd.concat(
            [features, features.iloc[[0]]], ignore_index=True
        )
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            validate_label_alignment(duplicated, labels)


class TestPartitionSegments:
    def test_700_row_segment_eligible_699_excluded(self):
        features = make_key_frame(
            {
                "trip_0001_seg_001": ("trip_0001", 700),
                "trip_0001_seg_002": ("trip_0001", 699),
            }
        )
        eligible, excluded = partition_segments(
            segment_summary(features), {}, min_rows=700
        )
        assert eligible == {"trip_0001": ["trip_0001_seg_001"]}
        assert excluded == [
            {
                "trip_id": "trip_0001",
                "segment_id": "trip_0001_seg_002",
                "rows": 699,
                "reason": "below minimum length 700",
            }
        ]

    def test_long_but_unhealthy_segment_excluded_whole(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 700)}
        )
        eligible, excluded = partition_segments(
            segment_summary(features),
            {"trip_0001_seg_001": 3},
            min_rows=700,
        )
        assert eligible == {}
        assert excluded == [
            {
                "trip_id": "trip_0001",
                "segment_id": "trip_0001_seg_001",
                "rows": 700,
                "reason": (
                    "3 rows flagged unhealthy by final_label_*"
                ),
            }
        ]

    def test_segment_failing_both_rules_gets_combined_reason(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 10)}
        )
        _, excluded = partition_segments(
            segment_summary(features),
            {"trip_0001_seg_001": 1},
            min_rows=700,
        )
        assert excluded[0]["reason"] == (
            "below minimum length 700; "
            "1 rows flagged unhealthy by final_label_*"
        )

    def test_eligible_segments_grouped_and_sorted_per_trip(self):
        features = make_key_frame(
            {
                "trip_0002_seg_002": ("trip_0002", 700),
                "trip_0002_seg_001": ("trip_0002", 700),
                "trip_0001_seg_001": ("trip_0001", 700),
            }
        )
        eligible, excluded = partition_segments(
            segment_summary(features), {}, min_rows=700
        )
        assert excluded == []
        assert eligible == {
            "trip_0001": ["trip_0001_seg_001"],
            "trip_0002": [
                "trip_0002_seg_001",
                "trip_0002_seg_002",
            ],
        }

    def test_trip_with_no_eligible_segment_absent(self):
        features = make_key_frame(
            {
                "trip_0001_seg_001": ("trip_0001", 700),
                "trip_0002_seg_001": ("trip_0002", 10),
            }
        )
        eligible, _ = partition_segments(
            segment_summary(features), {}, min_rows=700
        )
        assert "trip_0002" not in eligible


class TestSplitTrips:
    def test_floor_based_80_20_proportions(self):
        trips = [f"trip_{i:04d}" for i in range(10)]
        train, validation = split_trips(trips, 0.8, seed=42)
        assert len(train) == 8
        assert len(validation) == 2

    def test_disjoint_and_complete(self):
        trips = [f"trip_{i:04d}" for i in range(13)]
        train, validation = split_trips(trips, 0.8, seed=42)
        assert set(train).isdisjoint(validation)
        assert sorted(train + validation) == sorted(trips)

    def test_same_seed_same_split(self):
        trips = [f"trip_{i:04d}" for i in range(10)]
        assert split_trips(trips, 0.8, 42) == split_trips(
            trips, 0.8, 42
        )

    def test_split_independent_of_input_order(self):
        trips = [f"trip_{i:04d}" for i in range(10)]
        assert split_trips(trips, 0.8, 42) == split_trips(
            list(reversed(trips)), 0.8, 42
        )

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="[Nn]o eligible trips"):
            split_trips([], 0.8, 42)

    def test_empty_validation_side_raises(self):
        with pytest.raises(ValueError, match="empty"):
            split_trips(["trip_0001", "trip_0002"], 1.0, 42)

    def test_empty_train_side_raises(self):
        with pytest.raises(ValueError, match="empty"):
            split_trips(["trip_0001"], 0.8, 42)


class TestBuildManifest:
    @staticmethod
    def make_multi_trip_inputs():
        """10 trips, some multi-segment, one short, one unhealthy."""
        segments = {}
        for i in range(1, 11):
            trip = f"trip_{i:04d}"
            n_segments = 3 if i <= 2 else (2 if i <= 5 else 1)
            for j in range(1, n_segments + 1):
                segments[f"{trip}_seg_{j:03d}"] = (trip, 10)
        segments["trip_0001_seg_004"] = ("trip_0001", 4)
        features = make_key_frame(segments)
        labels = make_labels_frame(
            features, {"trip_0002_seg_003": [1]}
        )
        return features, labels

    def test_manifest_schema_and_values(self):
        features, labels = self.make_multi_trip_inputs()
        manifest = build_manifest(
            features, labels, "input.csv", "labels.csv",
            min_rows=10, train_fraction=0.8, seed=42,
        )
        assert manifest["input_file"] == "input.csv"
        assert manifest["labels_file"] == "labels.csv"
        assert manifest["min_rows"] == 10
        assert manifest["train_fraction"] == 0.8
        assert manifest["seed"] == 42
        assert manifest["label_columns"] == sorted(
            [LABEL_A, LABEL_B]
        )
        assert manifest["n_trips_total"] == 10
        assert manifest["n_trips_eligible"] == 10
        assert manifest["n_segments_total"] == 18
        assert manifest["n_segments_eligible"] == 16
        assert (
            manifest["segment_row_counts"]["trip_0001_seg_004"] == 4
        )
        assert len(manifest["train_trips"]) == 8
        assert len(manifest["validation_trips"]) == 2
        assert manifest["excluded_segments"] == [
            {
                "trip_id": "trip_0001",
                "segment_id": "trip_0001_seg_004",
                "rows": 4,
                "reason": "below minimum length 10",
            },
            {
                "trip_id": "trip_0002",
                "segment_id": "trip_0002_seg_003",
                "rows": 10,
                "reason": (
                    "1 rows flagged unhealthy by final_label_*"
                ),
            },
        ]
        assert "generated_at" in manifest

    def test_trip_grouped_split_invariant(self):
        features, labels = self.make_multi_trip_inputs()
        manifest = build_manifest(
            features, labels, "input.csv", "labels.csv",
            min_rows=10,
        )
        train_trips = set(manifest["train_trips"])
        validation_trips = set(manifest["validation_trips"])
        assert train_trips.isdisjoint(validation_trips)
        split_segments = sorted(
            segment
            for side in ("train_trips", "validation_trips")
            for segments in manifest[side].values()
            for segment in segments
        )
        excluded = {
            entry["segment_id"]
            for entry in manifest["excluded_segments"]
        }
        eligible = sorted(
            segment
            for segment in manifest["segment_row_counts"]
            if segment not in excluded
        )
        assert split_segments == eligible

    def test_labels_row_order_does_not_matter(self):
        # Group 1's trip numbering (and hence row order) is not
        # stable across deliveries; the timestamp join must not
        # depend on the labels CSV's ordering.
        features, labels = self.make_multi_trip_inputs()
        shuffled = labels.sample(
            frac=1, random_state=7
        ).reset_index(drop=True)
        manifest_a = build_manifest(
            features, labels, "input.csv", "labels.csv",
            min_rows=10,
        )
        manifest_b = build_manifest(
            features, shuffled, "input.csv", "labels.csv",
            min_rows=10,
        )
        for key in (
            "train_trips",
            "validation_trips",
            "excluded_segments",
        ):
            assert manifest_a[key] == manifest_b[key]

    def test_manifest_is_json_serialisable(self):
        features, labels = self.make_multi_trip_inputs()
        manifest = build_manifest(
            features, labels, "input.csv", "labels.csv",
            min_rows=10,
        )
        json.dumps(manifest)

    def test_no_eligible_segments_raises(self):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 5)}
        )
        labels = make_labels_frame(features)
        with pytest.raises(ValueError, match="[Nn]o eligible trips"):
            build_manifest(
                features, labels, "input.csv", "labels.csv",
                min_rows=700,
            )

    def test_alignment_failure_propagates(self):
        features = make_key_frame(
            {
                "trip_0001_seg_001": ("trip_0001", 10),
                "trip_0002_seg_001": ("trip_0002", 10),
            }
        )
        labels = make_labels_frame(features).iloc[:-1]
        with pytest.raises(ValueError, match="[Rr]ow count"):
            build_manifest(
                features, labels, "input.csv", "labels.csv",
                min_rows=5,
            )


class TestLoaders:
    def test_load_key_columns_returns_keys_only(self, tmp_path):
        csv_path = write_group1_csv(
            tmp_path / "features.csv", rows=12
        )
        frame = load_key_columns(csv_path)
        assert set(frame.columns) == set(KEY_COLUMNS + ["timestamp"])
        assert len(frame) == 12

    def test_load_key_columns_missing_column_raises(self, tmp_path):
        csv_path = write_group1_csv(
            tmp_path / "features.csv",
            rows=3,
            drop_columns=["segment_id"],
        )
        with pytest.raises(ValueError, match="segment_id"):
            load_key_columns(csv_path)

    def test_load_segment_labels_discovers_labels(self, tmp_path):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 4)}
        )
        labels = make_labels_frame(features)
        labels["proxy_flag_cooling_degradation"] = 0
        csv_path = tmp_path / "labels.csv"
        labels.to_csv(csv_path, index=False)
        frame = load_segment_labels(csv_path)
        assert set(frame.columns) == {
            "timestamp",
            LABEL_A,
            LABEL_B,
        }
        assert "proxy_flag_cooling_degradation" not in frame.columns

    def test_labels_csv_without_final_label_raises(self, tmp_path):
        features = make_key_frame(
            {"trip_0001_seg_001": ("trip_0001", 4)}
        )
        frame = features[["timestamp"]]
        csv_path = tmp_path / "labels.csv"
        frame.to_csv(csv_path, index=False)
        with pytest.raises(ValueError, match="final_label_"):
            load_segment_labels(csv_path)
