"""
Story 7 tests: synthetic fault injection functions (Lucca).

The injection functions perturb raw signals per the Data Layer's
Stage 4 designs (proxy_support.md) and propagate the change into
the exactly-derivable engineered columns the detector scores
(`maf_map_cohesion` via the air-load intermediates). Cohesion
z-score parameters are passed explicitly here so the tests do not
depend on the `data_layer/` delivery being present.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model.fault_injection import (  # noqa: E402
    COOLING_OFFSET_C,
    MAF_GAIN,
    MAP_GAIN,
    inject_cooling_fault,
    inject_intake_maf_fault,
)
from model.input_validation import (  # noqa: E402
    validate_sensor_ranges,
)
from group1_fixtures import make_group1_frame  # noqa: E402

# Explicit z-score parameters in the shape of
# feature_baselines.json `standardization_parameters
# .maf_map_cohesion` (values chosen near the delivered ones).
COHESION_PARAMS = {
    "maf_derived_air_load_raw": {"mean": 0.81, "std": 0.29},
    "map_derived_air_load_raw": {"mean": 786.3, "std": 296.5},
}


def expected_cohesion(maf_load: float, map_load: float) -> float:
    z_maf = (
        maf_load - COHESION_PARAMS["maf_derived_air_load_raw"]["mean"]
    ) / COHESION_PARAMS["maf_derived_air_load_raw"]["std"]
    z_map = (
        map_load - COHESION_PARAMS["map_derived_air_load_raw"]["mean"]
    ) / COHESION_PARAMS["map_derived_air_load_raw"]["std"]
    return abs(z_maf - z_map)


class TestInjectCoolingFault:
    def test_offset_applied_from_start_row_only(self):
        frame = make_group1_frame(rows=20)
        result = inject_cooling_fault(frame, start_row=10)

        before = result["coolant_temp"].iloc[:10]
        after = result["coolant_temp"].iloc[10:]
        assert (before == 92.0).all()
        assert (after == 92.0 + COOLING_OFFSET_C).all()

    def test_coolant_ambient_delta_tracks_offset(self):
        frame = make_group1_frame(rows=8)
        result = inject_cooling_fault(frame, start_row=4)

        assert (result["coolant_ambient_delta"].iloc[:4] == 70.0).all()
        assert (
            result["coolant_ambient_delta"].iloc[4:]
            == 70.0 + COOLING_OFFSET_C
        ).all()

    def test_other_columns_untouched_and_input_not_mutated(self):
        frame = make_group1_frame(rows=10)
        original = frame.copy()
        result = inject_cooling_fault(frame, start_row=0)

        pd.testing.assert_frame_equal(frame, original)
        untouched = result.drop(
            columns=["coolant_temp", "coolant_ambient_delta"]
        )
        pd.testing.assert_frame_equal(
            untouched,
            original.drop(
                columns=["coolant_temp", "coolant_ambient_delta"]
            ),
        )

    def test_custom_offset(self):
        frame = make_group1_frame(rows=5)
        result = inject_cooling_fault(frame, offset_c=5.0)
        assert (result["coolant_temp"] == 97.0).all()


class TestInjectIntakeMafFault:
    def test_low_maf_scales_maf_and_air_load(self):
        frame = make_group1_frame(rows=12)
        result = inject_intake_maf_fault(
            frame, "low_maf", COHESION_PARAMS, start_row=6
        )

        assert (result["maf"].iloc[:6] == 20.0).all()
        assert np.allclose(result["maf"].iloc[6:], 20.0 * MAF_GAIN)
        assert (
            result["maf_derived_air_load_raw"].iloc[:6] == 0.8
        ).all()
        assert np.allclose(
            result["maf_derived_air_load_raw"].iloc[6:],
            0.8 * MAF_GAIN,
        )
        # map side untouched
        assert (result["map"] == 110.0).all()
        assert (result["map_derived_air_load_raw"] == 110.0).all()

    def test_low_maf_recomputes_cohesion_on_affected_rows(self):
        frame = make_group1_frame(rows=10)
        result = inject_intake_maf_fault(
            frame, "low_maf", COHESION_PARAMS, start_row=5
        )

        assert (result["maf_map_cohesion"].iloc[:5] == 0.18).all()
        want = expected_cohesion(0.8 * MAF_GAIN, 110.0)
        assert np.allclose(result["maf_map_cohesion"].iloc[5:], want)

    def test_map_bias_scales_map_and_recomputes_cohesion(self):
        frame = make_group1_frame(rows=10)
        result = inject_intake_maf_fault(
            frame, "map_bias", COHESION_PARAMS, start_row=5
        )

        assert np.allclose(result["map"].iloc[5:], 110.0 * MAP_GAIN)
        assert np.allclose(
            result["map_derived_air_load_raw"].iloc[5:],
            110.0 * MAP_GAIN,
        )
        # maf side untouched
        assert (result["maf"] == 20.0).all()
        assert (
            result["maf_derived_air_load_raw"] == 0.8
        ).all()
        want = expected_cohesion(0.8, 110.0 * MAP_GAIN)
        assert np.allclose(result["maf_map_cohesion"].iloc[5:], want)

    def test_nan_values_stay_nan(self):
        frame = make_group1_frame(rows=6)
        frame.loc[4, "maf"] = np.nan
        frame.loc[4, "maf_derived_air_load_raw"] = np.nan
        frame.loc[4, "maf_map_cohesion"] = np.nan

        result = inject_intake_maf_fault(
            frame, "low_maf", COHESION_PARAMS, start_row=3
        )

        assert np.isnan(result.loc[4, "maf"])
        assert np.isnan(result.loc[4, "maf_derived_air_load_raw"])
        assert np.isnan(result.loc[4, "maf_map_cohesion"])
        # Neighbouring affected rows are still perturbed.
        assert np.isclose(result.loc[5, "maf"], 20.0 * MAF_GAIN)

    def test_unknown_variant_raises(self):
        frame = make_group1_frame(rows=5)
        with pytest.raises(ValueError, match="variant"):
            inject_intake_maf_fault(
                frame, "engine_on_fire", COHESION_PARAMS
            )

    def test_input_not_mutated(self):
        frame = make_group1_frame(rows=6)
        original = frame.copy()
        inject_intake_maf_fault(frame, "map_bias", COHESION_PARAMS)
        pd.testing.assert_frame_equal(frame, original)


class TestRunnerHelpers:
    """Pure helpers of run_synthetic_evaluation (no TTM run)."""

    def test_trim_to_post_warmup_drops_warmup_rows(self):
        from model.run_synthetic_evaluation import trim_to_post_warmup

        frame = make_group1_frame(rows=10)
        frame.loc[:3, "thermal_state"] = "warmup"
        trimmed = trim_to_post_warmup(frame, min_rows=5)
        assert len(trimmed) == 6
        assert (trimmed["thermal_state"] == "post_warmup").all()

    def test_trim_raises_without_post_warmup(self):
        from model.run_synthetic_evaluation import trim_to_post_warmup

        frame = make_group1_frame(rows=10)
        frame["thermal_state"] = "warmup"
        with pytest.raises(ValueError, match="never reaches"):
            trim_to_post_warmup(frame, min_rows=5)

    def test_trim_raises_when_too_short(self):
        from model.run_synthetic_evaluation import trim_to_post_warmup

        frame = make_group1_frame(rows=10)
        with pytest.raises(ValueError, match="need 20"):
            trim_to_post_warmup(frame, min_rows=20)

    def test_manifest_segments_selection(self, tmp_path):
        from model.run_synthetic_evaluation import manifest_segments

        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "train_trips": {"trip_0002": ["trip_0002_seg_001"]},
                    "validation_trips": {
                        "trip_0001": [
                            "trip_0001_seg_002",
                            "trip_0001_seg_001",
                        ]
                    },
                }
            )
        )
        assert manifest_segments(manifest, "validation") == [
            "trip_0001_seg_001",
            "trip_0001_seg_002",
        ]
        assert manifest_segments(manifest, "all") == [
            "trip_0001_seg_001",
            "trip_0001_seg_002",
            "trip_0002_seg_001",
        ]


class TestInjectedValuesStayPlausible:
    """Injected faults must survive the detector's input repair
    (validate_sensor_ranges NaNs implausible cells), otherwise the
    perturbation would be silently interpolated away."""

    def test_no_repairs_on_any_scenario(self):
        frame = make_group1_frame(rows=20)
        scenarios = [
            inject_cooling_fault(frame),
            inject_intake_maf_fault(frame, "low_maf", COHESION_PARAMS),
            inject_intake_maf_fault(
                frame, "map_bias", COHESION_PARAMS
            ),
        ]
        for injected in scenarios:
            outcome = validate_sensor_ranges(injected)
            assert outcome.repaired_counts == {}
