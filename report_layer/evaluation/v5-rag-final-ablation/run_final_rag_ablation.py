#!/usr/bin/env python3
"""Run a controlled final-pipeline RAG ablation across five anomaly types.

All conditions use the production report generator, final prompt templates,
certainty guidance, temperature, validator and correction loop. The only
change is the knowledge supplied to the prompt.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from report_layer.evaluation.report_quality_evaluator import (  # noqa: E402
    evaluate_report,
)
from report_layer.negation_constants import (  # noqa: E402
    find_unnegated_phrases,
)
from report_layer.pipeline import report_generator  # noqa: E402
from report_layer.pipeline.context_injection import (  # noqa: E402
    build_context_with_rag,
)
from report_layer.pipeline.prompt_chain_validator import (  # noqa: E402
    validate_chain,
)
from shared.interface_models import ModelLayerOutput  # noqa: E402


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

NO_FAULT_KNOWLEDGE = (
    "No retrieved fault knowledge was supplied in this controlled condition."
)
NO_ACTION_KNOWLEDGE = (
    "No retrieved action guidance was supplied in this controlled condition."
)

OWNER_SAFE_PREFIX = """Audience-safety transformation:
The source material below contains workshop procedures. Do not direct the
vehicle owner to dismantle, disconnect, remove, replace or bench-test a
component, use specialist tools, compressed air or a water bath, or work near
a hot or running engine. Convert every such procedure into a request for a
qualified mechanic. The owner may only monitor dashboard readings and warning
lights, stop driving safely when warning signs require it, book an inspection,
describe the evidence to a mechanic, look for visible leaks without touching
hot parts, and check a clearly marked fluid reservoir only when the engine is
cold. Keep owner actions and mechanic requests explicit.

