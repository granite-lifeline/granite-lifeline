"""Assemble the strict 46-column production feature handoff for Script 41."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.pipeline_data.manifests import (
    ArtifactDescriptor,
    ManifestError,
    ManifestValidationError,
    build_stage_manifest,
    load_json_object,
    ordered_column_contract_from_feature_manifest,
    validate_ordered_column_contract,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "41"
SCHEMA_VERSION = "feature_schema.v1"
CALIBRATION_VERSION = "calibration.v1"
KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ProductionAssemblyError(RuntimeError):
    """Raised when an input or final handoff violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class ProductionInputs:
    canonical: pd.DataFrame
    atomic: pd.DataFrame
    engine_start_context: pd.DataFrame
    engine_start_episodes: pd.DataFrame
    windows: pd.DataFrame
    calibrated: pd.DataFrame
    feature_contract: dict[str, Any]
    manifests: dict[str, dict[str, Any]]


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_exact_columns(
    frame: pd.DataFrame, expected: list[str], *, label: str
) -> None:
    actual = list(frame.columns)
    if actual != expected:
        missing = [column for column in expected if column not in actual]
        unexpected = [column for column in actual if column not in expected]
        raise ProductionAssemblyError(
            f"{label} columns violate the frozen allowlist/order; "
            f"missing={missing}, unexpected={unexpected}."
        )


def _feature_groups(contract: dict[str, Any]) -> dict[str, list[str]]:
    if (
        contract.get("schema_version") != SCHEMA_VERSION
        or contract.get("manifest_type") != "production_feature_contract"
        or contract.get("status") != "frozen"
        or contract.get("context_field_count") != 16
        or contract.get("feature_count") != 24
        or contract.get("total_column_count") != 46
    ):
        raise ProductionAssemblyError("Frozen production contract identity has drifted.")
    ordered = ordered_column_contract_from_feature_manifest(contract)
    validate_ordered_column_contract(ordered, ordered)
    keys = [item["name"] for item in contract["sample_keys"]]
    context = [item["name"] for item in contract["context_fields"]]
    features = contract["features"]
    provenance = [item["name"] for item in contract["provenance_columns"]]
    if keys != KEY_COLUMNS or len(context) != 16 or len(features) != 24:
        raise ProductionAssemblyError("Frozen key/context/feature counts have drifted.")
    positions = [item.get("position") for item in features]
    if positions != list(range(1, 25)):
        raise ProductionAssemblyError("Feature positions must be exactly 1 through 24.")
    groups = {
        "keys": keys,
        "context": context,
        "atomic": [item["name"] for item in features if item.get("class") == "B1a"],
        "calibrated": [item["name"] for item in features if item.get("class") == "B1b"],
        "engine_start": [item["name"] for item in features if item.get("class") == "B2"],
        "windows": [item["name"] for item in features if item.get("class") == "B3"],
        "features": [item["name"] for item in features],
        "provenance": provenance,
        "all": [item["name"] for item in ordered],
    }
    expected_lengths = {
        "atomic": 8, "calibrated": 2, "engine_start": 6, "windows": 8
    }
    if any(len(groups[name]) != count for name, count in expected_lengths.items()):
        raise ProductionAssemblyError("Frozen B-class grouping has drifted.")
    expected_owners = {
        "atomic": "10_atomic_feature_builder.py",
        "calibrated": "40_calibrated_feature_builder.py",
        "engine_start": "20_engine_start_context_builder.py",
        "windows": "30_window_feature_builder.py",
    }
    classes = {"atomic": "B1a", "calibrated": "B1b", "engine_start": "B2", "windows": "B3"}
    for group, owner in expected_owners.items():
        selected = [item for item in features if item.get("class") == classes[group]]
        if any(item.get("owner_script") != owner for item in selected):
            raise ProductionAssemblyError(f"Frozen owner contract drifted for {group}.")
    constants = {item["name"]: item.get("constant_value") for item in contract["provenance_columns"]}
    if constants != {
        "schema_version": SCHEMA_VERSION,
        "calibration_version": CALIBRATION_VERSION,
    }:
        raise ProductionAssemblyError("Provenance constant contract has drifted.")
    return groups


