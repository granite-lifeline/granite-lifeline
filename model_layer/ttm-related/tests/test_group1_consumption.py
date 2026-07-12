"""
Story 4 (Lucca): Group 1 feature-CSV consumption tests.

Evaluation-story evidence: characterises how the shared Story 3
validation (model/input_validation.py) behaves on mock Group 1
`feature_dataset.csv` inputs — correct, missing-column, wrong-type,
and too-short cases. Building the production Group 1 loader is
Story 5 and out of scope here.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import (  # noqa: E402
    make_group1_frame,
    write_group1_csv,
)
from model.input_validation import (  # noqa: E402
    GROUP1_REQUIRED_COLUMNS,
    PLAUSIBLE_RANGES,
    validate_required_columns,
    validate_sensor_ranges,
)


def consume_group1_csv(csv_path: Path):
    """Mirror the pipeline's consumption steps on a Group 1 CSV.

    Read, required-column check, numeric coercion of range-checked
    signals, plausibility validation — the same shared Story 3
    validation path the Story 5 loader will call.
    """
    raw = pd.read_csv(csv_path)
    validate_required_columns(
        raw.columns, GROUP1_REQUIRED_COLUMNS, str(csv_path)
    )
    for column in PLAUSIBLE_RANGES:
        if column in raw.columns:
            raw[column] = pd.to_numeric(
                raw[column], errors="coerce"
            )
    return validate_sensor_ranges(raw)


class TestGroup1Fixtures:
    def test_correct_fixture_has_all_interface_columns(self):
        frame = make_group1_frame(rows=10)
        assert list(frame.columns) == GROUP1_REQUIRED_COLUMNS
        assert len(frame) == 10

    def test_interface_column_count_is_41(self):
        # INTERFACE.md v0.6 Section 1: 10 key/condition fields
        # + 10 raw signals + 21 engineered features.
        assert len(GROUP1_REQUIRED_COLUMNS) == 41

    def test_row_identity_fields_are_per_row(self):
        frame = make_group1_frame(rows=5)
        assert list(frame["row_in_segment"]) == [1, 2, 3, 4, 5]
        assert frame["timestamp"].is_unique

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
            tmp_path / "feature_dataset.csv"
        )
        result = consume_group1_csv(path)
        assert result.notes == []
        assert result.repaired_counts == {}

    def test_extra_bookkeeping_columns_are_tolerated(
        self, tmp_path
    ):
        # Group 1's real output carries provenance columns
        # (source_file, brand, ...) beyond the interface set;
        # they must not break consumption.
        path = write_group1_csv(
            tmp_path / "enriched.csv", extra_bookkeeping=True
        )
        result = consume_group1_csv(path)
        assert result.notes == []

    def test_model_signals_route_into_detector_features(
        self, tmp_path
    ):
        from model.kit_residual_detector import (
            MODEL_SIGNALS,
            add_derived_features,
        )

        path = write_group1_csv(
            tmp_path / "feature_dataset.csv"
        )
        loaded = consume_group1_csv(path).df
        for signal in MODEL_SIGNALS:
            assert signal in loaded.columns
        # MVP recomputes internal derived equivalents until
        # Story 5 switches to Group 1's engineered features
        # (INTERFACE.md 1.3 supersession note).
        derived = add_derived_features(loaded)
        assert "load_stress" in derived.columns
        assert "maf_map_cohesion" in derived.columns
        assert "accel_pedal_channel_delta" in derived.columns


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
            drop_columns=["coolant_slope", "idle_flag"],
        )
        with pytest.raises(ValueError) as excinfo:
            consume_group1_csv(path)
        message = str(excinfo.value)
        assert "coolant_slope" in message
        assert "idle_flag" in message

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
