"""Command-line entry point for producing the cleaned model-input CSV.

The cleaning core returns an enriched DataFrame with both model columns and quality columns.
This wrapper writes the model-facing cleaned CSV
and keeps theenriched intermediate CSV for the quality-audit step.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from cleaning_core import (
    LOGGER,
    CleaningError,
    build_output_columns,
    clean_dataset_enriched,
    load_config,
)
from project_paths import CONFIG_PATH, REPO_ROOT
from project_paths import CLEANED_DATASET, ENRICHED_DATASET


def _resolve_optional_path(
        path: str | Path | None, default_path: Path
    ) -> Path:
    """Resolve a CLI override or fall back to the centralized project path."""
    return Path(path).expanduser().resolve() if path else default_path


def run_cleaning(
    config: dict[str, Any],
    output_csv: str | Path | None = None,
    enriched_csv: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run cleaning, write enriched CSV, and return the model table."""
    output_config = config["output"]
    output_target = _resolve_optional_path(output_csv, CLEANED_DATASET)
    enriched_target = _resolve_optional_path(enriched_csv, ENRICHED_DATASET)

    # Run the deterministic core cleaning flow once so outputs stay aligned.
    enriched, summary = clean_dataset_enriched(
        config,
        repo_root=REPO_ROOT,
        output_target=output_target,
    )
    model_output = enriched[build_output_columns(config)].copy()

    # Create output directories before writing CSV artifacts.
    output_target.parent.mkdir(parents=True, exist_ok=True)
    enriched_target.parent.mkdir(parents=True, exist_ok=True)

    # Write the model-facing CSV and the audit-ready enriched intermediate CSV.
    float_format = output_config.get("float_format")
    model_output.to_csv(
        output_target,
        index=False,
        encoding="utf-8",
        float_format=float_format,
    )
    enriched.to_csv(
        enriched_target,
        index=False,
        encoding="utf-8",
        float_format=float_format,
    )

    # Return an English summary that downstream notebooks and logs can display.
    summary.update(
        {
            "output_csv": str(output_target.resolve()),
            "output_rows": int(len(model_output)),
            "output_columns": list(model_output.columns),
            "enriched_csv": str(enriched_target.resolve()),
            "enriched_rows": int(len(enriched)),
            "enriched_columns": list(enriched.columns),
        }
    )
    return model_output, summary


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the cleaning-only entry point."""
    parser = argparse.ArgumentParser(
        description="Clean and resample the KIT Automotive OBD-II dataset.",
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="Path to the cleaning configuration file.",
    )
    parser.add_argument(
        "--input-dir",
        help="Override input.directory from the configuration file.",
    )
    parser.add_argument(
        "--output",
        help="Override the cleaned model CSV path.",
    )
    parser.add_argument(
        "--enriched-output",
        help="Override the enriched intermediate CSV path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def main() -> int:
    """Load config, run cleaning, and log processing summary."""
    args = build_argument_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(message)s",
    )
    try:
        config = load_config(args.config)
        if args.input_dir:
            config["input"]["directory"] = args.input_dir
        _, report = run_cleaning(
            config,
            output_csv=args.output,
            enriched_csv=args.enriched_output,
        )
    except (CleaningError, OSError, pd.errors.ParserError) as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info(
        "Done: %d files, %d input -> %d output rows, %d trips, %d segments",
        report["files_processed"],
        report["input_rows"],
        report["output_rows"],
        report["trips"],
        report["segments"],
    )
    LOGGER.info("Cleaned output: %s", report["output_csv"])
    LOGGER.info("Enriched intermediate: %s", report["enriched_csv"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
