"""
Model comparison script for diagnostic report generation.

Compares four Granite models on a typical cooling system stress scenario.
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from shared.interface_models import ModelLayerOutput
from report_layer.pipeline.context_injection import build_context


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OLLAMA_API_URL = "http://localhost:11434/api/generate"
TIMEOUT = 120
AUDIENCE = "non-technical vehicle owner"

MODELS = [
    "granite3.3:2b",
    "granite3.3:8b",
    "granite4.1:3b",
    "granite4.1:8b"
]


def load_test_input() -> ModelLayerOutput:
    """Load test input from typical_cooling_stress.json."""
    input_path = (
        PROJECT_ROOT / "report_layer" / "evaluation" /
        "typical_cooling_stress.json"
    )
    with open(input_path, "r") as f:
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
    """
    Extract JSON from response text.

    First tries direct parsing, then tries to extract JSON portion.
    """
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


def call_ollama(model: str, prompt: str) -> str:
    """Call Ollama API and return response text."""
    payload = {
        "model": model,
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


def run_layer1(
    model: str,
    context: str,
    template: str
) -> Dict[str, Any]:
    """Run layer 1: anomaly description."""
    print(f"Running {model} layer 1...")

    prompt = (
        template
        .replace("{context}", context)
        .replace("{audience}", AUDIENCE)
    )
    response_text = call_ollama(model, prompt)

    parsed = extract_json(response_text)
    if parsed and "anomaly_description" in parsed:
        return {
            "anomaly_description": parsed["anomaly_description"],
            "raw_response": None
        }
    else:
        return {
            "anomaly_description": None,
            "raw_response": response_text
        }


def run_layer2(
    model: str,
    context: str,
    template: str,
    anomaly_description: str
) -> Dict[str, Any]:
    """Run layer 2: possible cause."""
    print(f"Running {model} layer 2...")

    prompt = (
        template
        .replace("{context}", context)
        .replace("{audience}", AUDIENCE)
        .replace("{anomaly_description}", anomaly_description)
    )
    response_text = call_ollama(model, prompt)

    parsed = extract_json(response_text)
    if parsed and "possible_cause" in parsed:
        return {
            "possible_cause": parsed["possible_cause"],
            "raw_response": None
        }
    else:
        return {
            "possible_cause": None,
            "raw_response": response_text
        }


def run_layer3(
    model: str,
    context: str,
    template: str,
    anomaly_description: str,
    possible_cause: str
) -> Dict[str, Any]:
    """Run layer 3: recommended action."""
    print(f"Running {model} layer 3...")

    prompt = (
        template
        .replace("{context}", context)
        .replace("{audience}", AUDIENCE)
        .replace("{anomaly_description}", anomaly_description)
        .replace("{possible_cause}", possible_cause)
    )
    response_text = call_ollama(model, prompt)

    parsed = extract_json(response_text)
    if parsed and "recommended_action" in parsed:
        return {
            "recommended_action": parsed["recommended_action"],
            "raw_response": None
        }
    else:
        return {
            "recommended_action": None,
            "raw_response": response_text
        }


def run_model_chain(
    model: str,
    context: str,
    templates: Dict[int, str]
) -> Dict[str, Any]:
    """Run full three-layer chain for a model."""
    results = {}

    layer1_result = run_layer1(model, context, templates[1])
    results["layer1"] = layer1_result

    anomaly_desc = (
        layer1_result["anomaly_description"]
        if layer1_result["anomaly_description"]
        else layer1_result["raw_response"]
    )

    layer2_result = run_layer2(
        model, context, templates[2], anomaly_desc
    )
    results["layer2"] = layer2_result

    possible_cause = (
        layer2_result["possible_cause"]
        if layer2_result["possible_cause"]
        else layer2_result["raw_response"]
    )

    layer3_result = run_layer3(
        model, context, templates[3], anomaly_desc, possible_cause
    )
    results["layer3"] = layer3_result

    return results


def format_actions(actions: Any) -> str:
    """Format recommended actions as bullet list."""
    if isinstance(actions, list):
        return "\n".join(f"- {action}" for action in actions)
    else:
        return str(actions)


def write_markdown_report(
    test_input: ModelLayerOutput,
    all_results: Dict[str, Dict[str, Any]]
) -> None:
    """Write comparison results to markdown file."""
    output_path = (
        PROJECT_ROOT / "report_layer" / "evaluation" /
        "model_comparison.md"
    )

    with open(output_path, "w") as f:
        f.write("# Model Comparison Report\n\n")

        f.write("## Test Input Summary\n\n")
        f.write(f"- Anomaly Type: {test_input.component}\n")
        f.write(
            f"- Risk Score: {int(test_input.risk_score * 100)}%\n"
        )
        f.write(f"- Risk Level: {test_input.risk_level}\n")

        for signal in test_input.key_signals:
            ref_lower = signal.reference_range[0]
            ref_upper = signal.reference_range[1]
            is_abnormal = (
                signal.value < ref_lower or signal.value > ref_upper
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

        for model in MODELS:
            f.write(f"## {model}\n\n")
            results = all_results[model]

            f.write("### Anomaly Description\n\n")
            layer1 = results["layer1"]
            if layer1["anomaly_description"]:
                f.write(f"{layer1['anomaly_description']}\n\n")
            else:
                f.write("*JSON parsing failed. Raw response:*\n\n")
                f.write(f"```\n{layer1['raw_response']}\n```\n\n")

            f.write("### Possible Cause\n\n")
            layer2 = results["layer2"]
            if layer2["possible_cause"]:
                f.write(f"{layer2['possible_cause']}\n\n")
            else:
                f.write("*JSON parsing failed. Raw response:*\n\n")
                f.write(f"```\n{layer2['raw_response']}\n```\n\n")

            f.write("### Recommended Action\n\n")
            layer3 = results["layer3"]
            if layer3["recommended_action"]:
                actions_text = format_actions(
                    layer3["recommended_action"]
                )
                f.write(f"{actions_text}\n\n")
            else:
                f.write("*JSON parsing failed. Raw response:*\n\n")
                f.write(f"```\n{layer3['raw_response']}\n```\n\n")

        f.write("## Comparison Notes\n\n")
        f.write("To be completed after reviewing outputs above.\n")

    print(f"\nReport written to: {output_path}")


def main():
    """Main execution function."""
    print("Loading test input...")
    test_input = load_test_input()

    print("Building context...")
    context = build_context(test_input)

    print("Loading prompt templates...")
    templates = {
        1: load_prompt_template(1),
        2: load_prompt_template(2),
        3: load_prompt_template(3)
    }

    print("\nRunning model comparisons...\n")
    all_results = {}

    for model in MODELS:
        print(f"\n=== Processing {model} ===")
        try:
            results = run_model_chain(model, context, templates)
            all_results[model] = results
            print(f"Completed {model}\n")
        except Exception as e:
            print(f"Error processing {model}: {e}\n")
            all_results[model] = {
                "layer1": {
                    "anomaly_description": None,
                    "raw_response": f"Error: {e}"
                },
                "layer2": {
                    "possible_cause": None,
                    "raw_response": f"Error: {e}"
                },
                "layer3": {
                    "recommended_action": None,
                    "raw_response": f"Error: {e}"
                }
            }

    print("\nWriting comparison report...")
    write_markdown_report(test_input, all_results)
    print("Done!")


if __name__ == "__main__":
    main()
