"""Validate the two authoritative upstream inputs for Feature Script 00."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.pipeline_data.continuity import (  # noqa: E402
    build_continuity_blocks,
)
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    ManifestError,
    build_stage_manifest,
    compute_source_dataset_identity,
    load_json_object,
    validate_stage_manifest,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "00"
ISO_8601_UTC_SECONDS = "%Y-%m-%dT%H:%M:%SZ"
ISO_8601_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)
TRIP_ID_PATTERN = re.compile(r"^trip_(\d{4,})$")

KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
SIGNAL_COLUMNS = [
    "coolant_temp",
    "map",
    "rpm",
    "speed",
    "intake_temp",
    "maf",
    "tps",
    "ambient_temp",
    "accel_pedal_d",
    "accel_pedal_e",
]
OPERATING_CONTEXT_COLUMNS = [
    "dt_seconds",
    "thermal_state",
    "child_state",
    "operating_state",
    "condition_confidence",
    "condition_quality_flags",
]
PROVENANCE_COLUMNS = [
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
QUALITY_SUFFIXES = [
    "is_imputed",
    "is_suspicious",
    "had_hard_invalid_source",
]
PER_SIGNAL_QUALITY_COLUMNS = [
    f"{signal}_{suffix}"
    for signal in SIGNAL_COLUMNS
    for suffix in QUALITY_SUFFIXES
]
AGGREGATE_QUALITY_COLUMNS = [
    "is_imputed_any",
    "is_suspicious_any",
    "had_hard_invalid_source_any",
    "quality_flags",
]
QUALITY_COLUMNS = [
    *KEY_COLUMNS,
    *PROVENANCE_COLUMNS,
    *PER_SIGNAL_QUALITY_COLUMNS,
    *AGGREGATE_QUALITY_COLUMNS,
]

EXPECTED_KEY_CONTRACT = [
    ("timestamp", "datetime64[ns, UTC]", "UTC", False),
    ("trip_id", "string", "identifier", False),
    ("segment_id", "string", "identifier", False),
    ("row_in_segment", "int64", "1-based row index", False),
]
EXPECTED_CONTEXT_CONTRACT = [
    ("dt_seconds", "float64", "s", False),
    ("thermal_state", "string", "categorical", False),
    ("child_state", "string", "categorical", False),
    ("operating_state", "string", "categorical", False),
    ("condition_confidence", "string", "categorical", False),
    (
        "condition_quality_flags",
        "string",
        "categorical_flags",
        False,
    ),
    ("coolant_temp", "float64", "degC", True),
    ("map", "float64", "kPa", True),
    ("rpm", "float64", "rpm", True),
    ("speed", "float64", "km/h", True),
    ("intake_temp", "float64", "degC", True),
    ("maf", "float64", "g/s", True),
    ("tps", "float64", "percent", True),
    ("ambient_temp", "float64", "degC", True),
    ("accel_pedal_d", "float64", "percent", True),
    ("accel_pedal_e", "float64", "percent", True),
]


class InputContractError(RuntimeError):
    """Raised when Script 00 cannot validate an upstream input contract."""


@dataclass(frozen=True, slots=True)
class ValidatedInputs:
    """Canonical and quality inputs aligned to the frozen global row order."""

    canonical: pd.DataFrame
    quality: pd.DataFrame
    ordered_keys: pd.DataFrame
    ordered_sample_keys_sha256: str
    trip_count: int
    segment_count: int
    continuity_block_count: int
    ignored_operating_input_columns: tuple[str, ...]


def _read_csv_strict(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise InputContractError(f"Required input CSV does not exist: {path}.")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle), None)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InputContractError(
            f"Cannot read CSV header from {path}: {exc}") from exc
    if not header:
        raise InputContractError(f"Input CSV has no header: {path}.")
    duplicates = sorted({name for name in header if header.count(name) > 1})
    if duplicates:
        raise InputContractError(
            f"Input CSV contains duplicate columns {duplicates}: {path}."
        )
    try:
        return pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise InputContractError(
            f"Cannot parse input CSV {path}: {exc}") from exc


def _require_columns(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    input_name: str,
) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise InputContractError(
            f"{input_name} is missing required columns: {missing}."
        )


def _normalize_timestamp(
    series: pd.Series,
    *,
    input_name: str,
) -> tuple[pd.Series, pd.Series]:
    if series.isna().any():
        raise InputContractError(
            f"{input_name}.timestamp contains null values.")
    text = series.astype("string")
    invalid_format = ~text.str.fullmatch(ISO_8601_UTC_PATTERN)
    if invalid_format.any():
        examples = text.loc[invalid_format].drop_duplicates().head(3).tolist()
        raise InputContractError(
            f"{input_name}.timestamp must use YYYY-MM-DDTHH:MM:SSZ; "
            f"invalid examples: {examples}."
        )
    parsed = pd.to_datetime(text, utc=True, errors="coerce")
    if parsed.isna().any():
        raise InputContractError(
            f"{input_name}.timestamp contains invalid calendar timestamps."
        )
    normalized = parsed.dt.strftime(ISO_8601_UTC_SECONDS)
    return normalized, parsed


def _coerce_numeric(
    frame: pd.DataFrame,
    column: str,
    *,
    input_name: str,
    nullable: bool,
) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    invalid = frame[column].notna() & values.isna()
    if invalid.any() or (not nullable and values.isna().any()):
        raise InputContractError(
            f"{input_name}.{column} violates its numeric/nullability contract."
        )
    return values.astype(float)


def _coerce_boolean(
    series: pd.Series,
    *,
    label: str,
) -> pd.Series:
    mapping = {
        True: True,
        False: False,
        1: True,
        0: False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    normalized = series.map(
        lambda value: mapping.get(
            value.strip().casefold() if isinstance(value, str) else value,
            pd.NA,
        )
    ).astype("boolean")
    if normalized.isna().any():
        examples = series.loc[normalized.isna()].astype(str).head(3).tolist()
        raise InputContractError(
            f"{label} must be non-null boolean values; invalid examples: "
            f"{examples}."
        )
    return normalized.astype(bool)


def _validate_feature_contract(contract: dict[str, Any]) -> None:
    if contract.get("manifest_type") != "production_feature_contract":
        raise InputContractError("Unexpected feature contract manifest_type.")
    if contract.get("status") != "frozen":
        raise InputContractError("Feature contract must have frozen status.")
    if contract.get("schema_version") != "feature_schema.v1":
        raise InputContractError("Script 00 requires feature_schema.v1.")

    upstream = contract.get("upstream_input_contract", {})
    expected_authorities = [
        (
            "operating_condition_enriched",
            "operating_conditions/operating_condition_enriched.csv",
        ),
        ("cleaning_quality", "cleaning/cleaning_quality.csv"),
    ]
    received_authorities = [
        (item.get("id"), item.get("run_relative_path"))
        for item in upstream.get("authoritative_inputs", [])
        if isinstance(item, dict)
    ]
    input_count_ok = upstream.get("input_count") == 2
    authorities_ok = received_authorities == expected_authorities
    if not input_count_ok or not authorities_ok:
        raise InputContractError(
            "Feature contract must declare exactly the two frozen Script 00 "
            "authoritative inputs in order."
        )
    if upstream.get("join_keys") != KEY_COLUMNS:
        raise InputContractError("Feature contract join keys have drifted.")
    if upstream.get("timestamp_normalization") != "UTC":
        raise InputContractError(
            "Feature contract timestamp normalization is not UTC.")
    for flag in (
        "one_to_one_key_equality_required",
        "input_sha256_required",
        "source_dataset_identity_required",
        "additional_script_00_authorities_forbidden",
    ):
        if upstream.get(flag) is not True:
            raise InputContractError(f"Feature contract must set {flag}=true.")

    keys = contract.get("sample_keys", [])
    contexts = contract.get("context_fields", [])
    actual_keys = [
        (
            item.get("name"),
            item.get("dtype"),
            item.get("unit"),
            item.get("nullable"),
        )
        for item in keys
    ]
    actual_contexts = [
        (
            item.get("name"),
            item.get("dtype"),
            item.get("unit"),
            item.get("nullable"),
        )
        for item in contexts
    ]
    if actual_keys != EXPECTED_KEY_CONTRACT:
        raise InputContractError("Frozen sample-key contract has drifted.")
    if actual_contexts != EXPECTED_CONTEXT_CONTRACT:
        raise InputContractError(
            "Frozen A-class context/raw contract has drifted.")


def _validate_operating_input(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    input_name = "operating_condition_enriched"
    required = [*KEY_COLUMNS, *SIGNAL_COLUMNS, *OPERATING_CONTEXT_COLUMNS]
    _require_columns(frame, required, input_name=input_name)
    frame = frame.copy()
    frame["timestamp"], _ = _normalize_timestamp(
        frame["timestamp"], input_name=input_name
    )

    for column in ("trip_id", "segment_id"):
        values = frame[column].astype("string")
        if values.isna().any() or values.str.strip().eq("").any():
            raise InputContractError(
                f"{input_name}.{column} must be non-empty strings."
            )
        frame[column] = values

    row_numbers = pd.to_numeric(frame["row_in_segment"], errors="coerce")
    if (
        row_numbers.isna().any()
        or row_numbers.mod(1).ne(0).any()
        or row_numbers.lt(1).any()
    ):
        raise InputContractError(
            "operating_condition_enriched.row_in_segment must be "
            "positive integers."
        )
    frame["row_in_segment"] = row_numbers.astype("int64")

    frame["dt_seconds"] = _coerce_numeric(
        frame,
        "dt_seconds",
        input_name=input_name,
        nullable=False,
    )
    if not frame["dt_seconds"].eq(1.0).all():
        raise InputContractError(
            "Canonical 1 Hz input requires dt_seconds == 1.0.")
    for signal in SIGNAL_COLUMNS:
        frame[signal] = _coerce_numeric(
            frame,
            signal,
            input_name=input_name,
            nullable=True,
        )

    allowed = {
        "thermal_state": {"engine_off", "warmup", "post_warmup", "unknown"},
        "child_state": {
            "inactive_engine_off",
            "idle",
            "high_load",
            "acceleration",
            "deceleration",
            "steady_driving",
            "unknown",
        },
        "condition_confidence": {"high", "medium", "low"},
    }
    for column, values_allowed in allowed.items():
        values = frame[column].astype("string")
        has_null = values.isna().any()
        has_unsupported = not set(values.unique()).issubset(values_allowed)
        if has_null or has_unsupported:
            raise InputContractError(
                f"{input_name}.{column} contains null or unsupported values."
            )
        frame[column] = values

    thermal = frame["thermal_state"]
    child = frame["child_state"]
    expected_combined = thermal + "__" + child
    valid_operating_state = (
        frame["operating_state"].astype(
            "string").isin({"engine_off", "unknown"})
        | frame["operating_state"].astype("string").eq(expected_combined)
    )
    if not valid_operating_state.all():
        raise InputContractError(
            "operating_condition_enriched.operating_state is inconsistent "
            "with thermal_state/child_state."
        )
    frame["operating_state"] = frame["operating_state"].astype("string")

    allowed_flags = {
        "MISSING_ECT", "MISSING_MAF", "MISSING_RPM", "MISSING_SPEED",
    }
    quality_flags = frame["condition_quality_flags"].astype("string")
    invalid_flags = quality_flags.isna() | ~quality_flags.map(
        lambda value: value == "OK" or set(
            value.split("|")).issubset(allowed_flags)
    )
    if invalid_flags.any():
        raise InputContractError(
            "operating_condition_enriched.condition_quality_flags is invalid."
        )
    frame["condition_quality_flags"] = quality_flags
    canonical_columns = [
        *KEY_COLUMNS,
        *[name for name, *_ in EXPECTED_CONTEXT_CONTRACT],
    ]
    return frame[canonical_columns]


def _validate_quality_input(frame: pd.DataFrame) -> pd.DataFrame:
    input_name = "cleaning_quality"
    _require_columns(frame, QUALITY_COLUMNS, input_name=input_name)
    frame = frame.copy()
    frame["timestamp"], _ = _normalize_timestamp(
        frame["timestamp"], input_name=input_name
    )
    for column in ("trip_id", "segment_id", "source_file"):
        values = frame[column].astype("string")
        if values.isna().any() or values.str.strip().eq("").any():
            raise InputContractError(
                f"{input_name}.{column} must be non-empty strings."
            )
        frame[column] = values

    for column in (
        "brand",
        "model",
        "origin",
        "destination",
        "route",
        "condition",
    ):
        values = frame[column].astype("string")
        if values.isna().any() or values.str.strip().eq("").any():
            raise InputContractError(
                f"{input_name}.{column} must be non-empty strings."
            )
        frame[column] = values
    for column in ("route_sequence", "source_extension", "quality_flags"):
        frame[column] = frame[column].astype("string")

    row_numbers = pd.to_numeric(frame["row_in_segment"], errors="coerce")
    if (
        row_numbers.isna().any()
        or row_numbers.mod(1).ne(0).any()
        or row_numbers.lt(1).any()
    ):
        raise InputContractError(
            "cleaning_quality.row_in_segment must be positive integers."
        )
    frame["row_in_segment"] = row_numbers.astype("int64")

    boolean_columns = [
        "source_timestamp_was_monotonic",
        *PER_SIGNAL_QUALITY_COLUMNS,
        "is_imputed_any",
        "is_suspicious_any",
        "had_hard_invalid_source_any",
    ]
    for column in boolean_columns:
        frame[column] = _coerce_boolean(
            frame[column], label=f"{input_name}.{column}"
        )
    for column in ("source_sample_count", "observed_sensor_count"):
        values = pd.to_numeric(frame[column], errors="coerce")
        is_non_integer = values.mod(1).ne(0).any()
        is_negative = values.lt(0).any()
        if values.isna().any() or is_non_integer or is_negative:
            raise InputContractError(
                f"{input_name}.{column} must be non-negative integers."
            )
        frame[column] = values.astype("int64")
    if frame["observed_sensor_count"].gt(len(SIGNAL_COLUMNS)).any():
        raise InputContractError(
            "cleaning_quality.observed_sensor_count exceeds the signal "
            "contract."
        )

    aggregate_pairs = {
        "is_imputed_any": [
            f"{signal}_is_imputed" for signal in SIGNAL_COLUMNS
        ],
        "is_suspicious_any": [
            f"{signal}_is_suspicious" for signal in SIGNAL_COLUMNS
        ],
        "had_hard_invalid_source_any": [
            f"{signal}_had_hard_invalid_source" for signal in SIGNAL_COLUMNS
        ],
    }
    for aggregate, detail_columns in aggregate_pairs.items():
        expected = frame[detail_columns].any(axis=1)
        if not frame[aggregate].equals(expected):
            raise InputContractError(
                f"cleaning_quality.{aggregate} disagrees with "
                "per-signal flags."
            )
    return frame[QUALITY_COLUMNS]


def _reject_duplicate_keys(frame: pd.DataFrame, *, input_name: str) -> None:
    if frame[KEY_COLUMNS].isna().any().any():
        raise InputContractError(f"{input_name} contains null sample keys.")
    duplicate = frame.duplicated(KEY_COLUMNS, keep=False)
    if duplicate.any():
        raise InputContractError(
            f"{input_name} contains {int(duplicate.sum())} rows with "
            "duplicate sample keys."
        )


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_trip_and_segment_contract(
    canonical: pd.DataFrame,
    quality: pd.DataFrame,
) -> tuple[int, int, int]:
    trip_to_source = quality.groupby("trip_id", sort=False)[
                                     "source_file"].nunique()
    source_to_trip = quality.groupby("source_file", sort=False)[
                                     "trip_id"].nunique()
    if not trip_to_source.eq(1).all() or not source_to_trip.eq(1).all():
        raise InputContractError(
            "Trip/source-file identity must be strictly one-to-one."
        )

    parsed = pd.to_datetime(canonical["timestamp"], utc=True, errors="raise")
    trip_summary = pd.DataFrame(
        {
            "trip_id": canonical["trip_id"],
            "timestamp": parsed,
            "source_file": quality["source_file"],
        }
    ).groupby("trip_id", as_index=False).agg(
        trip_start_timestamp_utc=("timestamp", "min"),
        source_file=("source_file", "first"),
    )
    extracted = trip_summary["trip_id"].str.extract(
        TRIP_ID_PATTERN, expand=False)
    if extracted.isna().any():
        raise InputContractError(
            "trip_id must use trip_<zero-padded ordinal> format.")
    trip_summary["ordinal"] = extracted.astype(int)
    expected_order = trip_summary.sort_values(
        ["trip_start_timestamp_utc", "source_file"], kind="stable"
    )
    expected_ordinals = list(range(1, len(expected_order) + 1))
    if expected_order["ordinal"].tolist() != expected_ordinals:
        raise InputContractError(
            "trip_id assignment does not match chronological "
            "source-file order."
        )

    segment_owner_count = canonical.groupby("segment_id")["trip_id"].nunique()
    if not segment_owner_count.eq(1).all():
        raise InputContractError(
            "A segment_id must belong to exactly one trip_id.")
    within = canonical.sort_values(
        ["trip_id", "segment_id", "row_in_segment"], kind="stable"
    ).copy()
    expected_rows = within.groupby(
        ["trip_id", "segment_id"], sort=False
    ).cumcount().add(1)
    if not within["row_in_segment"].reset_index(drop=True).equals(
        expected_rows.reset_index(drop=True).astype("int64")
    ):
        raise InputContractError(
            "row_in_segment must be 1-based and strictly consecutive."
        )
    within["_timestamp"] = pd.to_datetime(within["timestamp"], utc=True)
    timestamp_diff = within.groupby(
        ["trip_id", "segment_id"], sort=False
    )["_timestamp"].diff().dt.total_seconds().dropna()
    if not timestamp_diff.eq(1.0).all():
        raise InputContractError(
            "Timestamps must be strictly consecutive at 1 Hz within segments."
        )

    continuity = build_continuity_blocks(canonical)
    segment_count = int(
        canonical[["trip_id", "segment_id"]].drop_duplicates().shape[0]
    )
    continuity_blocks = int(continuity.block_id.nunique())
    if continuity_blocks != segment_count:
        raise InputContractError(
            "Restored global order does not keep each segment in one "
            "continuous block."
        )
    return int(len(trip_summary)), segment_count, continuity_blocks


def validate_authoritative_inputs(
    run_layout: RunLayout,
    feature_contract: dict[str, Any],
) -> ValidatedInputs:
    """Validate and align both authoritative inputs without writing output."""

    _validate_feature_contract(feature_contract)
    operating_raw = _read_csv_strict(run_layout.operating_condition_enriched)
    quality_raw = _read_csv_strict(run_layout.cleaning_quality)
    operating = _validate_operating_input(operating_raw)
    quality = _validate_quality_input(quality_raw)
    _reject_duplicate_keys(
        operating, input_name="operating_condition_enriched")
    _reject_duplicate_keys(quality, input_name="cleaning_quality")

    comparison = operating[KEY_COLUMNS].merge(
        quality[KEY_COLUMNS],
        on=KEY_COLUMNS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    mismatched = comparison["_merge"].ne("both")
    if mismatched.any():
        counts = comparison.loc[mismatched, "_merge"].value_counts().to_dict()
        raise InputContractError(
            f"Authoritative input sample-key sets differ: {counts}."
        )

    ordered_keys = comparison[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    canonical = ordered_keys.merge(
        operating,
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    quality_aligned = ordered_keys.merge(
        quality,
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if not canonical[KEY_COLUMNS].equals(quality_aligned[KEY_COLUMNS]):
        raise InputContractError(
            "One-to-one key alignment failed unexpectedly.")

    trip_count, segment_count, continuity_blocks = (
        _validate_trip_and_segment_contract(canonical, quality_aligned)
    )
    return ValidatedInputs(
        canonical=canonical,
        quality=quality_aligned,
        ordered_keys=ordered_keys,
        ordered_sample_keys_sha256=_ordered_key_sha256(ordered_keys),
        trip_count=trip_count,
        segment_count=segment_count,
        continuity_block_count=continuity_blocks,
        ignored_operating_input_columns=tuple(
            column
            for column in operating_raw.columns
            if column not in operating.columns
        ),
    )


def _descriptor(
    path: Path,
    *,
    artifact_id: str,
    manifest_path: str,
    path_base: str,
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path,
        artifact_id=artifact_id,
        manifest_path=manifest_path,
        path_base=path_base,
    )


def run_input_contract_validation(
    run_layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> tuple[ValidatedInputs, dict[str, Any]]:
    """Validate Script 00 inputs and atomically write its stage manifest."""

    feature_contract = load_json_object(run_layout.feature_contract)
    validated = validate_authoritative_inputs(run_layout, feature_contract)

    contract_descriptor = _descriptor(
        run_layout.feature_contract,
        artifact_id="feature_contract",
        manifest_path="data_layer/contracts/feature_manifest.v1.json",
        path_base="repo_root",
    )
    operating_descriptor = _descriptor(
        run_layout.operating_condition_enriched,
        artifact_id="operating_condition_enriched",
        manifest_path=run_layout.run_relative_posix(
            run_layout.operating_condition_enriched
        ),
        path_base="run_dir",
    )
    quality_descriptor = _descriptor(
        run_layout.cleaning_quality,
        artifact_id="cleaning_quality",
        manifest_path=run_layout.run_relative_posix(
            run_layout.cleaning_quality),
        path_base="run_dir",
    )
    source_dataset_identity = compute_source_dataset_identity(
        [operating_descriptor, quality_descriptor]
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=feature_contract["schema_version"],
        script_version=SCRIPT_VERSION,
        source_dataset_identity=source_dataset_identity,
        input_artifacts=[
            contract_descriptor,
            operating_descriptor,
            quality_descriptor,
        ],
        output_artifacts=[],
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    manifest["validation_summary"] = {
        "authoritative_input_count": 2,
        "row_count": int(len(validated.ordered_keys)),
        "trip_count": validated.trip_count,
        "segment_count": validated.segment_count,
        "continuity_block_count": validated.continuity_block_count,
        "timestamp_format": "YYYY-MM-DDTHH:MM:SSZ",
        "timestamp_timezone": "UTC",
        "join_cardinality": "one_to_one",
        "global_sort_keys": KEY_COLUMNS,
        "ordered_sample_keys_sha256": validated.ordered_sample_keys_sha256,
        "canonical_column_order": list(validated.canonical.columns),
        "quality_column_order": list(validated.quality.columns),
        "ignored_operating_input_columns": list(
            validated.ignored_operating_input_columns
        ),
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=feature_contract["schema_version"],
        expected_calibration_version="not_applicable",
    )
    write_json_atomic(run_layout.input_contract_manifest, manifest)
    return validated, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the two authoritative Feature Script 00 inputs."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Explicit run directory under data/processed/runs/<run_id>.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        run_layout = RunLayout.from_run_dir(
            args.run_dir,
            repo_root=PROJECT_ROOT,
        )
        validated, manifest = run_input_contract_validation(run_layout)
    except (
        InputContractError,
        ManifestError,
        OSError,
        KeyError,
        ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "manifest": run_layout.run_relative_posix(
                    run_layout.input_contract_manifest
                ),
                "rows": int(len(validated.ordered_keys)),
                "trips": validated.trip_count,
                "segments": validated.segment_count,
                "source_dataset_identity": manifest[
                    "source_dataset_identity"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
