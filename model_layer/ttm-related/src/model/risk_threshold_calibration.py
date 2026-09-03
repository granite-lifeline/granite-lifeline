"""Calibrate Model Layer Low/Medium/High risk-score thresholds.

The script never retrains TTM and never edits the Data Layer's frozen
calibration registry.  It re-scores the committed, per-window synthetic
evaluation result using candidate alarm lines, chooses a line with a
pre-declared rule, and records both calibration and held-out segment results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    from model.risk_level_calibration import (
        DEFAULT_CALIBRATION_PATH,
        load_risk_level_calibration,
        risk_level,
    )
    from model.synthetic_evaluation_metrics import compute_metrics
except ImportError:  # direct script run
    from risk_level_calibration import (
        DEFAULT_CALIBRATION_PATH,
        load_risk_level_calibration,
        risk_level,
    )
    from synthetic_evaluation_metrics import compute_metrics


DEFAULT_INPUT = Path(
    "ttm-related/outputs/synthetic_eval_results_e5_lr5e-5.json"
)
DEFAULT_REGISTRY = Path("data_layer/calibration/calibration_registry.v1.json")
DEFAULT_JSON = Path(
    "ttm-related/outputs/risk_threshold_calibration_e5_lr5e-5.json"
)
DEFAULT_MD = Path(
    "ttm-related/outputs/risk_threshold_calibration_e5_lr5e-5.md"
)
TARGET_HEALTHY_FPR = 0.10


def primary_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in records
        if "error" not in row and row.get("evaluation_role") == "primary"
    ]


def split_segments(
    records: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Use every third sorted segment as an untouched hold-out subset."""
    segments = sorted({row["segment_id"] for row in primary_records(records)})
    if len(segments) < 3:
        raise ValueError("threshold calibration needs at least three segments")
    held_out = segments[2::3]
    calibration = [segment for segment in segments if segment not in held_out]
    return calibration, held_out


def records_for_segments(
    records: list[dict[str, Any]], segments: list[str]
) -> list[dict[str, Any]]:
    selected = set(segments)
    return [row for row in records if row.get("segment_id") in selected]


def candidate_thresholds(records: list[dict[str, Any]]) -> list[float]:
    scores = {
        float(row["risk_score"])
        for row in primary_records(records)
    }
    # The final sentinel documents the all-clear baseline when no candidate
    # can satisfy the FPR requirement; it can never be selected otherwise.
    return sorted({0.0, *scores, math.nextafter(1.0, math.inf)})


def compact_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        "macro_f1": metrics["macro"]["f1"],
        "micro_f1": metrics["micro"]["f1"],
        "exact_hit_rate": metrics["exact_hit_rate"],
        "healthy_false_positive_rate": metrics[
            "healthy_false_positive_rate"
        ],
        "healthy_alarms": metrics["healthy_alarms"],
        "healthy_runs": metrics["healthy_runs"],
    }


