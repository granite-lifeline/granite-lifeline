"""
Model input contract tests for Data Layer production_features v1.

These tests check that the accepted `production_features.csv` shape is
safe to pass into the Model Layer: required fields exist, model signals
are numeric, TTM windowing has enough rows, row identity is usable, and
the schema v1 B-class production features have the expected numeric
shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import make_group1_frame  # noqa: E402
from model.input_validation import (  # noqa: E402
    PRODUCTION_FEATURE_REQUIRED_COLUMNS,
)
from model.kit_residual_detector import (  # noqa: E402
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_PREDICTION_LENGTH,
    MODEL_SIGNALS,
    select_context_and_truth,
)


B_CLASS_FEATURE_CONTRACT_RANGES: dict[str, tuple[float, float]] = {
    "segment_gap_seconds": (0.0, 200000.0),
    "coolant_ambient_delta": (-80.0, 200.0),
    "intake_ambient_delta": (-80.0, 200.0),
    "accel_pedal_mean": (0.0, 100.0),
    "accel_pedal_channel_delta": (0.0, 10.0),
    "pedal_slope": (-100.0, 100.0),
    "rpm_slope": (-1000.0, 1000.0),
    "speed_density_maf_residual": (-500.0, 500.0),
    "pedal_mapping_residual": (-100.0, 100.0),
    "elapsed_since_engine_start": (0.0, 200000.0),
    "ect_start": (-40.0, 150.0),
    "aat_start": (-40.0, 80.0),
    "iat_start": (-40.0, 215.0),
    "maf_integral_180s": (0.0, 100000.0),
    "ect_rate_180s": (-100.0, 100.0),
    "intake_temp_stability": (0.0, 100.0),
    "speed_std_120s": (0.0, 300.0),
    "maf_std_120s": (0.0, 500.0),
    "rpm_std_120s": (0.0, 8000.0),
    "accel_pedal_mean_std_120s": (0.0, 100.0),
    "map_range_60s": (0.0, 400.0),
}


def assert_b_class_features_inside_contract(frame: pd.DataFrame) -> None:
    """Assert schema v1 B-class numeric features are bounded when present."""
    for feature, (low, high) in B_CLASS_FEATURE_CONTRACT_RANGES.items():
        assert feature in frame.columns
        source = frame[feature]
        series = pd.to_numeric(source, errors="coerce")
        valid = series.dropna()
        assert source.notna().sum() == len(valid), (
            f"{feature} contains non-numeric data"
        )
        assert valid.between(low, high).all(), (
            f"{feature} outside contract range [{low}, {high}]"
        )


class TestGroup1ModelInputContract:
    def test_group1_frame_contains_all_v13_required_columns(self):
        frame = make_group1_frame(rows=10)

        assert list(frame.columns) == PRODUCTION_FEATURE_REQUIRED_COLUMNS

    def test_model_signals_are_present_numeric_and_non_null(self):
        frame = make_group1_frame(rows=10)

        for signal in MODEL_SIGNALS:
            assert signal in frame.columns
            series = pd.to_numeric(frame[signal], errors="coerce")
            assert not series.isna().any()

    def test_b_class_features_are_inside_contract_ranges(self):
        frame = make_group1_frame(rows=10)

        assert_b_class_features_inside_contract(frame)

    @pytest.mark.parametrize(
        "feature", sorted(B_CLASS_FEATURE_CONTRACT_RANGES)
    )
    def test_b_class_feature_contract_catches_out_of_range_values(
        self, feature
    ):
        low, high = B_CLASS_FEATURE_CONTRACT_RANGES[feature]
        for bad_value in (low - 1.0, high + 1.0):
            frame = make_group1_frame(rows=10)
            frame.loc[0, feature] = bad_value

            with pytest.raises(
                AssertionError,
                match=f"{feature} outside contract range",
            ):
                assert_b_class_features_inside_contract(frame)

    def test_b_class_feature_contract_catches_non_numeric_values(self):
        # B-class features are not in PLAUSIBLE_RANGES, so the
        # consumption path never type-checks them; this contract
        # check is what catches a wrong-type engineered column.
        frame = make_group1_frame(rows=10)
        frame["rpm_slope"] = "sensor_error"

        with pytest.raises(
            AssertionError, match="rpm_slope contains non-numeric"
        ):
            assert_b_class_features_inside_contract(frame)

    def test_frame_has_enough_rows_for_default_ttm_window(self):
        required_rows = DEFAULT_CONTEXT_LENGTH + DEFAULT_PREDICTION_LENGTH
        frame = make_group1_frame(rows=required_rows)

        context, future = select_context_and_truth(
            frame,
            context_length=DEFAULT_CONTEXT_LENGTH,
            prediction_length=DEFAULT_PREDICTION_LENGTH,
        )

        assert len(context) == DEFAULT_CONTEXT_LENGTH
        assert len(future) == DEFAULT_PREDICTION_LENGTH
        # Future window must start right after the context window
        # (no overlap, no gap) for residuals to be meaningful.
        assert (
            future["row_in_segment"].iloc[0]
            == context["row_in_segment"].iloc[-1] + 1
        )

    def test_row_identity_supports_segment_safe_windowing(self):
        frame = make_group1_frame(rows=20)

        assert frame["trip_id"].nunique() == 1
        assert frame["segment_id"].nunique() == 1
        assert frame["row_in_segment"].tolist() == list(range(1, 21))
        dt = pd.to_numeric(frame["dt_seconds"], errors="coerce")
        assert dt.eq(1.0).all()
        assert frame["schema_version"].eq("feature_schema.v1").all()
        assert frame["calibration_version"].eq("calibration.v1").all()
        assert frame["operating_state"].str.contains("__").any()
        parsed = pd.to_datetime(frame["timestamp"], errors="coerce")
        assert not parsed.isna().any()
        assert parsed.is_monotonic_increasing
