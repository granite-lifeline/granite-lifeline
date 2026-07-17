"""
Story 7 synthetic-anomaly evaluation runner (Lucca).

Sweeps healthy Group 1 segments through the residual detector four
times each — one healthy control plus the three Story 7 fault
scenarios (fault_injection.py):

    cooling_fault   coolant_temp + 15 degC -> cooling_degradation
    maf_low_fault   maf x 0.7              -> air_intake_maf_anomaly
    map_bias_fault  map x 1.25             -> air_intake_maf_anomaly

Each segment is evaluated on its first 512+96 window starting at
the first `post_warmup` row (Group 1's `thermal_state`): the proxy
failure conditions are defined post-warm-up (proxy_support.md;
INTERFACE.md 2.4 gates cooling on >85 degC), and a cold-start
window saturates cooling risk on healthy data (the committed
kit_residual_sample.json shows this), which would put every run at
ceiling and record nothing usable. Segments that never reach
post_warmup are recorded as skipped.

The fault is injected from the context/future boundary onward, so
it covers the whole truth window but is unseen in the TTM context:
both the forecast-residual path and the rule path must react.
Raw `anomaly_type`/`risk_score` outputs are recorded per run for
Ray's precision/recall table and threshold calibration
(user_stories.md Story 7); this script does not judge pass/fail
beyond expected-type matching.

Run from the repository root:
    .venv/bin/python ttm-related/src/model/run_synthetic_evaluation.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

try:
    from model import kit_residual_detector as detector
    from model.fault_injection import (
        COOLING_OFFSET_C,
        DEFAULT_BASELINES_JSON,
        MAF_GAIN,
        MAP_GAIN,
        inject_cooling_fault,
        inject_intake_maf_fault,
        load_cohesion_params,
    )
except ImportError:  # direct script run: src/ not on sys.path
    import kit_residual_detector as detector
    from fault_injection import (
        COOLING_OFFSET_C,
        DEFAULT_BASELINES_JSON,
        MAF_GAIN,
        MAP_GAIN,
        inject_cooling_fault,
        inject_intake_maf_fault,
        load_cohesion_params,
    )

DEFAULT_MANIFEST = Path(
    "ttm-related/outputs/finetune_split_manifest.json"
)
DEFAULT_OUTPUT = Path(
    "ttm-related/outputs/synthetic_eval_results.json"
)

Injector = Callable[[pd.DataFrame, int], pd.DataFrame]


def build_scenarios(
    cohesion_params: dict[str, dict[str, float]],
) -> list[tuple[str, str | None, Injector | None]]:
    """(scenario name, expected anomaly_type, injector) triples.

    ``None`` injector = healthy control (negative for every fault
    type — used by Ray's precision computation).
    """
    return [
        ("healthy", None, None),
        (
            "cooling_fault",
            "cooling_degradation",
            lambda df, start: inject_cooling_fault(df, start_row=start),
        ),
        (
            "maf_low_fault",
            "air_intake_maf_anomaly",
            lambda df, start: inject_intake_maf_fault(
                df, "low_maf", cohesion_params, start_row=start
            ),
        ),
        (
            "map_bias_fault",
            "air_intake_maf_anomaly",
            lambda df, start: inject_intake_maf_fault(
                df, "map_bias", cohesion_params, start_row=start
            ),
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the residual detector on healthy and "
            "synthetically-perturbed Group 1 segments and record "
            "anomaly_type/risk_score per run (Story 7)."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=detector.DEFAULT_INPUT_CSV,
        help="Group 1 feature CSV (INTERFACE.md Section 1).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Story 6 split manifest listing eligible segments.",
    )
    parser.add_argument(
        "--segments",
        choices=["validation", "all"],
        default="validation",
        help=(
            "'validation' = the manifest's held-out validation "
            "segments (default, stays uncontaminated once Story 6 "
            "fine-tunes on the train split); 'all' = train + "
            "validation."
        ),
    )
    parser.add_argument(
        "--baselines",
        type=Path,
        default=DEFAULT_BASELINES_JSON,
        help="Group 1 feature_baselines.json (cohesion z-params).",
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=detector.DEFAULT_CONTEXT_LENGTH,
    )
    parser.add_argument(
        "--prediction-length",
        type=int,
        default=detector.DEFAULT_PREDICTION_LENGTH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to save the results JSON.",
    )
    return parser.parse_args()


def manifest_segments(manifest_path: Path, which: str) -> list[str]:
    with open(manifest_path) as handle:
        manifest = json.load(handle)
    groups = ["validation_trips"]
    if which == "all":
        groups = ["train_trips", "validation_trips"]
    segments: list[str] = []
    for group in groups:
        for trip_segments in manifest[group].values():
            segments.extend(trip_segments)
    return sorted(segments)


def trim_to_post_warmup(
    segment: pd.DataFrame, min_rows: int
) -> pd.DataFrame:
    """Drop rows before the segment's first post_warmup row.

    Raises ValueError when the segment never reaches post_warmup or
    has fewer than ``min_rows`` rows left after trimming.
    """
    states = segment["thermal_state"].astype(str)
    post = states.eq("post_warmup")
    if not post.any():
        raise ValueError("segment never reaches post_warmup")
    start = int(post.idxmax())
    trimmed = segment.loc[start:].reset_index(drop=True)
    if len(trimmed) < min_rows:
        raise ValueError(
            f"only {len(trimmed)} post_warmup rows, "
            f"need {min_rows}"
        )
    return trimmed


def run_one(
    segment: pd.DataFrame,
    injector: Injector | None,
    model,
    context_length: int,
    prediction_length: int,
) -> dict[str, Any]:
    """One detector pass over one (possibly injected) segment."""
    frame = segment
    if injector is not None:
        frame = injector(frame, context_length)
    frame, notes = detector.prepare_segment(frame)
    context, future = detector.select_context_and_truth(
        frame, context_length, prediction_length
    )
    prediction = detector.run_ttm_forecast(
        context, context_length, prediction_length, model
    )
    residual = detector.calculate_residuals(prediction, future)
    residual_summary = detector.summarize_residuals(residual)
    anomaly_type, score, confidence, top_signals, notes = (
        detector.calculate_risk(residual_summary, future, notes)
    )
    result = detector.build_interface_json(
        future=future,
        residual_summary=residual_summary,
        anomaly_type=anomaly_type,
        risk_score=score,
        confidence=confidence,
        top_residual_signals=top_signals,
        notes=notes,
    )
    errors = detector.validate_output(result)
    if errors:
        raise ValueError(f"interface JSON validation failed: {errors}")
    return result


def print_summary(records: list[dict[str, Any]]) -> None:
    print("\nScenario summary")
    print("-" * 60)
    scenarios: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        scenarios.setdefault(record["scenario"], []).append(record)
    for name, rows in scenarios.items():
        done = [row for row in rows if "error" not in row]
        failed = len(rows) - len(done)
        matched = sum(1 for row in done if row.get("correct"))
        scores = [row["risk_score"] for row in done]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        expected = rows[0]["expected_anomaly_type"] or "-"
        match_text = (
            f"matched {matched}/{len(done)}"
            if expected != "-"
            else "control"
        )
        print(
            f"{name:16s} runs={len(done):3d} errors={failed} "
            f"mean_risk={mean_score:6.4f} {match_text} "
            f"(expected: {expected})"
        )


def main() -> None:
    args = parse_args()

    print(f"Reading Group 1 feature dataset: {args.csv_path}")
    df = detector.load_group1_features(args.csv_path)
    segments = manifest_segments(args.manifest, args.segments)
    print(
        f"Sweeping {len(segments)} {args.segments} segment(s) x 4 "
        "conditions"
    )

    cohesion_params = load_cohesion_params(args.baselines)
    scenarios = build_scenarios(cohesion_params)
    model = detector.load_model(
        args.context_length, args.prediction_length
    )

    records: list[dict[str, Any]] = []
    window_rows = args.context_length + args.prediction_length
    for segment_id in segments:
        segment = detector.select_segment(df, segment_id=segment_id)
        trip_id = str(segment["trip_id"].iloc[0])
        try:
            segment = trim_to_post_warmup(segment, window_rows)
        except ValueError as error:
            records.append(
                {
                    "trip_id": trip_id,
                    "segment_id": segment_id,
                    "scenario": "all",
                    "expected_anomaly_type": None,
                    "error": f"segment skipped: {error}",
                }
            )
            print(f"  {segment_id}: skipped ({error})")
            continue
        for name, expected, injector in scenarios:
            record: dict[str, Any] = {
                "trip_id": trip_id,
                "segment_id": segment_id,
                "scenario": name,
                "expected_anomaly_type": expected,
            }
            try:
                output = run_one(
                    segment,
                    injector,
                    model,
                    args.context_length,
                    args.prediction_length,
                )
            except Exception as error:  # noqa: BLE001 — keep sweeping
                record["error"] = f"{type(error).__name__}: {error}"
                print(f"  {segment_id} {name}: {record['error']}")
            else:
                record["anomaly_type"] = output["anomaly_type"]
                record["risk_score"] = output["risk_score"]
                record["risk_level"] = output["risk_level"]
                record["correct"] = (
                    output["anomaly_type"] == expected
                    if expected is not None
                    else None
                )
                record["interface_json"] = output
                print(
                    f"  {segment_id} {name:16s} -> "
                    f"{output['anomaly_type']:24s} "
                    f"risk={output['risk_score']:.4f} "
                    f"({output['risk_level']})"
                )
            records.append(record)

    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_file": str(args.csv_path),
            "manifest": str(args.manifest),
            "segment_selection": args.segments,
            "n_segments": len(segments),
            "model": detector.MODEL_PATH,
            "model_state": (
                "zero-shot (Story 6 fine-tuning pending; re-run "
                "this sweep on the fine-tuned artifact)"
            ),
            "context_length": args.context_length,
            "prediction_length": args.prediction_length,
            "window_policy": (
                "first context+prediction window starting at the "
                "segment's first post_warmup row (proxy conditions "
                "are defined post-warm-up; cold-start windows "
                "saturate cooling risk on healthy data)"
            ),
            "fault_start_row": (
                f"{args.context_length} rows after the "
                "post_warmup window start (context/future "
                "boundary)"
            ),
            "injections": {
                "cooling_fault": (
                    f"coolant_temp + {COOLING_OFFSET_C} degC"
                ),
                "maf_low_fault": f"maf x {MAF_GAIN}",
                "map_bias_fault": f"map x {MAP_GAIN}",
            },
            "notes": (
                "map_bias_fault deviates from proxy_support.md "
                "Stage 4 (which scopes MAP injection to the pending "
                "map_load_signal_plausibility_fault); it is our "
                "cohesion-attribution test and the expected label "
                "stays air_intake_maf_anomaly (user_stories.md "
                "Story 7)."
            ),
        },
        "results": records,
    }

    print_summary(records)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    args.output.write_text(text)
    print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()
