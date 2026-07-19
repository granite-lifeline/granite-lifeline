"""Build the eight deterministic B3 strict-window features for Script 30."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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

from data_layer.pipeline_data.continuity import (  # noqa: E402
    build_continuity_blocks,
    build_quality_valid_mask,
    strict_elapsed_span_mask,
    strict_window_mask,
)
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    ManifestError,
    ManifestValidationError,
    build_stage_manifest,
    load_json_object,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "30"
KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
B3_COLUMNS = [
    "maf_integral_180s",
    "ect_rate_180s",
    "intake_temp_stability",
    "speed_std_120s",
    "maf_std_120s",
    "rpm_std_120s",
    "accel_pedal_mean_std_120s",
    "map_range_60s",
]
QUALITY_SUFFIXES = (
    "is_imputed",
    "is_suspicious",
    "had_hard_invalid_source",
)


class WindowFeatureError(RuntimeError):
    """Raised when Script 30 input or strict-window contracts are invalid."""


@dataclass(frozen=True, slots=True)
class WindowInputs:
    canonical: pd.DataFrame
    quality: pd.DataFrame
    atomic: pd.DataFrame
    engine_start_context: pd.DataFrame
    feature_contract: dict[str, Any]
    input_contract_manifest: dict[str, Any]
    atomic_manifest: dict[str, Any]
    engine_start_manifest: dict[str, Any]


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(frame: pd.DataFrame,
                     columns: list[str], *, label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise WindowFeatureError(
            f"{label} is missing required columns: {missing}.")


def _validate_b3_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    if contract.get("schema_version") != "feature_schema.v1":
        raise WindowFeatureError("Script 30 requires feature_schema.v1.")
    features = contract.get("features")
    if not isinstance(features, list) or len(features) < 24:
        raise WindowFeatureError(
            "Feature contract does not contain eight B3 fields.")
    b3 = features[16:24]
    if [item.get("name") for item in b3] != B3_COLUMNS:
        raise WindowFeatureError("B3 feature name/order contract has drifted.")
    expected_units = [
        "g", "degC/min", "degC", "km/h", "g/s", "rpm", "percent", "kPa"
    ]
    for position, (item, unit) in enumerate(zip(b3, expected_units), start=17):
        if (
            item.get("position") != position
            or item.get("class") != "B3"
            or item.get("dtype") != "float64"
            or item.get("unit") != unit
            or item.get("nullable") is not True
            or item.get("owner_script") != "30_window_feature_builder.py"
        ):
            raise WindowFeatureError(
                f"B3 contract has drifted at position {position}.")
    first, second, *sample_windows = b3
    if first.get("window_contract") != {
        "span_seconds": 180,
        "endpoint_count": 181,
        "interval_count": 180,
        "sampling_hz": 1,
        "same_continuity_block": True,
        "same_engine_start_episode": True,
        "all_endpoints_quality_valid": True,
    }:
        raise WindowFeatureError("MAF integral window contract has drifted.")
    if second.get("window_contract") != {
        "span_seconds": 180,
        "endpoint_count": 181,
        "sampling_hz": 1,
        "same_continuity_block": True,
        "all_endpoints_quality_valid": True,
    }:
        raise WindowFeatureError("ECT rate window contract has drifted.")
    expected_samples = [60, 120, 120, 120, 120, 60]
    for item, samples in zip(sample_windows, expected_samples):
        if item.get("window_sample_count") != samples:
            raise WindowFeatureError(
                "Window sample-count contract has drifted for "
                f"{item.get('name')}."
            )
    for item in sample_windows[:5]:
        if item.get("ddof") != 1:
            raise WindowFeatureError(
                "Sample-standard-deviation contract has drifted for "
                f"{item['name']}."
            )
    return [dict(item) for item in b3]


def _descriptor_map(manifest: dict[str, Any],
                    key: str) -> dict[str, ArtifactDescriptor]:
    return {
        item["artifact_id"]: ArtifactDescriptor.from_mapping(item)
        for item in manifest[key]
    }


def _validate_upstream_manifest(
    manifest: dict[str, Any], *, stage_id: str, run_layout: RunLayout
) -> None:
    validate_stage_manifest(
        manifest,
        expected_schema_version="feature_schema.v1",
        expected_calibration_version="not_applicable",
    )
    if manifest.get("stage_id") != stage_id:
        raise WindowFeatureError(f"Expected stage {stage_id} manifest.")
    verify_manifest_artifacts(
        manifest, run_dir=run_layout.run_dir, repo_root=run_layout.repo_root
    )


def load_window_inputs(run_layout: RunLayout) -> WindowInputs:
    """Verify stages 00/10/20 and align all sample-grain inputs."""

    input_manifest = load_json_object(run_layout.input_contract_manifest)
    atomic_manifest = load_json_object(run_layout.atomic_features_manifest)
    engine_manifest = load_json_object(
        run_layout.engine_start_context_manifest)
    for manifest, stage in (
        (input_manifest, "00"),
        (atomic_manifest, "10"),
        (engine_manifest, "20"),
    ):
        _validate_upstream_manifest(
            manifest, stage_id=stage, run_layout=run_layout)
    identities = {
        input_manifest["source_dataset_identity"],
        atomic_manifest["source_dataset_identity"],
        engine_manifest["source_dataset_identity"],
    }
    if len(identities) != 1:
        raise WindowFeatureError(
            "Stage 00/10/20 source dataset identities differ.")

    stage_00_inputs = _descriptor_map(
        input_manifest, "ordered_input_artifacts")
    if set(stage_00_inputs) != {
        "feature_contract", "operating_condition_enriched", "cleaning_quality"
    }:
        raise WindowFeatureError("Stage 00 authoritative inputs have drifted.")
    if set(_descriptor_map(atomic_manifest, "ordered_output_artifacts")) != {
        "atomic_features"
    }:
        raise WindowFeatureError("Stage 10 output contract has drifted.")
    if set(_descriptor_map(engine_manifest, "ordered_output_artifacts")) != {
        "engine_start_context", "engine_start_episodes"
    }:
        raise WindowFeatureError("Stage 20 output contract has drifted.")

    feature_contract = load_json_object(run_layout.feature_contract)
    _validate_b3_contract(feature_contract)
    summary_00 = input_manifest.get("validation_summary", {})
    atomic_contract = atomic_manifest.get("output_contract", {})
    engine_contract = engine_manifest.get(
        "output_contract", {}).get("sample_table", {})
    canonical_columns = summary_00.get("canonical_column_order")
    quality_columns = summary_00.get("quality_column_order")
    atomic_columns = atomic_contract.get("ordered_columns")
    engine_columns = engine_contract.get("ordered_columns")
    ordered_column_sources = (
        canonical_columns, quality_columns, atomic_columns, engine_columns,
    )
    if not all(
        isinstance(value, list) for value in ordered_column_sources
    ):
        raise WindowFeatureError(
            "Upstream ordered-column metadata is missing.")

    try:
        operating = pd.read_csv(
            run_layout.operating_condition_enriched, low_memory=False)
        quality = pd.read_csv(run_layout.cleaning_quality, low_memory=False)
        atomic = pd.read_csv(run_layout.atomic_features, low_memory=False)
        engine = pd.read_csv(run_layout.engine_start_context, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise WindowFeatureError(
            f"Cannot read Script 30 inputs: {exc}") from exc
    _require_columns(operating, canonical_columns, label="canonical input")
    _require_columns(quality, quality_columns, label="quality input")
    if list(atomic.columns) != atomic_columns:
        raise WindowFeatureError("Atomic CSV column order has drifted.")
    if list(engine.columns) != engine_columns:
        raise WindowFeatureError(
            "Engine-start context CSV column order has drifted.")

    key_union = operating[KEY_COLUMNS].merge(
        quality[KEY_COLUMNS],
        on=KEY_COLUMNS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not key_union["_merge"].eq("both").all():
        raise WindowFeatureError("Canonical and quality key sets differ.")
    ordered_keys = key_union[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    expected_key_hash = summary_00.get("ordered_sample_keys_sha256")
    if _ordered_key_sha256(ordered_keys) != expected_key_hash:
        raise WindowFeatureError("Stage 00 ordered key identity has drifted.")

    def align(frame: pd.DataFrame,
              columns: list[str], label: str) -> pd.DataFrame:
        aligned = ordered_keys.merge(
            frame[columns],
            on=KEY_COLUMNS,
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if _ordered_key_sha256(aligned[KEY_COLUMNS]) != expected_key_hash:
            raise WindowFeatureError(
                f"{label} ordered key identity has drifted.")
        return aligned

    canonical = align(operating, canonical_columns, "Canonical")
    aligned_quality = align(quality, quality_columns, "Quality")
    aligned_atomic = align(atomic, atomic_columns, "Atomic")
    aligned_engine = align(engine, engine_columns, "Engine-start")
    if atomic_contract.get("ordered_sample_keys_sha256") != expected_key_hash:
        raise WindowFeatureError("Stage 10 manifest key identity has drifted.")
    if engine_contract.get("ordered_sample_keys_sha256") != expected_key_hash:
        raise WindowFeatureError("Stage 20 manifest key identity has drifted.")
    return WindowInputs(
        canonical=canonical,
        quality=aligned_quality,
        atomic=aligned_atomic,
        engine_start_context=aligned_engine,
        feature_contract=feature_contract,
        input_contract_manifest=input_manifest,
        atomic_manifest=atomic_manifest,
        engine_start_manifest=engine_manifest,
    )


def _signal_valid_mask(inputs: WindowInputs, signal: str) -> pd.Series:
    columns: dict[str, pd.Series] = {signal: inputs.canonical[signal]}
    for suffix in QUALITY_SUFFIXES:
        flag = f"{signal}_{suffix}"
        columns[flag] = inputs.quality[flag]
    return build_quality_valid_mask(pd.DataFrame(columns), [signal])


def _rolling_statistic(
    values: pd.Series,
    block_ids: pd.Series,
    window_samples: int,
    statistic: str,
) -> pd.Series:
    result = pd.Series(float("nan"), index=values.index, dtype="float64")
    admitted = strict_window_mask(block_ids, window_samples)
    grouped = block_ids.dropna().groupby(block_ids.dropna(), sort=False)
    for _, indexes in grouped.groups.items():
        block_values = pd.to_numeric(values.loc[indexes], errors="coerce")
        rolling = block_values.rolling(
            window_samples, min_periods=window_samples)
        if statistic == "std":
            calculated = rolling.std(ddof=1)
        elif statistic == "range":
            calculated = rolling.max() - rolling.min()
        else:
            raise WindowFeatureError(
                f"Unknown rolling statistic: {statistic}.")
        result.loc[indexes] = calculated
    return result.where(admitted)


def build_window_features(inputs: WindowInputs) -> pd.DataFrame:
    """Calculate B3 features using strict shared continuity semantics."""

    _validate_b3_contract(inputs.feature_contract)
    canonical = inputs.canonical
    timestamps = canonical["timestamp"]
    output = canonical[KEY_COLUMNS].copy()

    maf_valid = _signal_valid_mask(inputs, "maf")
    episode_id = inputs.engine_start_context["engine_start_episode_id"].astype(
        "string")
    maf_episode_blocks = build_continuity_blocks(
        canonical, valid_mask=maf_valid & episode_id.notna()
    ).block_id
    maf_span = strict_elapsed_span_mask(maf_episode_blocks, timestamps, 180)
    maf_span &= episode_id.eq(episode_id.shift(180)).fillna(False)
    maf_values = pd.to_numeric(canonical["maf"], errors="coerce")
    maf_integral = pd.Series(
        float("nan"), index=canonical.index, dtype="float64")
    for _, indexes in maf_episode_blocks.dropna().groupby(
        maf_episode_blocks.dropna(), sort=False
    ).groups.items():
        values = maf_values.loc[indexes]
        sums = values.rolling(181, min_periods=181).sum()
        integral = sums - 0.5 * (values + values.shift(180))
        maf_integral.loc[indexes] = integral
    output["maf_integral_180s"] = maf_integral.where(maf_span)

    ect_valid = _signal_valid_mask(inputs, "coolant_temp")
    ect_blocks = build_continuity_blocks(
        canonical, valid_mask=ect_valid).block_id
    ect_span = strict_elapsed_span_mask(ect_blocks, timestamps, 180)
    ect = pd.to_numeric(canonical["coolant_temp"], errors="coerce")
    output["ect_rate_180s"] = ((ect - ect.shift(180)) / 3.0).where(ect_span)

    rolling_specs = [
        ("intake_temp_stability", "intake_temp", 60, "std"),
        ("speed_std_120s", "speed", 120, "std"),
        ("maf_std_120s", "maf", 120, "std"),
        ("rpm_std_120s", "rpm", 120, "std"),
        ("map_range_60s", "map", 60, "range"),
    ]
    for target, signal, samples, statistic in rolling_specs:
        valid = _signal_valid_mask(inputs, signal)
        blocks = build_continuity_blocks(canonical, valid_mask=valid).block_id
        output[target] = _rolling_statistic(
            canonical[signal], blocks, samples, statistic
        )

    pedal = pd.to_numeric(inputs.atomic["accel_pedal_mean"], errors="coerce")
    pedal_blocks = build_continuity_blocks(
        canonical, valid_mask=pedal.notna()
    ).block_id
    output["accel_pedal_mean_std_120s"] = _rolling_statistic(
        pedal, pedal_blocks, 120, "std"
    )
    output = output[[*KEY_COLUMNS, *B3_COLUMNS]]
    if not output[KEY_COLUMNS].equals(canonical[KEY_COLUMNS]):
        raise WindowFeatureError("Window feature keys changed unexpectedly.")
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
        raise WindowFeatureError(
            f"Cannot write window-feature CSV: {exc}") from exc


def _descriptor(path: Path, *, artifact_id: str,
                run_layout: RunLayout) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path,
        artifact_id=artifact_id,
        manifest_path=run_layout.run_relative_posix(path),
        path_base="run_dir",
    )


def run_window_feature_builder(
    run_layout: RunLayout, *, creation_time_utc: str | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build Script 30 output and its stage manifest."""

    inputs = load_window_inputs(run_layout)
    b3_contract = _validate_b3_contract(inputs.feature_contract)
    output = build_window_features(inputs)
    _write_csv_atomic(run_layout.window_features, output)

    stage_00_inputs = _descriptor_map(
        inputs.input_contract_manifest, "ordered_input_artifacts"
    )
    descriptors = [
        stage_00_inputs["feature_contract"],
        _descriptor(
            run_layout.input_contract_manifest,
            artifact_id="input_contract_manifest",
            run_layout=run_layout,
        ),
        _descriptor(
            run_layout.atomic_features_manifest,
            artifact_id="atomic_features_manifest",
            run_layout=run_layout,
        ),
        _descriptor(
            run_layout.engine_start_context_manifest,
            artifact_id="engine_start_context_manifest",
            run_layout=run_layout,
        ),
        stage_00_inputs["operating_condition_enriched"],
        stage_00_inputs["cleaning_quality"],
        _descriptor(
            run_layout.atomic_features,
            artifact_id="atomic_features",
            run_layout=run_layout,
        ),
        _descriptor(
            run_layout.engine_start_context,
            artifact_id="engine_start_context",
            run_layout=run_layout,
        ),
    ]
    output_descriptor = _descriptor(
        run_layout.window_features,
        artifact_id="window_features",
        run_layout=run_layout,
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=inputs.feature_contract["schema_version"],
        script_version=SCRIPT_VERSION,
        source_dataset_identity=inputs.input_contract_manifest[
            "source_dataset_identity"
        ],
        input_artifacts=descriptors,
        output_artifacts=[output_descriptor],
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    manifest["output_contract"] = {
        "grain": "sample",
        "key_columns": KEY_COLUMNS,
        "feature_columns": b3_contract,
        "ordered_columns": list(output.columns),
        "row_count": int(len(output)),
        "ordered_sample_keys_sha256": _ordered_key_sha256(output[KEY_COLUMNS]),
        "null_counts": {
            column: int(output[column].isna().sum()) for column in B3_COLUMNS
        },
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=inputs.feature_contract["schema_version"],
        expected_calibration_version="not_applicable",
    )
    write_json_atomic(run_layout.window_features_manifest, manifest)
    return output, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build strict B3 window features.")
    parser.add_argument(
        "--run-dir", required=True,
        help="Explicit run directory under data/processed/runs/<run_id>.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    try:
        run_layout = RunLayout.from_run_dir(
            args.run_dir, repo_root=PROJECT_ROOT)
        output, manifest = run_window_feature_builder(run_layout)
    except (
        WindowFeatureError, ManifestError, ManifestValidationError,
        OSError, KeyError, ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "window_features": run_layout.run_relative_posix(
            run_layout.window_features
        ),
        "manifest": run_layout.run_relative_posix(
            run_layout.window_features_manifest
        ),
        "sample_rows": int(len(output)),
        "source_dataset_identity": manifest["source_dataset_identity"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