def _descriptor_map(manifest: dict[str, Any], key: str) -> dict[str, ArtifactDescriptor]:
    return {
        item["artifact_id"]: ArtifactDescriptor.from_mapping(item)
        for item in manifest[key]
    }


def _validate_upstream_manifests(
    run_layout: RunLayout,
) -> dict[str, dict[str, Any]]:
    paths = {
        "00": run_layout.input_contract_manifest,
        "10": run_layout.atomic_features_manifest,
        "20": run_layout.engine_start_context_manifest,
        "30": run_layout.window_features_manifest,
        "40": run_layout.calibrated_features_manifest,
    }
    manifests = {stage: load_json_object(path) for stage, path in paths.items()}
    for stage, manifest in manifests.items():
        expected_calibration = CALIBRATION_VERSION if stage == "40" else "not_applicable"
        validate_stage_manifest(
            manifest,
            expected_schema_version=SCHEMA_VERSION,
            expected_calibration_version=expected_calibration,
        )
        if manifest.get("stage_id") != stage:
            raise ProductionAssemblyError(f"Expected stage {stage} manifest.")
        verify_manifest_artifacts(
            manifest, run_dir=run_layout.run_dir, repo_root=run_layout.repo_root
        )
    identities = {manifest["source_dataset_identity"] for manifest in manifests.values()}
    if len(identities) != 1:
        raise ProductionAssemblyError("Stage 00/10/20/30/40 dataset identities differ.")
    expected_outputs = {
        "10": {"atomic_features"},
        "20": {"engine_start_context", "engine_start_episodes"},
        "30": {"window_features"},
        "40": {"calibrated_features"},
    }
    for stage, expected in expected_outputs.items():
        actual = set(_descriptor_map(manifests[stage], "ordered_output_artifacts"))
        if actual != expected:
            raise ProductionAssemblyError(f"Stage {stage} output artifacts have drifted.")
    return manifests


