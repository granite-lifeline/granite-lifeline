"""
Story 6 fine-tuning entrypoint for Granite TTM.

This script consumes Lucca's train/validation split manifest, filters
Group 1's `feature_dataset.csv` by segment id, builds TTM forecast
windows, and optionally runs Hugging Face `Trainer` with the
`tsfm_public` TinyTimeMixer model.

Default behavior is a dry run: validate the split and dataset shape
without loading the model or starting training. Add `--train` for the
actual fine-tuning run in the next Story 6 task.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
import torch
from transformers import Trainer, TrainingArguments, set_seed
from tsfm_public.toolkit.dataset import ForecastDFDataset
from tsfm_public.toolkit.get_model import get_model

try:
    from model.kit_residual_detector import (
        DEFAULT_CONTEXT_LENGTH,
        DEFAULT_PREDICTION_LENGTH,
        MODEL_PATH,
        MODEL_SIGNALS,
        load_group1_features,
    )
except ImportError:  # direct script run: src/model is current package
    from kit_residual_detector import (
        DEFAULT_CONTEXT_LENGTH,
        DEFAULT_PREDICTION_LENGTH,
        MODEL_PATH,
        MODEL_SIGNALS,
        load_group1_features,
    )

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TTM_RELATED_DIR = Path(__file__).resolve().parents[2]

DEFAULT_MANIFEST = (
    _TTM_RELATED_DIR / "outputs" / "finetune_split_manifest.json"
)
DEFAULT_OUTPUT_DIR = _TTM_RELATED_DIR / "outputs" / "ttm_finetuned"
DEFAULT_STRIDE = DEFAULT_PREDICTION_LENGTH
TTM_BATCH_KEYS = (
    "past_values",
    "future_values",
    "past_observed_mask",
    "future_observed_mask",
)

SEGMENT_COLUMN = "segment_id"
TRIP_COLUMN = "trip_id"
ROW_COLUMN = "row_in_segment"
TIMESTAMP_COLUMN = "timestamp"


def resolve_repo_path(path: str | Path) -> Path:
    """Resolve manifest paths relative to this checkout's repo root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (_REPO_ROOT / candidate).resolve()


