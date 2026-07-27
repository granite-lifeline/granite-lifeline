"""Build the eight deterministic B1a atomic features for Feature Script 10."""

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
)
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    ManifestError,
    ManifestValidationError,
    build_stage_manifest,
    compute_source_dataset_identity,
    load_json_object,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "10"
KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
ATOMIC_FEATURE_COLUMNS = [
    "segment_gap_seconds",
    "engine_on_flag",
    "coolant_ambient_delta",
    "intake_ambient_delta",
    "accel_pedal_mean",
    "accel_pedal_channel_delta",
    "pedal_slope",
    "rpm_slope",
]
QUALITY_SUFFIXES = (
    "is_imputed",
    "is_suspicious",
    "had_hard_invalid_source",
)


class AtomicFeatureError(RuntimeError):
    """Raised when Script 10 inputs or deterministic outputs are invalid."""


@dataclass(frozen=True, slots=True)
class AtomicInputs:
    """Script 00-validated source tables aligned to frozen global order."""

    canonical: pd.DataFrame
    quality: pd.DataFrame
    feature_contract: dict[str, Any]
    input_contract_manifest: dict[str, Any]


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    label: str,
) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise AtomicFeatureError(
            f"{label} is missing required columns: {missing}.")


def _validate_atomic_feature_contract(
    feature_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    if feature_contract.get("schema_version") != "feature_schema.v1":
        raise AtomicFeatureError("Script 10 requires feature_schema.v1.")
    features = feature_contract.get("features")
    if not isinstance(features, list) or len(features) < 8:
        raise AtomicFeatureError(
            "Feature contract does not contain eight B1a fields.")
    atomic_contract = features[:8]
    atomic_names = [item.get("name") for item in atomic_contract]
    if atomic_names != ATOMIC_FEATURE_COLUMNS:
        raise AtomicFeatureError(
            "B1a feature name/order contract has drifted.")
    for position, item in enumerate(atomic_contract, start=1):
        if (
            item.get("position") != position
            or item.get("class") != "B1a"
            or item.get("owner_script") != "10_atomic_feature_builder.py"
            or item.get("nullable") is not True
        ):
            raise AtomicFeatureError(
                f"B1a feature contract has drifted at position {position}."
            )
    expected_types = [
        "float64",
        "boolean",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
    ]
    if [item.get("dtype") for item in atomic_contract] != expected_types:
        raise AtomicFeatureError("B1a dtype contract has drifted.")
    return [dict(item) for item in atomic_contract]


def _stage_00_data_descriptors(
    manifest: dict[str, Any],
) -> tuple[ArtifactDescriptor, ArtifactDescriptor, ArtifactDescriptor]:
    descriptors = [
        ArtifactDescriptor.from_mapping(item)
        for item in manifest["ordered_input_artifacts"]
    ]
    if [item.artifact_id for item in descriptors] != [
        "feature_contract",
        "operating_condition_enriched",
        "cleaning_quality",
    ]:
        raise AtomicFeatureError(
            "Script 00 manifest must reference the frozen contract and "
            "exactly two authoritative data inputs."
        )
    contract, operating, quality = descriptors
    if (
        contract.path_base != "repo_root"
        or contract.path != "data_layer/contracts/feature_manifest.v1.json"
        or operating.path_base != "run_dir"
        or operating.path
        != "operating_conditions/operating_condition_enriched.csv"
        or quality.path_base != "run_dir"
        or quality.path != "cleaning/cleaning_quality.csv"
    ):
        raise AtomicFeatureError(
            "Script 00 manifest artifact paths have drifted.")
    return contract, operating, quality


def load_atomic_inputs(run_layout: RunLayout) -> AtomicInputs:
    """Verify Script 00 provenance, then restore its validated input order."""

    input_manifest = load_json_object(run_layout.input_contract_manifest)
    validate_stage_manifest(
        input_manifest,
        expected_schema_version="feature_schema.v1",
        expected_calibration_version="not_applicable",
    )
    if input_manifest.get("stage_id") != "00":
        raise AtomicFeatureError(
            "Expected a stage 00 input-contract manifest.")
    verify_manifest_artifacts(
        input_manifest,
        run_dir=run_layout.run_dir,
        repo_root=run_layout.repo_root,
    )
    _, operating_descriptor, quality_descriptor = _stage_00_data_descriptors(
        input_manifest
    )
    expected_identity = compute_source_dataset_identity(
        [operating_descriptor, quality_descriptor]
    )
    if input_manifest.get("source_dataset_identity") != expected_identity:
        raise AtomicFeatureError(
            "Script 00 source dataset identity has drifted.")

    feature_contract = load_json_object(run_layout.feature_contract)
    _validate_atomic_feature_contract(feature_contract)
    summary = input_manifest.get("validation_summary")
    if not isinstance(summary, dict):
        raise AtomicFeatureError(
            "Script 00 manifest lacks validation_summary.")
    canonical_columns = summary.get("canonical_column_order")
    quality_columns = summary.get("quality_column_order")
    if not isinstance(canonical_columns, list) or not isinstance(
        quality_columns, list
    ):
        raise AtomicFeatureError(
            "Script 00 validated column orders are missing.")

    try:
        operating = pd.read_csv(
            run_layout.operating_condition_enriched, low_memory=False
        )
        quality = pd.read_csv(run_layout.cleaning_quality, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise AtomicFeatureError(
            f"Cannot read Script 10 inputs: {exc}") from exc
    _require_columns(operating, canonical_columns, label="canonical input")
    _require_columns(quality, quality_columns, label="quality input")

    keys = operating[KEY_COLUMNS].merge(
        quality[KEY_COLUMNS],
        on=KEY_COLUMNS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not keys["_merge"].eq("both").all():
        raise AtomicFeatureError(
            "Script 00 authoritative key sets no longer match.")
    ordered_keys = keys[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    if _ordered_key_sha256(ordered_keys) != summary.get(
        "ordered_sample_keys_sha256"
    ):
        raise AtomicFeatureError("Ordered sample-key identity has drifted.")

    canonical = ordered_keys.merge(
        operating[canonical_columns],
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    aligned_quality = ordered_keys.merge(
        quality[quality_columns],
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if len(canonical) != summary.get("row_count"):
        raise AtomicFeatureError("Script 00 validated row count has drifted.")
    return AtomicInputs(
        canonical=canonical,
        quality=aligned_quality,
        feature_contract=feature_contract,
        input_contract_manifest=input_manifest,
    )


def _signal_valid_mask(
    canonical: pd.DataFrame,
    quality: pd.DataFrame,
    signals: list[str],
) -> pd.Series:
    columns: dict[str, pd.Series] = {}
    for signal in signals:
        columns[signal] = canonical[signal]
        for suffix in QUALITY_SUFFIXES:
            flag = f"{signal}_{suffix}"
            columns[flag] = quality[flag]
    return build_quality_valid_mask(pd.DataFrame(columns), signals)


def _segment_gap_seconds(canonical: pd.DataFrame) -> pd.Series:
    parsed = pd.to_datetime(canonical["timestamp"], utc=True, errors="raise")
    working = canonical[["trip_id", "segment_id"]].copy()
    working["_timestamp"] = parsed
    working["_output_index"] = range(len(working))
    segments = working.groupby(
        ["trip_id", "segment_id"], sort=False, as_index=False
    ).agg(
        segment_start=("_timestamp", "min"),
        segment_end=("_timestamp", "max"),
        output_index=("_output_index", "first"),
    )
    segments = segments.sort_values(
        ["segment_start", "trip_id", "segment_id"], kind="stable"
    ).reset_index(drop=True)
    previous_end = segments["segment_end"].shift()
    gap = (segments["segment_start"] - previous_end).dt.total_seconds()
    valid_gap = previous_end.notna() & gap.ge(0)

    result = pd.Series(float("nan"), index=canonical.index, dtype="float64")
    result.loc[segments.loc[valid_gap, "output_index"].astype(int)] = gap.loc[
        valid_gap
    ].to_numpy()
    return result


def build_atomic_features(inputs: AtomicInputs) -> pd.DataFrame:
    """Compute the frozen eight B1a formulas without fitting or imputation."""

    canonical = inputs.canonical
    quality = inputs.quality
    _validate_atomic_feature_contract(inputs.feature_contract)
    output = canonical[KEY_COLUMNS].copy()
    output["segment_gap_seconds"] = _segment_gap_seconds(canonical)

    rpm_valid = _signal_valid_mask(canonical, quality, ["rpm"])
    engine_on = pd.Series(pd.NA, index=canonical.index, dtype="boolean")
    engine_on.loc[rpm_valid] = (
        canonical.loc[rpm_valid, "rpm"].ge(50).to_numpy()
    )
    output["engine_on_flag"] = engine_on

    coolant_valid = _signal_valid_mask(
        canonical, quality, ["coolant_temp", "ambient_temp"]
    )
    output["coolant_ambient_delta"] = (
        canonical["coolant_temp"] - canonical["ambient_temp"]
    ).where(coolant_valid)

    intake_valid = _signal_valid_mask(
        canonical, quality, ["intake_temp", "ambient_temp"]
    )
    output["intake_ambient_delta"] = (
        canonical["intake_temp"] - canonical["ambient_temp"]
    ).where(intake_valid)

    pedal_valid = _signal_valid_mask(
        canonical, quality, ["accel_pedal_d", "accel_pedal_e"]
    )
    pedal_mean = (
        canonical["accel_pedal_d"] + canonical["accel_pedal_e"]
    ).div(2).where(pedal_valid)
    output["accel_pedal_mean"] = pedal_mean
    output["accel_pedal_channel_delta"] = (
        canonical["accel_pedal_d"] - canonical["accel_pedal_e"]
    ).abs().where(pedal_valid)

    timestamps = pd.to_datetime(
        canonical["timestamp"], utc=True, errors="raise")
    elapsed = timestamps.diff().dt.total_seconds()
    pedal_continuity = build_continuity_blocks(
        canonical,
        valid_mask=pedal_valid,
    )
    output["pedal_slope"] = pedal_mean.diff().div(elapsed).where(
        pedal_continuity.continues_previous & elapsed.gt(0)
    )
    rpm_continuity = build_continuity_blocks(
        canonical,
        valid_mask=rpm_valid,
    )
    output["rpm_slope"] = canonical["rpm"].diff().div(elapsed).where(
        rpm_continuity.continues_previous & elapsed.gt(0)
    )

    expected_columns = [*KEY_COLUMNS, *ATOMIC_FEATURE_COLUMNS]
    if list(output.columns) != expected_columns:
        raise AtomicFeatureError("Atomic output column order is invalid.")
    if not output[KEY_COLUMNS].equals(canonical[KEY_COLUMNS]):
        raise AtomicFeatureError(
            "Atomic output sample keys changed unexpectedly.")
    return output


def _write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False, float_format="%.15g")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise AtomicFeatureError(
            f"Cannot write atomic feature CSV: {exc}") from exc


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


def run_atomic_feature_builder(
    run_layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build atomic features and their adjacent stage manifest."""

    inputs = load_atomic_inputs(run_layout)
    atomic_contract = _validate_atomic_feature_contract(
        inputs.feature_contract)
    output = build_atomic_features(inputs)
    _write_csv_atomic(run_layout.atomic_features, output)

    stage_00_descriptors = {
        item["artifact_id"]: ArtifactDescriptor.from_mapping(item)
        for item in inputs.input_contract_manifest["ordered_input_artifacts"]
    }
    input_manifest_descriptor = _descriptor(
        run_layout.input_contract_manifest,
        artifact_id="input_contract_manifest",
        manifest_path=run_layout.run_relative_posix(
            run_layout.input_contract_manifest
        ),
        path_base="run_dir",
    )
    output_descriptor = _descriptor(
        run_layout.atomic_features,
        artifact_id="atomic_features",
        manifest_path=run_layout.run_relative_posix(
            run_layout.atomic_features),
        path_base="run_dir",
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=inputs.feature_contract["schema_version"],
        script_version=SCRIPT_VERSION,
        source_dataset_identity=inputs.input_contract_manifest[
            "source_dataset_identity"
        ],
        input_artifacts=[
            stage_00_descriptors["feature_contract"],
            input_manifest_descriptor,
            stage_00_descriptors["operating_condition_enriched"],
            stage_00_descriptors["cleaning_quality"],
        ],
        output_artifacts=[output_descriptor],
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    manifest["output_contract"] = {
        "grain": "sample",
        "key_columns": KEY_COLUMNS,
        "feature_columns": atomic_contract,
        "ordered_columns": list(output.columns),
        "row_count": int(len(output)),
        "ordered_sample_keys_sha256": _ordered_key_sha256(output[KEY_COLUMNS]),
        "null_counts": {
            column: int(output[column].isna().sum())
            for column in ATOMIC_FEATURE_COLUMNS
        },
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=inputs.feature_contract["schema_version"],
        expected_calibration_version="not_applicable",
    )
    write_json_atomic(run_layout.atomic_features_manifest, manifest)
    return output, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the eight deterministic B1a atomic features."
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
        output, manifest = run_atomic_feature_builder(run_layout)
    except (
        AtomicFeatureError,
        ManifestError,
        ManifestValidationError,
        OSError,
        KeyError,
        ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "atomic_features": run_layout.run_relative_posix(
                    run_layout.atomic_features
                ),
                "manifest": run_layout.run_relative_posix(
                    run_layout.atomic_features_manifest
                ),
                "rows": int(len(output)),
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
