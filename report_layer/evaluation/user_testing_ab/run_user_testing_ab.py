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

from dashboard.data_loader import (  # noqa: E402
    _best_component_payloads,
    _component_risk_history,
)
from report_layer.pipeline import report_generator  # noqa: E402
from report_layer.pipeline.context_injection import (  # noqa: E402
    build_context_with_rag,
)
from report_layer.rag.rag_retriever import (  # noqa: E402
    FALLBACK_ACTIONS,
    FALLBACK_DESCRIPTION,
)
from shared.interface_models import ModelLayerOutput  # noqa: E402


def _condition_contexts(model: ModelLayerOutput) -> dict[str, dict[str, Any]]:
    """Build the two conditions from one shared context.

    The only variable that changes between conditions is whether the
    prompt receives real retrieved knowledge. Condition A's
    fault_knowledge/actions_knowledge are FALLBACK_DESCRIPTION and
    FALLBACK_ACTIONS from report_layer/rag/rag_retriever.py — the exact
    strings the production pipeline itself injects when ChromaDB
    retrieval genuinely finds nothing, not custom-authored guardrail
    text. The prompt templates, rules, and every other input are
    byte-identical between A and B; this keeps the comparison a
    single-variable ablation (presence vs. absence of retrieved
    knowledge) rather than also varying prompt constraints.
    """
    rag = build_context_with_rag(model)
    baseline = {
        "context": rag["context"],
        "certainty_guidance": rag["certainty_guidance"],
        "notes": rag["notes"],
        "fault_knowledge": FALLBACK_DESCRIPTION,
        "actions_knowledge": FALLBACK_ACTIONS,
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
                    message = (
                        f"Condition {label} produced a fallback "
                        f"for {component}"
                    )
                    raise RuntimeError(
                        message
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
        filename = f"dashboard-report-{label.lower()}.json"
        output_path = args.output_dir / filename
        output_path.write_text(
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
