"""Build Report Layer evaluation inputs from selected batch windows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from report_layer.evaluation.prompt_refinement.discovery import safe_stem
from report_layer.pipeline.report_generator import generate_report


DEFAULT_CANDIDATE_DIR = Path(__file__).resolve().parent / (
    "fault_injection_candidates"
)


def _truthy(value: Any) -> bool:
    """Return true for CSV boolean-ish values."""
    return str(value).strip().lower() in {"true", "1", "yes"}


def _load_selected_rows(manifest_path: Path) -> list[dict[str, str]]:
    """Load selected window manifest rows."""
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if _truthy(row.get("selected_for_eval"))]


def _load_raw_model_output(candidate_dir: Path, csv_path: str) -> dict[str, Any]:
    """Load the raw batch Model Layer output for a selected row."""
    output_path = (
        candidate_dir
        / "raw_model_outputs"
        / f"{safe_stem(Path(csv_path))}.json"
    )
    with output_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _find_window(model_output: dict[str, Any], window_id: str) -> dict[str, Any]:
    """Find one batch window by `window_id`."""
    for window in model_output.get("windows", []):
        if isinstance(window, dict) and window.get("window_id") == window_id:
            return window
    raise ValueError(f"window_id not found in raw model output: {window_id}")


def _risk_history(model_output: dict[str, Any]) -> list[dict[str, Any]]:
    """Build dashboard/report risk history from batch windows."""
    history = []
    for window in model_output.get("windows", []):
        if not isinstance(window, dict):
            continue
        if "timestamp" not in window or "risk_score" not in window:
            continue
        history.append({
            "timestamp": window["timestamp"],
            "risk_score": window["risk_score"],
        })
    return history


def _case_id(row: dict[str, str]) -> str:
    """Return a stable filename stem for one selected window case."""
    return (
        f"{row['anomaly_type']}__"
        f"{safe_stem(Path(row.get('window_id', 'window')))}"
    )


def build_selected_window_cases(
    candidate_dir: Path = DEFAULT_CANDIDATE_DIR,
    generate_reports: bool = False,
) -> list[dict[str, str]]:
    """Write selected window ModelLayerOutput cases and optional reports."""
    manifest_path = candidate_dir / "window_candidate_manifest.csv"
    model_input_dir = candidate_dir / "selected_window_model_outputs"
    report_dir = candidate_dir / "selected_window_reports"
    model_input_dir.mkdir(parents=True, exist_ok=True)
    if generate_reports:
        report_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_selected_rows(manifest_path)
    output_rows: list[dict[str, str]] = []
    for row in rows:
        raw_model_output = _load_raw_model_output(
            candidate_dir, row["csv_path"]
        )
        selected_window = _find_window(raw_model_output, row["window_id"])
        history = _risk_history(raw_model_output)
        case_id = _case_id(row)

        model_input_path = model_input_dir / f"{case_id}.json"
        model_input_path.write_text(
            json.dumps(selected_window, indent=2),
            encoding="utf-8",
        )

        report_path = ""
        if generate_reports:
            report = generate_report(selected_window, risk_history=history)
            report_output_path = report_dir / f"{case_id}.json"
            report_output_path.write_text(
                json.dumps(report, indent=2),
                encoding="utf-8",
            )
            report_path = str(report_output_path)

        output_rows.append({
            "case_id": case_id,
            "anomaly_type": row["anomaly_type"],
            "window_id": row["window_id"],
            "risk_level": row["risk_level"],
            "model_input_path": str(model_input_path),
            "report_path": report_path,
        })

    return output_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create prompt-refinement inputs from selected windows."
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=DEFAULT_CANDIDATE_DIR,
        help="Directory containing window_candidate_manifest.csv.",
    )
    parser.add_argument(
        "--generate-reports",
        action="store_true",
        help="Also call Report Layer/Ollama and save report outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_selected_window_cases(
        candidate_dir=args.candidate_dir,
        generate_reports=args.generate_reports,
    )
    print(
        f"Wrote {len(rows)} selected window model input(s) to "
        f"{args.candidate_dir / 'selected_window_model_outputs'}"
    )
    if args.generate_reports:
        print(
            f"Wrote report output(s) to "
            f"{args.candidate_dir / 'selected_window_reports'}"
        )


if __name__ == "__main__":
    main()