Technical source actions:
"""

RAW_FIELDS = (
    "coolant_temp", "risk_score", "prediction_confidence", "maf", "map",
    "accel_pedal_d", "accel_pedal_e", "throttle_pos",
)
INVASIVE_PHRASES = (
    "remove", "disconnect", "replace", "water bath", "compressed air",
    "rotate by hand", "rotated by hand", "multimeter", "garden hose",
    "disassemble", "disassembly", "dismantle", "bench-test", "bench test",
)
MECHANIC_TERMS = ("mechanic", "technician", "garage", "service centre")


def _condition_contexts(model: ModelLayerOutput) -> Dict[str, Dict[str, Any]]:
    rag = build_context_with_rag(model)
    common = {
        "context": rag["context"],
        "certainty_guidance": rag["certainty_guidance"],
        "notes": rag["notes"],
    }
    return {
        "controlled_baseline": {
            **common,
            "fault_knowledge": NO_FAULT_KNOWLEDGE,
            "actions_knowledge": NO_ACTION_KNOWLEDGE,
        },
        "cause_rag": {
            **common,
            "fault_knowledge": rag["fault_knowledge"],
            "actions_knowledge": NO_ACTION_KNOWLEDGE,
        },
        "current_full_rag": dict(rag),
        "owner_safe_rag": {
            **common,
            "fault_knowledge": rag["fault_knowledge"],
            "actions_knowledge": OWNER_SAFE_PREFIX + rag["actions_knowledge"],
        },
    }


def _text(report: Dict[str, Any]) -> str:
    actions = report.get("recommended_action", [])
    if not isinstance(actions, list):
        actions = [str(actions)]
    return " ".join([
        str(report.get("anomaly_description", "")),
        str(report.get("possible_cause", "")),
        *[str(action) for action in actions],
    ])


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text))


def _automatic_audit(
    report: Dict[str, Any], context: Dict[str, Any], anomaly_type: str
) -> Dict[str, Any]:
    report_text = _text(report)
    source_text = " ".join([
        str(context["context"]),
        str(context["fault_knowledge"]),
        str(context["actions_knowledge"]),
    ])
    unsupported_numbers = sorted(_numbers(report_text) - _numbers(source_text))
    lower = report_text.lower()
    raw_fields = sorted({field for field in RAW_FIELDS if field in lower})

    actions = report.get("recommended_action", [])
    if not isinstance(actions, list):
        actions = [str(actions)]
    unsafe_owner_actions = []
    delegated_actions = []
    for action in actions:
        action_lower = str(action).lower()
        is_invasive = bool(
            find_unnegated_phrases(action_lower, list(INVASIVE_PHRASES))
        )
        is_delegated = any(term in action_lower for term in MECHANIC_TERMS)
        if is_invasive and not is_delegated:
            unsafe_owner_actions.append(str(action))
        if is_delegated:
            delegated_actions.append(str(action))

    contradiction_terms = (
        "despite", "although", "inconsistent", "conflict", "does not align",
        "does not match", "even though", "however",
    )
    contradiction_acknowledged = None
    if anomaly_type == "cooling_degradation" and "108" in source_text:
        contradiction_acknowledged = any(
            term in lower for term in contradiction_terms
        )

    return {
        "unsupported_numbers": unsupported_numbers,
        "raw_fields": raw_fields,
        "unsafe_owner_actions": unsafe_owner_actions,
        "technician_delegated_action_count": len(delegated_actions),
        "contradiction_acknowledged": contradiction_acknowledged,
        "section_shape_valid": (
            bool(report.get("anomaly_description"))
            and bool(report.get("possible_cause"))
            and isinstance(report.get("recommended_action"), list)
            and 2 <= len(report.get("recommended_action", [])) <= 4
        ),
    }


def _render_prompts(
    context: Dict[str, Any], report: Dict[str, Any]
) -> Dict[str, str]:
    templates = {
        i: report_generator.load_prompt_template(i) for i in (1, 2, 3)
    }
    shared = {
        "context": context["context"],
        "audience": report_generator.AUDIENCE,
        "fault_knowledge": context["fault_knowledge"],
        "actions_knowledge": context["actions_knowledge"],
        "certainty_guidance": context["certainty_guidance"],
        "anomaly_description": report.get("anomaly_description", ""),
        "possible_cause": report.get("possible_cause", ""),
    }
    return {
        f"layer{i}": report_generator.render_prompt(templates[i], shared)
        for i in (1, 2, 3)
    }


def run() -> None:
    rows = []
    original_builder = report_generator.build_context_with_rag
    try:
        for fixture_name in FIXTURES:
            fixture = json.loads((FIXTURE_DIR / fixture_name).read_text())
            model = ModelLayerOutput(**fixture)
            contexts = _condition_contexts(model)
            for condition, condition_context in contexts.items():
                print(f"RUN {model.anomaly_type} / {condition}", flush=True)
                report_generator.build_context_with_rag = (
                    lambda _model, c=condition_context: c
                )
                started = time.time()
                report = report_generator.generate_report(fixture)
                elapsed = round(time.time() - started, 2)

                fallback = not bool(report.get("anomaly_description"))
                if fallback:
                    evaluator = None
                    validator = []
                else:
                    evaluator = evaluate_report(
                        report,
                        condition_context["context"],
                        model.anomaly_type,
                        model.risk_level or "Low",
                    )
                    validator = validate_chain(
                        report["anomaly_description"],
                        report["possible_cause"],
                        report["recommended_action"],
                        model.risk_level or "Low",
                    )

                row = {
                    "fixture": fixture_name,
                    "anomaly_type": model.anomaly_type,
                    "risk_level": model.risk_level,
                    "prediction_confidence": model.prediction_confidence,
                    "condition": condition,
                    "elapsed_seconds": elapsed,
                    "fallback": fallback,
                    "context": condition_context,
                    "report": report,
                    "prompts": _render_prompts(condition_context, report),
                    "quality_scores": None if evaluator is None else {
                        "factual_grounding": evaluator.factual_grounding,
                        "readability": evaluator.readability,
                        "hedging_appropriateness": (
                            evaluator.hedging_appropriateness
                        ),
                        "actionability": evaluator.actionability,
                        "overall": evaluator.overall_score,
                    },
                    "validator": [
                        {
                            "layer": item.layer,
                            "passed": item.passed,
                            "score": item.score,
                            "warnings": item.warnings,
                        }
                        for item in validator
                    ],
                    "audit": _automatic_audit(
                        report, condition_context, model.anomaly_type
                    ),
                }
                rows.append(row)
                print(
                    f"DONE {model.anomaly_type} / {condition}: "
                    f"fallback={fallback}, elapsed={elapsed}s",
                    flush=True,
                )
    finally:
        report_generator.build_context_with_rag = original_builder

    raw_path = OUTPUT_DIR / "final_rag_ablation_raw.json"
    raw_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    _write_summary(rows)
    print(f"WROTE {raw_path}", flush=True)


def _write_summary(rows: list[Dict[str, Any]]) -> None:
    conditions = [
        "controlled_baseline", "cause_rag", "current_full_rag",
        "owner_safe_rag",
    ]
    lines = [
        "# Final-pipeline RAG ablation results",
        "",
        "All conditions use the final production prompts, identical certainty "
        "guidance, temperature, validator and correction loop.",
        "",
        "> The legacy quality score and heuristic counts below are screening "
        "outputs. Manual review is required for relevance, mechanical "
        "accuracy and action safety.",
        "",
        "| Condition | Reports | Fallbacks | Mean legacy quality | "
        "Unsupported numbers | Unsafe owner actions | Raw fields |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in conditions:
        subset = [row for row in rows if row["condition"] == condition]
        scores = [
            row["quality_scores"]["overall"] for row in subset
            if row["quality_scores"] is not None
        ]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        lines.append(
            f"| {condition} | {len(subset)} | "
            f"{sum(row['fallback'] for row in subset)} | {mean_score:.3f} | "
            f"{sum(len(row['audit']['unsupported_numbers']) for row in subset)} | "  # noqa: E501
            f"{sum(len(row['audit']['unsafe_owner_actions']) for row in subset)} | "  # noqa: E501
            f"{sum(len(row['audit']['raw_fields']) for row in subset)} |"
        )

    lines.extend(["", "## Per-report results", ""])
    lines.append(
        "| Anomaly | Risk | Condition | Overall | Validator warnings | "
        "Unsupported numbers | Unsafe actions |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for row in rows:
        score = row["quality_scores"]
        overall = "—" if score is None else f"{score['overall']:.2f}"
        warning_count = sum(
            len(layer["warnings"]) for layer in row["validator"]
        )
        lines.append(
            f"| {row['anomaly_type']} | {row['risk_level']} | "
            f"{row['condition']} | {overall} | {warning_count} | "
            f"{len(row['audit']['unsupported_numbers'])} | "
            f"{len(row['audit']['unsafe_owner_actions'])} |"
        )

    (OUTPUT_DIR / "final_rag_ablation_results.md").write_text(
        "\n".join(lines) + "\n"
    )


if __name__ == "__main__":
    run()
