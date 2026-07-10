"""Core cleaning logic for the KIT Automotive OBD-II dataset.

This module performs deterministic cleaning only.
It returns an enriched DataFrame
that contains both model-ready signal columns and quality columns,
but it does not write any output files.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


LOGGER = logging.getLogger("obd_cleaning")
TIMESTAMP_FIELD = "timestamp"
CONDITION_LABELS = {"Normal", "Stau", "Frei", "Free", "Busy"}
UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class CleaningError(RuntimeError):
    """Raised when input data cannot be cleaned safely."""


@dataclass(frozen=True)
class TripMetadata:
    """Trip metadata parsed from the KIT file name."""

    date: str
    brand: str
    model: str
    origin: str
    destination: str
    condition: str | None
    extension: str | None
    route_sequence: str | None

    @property
    # A route label from origin and destination for filtering and QA.
    def route(self) -> str:
        return f"{self.origin}_{self.destination}"


# Load the cleaning configuration
# fall back to JSON when PyYAML is unavailable.
def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        config = yaml.safe_load(text)
    except ModuleNotFoundError:
        try:
            config = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CleaningError(
                "PyYAML is not installed and cleaning_config.yaml "
                "is not JSON-compatible."
            ) from exc

    if not isinstance(config, dict):
        raise CleaningError("The configuration root must be an object.")
    _validate_config(config)
    return config


# Validate the configuration shape, timing rules, aggregation, and thresholds.
def _validate_config(config: dict[str, Any]) -> None:
    required_sections = {"input", "output", "time", "quality", "fields"}
    missing_sections = required_sections.difference(config)
    if missing_sections:
        raise CleaningError(
            "Configuration is missing sections: "
            f"{sorted(missing_sections)}"
        )

    fields = config["fields"]
    if not isinstance(fields, dict) or not fields:
        raise CleaningError("'fields' must contain at least one sensor field.")

    required_field_keys = {
        "source_names",
        "unit",
        "missing_strategy",
        "resample_aggregation",
        "physical_min",
        "physical_max",
        "suspicious_min",
        "suspicious_max",
        "suspicious_exact_values",
    }
    allowed_strategies = {"interpolation", "forward_fill", "retain"}
    allowed_aggregations = {"last"}

    for output_name, spec in fields.items():
        missing_keys = required_field_keys.difference(spec)
        if missing_keys:
            raise CleaningError(
                f"Field '{output_name}' is missing configuration "
                f"keys: {sorted(missing_keys)}"
            )
        if spec["missing_strategy"] not in allowed_strategies:
            raise CleaningError(
                f"Field '{output_name}' has an unsupported "
                "missing-value strategy: "
                f"{spec['missing_strategy']}"
            )
        if spec["resample_aggregation"] not in allowed_aggregations:
            raise CleaningError(
                "Only 'last' aggregation is allowed to keep "
                f"timestamps aligned; field '{output_name}' is "
                f"configured as {spec['resample_aggregation']}."
            )
        if spec["physical_min"] > spec["physical_max"]:
            raise CleaningError(
                f"Field '{output_name}' has invalid physical bounds."
            )
        if spec["suspicious_min"] > spec["suspicious_max"]:
            raise CleaningError(
                f"Field '{output_name}' has invalid suspicious bounds."
            )
        if (
            spec["suspicious_min"] < spec["physical_min"]
            or spec["suspicious_max"] > spec["physical_max"]
        ):
            raise CleaningError(
                f"Field '{output_name}' suspicious bounds must stay "
                "within physical bounds."
            )

    segment_gap = config["time"].get("segment_gap_seconds")
    imputation_limit = config["time"].get("imputation_max_seconds")
    if not isinstance(segment_gap, (int, float)) or segment_gap <= 0:
        raise CleaningError("'segment_gap_seconds' must be positive.")
    if not isinstance(imputation_limit, int) or imputation_limit < 0:
        raise CleaningError(
            "'imputation_max_seconds' must be a non-negative integer."
        )
    if imputation_limit >= segment_gap:
        raise CleaningError(
            "The imputation limit must be smaller than the segment "
            "gap threshold."
        )


# Normalize source column names so field matching is stable across encodings.
def normalize_column_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    normalized = (
        normalized.replace("Â°", "°")
        .replace("脗掳", "°")
        .replace("掳", "°")
    )
    return re.sub(r"\s+", " ", normalized)


# Map raw CSV columns to canonical field names and keep a unit audit trail.
def build_column_mapping(
    source_columns: Iterable[str],
    config: dict[str, Any],
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    normalized_sources = {
        normalize_column_name(column): column for column in source_columns
    }
    mapping: dict[str, str] = {}
    audit: dict[str, dict[str, str]] = {}

    time_source = normalize_column_name(config["time"]["source_field"])
    if time_source not in normalized_sources:
        raise CleaningError(
            f"Could not find time field '{config['time']['source_field']}'."
        )
    mapping[normalized_sources[time_source]] = TIMESTAMP_FIELD

    for output_name, spec in config["fields"].items():
        matched_source = next(
            (
                normalized_sources[normalize_column_name(alias)]
                for alias in spec["source_names"]
                if normalize_column_name(alias) in normalized_sources
            ),
            None,
        )
        if matched_source is None:
            raise CleaningError(
                "Could not find a source column for output field "
                f"'{output_name}'; "
                f"accepted names: {spec['source_names']}"
            )
        mapping[matched_source] = output_name
        audit[output_name] = {
            "source_column": matched_source,
            "standard_unit": str(spec["unit"]),
        }

    return mapping, audit


# Parse KIT file names into date, vehicle, route, condition, and metadata.
def parse_filename(path: str | Path) -> TripMetadata:
    tokens = Path(path).stem.split("_")
    if len(tokens) < 6:
        raise CleaningError(
            "File name does not match the KIT naming rule: "
            f"{Path(path).name}"
        )

    date, brand, model, origin, destination = tokens[:5]
    tail = tokens[5:]
    condition_index = next(
        (
            index
            for index, token in enumerate(tail)
            if token in CONDITION_LABELS
        ),
        None,
    )

    if condition_index is None:
        condition = tail[0] if tail else None
        route_sequence = None
        extension_tokens = tail[1:]
    else:
        condition = tail[condition_index]
        route_sequence = "_".join(tail[:condition_index]) or None
        extension_tokens = tail[condition_index + 1:]

    return TripMetadata(
        date=date,
        brand=brand,
        model=model,
        origin=origin,
        destination=destination,
        condition=condition,
        extension="_".join(extension_tokens) or None,
        route_sequence=route_sequence,
    )


# Combine the file-name date and CSV time into timezone-aware timestamps.
def _parse_timestamps(
    time_values: pd.Series,
    trip_date: str,
    timezone: str,
    source_format: str,
) -> pd.DatetimeIndex:
    combined = trip_date + " " + time_values.astype("string").str.strip()
    try:
        naive = pd.to_datetime(
            combined,
            format=f"%Y-%m-%d {source_format}",
            errors="raise",
        )
    except (ValueError, TypeError) as exc:
        raise CleaningError(
            f"Could not parse timestamps for date {trip_date}."
        ) from exc

    try:
        return pd.DatetimeIndex(naive).tz_localize(
            timezone,
            ambiguous="raise",
            nonexistent="raise",
        )
    except (ValueError, TypeError) as exc:
        raise CleaningError(
            f"Could not localize timestamps to timezone '{timezone}'."
        ) from exc


def _format_utc_timestamp(value: Any) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp.strftime(UTC_TIMESTAMP_FORMAT)


# Build a chronological cycle sort key before assigning trip_id values.
def _get_trip_sort_key(
    path: Path,
    config: dict[str, Any],
) -> tuple[pd.Timestamp, str]:
    metadata = parse_filename(path)
    input_config = config["input"]
    time_source = normalize_column_name(config["time"]["source_field"])

    header = pd.read_csv(
        path,
        nrows=0,
        encoding=input_config.get("encoding", "utf-8-sig"),
        delimiter=input_config.get("delimiter", ","),
    )
    normalized_sources = {
        normalize_column_name(column): column for column in header.columns
    }
    time_column = normalized_sources.get(time_source)
    if time_column is None:
        raise CleaningError(
            f"Could not find time field '{config['time']['source_field']}' "
            f"in {path.name}."
        )

    time_values = pd.read_csv(
        path,
        usecols=[time_column],
        encoding=input_config.get("encoding", "utf-8-sig"),
        delimiter=input_config.get("delimiter", ","),
    )[time_column].dropna()
    if time_values.empty:
        raise CleaningError(f"No valid time values found in {path.name}.")

    timestamps = _parse_timestamps(
        time_values,
        metadata.date,
        config["time"]["timezone"],
        config["time"]["source_format"],
    )
    start_timestamp = pd.Timestamp(timestamps.min()).tz_convert("UTC")
    return start_timestamp, path.name


# Count True runs in a boolean mask for missing-value audit summaries.
def _count_true_runs(mask: pd.Series) -> dict[str, int]:
    if mask.empty:
        return {"runs": 0, "max_run": 0}
    groups = mask.ne(mask.shift(fill_value=False)).cumsum()
    lengths = mask[mask].groupby(groups[mask]).size()
    return {
        "runs": int(len(lengths)),
        "max_run": int(lengths.max()) if len(lengths) else 0,
    }


# Fill complete missing runs that are short enough for the configured limit.
def _fill_only_short_missing_runs(
    series: pd.Series,
    strategy: str,
    max_run_length: int,
) -> tuple[pd.Series, pd.Series]:
    original = series.copy()
    missing = original.isna()
    imputed = pd.Series(False, index=series.index, dtype=bool)

    if max_run_length == 0 or strategy == "retain" or not missing.any():
        return original, imputed

    groups = missing.ne(missing.shift(fill_value=False)).cumsum()
    run_lengths = missing.groupby(groups).transform("sum")
    eligible = missing & run_lengths.le(max_run_length)

    if strategy == "interpolation":
        candidate = original.interpolate(method="time", limit_area="inside")
    elif strategy == "forward_fill":
        candidate = original.ffill()
    else:
        raise CleaningError(f"Unsupported missing-value strategy: {strategy}")

    fillable = eligible & candidate.notna()
    result = original.copy()
    result.loc[fillable] = candidate.loc[fillable]
    imputed.loc[fillable] = True
    return result, imputed


# Identify values outside physical bounds and keep source flags.
def _build_hard_invalid_masks(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}
    for field, spec in config["fields"].items():
        masks[field] = frame[field].notna() & ~frame[field].between(
            spec["physical_min"],
            spec["physical_max"],
            inclusive="both",
        )
    return masks


# Mark suspicious operating values from soft bounds and exact sentinel values.
def _build_suspicious_masks(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}
    for field, spec in config["fields"].items():
        values = frame[field]
        range_mask = values.notna() & ~values.between(
            spec["suspicious_min"],
            spec["suspicious_max"],
            inclusive="both",
        )
        exact_values = spec.get("suspicious_exact_values", [])
        exact_mask = values.isin(exact_values) if exact_values else False
        masks[field] = range_mask | exact_mask
    return masks


# Append a quality rule name to the row-level quality_flags string.
def _append_quality_flag(
    quality_flags: pd.Series,
    mask: pd.Series,
    flag_name: str,
    separator: str,
) -> pd.Series:
    if not mask.any():
        return quality_flags
    existing = quality_flags.loc[mask]
    quality_flags.loc[mask] = np.where(
        existing.eq(""),
        flag_name,
        existing + separator + flag_name,
    )
    return quality_flags


# Add cross-field consistency rules that single-field bounds cannot detect.
def _apply_cross_field_quality_rules(
    sampled: pd.DataFrame,
    quality_flags: pd.Series,
    separator: str,
) -> tuple[pd.Series, dict[str, int]]:
    rule_masks = {
        "rpm_zero_while_speed_positive": (
            sampled["rpm"].eq(0) & sampled["speed"].gt(0)
        ),
        "maf_zero_while_rpm_positive": (
            sampled["maf"].eq(0) & sampled["rpm"].gt(0)
        ),
        "coolant_below_zero_in_warm_ambient": (
            sampled["coolant_temp"].lt(0) & sampled["ambient_temp"].gt(5)
        ),
    }
    counts: dict[str, int] = {}
    for rule_name, mask in rule_masks.items():
        counts[rule_name] = int(mask.sum())
        quality_flags = _append_quality_flag(
            quality_flags,
            mask,
            rule_name,
            separator,
        )
    return quality_flags, counts


# Resample one continuous segment to 1 Hz and create quality flags.
def _resample_segment(
    segment: pd.DataFrame,
    config: dict[str, Any],
    trip_id: str,
    segment_number: int,
    metadata: TripMetadata,
    source_file: str,
    source_timestamp_was_monotonic: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fields = list(config["fields"])
    frequency = config["time"]["resample_frequency"]
    imputation_limit = config["time"]["imputation_max_seconds"]
    separator = config["quality"].get("quality_flag_separator", "|")
    indexed = segment.set_index(TIMESTAMP_FIELD)

    aggregations: dict[str, str] = {}
    for field in fields:
        aggregations[field] = config["fields"][field]["resample_aggregation"]
    sampled = indexed[fields].resample(
        frequency,
        origin="start_day",
        label="left",
        closed="left",
    ).agg(aggregations)

    source_sample_count = indexed[fields[0]].resample(
        frequency,
        origin="start_day",
        label="left",
        closed="left",
    ).size()
    sampled["source_sample_count"] = source_sample_count.astype("int32")
    observed_sensor_count = sampled[fields].notna().sum(axis=1)
    sampled["observed_sensor_count"] = observed_sensor_count.astype("int8")

    hard_invalid_columns: dict[str, pd.Series] = {}
    for field in fields:
        raw_flag = indexed[f"_{field}_hard_invalid"].astype("int8")
        hard_invalid_columns[field] = raw_flag.resample(
            frequency,
            origin="start_day",
            label="left",
            closed="left",
        ).max().fillna(0).astype(bool)

    imputed_columns: dict[str, pd.Series] = {}
    for field in fields:
        sampled[field], imputed_columns[field] = _fill_only_short_missing_runs(
            sampled[field],
            config["fields"][field]["missing_strategy"],
            imputation_limit,
        )

    suspicious_columns = _build_suspicious_masks(sampled[fields], config)
    quality_flags = pd.Series("", index=sampled.index, dtype="string")

    for field in fields:
        quality_flags = _append_quality_flag(
            quality_flags,
            hard_invalid_columns[field],
            f"{field}:hard_invalid_source",
            separator,
        )
        quality_flags = _append_quality_flag(
            quality_flags,
            suspicious_columns[field],
            f"{field}:suspicious",
            separator,
        )

    quality_flags, cross_field_counts = _apply_cross_field_quality_rules(
        sampled,
        quality_flags,
        separator,
    )

    sampled["source_file"] = source_file
    sampled["trip_id"] = trip_id
    sampled["segment_id"] = f"{trip_id}_seg_{segment_number:03d}"
    sampled["row_in_segment"] = np.arange(1, len(sampled) + 1, dtype=np.int32)
    sampled["brand"] = metadata.brand
    sampled["model"] = metadata.model
    sampled["origin"] = metadata.origin
    sampled["destination"] = metadata.destination
    sampled["route"] = metadata.route
    sampled["condition"] = metadata.condition
    sampled["route_sequence"] = metadata.route_sequence
    sampled["source_extension"] = metadata.extension
    sampled["source_timestamp_was_monotonic"] = source_timestamp_was_monotonic

    for field in fields:
        if config["quality"].get("keep_field_imputation_flags", True):
            sampled[f"{field}_is_imputed"] = imputed_columns[field]
        if config["quality"].get("keep_field_suspicious_flags", True):
            sampled[f"{field}_is_suspicious"] = suspicious_columns[field]
        if config["quality"].get("keep_field_hard_invalid_flags", True):
            hard_invalid_name = f"{field}_had_hard_invalid_source"
            sampled[hard_invalid_name] = hard_invalid_columns[field]

    sampled["is_imputed_any"] = pd.concat(imputed_columns, axis=1).any(axis=1)
    sampled["is_suspicious_any"] = pd.concat(
        suspicious_columns,
        axis=1,
    ).any(axis=1)
    sampled["had_hard_invalid_source_any"] = pd.concat(
        hard_invalid_columns,
        axis=1,
    ).any(axis=1)
    sampled["quality_flags"] = quality_flags

    segment_report = {
        "segment_id": f"{trip_id}_seg_{segment_number:03d}",
        "input_rows": int(len(segment)),
        "output_rows": int(len(sampled)),
        "start_timestamp": _format_utc_timestamp(sampled.index.min()),
        "end_timestamp": _format_utc_timestamp(sampled.index.max()),
        "source_sample_count_min": int(sampled["source_sample_count"].min()),
        "source_sample_count_max": int(sampled["source_sample_count"].max()),
        "imputed_values": {
            field: int(imputed_columns[field].sum()) for field in fields
        },
        "suspicious_values": {
            field: int(suspicious_columns[field].sum()) for field in fields
        },
        "hard_invalid_source_bins": {
            field: int(hard_invalid_columns[field].sum()) for field in fields
        },
        "cross_field_quality_flags": cross_field_counts,
    }
    return sampled, segment_report


# Clean one raw CSV, assign trip_id, segment gaps, and resample segments.
def clean_file(
    csv_path: str | Path,
    config: dict[str, Any],
    trip_number: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = Path(csv_path)
    metadata = parse_filename(path)
    trip_id = f"trip_{trip_number:04d}"
    input_config = config["input"]

    raw = pd.read_csv(
        path,
        encoding=input_config.get("encoding", "utf-8-sig"),
        sep=input_config.get("delimiter", ","),
        low_memory=False,
    )
    if raw.empty:
        raise CleaningError(f"Input file is empty: {path.name}")

    mapping, unit_audit = build_column_mapping(raw.columns, config)
    fields = list(config["fields"])
    frame = raw.rename(columns=mapping)[[TIMESTAMP_FIELD, *fields]].copy()
    frame[TIMESTAMP_FIELD] = _parse_timestamps(
        frame[TIMESTAMP_FIELD],
        metadata.date,
        config["time"]["timezone"],
        config["time"]["source_format"],
    )

    numeric_conversion_failures: dict[str, int] = {}
    for field in fields:
        original_non_missing = frame[field].notna()
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        numeric_conversion_failures[field] = int(
            (original_non_missing & frame[field].isna()).sum()
        )

    original_rows = len(frame)
    timestamp_was_monotonic = bool(
        frame[TIMESTAMP_FIELD].is_monotonic_increasing
    )
    frame = frame.sort_values(TIMESTAMP_FIELD, kind="stable")
    duplicate_mask = frame.duplicated(TIMESTAMP_FIELD, keep=False)
    duplicate_rows = int(duplicate_mask.sum())
    frame = frame.drop_duplicates(
        TIMESTAMP_FIELD,
        keep=config["time"].get("duplicate_keep", "last"),
    ).reset_index(drop=True)

    hard_invalid_masks = _build_hard_invalid_masks(frame, config)
    hard_invalid_counts: dict[str, int] = {}
    for field in fields:
        frame[f"_{field}_hard_invalid"] = hard_invalid_masks[field]
        hard_invalid_counts[field] = int(hard_invalid_masks[field].sum())
        frame.loc[hard_invalid_masks[field], field] = np.nan

    gap_seconds = frame[TIMESTAMP_FIELD].diff().dt.total_seconds()
    max_raw_gap = (
        float(gap_seconds.max()) if gap_seconds.notna().any() else 0.0
    )
    segment_gap = config["time"]["segment_gap_seconds"]
    frame["_segment_number"] = gap_seconds.gt(segment_gap).cumsum() + 1

    segment_outputs: list[pd.DataFrame] = []
    segment_reports: list[dict[str, Any]] = []
    for segment_number, segment in frame.groupby("_segment_number", sort=True):
        sampled, segment_report = _resample_segment(
            segment,
            config,
            trip_id,
            int(segment_number),
            metadata,
            path.name,
            timestamp_was_monotonic,
        )
        segment_outputs.append(sampled)
        segment_reports.append(segment_report)

    cleaned = pd.concat(segment_outputs).sort_index(kind="stable")
    cleaned = cleaned.reset_index(names=TIMESTAMP_FIELD)
    cleaned[TIMESTAMP_FIELD] = cleaned[TIMESTAMP_FIELD].map(
        _format_utc_timestamp
    )

    missing_summary = {
        field: {
            "count": int(cleaned[field].isna().sum()),
            **_count_true_runs(cleaned[field].isna()),
        }
        for field in fields
    }
    report = {
        "source_file": path.name,
        "trip_id": trip_id,
        "metadata": asdict(metadata) | {"route": metadata.route},
        "input_rows": int(original_rows),
        "deduplicated_rows": int(len(frame)),
        "output_rows": int(len(cleaned)),
        "timestamp_was_monotonic": timestamp_was_monotonic,
        "duplicate_timestamp_rows": duplicate_rows,
        "continuous_segments": int(frame["_segment_number"].nunique()),
        "max_raw_gap_seconds": round(max_raw_gap, 6),
        "unit_audit": unit_audit,
        "numeric_conversion_failures": numeric_conversion_failures,
        "physical_invalid_values_removed": hard_invalid_counts,
        "remaining_missing": missing_summary,
        "segments": segment_reports,
    }
    return cleaned, report


# Discover raw CSV files recursively and exclude generated cleaning outputs.
def discover_input_files(
    config: dict[str, Any],
    repo_root: str | Path,
) -> list[Path]:
    repo_root = Path(repo_root).resolve()
    directory = Path(config["input"]["directory"]).expanduser()
    if not directory.is_absolute():
        directory = repo_root / directory
    if not directory.exists():
        raise CleaningError(
            f"Raw data directory does not exist: {directory.resolve()}. "
            "Unpack the official dataset there or pass --input-dir."
        )

    pattern = config["input"].get("glob", "**/*.csv")
    generated_prefixes = (
        "cleaned_dataset",
        "cleaning_enriched",
        "cleaning_quality",
    )
    paths = sorted(
        (
            path
            for path in directory.glob(pattern)
            if path.is_file() and not path.name.startswith(generated_prefixes)
        ),
        key=lambda path: _get_trip_sort_key(path, config),
    )
    if not paths:
        raise CleaningError(
            f"No raw CSV files were found in: {directory.resolve()}"
        )
    return paths


# Define the model-input columns for baseline/TTM runs.
def build_output_columns(config: dict[str, Any]) -> list[str]:
    fields = list(config["fields"])
    return [
        TIMESTAMP_FIELD,
        "trip_id",
        "segment_id",
        "row_in_segment",
        *fields,
    ]


# Define the quality-audit columns with lineage, imputation, and anomaly flags.
def build_quality_output_columns(config: dict[str, Any]) -> list[str]:
    fields = list(config["fields"])
    metadata_columns = [
        TIMESTAMP_FIELD,
        "trip_id",
        "segment_id",
        "row_in_segment",
        "source_file",
        "brand",
        "model",
        "origin",
        "destination",
        "route",
        "condition",
        "route_sequence",
        "source_extension",
        "source_timestamp_was_monotonic",
        "source_sample_count",
        "observed_sensor_count",
    ]
    quality_columns: list[str] = []
    for field in fields:
        if config["quality"].get("keep_field_imputation_flags", True):
            quality_columns.append(f"{field}_is_imputed")
        if config["quality"].get("keep_field_suspicious_flags", True):
            quality_columns.append(f"{field}_is_suspicious")
        if config["quality"].get("keep_field_hard_invalid_flags", True):
            quality_columns.append(f"{field}_had_hard_invalid_source")

    return [
        *metadata_columns,
        *quality_columns,
        "is_imputed_any",
        "is_suspicious_any",
        "had_hard_invalid_source_any",
        "quality_flags",
    ]


# Summarize file-level and segment-level audit data for a reproducible report.
def build_global_report(
    combined: pd.DataFrame,
    file_reports: list[dict[str, Any]],
    config: dict[str, Any],
    input_paths: list[Path],
    input_directory: Path,
    output_target: Path,
) -> dict[str, Any]:
    fields = list(config["fields"])
    key_columns = ["trip_id", "segment_id", TIMESTAMP_FIELD]
    duplicate_key_rows = int(
        combined.duplicated(key_columns, keep=False).sum()
    )
    segment_diffs = (
        combined.assign(
            _parsed_timestamp=pd.to_datetime(
                combined[TIMESTAMP_FIELD],
                utc=True,
                errors="raise",
            )
        )
        .groupby("segment_id", sort=False)["_parsed_timestamp"]
        .diff()
        .dt.total_seconds()
    )

    return {
        "pipeline_version": config.get("version"),
        "input_directory": str(input_directory.resolve()),
        "output_csv": str(output_target.resolve()),
        "files_processed": len(input_paths),
        "input_rows": int(sum(item["input_rows"] for item in file_reports)),
        "output_rows": int(len(combined)),
        "output_columns": list(combined.columns),
        "timezone": config["time"]["timezone"],
        "output_timezone": "UTC",
        "timestamp_format": UTC_TIMESTAMP_FORMAT,
        "trip_id_ordering": (
            "chronological_by_filename_date_then_in_file_start_time"
        ),
        "resample_frequency": config["time"]["resample_frequency"],
        "segment_gap_seconds": config["time"]["segment_gap_seconds"],
        "imputation_max_seconds": config["time"]["imputation_max_seconds"],
        "trips": int(combined["trip_id"].nunique()),
        "segments": int(combined["segment_id"].nunique()),
        "duplicate_composite_key_rows": duplicate_key_rows,
        "non_one_second_diffs_inside_segments": int(
            segment_diffs.dropna().ne(1).sum()
        ),
        "physical_invalid_values_removed": {
            field: int(
                sum(
                    report["physical_invalid_values_removed"][field]
                    for report in file_reports
                )
            )
            for field in fields
        },
        "imputed_values": {
            field: int(combined[f"{field}_is_imputed"].sum())
            for field in fields
        },
        "suspicious_values": {
            field: int(combined[f"{field}_is_suspicious"].sum())
            for field in fields
        },
        "remaining_missing": {
            field: int(combined[field].isna().sum()) for field in fields
        },
        "rows_with_any_imputation": int(combined["is_imputed_any"].sum()),
        "rows_with_any_suspicious_value": int(
            combined["is_suspicious_any"].sum()
        ),
        "rows_with_hard_invalid_source": int(
            combined["had_hard_invalid_source_any"].sum()
        ),
        "files": file_reports,
    }


# Run the full dataset cleaning flow and return the enriched in-memory result.
def clean_dataset_enriched(
    config: dict[str, Any],
    repo_root: str | Path,
    output_target: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = discover_input_files(config, repo_root)
    input_directory = (
        paths[0].parent if paths else Path(config["input"]["directory"])
    )
    cleaned_trips: list[pd.DataFrame] = []
    file_reports: list[dict[str, Any]] = []

    for trip_number, path in enumerate(paths, start=1):
        LOGGER.info("Cleaning %d/%d: %s", trip_number, len(paths), path.name)
        cleaned, report = clean_file(path, config, trip_number)
        cleaned_trips.append(cleaned)
        file_reports.append(report)

    enriched = pd.concat(cleaned_trips, ignore_index=True)
    enriched = (
        enriched.assign(
            _sort_timestamp=pd.to_datetime(
                enriched[TIMESTAMP_FIELD],
                utc=True,
                errors="raise",
            )
        )
        .sort_values(
            ["_sort_timestamp", "trip_id", "segment_id", "row_in_segment"],
            kind="stable",
        )
        .drop(columns="_sort_timestamp")
        .reset_index(drop=True)
    )

    summary = build_global_report(
        enriched,
        file_reports,
        config,
        paths,
        input_directory,
        Path(output_target),
    )
    summary["enriched_rows"] = int(len(enriched))
    summary["enriched_columns"] = list(enriched.columns)
    summary["model_output_columns"] = build_output_columns(config)
    summary["quality_output_columns"] = build_quality_output_columns(config)
    return enriched, summary