def score_thresholds(
    records: list[dict[str, Any]], thresholds: list[float]
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for threshold in thresholds:
        metrics = compute_metrics([dict(row) for row in records], threshold)
        rows.append({"threshold": threshold, **compact_metrics(metrics)})
    return rows


def choose_threshold(
    rows: list[dict[str, float]], target_fpr: float = TARGET_HEALTHY_FPR
) -> dict[str, float]:
    feasible = [
        row for row in rows
        if row["healthy_false_positive_rate"] <= target_fpr
    ]
    if not feasible:
        raise ValueError(
            "the candidate set does not include an all-clear line"
        )
    # In tie cases: retain more true hits, then fewer healthy alarms, then use
    # the lower threshold so the policy does not discard detection needlessly.
    return max(
        feasible,
        key=lambda row: (
            row["macro_f1"], row["exact_hit_rate"],
            -row["healthy_false_positive_rate"], -row["threshold"],
        ),
    )


def registry_reconciliation(path: Path) -> dict[str, Any]:
    """Record the frozen Data Layer rules that overlap our input evidence."""
    payload = json.loads(path.read_text())
    rules = payload["proxy_rules"]
    required = ("1-S1", "1-S3", "2-S2", "3-S1a")
    missing = [name for name in required if name not in rules]
    if missing:
        raise ValueError(
            f"registry is missing expected proxy rules: {missing}"
        )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "calibration_version": payload["calibration_version"],
        "status": payload["status"],
        "immutable": payload["immutable"],
        "read_only_confirmation": (
            "The registry was read for this report and was not modified."
        ),
        "overlap": {
            "cooling": {
                "rules": ["1-S1", "1-S3"],
                "detector_inputs": ["coolant_temp", "ect_rate_180s"],
            },
            "maf": {
                "rules": ["2-S2"],
                "detector_inputs": [
                    "speed_density_maf_residual", "maf", "map"
                ],
            },
            "pedal": {
                "rules": ["3-S1a"],
                "detector_inputs": [
                    "accel_pedal_channel_delta", "pedal_mapping_residual"
                ],
            },
        },
    }