def repo_relative(path: str | Path) -> str:
    """Return a portable repo-root-relative path when possible."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and minimally validate Lucca's split manifest."""
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    required = {"input_file", "train_trips", "validation_trips"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(
            f"{manifest_path} is missing required keys: {missing}"
        )
    return manifest


def flatten_segment_ids(
    split: Mapping[str, Sequence[str]] | Sequence[str],
) -> list[str]:
    """Flatten manifest split data into a stable segment id list.

    Current manifests store `{trip_id: [segment_id, ...]}` so whole
    trips stay on one side of the split. A plain list is accepted for
    backward compatibility with early split drafts.
    """
    if isinstance(split, Mapping):
        segment_ids: list[str] = []
        for trip_id in sorted(split):
            segment_ids.extend(str(segment) for segment in split[trip_id])
        return segment_ids
    return [str(segment) for segment in split]


def select_manifest_segments(
    manifest: Mapping[str, Any],
    *,
    max_train_segments: int | None = None,
    max_validation_segments: int | None = None,
) -> tuple[list[str], list[str]]:
    """Return train/validation segment ids, optionally shortened."""
    train_segments = flatten_segment_ids(manifest["train_trips"])
    validation_segments = flatten_segment_ids(manifest["validation_trips"])

    if max_train_segments is not None:
        train_segments = train_segments[:max_train_segments]
    if max_validation_segments is not None:
        validation_segments = validation_segments[:max_validation_segments]
    return train_segments, validation_segments


def filter_by_segments(
    frame: pd.DataFrame,
    segment_ids: Sequence[str],
    split_name: str,
) -> pd.DataFrame:
    """Filter the feature frame and fail loudly on missing segments."""
    if not segment_ids:
        raise ValueError(f"{split_name} split has no segment ids")

    requested = set(segment_ids)
    available = set(frame[SEGMENT_COLUMN].astype(str).unique())
    missing = sorted(requested - available)
    if missing:
        raise ValueError(
            f"{split_name} split references {len(missing)} missing "
            f"segment ids, e.g. {missing[:5]}"
        )

    selected = frame[frame[SEGMENT_COLUMN].astype(str).isin(requested)].copy()
    return selected.sort_values([TRIP_COLUMN, SEGMENT_COLUMN, ROW_COLUMN])


def build_forecast_dataset(
    frame: pd.DataFrame,
    *,
    context_length: int,
    prediction_length: int,
    stride: int,
) -> ForecastDFDataset:
    """Build TTM forecast windows from one split of Group 1 data."""
    missing_signals = sorted(set(MODEL_SIGNALS) - set(frame.columns))
    if missing_signals:
        raise ValueError(f"Missing model signals: {missing_signals}")

    for signal in MODEL_SIGNALS:
        values = pd.to_numeric(frame[signal], errors="coerce")
        bad_values = values.isna() & frame[signal].notna()
        if bad_values.any():
            raise ValueError(
                f"{signal} contains non-numeric values; clean them "
                "before fine-tuning"
            )
        frame[signal] = values

    return ForecastDFDataset(
        data=frame,
        id_columns=[SEGMENT_COLUMN],
        timestamp_column=TIMESTAMP_COLUMN,
        target_columns=MODEL_SIGNALS,
        context_length=context_length,
        prediction_length=prediction_length,
        stride=stride,
        enable_padding=False,
        impute_method="fill",
    )


def load_split_frames(
    manifest_path: Path,
    input_csv: Path | None = None,
    *,
    max_train_segments: int | None = None,
    max_validation_segments: int | None = None,
) -> tuple[
    pd.DataFrame, pd.DataFrame, dict[str, Any], Path, list[str], list[str]
]:
    """Load Group 1 features and split them according to the manifest."""
    manifest = load_manifest(manifest_path)
    resolved_input = (
        input_csv.resolve()
        if input_csv is not None
        else resolve_repo_path(manifest["input_file"])
    )

    frame = load_group1_features(resolved_input)
    train_segments, validation_segments = select_manifest_segments(
        manifest,
        max_train_segments=max_train_segments,
        max_validation_segments=max_validation_segments,
    )
    train_frame = filter_by_segments(frame, train_segments, "train")
    validation_frame = filter_by_segments(
        frame, validation_segments, "validation"
    )
    return (
        train_frame,
        validation_frame,
        manifest,
        resolved_input,
        train_segments,
        validation_segments,
    )


def summarize_dataset(
    frame: pd.DataFrame,
    dataset: ForecastDFDataset,
    segment_ids: Sequence[str],
) -> dict[str, Any]:
    """Summarize one split for config and terminal output."""
    missing_counts = {
        signal: int(frame[signal].isna().sum())
        for signal in MODEL_SIGNALS
    }
    return {
        "segments": len(segment_ids),
        "rows": int(len(frame)),
        "windows": int(len(dataset)),
        "trips": int(frame[TRIP_COLUMN].nunique()),
        "missing_model_signal_values": missing_counts,
    }


def sample_shapes(dataset: ForecastDFDataset) -> dict[str, list[int]]:
    """Return tensor shapes from the first TTM training sample."""
    if len(dataset) == 0:
        raise ValueError(
            "No training windows were produced; check segment length, "
            "context_length, prediction_length, and stride"
        )
    sample = dataset[0]
    return {
        "past_values": list(sample["past_values"].shape),
        "future_values": list(sample["future_values"].shape),
    }


def ttm_data_collator(
    features: Sequence[Mapping[str, Any]],
) -> dict[str, torch.Tensor]:
    """Batch only tensor inputs accepted by TinyTimeMixer.forward().

    ForecastDFDataset also returns metadata fields such as timestamp
    and id; Hugging Face's default collator tries to tensorize them
    and fails. Keep metadata out of the training batch.
    """
    return {
        key: torch.stack([feature[key] for feature in features])
        for key in TTM_BATCH_KEYS
    }


def build_run_config(
    *,
    manifest_path: Path,
    input_csv: Path,
    output_dir: Path,
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    train_dataset: ForecastDFDataset,
    validation_dataset: ForecastDFDataset,
    train_segments: Sequence[str],
    validation_segments: Sequence[str],
    args: argparse.Namespace,
    mode: str,
) -> dict[str, Any]:
    """Build a reproducible config record for dry-runs and training."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "model_path": args.model_path,
        "manifest_file": repo_relative(manifest_path),
        "input_file": repo_relative(input_csv),
        "output_dir": repo_relative(output_dir),
        "model_signals": list(MODEL_SIGNALS),
        "context_length": args.context_length,
        "prediction_length": args.prediction_length,
        "stride": args.stride,
        "seed": args.seed,
        "training": {
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
        },
        "train": summarize_dataset(
            train_frame, train_dataset, train_segments
        ),
        "validation": summarize_dataset(
            validation_frame, validation_dataset, validation_segments
        ),
        "sample_shapes": sample_shapes(train_dataset),
        "note": (
            "Dry-run mode validates the fine-tuning input pipeline only; "
            "use --train to load TTM, run Trainer.train(), and save the "
            "model artifact."
        )
        if mode == "dry_run"
        else "Training run completed and model artifact was saved.",
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def create_trainer(
    *,
    train_dataset: ForecastDFDataset,
    validation_dataset: ForecastDFDataset,
    args: argparse.Namespace,
) -> Trainer:
    """Instantiate the TTM model and Hugging Face trainer."""
    set_seed(args.seed)
    model = get_model(
        args.model_path,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
    )
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "checkpoints"),
        overwrite_output_dir=True,
        do_train=True,
        do_eval=True,
        eval_strategy="epoch",
        save_strategy="no",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        report_to=[],
        remove_unused_columns=False,
        seed=args.seed,
    )
    return Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=ttm_data_collator,
    )


def copy_manifest(manifest_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, output_dir / "finetune_split_manifest.json")


def print_summary(config: Mapping[str, Any]) -> None:
    print(json.dumps(config, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build Group 1 train/validation TTM datasets from Lucca's "
            "manifest and optionally run Granite TTM fine-tuning."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to finetune_split_manifest.json.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=None,
        help="Override manifest input_file with a specific feature CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for config, split copy, and trained model.",
    )
    parser.add_argument(
        "--model-path",
        default=MODEL_PATH,
        help="Hugging Face model id or local TTM model path.",
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=DEFAULT_CONTEXT_LENGTH,
        help="TTM context window length.",
    )
    parser.add_argument(
        "--prediction-length",
        type=int,
        default=DEFAULT_PREDICTION_LENGTH,
        help="TTM prediction horizon length.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=DEFAULT_STRIDE,
        help="Window stride within each segment.",
    )
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--max-train-segments",
        type=int,
        default=None,
        help="Debug option to shorten the train split.",
    )
    parser.add_argument(
        "--max-validation-segments",
        type=int,
        default=None,
        help="Debug option to shorten the validation split.",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Actually run Trainer.train(); without this, only dry-run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.manifest = args.manifest.resolve()
    args.output_dir = args.output_dir.resolve()
    args.input_csv = args.input_csv.resolve() if args.input_csv else None

    (
        train_frame,
        validation_frame,
        _manifest,
        resolved_input,
        train_segments,
        validation_segments,
    ) = load_split_frames(
        args.manifest,
        args.input_csv,
        max_train_segments=args.max_train_segments,
        max_validation_segments=args.max_validation_segments,
    )

    train_dataset = build_forecast_dataset(
        train_frame,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
        stride=args.stride,
    )
    validation_dataset = build_forecast_dataset(
        validation_frame,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
        stride=args.stride,
    )

    mode = "train" if args.train else "dry_run"
    config = build_run_config(
        manifest_path=args.manifest,
        input_csv=resolved_input,
        output_dir=args.output_dir,
        train_frame=train_frame,
        validation_frame=validation_frame,
        train_dataset=train_dataset,
        validation_dataset=validation_dataset,
        train_segments=train_segments,
        validation_segments=validation_segments,
        args=args,
        mode=mode,
    )
    write_json(args.output_dir / "training_config.json", config)
    copy_manifest(args.manifest, args.output_dir)

    if not args.train:
        print_summary(config)
        return

    trainer = create_trainer(
        train_dataset=train_dataset,
        validation_dataset=validation_dataset,
        args=args,
    )
    train_result = trainer.train()
    eval_metrics = trainer.evaluate()
    trainer.save_model(str(args.output_dir / "model"))
    config["trainer_metrics"] = {
        "train": train_result.metrics,
        "validation": eval_metrics,
    }
    config["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_json(args.output_dir / "training_config.json", config)
    print_summary(config)


if __name__ == "__main__":
    main()
