"""Metrics for GL-322 synthetic evaluation result JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from model.risk_level_calibration import alarm_threshold
except ImportError:  # direct script run
    from risk_level_calibration import alarm_threshold

DEFAULT_INPUT = Path(
    "ttm-related/outputs/synthetic_eval_results_e5_lr5e-5.json"
)
DEFAULT_JSON = Path(
    "ttm-related/outputs/synthetic_eval_metrics_e5_lr5e-5_calibrated.json"
)
DEFAULT_MD = Path(
    "ttm-related/outputs/synthetic_eval_metrics_e5_lr5e-5_calibrated.md"
)
ALARM_THRESHOLD = alarm_threshold()
FAULT_TYPES = [
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
]


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def scored_label(row: dict[str, Any], threshold: float) -> str:
    if float(row["risk_score"]) < threshold:
        return "no_alarm"
    return str(row["anomaly_type"])


def compute_metrics(
    records: list[dict[str, Any]], threshold: float = ALARM_THRESHOLD
) -> dict[str, Any]:
    completed = [row for row in records if "error" not in row]
    primary = [
        row for row in completed if row.get("evaluation_role") == "primary"
    ]
    for row in primary:
        row["_predicted_label"] = scored_label(row, threshold)

    per_type: dict[str, dict[str, Any]] = {}
    total_tp = total_fp = total_fn = 0
    for fault_type in FAULT_TYPES:
        tp = sum(
            row.get("expected_anomaly_type") == fault_type
            and row["_predicted_label"] == fault_type
            for row in primary
        )
        fp = sum(
            row.get("expected_anomaly_type") != fault_type
            and row["_predicted_label"] == fault_type
            for row in primary
        )
        fn = sum(
            row.get("expected_anomaly_type") == fault_type
            and row["_predicted_label"] != fault_type
            for row in primary
        )
        precision, recall = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
        f1 = safe_div(2 * tp, 2 * tp + fp + fn)
        per_type[fault_type] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    healthy = [row for row in primary if row.get("fault_family") == "healthy"]
    healthy_alarms = sum(
        row["_predicted_label"] != "no_alarm" for row in healthy
    )
    injected = [row for row in primary if row.get("expected_anomaly_type")]
    attribution_correct = sum(
        row.get("anomaly_type") == row.get("expected_anomaly_type")
        for row in injected
    )
    exact_hits = sum(
        row["_predicted_label"] == row.get("expected_anomaly_type")
        for row in injected
    )

    labels = ["healthy", *FAULT_TYPES]
    predictions = ["no_alarm", *FAULT_TYPES]
    confusion = {truth: {pred: 0 for pred in predictions} for truth in labels}
    for row in primary:
        truth = row.get("expected_anomaly_type") or "healthy"
        prediction = row["_predicted_label"]
        if prediction not in predictions:
            predictions.append(prediction)
            for counts in confusion.values():
                counts[prediction] = 0
        confusion[truth][prediction] += 1

    severity: list[dict[str, Any]] = []
    keys = sorted({
        (row["scenario"], row["fault_family"], row["severity"],
         row["severity_unit"], row.get("expected_anomaly_type"))
        for row in injected
    })
    for scenario, family, level, unit, expected in keys:
        rows = [row for row in injected if row["scenario"] == scenario]
        hits = sum(row["_predicted_label"] == expected for row in rows)
        alarms = sum(row["_predicted_label"] != "no_alarm" for row in rows)
        severity.append({
            "scenario": scenario, "fault_family": family,
            "severity": level, "severity_unit": unit,
            "runs": len(rows), "hits": hits,
            "hit_rate": safe_div(hits, len(rows)),
            "alarm_rate": safe_div(alarms, len(rows)),
            "mean_risk_score": (
                sum(float(row["risk_score"]) for row in rows) / len(rows)
            ),
        })

    macro = {
        metric: sum(per_type[name][metric] for name in FAULT_TYPES)
        / len(FAULT_TYPES)
        for metric in ("precision", "recall", "f1")
    }
    micro_precision = safe_div(total_tp, total_tp + total_fp)
    micro_recall = safe_div(total_tp, total_tp + total_fn)
    return {
        "alarm_threshold": threshold,
        "hit_definition": (
            "risk_score >= threshold AND predicted type == truth"
        ),
        "completed_primary_runs": len(primary),
        "failed_runs": len(records) - len(completed),
        "per_type": per_type,
        "macro": macro,
        "micro": {
            "precision": micro_precision,
            "recall": micro_recall,
            "f1": safe_div(
                2 * micro_precision * micro_recall,
                micro_precision + micro_recall,
            ),
        },
        "healthy_false_positive_rate": safe_div(healthy_alarms, len(healthy)),
        "healthy_alarms": healthy_alarms,
        "healthy_runs": len(healthy),
        "exact_hit_rate": safe_div(exact_hits, len(injected)),
        "attribution_accuracy_ignoring_threshold": safe_div(
            attribution_correct, len(injected)
        ),
        "confusion_matrix": confusion,
        "severity_curves": severity,
        "controls": [
            {
                "scenario": row["scenario"],
                "segment_id": row["segment_id"],
                "risk_score": row["risk_score"],
                "anomaly_type": row["anomaly_type"],
                "alarm": scored_label(row, threshold) != "no_alarm",
            }
            for row in completed if row.get("evaluation_role") == "control"
        ],
    }


def markdown_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# GL-322 synthetic-fault evaluation",
        "",
        f"Alarm threshold: `{metrics['alarm_threshold']}`. A hit requires an "
        "alarm and the correct anomaly type.",
        "",
        "| Type | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in metrics["per_type"].items():
        lines.append(
            f"| {name} | {row['tp']} | {row['fp']} | {row['fn']} | "
            f"{row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )
    lines.extend([
        "",
        f"Macro F1: **{metrics['macro']['f1']:.3f}**; micro F1: "
        f"**{metrics['micro']['f1']:.3f}**; healthy FPR: "
        f"**{metrics['healthy_false_positive_rate']:.3f}**.",
        "",
        f"Exact hit rate: **{metrics['exact_hit_rate']:.3f}**; attribution "
        "accuracy without the alarm threshold: "
        f"**{metrics['attribution_accuracy_ignoring_threshold']:.3f}**.",
        "",
        "## Severity response",
        "",
        "| Scenario | Runs | Hit rate | Alarm rate | Mean risk |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in metrics["severity_curves"]:
        lines.append(
            f"| {row['scenario']} | {row['runs']} | {row['hit_rate']:.3f} | "
            f"{row['alarm_rate']:.3f} | {row['mean_risk_score']:.3f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--threshold", type=float, default=ALARM_THRESHOLD)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    metrics = compute_metrics(payload["records"], args.threshold)
    metrics["source_results"] = str(args.input)
    args.json_output.write_text(json.dumps(metrics, indent=2) + "\n")
    args.markdown_output.write_text(markdown_report(metrics))
    print(f"Wrote {args.json_output} and {args.markdown_output}")


if __name__ == "__main__":
    main()
