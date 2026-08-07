"""
Perturbation regression test for report_quality_evaluator.py.

Methodology adapted from Anghel et al.'s mirrored-comparison approach
for diagnosing LLM-judge position bias: instead of comparing the same
content in two positions, this generates lexical-noise, negation-
rephrase, and punctuation/formatting variants of the same three real
RAG-generated reports (report_layer/evaluation/v3-rag-baseline-comparison/
scenario_comparison_rag.md) and checks whether
report_quality_evaluator.evaluate_report() scores them consistently.
The point is not to prove the evaluator is perfect — it is a small,
keyword-based heuristic by design — but to measure, with a number,
how much of a wording change it takes to flip a score, and specifically
whether the negation-aware fix in evaluate_hedging_appropriateness()
(see report_quality_evaluator.py NEGATION_WORDS /
_find_unnegated_phrases) actually holds up under paraphrase.

Run: python3 report_layer/evaluation/perturbation_regression/run_perturbation_test.py
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from report_layer.evaluation.report_quality_evaluator import (  # noqa: E402
    evaluate_report,
)
from report_layer.pipeline.context_injection import build_context  # noqa: E402
from shared.interface_models import ModelLayerOutput  # noqa: E402


SCENARIOS_DIR = PROJECT_ROOT / "report_layer" / "evaluation" / "test_scenarios"

# Real RAG-generated report text, transcribed from
# report_layer/evaluation/v3-rag-baseline-comparison/scenario_comparison_rag.md,
# with markdown bold markers stripped for plain-text scoring.
REAL_REPORTS = {
    "typical_cooling_stress": {
        "anomaly_description": (
            "Your engine's coolant temperature is running higher than "
            "the safe operating range. The sensor reading shows 102°C, "
            "while the normal range for optimal cooling is 90-95°C. "
            "This elevated temperature is marked as ABNORMAL in the "
            "system data, indicating that the cooling system may not "
            "be functioning properly to remove heat efficiently. "
            "Because the risk level is classified as High, this "
            "situation suggests that prompt attention is advisable, "
            "especially if you continue driving under load or notice "
            "any warning lights related to overheating."
        ),
        "possible_cause": (
            "The elevated coolant temperature of 102°C, above the "
            "normal safe range of 90-95°C, may indicate that the "
            "cooling system is not effectively removing heat from the "
            "engine. Several factors could contribute to this "
            "condition: a thermostat stuck closed, a clogged radiator "
            "or cooling tube, damaged fins or contaminated coolant, "
            "insufficient coolant level, or a cooling fan malfunction."
        ),
        "recommended_action": [
            "Check the thermostat: locate it near the radiator and "
            "verify it opens at around 82°C. If it stays closed, "
            "replace it to allow coolant flow.",
            "Inspect the radiator for blockages or damage soon, and "
            "clean or clear any obstruction you find.",
            "Verify coolant level and quality, and add fresh "
            "antifreeze of the correct type if the level is low.",
            "Test the cooling fan operation with the engine warm, "
            "and have a mechanic check the fan motor promptly if it "
            "does not start.",
        ],
    },
    "atypical_cooling_stress": {
        "anomaly_description": (
            "The diagnostic system has detected a potential cooling "
            "degradation issue with your vehicle. The coolant "
            "temperature is currently at 93.0°C, which falls within "
            "the normal operating range of 90.0-95.0°C, so no "
            "immediate abnormality is observed in this specific "
            "signal. However, the overall risk level for cooling "
            "degradation is rated as Medium (55% risk score), "
            "suggesting that while there isn't a critical problem "
            "right now, it may develop into one if not monitored."
        ),
        "possible_cause": (
            "The medium-risk cooling degradation (55% score) could "
            "suggest several potential issues related to the "
            "vehicle's cooling system, despite the current coolant "
            "temperature being within normal limits. Possible causes "
            "may include a thermostat that is partially stuck, a "
            "water pump that is beginning to fail, or a partially "
            "clogged radiator cooling tube."
        ),
        "recommended_action": [
            "Inspect and clean the radiator soon, checking for dirt, "
            "leaves, or debris on the fins.",
            "Check coolant levels and quality, topping off with the "
            "correct antifreeze mixture if low.",
            "Inspect the thermostat operation after the engine has "
            "cooled, and replace it if it fails to open at around "
            "82°C.",
            "Examine the drive belt and water pump for wear or "
            "unusual noise, and schedule a mechanic visit within the "
            "next week if anything looks suspect.",
        ],
    },
    "contradictory_cooling_stress": {
        "anomaly_description": (
            "Your engine's coolant temperature is running higher "
            "than the safe operating range. The current reading "
            "shows a coolant temperature of 108.0°C, which exceeds "
            "the normal reference range of 90.0-95.0°C. This "
            "elevated temperature has been flagged as an abnormal "
            "condition in the diagnostic data. Given that the risk "
            "level for this cooling degradation issue is categorized "
            "as Low, it suggests that while there is some concern, "
            "the problem does not appear to be urgent at this moment."
        ),
        "possible_cause": (
            "The elevated coolant temperature (108.0°C) may indicate "
            "a thermostat stuck closed, cooling fan malfunction, "
            "partial radiator clog, insufficient or contaminated "
            "coolant, or a worn drive belt affecting water pump "
            "operation. These factors could restrict coolant flow or "
            "reduce heat dissipation, leading to higher engine "
            "temperatures despite the low overall risk level."
        ),
        "recommended_action": [
            "Check the engine coolant level when the engine is cool, "
            "and ensure the coolant is between the MIN and MAX marks.",
            "Inspect the thermostat operation after driving, and "
            "check whether the cooling fan turns on at higher "
            "temperatures.",
            "Look for signs of a clogged radiator or damaged fins, "
            "and gently clean them if possible.",
            "Monitor the coolant temperature gauge during typical "
            "driving conditions, and note any further increases "
            "above 95°C.",
        ],
    },
}

SYNONYMS = {
    "elevated": "high",
    "indicate": "suggest",
    "indicating": "suggesting",
    "malfunction": "failure",
    "inspect": "check",
    "advisable": "recommended",
    "prompt attention": "quick attention",
    "abnormal": "outside the normal range",
    "condition": "situation",
    "sufficient": "adequate",
}


def apply_synonym_variant(text: str) -> str:
    for old, new in SYNONYMS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text, flags=re.IGNORECASE)
    return text


def apply_punctuation_variant(text: str) -> str:
    text = text.replace("90-95", "90 to 95")
    text = text.replace("°C", " degrees Celsius")
    text = text.replace("cannot", "can't")
    text = text.replace("does not", "doesn't")
    text = text.replace("is not", "isn't")
    return text


NEGATION_REPHRASE = {
    "typical_cooling_stress": (
        "possible_cause",
        (
            "The elevated coolant temperature of 102°C, above the "
            "normal safe range of 90-95°C, may indicate that the "
            "cooling system is not effectively removing heat from the "
            "engine."
        ),
        (
            "No specific fault has been confirmed yet, but the "
            "elevated coolant temperature of 102°C, above the "
            "normal safe range of 90-95°C, is consistent with the "
            "cooling system not effectively removing heat from the "
            "engine."
        ),
    ),
    "atypical_cooling_stress": (
        "anomaly_description",
        (
            "However, the overall risk level for cooling degradation "
            "is rated as Medium (55% risk score), suggesting that "
            "while there isn't a critical problem right now, it may "
            "develop into one if not monitored."
        ),
        (
            "However, no critical problem is confirmed right now: the "
            "overall risk level for cooling degradation is rated as "
            "Medium (55% risk score), and this unconfirmed pattern "
            "may develop into one if not monitored."
        ),
    ),
    "contradictory_cooling_stress": (
        "anomaly_description",
        (
            "Given that the risk level for this cooling degradation "
            "issue is categorized as Low, it suggests that while "
            "there is some concern, the problem does not appear to be "
            "urgent at this moment."
        ),
        (
            "The risk level for this cooling degradation issue is "
            "categorized as Low, so no urgent problem is confirmed at "
            "this moment, even though there is some concern."
        ),
    ),
}


def apply_negation_variant(scenario_name: str, report: dict) -> dict:
    field, old_sentence, new_sentence = NEGATION_REPHRASE[scenario_name]
    variant = dict(report)
    if old_sentence not in variant[field]:
        raise ValueError(
            f"Expected sentence not found in {scenario_name}.{field} — "
            "REAL_REPORTS text may have drifted from the source markdown."
        )
    variant[field] = variant[field].replace(old_sentence, new_sentence)
    return variant


def apply_text_variant(report: dict, fn) -> dict:
    return {
        "anomaly_description": fn(report["anomaly_description"]),
        "possible_cause": fn(report["possible_cause"]),
        "recommended_action": [fn(a) for a in report["recommended_action"]],
    }


def load_context(scenario_name: str) -> str:
    data = json.loads((SCENARIOS_DIR / f"{scenario_name}.json").read_text())
    data.setdefault("notes", [])
    data.setdefault("estimated_cycles_to_failure", None)
    data.setdefault("estimated_failure_probability", None)
    model_output = ModelLayerOutput(**data)
    return build_context(model_output)


def run() -> None:
    rows = []
    for scenario_name, report in REAL_REPORTS.items():
        risk_level = {
            "typical_cooling_stress": "High",
            "atypical_cooling_stress": "Medium",
            "contradictory_cooling_stress": "Low",
        }[scenario_name]
        context = load_context(scenario_name)

        variants = {
            "original": report,
            "synonym": apply_text_variant(report, apply_synonym_variant),
            "punctuation": apply_text_variant(
                report, apply_punctuation_variant
            ),
            "negation_rephrase": apply_negation_variant(
                scenario_name, report
            ),
        }

        scenario_scores = {}
        for variant_name, variant_report in variants.items():
            score = evaluate_report(
                variant_report, context, "cooling_degradation", risk_level
            )
            scenario_scores[variant_name] = score
            print(
                f"{scenario_name:<28} {variant_name:<18} "
                f"overall={score.overall_score:.2f} "
                f"grounding={score.factual_grounding:.2f} "
                f"readability={score.readability:.2f} "
                f"hedging={score.hedging_appropriateness:.2f} "
                f"actionability={score.actionability:.2f}"
            )

        rows.append((scenario_name, scenario_scores))

    write_markdown(rows)


def write_markdown(rows) -> None:
    output_path = (
        Path(__file__).resolve().parent / "perturbation_results.md"
    )
    dims = [
        "factual_grounding", "readability",
        "hedging_appropriateness", "actionability", "overall_score",
    ]
    total_checks = 0
    stable_checks = 0

    with open(output_path, "w") as f:
        f.write("# Perturbation Regression Results\n\n")
        f.write(
            "Consistency of report_quality_evaluator.py's four "
            "dimension scores across synonym, punctuation, and "
            "negation-rephrase variants of the same three real "
            "RAG-generated reports (scenario_comparison_rag.md). "
            "Run after the negation-aware fix to "
            "evaluate_hedging_appropriateness().\n\n"
        )
        for scenario_name, scores in rows:
            f.write(f"## {scenario_name}\n\n")
            separator = "|" + "|".join(["---"] * (len(dims) + 1)) + "|\n"
            f.write("| Variant | " + " | ".join(dims) + " |\n")
            f.write(separator)
            original = scores["original"]
            for variant_name, score in scores.items():
                f.write(f"| {variant_name} | " + " | ".join(
                    f"{getattr(score, d):.2f}" for d in dims
                ) + " |\n")
                if variant_name != "original":
                    for d in dims:
                        total_checks += 1
                        if getattr(score, d) == getattr(original, d):
                            stable_checks += 1
            f.write("\n")

        consistency = 100 * stable_checks / total_checks
        f.write("## Summary\n\n")
        f.write(
            f"Consistency rate across all scenario x variant x "
            f"dimension checks: **{stable_checks}/{total_checks} "
            f"({consistency:.1f}%)**.\n\n"
        )
        f.write(
            "The negation_rephrase variants specifically exercise the "
            "negation-aware fix in evaluate_hedging_appropriateness(): "
            "each one rewrites a hedged sentence to explicitly use "
            "negated wording ('no ... confirmed', 'unconfirmed') "
            "instead of 'may indicate' style hedging, while preserving "
            "the same claim. Before the fix, these would have been "
            "penalised by the bare 'confirmed' substring match; after "
            "the fix, hedging_appropriateness should be unaffected by "
            "this rewrite.\n"
        )
    print(f"\nConsistency: {stable_checks}/{total_checks} ({consistency:.1f}%)")
    print(f"Markdown report written to: {output_path}")


if __name__ == "__main__":
    run()
