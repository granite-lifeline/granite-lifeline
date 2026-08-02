"""Build prompt-refinement candidates from real CSV pipeline runs.

The discovery pass runs real OBD-II CSV files through the current Data Layer
and Model Layer, writes raw model outputs, and creates manifest/audit CSVs.
Report generation is optional because it requires a local Ollama Granite model.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from dashboard.csv_pipeline import (
    UploadedCsvPipelineError,
    _run_data_layer,
    _run_model_layer,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = REPO_ROOT / "data" / "raw" / "OBD-II-Dataset"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent
FORWARDED_TYPES = (
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault",
)
NATIVE_MODEL_TYPES = (
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
)
RISK_LEVEL_ORDER = ("High", "Medium", "Low")
PROXY_PROVENANCE_MARKERS = (
    "forwarded from Data Layer proxy_decisions.csv",
    "Data Layer proxy decision",
    "not TTM residual scoring",
)


@dataclass(frozen=True)
class FeatureProxyPair:
    """Existing feature/proxy artifacts to send directly to Model Layer."""

    source_id: str
    production_features_path: Path
    proxy_decisions_path: Path


def repo_relative(path: Path | None) -> str:
    """Return a repo-relative path when possible, else an empty/string path."""
    if path is None:
        return ""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def safe_stem(path: Path) -> str:
    """Return a filesystem-safe stem while preserving the source identity."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)


def extract_summary(model_output: dict[str, Any]) -> dict[str, Any]:
    """Return the `summary` payload from single or batch model output."""
    summary = model_output.get("summary")
    if isinstance(summary, dict) and isinstance(
        model_output.get("windows"), list
    ):
        return summary
    return model_output


def extract_risk_history_count(model_output: dict[str, Any]) -> int:
    """Count usable batch risk-history points."""
    windows = model_output.get("windows")
    if not isinstance(windows, list):
        return 0
    return sum(
        1
        for window in windows
        if isinstance(window, dict)
        and "timestamp" in window
        and "risk_score" in window
    )


def has_proxy_provenance_note(notes: Iterable[Any]) -> bool:
    """Return true when notes identify proxy-forwarding provenance."""
    note_text = "\n".join(str(note) for note in notes)
    return any(marker in note_text for marker in PROXY_PROVENANCE_MARKERS)


def summarize_model_output(
    source_path: Path,
    model_output: dict[str, Any],
    proxy_decisions_path: Path | None,
    source_kind: str = "real_csv",
) -> dict[str, Any]:
    """Create one manifest row from a model output envelope."""
    summary = extract_summary(model_output)
    notes = summary.get("notes") or []
    if not isinstance(notes, list):
        notes = [notes]
    cycles = summary.get("estimated_cycles_to_failure")
    probability = summary.get("estimated_failure_probability")
    return {
        "source_kind": source_kind,
        "csv_path": repo_relative(source_path),
        "output_shape": (
            "batch"
            if isinstance(model_output.get("windows"), list)
            else "single"
        ),
        "anomaly_type": summary.get("anomaly_type", ""),
        "risk_score": summary.get("risk_score", ""),
        "risk_level": summary.get("risk_level", ""),
        "prediction_confidence": summary.get(
            "prediction_confidence", ""
        ),
        "estimated_cycles_to_failure": cycles,
        "estimated_failure_probability": probability,
        "projection_is_null": cycles is None or probability is None,
        "risk_history_count": extract_risk_history_count(model_output),
        "has_notes": bool(notes),
        "notes": " | ".join(str(note) for note in notes),
        "has_proxy_decisions_path": proxy_decisions_path is not None,
        "proxy_decisions_path": repo_relative(proxy_decisions_path),
        "has_proxy_provenance_note": has_proxy_provenance_note(notes),
        "selected_for_eval": False,
        "selection_reason": "",
    }


