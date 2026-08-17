#!/usr/bin/env python3
"""Generate blind no-RAG/RAG Dashboard stimuli from one Model batch.

The Data and Model outputs are held fixed. Both conditions use the same
Granite model, temperature, prompts, certainty guidance, validator and
correction path; only retrieved fault/action knowledge changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.data_loader import (
    _best_component_payloads,
    _component_risk_history,
)
from report_layer.pipeline import report_generator
from report_layer.pipeline.context_injection import build_context_with_rag
from shared.interface_models import ModelLayerOutput


NO_FAULT_KNOWLEDGE = (
    "No retrieved fault knowledge was supplied in this controlled condition. "
    "Do not use general model knowledge to name a mechanical cause. Explain "
    "that the observed data pattern alone cannot identify a specific cause "
    "and requires professional verification."
)
NO_ACTION_KNOWLEDGE = (
    "No retrieved action guidance was supplied in this controlled condition. "
    "Do not invent a component test or repair procedure. Give risk-appropriate "
    "owner observations and ask the mechanic to investigate the reported "
    "signal pattern generally."
)


def _condition_contexts(model: ModelLayerOutput) -> dict[str, dict[str, Any]]:
    rag = build_context_with_rag(model)
    baseline = {
        "context": rag["context"],
        "certainty_guidance": rag["certainty_guidance"],
        "notes": rag["notes"],
        "fault_knowledge": NO_FAULT_KNOWLEDGE,
        "actions_knowledge": NO_ACTION_KNOWLEDGE,
    }
    return {"A": baseline, "B": rag}


def generate(model_batch: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    outputs = {"A": [], "B": []}
    original_builder = report_generator.build_context_with_rag
    try:
        for component, payload in _best_component_payloads(
            model_batch
        ).items():
            model = ModelLayerOutput(**payload)
            history = _component_risk_history(model_batch, component)
            for label, context in _condition_contexts(model).items():
                report_generator.build_context_with_rag = (
                    lambda _model, selected=context: selected
                )
                report = report_generator.generate_report(
                    payload, risk_history=history
                )
                if not report.get("anomaly_description"):
                    raise RuntimeError(
                        f"Condition {label} produced a fallback for {component}"
                    )
                outputs[label].append(report)
    finally:
        report_generator.build_context_with_rag = original_builder
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_output", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    model_batch = json.loads(args.model_output.read_text())
    outputs = generate(model_batch)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for label, reports in outputs.items():
        (args.output_dir / f"dashboard-report-{label.lower()}.json").write_text(
            json.dumps(reports, indent=2, ensure_ascii=False) + "\n"
        )
    (args.output_dir / "administrator-condition-key.json").write_text(
        json.dumps(
            {
                "A": "controlled_no_rag",
                "B": "owner_safe_rag",
                "controlled_variables": [
                    "five-trip Data Layer output",
                    "Model Layer output and risk history",
                    "granite4.1:8b",
                    "temperature=0",
                    "prompt templates",
                    "certainty guidance",
                    "validator and one-correction release gate",
                    "Dashboard layout",
                ],
            },
            indent=2,
        ) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
