"""
Story 4 (Ray): model input contract tests for Group 1 output.

These tests sit after Lucca's CSV consumption tests. They check that
the accepted `feature_dataset.csv` shape is safe to pass into the
Model Layer: required fields exist, model signals are numeric, TTM
windowing has enough rows, row identity is usable, and confirmed v0.6
engineered features stay inside the Story 4 contract ranges.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import make_group1_frame  # noqa: E402
from model.input_validation import GROUP1_REQUIRED_COLUMNS  # noqa: E402
from model.kit_residual_detector import (  # noqa: E402
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_PREDICTION_LENGTH,
    MODEL_SIGNALS,
    select_context_and_truth,
)


# Story 4 contract ranges for confirmed INTERFACE.md v0.6 engineered
# features. These are deliberately input-contract checks, not final
# anomaly thresholds. They keep mock Group 1 feature values realistic
# while Story 6/7 later calibrate model and risk thresholds.
ENGINEERED_FEATURE_CONTRACT_RANGES: dict[str, tuple[float, float]] = {
    "coolant_slope": (-0.05, 0.05),
    "coolant_stability": (0.0, 2.0),
    "maf_map_cohesion": (0.0, 1.8),
    "map_slope": (-5.0, 5.0),
    "pedal_throttle_gap": (-10.0, 10.0),
    "accel_pedal_channel_delta": (0.0, 10.0),
    "rpm_slope": (-100.0, 100.0),
    "idle_rpm_stability": (0.0, 200.0),
}


def assert_features_inside_contract(frame: pd.DataFrame) -> None:
    """Assert all Story 4 engineered features are numeric and bounded."""
    for feature, (low, high) in ENGINEERED_FEATURE_CONTRACT_RANGES.items():
        assert feature in frame.columns
        series = pd.to_numeric(frame[feature], errors="coerce")
        assert not series.isna().any(), f"{feature} contains non-numeric data"
        assert series.between(low, high).all(), (
            f"{feature} outside contract range [{low}, {high}]"
        )


class TestGroup1ModelInputContract:
    def test_group1_frame_contains_all_v06_required_columns(self):
        frame = make_group1_frame(rows=10)

        assert list(frame.columns) == GROUP1_REQUIRED_COLUMNS

    def test_model_signals_are_present_numeric_and_non_null(self):
        frame = make_group1_frame(rows=10)

        for signal in MODEL_SIGNALS:
            assert signal in frame.columns
            series = pd.to_numeric(frame[signal], errors="coerce")
            assert not series.isna().any()

    def test_confirmed_engineered_features_are_inside_contract_ranges(self):
        frame = make_group1_frame(rows=10)

        assert_features_inside_contract(frame)

    @pytest.mark.parametrize(
        "feature", sorted(ENGINEERED_FEATURE_CONTRACT_RANGES)
    )
    def test_engineered_feature_contract_catches_out_of_range_values(
        self, feature
    ):
        low, high = ENGINEERED_FEATURE_CONTRACT_RANGES[feature]
        for bad_value in (low - 1.0, high + 1.0):
            frame = make_group1_frame(rows=10)
            frame.loc[0, feature] = bad_value

            with pytest.raises(
                AssertionError,
                match=f"{feature} outside contract range",
            ):
                assert_features_inside_contract(frame)

    def test_engineered_feature_contract_catches_non_numeric_values(self):
        # Engineered features are not in PLAUSIBLE_RANGES, so the
        # consumption path never type-checks them; this contract
        # check is what catches a wrong-type engineered column.
        frame = make_group1_frame(rows=10)
        frame["rpm_slope"] = "sensor_error"

        with pytest.raises(
            AssertionError, match="rpm_slope contains non-numeric"
        ):
            assert_features_inside_contract(frame)

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
        parsed = pd.to_datetime(frame["timestamp"], errors="coerce")
        assert not parsed.isna().any()
        assert parsed.is_monotonic_increasing
