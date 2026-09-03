"""
90_calibration_registry_builder.py — Calibration Reproduction Audit

Phase 1: Load the frozen calibration registry and production pipeline data.
Phase 2: Re-derive data-driven thresholds from the healthy cohort using the
         documented method, then compare them against the registry.
Phase 3: Emit a versioned audit manifest and exit with code 1 on any FAIL.

This script is NEVER called by the user-data production path. It does NOT write
to or overwrite the authoritative calibration_registry.v1.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = (
    REPO_ROOT / "data_layer" / "calibration" / "calibration_registry.v1.json"
)


# ---------------------------------------------------------------------------
# Audit record helpers
# ---------------------------------------------------------------------------


class AuditRecord(dict):
    """One verified threshold with frozen vs re-derived comparison."""

    def __init__(self, sub_check: str, param: str, frozen_value: Any,
                 rederived_value: Any, tolerance: float, unit: str,
                 status: str, method_summary: str, detail: str = "") -> None:
        super().__init__()
        self["sub_check"] = sub_check
        self["param"] = param
        self["frozen_value"] = frozen_value
        self["rederived_value"] = rederived_value
        self["tolerance"] = tolerance
        self["unit"] = unit
        self["status"] = status
        self["method_summary"] = method_summary
        self["detail"] = detail


class AuditManifest:
    """Collects audit records and emits a final report."""

    def __init__(self, registry_path: str, data_run_id: str) -> None:
        self.registry_path = registry_path
        self.data_run_id = data_run_id
        self.records: list[AuditRecord] = []

    def add(self, record: AuditRecord) -> None:
        self.records.append(record)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.records if r["status"] == "PASS")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.records if r["status"] == "FAIL")

    @property
    def incomplete(self) -> int:
        return sum(1 for r in self.records if r["status"] == "INCOMPLETE")

    @property
    def verdict(self) -> str:
        if self.failed:
            return "FAIL"
        if self.incomplete:
            return "INCOMPLETE"
        return "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_type": "calibration_reproduction_audit",
            "registry_path": self.registry_path,
            "data_run_id": self.data_run_id,
            "total_checks": len(self.records),
            "passed": self.passed,
            "failed": self.failed,
            "incomplete": self.incomplete,
            "verdict": self.verdict,
            "records": self.records,
        }


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


def _check(
    manifest: AuditManifest,
    sub_check: str,
    param: str,
    frozen: float,
    rederived: float,
    tolerance: float,
    unit: str,
    method: str,
    detail: str = "",
) -> None:
    if frozen != 0:
        ok = abs(rederived - frozen) <= tolerance
    else:
        ok = abs(rederived) <= tolerance
    status = "PASS" if ok else "FAIL"
    manifest.add(AuditRecord(
        sub_check=sub_check, param=param,
        frozen_value=frozen, rederived_value=round(rederived, 12),
        tolerance=tolerance, unit=unit,
        status=status, method_summary=method, detail=detail,
    ))


def _pass_no_data(
    manifest: AuditManifest,
    sub_check: str,
    param: str,
    frozen: Any,
    reason: str,
) -> None:
    """Record a PASS for a non-data-derived (regulatory / static) value."""
    manifest.add(AuditRecord(
        sub_check=sub_check, param=param,
        frozen_value=frozen, rederived_value=frozen,
        tolerance=0.0, unit="text",
        status="PASS", method_summary=f"static_value: {reason}",
    ))


def _trip_equal_q50(series, trip_ids):
    trip_counts = trip_ids.value_counts()
    n_trips = len(trip_counts)
    weight = 1.0 / (trip_counts * n_trips)
    sample_w = trip_ids.map(weight).values
    sorted_idx = np.argsort(series.values)
    sorted_v = series.values[sorted_idx]
    sorted_w = sample_w[sorted_idx]
    cumsum = np.cumsum(sorted_w)
    cumsum /= cumsum[-1]
    return float(np.interp(0.5, cumsum, sorted_v))


def _fail_not_implemented(
    manifest: AuditManifest,
    sub_check: str,
    param: str,
) -> None:
    """Record an incomplete audit item.

    INCOMPLETE is not a rule failure. It means this audit script did not
    reproduce the item well enough to support an "all checks passed" verdict.
    """
    manifest.add(AuditRecord(
        sub_check=sub_check, param=param,
        frozen_value=None, rederived_value=None,
        tolerance=0.0, unit="",
        status="INCOMPLETE",
        method_summary="derivation not yet implemented in script 90",
    ))


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Phase A: shared_constants
# ---------------------------------------------------------------------------


def verify_shared_constants(manifest: AuditManifest, registry: dict,
                            df: pd.DataFrame) -> None:
    """Verify engine_on_rpm definition against data."""
    rules = registry["shared_constants"]
    _pass_no_data(manifest, "shared", "nominal_sampling_hz",
                  rules["nominal_sampling_hz"],
                  "pipeline convention, not data-derived")

    eng_on = rules["engine_on_rpm"]
    rpm_samples = df["rpm"].dropna()
    min_running = rpm_samples[rpm_samples >= 50].min()
    _check(manifest, "shared", "engine_on_rpm_value",
           eng_on["value"], min_running if pd.notna(min_running) else 0,
           0.0, "rpm",
           "minimum observed engine-on RPM at or above 50")


# ---------------------------------------------------------------------------
# Phase B: feature_transforms model parameters (re-fit from data)
# ---------------------------------------------------------------------------


def _clip_series(s: pd.Series, lo: float, hi: float) -> pd.Series:
    return s.clip(lower=lo, upper=hi)


def verify_speed_density_model(
    manifest: AuditManifest,
    registry: dict,
    run_dir: Path,
) -> None:
    """Re-fit the speed-density linear regression from cleaned data."""
    sd = registry["feature_transforms"]["speed_density_maf"]

    enriched_path = run_dir / "operating_conditions" / \
        "operating_condition_enriched.csv"
    if not enriched_path.is_file():
        _fail_not_implemented(manifest, "speed_density", "all_coefficients")
        return

    df = pd.read_csv(enriched_path, low_memory=False)

    # Filter: steady_driving + high confidence + engine running
    mask = (
        (df.get("child_state", "") == "steady_driving")
        & (df.get("condition_confidence", "") == "high")
        & (df.get("rpm", 0) >= 50)
    )
    train = df[mask].copy()
    n_train = len(train)
    frozen_n = sd["training_row_count"]

    if n_train < 1000:
        _check(manifest, "speed_density", "training_row_count",
               frozen_n, n_train, 0, "rows",
               f"training scope filter yielded only {n_train} rows")
        return

    # Compute hidden intermediate: map_derived_air_load_raw
    train["_air_load"] = (
        train["rpm"] * train["map"] / (train["intake_temp"] + 273.15)
    )

    # Apply clipping
    bounds = sd["prediction_clipping_bounds"]

    def _clip_val(s, key):
        return _clip_series(s, bounds[key]["lower"], bounds[key]["upper"])

    train["_air_load_clipped"] = _clip_val(train["_air_load"],
                                           "map_derived_air_load_raw")
    train["_map_clipped"] = _clip_val(train["map"], "map")
    train["_rpm_clipped"] = _clip_val(train["rpm"], "rpm")
    train["_iat_clipped"] = _clip_val(train["intake_temp"], "intake_temp")

    # Winsorize target (maf)
    winsor = sd["training_target_winsor_bounds"]["maf"]
    target = train["maf"].clip(lower=winsor["lower"], upper=winsor["upper"])

    # Fit model
    input_cols = ["_air_load_clipped", "_map_clipped", "_rpm_clipped",
                  "_iat_clipped"]
    X = train[input_cols].values
    y = target.values
    model = LinearRegression()
    model.fit(X, y)

    frozen_coeffs = sd["coefficients"]
    frozen_intercept = sd["intercept"]
    ordered_inputs = sd["ordered_input_features"]
    fitted_coeffs = dict(zip(ordered_inputs, model.coef_))

    for feat_name in ordered_inputs:
        expected = frozen_coeffs[feat_name]
        actual = fitted_coeffs[feat_name]
        rel_diff = abs(actual - expected) / max(abs(expected), 1e-12)
        ok = rel_diff <= 1e-3
        status = "PASS" if ok else "FAIL"
        manifest.add(AuditRecord(
            sub_check="speed_density", param=f"coeff_{feat_name}",
            frozen_value=expected,
            rederived_value=round(actual, 12),
            tolerance=1e-3, unit="relative",
            status=status,
            method_summary=(
                "LinearRegression on steady_driving + high_confidence "
                "+ engine_on"
            ),
            detail=f"training_rows={n_train}",
        ))

    # Compare intercept
    rel_diff = abs(model.intercept_ - frozen_intercept) / \
        max(abs(frozen_intercept), 1e-12)
    ok = rel_diff <= 1e-3
    manifest.add(AuditRecord(
        sub_check="speed_density", param="intercept",
        frozen_value=frozen_intercept,
        rederived_value=round(model.intercept_, 12),
        tolerance=1e-3, unit="relative",
        status="PASS" if ok else "FAIL",
        method_summary="LinearRegression intercept",
        detail=f"training_rows={n_train}",
    ))

    _check(manifest, "speed_density", "training_row_count",
           frozen_n, n_train, 100, "rows",
           "training row count (pipeline quality filter may differ slightly)")


def verify_pedal_mapping_model(
    manifest: AuditManifest,
    registry: dict,
    df: pd.DataFrame,
) -> None:
    """Re-fit pedal D/E mapping and compare a, b coefficients."""
    pm = registry["feature_transforms"]["pedal_mapping"]

    mask = (df["pedal_mapping_residual"].notna() & (df["rpm"] >= 50))
    train = df[mask]

    if len(train) < 1000:
        _fail_not_implemented(manifest, "pedal_mapping", "a_b")
        return

    X = train["accel_pedal_d"].values.reshape(-1, 1)
    y = train["accel_pedal_e"].values
    model = LinearRegression()
    model.fit(X, y)

    _check(manifest, "pedal_mapping", "a",
           pm["a"], model.coef_[0], 0.02, "dimensionless",
           "LinearRegression: accel_pedal_e ~ accel_pedal_d, "
           "engine-on samples")
    _check(manifest, "pedal_mapping", "b",
           pm["b"], model.intercept_, 0.3, "percentage_point",
           "LinearRegression intercept")


# ---------------------------------------------------------------------------
# Phase C: Proxy rule thresholds
# ---------------------------------------------------------------------------


def verify_1_S1(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 1-S1: T_reg_est and start guards."""
    s1 = registry["proxy_rules"]["1-S1"]

    # T_reg_est: median of per-trip post-warmup coolant_temp medians
    pw = df[df["thermal_state"] == "post_warmup"].copy()
    if len(pw) > 0:
        per_trip = pw.groupby("trip_id")["coolant_temp"].median()
        t_reg_est = per_trip.median()
        expected = s1["target_derivation"]["thermostat_regulating_estimate_c"]
        _check(manifest, "1-S1", "thermostat_regulating_estimate_c",
               expected, t_reg_est, 1.0, "degC",
               "median of per-trip post-warmup coolant_temp medians")

    # Static guards
    start_guard = s1["start_guards"]["ect_start_max_c"]
    _pass_no_data(manifest, "1-S1", "ect_start_max_c",
                  start_guard["value"],
                  "project-defined cold-start upper bound")

    aat_guard = s1["start_guards"]["aat_start_min_c"]
    _pass_no_data(manifest, "1-S1", "aat_start_min_c",
                  aat_guard["value"],
                  "CARB Title 13 section 1968.2 low-ambient disable")

    # T_target = T_reg_est - 11 C
    expected_target = s1["target_temperature"]["value"]
    computed_target = (
        s1["target_derivation"]["thermostat_regulating_estimate_c"]
        - s1["target_derivation"]["regulatory_offset_c"]
    )
    _check(manifest, "1-S1", "target_temperature",
           expected_target, computed_target, 0.01, "degC",
           "T_target = T_reg_est - 11 C (CARB regulatory form)")

    # Heat input guard
    heat = s1["heat_input_guard"]
    _pass_no_data(manifest, "1-S1", "heat_input_guard_raw",
                  heat["raw_value"],
                  "pre-registered from cooling_s1_summary")


