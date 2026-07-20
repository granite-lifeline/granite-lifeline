from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from group1_fixtures import make_multi_segment_frame  # noqa: E402
from model.finetune_ttm import (  # noqa: E402
    build_forecast_dataset,
    filter_by_segments,
    flatten_segment_ids,
    validate_segment_contiguity,
    sample_shapes,
)
from model.kit_residual_detector import (  # noqa: E402
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_PREDICTION_LENGTH,
    MODEL_SIGNALS,
)


def test_flatten_segment_ids_accepts_trip_grouped_manifest_shape():
    split = {
        "trip_b": ["trip_b_seg_001"],
        "trip_a": ["trip_a_seg_001", "trip_a_seg_002"],
    }

    assert flatten_segment_ids(split) == [
        "trip_a_seg_001",
        "trip_a_seg_002",
        "trip_b_seg_001",
    ]


def test_filter_by_segments_rejects_manifest_segment_not_in_feature_frame():
    frame = make_multi_segment_frame(
        [("trip_001", "trip_001_seg_001", 700)]
    )

    with pytest.raises(ValueError, match="missing segment ids"):
        filter_by_segments(
            frame, ["trip_999_seg_001"], split_name="validation"
        )


def test_build_forecast_dataset_uses_ttm_context_and_prediction_shapes():
    frame = make_multi_segment_frame(
        [("trip_001", "trip_001_seg_001", 700)]
    )
    dataset = build_forecast_dataset(
        frame,
        context_length=DEFAULT_CONTEXT_LENGTH,
        prediction_length=DEFAULT_PREDICTION_LENGTH,
        stride=DEFAULT_PREDICTION_LENGTH,
    )

    shapes = sample_shapes(dataset)

    assert len(dataset) >= 1
    assert shapes["past_values"] == [
        DEFAULT_CONTEXT_LENGTH,
        len(MODEL_SIGNALS),
    ]
    assert shapes["future_values"] == [
        DEFAULT_PREDICTION_LENGTH,
        len(MODEL_SIGNALS),
    ]


def test_build_forecast_dataset_rejects_non_numeric_model_signal():
    frame = make_multi_segment_frame(
        [("trip_001", "trip_001_seg_001", 700)]
    )
    frame["rpm"] = frame["rpm"].astype(object)
    frame.loc[0, "rpm"] = "bad_rpm"

    with pytest.raises(ValueError, match="rpm contains non-numeric"):
        build_forecast_dataset(
            frame,
            context_length=DEFAULT_CONTEXT_LENGTH,
            prediction_length=DEFAULT_PREDICTION_LENGTH,
            stride=DEFAULT_PREDICTION_LENGTH,
        )


def test_segment_contiguity_rejects_missing_row_inside_segment():
    frame = make_multi_segment_frame(
        [("trip_001", "trip_001_seg_001", 700)]
    ).drop(index=20)
    with pytest.raises(ValueError, match="row_in_segment"):
        validate_segment_contiguity(frame, "train")


def test_forecast_dataset_handles_schema_v1_signal_nans_with_masks():
    frame = make_multi_segment_frame(
        [("trip_001", "trip_001_seg_001", 700)]
    )
    frame.loc[10, "maf"] = float("nan")
    dataset = build_forecast_dataset(
        frame,
        context_length=DEFAULT_CONTEXT_LENGTH,
        prediction_length=DEFAULT_PREDICTION_LENGTH,
        stride=DEFAULT_PREDICTION_LENGTH,
    )
    sample = dataset[0]
    maf_index = MODEL_SIGNALS.index("maf")
    assert sample["past_observed_mask"][10, maf_index].item() == 0
    assert sample["past_values"][10, maf_index].isfinite().item()
