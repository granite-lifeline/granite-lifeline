"""
Scenario evaluation script for GL-30 and GL-120.

Runs granite4.1:8b on three diagnostic scenarios to evaluate how the
model handles typical, atypical, and contradictory fault patterns.

Supports two modes:
- baseline: Uses build_context() without RAG knowledge retrieval
- rag: Uses build_context_with_rag() with fault knowledge retrieval
"""

import argparse
import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to Python path before importing project modules
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# noqa comments to suppress E402 for imports after path modification
from shared.interface_models import ModelLayerOutput  # noqa: E402
from report_layer.pipeline.context_injection import (  # noqa: E402
    build_context,
    build_context_with_rag
)


OLLAMA_API_URL = "http://localhost:11434/api/generate"
TIMEOUT = 120
AUDIENCE = "non-technical vehicle owner"
MODEL = "granite4.1:8b"

SCENARIOS = [
    {
        "name": "typical_cooling_stress",
        "file": "typical_cooling_stress.json",
        "description": "Typical fault pattern with clear ABNORMAL signal"
    },
    {
        "name": "atypical_cooling_stress",
        "file": "atypical_cooling_stress.json",
        "description": "Atypical pattern with NORMAL signal but anomaly flag"
    },
    {
        "name": "contradictory_cooling_stress",
        "file": "contradictory_cooling_stress.json",
        "description": "Contradictory signals and risk assessment"
    }
]

DEFAULT_PROMPT_VALUES = {
    "fault_knowledge": (
        "No retrieved fault knowledge was available for this run."
    ),
    "actions_knowledge": (
        "No retrieved action guidance was available for this run."
    ),
    "certainty_guidance": (
        "Use careful wording and do not present predictions as "
        "confirmed faults."
    ),
}


def render_prompt(template: str, values: Dict[str, str]) -> str:
    """Replace prompt placeholders with available values."""
    prompt_values = DEFAULT_PROMPT_VALUES.copy()
    prompt_values.update(values)

    prompt = template
    for key, value in prompt_values.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    return prompt


def load_scenario(filename: str) -> ModelLayerOutput:
    """Load test scenario from evaluation directory."""
    scenario_path = (
        PROJECT_ROOT / "report_layer" / "evaluation" / filename
    )
    with open(scenario_path, "r") as f:
        data = json.load(f)
    return ModelLayerOutput(**data)


def load_prompt_template(layer: int) -> str:
    """Load prompt template for specified layer."""
    filename = f"layer{layer}_"
    if layer == 1:
        filename += "description.txt"
    elif layer == 2:
        filename += "cause.txt"
    elif layer == 3:
        filename += "action.txt"
    else:
        raise ValueError(f"Invalid layer: {layer}")

    template_path = PROJECT_ROOT / "report_layer" / "prompts" / filename
    with open(template_path, "r") as f:
        return f.read()


