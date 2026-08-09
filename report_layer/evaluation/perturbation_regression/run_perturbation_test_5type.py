"""
Perturbation regression test, extended to all 5 current anomaly types.

run_perturbation_test.py covered only cooling_degradation (3 hand-
written scenarios). This extends the same methodology (synonym,
punctuation, and negation-rephrase variants, scored with
report_quality_evaluator.evaluate_report()) to real generated reports
for all 5 anomaly types, reusing the reports already produced by
report_layer/evaluation/qa_cross_validation/run_cross_validation.py —
no new Ollama calls needed, since the text and its real context are
already saved in cross_validation_raw.json.

Run:
python3 report_layer/evaluation/perturbation_regression/\
    run_perturbation_test_5type.py
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

FIXTURES_DIR = (
    PROJECT_ROOT / "report_layer" / "evaluation" / "prompt_refinement"
    / "fault_injection_candidates" / "selected_window_model_outputs"
)
CROSS_VALIDATION_RAW = (
    PROJECT_ROOT / "report_layer" / "evaluation" / "qa_cross_validation"
    / "cross_validation_raw.json"
)

SYNONYMS = {
    "elevated": "high",
    "indicate": "suggest",
    "indicating": "suggesting",
    "malfunction": "failure",
    "inspect": "check",
    "abnormal": "outside the normal range",
    "possible": "potential",
    "slight": "minor",
    "reading": "measurement",
}


def apply_synonym_variant(text: str) -> str:
    for old, new in SYNONYMS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text, flags=re.IGNORECASE)
    return text


def apply_punctuation_variant(text: str) -> str:
    text = text.replace("°C", " degrees Celsius")
    text = text.replace("g/s", " grams per second")
    text = text.replace("kPa", " kilopascals")
    text = text.replace("cannot", "can't")
    text = text.replace("does not", "doesn't")
    text = text.replace("is not", "isn't")
    return text


# (anomaly_type, field, sentence to replace, negation-rephrased replacement)
NEGATION_REPHRASE = {
    "cooling_degradation": (
        "possible_cause",
        (
            "The slightly lower-than-expected coolant temperature and "
            "unusually slow cooling rate may indicate a minor sensor "
            "reading issue or an early sign of reduced cooling fan "
            "effectiveness."
        ),
        (
            "No specific mechanical fault has been confirmed; the "
            "slightly lower-than-expected coolant temperature and "
            "unusually slow cooling rate are consistent with a minor "
            "sensor reading issue or an early sign of reduced cooling "
            "fan effectiveness."
        ),
    ),
    "air_intake_maf_anomaly": (
        "possible_cause",
        (
            "Because related readings are still normal, there is not "
            "enough evidence to identify a specific intake-system "
            "fault."
        ),
        (
            "No specific intake-system fault has been confirmed, "
            "since related readings are still normal."
        ),
    ),
    "accelerator_pedal_sensor": (
        "possible_cause",
        (
            "The slight variation between the two accelerator pedal "
            "sensor channels could be due to normal sensor tolerance, "
            "a minor wiring or connector issue, or early signs of "
            "sensor wear."
        ),
        (
            "No fault has been confirmed in the accelerator pedal "
            "sensor channels; the slight variation between them could "
            "be due to normal sensor tolerance, a minor wiring or "
            "connector issue, or early signs of sensor wear."
        ),
    ),
    "intake_air_temperature_sensor_fault": (
        "possible_cause",
        (
            "The high-risk flag for the intake air temperature sensor "
            "may indicate an intermittent sensor signal, a loose or "
            "corroded connector, or early sensor drift."
        ),
        (
            "No specific sensor fault has been confirmed yet, but the "
            "high-risk flag for the intake air temperature sensor is "
            "consistent with an intermittent sensor signal, a loose or "
            "corroded connector, or early sensor drift."
        ),
    ),
    "map_load_signal_plausibility_fault": (
        "possible_cause",
        (
            "The abnormal manifold pressure range reading suggests a "
            "potential issue with the intake manifold pressure (MAP) "
            "sensor."
        ),
        (
            "No specific MAP sensor issue has been confirmed, but the "
            "abnormal manifold pressure range reading is consistent "
            "with a potential issue with the intake manifold pressure "
            "(MAP) sensor."
        ),
    ),
}


def apply_negation_variant(anomaly_type: str, report: dict) -> dict:
    field, old_sentence, new_sentence = NEGATION_REPHRASE[anomaly_type]
    variant = dict(report)
    if old_sentence not in variant[field]:
        raise ValueError(
            f"Expected sentence not found in {anomaly_type}.{field} — "
            "cross_validation_raw.json text may have changed since "
            "this variant was written."
        )
    variant[field] = variant[field].replace(old_sentence, new_sentence)
    return variant


def apply_text_variant(report: dict, fn) -> dict:
    return {
        "anomaly_description": fn(report["anomaly_description"]),
        "possible_cause": fn(report["possible_cause"]),
        "recommended_action": [fn(a) for a in report["recommended_action"]],
    }


def run() -> None:
    cross_validation = json.loads(CROSS_VALIDATION_RAW.read_text())
    rows = []

    for entry in cross_validation:
        if entry.get("generation_failed"):
            continue
        anomaly_type = entry["anomaly_type"]
        risk_level = entry["risk_level"]
        report = entry["report"]

        fixture = json.loads(
            (FIXTURES_DIR / entry["fixture"]).read_text()
        )
        context = build_context(ModelLayerOutput(**fixture))

        variants = {
            "original": report,
            "synonym": apply_text_variant(report, apply_synonym_variant),
            "punctuation": apply_text_variant(
                report, apply_punctuation_variant
            ),
            "negation_rephrase": apply_negation_variant(
                anomaly_type, report
            ),
        }

        scenario_scores = {}
        for variant_name, variant_report in variants.items():
            score = evaluate_report(
                variant_report, context, anomaly_type, risk_level
            )
            scenario_scores[variant_name] = score
            print(
                f"{anomaly_type:<38} {variant_name:<18} "
                f"overall={score.overall_score:.2f} "
                f"grounding={score.factual_grounding:.2f} "
                f"readability={score.readability:.2f} "
                f"hedging={score.hedging_appropriateness:.2f} "
                f"actionability={score.actionability:.2f}"
            )

        rows.append((anomaly_type, risk_level, scenario_scores))

    write_markdown(rows)


def write_markdown(rows) -> None:
    output_path = (
        Path(__file__).resolve().parent / "perturbation_results_5type.md"
    )
    dims = [
        "factual_grounding", "readability",
        "hedging_appropriateness", "actionability", "overall_score",
    ]
    total_checks = 0
    stable_checks = 0

    with open(output_path, "w") as f:
        f.write("# Perturbation Regression Results — All 5 Anomaly Types\n\n")
        f.write(
            "Extends run_perturbation_test.py (cooling_degradation "
            "only, 3 hand-written scenarios) to all 5 current anomaly "
            "types, using the real generated reports from "
            "qa_cross_validation/cross_validation_raw.json. Run after "
            "the pseudo-negation fix (PSEUDO_NEGATIONS).\n\n"
        )
        for anomaly_type, risk_level, scores in rows:
            f.write(f"## {anomaly_type} ({risk_level})\n\n")
            f.write(
                "| Variant | " + " | ".join(dims) + " |\n"
            )
            f.write("|" + "|".join(["---"] * (len(dims) + 1)) + "|\n")
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
            f"Consistency rate across all anomaly-type x variant x "
            f"dimension checks: **{stable_checks}/{total_checks} "
            f"({consistency:.1f}%)**.\n\n"
        )
        f.write(
            "Combined with the original 3-scenario cooling_degradation "
            "run (41/45, 91.1%), this covers all 5 anomaly types "
            "rather than one, and uses reports actually produced by "
            "the live pipeline (generate_report(), with the validator "
            "wired in) rather than only hand-authored scenario text.\n"
        )
    print(
        f"\nConsistency: {stable_checks}/{total_checks} "
        f"({consistency:.1f}%)"
    )
    print(f"Markdown report written to: {output_path}")


if __name__ == "__main__":
    run()