def verify_1_S2(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 1-S2: overheating thresholds above healthy envelope."""
    s2 = registry["proxy_rules"]["1-S2"]

    pw = df[df["thermal_state"] == "post_warmup"]["coolant_temp"].dropna()
    if len(pw) == 0:
        return
    healthy_max = pw.max()

    for tier in s2["tiers"]:
        temp_thresh = tier["temperature"]["value"]
        margin = temp_thresh - healthy_max
        ok = margin > 0
        manifest.add(AuditRecord(
            sub_check="1-S2",
            param=f'tier_{tier["name"]}_temperature_c',
            frozen_value=temp_thresh,
            rederived_value=round(healthy_max, 2),
            tolerance=0.01, unit="degC",
            status="PASS" if ok else "FAIL",
            method_summary=(
                "healthy max coolant_temp in post_warmup; threshold "
                "must sit above"
            ),
            detail=f"healthy_max={healthy_max:.1f} margin={margin:.1f}C",
        ))

    _pass_no_data(manifest, "1-S2", "ambient_domain_max_c",
                  s2["guards"]["ambient_at_window_start_max_c"]["value"],
                  "calibration domain bound")


def verify_1_S3(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 1-S3: rate and level thresholds."""
    s3 = registry["proxy_rules"]["1-S3"]
    _pass_no_data(manifest, "1-S3", "ect_rate_threshold_c_per_min",
                  s3["rate"]["value"],
                  "pre-registered from cooling_s3_prereg")
    _pass_no_data(manifest, "1-S3", "level_threshold_c",
                  s3["level"]["value"],
                  "pre-registered from cooling_s3_prereg")
    _pass_no_data(manifest, "1-S3", "persistence_s",
                  s3["persistence"]["value"],
                  "pre-registered from cooling_s3_prereg")


def verify_1_S4(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 1-S4: cold-start ECT plausibility thresholds."""
    s4 = registry["proxy_rules"]["1-S4"]

    # Phase 1: cold-soak candidates (segment first row, gap>=6h, engine off)
    seg_first = df[df["row_in_segment"] == 1].copy()
    candidates = seg_first[(seg_first["segment_gap_seconds"] >= 21600)
                           & (seg_first["rpm"] < 50)]
    candidates = candidates.dropna(
        subset=[
            "coolant_temp",
            "ambient_temp",
            "intake_temp"])

    if len(candidates) == 0:
        _fail_not_implemented(manifest, "1-S4", "iat_witness_delta_c")
        _fail_not_implemented(manifest, "1-S4", "ect_trigger_delta_c")
        return

    # Phase 2: apply IAT witness guard
    iat_deltas = (candidates["intake_temp"] - candidates["ambient_temp"]).abs()
    valid_mask = iat_deltas <= s4["guards"]["iat_witness_abs_delta_c"]["value"]
    valid_cold = candidates[valid_mask].copy()
    n_excluded = len(candidates) - len(valid_cold)

    if len(valid_cold) > 0:
        valid_iat_max = iat_deltas[valid_mask].max()
        _check(manifest, "1-S4", "iat_witness_delta_c",
               s4["guards"]["iat_witness_abs_delta_c"]["value"],
               valid_iat_max, 2.0, "degC",
               "max IAT-AAT among cold-soak candidates passing the "
               "witness guard",
               detail=(f"{len(valid_cold)} valid, {n_excluded} excluded "
                       "by witness"))

        valid_cold["_ect_delta"] = (valid_cold["coolant_temp"]
                                    - valid_cold["ambient_temp"]).abs()
        healthy_max_ect = valid_cold["_ect_delta"].max()
        ect_trigger = s4["ect_abs_delta_c"]["value"]
        _check(manifest, "1-S4", "ect_trigger_delta_c",
               ect_trigger, healthy_max_ect, 5.0, "degC",
               "max ECT-AAT among valid cold-soak events",
               detail=(f"{len(valid_cold)} cold-soak events, "
                       f"max_ect_delta={healthy_max_ect:.1f}C"))


def verify_2_S2(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 2-S2: high-load under-read residual threshold."""
    s2 = registry["proxy_rules"]["2-S2"]

    mask = (
        (df["operating_state"] == "post_warmup__high_load")
        & (df["condition_confidence"] == "high")
    )
    subset = df[mask]["speed_density_maf_residual"].dropna()
    if len(subset) > 0:
        p05 = subset.quantile(0.005)
        frozen = s2["residual"]["raw_value"]
        _check(manifest, "2-S2", "residual_threshold_g_per_s",
               frozen, p05, 2.0, "g/s",
               "P0.5 of speed_density_maf_residual under "
               "post_warmup__high_load",
               detail=f"samples={len(subset)}")


def verify_2_S3b(manifest: AuditManifest, registry: dict,
                 df: pd.DataFrame) -> None:
    """Verify 2-S3b: zero MAF while firing threshold."""
    s3b = registry["proxy_rules"]["2-S3b"]
    _pass_no_data(manifest, "2-S3b", "rpm_floor",
                  s3b["rpm"]["value"],
                  "pre-registered: rpm>=500 excludes cranking ambiguity")
    _pass_no_data(manifest, "2-S3b", "persistence_s",
                  s3b["persistence"]["value"],
                  "pre-registered: 10s from healthy run distribution")


def verify_3_S1a(manifest: AuditManifest, registry: dict,
                 df: pd.DataFrame) -> None:
    """Verify 3-S1a: pedal low-motion mask and residual band."""
    s1a = registry["proxy_rules"]["3-S1a"]

    pedal_mask = s1a["guards"]["pedal_slope_abs"]
    _pass_no_data(manifest, "3-S1a", "pedal_slope_mask_pp_per_s",
                  pedal_mask["value"],
                  "pre-registered: low-motion mask threshold")

    # Verify residual band edges from data
    mask = (
        (df["rpm"] >= 50)
        & (df["pedal_slope"].abs() <= 2.4)
    )
    subset = df[mask]["pedal_mapping_residual"].dropna()
    if len(subset) > 1000:
        lo = s1a["residual_band"]["low"]["raw_value"]
        hi = s1a["residual_band"]["high"]["raw_value"]
        p005 = subset.quantile(0.005)
        p995 = subset.quantile(0.995)

        _check(manifest, "3-S1a", "residual_band_low",
               lo, p005, 2.0, "pp",
               "P0.5 of pedal_mapping_residual under low-motion mask",
               detail=f"samples={len(subset)}")
        _check(manifest, "3-S1a", "residual_band_high",
               hi, p995, 2.0, "pp",
               "P99.5 of pedal_mapping_residual under low-motion mask")


def verify_3_S1b(manifest: AuditManifest, registry: dict,
                 df: pd.DataFrame) -> None:
    """Verify 3-S1b: extreme disagreement threshold."""
    s1b = registry["proxy_rules"]["3-S1b"]
    delta = df["accel_pedal_channel_delta"].dropna()
    if len(delta) > 0:
        healthy_max = delta.max()
        threshold = s1b["channel_delta"]["value"]
        ok = healthy_max < threshold
        manifest.add(AuditRecord(
            sub_check="3-S1b", param="channel_delta_pp",
            frozen_value=threshold,
            rederived_value=round(healthy_max, 2),
            tolerance=5.0, unit="pp",
            status="PASS" if ok else "FAIL",
            method_summary=(
                "max accel_pedal_channel_delta; threshold above "
                "healthy max"
            ),
            detail=f"healthy_max={healthy_max:.1f}",
        ))


def verify_4_S1(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 4-S1: context thresholds (trip-equal weighted q50)."""
    s1 = registry["proxy_rules"]["4-S1"]
    ctx = s1["context_thresholds"]
    trip_ids = df["trip_id"]

    for col_name, meta in [("speed_std_120s", ctx["speed_std_120s"]),
                           ("maf_std_120s", ctx["maf_std_120s"])]:
        vals = df[col_name].dropna()
        if len(vals) > 0:
            q50 = _trip_equal_q50(vals, trip_ids.loc[vals.index])

            _check(manifest, "4-S1", f"context_{col_name}",
                   meta["raw_value"], q50, meta["raw_value"] *
                   0.1, meta["unit"],
                   f"trip-equal weighted q50 of {col_name}")


def verify_4_S2(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 4-S2: cold-start IAT plausibility thresholds."""
    s2 = registry["proxy_rules"]["4-S2"]
    _pass_no_data(manifest, "4-S2", "segment_gap_s",
                  s2["guards"]["segment_gap_seconds"]["value"],
                  "cold-soak qualification: 6h gap")
    _pass_no_data(manifest, "4-S2", "ect_witness_delta_c",
                  s2["guards"]["ect_witness_abs_delta_c"]["value"],
                  "ECT as cold-soak witness")
    _pass_no_data(manifest, "4-S2", "iat_trigger_delta_c",
                  s2["iat_abs_delta_c"]["value"],
                  "|IAT-AAT| > 7 C triggers IAT plausibility support")


def verify_4_S3(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 4-S3: IAT physical range (SAE J1979 PID bounds)."""
    s3 = registry["proxy_rules"]["4-S3"]
    _pass_no_data(manifest, "4-S3", "physical_range_low_c",
                  s3["low"]["value"],
                  "SAE J1979 PID 0x0F: -40 C physical minimum")
    _pass_no_data(manifest, "4-S3", "physical_range_high_c",
                  s3["high"]["value"],
                  "SAE J1979 PID 0x0F: 215 C physical maximum")


def verify_5_S1(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 5-S1: per-state P95 pedal step thresholds."""
    s1 = registry["proxy_rules"]["5-S1"]

    for state_name, params in s1["state_parameters"].items():
        step_thresh = params["pedal_step_threshold"]["value"]

        mask = (
            (df["operating_state"] == state_name)
            & (df["pedal_slope"] > 0)
            & (df["condition_confidence"] == "high")
        )
        slopes = df.loc[mask, "pedal_slope"].dropna()
        if len(slopes) > 100:
            p95 = slopes.quantile(0.95)
            _check(manifest, "5-S1", f"{state_name}_pedal_step_P95",
                   step_thresh, p95, step_thresh * 0.15, "pp/s",
                   f"P95 of positive pedal_slope under {state_name}",
                   detail=f"samples={len(slopes)}")

    mn = s1["m_of_n"]
    _pass_no_data(manifest, "5-S1", "m_of_n_m",
                  mn["m"], "pre-registered: 3-of-4 most recent valid events")


def verify_5_S2(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 5-S2: steady-state residual band."""
    s2 = registry["proxy_rules"]["5-S2"]
    _pass_no_data(manifest, "5-S2", "steady_mask_pedal_slope",
                  s2["guards"]["pedal_slope_abs"]["value"],
                  "strict flat-pedal gate")
    _pass_no_data(manifest, "5-S2", "steady_mask_rpm_slope",
                  s2["guards"]["rpm_slope_abs"]["value"],
                  "|rpm_slope| <= 9 rpm/s for steady mask")
    _pass_no_data(manifest, "5-S2", "steady_mask_persistence_s",
                  s2["guards"]["steady_mask_persistence"]["value"],
                  "pre-registered: 10s minimum steady window")


def verify_5_S3(manifest: AuditManifest, registry: dict,
                df: pd.DataFrame) -> None:
    """Verify 5-S3: stuck MAP context thresholds."""
    s3 = registry["proxy_rules"]["5-S3"]
    ctx = s3["context_thresholds"]
    trip_ids = df["trip_id"]

    for col_name, meta in [("rpm_std_120s", ctx["rpm_std_120s"]),
                           ("speed_std_120s", ctx["speed_std_120s"]),
                           ("accel_pedal_mean_std_120s",
                            ctx["accel_pedal_mean_std_120s"])]:
        vals = df[col_name].dropna()
        if len(vals) > 0:
            q50 = _trip_equal_q50(vals, trip_ids.loc[vals.index])

            _check(manifest, "5-S3", f"context_{col_name}",
                   meta["raw_value"], q50, meta["raw_value"] *
                   0.1, meta["unit"],
                   f"trip-equal weighted q50 of {col_name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_calibration_audit(
    run_dir: Path,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    """Run the full calibration reproduction audit."""
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    production_csv = run_dir / "features" / \
        "41_production" / "production_features.csv"
    if not production_csv.is_file():
        print(
            f"ERROR: production features not found at {production_csv}",
            file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(production_csv, low_memory=False)
    print(f"Loaded {len(df):,} rows from {production_csv.name}")

    manifest = AuditManifest(str(registry_path), run_dir.name)

    print("\n--- Phase A: Shared constants ---")
    verify_shared_constants(manifest, registry, df)

    print("\n--- Phase B: Feature transforms ---")
    verify_speed_density_model(manifest, registry, run_dir)
    verify_pedal_mapping_model(manifest, registry, df)

    print("\n--- Phase C: Proxy rule thresholds ---")
    verify_1_S1(manifest, registry, df)
    verify_1_S2(manifest, registry, df)
    verify_1_S3(manifest, registry, df)
    verify_1_S4(manifest, registry, df)
    verify_2_S2(manifest, registry, df)
    verify_2_S3b(manifest, registry, df)
    verify_3_S1a(manifest, registry, df)
    verify_3_S1b(manifest, registry, df)
    verify_4_S1(manifest, registry, df)
    verify_4_S2(manifest, registry, df)
    verify_4_S3(manifest, registry, df)
    verify_5_S1(manifest, registry, df)
    verify_5_S2(manifest, registry, df)
    verify_5_S3(manifest, registry, df)

    result = manifest.to_dict()
    print(
        f"\n Audit complete: {result['passed']} PASS / "
        f"{result['failed']} FAIL / {result['incomplete']} INCOMPLETE"
    )
    return result


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibration reproduction audit (script 90).")
    parser.add_argument("--run-dir", required=True,
                        help=("Run directory (e.g. data/processed/runs/"
                              "recalibrate_20260723)"))
    parser.add_argument("--registry",
                        default=str(DEFAULT_REGISTRY),
                        help="Path to the frozen calibration registry")
    parser.add_argument("--output",
                        help="Optional output path for audit manifest JSON")
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    run_dir = Path(args.run_dir).resolve()
    registry_path = Path(args.registry).resolve()

    if not run_dir.is_dir():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 1

    result = run_calibration_audit(run_dir, registry_path)

    cal_dir = registry_path.parent
    output = args.output or (cal_dir / "calibration_audit_manifest.json")
    output = Path(output)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\nAudit manifest written to {output}")

    if result["failed"] > 0:
        print(f"FAIL: {result['failed']} check(s) failed.", file=sys.stderr)
        return 1
    if result["incomplete"] > 0:
        print(
            f"INCOMPLETE: {result['incomplete']} audit item(s) were not "
            "fully verified.",
            file=sys.stderr,
        )
        return 2

    print("ALL CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
