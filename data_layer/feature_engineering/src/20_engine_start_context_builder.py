"""Build observed engine-start sample context and authoritative episodes."""

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
    load_json_object,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


SCRIPT_VERSION = "1.0.0"
STAGE_ID = "20"
KEY_COLUMNS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
B2_COLUMNS = [
    "engine_start_observed",
    "engine_start_episode_id",
    "elapsed_since_engine_start",
    "ect_start",
    "aat_start",
    "iat_start",
]
EPISODE_COLUMNS = [
    "trip_id",
    "engine_start_episode_id",
    "segment_id",
    "continuity_block_id",
    "start_timestamp",
    "start_row_in_segment",
    "end_timestamp",
    "end_row_in_segment",
    "episode_sample_count",
    "episode_duration_seconds",
    "termination_reason",
    "ect_start",
    "aat_start",
    "iat_start",
]
EPISODE_CONTRACT = [
    {"name": "trip_id", "dtype": "string", "unit": "identifier", "nullable": False},
    {
        "name": "engine_start_episode_id",
        "dtype": "string",
        "unit": "identifier",
        "nullable": False,
    },
    {"name": "segment_id", "dtype": "string", "unit": "identifier", "nullable": False},
    {
        "name": "continuity_block_id",
        "dtype": "int64",
        "unit": "identifier",
        "nullable": False,
    },
    {"name": "start_timestamp", "dtype": "string", "unit": "UTC", "nullable": False},
    {
        "name": "start_row_in_segment",
        "dtype": "int64",
        "unit": "1-based row index",
        "nullable": False,
    },
    {"name": "end_timestamp", "dtype": "string", "unit": "UTC", "nullable": False},
    {
        "name": "end_row_in_segment",
        "dtype": "int64",
        "unit": "1-based row index",
        "nullable": False,
    },
    {
        "name": "episode_sample_count",
        "dtype": "int64",
        "unit": "samples",
        "nullable": False,
    },
    {
        "name": "episode_duration_seconds",
        "dtype": "float64",
        "unit": "s",
        "nullable": False,
    },
    {
        "name": "termination_reason",
        "dtype": "string",
        "unit": "categorical",
        "nullable": False,
    },
    {"name": "ect_start", "dtype": "float64", "unit": "degC", "nullable": True},
    {"name": "aat_start", "dtype": "float64", "unit": "degC", "nullable": True},
    {"name": "iat_start", "dtype": "float64", "unit": "degC", "nullable": True},
]
QUALITY_SUFFIXES = (
    "is_imputed",
    "is_suspicious",
    "had_hard_invalid_source",
)


class EngineStartError(RuntimeError):
    """Raised when Script 20 input or episode contracts are invalid."""


@dataclass(frozen=True, slots=True)
class EngineStartInputs:
    canonical: pd.DataFrame
    quality: pd.DataFrame
    atomic: pd.DataFrame
    feature_contract: dict[str, Any]
    input_contract_manifest: dict[str, Any]
    atomic_manifest: dict[str, Any]


def _ordered_key_sha256(keys: pd.DataFrame) -> str:
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(frame: pd.DataFrame, columns: list[str], *, label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise EngineStartError(f"{label} is missing required columns: {missing}.")


def _validate_b2_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    if contract.get("schema_version") != "feature_schema.v1":
        raise EngineStartError("Script 20 requires feature_schema.v1.")
    features = contract.get("features")
    if not isinstance(features, list) or len(features) < 16:
        raise EngineStartError("Feature contract does not contain six B2 fields.")
    b2 = features[10:16]
    if [item.get("name") for item in b2] != B2_COLUMNS:
        raise EngineStartError("B2 feature name/order contract has drifted.")
    expected_types = ["boolean", "string", "float64", "float64", "float64", "float64"]
    for offset, (item, expected_type) in enumerate(zip(b2, expected_types), start=11):
        if (
            item.get("position") != offset
            or item.get("class") != "B2"
            or item.get("dtype") != expected_type
            or item.get("owner_script") != "20_engine_start_context_builder.py"
            or item.get("nullable") is not True
        ):
            raise EngineStartError(f"B2 contract has drifted at position {offset}.")
    return [dict(item) for item in b2]


def _descriptor_map(
    manifest: dict[str, Any], key: str
) -> dict[str, ArtifactDescriptor]:
    return {
        item["artifact_id"]: ArtifactDescriptor.from_mapping(item)
        for item in manifest[key]
    }


def _nullable_boolean(series: pd.Series, *, label: str) -> pd.Series:
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
        lambda value: (
            pd.NA
            if pd.isna(value)
            else mapping.get(
                value.strip().casefold() if isinstance(value, str) else value,
                "invalid",
            )
        )
    )
    invalid = normalized.eq("invalid")
    if invalid.any():
        raise EngineStartError(f"{label} contains invalid boolean values.")
    return normalized.astype("boolean")


