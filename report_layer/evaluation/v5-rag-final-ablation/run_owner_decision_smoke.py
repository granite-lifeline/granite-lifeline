#!/usr/bin/env python3
"""Generate five production reports after owner-decision RAG governance."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from report_layer.pipeline.report_generator import (  # noqa: E402
    generate_report,
)


FIXTURE_DIR = (
    PROJECT_ROOT / "report_layer" / "evaluation" / "prompt_refinement"
    / "fault_injection_candidates" / "selected_window_model_outputs"
)
OUTPUT_DIR = Path(__file__).resolve().parent
FIXTURES = [
    "cooling_degradation__trip_0040_seg_001__w003.json",
    "air_intake_maf_anomaly__trip_0061_seg_001__w002.json",
    "accelerator_pedal_sensor__trip_0041_seg_001__w002.json",
    "intake_air_temperature_sensor_fault__trip_0001_seg_001__w001.json",
    "map_load_signal_plausibility_fault__trip_0001_seg_001__w001.json",
]
PREFIXES = (
    "Now:",
    "Service timing:",
    "Stop driving and seek help if:",
    "Tell the mechanic:",
)
OWNER_TECHNICAL_TERMS = (
    "connect a scan tool",
    "use a multimeter",
    "clear the diagnostic",
    "remove the",
    "replace the",
    "clean the contacts",
    "perform a relearn",
)


def _audit(report: dict[str, Any]) -> dict[str, Any]:
    actions = report.get("recommended_action") or []
    lower_actions = [str(action).lower() for action in actions]
    return {
        "released": bool(report.get("anomaly_description")),
        "action_count": len(actions),
        "prefixes_present": {
            prefix: any(
                str(action).startswith(prefix) for action in actions
            )
            for prefix in PREFIXES
        },
        "owner_technical_instructions": [
            term
            for term in OWNER_TECHNICAL_TERMS
            if any(
                term in action
                and not action.startswith("tell the mechanic:")
                for action in lower_actions
            )
        ],
    }


def run(anomaly_types: set[str] | None = None) -> None:
    raw_path = OUTPUT_DIR / "owner_decision_smoke_raw.json"
    rows = []
    for fixture_name in FIXTURES:
        fixture = json.loads((FIXTURE_DIR / fixture_name).read_text())
        if (
            anomaly_types
            and fixture["anomaly_type"] not in anomaly_types
        ):
            continue
        print(f"RUN {fixture['anomaly_type']}", flush=True)
        started = time.time()
        report = generate_report(fixture)
        row = {
            "fixture": fixture_name,
            "anomaly_type": fixture["anomaly_type"],
            "risk_level": fixture.get("risk_level"),
            "elapsed_seconds": round(time.time() - started, 2),
            "report": report,
            "audit": _audit(report),
        }
        rows.append(row)
        print(
            f"DONE {fixture['anomaly_type']}: {row['audit']}",
            flush=True,
        )

    if anomaly_types and raw_path.exists():
        existing = json.loads(raw_path.read_text(encoding="utf-8"))
        rows = [
            row for row in existing
            if row.get("anomaly_type") not in anomaly_types
        ] + rows
        fixture_order = {
            name.split("__", 1)[0]: index
            for index, name in enumerate(FIXTURES)
        }
        rows.sort(key=lambda row: fixture_order[row["anomaly_type"]])
    raw_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# Owner-decision compatibility smoke test",
        "",
        "| Anomaly | Risk | Released | Four actions | All prefixes | "
        "Owner technical instructions |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        audit = row["audit"]
        lines.append(
            f"| {row['anomaly_type']} | {row['risk_level']} | "
            f"{'Yes' if audit['released'] else 'No'} | "
            f"{'Yes' if audit['action_count'] == 4 else 'No'} | "
            f"{'Yes' if all(audit['prefixes_present'].values()) else 'No'} | "
            f"{len(audit['owner_technical_instructions'])} |"
        )
    (OUTPUT_DIR / "owner_decision_smoke_results.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    """Parse optional anomaly filters for targeted reruns."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--anomaly-type", action="append", default=[])
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(set(args.anomaly_type) or None)
