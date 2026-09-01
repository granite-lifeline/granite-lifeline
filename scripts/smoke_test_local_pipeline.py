"""Run one real local CSV-to-report integration smoke test.

This command is intentionally separate from CI. It requires the local Data
Layer, committed TTM runtime, production RAG index and Ollama Granite model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.csv_pipeline import (  # noqa: E402
    run_uploaded_csv_batch,
    run_uploaded_csv_history_batch,
)
from shared.interface_models import ReportLayerOutput  # noqa: E402


def validate_dashboard_reports(dashboard_data: dict[str, Any]) -> list[str]:
    """Validate that every returned component has a complete live report."""
    generated = []
    incomplete = []
    for component, payload in dashboard_data.items():
        if component == "_data_source" or not isinstance(payload, dict):
            continue
        report = ReportLayerOutput(**payload)
        if (
            report.anomaly_description.strip()
            and report.possible_cause.strip()
            and report.recommended_action
        ):
            generated.append(component)
        else:
            incomplete.append(component)
    if incomplete:
        raise RuntimeError(
            "The pipeline returned an empty fallback report for: "
            + ", ".join(incomplete)
            + ". Check the Report Layer logs."
        )
    if not generated:
        raise RuntimeError("The pipeline returned no affected components.")
    return generated


def _progress(percent: int, message: str) -> None:
    print(f"[{percent:3d}%] {message}")


def run(csv_paths: list[Path]) -> list[str]:
    """Run the existing upload integration path for one or more trips."""
    trips = [(path.read_bytes(), path.name) for path in csv_paths]
    if len(trips) == 1:
        dashboard_data = run_uploaded_csv_batch(
            trips[0][0], trips[0][1], progress_callback=_progress
        )
    else:
        if len(trips) < 5:
            raise ValueError("Use either one CSV or at least five CSV files.")
        result = run_uploaded_csv_history_batch(
            trips, progress_callback=_progress
        )
        dashboard_data = result["dashboard_data"]
    return validate_dashboard_reports(dashboard_data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a real local Granite Lifeline pipeline smoke test."
    )
    parser.add_argument(
        "csv",
        nargs="+",
        type=Path,
        help="One original KIT CSV, or at least five chronological KIT CSVs.",
    )
    args = parser.parse_args()
    missing = [str(path) for path in args.csv if not path.is_file()]
    if missing:
        parser.error("CSV file not found: " + ", ".join(missing))

    components = run(args.csv)
    print("PASS: complete generated report for " + ", ".join(components))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
