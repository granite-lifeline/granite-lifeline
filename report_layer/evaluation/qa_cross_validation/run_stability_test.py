"""
Sampling stability check: does temperature=0 actually give us the
determinism the cross-validation and perturbation results implicitly
assume?

call_ollama() (report_layer/pipeline/report_generator.py) sets
"temperature": 0, i.e. greedy decoding — but temperature=0 does not
guarantee bit-identical output run to run on real inference servers:
floating-point non-associativity under GPU/batched execution can
still introduce tiny numerical differences that cascade into
different token choices. Every comparison in
qa_cross_validation/cross_validation_results.md and
perturbation_regression/*.md implicitly assumes that a single
generated report is representative of "what generate_report() would
produce for this input" — this test checks whether that assumption
actually holds, using the exact same real fixture already used
elsewhere (cooling_degradation, Low), rather than asserting it.

Run: python3 report_layer/evaluation/qa_cross_validation/run_stability_test.py
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

FIXTURE_PATH = (
    PROJECT_ROOT / "report_layer" / "evaluation" / "prompt_refinement"
    / "fault_injection_candidates" / "selected_window_model_outputs"
    / "cooling_degradation__trip_0040_seg_001__w003.json"
)
NUM_RUNS = 5


def run() -> None:
    model_output = json.loads(FIXTURE_PATH.read_text())
    anomaly_type = model_output["anomaly_type"]
    risk_level = model_output["risk_level"]
    validated = ModelLayerOutput(**model_output)
    context = build_context(validated)

    runs = []
    for i in range(1, NUM_RUNS + 1):
        print(f"Run {i}/{NUM_RUNS}...")
        t0 = time.time()
        report = generate_report(model_output)
        elapsed = time.time() - t0

        validator_results = validate_chain(
            report["anomaly_description"],
            report["possible_cause"],
            report["recommended_action"],
            risk_level,
        )
        evaluator_score = evaluate_report(
            report, context, anomaly_type, risk_level
        )
        runs.append({
            "run": i,
            "elapsed_seconds": round(elapsed, 1),
            "anomaly_description": report["anomaly_description"],
            "possible_cause": report["possible_cause"],
            "recommended_action": report["recommended_action"],
            "validator_warnings": [
                w for r in validator_results for w in r.warnings
            ],
            "evaluator_overall": evaluator_score.overall_score,
            "evaluator_dims": {
                "factual_grounding": evaluator_score.factual_grounding,
                "readability": evaluator_score.readability,
                "hedging_appropriateness":
                    evaluator_score.hedging_appropriateness,
                "actionability": evaluator_score.actionability,
            },
        })
        print(
            f"  overall={evaluator_score.overall_score:.2f} "
            f"validator_warnings={len(runs[-1]['validator_warnings'])} "
            f"desc_len={len(report['anomaly_description'])}"
        )

    write_outputs(runs)


def write_outputs(runs) -> None:
    out_dir = Path(__file__).resolve().parent
    (out_dir / "stability_test_raw.json").write_text(
        json.dumps(runs, indent=2, ensure_ascii=False)
    )

    unique_descriptions = {r["anomaly_description"] for r in runs}
    unique_causes = {r["possible_cause"] for r in runs}
    unique_actions = {
        tuple(r["recommended_action"]) for r in runs
    }
    unique_overall_scores = {r["evaluator_overall"] for r in runs}
    unique_warning_counts = {len(r["validator_warnings"]) for r in runs}

    with open(out_dir / "stability_test_results.md", "w") as f:
        f.write("# Sampling Stability Test\n\n")
        f.write(
            f"{NUM_RUNS} identical calls to `generate_report()` on the "
            "same real fixture (cooling_degradation, Low — "
            "`selected_window_model_outputs/"
            "cooling_degradation__trip_0040_seg_001__w003.json`), same "
            "prompt, same `temperature: 0` setting already used in "
            "production. Checks whether every prior cross-validation "
            "and perturbation-test comparison's implicit assumption — "
            "that a single generated report represents \"what "
            "generate_report() produces for this input\" — actually "
            "holds.\n\n"
        )
        f.write("## Results\n\n")
        f.write(
            "| Run | Time (s) | Description length | Evaluator overall | "
            "Validator warnings |\n"
        )
        f.write("|---|---|---|---|---|\n")
        for r in runs:
            f.write(
                f"| {r['run']} | {r['elapsed_seconds']} | "
                f"{len(r['anomaly_description'])} | "
                f"{r['evaluator_overall']:.2f} | "
                f"{len(r['validator_warnings'])} |\n"
            )

        f.write("\n## Stability summary\n\n")
        f.write(
            f"- Unique anomaly_description texts across {NUM_RUNS} runs: "
            f"**{len(unique_descriptions)}**\n"
        )
        f.write(
            f"- Unique possible_cause texts: **{len(unique_causes)}**\n"
        )
        f.write(
            f"- Unique recommended_action lists: **{len(unique_actions)}**\n"
        )
        f.write(
            f"- Unique evaluator overall scores: "
            f"**{len(unique_overall_scores)}** "
            f"({sorted(unique_overall_scores)})\n"
        )
        f.write(
            f"- Unique validator warning counts: "
            f"**{len(unique_warning_counts)}** "
            f"({sorted(unique_warning_counts)})\n\n"
        )

        if len(unique_descriptions) == 1 and len(unique_causes) == 1:
            f.write(
                "**temperature=0 produced byte-identical text across all "
                f"{NUM_RUNS} runs.** The single-sample comparisons in "
                "qa_cross_validation and perturbation_regression are "
                "representative, not one lucky draw out of a "
                "distribution.\n"
            )
        else:
            f.write(
                "**Output was NOT byte-identical across runs despite "
                "temperature=0.** This means the single-sample "
                "comparisons elsewhere in qa_cross_validation and "
                "perturbation_regression are each one draw from a "
                "distribution, not a deterministic fixed point — see "
                "the per-run text below for how much it varied, and "
                "whether the variation changed any QA conclusions "
                "(e.g. evaluator score, validator warnings).\n"
            )

        f.write("\n## Per-run text\n\n")
        for r in runs:
            f.write(f"### Run {r['run']}\n\n")
            f.write(f"- anomaly_description: {r['anomaly_description']}\n\n")
            f.write(f"- possible_cause: {r['possible_cause']}\n\n")
            f.write("- recommended_action:\n")
            for action in r["recommended_action"]:
                f.write(f"  - {action}\n")
            f.write(
                f"\n- evaluator: overall={r['evaluator_overall']:.2f}, "
                + ", ".join(
                    f"{k}={v:.2f}" for k, v in r["evaluator_dims"].items()
                )
                + "\n"
            )
            f.write(
                "- validator warnings: "
                f"{r['validator_warnings'] or '(none)'}\n\n"
            )

    print(f"\nWritten: {out_dir / 'stability_test_results.md'}")


if __name__ == "__main__":
    run()
