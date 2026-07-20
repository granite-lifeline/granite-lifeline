"""
Story 7 tests: synthetic fault injection functions (Lucca).

The two active injectors perturb raw signals per the Data Layer's
Stage 4 designs (proxy_support.md) and propagate the change into the
schema v1 engineered columns the detector scores (`ect_rate_180s`,
`speed_density_maf_residual`). The speed-density transform is passed
explicitly here (shaped like `load_speed_density_transform()`'s
return value) so the tests do not depend on the `data_layer/`
delivery being present; values match the frozen
`calibration_registry.v1.json` so the test also serves as an
informal cross-check.

The three pending-type injectors (`inject_intake_air_temp_fault`,
`inject_map_plausibility_fault`, `inject_idle_speed_fault`) are
frozen historical code not migrated to schema v1 — see
fault_injection.py's module docstring and GL-322. Their test classes
are skipped rather than deleted, so the coverage intent stays
documented pending their formal retirement.

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
    ECT_RATE_WINDOW_ROWS,
    IDLE_OFFSET_RPM,
    IDLE_OSC_AMPLITUDE_RPM,
    IDLE_OSC_PERIOD_S,
    KELVIN_OFFSET,
    MAF_GAIN,
    MAP_GAIN,
    inject_cooling_fault,
    inject_idle_speed_fault,
    inject_intake_air_temp_fault,
    inject_intake_maf_fault,
    inject_map_plausibility_fault,
)
from model.input_validation import (  # noqa: E402
    validate_sensor_ranges,
)
from group1_fixtures import make_group1_frame  # noqa: E402

# Explicit z-score parameters in the shape of the pre-migration
# feature_baselines.json `standardization_parameters
# .maf_map_cohesion` — only used by the skipped pending-type tests
# below, which still exercise the frozen pre-migration formulas.
COHESION_PARAMS = {
    "maf_derived_air_load_raw": {"mean": 0.81, "std": 0.29},
    "map_derived_air_load_raw": {"mean": 786.3, "std": 296.5},
}

# Pre-migration speed-density regression shape (feature_baselines.json
# `models.speed_density_model`) — only used by the skipped
# pending-type tests below.
SD_MODEL = {
    "coefficients": {
        "map_derived_air_load_raw": 0.0238,
        "map": 0.1413,
        "rpm": 6.69e-05,
        "intake_temp": 0.071,
    },
    "intercept": -14.689,
    "winsorize_bounds": {
        "map_derived_air_load_raw": {
            "lower": 0.0, "upper": 4000.0,
        },
        "map": {"lower": 0.0, "upper": 400.0},
        "rpm": {"lower": 0.0, "upper": 8000.0},
        "intake_temp": {"lower": -40.0, "upper": 150.0},
    },
}

# Schema v1 speed-density transform, shaped like
# load_speed_density_transform()'s return value. Values match the
# frozen calibration_registry.v1.json
# `feature_transforms.speed_density_maf`.
SPEED_DENSITY_TRANSFORM = {
    "coefficients": {
        "map_derived_air_load_raw": 0.023778032668470294,
        "map": 0.14127609145896305,
        "rpm": 0.00006690047685838753,
        "intake_temp": 0.07101467711912292,
    },
    "intercept": -14.688826051927967,
    "ordered_input_features": [
        "map_derived_air_load_raw", "map", "rpm", "intake_temp",
    ],
    "prediction_clipping_bounds": {
        "map_derived_air_load_raw": {
            "lower": 293.93209175000004, "upper": 1516.36693525,
        },
        "map": {"lower": 94.0, "upper": 203.0},
        "rpm": {"lower": 877.0, "upper": 2205.0},
        "intake_temp": {"lower": -8.0, "upper": 40.0},
    },
}


def expected_cohesion(maf_load: float, map_load: float) -> float:
    z_maf = (
        maf_load - COHESION_PARAMS["maf_derived_air_load_raw"]["mean"]
    ) / COHESION_PARAMS["maf_derived_air_load_raw"]["std"]
    z_map = (
        map_load - COHESION_PARAMS["map_derived_air_load_raw"]["mean"]
    ) / COHESION_PARAMS["map_derived_air_load_raw"]["std"]
    return abs(z_maf - z_map)


def expected_speed_density(
    maf: float,
    map_load: float,
    map_kpa: float,
    rpm: float,
    intake_temp: float,
) -> float:
    coef = SD_MODEL["coefficients"]
    bounds = SD_MODEL["winsorize_bounds"]
    inputs = {
        "map_derived_air_load_raw": map_load,
        "map": map_kpa,
        "rpm": rpm,
        "intake_temp": intake_temp,
    }
    predicted = SD_MODEL["intercept"]
    for name, value in inputs.items():
        clipped = min(
            max(value, bounds[name]["lower"]),
            bounds[name]["upper"],
        )
        predicted += coef[name] * clipped
    return maf - predicted


def expected_map_load(
    map_kpa: float, rpm: float, intake_temp: float
) -> float:
    return map_kpa * rpm / (intake_temp + KELVIN_OFFSET)


def expected_speed_density_residual_v1(
    maf: float, map_kpa: float, rpm: float, intake_temp: float
) -> float:
    """Mirrors recompute_speed_density_maf_residual() against
    SPEED_DENSITY_TRANSFORM (schema v1 formula)."""
    raw_load = expected_map_load(map_kpa, rpm, intake_temp)
    inputs = {
        "map_derived_air_load_raw": raw_load,
        "map": map_kpa,
        "rpm": rpm,
        "intake_temp": intake_temp,
    }
    coef = SPEED_DENSITY_TRANSFORM["coefficients"]
    bounds = SPEED_DENSITY_TRANSFORM["prediction_clipping_bounds"]
    predicted = SPEED_DENSITY_TRANSFORM["intercept"]
    for name in SPEED_DENSITY_TRANSFORM["ordered_input_features"]:
        clipped = min(
            max(inputs[name], bounds[name]["lower"]),
            bounds[name]["upper"],
        )
        predicted += coef[name] * clipped
    return maf - predicted


def assert_recompute_matches(
    before: pd.Series, after: pd.Series, expected: pd.Series
) -> None:
    """Where ``before`` was finite, ``after`` must equal
    ``expected``; where ``before`` was NaN (delivered policy NaN),
    ``after`` stays NaN too (masked_assign's preserved mask)."""
    finite = before.notna()
    assert np.allclose(after[finite], expected[finite])
    assert after[~finite].isna().all()


class TestInjectCoolingFault:
    def test_offset_applied_from_start_row_only(self):
        frame = make_group1_frame(rows=20)
        result = inject_cooling_fault(frame, start_row=10)

        before = frame["coolant_temp"]
        assert (result["coolant_temp"].iloc[:10] == before.iloc[:10]).all()
        assert np.allclose(
            result["coolant_temp"].iloc[10:],
            before.iloc[10:] + COOLING_OFFSET_C,
        )

    def test_coolant_ambient_delta_tracks_offset(self):
        frame = make_group1_frame(rows=8)
        result = inject_cooling_fault(frame, start_row=4)

        before = frame["coolant_ambient_delta"]
        pd.testing.assert_series_equal(
            result["coolant_ambient_delta"].iloc[:4], before.iloc[:4]
        )
        assert np.allclose(
            result["coolant_ambient_delta"].iloc[4:],
            before.iloc[4:] + COOLING_OFFSET_C,
        )

    def test_ect_rate_180s_recomputed(self):
        # make_group1_frame tiles a 186-row fixture, so a window
        # this long straddles a tile boundary — compare against a
        # baseline computed directly from this frame's own
        # (pre-injection) coolant_temp, not the delivered
        # ect_rate_180s column, which the tiling makes discontinuous
        # across repeats.
        frame = make_group1_frame(rows=400)
        start_row = 200
        result = inject_cooling_fault(frame, start_row=start_row)

        coolant = frame["coolant_temp"].astype(float)
        baseline_rate = (
            coolant - coolant.shift(ECT_RATE_WINDOW_ROWS)
        ) / 3.0
        delivered = frame["ect_rate_180s"]
        after = result["ect_rate_180s"]

        # Pre-onset rows: untouched.
        pd.testing.assert_series_equal(
            after.iloc[:start_row], delivered.iloc[:start_row]
        )
        # Rows within one window of onset: only the t endpoint is
        # offset (t-180s falls before start_row), so the rate shifts
        # by offset_c/3 relative to this frame's own baseline.
        window_end = start_row + ECT_RATE_WINDOW_ROWS
        assert_recompute_matches(
            delivered.iloc[start_row:window_end],
            after.iloc[start_row:window_end],
            baseline_rate.iloc[start_row:window_end]
            + COOLING_OFFSET_C / 3,
        )
        # Rows a full window past onset: both (t, t-180s) endpoints
        # are inside the offset region, so the rate reverts to the
        # baseline.
        assert_recompute_matches(
            delivered.iloc[window_end:],
            after.iloc[window_end:],
            baseline_rate.iloc[window_end:],
        )

    def test_other_columns_untouched_and_input_not_mutated(self):
        frame = make_group1_frame(rows=10)
        original = frame.copy()
        result = inject_cooling_fault(frame, start_row=0)

        pd.testing.assert_frame_equal(frame, original)
        touched = [
            "coolant_temp", "coolant_ambient_delta", "ect_rate_180s",
        ]
        untouched = result.drop(columns=touched)
        pd.testing.assert_frame_equal(
            untouched, original.drop(columns=touched)
        )

    def test_custom_offset(self):
        frame = make_group1_frame(rows=5)
        result = inject_cooling_fault(frame, offset_c=5.0)
        assert np.allclose(
            result["coolant_temp"], frame["coolant_temp"] + 5.0
        )


class TestInjectIntakeMafFault:
    def test_low_maf_scales_maf_only(self):
        frame = make_group1_frame(rows=12)
        result = inject_intake_maf_fault(
            frame, "low_maf", SPEED_DENSITY_TRANSFORM, start_row=6
        )

        before = frame["maf"]
        assert (result["maf"].iloc[:6] == before.iloc[:6]).all()
        assert np.allclose(
            result["maf"].iloc[6:], before.iloc[6:] * MAF_GAIN
        )
        # map side untouched
        assert (result["map"] == frame["map"]).all()

    def test_low_maf_recomputes_residual_on_affected_rows(self):
        frame = make_group1_frame(rows=10)
        result = inject_intake_maf_fault(
            frame, "low_maf", SPEED_DENSITY_TRANSFORM, start_row=5
        )

        before = frame["speed_density_maf_residual"]
        after = result["speed_density_maf_residual"]
        pd.testing.assert_series_equal(
            after.iloc[:5], before.iloc[:5]
        )
        expected = pd.Series(
            [
                expected_speed_density_residual_v1(
                    frame["maf"].iloc[i] * MAF_GAIN,
                    frame["map"].iloc[i],
                    frame["rpm"].iloc[i],
                    frame["intake_temp"].iloc[i],
                )
                for i in range(5, 10)
            ],
            index=before.index[5:10],
        )
        assert_recompute_matches(
            before.iloc[5:], after.iloc[5:], expected
        )

    def test_map_bias_scales_map_only_and_recomputes_residual(self):
        frame = make_group1_frame(rows=10)
        result = inject_intake_maf_fault(
            frame, "map_bias", SPEED_DENSITY_TRANSFORM, start_row=5
        )

        before_map = frame["map"]
        assert np.allclose(
            result["map"].iloc[5:], before_map.iloc[5:] * MAP_GAIN
        )
        # maf side untouched
        assert (result["maf"] == frame["maf"]).all()

        before = frame["speed_density_maf_residual"]
        after = result["speed_density_maf_residual"]
        expected = pd.Series(
            [
                expected_speed_density_residual_v1(
                    frame["maf"].iloc[i],
                    frame["map"].iloc[i] * MAP_GAIN,
                    frame["rpm"].iloc[i],
                    frame["intake_temp"].iloc[i],
                )
                for i in range(5, 10)
            ],
            index=before.index[5:10],
        )
        assert_recompute_matches(
            before.iloc[5:], after.iloc[5:], expected
        )

    def test_nan_values_stay_nan(self):
        frame = make_group1_frame(rows=6)
        frame.loc[4, "maf"] = np.nan
        frame.loc[4, "speed_density_maf_residual"] = np.nan

        result = inject_intake_maf_fault(
            frame, "low_maf", SPEED_DENSITY_TRANSFORM, start_row=3
        )

        assert np.isnan(result.loc[4, "maf"])
        assert np.isnan(result.loc[4, "speed_density_maf_residual"])
        # Neighbouring affected row is still perturbed.
        assert np.isclose(
            result.loc[5, "maf"], frame.loc[5, "maf"] * MAF_GAIN
        )

    def test_unknown_variant_raises(self):
        frame = make_group1_frame(rows=5)
        with pytest.raises(ValueError, match="variant"):
            inject_intake_maf_fault(
                frame, "engine_on_fire", SPEED_DENSITY_TRANSFORM
            )

    def test_input_not_mutated(self):
        frame = make_group1_frame(rows=6)
        original = frame.copy()
        inject_intake_maf_fault(
            frame, "map_bias", SPEED_DENSITY_TRANSFORM
        )
        pd.testing.assert_frame_equal(frame, original)


@pytest.mark.skip(
    reason=(
        "frozen historical scenario, not migrated to schema v1 — "
        "GL-322"
    )
)
class TestInjectIntakeAirTempFault:
    def make_frame(self, rows: int = 12) -> pd.DataFrame:
        frame = make_group1_frame(rows)
        # Varying IAT so freezing is visible (fixture default is
        # constant).
        frame["intake_temp"] = 30.0 + 0.5 * np.arange(rows)
        return frame

    def test_frozen_from_start_row_only(self):
        frame = self.make_frame()
        result = inject_intake_air_temp_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=6
        )

        assert np.allclose(
            result["intake_temp"].iloc[:6],
            frame["intake_temp"].iloc[:6],
        )
        assert (result["intake_temp"].iloc[6:] == 33.0).all()

    def test_delta_and_slope_propagate(self):
        frame = self.make_frame()
        result = inject_intake_air_temp_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=6
        )

        # Pre-onset rows keep the delivered values.
        assert (result["intake_ambient_delta"].iloc[:6] == 13.0).all()
        assert (result["intake_temp_slope"].iloc[:6] == 0.05).all()
        # Frozen region: delta tracks the frozen value; the slope
        # is the onset step then flat zero.
        assert np.allclose(
            result["intake_ambient_delta"].iloc[6:], 33.0 - 22.0
        )
        assert np.isclose(result["intake_temp_slope"].iloc[6], 0.5)
        assert (result["intake_temp_slope"].iloc[7:] == 0.0).all()

    def test_air_load_cohesion_speed_density_recomputed(self):
        frame = self.make_frame()
        result = inject_intake_air_temp_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=6
        )

        want_load = expected_map_load(110.0, 1500.0, 33.0)
        assert np.allclose(
            result["map_derived_air_load_raw"].iloc[6:], want_load
        )
        want_cohesion = expected_cohesion(0.8, want_load)
        assert np.allclose(
            result["maf_map_cohesion"].iloc[6:], want_cohesion
        )
        want_residual = expected_speed_density(
            20.0, want_load, 110.0, 1500.0, 33.0
        )
        assert np.allclose(
            result["speed_density_maf_residual"].iloc[6:],
            want_residual,
        )
        # Pre-onset rows keep the delivered values.
        assert (
            result["map_derived_air_load_raw"].iloc[:6] == 110.0
        ).all()
        assert (result["maf_map_cohesion"].iloc[:6] == 0.18).all()
        assert (
            result["speed_density_maf_residual"].iloc[:6] == 1.2
        ).all()

    def test_nan_values_stay_nan(self):
        frame = self.make_frame()
        nan_columns = [
            "intake_temp",
            "intake_ambient_delta",
            "intake_temp_slope",
            "map_derived_air_load_raw",
            "maf_map_cohesion",
            "speed_density_maf_residual",
        ]
        frame.loc[8, nan_columns] = np.nan

        result = inject_intake_air_temp_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=6
        )

        for column in nan_columns:
            assert np.isnan(result.loc[8, column]), column
        # Neighbouring affected rows are still frozen.
        assert result.loc[9, "intake_temp"] == 33.0

    def test_raises_when_onset_value_not_finite(self):
        frame = self.make_frame()
        frame.loc[6, "intake_temp"] = np.nan
        with pytest.raises(ValueError, match="freeze"):
            inject_intake_air_temp_fault(
                frame, COHESION_PARAMS, SD_MODEL, start_row=6
            )

    def test_input_not_mutated(self):
        frame = self.make_frame()
        original = frame.copy()
        inject_intake_air_temp_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=3
        )
        pd.testing.assert_frame_equal(frame, original)


