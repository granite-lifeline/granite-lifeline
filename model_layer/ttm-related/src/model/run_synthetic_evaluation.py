"""Run the GL-322 single-window synthetic-fault evaluation."""

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
        DEFAULT_CALIBRATION_REGISTRY,
        inject_cooling_fault,
        inject_intake_maf_fault,
        inject_pedal_sensor_fault,
        load_feature_transforms,
    )
except ImportError:
    import kit_residual_detector as detector
    from fault_injection import (
        DEFAULT_CALIBRATION_REGISTRY,
        inject_cooling_fault,
        inject_intake_maf_fault,
        inject_pedal_sensor_fault,
        load_feature_transforms,
    )

DEFAULT_CSV = Path(
    "ttm-related/data/production_feature_manifest/production_features.csv"
)
DEFAULT_MANIFEST = Path("ttm-related/outputs/finetune_split_manifest.json")
DEFAULT_MODEL = Path("ttm-related/outputs/ttm_finetuned_e5_lr5e-5/model")
DEFAULT_OUTPUT = Path(
    "ttm-related/outputs/synthetic_eval_results_e5_lr5e-5.json"
)
SUSTAINED_FLOW_SPEED_KMH = 30.0
Injector = Callable[[pd.DataFrame, int], pd.DataFrame]


