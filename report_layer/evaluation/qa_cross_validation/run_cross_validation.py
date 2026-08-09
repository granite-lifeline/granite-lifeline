"""
Cross-validate prompt_chain_validator and report_quality_evaluator
against real generated reports, across all 5 current anomaly types.

Both QA mechanisms have so far only been checked in isolation:
prompt_chain_validator with hand-written strings in its own tests,
report_quality_evaluator against 3 hand-written cooling_degradation
scenarios. Neither has been run against the SAME real, LLM-generated
report, and neither has been run outside cooling_degradation.

This script runs the full RAG pipeline (generate_report(), which now
calls prompt_chain_validator.validate_chain() internally) on the 5
real per-type fixtures already in the repo
(report_layer/evaluation/prompt_refinement/fault_injection_candidates/
selected_window_model_outputs/), then separately scores the same
generated report with report_quality_evaluator.evaluate_report(), and
reports where the two mechanisms agree or disagree.

Requires local Ollama running with granite4.1:8b.
Run:
python3 report_layer/evaluation/qa_cross_validation/run_cross_validation.py
"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from report_layer.evaluation.report_quality_evaluator import (  # noqa: E402
    evaluate_report,
)
from report_layer.pipeline.context_injection import build_context  # noqa: E402
from report_layer.pipeline.prompt_chain_validator import (  # noqa: E402
    validate_chain,
)
from report_layer.pipeline.report_generator import (  # noqa: E402
    generate_report,
)
from shared.interface_models import ModelLayerOutput  # noqa: E402

FIXTURES_DIR = (
    PROJECT_ROOT / "report_layer" / "evaluation" / "prompt_refinement"
    / "fault_injection_candidates" / "selected_window_model_outputs"
)

FIXTURES = [
    "cooling_degradation__trip_0040_seg_001__w003.json",
    "air_intake_maf_anomaly__trip_0061_seg_001__w002.json",
    "accelerator_pedal_sensor__trip_0041_seg_001__w002.json",
    "intake_air_temperature_sensor_fault__trip_0001_seg_001__w001.json",
    "map_load_signal_plausibility_fault__trip_0001_seg_001__w001.json",
]


def run() -> None:
    results = []
    for fixture_name in FIXTURES:
        model_output = json.loads((FIXTURES_DIR / fixture_name).read_text())
        anomaly_type = model_output["anomaly_type"]
        risk_level = model_output["risk_level"]

        print(f"\n=== {fixture_name} ({anomaly_type}, {risk_level}) ===")
        t0 = time.time()
        report = generate_report(model_output)
        elapsed = time.time() - t0
        print(f"generate_report(): {elapsed:.1f}s")

        if not report["anomaly_description"]:
            print("FALLBACK REPORT (generation failed) — skipping scoring")
            results.append({
                "fixture": fixture_name,
                "anomaly_type": anomaly_type,
                "risk_level": risk_level,
                "generation_failed": True,
            })
            continue

        validated = ModelLayerOutput(**model_output)
        context = build_context(validated)

        validator_results = validate_chain(
            report["anomaly_description"],
            report["possible_cause"],
            report["recommended_action"],
            risk_level,
        )
        evaluator_score = evaluate_report(
            report, context, anomaly_type, risk_level
        )

        validator_all_passed = all(r.passed for r in validator_results)
        validator_any_warnings = any(r.warnings for r in validator_results)

        print(
            f"validator: all_passed={validator_all_passed} "
            f"warnings={sum(len(r.warnings) for r in validator_results)}"
        )
        for r in validator_results:
            for w in r.warnings:
                print(f"  [layer {r.layer}] {w}")
        print(
            f"evaluator: overall={evaluator_score.overall_score:.2f} "
            f"grounding={evaluator_score.factual_grounding:.2f} "
            f"readability={evaluator_score.readability:.2f} "
            f"hedging={evaluator_score.hedging_appropriateness:.2f} "
            f"actionability={evaluator_score.actionability:.2f}"
        )

        results.append({
            "fixture": fixture_name,
            "anomaly_type": anomaly_type,
            "risk_level": risk_level,
            "generation_failed": False,
            "generation_seconds": round(elapsed, 1),
            "report": report,
            "validator_all_passed": validator_all_passed,
            "validator_any_warnings": validator_any_warnings,
            "validator_warnings": [
                w for r in validator_results for w in r.warnings
            ],
            "validator_scores": {
                r.layer: r.score for r in validator_results
            },
            "evaluator_overall": evaluator_score.overall_score,
            "evaluator_dims": {
                "factual_grounding": evaluator_score.factual_grounding,
                "readability": evaluator_score.readability,
                "hedging_appropriateness":
                    evaluator_score.hedging_appropriateness,
                "actionability": evaluator_score.actionability,
            },
        })

    write_outputs(results)


def write_outputs(results) -> None:
    out_dir = Path(__file__).resolve().parent
    (out_dir / "cross_validation_raw.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )

    with open(out_dir / "cross_validation_results.md", "w") as f:
        f.write("# QA Cross-Validation: All 5 Anomaly Types\n\n")
        f.write(
            "prompt_chain_validator.validate_chain() and "
            "report_quality_evaluator.evaluate_report() run against "
            "the SAME real, LLM-generated report, for each of the 5 "
            "current anomaly types, using the real per-type fixtures "
            "in report_layer/evaluation/prompt_refinement/"
            "fault_injection_candidates/selected_window_model_outputs/. "
            "Neither QA mechanism had previously been run outside "
            "cooling_degradation, and they had never been run against "
            "the same report before.\n\n"
        )
        f.write(
            "| Anomaly type | Risk | Validator all-passed | "
            "Validator warnings | Evaluator overall | Agreement |\n"
        )
        f.write("|---|---|---|---|---|---|\n")
        for r in results:
            if r.get("generation_failed"):
                f.write(
                    f"| {r['anomaly_type']} | {r['risk_level']} | "
                    f"— | GENERATION FAILED | — | — |\n"
                )
                continue
            low_evaluator = r["evaluator_overall"] < 0.9
            validator_flagged = not r["validator_all_passed"]
            if validator_flagged and low_evaluator:
                agreement = "both flag"
            elif not validator_flagged and not low_evaluator:
                agreement = "both clean"
            else:
                agreement = "DISAGREE"
            f.write(
                f"| {r['anomaly_type']} | {r['risk_level']} | "
                f"{r['validator_all_passed']} | "
                f"{len(r['validator_warnings'])} | "
                f"{r['evaluator_overall']:.2f} | {agreement} |\n"
            )

        f.write("\n## Details\n\n")
        for r in results:
            f.write(f"### {r['anomaly_type']} ({r['risk_level']})\n\n")
            if r.get("generation_failed"):
                f.write("Generation failed — fell back to empty report.\n\n")
                continue
            f.write(f"Generation time: {r['generation_seconds']}s\n\n")
            f.write("**Validator warnings:**\n\n")
            if r["validator_warnings"]:
                for w in r["validator_warnings"]:
                    f.write(f"- {w}\n")
            else:
                f.write("(none)\n")
            f.write(
                f"\n**Evaluator scores:** overall="
                f"{r['evaluator_overall']:.2f}, "
                + ", ".join(
                    f"{k}={v:.2f}" for k, v in r["evaluator_dims"].items()
                )
                + "\n\n"
            )
            f.write("**Generated report:**\n\n")
            f.write(
                "- anomaly_description: "
                f"{r['report']['anomaly_description']}\n\n"
            )
            f.write(f"- possible_cause: {r['report']['possible_cause']}\n\n")
            f.write("- recommended_action:\n")
            for action in r["report"]["recommended_action"]:
                f.write(f"  - {action}\n")
            f.write("\n")

    print(f"\nWritten: {out_dir / 'cross_validation_results.md'}")
    print(f"Written: {out_dir / 'cross_validation_raw.json'}")


if __name__ == "__main__":
    run()
