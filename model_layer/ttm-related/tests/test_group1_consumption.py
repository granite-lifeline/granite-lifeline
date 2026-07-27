"""
Model input consumption tests for Data Layer production features.

Characterises how `load_group1_features` + `prepare_segment` behave
on Data Layer `production_features.csv` v1 inputs: the tracked fixture,
missing-column, wrong-type, stale-contract, and too-short cases.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import (  # noqa: E402
    PRODUCTION_FIXTURE_CSV,
    make_group1_frame,
    write_group1_csv,
)
from model.input_validation import (  # noqa: E402
    PRODUCTION_FEATURE_REQUIRED_COLUMNS,
)
from model.kit_residual_detector import (  # noqa: E402
    load_group1_features,
    prepare_segment,
    select_segment,
)


def consume_group1_csv(csv_path: Path):
    """Run the pipeline's production consumption steps on a CSV:
    load + column/numeric validation, then plausibility repair."""
    df = load_group1_features(csv_path)
    repaired, notes = prepare_segment(df)
    return repaired, notes


class TestGroup1Fixtures:
    def test_tracked_fixture_has_all_interface_columns(self):
        frame = pd.read_csv(PRODUCTION_FIXTURE_CSV)
        assert list(frame.columns) == PRODUCTION_FEATURE_REQUIRED_COLUMNS
        assert len(frame.columns) == 46
        assert len(frame) > 0

    def test_generated_fixture_has_all_interface_columns(self):
        frame = make_group1_frame(rows=10)
        assert list(frame.columns) == PRODUCTION_FEATURE_REQUIRED_COLUMNS
        assert len(frame) == 10

    def test_interface_column_count_is_46(self):
        # INTERFACE.md v0.13: 4 sample keys + 16 A-class
        # context/raw columns + 24 B-class features + 2 provenance.
        assert len(PRODUCTION_FEATURE_REQUIRED_COLUMNS) == 46

    def test_row_identity_fields_are_per_row(self):
        frame = make_group1_frame(rows=5)
        assert list(frame["row_in_segment"]) == [1, 2, 3, 4, 5]
        assert frame["timestamp"].is_unique
        assert frame["dt_seconds"].eq(1.0).all()
        assert frame["operating_state"].str.contains("__").any()

    def test_drop_columns_builds_missing_column_case(
        self, tmp_path
    ):
        path = write_group1_csv(
            tmp_path / "missing.csv", drop_columns=["maf"]
        )
        header = pd.read_csv(path, nrows=0).columns
        assert "maf" not in header
        assert "rpm" in header

    def test_wrong_type_columns_are_non_numeric(self, tmp_path):
        path = write_group1_csv(
            tmp_path / "wrong_type.csv",
            wrong_type_columns=["coolant_temp"],
        )
        raw = pd.read_csv(path)
        coerced = pd.to_numeric(
            raw["coolant_temp"], errors="coerce"
        )
        assert coerced.isna().all()


class TestGroup1NormalConsumption:
    def test_correct_fixture_consumes_clean(self, tmp_path):
        path = write_group1_csv(
            tmp_path / "production_features.csv"
        )
        _, notes = consume_group1_csv(path)
        assert notes == []

    def test_tracked_data_layer_fixture_consumes_clean(self):
        _, notes = consume_group1_csv(PRODUCTION_FIXTURE_CSV)
        assert notes == []

    def test_extra_bookkeeping_columns_are_tolerated(
        self, tmp_path
    ):
        # Group 1's real output carries provenance columns
        # (source_file, brand, ...) beyond the interface set;
        # they must not break consumption.
        path = write_group1_csv(
            tmp_path / "enriched.csv", extra_bookkeeping=True
        )
        _, notes = consume_group1_csv(path)
        assert notes == []

    def test_model_signals_and_features_come_from_group1(
        self, tmp_path
    ):
        from model.kit_residual_detector import MODEL_SIGNALS

        path = write_group1_csv(
            tmp_path / "production_features.csv"
        )
        loaded, _ = consume_group1_csv(path)
        for signal in MODEL_SIGNALS:
            assert signal in loaded.columns
        # B-class production features are consumed directly from
        # Data Layer columns — nothing is recomputed internally.
        assert "speed_density_maf_residual" in loaded.columns
        assert "accel_pedal_channel_delta" in loaded.columns
        pd.testing.assert_series_equal(
            loaded["speed_density_maf_residual"],
            make_group1_frame(rows=len(loaded))[
                "speed_density_maf_residual"
            ],
            check_names=False,
            check_exact=False,
            rtol=1e-12,
        )


class TestSegmentSelection:
    def make_multi_segment_frame(self):
        first = make_group1_frame(rows=650)
        second = make_group1_frame(rows=750)
        second["segment_id"] = "trip_0001_seg_002"
        third = make_group1_frame(rows=800)
        third["trip_id"] = "trip_0002"
        third["segment_id"] = "trip_0002_seg_001"
        return pd.concat(
            [first, second, third], ignore_index=True
        )

    def test_default_picks_first_segment_with_enough_rows(self):
        df = self.make_multi_segment_frame()
        segment = select_segment(df)
        # First segment (650 rows) is below the INTERFACE.md 1.5
        # minimum of 700; the second qualifies.
        assert segment["segment_id"].unique().tolist() == [
            "trip_0001_seg_002"
        ]
        assert len(segment) == 750

    def test_selected_window_never_crosses_segments(self):
        from model.kit_residual_detector import (
            select_context_and_truth,
        )

        df = self.make_multi_segment_frame()
        segment = select_segment(df)
        context, future = select_context_and_truth(
            segment, context_length=512, prediction_length=96
        )
        window = pd.concat([context, future])
        assert window["segment_id"].nunique() == 1

    def test_trip_and_segment_flags_are_honoured(self):
        df = self.make_multi_segment_frame()
        by_trip = select_segment(df, trip_id="trip_0002")
        assert by_trip["trip_id"].unique().tolist() == ["trip_0002"]
        by_segment = select_segment(
            df, segment_id="trip_0001_seg_002"
        )
        assert by_segment["segment_id"].unique().tolist() == [
            "trip_0001_seg_002"
        ]

    def test_unknown_ids_and_short_segments_raise(self):
        df = self.make_multi_segment_frame()
        with pytest.raises(ValueError, match="trip_9999"):
            select_segment(df, trip_id="trip_9999")
        with pytest.raises(ValueError, match="seg_042"):
            select_segment(df, segment_id="trip_0001_seg_042")
        short_only = make_group1_frame(rows=100)
        with pytest.raises(ValueError, match="700"):
            select_segment(short_only)


class TestGroup1BadInput:
    def test_missing_raw_signal_raises_named_error(
        self, tmp_path
    ):
        path = write_group1_csv(
            tmp_path / "missing.csv", drop_columns=["maf"]
        )
        with pytest.raises(ValueError) as excinfo:
            consume_group1_csv(path)
        assert "maf" in str(excinfo.value)
        assert "missing.csv" in str(excinfo.value)

    def test_missing_engineered_features_raise_named_error(
        self, tmp_path
    ):
        path = write_group1_csv(
            tmp_path / "missing_feature.csv",
            drop_columns=["ect_rate_180s", "map_range_60s"],
        )
        with pytest.raises(ValueError) as excinfo:
            consume_group1_csv(path)
        message = str(excinfo.value)
        assert "ect_rate_180s" in message
        assert "map_range_60s" in message

    def test_nullable_dt_seconds_is_rejected(self, tmp_path):
        path = write_group1_csv(tmp_path / "bad_dt.csv")
        frame = pd.read_csv(path)
        frame.loc[0, "dt_seconds"] = pd.NA
        frame.to_csv(path, index=False)
        with pytest.raises(ValueError, match="dt_seconds"):
            consume_group1_csv(path)

    def test_single_underscore_operating_state_is_rejected(self, tmp_path):
        path = write_group1_csv(tmp_path / "bad_state.csv")
        frame = pd.read_csv(path)
        frame.loc[0, "operating_state"] = "post_warmup_steady_driving"
        frame.to_csv(path, index=False)
        with pytest.raises(ValueError, match="operating_state"):
            consume_group1_csv(path)

    def test_wrong_type_raw_signal_raises_clear_error(
        self, tmp_path
    ):
        # Non-numeric strings coerce to all-NaN; the shared
        # validation must reject the column by name rather
        # than silently producing wrong results.
        path = write_group1_csv(
            tmp_path / "wrong_type.csv",
            wrong_type_columns=["coolant_temp"],
        )
        with pytest.raises(ValueError) as excinfo:
            consume_group1_csv(path)
        assert "coolant_temp" in str(excinfo.value)

    def test_below_minimum_rows_raises_clear_error(
        self, tmp_path
    ):
        from model.kit_residual_detector import (
            select_context_and_truth,
        )

        frame = make_group1_frame(rows=50)
        with pytest.raises(ValueError) as excinfo:
            select_context_and_truth(
                frame, context_length=512, prediction_length=96
            )
        message = str(excinfo.value)
        assert "608" in message
        assert "50" in message
