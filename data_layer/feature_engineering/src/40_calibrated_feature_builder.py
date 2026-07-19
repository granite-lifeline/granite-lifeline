"""Apply the frozen calibration registry to build the two B1b features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from data_layer.pipeline_data.continuity import build_quality_valid_mask  # noqa: E402
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    ManifestError,
    ManifestValidationError,
    build_stage_manifest,
    load_json_object,
    sha256_file,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout, repo_relative_posix  # noqa: E402


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "40"
KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
B1B_COLUMNS = ["speed_density_maf_residual", "pedal_mapping_residual"]
QUALITY_SUFFIXES = (
    "is_imputed",
    "is_suspicious",
    "had_hard_invalid_source",
)
CALIBRATION_VERSION = "calibration.v1"


class CalibratedFeatureError(RuntimeError):
    """Raised when frozen calibration inputs or outputs violate contract."""


@dataclass(frozen=True, slots=True)
class CalibratedInputs:
    canonical: pd.DataFrame
    quality: pd.DataFrame
    atomic: pd.DataFrame
    feature_contract: dict[str, Any]
    registry: dict[str, Any]
    release_manifest: dict[str, Any]
    input_contract_manifest: dict[str, Any]
    atomic_manifest: dict[str, Any]


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(frame: pd.DataFrame, columns: list[str], *, label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise CalibratedFeatureError(f"{label} is missing required columns: {missing}.")


def _validate_b1b_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    if contract.get("schema_version") != "feature_schema.v1":
        raise CalibratedFeatureError("Script 40 requires feature_schema.v1.")
    features = contract.get("features")
    if not isinstance(features, list) or len(features) < 10:
        raise CalibratedFeatureError("Feature contract does not contain two B1b fields.")
    b1b = features[8:10]
    expected_units = ["g/s", "percentage_point"]
    expected_references = [
        "data_layer/calibration/calibration_registry.v1.json#/feature_transforms/speed_density_maf",
        "data_layer/calibration/calibration_registry.v1.json#/feature_transforms/pedal_mapping",
    ]
    if [item.get("name") for item in b1b] != B1B_COLUMNS:
        raise CalibratedFeatureError("B1b feature name/order contract has drifted.")
    for position, (item, unit, reference) in enumerate(
        zip(b1b, expected_units, expected_references), start=9
    ):
        if (
            item.get("position") != position
            or item.get("class") != "B1b"
            or item.get("dtype") != "float64"
            or item.get("unit") != unit
            or item.get("nullable") is not True
            or item.get("owner_script") != "40_calibrated_feature_builder.py"
            or item.get("calibration_reference") != reference
        ):
            raise CalibratedFeatureError(
                f"B1b feature contract has drifted at position {position}."
            )
    return [dict(item) for item in b1b]


def _finite_number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibratedFeatureError(f"{label} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise CalibratedFeatureError(f"{label} must be finite.")
    return result


def _validate_registry(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        registry.get("registry_type") != "frozen_calibration_registry"
        or registry.get("calibration_version") != CALIBRATION_VERSION
        or registry.get("registry_schema_version") != "1.0.1"
        or registry.get("status") != "frozen"
        or registry.get("immutable") is not True
    ):
        raise CalibratedFeatureError("Frozen registry identity/status has drifted.")
    expected_policy = {
        "read_only": True,
        "fit_allowed": False,
        "quantile_selection_allowed": False,
        "candidate_search_allowed": False,
        "loto_allowed": False,
        "bootstrap_allowed": False,
    }
    if registry.get("online_policy") != expected_policy:
        raise CalibratedFeatureError("Frozen registry online policy has drifted.")
    transforms = registry.get("feature_transforms")
    if not isinstance(transforms, dict) or list(transforms)[:2] != [
        "speed_density_maf", "pedal_mapping"
    ]:
        raise CalibratedFeatureError("Required frozen transforms are missing or reordered.")
    speed = transforms["speed_density_maf"]
    pedal = transforms["pedal_mapping"]
    if (
        speed.get("output_feature") != B1B_COLUMNS[0]
        or speed.get("model_type") != "linear_regression"
        or speed.get("target") != "maf"
        or speed.get("ordered_input_features")
        != ["map_derived_air_load_raw", "map", "rpm", "intake_temp"]
        or speed.get("prediction_missing_policy")
        != "null when MAF or any model input is not quality-valid"
    ):
        raise CalibratedFeatureError("Speed-density transform contract has drifted.")
    hidden = speed.get("hidden_intermediate", {})
    if (
        hidden.get("name") != "map_derived_air_load_raw"
        or hidden.get("formula") != "rpm * map / (intake_temp + 273.15)"
    ):
        raise CalibratedFeatureError("Speed-density hidden formula has drifted.")
    inputs = speed["ordered_input_features"]
    coefficients = speed.get("coefficients")
    bounds = speed.get("prediction_clipping_bounds")
    if not isinstance(coefficients, dict) or list(coefficients) != inputs:
        raise CalibratedFeatureError("Speed-density coefficient order has drifted.")
    if not isinstance(bounds, dict) or list(bounds) != inputs:
        raise CalibratedFeatureError("Speed-density clipping-bound order has drifted.")
    _finite_number(speed.get("intercept"), label="speed-density intercept")
    for name in inputs:
        _finite_number(coefficients[name], label=f"coefficient {name}")
        bound = bounds[name]
        lower = _finite_number(bound.get("lower"), label=f"{name} lower bound")
        upper = _finite_number(bound.get("upper"), label=f"{name} upper bound")
        if lower > upper:
            raise CalibratedFeatureError(f"Invalid clipping bounds for {name}.")
    if (
        pedal.get("output_feature") != B1B_COLUMNS[1]
        or pedal.get("formula") != "accel_pedal_e - (a * accel_pedal_d + b)"
        or pedal.get("prediction_clipping") != "none"
        or pedal.get("prediction_missing_policy")
        != "null unless both pedal channels are quality-valid"
    ):
        raise CalibratedFeatureError("Pedal transform contract has drifted.")
    _finite_number(pedal.get("a"), label="pedal a")
    _finite_number(pedal.get("b"), label="pedal b")
    return {"speed_density_maf": speed, "pedal_mapping": pedal}


def _validate_release_bundle(
    run_layout: RunLayout,
    feature_contract: dict[str, Any],
    registry: dict[str, Any],
    release: dict[str, Any],
) -> None:
    if (
        release.get("manifest_type") != "calibration_registry_release_manifest"
        or release.get("manifest_version") != "1.2.0"
        or release.get("calibration_version") != CALIBRATION_VERSION
        or release.get("status") != "frozen"
        or release.get("hash_algorithm") != "SHA-256"
    ):
        raise CalibratedFeatureError("Calibration release manifest identity has drifted.")
    registry_record = release.get("registry", {})
    contract_record = release.get("feature_contract", {})
    if (
        registry_record.get("path")
        != repo_relative_posix(run_layout.calibration_registry, repo_root=run_layout.repo_root)
        or registry_record.get("sha256") != sha256_file(run_layout.calibration_registry)
        or registry_record.get("registry_schema_version")
        != registry.get("registry_schema_version")
        or registry_record.get("immutable") is not True
    ):
        raise CalibratedFeatureError("Frozen registry checksum/release binding has drifted.")
    if (
        contract_record.get("path")
        != repo_relative_posix(run_layout.feature_contract, repo_root=run_layout.repo_root)
        or contract_record.get("sha256") != sha256_file(run_layout.feature_contract)
        or contract_record.get("manifest_version")
        != feature_contract.get("manifest_version")
        or contract_record.get("schema_version")
        != feature_contract.get("schema_version")
    ):
        raise CalibratedFeatureError("Feature contract checksum/release binding has drifted.")
    checks = release.get("release_checks", {})
    if (
        checks.get("cross_contract_lint_passed") is not True
        or checks.get("online_fit_paths_forbidden") is not True
        or checks.get("numeric_calibration_changed") is not False
    ):
        raise CalibratedFeatureError("Calibration release checks are not acceptable.")


def _descriptor_map(manifest: dict[str, Any], key: str) -> dict[str, ArtifactDescriptor]:
    return {
        item["artifact_id"]: ArtifactDescriptor.from_mapping(item)
        for item in manifest[key]
    }


def load_calibrated_inputs(run_layout: RunLayout) -> CalibratedInputs:
    """Verify stages 00/10 and the frozen calibration release bundle."""

    input_manifest = load_json_object(run_layout.input_contract_manifest)
    atomic_manifest = load_json_object(run_layout.atomic_features_manifest)
    for manifest, stage in ((input_manifest, "00"), (atomic_manifest, "10")):
        validate_stage_manifest(
            manifest,
            expected_schema_version="feature_schema.v1",
            expected_calibration_version="not_applicable",
        )
        if manifest.get("stage_id") != stage:
            raise CalibratedFeatureError(f"Expected stage {stage} manifest.")
        verify_manifest_artifacts(
            manifest, run_dir=run_layout.run_dir, repo_root=run_layout.repo_root
        )
    if atomic_manifest["source_dataset_identity"] != input_manifest[
        "source_dataset_identity"
    ]:
        raise CalibratedFeatureError("Stage 00/10 source dataset identities differ.")

    stage_00_inputs = _descriptor_map(input_manifest, "ordered_input_artifacts")
    if set(stage_00_inputs) != {
        "feature_contract", "operating_condition_enriched", "cleaning_quality"
    }:
        raise CalibratedFeatureError("Stage 00 authoritative inputs have drifted.")
    if set(_descriptor_map(atomic_manifest, "ordered_output_artifacts")) != {
        "atomic_features"
    }:
        raise CalibratedFeatureError("Stage 10 output contract has drifted.")

    feature_contract = load_json_object(run_layout.feature_contract)
    registry = load_json_object(run_layout.calibration_registry)
    release = load_json_object(run_layout.calibration_release_manifest)
    _validate_b1b_contract(feature_contract)
    _validate_registry(registry)
    _validate_release_bundle(run_layout, feature_contract, registry, release)

    summary_00 = input_manifest.get("validation_summary", {})
    atomic_contract = atomic_manifest.get("output_contract", {})
    canonical_columns = summary_00.get("canonical_column_order")
    quality_columns = summary_00.get("quality_column_order")
    atomic_columns = atomic_contract.get("ordered_columns")
    if not all(
        isinstance(value, list)
        for value in (canonical_columns, quality_columns, atomic_columns)
    ):
        raise CalibratedFeatureError("Upstream ordered-column metadata is missing.")
    try:
        operating = pd.read_csv(run_layout.operating_condition_enriched, low_memory=False)
        quality = pd.read_csv(run_layout.cleaning_quality, low_memory=False)
        atomic = pd.read_csv(run_layout.atomic_features, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise CalibratedFeatureError(f"Cannot read Script 40 inputs: {exc}") from exc
    _require_columns(operating, canonical_columns, label="canonical input")
    _require_columns(quality, quality_columns, label="quality input")
    if list(atomic.columns) != atomic_columns:
        raise CalibratedFeatureError("Atomic CSV column order has drifted.")

    key_union = operating[KEY_COLUMNS].merge(
        quality[KEY_COLUMNS], on=KEY_COLUMNS, how="outer", validate="one_to_one",
        indicator=True,
    )
    if not key_union["_merge"].eq("both").all():
        raise CalibratedFeatureError("Canonical and quality key sets differ.")
    ordered_keys = key_union[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    expected_key_hash = summary_00.get("ordered_sample_keys_sha256")
    if _ordered_key_sha256(ordered_keys) != expected_key_hash:
        raise CalibratedFeatureError("Stage 00 ordered key identity has drifted.")

    def align(frame: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
        aligned = ordered_keys.merge(
            frame[columns], on=KEY_COLUMNS, how="left", validate="one_to_one", sort=False
        )
        if _ordered_key_sha256(aligned[KEY_COLUMNS]) != expected_key_hash:
            raise CalibratedFeatureError(f"{label} ordered key identity has drifted.")
        return aligned

    if atomic_contract.get("ordered_sample_keys_sha256") != expected_key_hash:
        raise CalibratedFeatureError("Stage 10 manifest key identity has drifted.")
    return CalibratedInputs(
        canonical=align(operating, canonical_columns, "Canonical"),
        quality=align(quality, quality_columns, "Quality"),
        atomic=align(atomic, atomic_columns, "Atomic"),
        feature_contract=feature_contract,
        registry=registry,
        release_manifest=release,
        input_contract_manifest=input_manifest,
        atomic_manifest=atomic_manifest,
    )


def _quality_valid_mask(inputs: CalibratedInputs, signals: list[str]) -> pd.Series:
    columns: dict[str, pd.Series] = {}
    for signal in signals:
        columns[signal] = inputs.canonical[signal]
        for suffix in QUALITY_SUFFIXES:
            flag = f"{signal}_{suffix}"
            columns[flag] = inputs.quality[flag]
    return build_quality_valid_mask(pd.DataFrame(columns), signals)


def build_calibrated_features(inputs: CalibratedInputs) -> pd.DataFrame:
    """Apply frozen numeric parameters; no fitting path exists in this stage."""

    _validate_b1b_contract(inputs.feature_contract)
    transforms = _validate_registry(inputs.registry)
    canonical = inputs.canonical
    output = canonical[KEY_COLUMNS].copy()

    speed = transforms["speed_density_maf"]
    required = ["maf", "map", "rpm", "intake_temp"]
    speed_valid = _quality_valid_mask(inputs, required)
    numeric = {name: pd.to_numeric(canonical[name], errors="coerce") for name in required}
    denominator = numeric["intake_temp"] + 273.15
    raw_load = numeric["rpm"] * numeric["map"] / denominator
    finite_raw = raw_load.map(math.isfinite)
    speed_valid &= denominator.ne(0) & finite_raw
    model_inputs = {
        "map_derived_air_load_raw": raw_load,
        "map": numeric["map"],
        "rpm": numeric["rpm"],
        "intake_temp": numeric["intake_temp"],
    }
    expected = pd.Series(
        _finite_number(speed["intercept"], label="speed-density intercept"),
        index=canonical.index,
        dtype="float64",
    )
    for name in speed["ordered_input_features"]:
        bound = speed["prediction_clipping_bounds"][name]
        clipped = model_inputs[name].clip(
            lower=float(bound["lower"]), upper=float(bound["upper"])
        )
        expected += float(speed["coefficients"][name]) * clipped
    output["speed_density_maf_residual"] = (
        numeric["maf"] - expected
    ).where(speed_valid)

    pedal = transforms["pedal_mapping"]
    pedal_signals = ["accel_pedal_d", "accel_pedal_e"]
    pedal_valid = _quality_valid_mask(inputs, pedal_signals)
    pedal_d = pd.to_numeric(canonical["accel_pedal_d"], errors="coerce")
    pedal_e = pd.to_numeric(canonical["accel_pedal_e"], errors="coerce")
    output["pedal_mapping_residual"] = (
        pedal_e - (float(pedal["a"]) * pedal_d + float(pedal["b"]))
    ).where(pedal_valid)
    output = output[[*KEY_COLUMNS, *B1B_COLUMNS]]
    if not output[KEY_COLUMNS].equals(canonical[KEY_COLUMNS]):
        raise CalibratedFeatureError("Calibrated feature keys changed unexpectedly.")
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
        raise CalibratedFeatureError(f"Cannot write calibrated-feature CSV: {exc}") from exc


def _run_descriptor(
    path: Path, *, artifact_id: str, run_layout: RunLayout
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path, artifact_id=artifact_id,
        manifest_path=run_layout.run_relative_posix(path), path_base="run_dir"
    )


def _repo_descriptor(
    path: Path, *, artifact_id: str, run_layout: RunLayout
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path, artifact_id=artifact_id,
        manifest_path=repo_relative_posix(path, repo_root=run_layout.repo_root),
        path_base="repo_root",
    )


def run_calibrated_feature_builder(
    run_layout: RunLayout, *, creation_time_utc: str | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build Script 40 output and its calibration-bound stage manifest."""

    inputs = load_calibrated_inputs(run_layout)
    b1b_contract = _validate_b1b_contract(inputs.feature_contract)
    output = build_calibrated_features(inputs)
    _write_csv_atomic(run_layout.calibrated_features, output)
    stage_00_inputs = _descriptor_map(
        inputs.input_contract_manifest, "ordered_input_artifacts"
    )
    input_artifacts = [
        stage_00_inputs["feature_contract"],
        _repo_descriptor(
            run_layout.calibration_registry,
            artifact_id="calibration_registry",
            run_layout=run_layout,
        ),
        _repo_descriptor(
            run_layout.calibration_release_manifest,
            artifact_id="calibration_release_manifest",
            run_layout=run_layout,
        ),
        _run_descriptor(
            run_layout.input_contract_manifest,
            artifact_id="input_contract_manifest",
            run_layout=run_layout,
        ),
        _run_descriptor(
            run_layout.atomic_features_manifest,
            artifact_id="atomic_features_manifest",
            run_layout=run_layout,
        ),
        stage_00_inputs["operating_condition_enriched"],
        stage_00_inputs["cleaning_quality"],
        _run_descriptor(
            run_layout.atomic_features,
            artifact_id="atomic_features",
            run_layout=run_layout,
        ),
    ]
    output_descriptor = _run_descriptor(
        run_layout.calibrated_features,
        artifact_id="calibrated_features",
        run_layout=run_layout,
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=inputs.feature_contract["schema_version"],
        script_version=SCRIPT_VERSION,
        source_dataset_identity=inputs.input_contract_manifest[
            "source_dataset_identity"
        ],
        input_artifacts=input_artifacts,
        output_artifacts=[output_descriptor],
        calibration_version=inputs.registry["calibration_version"],
        creation_time_utc=creation_time_utc,
    )
    manifest["calibration_contract"] = {
        "registry_schema_version": inputs.registry["registry_schema_version"],
        "registry_sha256": sha256_file(run_layout.calibration_registry),
        "release_manifest_version": inputs.release_manifest["manifest_version"],
        "application_mode": "predict_only",
        "fit_allowed": False,
        "hidden_intermediates_emitted": False,
    }
    manifest["output_contract"] = {
        "grain": "sample",
        "key_columns": KEY_COLUMNS,
        "feature_columns": b1b_contract,
        "ordered_columns": list(output.columns),
        "row_count": int(len(output)),
        "ordered_sample_keys_sha256": _ordered_key_sha256(output[KEY_COLUMNS]),
        "null_counts": {
            column: int(output[column].isna().sum()) for column in B1B_COLUMNS
        },
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=inputs.feature_contract["schema_version"],
        expected_calibration_version=CALIBRATION_VERSION,
    )
    write_json_atomic(run_layout.calibrated_features_manifest, manifest)
    return output, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply frozen calibration transforms to sample data."
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
        output, manifest = run_calibrated_feature_builder(run_layout)
    except (
        CalibratedFeatureError, ManifestError, ManifestValidationError,
        OSError, KeyError, ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "calibrated_features": run_layout.run_relative_posix(
            run_layout.calibrated_features
        ),
        "manifest": run_layout.run_relative_posix(
            run_layout.calibrated_features_manifest
        ),
        "sample_rows": int(len(output)),
        "calibration_version": manifest["calibration_version"],
        "source_dataset_identity": manifest["source_dataset_identity"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
