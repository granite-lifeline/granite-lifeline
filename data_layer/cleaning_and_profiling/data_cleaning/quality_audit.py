"""Generate quality-audit CSV and JSON from the enriched cleaning CSV."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from cleaning_core import (
    LOGGER,
    TIMESTAMP_FIELD,
    UTC_TIMESTAMP_FORMAT,
    CleaningError,
    build_output_columns,
    build_quality_output_columns,
    load_config,
)
from project_paths import (
    CONFIG_PATH,
    ENRICHED_DATASET,
    QUALITY_CSV,
    REPORT_JSON,
    display_path,
)


def _resolve_optional_path(
        path: str | Path | None, default_path: Path
    ) -> Path:
    """Resolve a CLI override or fall back to the centralized project path."""
    return Path(path).expanduser().resolve() if path else default_path


def build_quality_report(
    enriched: pd.DataFrame,
    config: dict[str, Any],
    enriched_target: Path,
    quality_target: Path,
) -> dict[str, Any]:
    """Build an English audit report from the enriched intermediate table."""
    fields = list(config["fields"])
    key_columns = ["trip_id", "segment_id", TIMESTAMP_FIELD]
    duplicate_key_rows = int(
        enriched.duplicated(key_columns, keep=False).sum()
    )

    # Verify the one-second cadence inside each continuous segment.
    parsed_timestamps = pd.to_datetime(
        enriched[TIMESTAMP_FIELD],
        utc=True,
        errors="raise",
    )
    segment_diffs = (
        enriched.assign(_parsed_timestamp=parsed_timestamps)
        .groupby("segment_id", sort=False)["_parsed_timestamp"]
        .diff()
        .dt.total_seconds()
    )

    # Count per-field audit signals when the corresponding columns are present.
    imputed_values = {
        field: int(
            enriched.get(f"{field}_is_imputed", pd.Series(False)).sum()
        )
        for field in fields
    }
    suspicious_values = {
        field: int(
            enriched.get(f"{field}_is_suspicious", pd.Series(False)).sum()
        )
        for field in fields
    }
    hard_invalid_source_bins = {
        field: int(
            enriched.get(
                f"{field}_had_hard_invalid_source", pd.Series(False)).sum()
        )
        for field in fields
    }
    remaining_missing = {
        field: int(enriched[field].isna().sum())
        for field in fields
        if field in enriched.columns
    }

    return {
        "pipeline_version": config.get("version"),
        "report_source": "enriched_intermediate_csv",
        "enriched_csv": display_path(enriched_target),
        "quality_csv": display_path(quality_target),
        "quality_rows": int(len(enriched)),
        "quality_columns": build_quality_output_columns(config),
        "model_output_columns": build_output_columns(config),
        "timezone": config["time"]["timezone"],
        "output_timezone": "UTC",
        "timestamp_format": UTC_TIMESTAMP_FORMAT,
        "resample_frequency": config["time"]["resample_frequency"],
        "segment_gap_seconds": config["time"]["segment_gap_seconds"],
        "imputation_max_seconds": config["time"]["imputation_max_seconds"],
        "source_files": int(enriched["source_file"].nunique()),
        "trips": int(enriched["trip_id"].nunique()),
        "segments": int(enriched["segment_id"].nunique()),
        "duplicate_composite_key_rows": duplicate_key_rows,
        "non_one_second_diffs_inside_segments": int(
            segment_diffs.dropna().ne(1).sum()
        ),
        "imputed_values": imputed_values,
        "suspicious_values": suspicious_values,
        "hard_invalid_source_bins": hard_invalid_source_bins,
        "remaining_missing": remaining_missing,
        "rows_with_any_imputation": int(enriched["is_imputed_any"].sum()),
        "rows_with_any_suspicious_value": int(
            enriched["is_suspicious_any"].sum()),
        "rows_with_hard_invalid_source": int(
            enriched["had_hard_invalid_source_any"].sum()
        ),
        "report_notes": [
            "This report was generated from the enriched intermediate CSV.",
            "Raw input row counts are not recomputed by the audit step.",
        ],
    }


def run_quality_audit(
    config: dict[str, Any],
    enriched_csv: str | Path | None = None,
    quality_csv: str | Path | None = None,
    report_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read enriched data, write quality report, and return quality table."""
    output_config = config["output"]
    enriched_target = _resolve_optional_path(enriched_csv, ENRICHED_DATASET)
    quality_target = _resolve_optional_path(quality_csv, QUALITY_CSV)
    report_target = _resolve_optional_path(report_path, REPORT_JSON)

    if not enriched_target.exists():
        raise CleaningError(
            f"Enriched intermediate CSV not found: {enriched_target}. "
            "Run data_cleaning.py first."
        )

    # Read the enriched intermediate 
    # with low_memory disabled to preserve mixed text fields.
    enriched = pd.read_csv(enriched_target, low_memory=False)
    quality_output = enriched[build_quality_output_columns(config)].copy()

    # Write the row-level quality table and the English JSON audit report.
    quality_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    quality_output.to_csv(
        quality_target,
        index=False,
        encoding="utf-8",
        float_format=output_config.get("float_format"),
    )

    report = build_quality_report
    (enriched, config, enriched_target, quality_target)
    report["report_json"] = display_path(report_target)
    report_target.write_text(
        json.dumps(report, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return quality_output, report


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the quality-audit entry point."""
    parser = argparse.ArgumentParser(
        description="Generate quality-audit outputs from enriched CSV.",
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="Path to the cleaning configuration file.",
    )
    parser.add_argument(
        "--enriched-input",
        help="Override the enriched intermediate CSV path.",
    )
    parser.add_argument(
        "--quality-output",
        help="Override the quality-audit CSV path.",
    )
    parser.add_argument(
        "--report",
        help="Override the JSON audit report path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def main() -> int:
    """Load config, generate audit outputs, and log summary."""
    args = build_argument_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(message)s",
    )
    try:
        config = load_config(args.config)
        _, report = run_quality_audit(
            config,
            enriched_csv=args.enriched_input,
            quality_csv=args.quality_output,
            report_path=args.report,
        )
    except (CleaningError, OSError, pd.errors.ParserError, KeyError) as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info(
        "Audit done: %d rows, %d trips, %d segments",
        report["quality_rows"],
        report["trips"],
        report["segments"],
    )
    LOGGER.info("Quality output: %s", report["quality_csv"])
    LOGGER.info("Audit report: %s", report["report_json"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
