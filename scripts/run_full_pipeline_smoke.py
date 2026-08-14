"""Run reproducible, unmocked CSV-to-dashboard smoke tests locally."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dashboard.csv_pipeline import run_uploaded_csv_batch  # noqa: E402


REQUIRED_REPORT_FIELDS = (
    "anomaly_description",
    "possible_cause",
    "recommended_action",
)


def run_csv(csv_path: Path) -> dict[str, Any]:
    """Run one real CSV and return a compact, auditable result."""
    started = time.perf_counter()
    result = run_uploaded_csv_batch(csv_path.read_bytes(), csv_path.name)
    elapsed = time.perf_counter() - started

    components = {
        key: value
        for key, value in result.items()
        if key != "_data_source" and isinstance(value, dict)
    }
    if len(components) != 1:
        raise RuntimeError(
            f"Expected one dashboard component, received {len(components)}."
        )

    component_key, report = next(iter(components.items()))
    populated = {
        field: bool(report.get(field)) for field in REQUIRED_REPORT_FIELDS
    }
    return {
        "file": csv_path.name,
        "status": "passed" if all(populated.values()) else "failed",
        "elapsed_seconds": round(elapsed, 2),
        "component": component_key,
        "risk_score": report.get("risk_score"),
        "risk_level": report.get("risk_level"),
        "prediction_confidence": report.get("prediction_confidence"),
        "generated_fields_populated": populated,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run real Data, Model, Report, and Dashboard pipeline smoke tests."
        )
    )
    parser.add_argument("csv", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = []
    for csv_path in args.csv:
        if not csv_path.is_file():
            raise FileNotFoundError(csv_path)
        print(f"Running full pipeline: {csv_path.name}", flush=True)
        result = run_csv(csv_path)
        results.append(result)
        print(json.dumps(result, indent=2), flush=True)

    summary = {
        "test_type": "unmocked local end-to-end smoke test",
        "runs": results,
        "passed": sum(result["status"] == "passed" for result in results),
        "total": len(results),
    }
    rendered = json.dumps(summary, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
