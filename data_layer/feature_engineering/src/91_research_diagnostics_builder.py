"""91_research_diagnostics_builder.py — Research Diagnostics

Phase 1 — LOTO: all data-driven thresholds (always runs).
Phase 2 — Grid scans: candidate sensitivity (--grid-scans).
Phase 3 — Bootstrap: confidence intervals (--bootstrap).

Disabled by default (use --grid-scans, --bootstrap).
Output: research_diagnostics/ under the run dir.
Never writes to production_features.csv or modifies the calibration registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_research_approved_run(run_dir: Path) -> bool:
    """Return true only when the run is explicitly marked for research."""

    marker = run_dir / "research_diagnostics_approved.json"
    if marker.is_file():
        data = json.loads(marker.read_text(encoding="utf-8"))
        return bool(data.get("research_diagnostics"))

    manifest = (
        run_dir / "features/41_production/production_feature_manifest.json"
    )
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return bool(
            data.get("research_diagnostics")
            or data.get("research_diagnostics_enabled")
            or data.get("approved_research_run")
        )
    return False


def _write_manifest(
    run_dir: Path,
    output_dir: Path,
    registry_path: Path,
    result: dict[str, Any],
    *,
    allow_production_run: bool,
) -> None:
    outputs = []
    for path in sorted(output_dir.glob("*")):
        if path.name == "research_diagnostics_manifest.json":
            continue
        if path.is_file():
            outputs.append({
                "path": path.relative_to(run_dir).as_posix(),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            })
    manifest = {
        "manifest_type": "research_diagnostics_output",
        "script": "91_research_diagnostics_builder.py",
        "run_dir": str(run_dir),
        "registry_path": str(registry_path),
        "registry_sha256": (
            _sha256_file(registry_path) if registry_path.is_file() else None
        ),
        "allow_production_run": allow_production_run,
        "summary": result,
        "outputs": outputs,
    }
    (output_dir / "research_diagnostics_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _trip_equal_q50(series: pd.Series, trip_ids: pd.Series) -> float:
    """Trip-equal weighted median (each trip contributes equal weight)."""
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


def _loto(
    df: pd.DataFrame,
    trip_ids: pd.Series,
    compute_fn: Callable[[pd.DataFrame], float],
    frozen_value: float,
    label: str,
    tolerance: float = 0.0,
    output_dir: Path | None = None,
) -> pd.DataFrame:
    """Generic LOTO: leave out each trip, recompute threshold, compare."""
    all_trips = trip_ids.unique()
    records = []
    for left_out in all_trips:
        rest = df[trip_ids != left_out]
        recalculated = compute_fn(rest)
        deviation = recalculated - frozen_value
        deviation_pct = (
            deviation /
            frozen_value *
            100) if frozen_value != 0 else 0.0
        passes = abs(deviation) <= tolerance if tolerance > 0 else True
        records.append({
            "sub_check": label,
            "left_out_trip": left_out,
            "frozen_value": frozen_value,
            "recalculated_value": round(recalculated, 6),
            "deviation": round(deviation, 6),
            "deviation_pct": round(deviation_pct, 4),
            "passes": passes,
        })
    result = pd.DataFrame(records)
    n_pass = int(result["passes"].sum())
    n_total = len(result)
    max_dev = float(result["deviation_pct"].abs().max())
    print(f"  LOTO {label}: {n_pass}/{n_total} passed, max dev={max_dev:.2f}%")
    if output_dir:
        safe_label = label.replace("/", "_")
        result.to_csv(
            output_dir / f"loto_{safe_label}.csv",
            index=False,
        )
    return result


def _bootstrap(
    df: pd.DataFrame,
    trip_ids: pd.Series,
    compute_fn: Callable[[pd.DataFrame], float],
    n_iterations: int,
    label: str,
) -> dict[str, Any]:
    """Sample trips with replacement and compute the threshold each time."""
    all_trips = trip_ids.unique()
    values = []
    for _ in range(n_iterations):
        sampled = np.random.choice(
            all_trips, size=len(all_trips), replace=True)
        chunks = [df[trip_ids == t] for t in sampled]
        boot_df = pd.concat(chunks, ignore_index=True)
        values.append(compute_fn(boot_df))
    arr = np.array(values)
    result = {
        "sub_check": label,
        "n_iterations": n_iterations,
        "n_trips_per_sample": len(all_trips),
        "mean": round(float(np.mean(arr)), 6),
        "std": round(float(np.std(arr)), 6),
        "ci_lower_2.5": round(float(np.percentile(arr, 2.5)), 6),
        "ci_upper_97.5": round(float(np.percentile(arr, 97.5)), 6),
    }
    print(f"  Bootstrap {label}: mean={result['mean']:.3f} "
          f"95% CI=[{result['ci_lower_2.5']:.3f}, "
          f"{result['ci_upper_97.5']:.3f}]")
    return result


# ---------------------------------------------------------------------------
# Phase 1 — LOTO
# ---------------------------------------------------------------------------


def loto_1_S1_T_reg_est(df, registry, output_dir, trip_ids):
    """T_reg_est = median of per-trip post-warmup coolant_temp medians."""
    pw = df[df["thermal_state"] == "post_warmup"]
    target = registry["proxy_rules"]["1-S1"]["target_derivation"]
    frozen = target["thermostat_regulating_estimate_c"]
    _loto(
        pw,
        pw["trip_id"],
        lambda r: r.groupby("trip_id")["coolant_temp"].median().median(),
        frozen,
        "1-S1_T_reg_est",
        tolerance=1.0,
        output_dir=output_dir,
    )


def loto_1_S2_envelope(df, registry, output_dir, trip_ids):
    """Max coolant_temp in post_warmup; verify 105C sits above."""
    pw = df[df["thermal_state"] == "post_warmup"]
    f = registry["proxy_rules"]["1-S2"]["tiers"][0]["temperature"]["value"]
    _loto(pw, pw["trip_id"],
          lambda r: r["coolant_temp"].max(),
          f, "1-S2_max_coolant_temp", tolerance=5.0, output_dir=output_dir)


def loto_2_S2_residual(df, registry, output_dir, trip_ids):
    """P0.5 of speed_density_maf_residual under post_warmup__high_load."""
    mask = (
        df["operating_state"] == "post_warmup__high_load") & (
        df["condition_confidence"] == "high")
    sub = df[mask]
    f = registry["proxy_rules"]["2-S2"]["residual"]["raw_value"]

    def _comp(r):
        vals = r["speed_density_maf_residual"].dropna()
        return vals.quantile(0.005) if len(vals) > 10 else float("nan")

    _loto(sub, sub["trip_id"], _comp, f, "2-S2_residual_P0.5",
          tolerance=abs(f) * 0.15, output_dir=output_dir)


def loto_3_S1a_band(df, registry, output_dir, trip_ids):
    """Pedal residual band edges under low-motion mask."""
    s1a = registry["proxy_rules"]["3-S1a"]
    mask = (df["rpm"] >= 50) & (df["pedal_slope"].abs()
                                <= s1a["guards"]["pedal_slope_abs"]["value"])
    sub = df[mask]

    for side, key, frozen_field in [
            ("low", "low", "raw_value"), ("high", "high", "raw_value")]:
        f = s1a["residual_band"][key][frozen_field]

        def _comp(r, side=side):
            vals = r["pedal_mapping_residual"].dropna()
            if len(vals) < 100:
                return float("nan")
            return vals.quantile(0.005 if side == "low" else 0.995)

        _loto(sub, sub["trip_id"], _comp, f, f"3-S1a_band_{key}",
              tolerance=abs(f) * 0.15, output_dir=output_dir)


def loto_3_S1b_channel_delta(df, registry, output_dir, trip_ids):
    """Max accel_pedal_channel_delta."""
    f = registry["proxy_rules"]["3-S1b"]["channel_delta"]["value"]
    _loto(df, trip_ids, lambda r: r["accel_pedal_channel_delta"].max(),
          f, "3-S1b_channel_delta", tolerance=5.0, output_dir=output_dir)


def loto_4_S1_context(df, registry, output_dir, trip_ids):
    """Trip-equal q50 of context thresholds for 4-S1."""
    s1 = registry["proxy_rules"]["4-S1"]
    ctx = s1["context_thresholds"]
    for col, meta in [("speed_std_120s", ctx["speed_std_120s"]),
                      ("maf_std_120s", ctx["maf_std_120s"])]:
        f = meta["raw_value"]
        _loto(df, trip_ids,
              lambda r, c=col: _trip_equal_q50(
                  r[c].dropna(), r.loc[r[c].dropna().index, "trip_id"]),
              f, f"4-S1_{col}_q50", tolerance=f * 0.15, output_dir=output_dir)


def loto_5_S1_steps(df, registry, output_dir, trip_ids):
    """Per-state P95 of positive pedal_slope."""
    s1 = registry["proxy_rules"]["5-S1"]
    for state, params in s1["state_parameters"].items():
        f = params["pedal_step_threshold"]["value"]

        def _comp(r, st=state):
            m = (
                r["operating_state"] == st) & (
                r["pedal_slope"] > 0) & (
                r["condition_confidence"] == "high")
            vals = r.loc[m, "pedal_slope"].dropna()
            return vals.quantile(0.95) if len(vals) > 10 else float("nan")

        _loto(df, trip_ids, _comp, f, f"5-S1_{state}_P95",
              tolerance=f * 0.15, output_dir=output_dir)


def loto_5_S3_context(df, registry, output_dir, trip_ids):
    """Trip-equal q50 of context thresholds for 5-S3."""
    s3 = registry["proxy_rules"]["5-S3"]
    ctx = s3["context_thresholds"]
    checks = [
        ("rpm_std_120s", ctx["rpm_std_120s"]),
        ("speed_std_120s", ctx["speed_std_120s"]),
        (
            "accel_pedal_mean_std_120s",
            ctx["accel_pedal_mean_std_120s"],
        ),
    ]
    for col, meta in checks:
        f = meta["raw_value"]
        _loto(df, trip_ids,
              lambda r, c=col: _trip_equal_q50(
                  r[c].dropna(), r.loc[r[c].dropna().index, "trip_id"]),
              f, f"5-S3_{col}_q50", tolerance=f * 0.15, output_dir=output_dir)


# ---------------------------------------------------------------------------
# Phase 2 — Grid scans
# ---------------------------------------------------------------------------


def grid_2_S2_persistence(df, registry, output_dir):
    """Persitence window candidates for high-load under-read."""
    s2 = registry["proxy_rules"]["2-S2"]
    residual_th = s2["residual"]["raw_value"]
    mask = (
        df["operating_state"] == "post_warmup__high_load") & (
        df["condition_confidence"] == "high")
    sub = df[mask]
    if len(sub) == 0:
        return

    trip_max = {}
    for tid, g in sub.groupby("trip_id"):
        trip_longest = 0
        for _segment, sg in g.groupby("segment_id", sort=False):
            cur = 0
            mx = 0
            for v in sg.sort_values("row_in_segment")[
                "speed_density_maf_residual"
            ]:
                if v < residual_th:
                    cur += 1
                    mx = max(mx, cur)
                else:
                    cur = 0
            trip_longest = max(trip_longest, mx)
        trip_max[tid] = trip_longest

    runs = list(trip_max.values())
    n_trips = len(runs)
    records = []
    for cand in [5, 10, 15, 30]:
        trig = sum(1 for r_ in runs if r_ >= cand)
        longest = max(runs)
        records.append({
            "candidate_persistence_s": cand,
            "trips_triggered": trig, "total_trips": n_trips,
            "trigger_pct": round(trig / n_trips * 100, 1),
            "longest_healthy_run_s": longest,
            "margin_s": cand - longest if cand > longest else -1,
        })
    result = pd.DataFrame(records)
    result.to_csv(output_dir / "grid_2_S2_persistence.csv", index=False)
    chosen = s2["persistence"]["value"]
    for _, r in result.iterrows():
        marker = (
            " << CHOSEN"
            if r["candidate_persistence_s"] == chosen
            else ""
        )
        print(f"  Grid 2-S2 {r['candidate_persistence_s']}s: "
              f"{r['trips_triggered']}/{r['total_trips']} trips "
              f"margin={r['margin_s']}s{marker}")


def grid_3_S1a_pedal_mask(df, registry, output_dir):
    """Pedal slope mask threshold candidates."""
    s1a = registry["proxy_rules"]["3-S1a"]
    frozen_mask = s1a["guards"]["pedal_slope_abs"]["value"]

    records = []
    for cand in [1.5, 2.0, 2.4, 3.0, 4.0]:
        mask = (df["rpm"] >= 50) & (df["pedal_slope"].abs() <= cand)
        sub = df[mask]
        vals = sub["pedal_mapping_residual"].dropna()
        n_samp = len(vals)
        lo = vals.quantile(0.005)
        hi = vals.quantile(0.995)
        bandwidth = hi - lo
        records.append({
            "candidate_mask_pp_s": cand,
            "n_samples": n_samp,
            "p0.5": round(lo, 4),
            "p99.5": round(hi, 4),
            "bandwidth": round(bandwidth, 4),
            "is_frozen": cand == frozen_mask,
        })
    result = pd.DataFrame(records)
    result.to_csv(output_dir / "grid_3_S1a_pedal_mask.csv", index=False)
    print("  Grid 3-S1a pedal mask:")
    for _, r in result.iterrows():
        m = " << FROZEN" if r["is_frozen"] else ""
        print(f"    {r['candidate_mask_pp_s']} pp/s: "
              f"band=[{r['p0.5']}, {r['p99.5']}] "
              f"width={r['bandwidth']:.2f} n={r['n_samples']}{m}")


def grid_1_S3_rate(df, registry, output_dir):
    """ECT rate threshold candidates for rising-without-plateau."""
    s3 = registry["proxy_rules"]["1-S3"]
    level = s3["level"]["value"]
    persistence = s3["persistence"]["value"]
    frozen_rate = s3["rate"]["value"]
    mask = (
        df["thermal_state"] == "post_warmup") & (
        df["coolant_temp"] >= level)
    sub = df[mask]

    records = []
    for cand in [0.3, 0.5, 0.7, 1.0]:
        trig = 0
        for tid, g in sub.groupby("trip_id"):
            hit = False
            for _segment, sg in g.groupby("segment_id", sort=False):
                cur = 0
                for v in sg.sort_values("row_in_segment")["ect_rate_180s"]:
                    if v >= cand:
                        cur += 1
                        if cur >= persistence:
                            hit = True
                            break
                    else:
                        cur = 0
                if hit:
                    break
            if hit:
                trig += 1
        records.append({
            "candidate_rate_c_per_min": cand,
            "trips_with_persistent_episode": trig,
            "total_trips": sub["trip_id"].nunique(),
            "is_frozen": cand == frozen_rate,
        })
    result = pd.DataFrame(records)
    result.to_csv(output_dir / "grid_1_S3_rate.csv", index=False)
    print("  Grid 1-S3 rate:")
    for _, r in result.iterrows():
        m = " << FROZEN" if r["is_frozen"] else ""
        print(f"    {r['candidate_rate_c_per_min']} C/min: "
              f"{r['trips_with_persistent_episode']}/"
              f"{r['total_trips']} trips{m}")


# ---------------------------------------------------------------------------
# Phase 3 — Bootstrap
# ---------------------------------------------------------------------------


def bootstrap_1_S1_T_reg_est(df, output_dir, trip_ids):
    """Bootstrap CI for T_reg_est (optimized: pre-compute per-trip stats)."""
    pw = df[df["thermal_state"] == "post_warmup"]
    per_trip = pw.groupby("trip_id")["coolant_temp"].median()
    trips_arr = per_trip.values
    n = len(trips_arr)
    values = []
    rng = np.random.default_rng(42)
    for _ in range(1000):
        idx = rng.integers(0, n, size=n)
        values.append(float(np.median(trips_arr[idx])))
    arr = np.array(values)
    result = {
        "sub_check": "1-S1_T_reg_est", "n_iterations": 1000, "n_trips": n,
        "mean": round(float(arr.mean()), 4), "std": round(float(arr.std()), 4),
        "ci_lower_2.5": round(float(np.percentile(arr, 2.5)), 4),
        "ci_upper_97.5": round(float(np.percentile(arr, 97.5)), 4),
    }
    output_path = output_dir / "bootstrap_1_S1_T_reg_est.json"
    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(f"  Bootstrap 1-S1 T_reg_est: {result['mean']:.2f}C "
          f"95% CI=[{result['ci_lower_2.5']:.2f}, "
          f"{result['ci_upper_97.5']:.2f}]C")


def bootstrap_3_S1b_channel_delta(df, output_dir, trip_ids):
    """Bootstrap CI for max channel_delta (optimized)."""
    per_trip = df.groupby("trip_id")["accel_pedal_channel_delta"].max()
    vals = per_trip.values
    n = len(vals)
    rng = np.random.default_rng(43)
    values = []
    for _ in range(1000):
        idx = rng.integers(0, n, size=n)
        values.append(float(np.max(vals[idx])))
    arr = np.array(values)
    result = {
        "sub_check": "3-S1b_channel_delta", "n_iterations": 1000, "n_trips": n,
        "mean": round(float(arr.mean()), 4), "std": round(float(arr.std()), 4),
        "ci_lower_2.5": round(float(np.percentile(arr, 2.5)), 4),
        "ci_upper_97.5": round(float(np.percentile(arr, 97.5)), 4),
    }
    (output_dir / "bootstrap_3_S1b_channel_delta.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(f"  Bootstrap 3-S1b channel_delta: {result['mean']:.1f}pp "
          f"95% CI=[{result['ci_lower_2.5']:.1f}, "
          f"{result['ci_upper_97.5']:.1f}]pp")


def bootstrap_2_S2_residual(df, output_dir, trip_ids):
    """Bootstrap CI for residual P0.5 under high_load (optimized)."""
    mask = (
        df["operating_state"] == "post_warmup__high_load") & (
        df["condition_confidence"] == "high")
    sub = df[mask]
    per_trip = sub.groupby("trip_id")["speed_density_maf_residual"].apply(
        lambda s: s.quantile(0.005) if len(s) > 5 else float("nan")
    )
    vals = per_trip.dropna().values
    n = len(vals)
    rng = np.random.default_rng(44)
    values = []
    for _ in range(1000):
        idx = rng.integers(0, n, size=n)
        values.append(float(np.median(vals[idx])))
    arr = np.array(values)
    result = {
        "sub_check": "2-S2_residual_P0.5",
        "n_iterations": 1000,
        "n_trips_used": n,
        "mean": round(float(arr.mean()), 4), "std": round(float(arr.std()), 4),
        "ci_lower_2.5": round(float(np.percentile(arr, 2.5)), 4),
        "ci_upper_97.5": round(float(np.percentile(arr, 97.5)), 4),
    }
    output_path = output_dir / "bootstrap_2_S2_residual.json"
    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(f"  Bootstrap 2-S2 residual: {result['mean']:.2f} g/s "
          f"95% CI=[{result['ci_lower_2.5']:.2f}, "
          f"{result['ci_upper_97.5']:.2f}] g/s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(
    rid: str,
    registry: dict,
    enable_grid: bool,
    enable_boot: bool,
    *,
    allow_production_run: bool = False,
) -> dict:
    """Run all phases and return summary."""
    run_dir = Path(rid).resolve()
    if not allow_production_run and not _is_research_approved_run(run_dir):
        raise RuntimeError(
            "This run is not marked as research_diagnostics=true. "
            "Create run_dir/research_diagnostics_approved.json or rerun "
            "with --allow-production-run for an explicit one-off audit."
        )
    csv = run_dir / "features/41_production/production_features.csv"
    df = pd.read_csv(csv, low_memory=False)
    trip_ids = df["trip_id"]
    print(f"Loaded {len(df):,} rows, {trip_ids.nunique()} trips")
    out = REPO_ROOT / "data_layer" / "research_diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    print(f"Output: {out}\n")

    # Phase 1 — LOTO
    print("--- Phase 1: LOTO ---")
    loto_1_S1_T_reg_est(df, registry, out, trip_ids)
    loto_1_S2_envelope(df, registry, out, trip_ids)
    loto_2_S2_residual(df, registry, out, trip_ids)
    loto_3_S1a_band(df, registry, out, trip_ids)
    loto_3_S1b_channel_delta(df, registry, out, trip_ids)
    loto_4_S1_context(df, registry, out, trip_ids)
    loto_5_S1_steps(df, registry, out, trip_ids)
    loto_5_S3_context(df, registry, out, trip_ids)

    # Phase 2 — Grid scans
    if enable_grid:
        print("\n--- Phase 2: Grid scans ---")
        grid_2_S2_persistence(df, registry, out)
        grid_3_S1a_pedal_mask(df, registry, out)
        grid_1_S3_rate(df, registry, out)
    else:
        print("\n--- Phase 2: Grid scans disabled (use --grid-scans) ---")

    # Phase 3 — Bootstrap
    if enable_boot:
        print("\n--- Phase 3: Bootstrap ---")
        bootstrap_1_S1_T_reg_est(df, out, trip_ids)
        bootstrap_2_S2_residual(df, out, trip_ids)
        bootstrap_3_S1b_channel_delta(df, out, trip_ids)
    else:
        print("\n--- Phase 3: Bootstrap disabled (use --bootstrap) ---")

    loto_files = sorted(f.name for f in out.glob("loto_*.csv"))
    grid_files = sorted(f.name for f in out.glob("grid_*.csv"))
    boot_files = sorted(f.name for f in out.glob("bootstrap_*.json"))
    print(
        f"\n Done: {len(loto_files)} LOTO, "
        f"{len(grid_files)} grid, {len(boot_files)} bootstrap"
    )
    return {"output_dir": str(out), "loto": loto_files,
            "grid": grid_files, "bootstrap": boot_files}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Research diagnostics (script 91).")
    p.add_argument("--run-dir", required=True)
    p.add_argument(
        "--registry",
        default=str(
            REPO_ROOT /
            "data_layer/calibration/calibration_registry.v1.json"))
    p.add_argument("--grid-scans", action="store_true")
    p.add_argument("--bootstrap", action="store_true")
    p.add_argument(
        "--allow-production-run",
        action="store_true",
        help=("Allow diagnostics on a normal production run. This is useful "
              "for one-off audits, but the output remains research-only."),
    )
    args = p.parse_args()
    registry_path = Path(args.registry).resolve()
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    try:
        result = run(
            args.run_dir,
            reg,
            args.grid_scans,
            args.bootstrap,
            allow_production_run=args.allow_production_run,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    run_dir = Path(args.run_dir).resolve()
    summary = (
        REPO_ROOT / "data_layer" / "research_diagnostics" / "summary.json"
    )
    summary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_manifest(
        run_dir,
        summary.parent,
        registry_path,
        result,
        allow_production_run=args.allow_production_run,
    )
    print(f"Summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