@pytest.mark.skip(
    reason=(
        "frozen historical scenario, not migrated to schema v1 — "
        "GL-322"
    )
)
class TestInjectMapPlausibilityFault:
    def make_frame(self, rows: int = 12) -> pd.DataFrame:
        frame = make_group1_frame(rows)
        frame["map"] = 100.0 + np.arange(rows, dtype=float)
        return frame

    def test_frozen_from_start_row(self):
        frame = self.make_frame()
        result = inject_map_plausibility_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=5
        )

        assert np.allclose(
            result["map"].iloc[:5], frame["map"].iloc[:5]
        )
        assert (result["map"].iloc[5:] == 105.0).all()

    def test_air_load_cohesion_speed_density_recomputed(self):
        frame = self.make_frame()
        result = inject_map_plausibility_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=5
        )

        want_load = expected_map_load(105.0, 1500.0, 35.0)
        assert np.allclose(
            result["map_derived_air_load_raw"].iloc[5:], want_load
        )
        want_cohesion = expected_cohesion(0.8, want_load)
        assert np.allclose(
            result["maf_map_cohesion"].iloc[5:], want_cohesion
        )
        want_residual = expected_speed_density(
            20.0, want_load, 105.0, 1500.0, 35.0
        )
        assert np.allclose(
            result["speed_density_maf_residual"].iloc[5:],
            want_residual,
        )
        # maf side untouched.
        assert (result["maf"] == 20.0).all()
        assert (
            result["maf_derived_air_load_raw"] == 0.8
        ).all()

    def test_input_not_mutated(self):
        frame = self.make_frame()
        original = frame.copy()
        inject_map_plausibility_fault(
            frame, COHESION_PARAMS, SD_MODEL
        )
        pd.testing.assert_frame_equal(frame, original)


