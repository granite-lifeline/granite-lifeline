from model.risk_level_calibration import (
    alarm_threshold,
    load_risk_level_calibration,
    risk_level,
)
from model.risk_threshold_calibration import choose_threshold, split_segments


def primary_row(segment_id):
    return {
        "segment_id": segment_id,
        "evaluation_role": "primary",
        "risk_score": 0.5,
    }


def test_versioned_policy_defines_the_detector_boundaries():
    policy = load_risk_level_calibration()

    assert policy["calibration_version"] == "model-risk-level.v1"
    assert alarm_threshold() == 0.4129
    assert risk_level(0.4128) == "Low"
    assert risk_level(0.4129) == "Medium"
    assert risk_level(0.8999) == "Medium"
    assert risk_level(0.9) == "High"


def test_threshold_choice_requires_the_declared_false_alarm_limit():
    candidates = [
        {
            "threshold": 0.3,
            "macro_f1": 0.70,
            "exact_hit_rate": 0.70,
            "healthy_false_positive_rate": 0.20,
        },
        {
            "threshold": 0.4,
            "macro_f1": 0.55,
            "exact_hit_rate": 0.50,
            "healthy_false_positive_rate": 0.10,
        },
        {
            "threshold": 0.5,
            "macro_f1": 0.50,
            "exact_hit_rate": 0.40,
            "healthy_false_positive_rate": 0.00,
        },
    ]

    assert choose_threshold(candidates)["threshold"] == 0.4


def test_every_third_segment_is_reserved_for_holdout():
    records = [
        primary_row(f"trip_{number:04}_seg_001") for number in range(1, 7)
    ]

    calibration, held_out = split_segments(records)

    assert held_out == ["trip_0003_seg_001", "trip_0006_seg_001"]
    assert calibration == [
        "trip_0001_seg_001", "trip_0002_seg_001",
        "trip_0004_seg_001", "trip_0005_seg_001",
    ]