def load_engine_start_inputs(run_layout: RunLayout) -> EngineStartInputs:
    """Verify stages 00/10 and align canonical, quality, and atomic rows."""

    input_manifest = load_json_object(run_layout.input_contract_manifest)
    atomic_manifest = load_json_object(run_layout.atomic_features_manifest)
    for manifest, stage in ((input_manifest, "00"), (atomic_manifest, "10")):
        validate_stage_manifest(
            manifest,
            expected_schema_version="feature_schema.v1",
            expected_calibration_version="not_applicable",
        )
        if manifest.get("stage_id") != stage:
            raise EngineStartError(f"Expected stage {stage} manifest.")
        verify_manifest_artifacts(
            manifest,
            run_dir=run_layout.run_dir,
            repo_root=run_layout.repo_root,
        )
    if atomic_manifest["source_dataset_identity"] != input_manifest[
        "source_dataset_identity"
    ]:
        raise EngineStartError("Stage 00/10 source dataset identities differ.")

    stage_00_inputs = _descriptor_map(input_manifest, "ordered_input_artifacts")
    if set(stage_00_inputs) != {
        "feature_contract",
        "operating_condition_enriched",
        "cleaning_quality",
    }:
        raise EngineStartError("Stage 00 authoritative inputs have drifted.")
    stage_10_outputs = _descriptor_map(atomic_manifest, "ordered_output_artifacts")
    if set(stage_10_outputs) != {"atomic_features"}:
        raise EngineStartError("Stage 10 must have exactly one atomic output.")

    feature_contract = load_json_object(run_layout.feature_contract)
    _validate_b2_contract(feature_contract)
    summary_00 = input_manifest.get("validation_summary", {})
    contract_10 = atomic_manifest.get("output_contract", {})
    canonical_columns = summary_00.get("canonical_column_order")
    quality_columns = summary_00.get("quality_column_order")
    atomic_columns = contract_10.get("ordered_columns")
    if not all(
        isinstance(value, list)
        for value in (canonical_columns, quality_columns, atomic_columns)
    ):
        raise EngineStartError("Upstream ordered-column metadata is missing.")

    try:
        operating = pd.read_csv(
            run_layout.operating_condition_enriched, low_memory=False
        )
        quality = pd.read_csv(run_layout.cleaning_quality, low_memory=False)
        atomic = pd.read_csv(run_layout.atomic_features, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise EngineStartError(f"Cannot read Script 20 inputs: {exc}") from exc
    _require_columns(operating, canonical_columns, label="canonical input")
    _require_columns(quality, quality_columns, label="quality input")
    if list(atomic.columns) != atomic_columns:
        raise EngineStartError("Atomic CSV column order has drifted.")

    key_union = operating[KEY_COLUMNS].merge(
        quality[KEY_COLUMNS],
        on=KEY_COLUMNS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not key_union["_merge"].eq("both").all():
        raise EngineStartError("Canonical and quality key sets differ.")
    ordered_keys = key_union[KEY_COLUMNS].sort_values(
        KEY_COLUMNS, kind="stable"
    ).reset_index(drop=True)
    if _ordered_key_sha256(ordered_keys) != summary_00.get(
        "ordered_sample_keys_sha256"
    ):
        raise EngineStartError("Stage 00 ordered key identity has drifted.")

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
    aligned_atomic = ordered_keys.merge(
        atomic,
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if _ordered_key_sha256(aligned_atomic[KEY_COLUMNS]) != contract_10.get(
        "ordered_sample_keys_sha256"
    ):
        raise EngineStartError("Stage 10 ordered key identity has drifted.")
    aligned_atomic["engine_on_flag"] = _nullable_boolean(
        aligned_atomic["engine_on_flag"], label="atomic.engine_on_flag"
    )
    return EngineStartInputs(
        canonical=canonical,
        quality=aligned_quality,
        atomic=aligned_atomic,
        feature_contract=feature_contract,
        input_contract_manifest=input_manifest,
        atomic_manifest=atomic_manifest,
    )


def _signal_valid_mask(
    canonical: pd.DataFrame,
    quality: pd.DataFrame,
    signal: str,
) -> pd.Series:
    columns: dict[str, pd.Series] = {signal: canonical[signal]}
    for suffix in QUALITY_SUFFIXES:
        flag = f"{signal}_{suffix}"
        columns[flag] = quality[flag]
    return build_quality_valid_mask(pd.DataFrame(columns), [signal])


def _empty_episode_table() -> pd.DataFrame:
    return pd.DataFrame(
        {column: pd.Series(dtype="object") for column in EPISODE_COLUMNS}
    )


def build_engine_start_context(
    inputs: EngineStartInputs,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detect observed starts, build episodes, and map episode start values."""

    _validate_b2_contract(inputs.feature_contract)
    canonical = inputs.canonical
    engine_on = inputs.atomic["engine_on_flag"].astype("boolean")
    rpm_valid = engine_on.notna()
    continuity = build_continuity_blocks(canonical, valid_mask=rpm_valid)
    crossing = (
        continuity.continues_previous
        & engine_on.eq(True).fillna(False)
        & engine_on.shift().eq(False).fillna(False)
    )

    observed = pd.Series(pd.NA, index=canonical.index, dtype="boolean")
    observed.loc[rpm_valid] = False
    observed.loc[crossing] = True
    episode_ids = pd.Series(pd.NA, index=canonical.index, dtype="string")
    elapsed = pd.Series(float("nan"), index=canonical.index, dtype="float64")

    temperature_valid = {
        "ect_start": _signal_valid_mask(
            canonical, inputs.quality, "coolant_temp"
        ),
        "aat_start": _signal_valid_mask(
            canonical, inputs.quality, "ambient_temp"
        ),
        "iat_start": _signal_valid_mask(
            canonical, inputs.quality, "intake_temp"
        ),
    }
    source_columns = {
        "ect_start": "coolant_temp",
        "aat_start": "ambient_temp",
        "iat_start": "intake_temp",
    }
    timestamps = pd.to_datetime(canonical["timestamp"], utc=True, errors="raise")
    trip_counters: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None

    def close_active(reason: str) -> None:
        nonlocal active
        if active is None:
            return
        start_index = active["start_index"]
        end_index = active["end_index"]
        record = {
            "trip_id": active["trip_id"],
            "engine_start_episode_id": active["episode_id"],
            "segment_id": active["segment_id"],
            "continuity_block_id": active["continuity_block_id"],
            "start_timestamp": canonical.at[start_index, "timestamp"],
            "start_row_in_segment": int(
                canonical.at[start_index, "row_in_segment"]
            ),
            "end_timestamp": canonical.at[end_index, "timestamp"],
            "end_row_in_segment": int(
                canonical.at[end_index, "row_in_segment"]
            ),
            "episode_sample_count": int(active["sample_count"]),
            "episode_duration_seconds": float(
                (timestamps.at[end_index] - timestamps.at[start_index])
                .total_seconds()
            ),
            "termination_reason": reason,
            **active["start_values"],
        }
        records.append(record)
        active = None

    for index in canonical.index:
        if active is not None:
            if not rpm_valid.at[index]:
                close_active("rpm_invalid")
            elif not continuity.continues_previous.at[index]:
                close_active("continuity_break")
            elif not bool(engine_on.at[index]):
                close_active("rpm_below_50")

        if crossing.at[index]:
            trip_id = str(canonical.at[index, "trip_id"])
            trip_counters[trip_id] = trip_counters.get(trip_id, 0) + 1
            episode_id = f"{trip_id}_start_{trip_counters[trip_id]:03d}"
            start_values = {
                target: (
                    float(canonical.at[index, source])
                    if temperature_valid[target].at[index]
                    else float("nan")
                )
                for target, source in source_columns.items()
            }
            active = {
                "trip_id": trip_id,
                "segment_id": str(canonical.at[index, "segment_id"]),
                "continuity_block_id": int(continuity.block_id.at[index]),
                "episode_id": episode_id,
                "start_index": index,
                "end_index": index,
                "sample_count": 1,
                "start_values": start_values,
            }
            episode_ids.at[index] = episode_id
            elapsed.at[index] = 0.0
        elif active is not None:
            active["end_index"] = index
            active["sample_count"] += 1
            episode_ids.at[index] = active["episode_id"]
            elapsed.at[index] = float(
                (timestamps.at[index] - timestamps.at[active["start_index"]])
                .total_seconds()
            )

    close_active("end_of_data")
    episodes = (
        pd.DataFrame.from_records(records, columns=EPISODE_COLUMNS)
        if records
        else _empty_episode_table()
    )

    context = canonical[KEY_COLUMNS].copy()
    context["engine_start_observed"] = observed
    context["engine_start_episode_id"] = episode_ids
    context["elapsed_since_engine_start"] = elapsed
    for column in ("ect_start", "aat_start", "iat_start"):
        mapping = (
            episodes.set_index("engine_start_episode_id")[column]
            if not episodes.empty
            else pd.Series(dtype="float64")
        )
        context[column] = episode_ids.map(mapping).astype("float64")

    if list(context.columns) != [*KEY_COLUMNS, *B2_COLUMNS]:
        raise EngineStartError("Engine-start sample output column order is invalid.")
    if not context[KEY_COLUMNS].equals(canonical[KEY_COLUMNS]):
        raise EngineStartError("Engine-start sample keys changed unexpectedly.")
    observed_episode_ids = context.loc[
        context["engine_start_observed"].eq(True),
        "engine_start_episode_id",
    ]
    if observed_episode_ids.isna().any():
        raise EngineStartError("Observed starts must reference an episode.")
    return context, episodes


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
        raise EngineStartError(f"Cannot write engine-start CSV: {exc}") from exc


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


def run_engine_start_context_builder(
    run_layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build both Script 20 outputs and their adjacent stage manifest."""

    inputs = load_engine_start_inputs(run_layout)
    b2_contract = _validate_b2_contract(inputs.feature_contract)
    context, episodes = build_engine_start_context(inputs)
    _write_csv_atomic(run_layout.engine_start_context, context)
    _write_csv_atomic(run_layout.engine_start_episodes, episodes)

    stage_00_inputs = _descriptor_map(
        inputs.input_contract_manifest, "ordered_input_artifacts"
    )
    input_manifest_descriptor = _descriptor(
        run_layout.input_contract_manifest,
        artifact_id="input_contract_manifest",
        manifest_path=run_layout.run_relative_posix(
            run_layout.input_contract_manifest
        ),
        path_base="run_dir",
    )
    atomic_manifest_descriptor = _descriptor(
        run_layout.atomic_features_manifest,
        artifact_id="atomic_features_manifest",
        manifest_path=run_layout.run_relative_posix(
            run_layout.atomic_features_manifest
        ),
        path_base="run_dir",
    )
    atomic_descriptor = _descriptor(
        run_layout.atomic_features,
        artifact_id="atomic_features",
        manifest_path=run_layout.run_relative_posix(run_layout.atomic_features),
        path_base="run_dir",
    )
    context_descriptor = _descriptor(
        run_layout.engine_start_context,
        artifact_id="engine_start_context",
        manifest_path=run_layout.run_relative_posix(
            run_layout.engine_start_context
        ),
        path_base="run_dir",
    )
    episodes_descriptor = _descriptor(
        run_layout.engine_start_episodes,
        artifact_id="engine_start_episodes",
        manifest_path=run_layout.run_relative_posix(
            run_layout.engine_start_episodes
        ),
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
            stage_00_inputs["feature_contract"],
            input_manifest_descriptor,
            atomic_manifest_descriptor,
            stage_00_inputs["operating_condition_enriched"],
            stage_00_inputs["cleaning_quality"],
            atomic_descriptor,
        ],
        output_artifacts=[context_descriptor, episodes_descriptor],
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    manifest["output_contract"] = {
        "sample_table": {
            "grain": "sample",
            "key_columns": KEY_COLUMNS,
            "feature_columns": b2_contract,
            "ordered_columns": list(context.columns),
            "row_count": int(len(context)),
            "ordered_sample_keys_sha256": _ordered_key_sha256(
                context[KEY_COLUMNS]
            ),
            "null_counts": {
                column: int(context[column].isna().sum()) for column in B2_COLUMNS
            },
        },
        "episode_table": {
            "grain": "engine_start_episode",
            "primary_key": ["trip_id", "engine_start_episode_id"],
            "column_contract": EPISODE_CONTRACT,
            "ordered_columns": EPISODE_COLUMNS,
            "row_count": int(len(episodes)),
            "termination_reason_counts": (
                episodes["termination_reason"].value_counts().sort_index().to_dict()
                if not episodes.empty
                else {}
            ),
        },
    }
    validate_stage_manifest(
        manifest,
        expected_schema_version=inputs.feature_contract["schema_version"],
        expected_calibration_version="not_applicable",
    )
    write_json_atomic(run_layout.engine_start_context_manifest, manifest)
    return context, episodes, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build observed engine-start context and episode tables."
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
        context, episodes, manifest = run_engine_start_context_builder(run_layout)
    except (
        EngineStartError,
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
                "engine_start_context": run_layout.run_relative_posix(
                    run_layout.engine_start_context
                ),
                "engine_start_episodes": run_layout.run_relative_posix(
                    run_layout.engine_start_episodes
                ),
                "manifest": run_layout.run_relative_posix(
                    run_layout.engine_start_context_manifest
                ),
                "sample_rows": int(len(context)),
                "episode_rows": int(len(episodes)),
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
