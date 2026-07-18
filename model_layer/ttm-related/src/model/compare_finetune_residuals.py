"""
Story 6 comparison: zero-shot TTM vs fine-tuned TTM residuals.

This evaluates both models on the same held-out validation windows
from Lucca's split manifest and writes a small comparison table.
The comparison criterion is project-local: fine-tuning is considered
beneficial if overall validation MAE improves by at least 5% and at
least 4 of the 6 model signals do not get worse.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import torch
from torch.utils.data import DataLoader
from tqdm.auto import tqdm
from tsfm_public.toolkit.get_model import get_model

try:
    from model.finetune_ttm import (
        DEFAULT_MANIFEST,
        DEFAULT_OUTPUT_DIR,
        DEFAULT_STRIDE,
        build_forecast_dataset,
        load_split_frames,
        repo_relative,
        ttm_data_collator,
    )
    from model.kit_residual_detector import (
        DEFAULT_CONTEXT_LENGTH,
        DEFAULT_PREDICTION_LENGTH,
        MODEL_PATH,
        MODEL_SIGNALS,
        extract_prediction_tensor,
    )
except ImportError:  # direct script run: src/model is current package
    from finetune_ttm import (
        DEFAULT_MANIFEST,
        DEFAULT_OUTPUT_DIR,
        DEFAULT_STRIDE,
        build_forecast_dataset,
        load_split_frames,
        repo_relative,
        ttm_data_collator,
    )
    from kit_residual_detector import (
        DEFAULT_CONTEXT_LENGTH,
        DEFAULT_PREDICTION_LENGTH,
        MODEL_PATH,
        MODEL_SIGNALS,
        extract_prediction_tensor,
    )

_TTM_RELATED_DIR = Path(__file__).resolve().parents[2]
DEFAULT_FINETUNED_MODEL = DEFAULT_OUTPUT_DIR / "model"
DEFAULT_OUTPUT_JSON = (
    _TTM_RELATED_DIR / "outputs" / "finetune_residual_comparison.json"
)
DEFAULT_OUTPUT_MD = (
    _TTM_RELATED_DIR / "outputs" / "finetune_residual_comparison.md"
)
MIN_CLEAR_IMPROVEMENT_PCT = 5.0
MIN_NON_WORSE_SIGNALS = 4


def load_ttm_model(
    model_path: str | Path,
    *,
    context_length: int,
    prediction_length: int,
):
    model = get_model(
        str(model_path),
        context_length=context_length,
        prediction_length=prediction_length,
    )
    model.eval()
    return model


def evaluate_model_mae(
    model,
    dataloader: DataLoader,
) -> dict[str, Any]:
    """Compute overall and per-signal MAE, respecting observed masks."""
    signal_abs_error = torch.zeros(len(MODEL_SIGNALS), dtype=torch.float64)
    signal_counts = torch.zeros(len(MODEL_SIGNALS), dtype=torch.float64)

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="evaluating", leave=False):
            output = model(
                past_values=batch["past_values"],
                past_observed_mask=batch["past_observed_mask"],
            )
            prediction = extract_prediction_tensor(output).detach().cpu()
            truth = batch["future_values"].detach().cpu()
            observed = batch["future_observed_mask"].detach().cpu().bool()
            abs_error = (prediction - truth).abs()
            masked_error = abs_error * observed
            signal_abs_error += masked_error.sum(dim=(0, 1)).double()
            signal_counts += observed.sum(dim=(0, 1)).double()

    per_signal = {
        signal: float(signal_abs_error[index] / signal_counts[index])
        for index, signal in enumerate(MODEL_SIGNALS)
    }
    overall = float(signal_abs_error.sum() / signal_counts.sum())
    return {
        "overall_mae": overall,
        "per_signal_mae": per_signal,
        "valid_points": int(signal_counts.sum().item()),
        "per_signal_valid_points": {
            signal: int(signal_counts[index].item())
            for index, signal in enumerate(MODEL_SIGNALS)
        },
    }


def improvement_pct(before: float, after: float) -> float:
    if before == 0:
        return 0.0
    return (before - after) / before * 100.0


def build_comparison(
    zero_shot: Mapping[str, Any],
    fine_tuned: Mapping[str, Any],
) -> dict[str, Any]:
    per_signal = {}
    non_worse_signals = 0
    for signal in MODEL_SIGNALS:
        zero_value = zero_shot["per_signal_mae"][signal]
        tuned_value = fine_tuned["per_signal_mae"][signal]
        delta = improvement_pct(zero_value, tuned_value)
        if delta >= 0:
            non_worse_signals += 1
        per_signal[signal] = {
            "zero_shot_mae": zero_value,
            "fine_tuned_mae": tuned_value,
            "improvement_pct": delta,
        }

    overall_improvement = improvement_pct(
        zero_shot["overall_mae"], fine_tuned["overall_mae"]
    )
    is_clear = (
        overall_improvement >= MIN_CLEAR_IMPROVEMENT_PCT
        and non_worse_signals >= MIN_NON_WORSE_SIGNALS
    )
    return {
        "overall": {
            "zero_shot_mae": zero_shot["overall_mae"],
            "fine_tuned_mae": fine_tuned["overall_mae"],
            "improvement_pct": overall_improvement,
        },
        "per_signal": per_signal,
        "decision_rule": {
            "clear_improvement_threshold_pct": MIN_CLEAR_IMPROVEMENT_PCT,
            "minimum_non_worse_signals": MIN_NON_WORSE_SIGNALS,
            "signals_total": len(MODEL_SIGNALS),
            "clear_improvement": is_clear,
            "non_worse_signals": non_worse_signals,
        },
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_markdown(path: Path, payload: Mapping[str, Any]) -> None:
    comparison = payload["comparison"]
    rows = [
        "| Metric | Zero-shot MAE | Fine-tuned MAE | Improvement |",
        "|---|---:|---:|---:|",
        (
            "| Overall | "
            f"{comparison['overall']['zero_shot_mae']:.4f} | "
            f"{comparison['overall']['fine_tuned_mae']:.4f} | "
            f"{comparison['overall']['improvement_pct']:.2f}% |"
        ),
    ]
    for signal, stats in comparison["per_signal"].items():
        rows.append(
            f"| {signal} | {stats['zero_shot_mae']:.4f} | "
            f"{stats['fine_tuned_mae']:.4f} | "
            f"{stats['improvement_pct']:.2f}% |"
        )

    decision = comparison["decision_rule"]
    verdict = (
        "clear improvement"
        if decision["clear_improvement"]
        else "not a clear improvement"
    )
    text = "\n".join(
        [
            "# Fine-tuned TTM Residual Comparison",
            "",
            f"Generated at: `{payload['generated_at']}`",
            "",
            f"Validation windows: `{payload['validation']['windows']}`",
            f"Validation segments: `{payload['validation']['segments']}`",
            "",
            *rows,
            "",
            "## Decision Rule",
            "",
            (
                "Fine-tuning is considered beneficial if the overall "
                "validation MAE decreases by at least 5% and at least "
                "4 of the 6 model signals do not get worse."
            ),
            "",
            f"Result: **{verdict}**.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare zero-shot and fine-tuned TTM residuals."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-csv", type=Path, default=None)
    parser.add_argument(
        "--fine-tuned-model",
        type=Path,
        default=DEFAULT_FINETUNED_MODEL,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument(
        "--prediction-length", type=int, default=DEFAULT_PREDICTION_LENGTH
    )
    parser.add_argument("--stride", type=int, default=DEFAULT_STRIDE)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-validation-segments", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    (
        _train_frame,
        validation_frame,
        _manifest,
        resolved_input,
        _train_segments,
        validation_segments,
    ) = load_split_frames(
        args.manifest,
        args.input_csv,
        max_validation_segments=args.max_validation_segments,
    )
    validation_dataset = build_forecast_dataset(
        validation_frame,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
        stride=args.stride,
    )
    dataloader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=ttm_data_collator,
    )

    zero_model = load_ttm_model(
        MODEL_PATH,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
    )
    zero_metrics = evaluate_model_mae(zero_model, dataloader)
    del zero_model

    tuned_model = load_ttm_model(
        args.fine_tuned_model,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
    )
    tuned_metrics = evaluate_model_mae(tuned_model, dataloader)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_signals": list(MODEL_SIGNALS),
        "manifest_file": repo_relative(args.manifest),
        "input_file": repo_relative(resolved_input),
        "zero_shot_model": MODEL_PATH,
        "fine_tuned_model": repo_relative(args.fine_tuned_model),
        "validation": {
            "segments": len(validation_segments),
            "rows": int(len(validation_frame)),
            "windows": int(len(validation_dataset)),
            "trips": int(validation_frame["trip_id"].nunique()),
        },
        "zero_shot": zero_metrics,
        "fine_tuned": tuned_metrics,
        "comparison": build_comparison(zero_metrics, tuned_metrics),
    }
    write_json(args.output_json, payload)
    write_markdown(args.output_md, payload)
    print(json.dumps(payload["comparison"], indent=2))


if __name__ == "__main__":
    main()