def summarize_proxy_decisions(
    source_path: Path,
    proxy_decisions_path: Path | None,
    source_kind: str = "real_csv",
) -> list[dict[str, Any]]:
    """Summarize Data Layer proxy decisions for the two forwarded types."""
    rows = []
    if proxy_decisions_path is None:
        for anomaly_type in FORWARDED_TYPES:
            rows.append({
                "source_kind": source_kind,
                "csv_path": repo_relative(source_path),
                "proxy_decisions_path": "",
                "anomaly_type": anomaly_type,
                "rows": 0,
                "triggered_rows": 0,
                "dtc_emitted_rows": 0,
                "result_states": "",
                "confidence_values": "",
                "sub_checks": "",
                "has_positive_proxy_evidence": False,
            })
        return rows

    df = pd.read_csv(proxy_decisions_path, low_memory=False)
    for anomaly_type in FORWARDED_TYPES:
        subset = df[df.get("proxy_id") == anomaly_type]
        triggered = subset[subset.get("result_state") == "triggered"]
        dtc_emitted = subset[subset.get("dtc_emitted").astype(str) == "True"]
        rows.append({
            "source_kind": source_kind,
            "csv_path": repo_relative(source_path),
            "proxy_decisions_path": repo_relative(proxy_decisions_path),
            "anomaly_type": anomaly_type,
            "rows": len(subset),
            "triggered_rows": len(triggered),
            "dtc_emitted_rows": len(dtc_emitted),
            "result_states": "|".join(
                sorted(
                    str(value)
                    for value in subset["result_state"].dropna().unique()
                )
            ),
            "confidence_values": "|".join(
                sorted(
                    str(value)
                    for value in subset["confidence"].dropna().unique()
                )
            ),
            "sub_checks": "|".join(
                sorted(
                    str(value)
                    for value in subset["sub_check_id"].dropna().unique()
                )
            ),
            "has_positive_proxy_evidence": (
                len(triggered) > 0 or len(dtc_emitted) > 0
            ),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows as CSV, preserving first-row field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _as_float(value: Any) -> float:
    """Convert numeric-ish values for candidate ranking."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def mark_selected_eval_cases(
    manifest_rows: list[dict[str, Any]],
    proxy_rows: list[dict[str, Any]],
) -> None:
    """Mark representative real outputs for prompt-refinement evaluation.

    Native Model Layer anomaly types are selected by anomaly type and risk
    level. Proxy-forwarded types are only selected when the model output also
    carries an explicit proxy provenance note and the proxy audit has positive
    evidence for that CSV/type pair.
    """
    positive_proxy_pairs = {
        (row["csv_path"], row["anomaly_type"])
        for row in proxy_rows
        if row.get("has_positive_proxy_evidence") is True
        or row.get("has_positive_proxy_evidence") == "True"
    }

    for anomaly_type in NATIVE_MODEL_TYPES:
        for risk_level in RISK_LEVEL_ORDER:
            candidates = [
                row
                for row in manifest_rows
                if row.get("output_shape") in {"single", "batch"}
                and row.get("anomaly_type") == anomaly_type
                and row.get("risk_level") == risk_level
            ]
            if not candidates:
                continue
            selected = max(
                candidates,
                key=lambda row: (
                    _as_float(row.get("prediction_confidence")),
                    _as_float(row.get("risk_score")),
                    row.get("risk_history_count", 0),
                ),
            )
            selected["selected_for_eval"] = True
            selected["selection_reason"] = (
                f"representative_{anomaly_type}_{risk_level.lower()}"
            )

    for anomaly_type in FORWARDED_TYPES:
        candidates = [
            row
            for row in manifest_rows
            if row.get("output_shape") in {"single", "batch"}
            and row.get("anomaly_type") == anomaly_type
            and row.get("has_proxy_provenance_note") is True
            and (row.get("csv_path"), anomaly_type) in positive_proxy_pairs
        ]
        if not candidates:
            continue
        selected = max(
            candidates,
            key=lambda row: (
                _as_float(row.get("prediction_confidence")),
                _as_float(row.get("risk_score")),
            ),
        )
        selected["selected_for_eval"] = True
        selected["selection_reason"] = (
            f"proxy_forwarded_positive_{anomaly_type}"
        )


def discover_csvs(
    csv_paths: list[Path],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    generate_reports: bool = False,
    continue_on_error: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run discovery and return `(manifest_rows, proxy_audit_rows)`."""
    raw_output_dir = output_dir / "raw_model_outputs"
    report_output_dir = output_dir / "generated_reports"
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    if generate_reports:
        report_output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    proxy_rows: list[dict[str, Any]] = []

    for csv_path in csv_paths:
        try:
            production_path, proxy_path = _run_data_layer(csv_path)
            output_path = raw_output_dir / f"{safe_stem(csv_path)}.json"
            model_output = _run_model_layer(
                production_path, proxy_path, output_path
            )
            manifest_rows.append(
                summarize_model_output(csv_path, model_output, proxy_path)
            )
            proxy_rows.extend(summarize_proxy_decisions(csv_path, proxy_path))

            if generate_reports:
                from dashboard.data_loader import (
                    load_model_output_for_dashboard,
                )

                report = load_model_output_for_dashboard(
                    model_output, "real_csv_evaluation"
                )
                report_path = report_output_dir / f"{safe_stem(csv_path)}.json"
                report_path.write_text(
                    json.dumps(report, indent=2), encoding="utf-8"
                )

        except Exception as exc:
            if not continue_on_error:
                raise
            manifest_rows.append({
                "source_kind": "real_csv",
                "csv_path": repo_relative(csv_path),
                "output_shape": "error",
                "anomaly_type": "",
                "risk_score": "",
                "risk_level": "",
                "prediction_confidence": "",
                "estimated_cycles_to_failure": "",
                "estimated_failure_probability": "",
                "projection_is_null": "",
                "risk_history_count": 0,
                "has_notes": True,
                "notes": (
                    str(exc)
                    if isinstance(exc, UploadedCsvPipelineError)
                    else f"{type(exc).__name__}: {exc}"
                ),
                "has_proxy_decisions_path": False,
                "proxy_decisions_path": "",
                "has_proxy_provenance_note": False,
                "selected_for_eval": False,
                "selection_reason": "pipeline_error",
            })

    mark_selected_eval_cases(manifest_rows, proxy_rows)
    write_csv(output_dir / "real_csv_manifest.csv", manifest_rows)
    write_csv(output_dir / "proxy_forwarding_audit.csv", proxy_rows)
    return manifest_rows, proxy_rows


def parse_feature_proxy_pair(value: str) -> FeatureProxyPair:
    """Parse `source_id=features.csv:proxy_decisions.csv` CLI values."""
    source_id = ""
    pair_value = value
    if "=" in value:
        source_id, pair_value = value.split("=", 1)
    if ":" not in pair_value:
        raise argparse.ArgumentTypeError(
            "--feature-proxy-pair must use "
            "source_id=production_features.csv:proxy_decisions.csv"
        )
    features_raw, proxy_raw = pair_value.split(":", 1)
    features = Path(features_raw)
    proxy = Path(proxy_raw)
    if not source_id:
        source_id = features.parent.parent.parent.name or features.stem
    return FeatureProxyPair(source_id, features, proxy)


def feature_proxy_pair_from_run_dir(run_dir: Path) -> FeatureProxyPair:
    """Build a direct Model Layer input pair from a processed run dir."""
    return FeatureProxyPair(
        source_id=run_dir.name,
        production_features_path=(
            run_dir / "features" / "41_production"
            / "production_features.csv"
        ),
        proxy_decisions_path=(
            run_dir / "proxy" / "70_decisions" / "proxy_decisions.csv"
        ),
    )


def discover_feature_proxy_pairs(
    pairs: list[FeatureProxyPair],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    continue_on_error: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run Model Layer directly on existing feature/proxy artifacts."""
    raw_output_dir = output_dir / "raw_model_outputs"
    raw_output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    proxy_rows: list[dict[str, Any]] = []

    for pair in pairs:
        try:
            if not pair.production_features_path.is_file():
                raise UploadedCsvPipelineError(
                    "production_features.csv not found: "
                    f"{pair.production_features_path}"
                )
            if not pair.proxy_decisions_path.is_file():
                raise UploadedCsvPipelineError(
                    "proxy_decisions.csv not found: "
                    f"{pair.proxy_decisions_path}"
                )
            output_path = (
                raw_output_dir / f"{safe_stem(Path(pair.source_id))}.json"
            )
            model_output = _run_model_layer(
                pair.production_features_path,
                pair.proxy_decisions_path,
                output_path,
            )
            manifest_rows.append(
                summarize_model_output(
                    Path(pair.source_id),
                    model_output,
                    pair.proxy_decisions_path,
                    source_kind="feature_proxy_pair",
                )
            )
            proxy_rows.extend(
                summarize_proxy_decisions(
                    Path(pair.source_id),
                    pair.proxy_decisions_path,
                    source_kind="feature_proxy_pair",
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            manifest_rows.append({
                "source_kind": "feature_proxy_pair",
                "csv_path": pair.source_id,
                "output_shape": "error",
                "anomaly_type": "",
                "risk_score": "",
                "risk_level": "",
                "prediction_confidence": "",
                "estimated_cycles_to_failure": "",
                "estimated_failure_probability": "",
                "projection_is_null": "",
                "risk_history_count": 0,
                "has_notes": True,
                "notes": (
                    str(exc)
                    if isinstance(exc, UploadedCsvPipelineError)
                    else f"{type(exc).__name__}: {exc}"
                ),
                "has_proxy_decisions_path": False,
                "proxy_decisions_path": repo_relative(
                    pair.proxy_decisions_path
                ),
                "has_proxy_provenance_note": False,
                "selected_for_eval": False,
                "selection_reason": "pipeline_error",
            })

    mark_selected_eval_cases(manifest_rows, proxy_rows)
    write_csv(output_dir / "real_csv_manifest.csv", manifest_rows)
    write_csv(output_dir / "proxy_forwarding_audit.csv", proxy_rows)
    return manifest_rows, proxy_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover real CSV prompt-refinement candidates."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=DEFAULT_CSV_DIR,
        help="Directory of real OBD-II CSV files.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        action="append",
        default=[],
        help="Specific CSV file to run. Can be passed multiple times.",
    )
    parser.add_argument(
        "--glob",
        default="*.csv",
        help="Glob used when --csv is not provided.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of CSV files to run.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for manifest/audit/model outputs.",
    )
    parser.add_argument(
        "--feature-proxy-pair",
        type=parse_feature_proxy_pair,
        action="append",
        default=[],
        help=(
            "Existing Model input artifacts to run directly, formatted as "
            "source_id=production_features.csv:proxy_decisions.csv. "
            "Use this for fault-injection evidence."
        ),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=[],
        help=(
            "Existing processed run directory containing "
            "features/41_production/production_features.csv and "
            "proxy/70_decisions/proxy_decisions.csv."
        ),
    )
    parser.add_argument(
        "--generate-reports",
        action="store_true",
        help="Also run Report Layer/Ollama and save generated reports.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first failed CSV instead of recording it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pairs = list(args.feature_proxy_pair)
    pairs.extend(feature_proxy_pair_from_run_dir(path) for path in args.run_dir)
    csv_paths = list(args.csv)
    if not csv_paths and not pairs:
        csv_paths = sorted(args.csv_dir.glob(args.glob))
    if args.limit is not None:
        csv_paths = csv_paths[:args.limit]
    if not csv_paths and not pairs:
        raise SystemExit("No CSV files or feature/proxy pairs selected.")

    manifest_rows, proxy_rows = discover_csvs(
        csv_paths=csv_paths,
        output_dir=args.output_dir,
        generate_reports=args.generate_reports,
        continue_on_error=not args.fail_fast,
    ) if csv_paths else ([], [])
    pair_manifest_rows, pair_proxy_rows = discover_feature_proxy_pairs(
        pairs=pairs,
        output_dir=args.output_dir,
        continue_on_error=not args.fail_fast,
    ) if pairs else ([], [])
    manifest_rows.extend(pair_manifest_rows)
    proxy_rows.extend(pair_proxy_rows)
    if pairs and csv_paths:
        mark_selected_eval_cases(manifest_rows, proxy_rows)
        write_csv(args.output_dir / "real_csv_manifest.csv", manifest_rows)
        write_csv(args.output_dir / "proxy_forwarding_audit.csv", proxy_rows)
    print(
        f"Wrote {len(manifest_rows)} manifest row(s) and "
        f"{len(proxy_rows)} proxy audit row(s) to {args.output_dir}"
    )


if __name__ == "__main__":
    main()