def level_distribution(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    distribution: dict[str, dict[str, int]] = {}
    for row in primary_records(records):
        family = str(row["fault_family"])
        levels = distribution.setdefault(
            family, {"Low": 0, "Medium": 0, "High": 0}
        )
        levels[risk_level(float(row["risk_score"]))] += 1
    return distribution


def markdown_report(payload: dict[str, Any]) -> str:
    selected = payload["selection"]["selected"]
    config = payload["policy"]
    calibration = payload["selection"]["calibration_metrics"]
    holdout = payload["selection"]["holdout_metrics"]
    full = payload["selection"]["full_metrics"]
    baseline = payload["selection"]["previous_0_3_metrics"]
    lines = [
        "# Model risk-threshold calibration (epochs=5, lr=5e-5)",
        "",
        "## Decision",
        "",
        f"- **Low:** score `< {config['medium_min_inclusive']:.4f}` — "
        "record only.",
        f"- **Medium:** score `>= {config['medium_min_inclusive']:.4f}` and "
        f"`< {config['high_min_inclusive']:.4f}` — inspection alarm.",
        f"- **High:** score `>= {config['high_min_inclusive']:.4f}` — "
        "priority inspection alarm.",
        "",
        "The alarm line was selected on the calibration subset by maximising "
        "macro F1 while requiring healthy false-positive rate (FPR) <= 10%. "
        "The High boundary is a conservative near-maximum-evidence label; it "
        "is not a calibrated probability of vehicle failure.",
        "",
        "## Selection evidence",
        "",
        f"- Selected alarm line: `{selected['threshold']:.4f}`.",
        "- Calibration segments "
        f"({len(payload['split']['calibration_segments'])}): "
        + ", ".join(payload["split"]["calibration_segments"]),
        f"- Held-out segments ({len(payload['split']['held_out_segments'])}): "
        + ", ".join(payload["split"]["held_out_segments"]),
        "",
        "| Evaluation subset | Alarm line | Macro F1 | Exact hit rate "
        "| Healthy FPR | Healthy alarms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, metrics in (
        ("Previous policy (all segments)", baseline),
        ("Calibration subset", calibration),
        ("Held-out subset", holdout),
        ("All 11 segments", full),
    ):
        threshold = (
            0.3 if label.startswith("Previous") else selected["threshold"]
        )
        lines.append(
            f"| {label} | {threshold:.4f} | {metrics['macro_f1']:.3f} | "
            f"{metrics['exact_hit_rate']:.3f} | "
            f"{metrics['healthy_false_positive_rate']:.3f} | "
            f"{int(metrics['healthy_alarms'])}/"
            f"{int(metrics['healthy_runs'])} |"
        )
    lines.extend([
        "",
        "## Important limitation",
        "",
        "The selected line meets the 10% healthy-FPR target on the eight "
        "calibration segments, but the three held-out segments contain one "
        "healthy score of 1.0. Therefore their healthy FPR is 1/3, and no "
        "threshold at or below 1.0 can remove that false alarm. This policy "
        "is consequently provisional: it makes the choice reproducible, but "
        "does not prove real-fault performance or safety suitability.",
        "",
        "## Frozen Data Layer registry check",
        "",
        f"Read-only registry: `{payload['registry_reconciliation']['path']}` "
        f"(`{payload['registry_reconciliation']['calibration_version']}`, "
        f"SHA-256 `{payload['registry_reconciliation']['sha256']}`).",
        "",
        "The registry was not modified. Its cooling (1-S1/1-S3), MAF (2-S2), "
        "and pedal (3-S1a) rules remain the source for the physical evidence "
        "features; this Model Layer policy only maps the already-normalised "
        "risk score to Low, Medium, or High.",
        "",
        "## Reproduction",
        "",
        "```bash",
        ".venv/bin/python ttm-related/src/model/risk_threshold_calibration.py",
        "```",
        "",
        "The complete candidate-line table is stored in the companion JSON "
        "file. No TTM training or synthetic-injection run is performed here.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--policy", type=Path, default=DEFAULT_CALIBRATION_PATH
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = json.loads(args.input.read_text())
    records = source["records"]
    calibration_segments, held_out_segments = split_segments(records)
    calibration_records = records_for_segments(records, calibration_segments)
    held_out_records = records_for_segments(records, held_out_segments)
    thresholds = candidate_thresholds(records)
    candidates = score_thresholds(calibration_records, thresholds)
    selected = choose_threshold(candidates)
    policy = load_risk_level_calibration(args.policy)
    policy_thresholds = policy["risk_level_thresholds"]
    configured_alarm = float(policy_thresholds["medium_min_inclusive"])
    if not math.isclose(
        configured_alarm, selected["threshold"], abs_tol=1e-12
    ):
        raise ValueError(
            "policy alarm threshold does not match reproducible selection: "
            f"configured={configured_alarm}, selected={selected['threshold']}"
        )

    selected_threshold = selected["threshold"]
    payload = {
        "calibration_type": "model_risk_threshold_sweep",
        "source_results": str(args.input),
        "source_metadata": source.get("metadata", {}),
        "selection_rule": {
            "target_healthy_false_positive_rate": TARGET_HEALTHY_FPR,
            "objective": "maximise macro_f1 among thresholds meeting target",
            "tie_breakers": [
                "higher exact_hit_rate", "lower healthy_false_positive_rate",
                "lower threshold",
            ],
        },
        "split": {
            "method": "every third sorted segment held out",
            "calibration_segments": calibration_segments,
            "held_out_segments": held_out_segments,
        },
        "policy": {
            "path": str(args.policy),
            "calibration_version": policy["calibration_version"],
            "status": policy["status"],
            **policy_thresholds,
        },
        "selection": {
            "selected": selected,
            "candidate_metrics_on_calibration_subset": candidates,
            "previous_0_3_metrics": compact_metrics(
                compute_metrics([dict(row) for row in records], 0.3)
            ),
            "calibration_metrics": compact_metrics(
                compute_metrics(
                    [dict(row) for row in calibration_records],
                    selected_threshold,
                )
            ),
            "holdout_metrics": compact_metrics(
                compute_metrics(
                    [dict(row) for row in held_out_records],
                    selected_threshold,
                )
            ),
            "full_metrics": compact_metrics(
                compute_metrics(
                    [dict(row) for row in records], selected_threshold
                )
            ),
        },
        "risk_level_distribution_all_segments": level_distribution(records),
        "registry_reconciliation": registry_reconciliation(args.registry),
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2) + "\n")
    args.markdown_output.write_text(markdown_report(payload))
    print(
        f"Selected alarm threshold {selected_threshold:.4f}; wrote "
        f"{args.json_output} and {args.markdown_output}"
    )


if __name__ == "__main__":
    main()