def _read_csv(path: Path, *, label: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ProductionAssemblyError(f"Cannot read {label}: {exc}") from exc


def _align_to_keys(
    ordered_keys: pd.DataFrame,
    frame: pd.DataFrame,
    *,
    expected_columns: list[str],
    expected_key_hash: str,
    label: str,
) -> pd.DataFrame:
    _require_exact_columns(frame, expected_columns, label=label)
    if frame.duplicated(KEY_COLUMNS).any():
        raise ProductionAssemblyError(f"{label} contains duplicate sample keys.")
    key_check = ordered_keys.merge(
        frame[KEY_COLUMNS], on=KEY_COLUMNS, how="outer", validate="one_to_one",
        indicator=True,
    )
    if not key_check["_merge"].eq("both").all():
        raise ProductionAssemblyError(f"{label} sample-key set differs from canonical.")
    aligned = ordered_keys.merge(
        frame, on=KEY_COLUMNS, how="left", validate="one_to_one", sort=False
    )
    if _ordered_key_sha256(aligned[KEY_COLUMNS]) != expected_key_hash:
        raise ProductionAssemblyError(f"{label} ordered key identity has drifted.")
    return aligned


def load_production_inputs(run_layout: RunLayout) -> ProductionInputs:
    """Verify all upstream manifests and restore every sample table to one order."""

    manifests = _validate_upstream_manifests(run_layout)
    contract = load_json_object(run_layout.feature_contract)
    groups = _feature_groups(contract)
    stage_00_inputs = _descriptor_map(manifests["00"], "ordered_input_artifacts")
    if set(stage_00_inputs) != {
        "feature_contract", "operating_condition_enriched", "cleaning_quality"
    }:
        raise ProductionAssemblyError("Stage 00 authoritative inputs have drifted.")
    summary_00 = manifests["00"].get("validation_summary", {})
    canonical_columns = summary_00.get("canonical_column_order")
    if not isinstance(canonical_columns, list):
        raise ProductionAssemblyError("Stage 00 canonical column order is missing.")
    for field in groups["context"]:
        if field not in canonical_columns:
            raise ProductionAssemblyError(f"Canonical input is missing A field {field}.")

    canonical_raw = _read_csv(
        run_layout.operating_condition_enriched, label="canonical input"
    )
    missing_canonical = [column for column in canonical_columns if column not in canonical_raw]
    if missing_canonical:
        raise ProductionAssemblyError(
            f"Canonical input is missing validated columns: {missing_canonical}."
        )
    if canonical_raw.duplicated(KEY_COLUMNS).any():
        raise ProductionAssemblyError("Canonical input contains duplicate sample keys.")
    ordered_keys = canonical_raw[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    expected_key_hash = summary_00.get("ordered_sample_keys_sha256")
    if _ordered_key_sha256(ordered_keys) != expected_key_hash:
        raise ProductionAssemblyError("Stage 00 ordered key identity has drifted.")
    canonical = ordered_keys.merge(
        canonical_raw[canonical_columns],
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )

    expected_stage_columns = {
        "10": [*KEY_COLUMNS, *groups["atomic"]],
        "20": [*KEY_COLUMNS, *groups["engine_start"]],
        "30": [*KEY_COLUMNS, *groups["windows"]],
        "40": [*KEY_COLUMNS, *groups["calibrated"]],
    }
    for stage in ("10", "30", "40"):
        declared = manifests[stage].get("output_contract", {}).get("ordered_columns")
        if declared != expected_stage_columns[stage]:
            raise ProductionAssemblyError(f"Stage {stage} ordered-column contract drifted.")
        if manifests[stage]["output_contract"].get(
            "ordered_sample_keys_sha256"
        ) != expected_key_hash:
            raise ProductionAssemblyError(f"Stage {stage} key hash differs from stage 00.")
    sample_20 = manifests["20"].get("output_contract", {}).get("sample_table", {})
    if sample_20.get("ordered_columns") != expected_stage_columns["20"]:
        raise ProductionAssemblyError("Stage 20 sample-column contract drifted.")
    if sample_20.get("ordered_sample_keys_sha256") != expected_key_hash:
        raise ProductionAssemblyError("Stage 20 key hash differs from stage 00.")

    atomic = _align_to_keys(
        ordered_keys, _read_csv(run_layout.atomic_features, label="atomic features"),
        expected_columns=expected_stage_columns["10"],
        expected_key_hash=expected_key_hash, label="atomic features",
    )
    context = _align_to_keys(
        ordered_keys,
        _read_csv(run_layout.engine_start_context, label="engine-start context"),
        expected_columns=expected_stage_columns["20"],
        expected_key_hash=expected_key_hash, label="engine-start context",
    )
    windows = _align_to_keys(
        ordered_keys, _read_csv(run_layout.window_features, label="window features"),
        expected_columns=expected_stage_columns["30"],
        expected_key_hash=expected_key_hash, label="window features",
    )
    calibrated = _align_to_keys(
        ordered_keys,
        _read_csv(run_layout.calibrated_features, label="calibrated features"),
        expected_columns=expected_stage_columns["40"],
        expected_key_hash=expected_key_hash, label="calibrated features",
    )
    episodes = _read_csv(run_layout.engine_start_episodes, label="engine-start episodes")
    episode_columns = manifests["20"].get("output_contract", {}).get(
        "episode_table", {}
    ).get("ordered_columns")
    if not isinstance(episode_columns, list):
        raise ProductionAssemblyError("Stage 20 episode-column contract is missing.")
    _require_exact_columns(episodes, episode_columns, label="engine-start episodes")
    return ProductionInputs(
        canonical=canonical,
        atomic=atomic,
        engine_start_context=context,
        engine_start_episodes=episodes,
        windows=windows,
        calibrated=calibrated,
        feature_contract=contract,
        manifests=manifests,
    )


def _validate_episode_foreign_keys(inputs: ProductionInputs) -> None:
    context = inputs.engine_start_context
    episodes = inputs.engine_start_episodes
    episode_key = ["trip_id", "engine_start_episode_id"]
    if episodes.duplicated(episode_key).any():
        raise ProductionAssemblyError("Engine-start episode primary keys are not unique.")
    referenced = context.loc[
        context["engine_start_episode_id"].notna(),
        [*episode_key, "engine_start_observed", "ect_start", "aat_start", "iat_start"],
    ]
    if referenced.empty:
        if not episodes.empty:
            raise ProductionAssemblyError("Unreferenced engine-start episodes exist.")
        return
    joined = referenced.merge(
        episodes[[*episode_key, "ect_start", "aat_start", "iat_start"]],
        on=episode_key,
        how="left",
        validate="many_to_one",
        indicator=True,
        suffixes=("_sample", "_episode"),
    )
    if not joined["_merge"].eq("both").all():
        raise ProductionAssemblyError("Engine-start context contains orphan episode IDs.")
    for column in ("ect_start", "aat_start", "iat_start"):
        left = pd.to_numeric(joined[f"{column}_sample"], errors="coerce")
        right = pd.to_numeric(joined[f"{column}_episode"], errors="coerce")
        equal = left.eq(right) | (left.isna() & right.isna())
        if not equal.all():
            raise ProductionAssemblyError(f"Episode-mapped {column} values have drifted.")
    observed = _parse_boolean(
        context["engine_start_observed"], label="engine_start_observed"
    )
    if context.loc[observed.eq(True), "engine_start_episode_id"].isna().any():
        raise ProductionAssemblyError("Observed engine starts must reference episodes.")
    observed_keys = context.loc[observed.eq(True), episode_key]
    if len(observed_keys) != len(episodes):
        raise ProductionAssemblyError("Each episode must have exactly one observed start.")
    if observed_keys.duplicated(episode_key).any():
        raise ProductionAssemblyError("An episode has multiple observed start rows.")


def _parse_boolean(series: pd.Series, *, label: str) -> pd.Series:
    mapping = {
        True: True, False: False, 1: True, 0: False,
        "true": True, "false": False, "1": True, "0": False,
    }
    normalized = series.map(
        lambda value: pd.NA if pd.isna(value) else mapping.get(
            value.strip().casefold() if isinstance(value, str) else value,
            "invalid",
        )
    )
    if normalized.eq("invalid").any():
        raise ProductionAssemblyError(f"{label} contains invalid boolean values.")
    return normalized.astype("boolean")


def _normalize_and_validate_dtypes(
    output: pd.DataFrame, contract: dict[str, Any]
) -> pd.DataFrame:
    normalized = output.copy()
    fields = ordered_column_contract_from_feature_manifest(contract)
    for field in fields:
        name = field["name"]
        dtype = field["dtype"]
        nullable = field["nullable"]
        original = normalized[name]
        if dtype == "datetime64[ns, UTC]":
            text = original.astype("string")
            valid_format = text.map(
                lambda value: bool(TIMESTAMP_PATTERN.fullmatch(value))
                if not pd.isna(value) else False
            )
            parsed = pd.to_datetime(text, utc=True, errors="coerce")
            if not valid_format.all() or parsed.isna().any():
                raise ProductionAssemblyError(
                    "timestamp must use strict ISO 8601 second-level UTC Z format."
                )
            normalized[name] = text
        elif dtype == "int64":
            numeric = pd.to_numeric(original, errors="coerce")
            invalid = original.notna() & numeric.isna()
            if invalid.any() or numeric.isna().any() or not numeric.mod(1).eq(0).all():
                raise ProductionAssemblyError(f"{name} violates int64 contract.")
            normalized[name] = numeric.astype("int64")
        elif dtype == "float64":
            numeric = pd.to_numeric(original, errors="coerce")
            if (original.notna() & numeric.isna()).any():
                raise ProductionAssemblyError(f"{name} contains non-numeric values.")
            normalized[name] = numeric.astype("float64")
        elif dtype == "boolean":
            normalized[name] = _parse_boolean(original, label=name)
        elif dtype == "string":
            invalid = original.notna() & ~original.map(
                lambda value: isinstance(value, str) if not pd.isna(value) else True
            )
            if invalid.any():
                raise ProductionAssemblyError(f"{name} contains non-string values.")
            normalized[name] = original.astype("string")
        else:
            raise ProductionAssemblyError(f"Unsupported contracted dtype {dtype} for {name}.")
        if not nullable and normalized[name].isna().any():
            raise ProductionAssemblyError(f"Non-nullable column {name} contains nulls.")
        allowed = field.get("allowed_values")
        if allowed is not None:
            unexpected = set(normalized[name].dropna().unique()) - set(allowed)
            if unexpected:
                raise ProductionAssemblyError(
                    f"{name} contains values outside its frozen domain: {sorted(unexpected)}."
                )
        constant = field.get("constant_value")
        if constant is not None and not normalized[name].eq(constant).all():
            raise ProductionAssemblyError(f"Provenance column {name} is not constant.")
    return normalized


def _validate_global_order(output: pd.DataFrame) -> None:
    expected = output.sort_values(KEY_COLUMNS, kind="stable").reset_index(drop=True)
    if not output[KEY_COLUMNS].reset_index(drop=True).equals(expected[KEY_COLUMNS]):
        raise ProductionAssemblyError("Production rows are not in frozen global order.")
    grouped = output.groupby(["trip_id", "segment_id"], sort=False, dropna=False)
    for _, frame in grouped:
        rows = frame["row_in_segment"]
        if not rows.eq(pd.Series(range(1, len(frame) + 1), index=frame.index)).all():
            raise ProductionAssemblyError(
                "row_in_segment must be 1-based and consecutive within each segment."
            )
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
        if len(frame) > 1 and not timestamps.diff().iloc[1:].dt.total_seconds().eq(1.0).all():
            raise ProductionAssemblyError(
                "Timestamps must be strictly consecutive at 1 Hz within each segment."
            )


def build_production_features(inputs: ProductionInputs) -> pd.DataFrame:
    """Join all approved fields, restore order, and enforce the 46-column schema."""

    groups = _feature_groups(inputs.feature_contract)
    _validate_episode_foreign_keys(inputs)
    ordered_keys = inputs.canonical[KEY_COLUMNS].copy()
    output = inputs.canonical[[*KEY_COLUMNS, *groups["context"]]].copy()
    sources = [
        (inputs.atomic, groups["atomic"]),
        (inputs.calibrated, groups["calibrated"]),
        (inputs.engine_start_context, groups["engine_start"]),
        (inputs.windows, groups["windows"]),
    ]
    for frame, columns in sources:
        _require_exact_columns(
            frame, [*KEY_COLUMNS, *columns], label=f"upstream {columns[0]} table"
        )
        key_check = ordered_keys.merge(
            frame[KEY_COLUMNS], on=KEY_COLUMNS, how="outer",
            validate="one_to_one", indicator=True,
        )
        if not key_check["_merge"].eq("both").all():
            raise ProductionAssemblyError("An upstream sample-key set differs.")
        output = output.merge(
            frame[[*KEY_COLUMNS, *columns]],
            on=KEY_COLUMNS,
            how="left",
            validate="one_to_one",
            sort=False,
        )
    output["schema_version"] = SCHEMA_VERSION
    output["calibration_version"] = CALIBRATION_VERSION
    output = output[groups["all"]]
    _require_exact_columns(output, groups["all"], label="production output")
    if len(output) != len(inputs.canonical):
        raise ProductionAssemblyError("Production assembly changed the sample row count.")
    output = _normalize_and_validate_dtypes(output, inputs.feature_contract)
    _validate_global_order(output)
    if _ordered_key_sha256(output[KEY_COLUMNS]) != _ordered_key_sha256(ordered_keys):
        raise ProductionAssemblyError("Production sample keys changed unexpectedly.")
    return output


def _write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False, float_format="%.15g")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ProductionAssemblyError(f"Cannot write production CSV: {exc}") from exc


def _descriptor(
    path: Path, *, artifact_id: str, run_layout: RunLayout
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path, artifact_id=artifact_id,
        manifest_path=run_layout.run_relative_posix(path), path_base="run_dir"
    )


def run_production_feature_assembler(
    run_layout: RunLayout, *, creation_time_utc: str | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Write the strict production handoff and adjacent Script 41 manifest."""

    inputs = load_production_inputs(run_layout)
    output = build_production_features(inputs)
    _write_csv_atomic(run_layout.production_features, output)
    stage_00_inputs = _descriptor_map(
        inputs.manifests["00"], "ordered_input_artifacts"
    )
    stage_manifest_paths = {
        "00": run_layout.input_contract_manifest,
        "10": run_layout.atomic_features_manifest,
        "20": run_layout.engine_start_context_manifest,
        "30": run_layout.window_features_manifest,
        "40": run_layout.calibrated_features_manifest,
    }
    input_artifacts: list[ArtifactDescriptor] = [stage_00_inputs["feature_contract"]]
    input_artifacts.extend(
        _descriptor(path, artifact_id=f"stage_{stage}_manifest", run_layout=run_layout)
        for stage, path in stage_manifest_paths.items()
    )
    input_artifacts.extend([
        stage_00_inputs["operating_condition_enriched"],
        _descriptor(run_layout.atomic_features, artifact_id="atomic_features", run_layout=run_layout),
        _descriptor(
            run_layout.engine_start_context,
            artifact_id="engine_start_context",
            run_layout=run_layout,
        ),
        _descriptor(
            run_layout.engine_start_episodes,
            artifact_id="engine_start_episodes",
            run_layout=run_layout,
        ),
        _descriptor(run_layout.window_features, artifact_id="window_features", run_layout=run_layout),
        _descriptor(
            run_layout.calibrated_features,
            artifact_id="calibrated_features",
            run_layout=run_layout,
        ),
    ])
    output_descriptor = _descriptor(
        run_layout.production_features,
        artifact_id="production_features",
        run_layout=run_layout,
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=SCHEMA_VERSION,
        script_version=SCRIPT_VERSION,
        source_dataset_identity=inputs.manifests["00"]["source_dataset_identity"],
        input_artifacts=input_artifacts,
        output_artifacts=[output_descriptor],
        calibration_version=CALIBRATION_VERSION,
        creation_time_utc=creation_time_utc,
    )
    fields = [dict(item) for item in ordered_column_contract_from_feature_manifest(
        inputs.feature_contract
    )]
    validate_ordered_column_contract(fields, fields)
    segment_sizes = output.groupby(["trip_id", "segment_id"], sort=False).size()
    manifest["output_contract"] = {
        "table_name": "production_features",
        "grain": "sample",
        "ordered_column_contract": fields,
        "ordered_columns": list(output.columns),
        "total_column_count": 46,
        "context_field_count": 16,
        "feature_count": 24,
        "provenance_column_count": 2,
        "row_count": int(len(output)),
        "ordered_sample_keys_sha256": _ordered_key_sha256(output[KEY_COLUMNS]),
        "null_counts": {column: int(output[column].isna().sum()) for column in output.columns},
        "strict_allowlist_enforced": True,
        "assembler_imputation_performed": False,
        "episode_foreign_keys_validated": True,
    }
    manifest["delivery_summary"] = {
        "trip_count": int(output["trip_id"].nunique()),
        "segment_count": int(len(segment_sizes)),
        "minimum_segment_sample_count": int(segment_sizes.min()),
        "segments_with_at_least_700_samples": int(segment_sizes.ge(700).sum()),
        "all_timestamps_strict_second_level_utc_z": True,
        "within_segment_sampling_hz": 1,
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=SCHEMA_VERSION,
        expected_calibration_version=CALIBRATION_VERSION,
    )
    write_json_atomic(run_layout.production_feature_manifest, manifest)
    return output, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble the strict 46-column production feature table."
    )
    parser.add_argument(
        "--run-dir", required=True,
        help="Explicit run directory under data/processed/runs/<run_id>.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        run_layout = RunLayout.from_run_dir(args.run_dir, repo_root=PROJECT_ROOT)
        output, manifest = run_production_feature_assembler(run_layout)
    except (
        ProductionAssemblyError, ManifestError, ManifestValidationError,
        OSError, KeyError, TypeError, ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "production_features": run_layout.run_relative_posix(
            run_layout.production_features
        ),
        "manifest": run_layout.run_relative_posix(
            run_layout.production_feature_manifest
        ),
        "sample_rows": int(len(output)),
        "column_count": int(len(output.columns)),
        "schema_version": manifest["schema_version"],
        "calibration_version": manifest["calibration_version"],
        "source_dataset_identity": manifest["source_dataset_identity"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