@pytest.mark.skip(
    reason=(
        "frozen historical scenario, not migrated to schema v1 — "
        "GL-322"
    )
)
class TestInjectIdleSpeedFault:
    IDLE_START = 8
    IDLE_END = 16  # exclusive

    def make_frame(self, rows: int = 20) -> pd.DataFrame:
        frame = make_group1_frame(rows)
        idle_rows = frame.index[self.IDLE_START:self.IDLE_END]
        frame.loc[idle_rows, "idle_flag"] = 1.0
        frame.loc[idle_rows, "rpm"] = 800.0
        return frame

    def expected_rpm(self, row: int, start_row: int) -> float:
        wave = IDLE_OSC_AMPLITUDE_RPM * np.sin(
            2.0 * np.pi * (row - start_row) / IDLE_OSC_PERIOD_S
        )
        return 800.0 + IDLE_OFFSET_RPM + wave

    def test_offset_and_wave_on_idle_rows_only(self):
        frame = self.make_frame()
        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )

        for row in range(len(result)):
            if self.IDLE_START <= row < self.IDLE_END:
                assert np.isclose(
                    result.loc[row, "rpm"],
                    self.expected_rpm(row, start_row=4),
                ), row
            else:
                assert result.loc[row, "rpm"] == 1500.0, row

    def test_idle_flag_and_engine_on_unchanged(self):
        frame = self.make_frame()
        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )
        pd.testing.assert_series_equal(
            result["idle_flag"], frame["idle_flag"]
        )
        pd.testing.assert_series_equal(
            result["engine_on_flag"], frame["engine_on_flag"]
        )

    def test_slope_recomputed(self):
        frame = self.make_frame()
        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )

        # Pre-onset rows keep the delivered slope.
        assert (result["rpm_slope"].iloc[:4] == 12.0).all()
        first = self.IDLE_START
        assert np.isclose(
            result.loc[first, "rpm_slope"],
            result.loc[first, "rpm"] - 1500.0,
        )
        assert np.isclose(
            result.loc[first + 1, "rpm_slope"],
            result.loc[first + 1, "rpm"]
            - result.loc[first, "rpm"],
        )

    def test_air_loads_recomputed_on_idle_rows_only(self):
        frame = self.make_frame()
        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )

        for row in range(4, len(result)):
            if self.IDLE_START <= row < self.IDLE_END:
                rpm = result.loc[row, "rpm"]
                want_maf_load = 60.0 * 20.0 / rpm
                want_map_load = expected_map_load(110.0, rpm, 35.0)
                assert np.isclose(
                    result.loc[row, "maf_derived_air_load_raw"],
                    want_maf_load,
                )
                assert np.isclose(
                    result.loc[row, "map_derived_air_load_raw"],
                    want_map_load,
                )
                assert np.isclose(
                    result.loc[row, "maf_map_cohesion"],
                    expected_cohesion(want_maf_load, want_map_load),
                )
                assert np.isclose(
                    result.loc[row, "speed_density_maf_residual"],
                    expected_speed_density(
                        20.0, want_map_load, 110.0, rpm, 35.0
                    ),
                )
            else:
                assert (
                    result.loc[row, "maf_derived_air_load_raw"]
                    == 0.8
                )
                assert (
                    result.loc[row, "map_derived_air_load_raw"]
                    == 110.0
                )
                assert result.loc[row, "maf_map_cohesion"] == 0.18

    def test_nan_values_stay_nan(self):
        frame = self.make_frame()
        nan_columns = [
            "rpm",
            "maf_derived_air_load_raw",
            "map_derived_air_load_raw",
            "maf_map_cohesion",
            "speed_density_maf_residual",
        ]
        frame.loc[10, nan_columns] = np.nan

        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )

        for column in nan_columns:
            assert np.isnan(result.loc[10, column]), column
        # Neighbouring idle rows are still perturbed.
        assert np.isclose(
            result.loc[11, "rpm"], self.expected_rpm(11, 4)
        )

    def test_no_idle_rows_leaves_signals_unchanged(self):
        frame = make_group1_frame(rows=12)  # idle_flag all 0
        result = inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=2
        )
        assert (result["rpm"] == 1500.0).all()
        assert (result["maf_derived_air_load_raw"] == 0.8).all()

    def test_input_not_mutated(self):
        frame = self.make_frame()
        original = frame.copy()
        inject_idle_speed_fault(
            frame, COHESION_PARAMS, SD_MODEL, start_row=4
        )
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
            inject_intake_maf_fault(
                frame, "low_maf", SPEED_DENSITY_TRANSFORM
            ),
            inject_intake_maf_fault(
                frame, "map_bias", SPEED_DENSITY_TRANSFORM
            ),
        ]
        for injected in scenarios:
            outcome = validate_sensor_ranges(injected)
            assert outcome.repaired_counts == {}