def build_scenarios(
    transforms: dict[str, dict[str, object]],
) -> list[dict[str, Any]]:
    speed = transforms["speed_density_maf"]
    pedal = transforms["pedal_mapping"]
    scenarios: list[dict[str, Any]] = [
        {
            "scenario": "healthy",
            "fault_family": "healthy",
            "expected_anomaly_type": None,
            "evaluation_role": "primary",
            "severity": 0.0,
            "severity_unit": "none",
            "injector": None,
        }
    ]
    for offset in (5.0, 10.0, 15.0):
        scenarios.append({
            "scenario": f"cooling_offset_{offset:g}c",
            "fault_family": "cooling",
            "expected_anomaly_type": "cooling_degradation",
            "evaluation_role": "primary",
            "severity": offset,
            "severity_unit": "degC_offset",
            "injector": lambda df, start, value=offset: (
                inject_cooling_fault(df, start, value)
            ),
        })
    for gain in (0.95, 0.90, 0.80, 0.70):
        scenarios.append({
            "scenario": f"maf_gain_{gain:.2f}",
            "fault_family": "maf",
            "expected_anomaly_type": "air_intake_maf_anomaly",
            "evaluation_role": "primary",
            "severity": round(1.0 - gain, 2),
            "severity_unit": "fractional_underread",
            "injector": lambda df, start, value=gain: (
                inject_intake_maf_fault(
                    df, "low_maf", speed, start, value
                )
            ),
        })
    for offset in (2.0, 5.0, 10.0, 20.0):
        scenarios.append({
            "scenario": f"pedal_d_offset_{offset:g}pp",
            "fault_family": "pedal",
            "expected_anomaly_type": "accelerator_pedal_sensor",
            "evaluation_role": "primary",
            "severity": offset,
            "severity_unit": "percentage_point_offset",
            "injector": lambda df, start, value=offset: (
                inject_pedal_sensor_fault(
                    df, pedal, start, channel="d", mode="offset",
                    magnitude=value,
                )
            ),
        })
    for gain in (1.05, 1.10, 1.20):
        scenarios.append({
            "scenario": f"pedal_e_gain_{gain:.2f}",
            "fault_family": "pedal",
            "expected_anomaly_type": "accelerator_pedal_sensor",
            "evaluation_role": "primary",
            "severity": round(gain - 1.0, 2),
            "severity_unit": "fractional_gain_error",
            "injector": lambda df, start, value=gain: (
                inject_pedal_sensor_fault(
                    df, pedal, start, channel="e", mode="gain",
                    magnitude=value,
                )
            ),
        })
    scenarios.append({
        "scenario": "map_bias_control_1.25",
        "fault_family": "map_attribution_control",
        "expected_anomaly_type": "air_intake_maf_anomaly",
        "evaluation_role": "control",
        "severity": 0.25,
        "severity_unit": "fractional_gain_error",
        "injector": lambda df, start: inject_intake_maf_fault(
            df, "map_bias", speed, start, 1.25
        ),
    })
    return scenarios


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", nargs="?", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument(
        "--segments", choices=["validation", "all"], default="validation"
    )
    parser.add_argument(
        "--calibration-registry", type=Path,
        default=DEFAULT_CALIBRATION_REGISTRY,
    )
    parser.add_argument(
        "--context-length", type=int, default=detector.DEFAULT_CONTEXT_LENGTH
    )
    parser.add_argument(
        "--prediction-length", type=int,
        default=detector.DEFAULT_PREDICTION_LENGTH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def manifest_segments(manifest_path: Path, which: str) -> list[str]:
    with open(manifest_path) as handle:
        manifest = json.load(handle)
    groups = ["validation_trips"]
    if which == "all":
        groups.insert(0, "train_trips")
    return sorted(
        segment
        for group in groups
        for values in manifest[group].values()
        for segment in values
    )


def trim_to_post_warmup(
    segment: pd.DataFrame, min_rows: int
) -> pd.DataFrame:
    post = segment["thermal_state"].astype(str).eq("post_warmup")
    if not post.any():
        raise ValueError("segment never reaches post_warmup")
    trimmed = segment.loc[int(post.idxmax()):].reset_index(drop=True)
    if len(trimmed) < min_rows:
        raise ValueError(
            f"only {len(trimmed)} post_warmup rows, need {min_rows}"
        )
    return trimmed


def run_one(
    segment: pd.DataFrame,
    injector: Injector | None,
    model: Any,
    context_length: int,
    prediction_length: int,
) -> dict[str, Any]:
    frame = injector(segment, context_length) if injector else segment
    frame, notes = detector.prepare_segment(frame)
    context, future = detector.select_context_and_truth(
        frame, context_length, prediction_length
    )
    prediction = detector.run_ttm_forecast(
        context, context_length, prediction_length, model
    )
    residual = detector.summarize_residuals(
        detector.calculate_residuals(prediction, future)
    )
    anomaly, score, confidence, signals, notes = detector.calculate_risk(
        residual, future, notes
    )
    output = detector.build_interface_json(
        future=future,
        residual_summary=residual,
        anomaly_type=anomaly,
        risk_score=score,
        confidence=confidence,
        top_residual_signals=signals,
        notes=notes,
    )
    errors = detector.validate_output(output)
    if errors:
        raise ValueError(f"interface JSON validation failed: {errors}")
    return output


def main() -> None:
    args = parse_args()
    frame = detector.load_group1_features(args.csv_path)
    segments = manifest_segments(args.manifest, args.segments)
    transforms = load_feature_transforms(args.calibration_registry)
    scenarios = build_scenarios(transforms)
    model = detector.load_model(
        args.context_length, args.prediction_length, args.model_path
    )
    records: list[dict[str, Any]] = []
    needed = args.context_length + args.prediction_length
    for segment_id in segments:
        segment = detector.select_segment(frame, segment_id=segment_id)
        trip_id = str(segment["trip_id"].iloc[0])
        try:
            segment = trim_to_post_warmup(segment, needed)
        except ValueError as error:
            records.append({
                "trip_id": trip_id, "segment_id": segment_id,
                "scenario": "all", "error": f"segment skipped: {error}",
            })
            continue
        sustained = int(
            (segment.iloc[args.context_length:needed]["speed"]
             > SUSTAINED_FLOW_SPEED_KMH).sum()
        )
        for scenario in scenarios:
            record = {
                key: value for key, value in scenario.items()
                if key != "injector"
            }
            record.update({
                "trip_id": trip_id,
                "segment_id": segment_id,
                "injection_start_row": args.context_length,
                "injection_duration_rows": args.prediction_length,
                "future_sustained_flow_rows": sustained,
            })
            try:
                output = run_one(
                    segment, scenario["injector"], model,
                    args.context_length, args.prediction_length,
                )
                record.update({
                    "anomaly_type": output["anomaly_type"],
                    "risk_score": output["risk_score"],
                    "risk_level": output["risk_level"],
                    "interface_json": output,
                })
            except Exception as error:  # noqa: BLE001
                record["error"] = f"{type(error).__name__}: {error}"
            records.append(record)
            status = record.get("error") or (
                f"{record['anomaly_type']} {record['risk_score']:.3f}"
            )
            print(f"{segment_id} {record['scenario']}: {status}")

    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "csv_path": str(args.csv_path),
            "manifest_path": str(args.manifest),
            "model_path": str(args.model_path),
            "segments": args.segments,
            "context_length": args.context_length,
            "prediction_length": args.prediction_length,
            "injection_design": "512 healthy context + 96 injected future",
            "risk_alarm_threshold": 0.3,
            "calibration_registry": str(args.calibration_registry),
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.output} ({len(records)} records)")


if __name__ == "__main__":
    main()