def extract_json(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from response text with fallback."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def call_ollama(prompt: str) -> str:
    """Call Ollama API and return response text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_API_URL,
        json=payload,
        timeout=TIMEOUT
    )
    response.raise_for_status()

    result = response.json()
    return result.get("response", "")


def run_three_layer_chain(
    context_dict: dict,
    templates: Dict[int, str],
    mode: str = "rag"
) -> Dict[str, Any]:
    """
    Run three-layer prompt chain for a scenario.

    Args:
        context_dict: Context dictionary from build_context() or
                      build_context_with_rag()
        templates: Prompt templates for each layer
        mode: "baseline" or "rag"
    """
    results = {}

    print("  Running layer 1...")
    if mode == "baseline":
        # Baseline mode: only context and audience
        prompt1 = render_prompt(
            templates[1],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
            }
        )
    else:
        # RAG mode: include all RAG fields
        prompt1 = render_prompt(
            templates[1],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "fault_knowledge": context_dict["fault_knowledge"],
                "certainty_guidance": context_dict["certainty_guidance"],
            }
        )
    response1 = call_ollama(prompt1)
    parsed1 = extract_json(response1)

    if parsed1 and "anomaly_description" in parsed1:
        results["anomaly_description"] = parsed1["anomaly_description"]
    else:
        results["anomaly_description"] = response1
        print("  Warning: Layer 1 JSON parse failed")

    anomaly_desc = results["anomaly_description"]

    print("  Running layer 2...")
    if mode == "baseline":
        prompt2 = render_prompt(
            templates[2],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_desc,
            }
        )
    else:
        prompt2 = render_prompt(
            templates[2],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_desc,
                "fault_knowledge": context_dict["fault_knowledge"],
                "certainty_guidance": context_dict["certainty_guidance"],
            }
        )
    response2 = call_ollama(prompt2)
    parsed2 = extract_json(response2)

    if parsed2 and "possible_cause" in parsed2:
        results["possible_cause"] = parsed2["possible_cause"]
    else:
        results["possible_cause"] = response2
        print("  Warning: Layer 2 JSON parse failed")

    possible_cause = results["possible_cause"]

    print("  Running layer 3...")
    if mode == "baseline":
        prompt3 = render_prompt(
            templates[3],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_desc,
                "possible_cause": possible_cause,
            }
        )
    else:
        prompt3 = render_prompt(
            templates[3],
            {
                "context": context_dict["context"],
                "audience": AUDIENCE,
                "anomaly_description": anomaly_desc,
                "possible_cause": possible_cause,
                "fault_knowledge": context_dict["fault_knowledge"],
                "actions_knowledge": context_dict["actions_knowledge"],
                "certainty_guidance": context_dict["certainty_guidance"],
            }
        )
    response3 = call_ollama(prompt3)
    parsed3 = extract_json(response3)

    if parsed3 and "recommended_action" in parsed3:
        results["recommended_action"] = parsed3["recommended_action"]
    else:
        results["recommended_action"] = response3
        print("  Warning: Layer 3 JSON parse failed")

    return results


def format_actions(actions: Any) -> str:
    """Format recommended actions as bullet list."""
    if isinstance(actions, list):
        return "\n".join(f"- {action}" for action in actions)
    else:
        return str(actions)


def write_comparison_report(
    scenario_results: List[Dict[str, Any]],
    mode: str = "rag"
) -> None:
    """Write scenario comparison report to markdown."""
    output_path = (
        PROJECT_ROOT / "report_layer" / "evaluation" /
        "scenario_comparison.md"
    )

    mode_label = "RAG-Enhanced" if mode == "rag" else "Baseline"

    with open(output_path, "w") as f:
        f.write(f"# Scenario Comparison Report - GL-30 ({mode_label})\n\n")
        f.write(f"**Model:** {MODEL}\n")
        f.write(f"**Mode:** {mode_label}\n\n")
        f.write("**Objective:** Evaluate how granite4.1:8b handles ")
        f.write("typical, atypical, and contradictory diagnostic ")
        f.write("scenarios.\n\n")
        f.write("---\n\n")

        f.write("## Executive Summary\n\n")
        f.write("This evaluation validates Story 2 AC3 requirement: ")
        f.write("the model must distinguish typical from atypical ")
        f.write("fault scenarios and avoid force-fitting anomalies ")
        f.write("into known fault categories.\n\n")
        f.write("**Key Findings:**\n\n")
        f.write("- [To be completed after reviewing outputs]\n\n")
        f.write("---\n\n")

        f.write("## Test Scenarios\n\n")
        for scenario in scenario_results:
            f.write(f"### {scenario['name']}\n\n")
            f.write(f"**Description:** {scenario['description']}\n\n")

            input_data = scenario['input']
            f.write("**Input Summary:**\n\n")
            f.write("- Risk Score: ")
            f.write(f"{int(input_data.risk_score * 100)}%\n")
            f.write(f"- Risk Level: {input_data.risk_level}\n")
            f.write("- Prediction Confidence: ")
            f.write(f"{int(input_data.prediction_confidence * 100)}%\n")

            for signal in input_data.key_signals:
                ref_lower = signal.reference_range[0]
                ref_upper = signal.reference_range[1]
                is_abnormal = (
                    signal.value < ref_lower or
                    signal.value > ref_upper
                )
                status = "ABNORMAL" if is_abnormal else "NORMAL"
                unit_str = signal.unit if signal.unit else ""

                f.write(
                    f"- Key Signal: {signal.feature} = "
                    f"{signal.value}{unit_str} "
                    f"(reference: {ref_lower}-{ref_upper}{unit_str}) "
                    f"[{status}]\n"
                )

            f.write("\n")

            results = scenario['results']

            f.write("#### Anomaly Description\n\n")
            f.write(f"{results['anomaly_description']}\n\n")

            f.write("#### Possible Cause\n\n")
            f.write(f"{results['possible_cause']}\n\n")

            f.write("#### Recommended Action\n\n")
            actions_text = format_actions(
                results['recommended_action']
            )
            f.write(f"{actions_text}\n\n")

            f.write("---\n\n")

        f.write("## Comparative Analysis\n\n")

        f.write("### Language Adaptation by Risk Level\n\n")
        f.write("| Scenario | Risk Level | Confidence | ")
        f.write("Language Strength |\n")
        f.write("|----------|------------|------------|")
        f.write("-------------------|\n")
        for scenario in scenario_results:
            input_data = scenario['input']
            f.write(f"| {scenario['name']} | ")
            f.write(f"{input_data.risk_level} | ")
            f.write(f"{int(input_data.prediction_confidence * 100)}% | ")
            f.write("[To be analyzed] |\n")
        f.write("\n")

        f.write("### Signal Pattern Recognition\n\n")
        f.write("| Scenario | Signal Status | Model Response |\n")
        f.write("|----------|---------------|----------------|\n")
        for scenario in scenario_results:
            input_data = scenario['input']
            signal = input_data.key_signals[0]
            ref_lower = signal.reference_range[0]
            ref_upper = signal.reference_range[1]
            is_abnormal = (
                signal.value < ref_lower or
                signal.value > ref_upper
            )
            status = "ABNORMAL" if is_abnormal else "NORMAL"
            f.write(f"| {scenario['name']} | {status} | ")
            f.write("[To be analyzed] |\n")
        f.write("\n")

        f.write("### Story 2 AC3 Validation\n\n")
        f.write("**Requirement:** Model must distinguish typical ")
        f.write("from atypical fault scenarios.\n\n")
        f.write("**Evaluation Criteria:**\n\n")
        f.write("1. **Typical scenario**: Should produce confident, ")
        f.write("specific recommendations\n")
        f.write("2. **Atypical scenario**: Should acknowledge low ")
        f.write("confidence and mixed signals\n")
        f.write("3. **Contradictory scenario**: Should note ")
        f.write("contradiction without force-fitting\n\n")
        f.write("**Results:**\n\n")
        f.write("- [To be completed after manual review]\n\n")

        f.write("---\n\n")

        f.write("## Conclusion\n\n")
        f.write("[To be completed after reviewing all outputs]\n")

    print(f"\nReport written to: {output_path}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run scenario evaluation in baseline or RAG mode"
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "rag"],
        default="rag",
        help="Evaluation mode: baseline (no RAG) or rag (with RAG)"
    )
    args = parser.parse_args()

    mode = args.mode
    mode_label = "RAG-Enhanced" if mode == "rag" else "Baseline"

    print(f"Running scenario evaluation with {MODEL} ({mode_label})...\n")

    print("Loading prompt templates...")
    templates = {
        1: load_prompt_template(1),
        2: load_prompt_template(2),
        3: load_prompt_template(3)
    }

    scenario_results = []

    for scenario_info in SCENARIOS:
        print(f"\n=== Processing {scenario_info['name']} ===")

        print("Loading scenario...")
        test_input = load_scenario(scenario_info['file'])

        print("Building context...")
        if mode == "baseline":
            # Baseline mode: wrap string context in dict
            context_str = build_context(test_input)
            context_dict = {"context": context_str}
        else:
            # RAG mode: returns dict with all fields
            context_dict = build_context_with_rag(test_input)

        try:
            results = run_three_layer_chain(context_dict, templates, mode)
            scenario_results.append({
                "name": scenario_info['name'],
                "description": scenario_info['description'],
                "input": test_input,
                "results": results,
                "mode": mode
            })
            print(f"Completed {scenario_info['name']}\n")
        except Exception as e:
            print(f"Error processing {scenario_info['name']}: {e}\n")
            scenario_results.append({
                "name": scenario_info['name'],
                "description": scenario_info['description'],
                "input": test_input,
                "results": {
                    "anomaly_description": f"Error: {e}",
                    "possible_cause": f"Error: {e}",
                    "recommended_action": f"Error: {e}"
                },
                "mode": mode
            })

    print("\nWriting comparison report...")
    write_comparison_report(scenario_results, mode)
    print("Done!")


if __name__ == "__main__":
    main()
