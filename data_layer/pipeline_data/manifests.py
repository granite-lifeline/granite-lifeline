"""Versioned JSON, hashing, identity, and column-contract utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


class ManifestError(RuntimeError):
    """Base error for manifest I/O and validation."""


class ManifestValidationError(ManifestError):
    """Raised when a manifest or ordered schema violates its contract."""


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DATASET_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_STAGE_ID_PATTERN = re.compile(r"^(?:[0-9]{2}|cleaning|operating_conditions)$")
_PATH_BASES = frozenset({"run_dir", "repo_root"})


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest of a file."""

    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(target)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for identities and regression checks."""

    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ManifestValidationError(f"Value is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON document and require an object at its root."""

    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Cannot load JSON object from {target}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestValidationError(f"JSON root must be an object: {target}")
    return value


def write_json_atomic(path: str | Path, value: Mapping[str, Any]) -> Path:
    """Write stable UTF-8/LF JSON and atomically replace the target."""

    if not isinstance(value, Mapping):
        raise ManifestValidationError("Manifest root must be a mapping.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(
                dict(value),
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except (OSError, TypeError, ValueError) as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ManifestError(f"Cannot atomically write {target}: {exc}") from exc
    return target


def _validate_manifest_path(path: str) -> None:
    if not path or "\\" in path or re.match(r"^[A-Za-z]:", path):
        raise ManifestValidationError(
            f"Manifest path must be a relative POSIX path: {path!r}."
        )
    pure = PurePosixPath(path)
    if (
        pure.is_absolute()
        or pure.as_posix() != path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise ManifestValidationError(
            f"Manifest path must be a normalized relative POSIX path: {path!r}."
        )


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    """Portable identity and integrity metadata for one artifact."""

    artifact_id: str
    path: str
    path_base: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not self.artifact_id or not isinstance(self.artifact_id, str):
            raise ManifestValidationError("artifact_id must be a non-empty string.")
        _validate_manifest_path(self.path)
        if self.path_base not in _PATH_BASES:
            raise ManifestValidationError(
                f"path_base must be one of {sorted(_PATH_BASES)}."
            )
        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ManifestValidationError(f"Invalid SHA-256: {self.sha256!r}.")
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ManifestValidationError("size_bytes must be a non-negative int.")

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        *,
        artifact_id: str,
        manifest_path: str,
        path_base: str,
    ) -> "ArtifactDescriptor":
        target = Path(file_path)
        if not target.is_file():
            raise FileNotFoundError(target)
        return cls(
            artifact_id=artifact_id,
            path=manifest_path,
            path_base=path_base,
            sha256=sha256_file(target),
            size_bytes=target.stat().st_size,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactDescriptor":
        try:
            return cls(
                artifact_id=value["artifact_id"],
                path=value["path"],
                path_base=value["path_base"],
                sha256=value["sha256"],
                size_bytes=value["size_bytes"],
            )
        except (KeyError, TypeError) as exc:
            raise ManifestValidationError(
                f"Invalid artifact descriptor: {value!r}."
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "path_base": self.path_base,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def _as_descriptor(value: ArtifactDescriptor | Mapping[str, Any]) -> ArtifactDescriptor:
    if isinstance(value, ArtifactDescriptor):
        return value
    return ArtifactDescriptor.from_mapping(value)


def compute_source_dataset_identity(
    artifacts: Sequence[ArtifactDescriptor | Mapping[str, Any]],
) -> str:
    """Build an order-independent identity from logical IDs and checksums.

    Local absolute paths and file modification times are intentionally excluded.
    """

    descriptors = [_as_descriptor(value) for value in artifacts]
    if not descriptors:
        raise ManifestValidationError(
            "At least one artifact is required for source dataset identity."
        )
    identities = [
        {"artifact_id": item.artifact_id, "sha256": item.sha256}
        for item in descriptors
    ]
    if len({item["artifact_id"] for item in identities}) != len(identities):
        raise ManifestValidationError("Dataset artifact IDs must be unique.")
    digest = hashlib.sha256(
        canonical_json_bytes(sorted(identities, key=lambda item: item["artifact_id"]))
    ).hexdigest()
    return f"sha256:{digest}"


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def build_stage_manifest(
    *,
    stage_id: str,
    schema_version: str,
    script_version: str,
    source_dataset_identity: str,
    input_artifacts: Sequence[ArtifactDescriptor | Mapping[str, Any]],
    output_artifacts: Sequence[ArtifactDescriptor | Mapping[str, Any]],
    calibration_version: str | None = None,
    creation_time_utc: str | None = None,
    manifest_version: str = "1.0.0",
) -> dict[str, Any]:
    """Construct and validate a portable stage-output manifest."""

    inputs = [_as_descriptor(value) for value in input_artifacts]
    outputs = [_as_descriptor(value) for value in output_artifacts]
    all_artifacts = inputs + outputs
    paths = [item.path for item in all_artifacts]
    if len(paths) != len(set(paths)):
        raise ManifestValidationError("Artifact paths must be unique in a manifest.")
    manifest = {
        "manifest_type": "data_layer_stage_output",
        "manifest_version": manifest_version,
        "stage_id": stage_id,
        "schema_version": schema_version,
        "source_dataset_identity": source_dataset_identity,
        "script_version": script_version,
        "creation_time_utc": creation_time_utc or _utc_now_text(),
        "calibration_version": calibration_version or "not_applicable",
        "ordered_input_artifacts": [item.to_dict() for item in inputs],
        "ordered_output_artifacts": [item.to_dict() for item in outputs],
        "artifact_sha256": {item.path: item.sha256 for item in all_artifacts},
    }
    validate_stage_manifest(manifest)
    return manifest


def _validate_utc_timestamp(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ManifestValidationError("creation_time_utc must be an ISO 8601 UTC string.")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestValidationError(
            "creation_time_utc must be an ISO 8601 UTC string."
        ) from exc


def validate_stage_manifest(
    manifest: Mapping[str, Any],
    *,
    expected_schema_version: str | None = None,
    expected_calibration_version: str | None = None,
) -> None:
    """Validate minimum metadata and artifact integrity declarations."""

    required = {
        "manifest_type",
        "manifest_version",
        "stage_id",
        "schema_version",
        "source_dataset_identity",
        "script_version",
        "creation_time_utc",
        "calibration_version",
        "ordered_input_artifacts",
        "ordered_output_artifacts",
        "artifact_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ManifestValidationError(f"Missing manifest fields: {missing}.")
    if manifest["manifest_type"] != "data_layer_stage_output":
        raise ManifestValidationError("Unexpected manifest_type.")
    if not isinstance(manifest["stage_id"], str) or not _STAGE_ID_PATTERN.fullmatch(
        manifest["stage_id"]
    ):
        raise ManifestValidationError(f"Invalid stage_id: {manifest['stage_id']!r}.")
    for key in ("manifest_version", "schema_version", "script_version"):
        if not isinstance(manifest[key], str) or not manifest[key]:
            raise ManifestValidationError(f"{key} must be a non-empty string.")
    if not _DATASET_ID_PATTERN.fullmatch(str(manifest["source_dataset_identity"])):
        raise ManifestValidationError("Invalid source_dataset_identity.")
    _validate_utc_timestamp(manifest["creation_time_utc"])
    calibration = manifest["calibration_version"]
    if not isinstance(calibration, str) or not calibration:
        raise ManifestValidationError("calibration_version must be a non-empty string.")
    if expected_schema_version and manifest["schema_version"] != expected_schema_version:
        raise ManifestValidationError("schema_version does not match the expected contract.")
    if (
        expected_calibration_version
        and calibration != expected_calibration_version
    ):
        raise ManifestValidationError(
            "calibration_version does not match the expected contract."
        )

    descriptors: list[ArtifactDescriptor] = []
    for key in ("ordered_input_artifacts", "ordered_output_artifacts"):
        values = manifest[key]
        if not isinstance(values, list):
            raise ManifestValidationError(f"{key} must be a list.")
        descriptors.extend(ArtifactDescriptor.from_mapping(value) for value in values)
    ids = [item.artifact_id for item in descriptors]
    paths = [item.path for item in descriptors]
    if len(ids) != len(set(ids)):
        raise ManifestValidationError("Artifact IDs must be unique in a manifest.")
    if len(paths) != len(set(paths)):
        raise ManifestValidationError("Artifact paths must be unique in a manifest.")
    expected_hashes = {item.path: item.sha256 for item in descriptors}
    if manifest["artifact_sha256"] != expected_hashes:
        raise ManifestValidationError("artifact_sha256 does not match artifact records.")


def verify_manifest_artifacts(
    manifest: Mapping[str, Any],
    *,
    run_dir: str | Path,
    repo_root: str | Path,
) -> None:
    """Recompute every declared artifact hash and size from its path base."""

    validate_stage_manifest(manifest)
    bases = {
        "run_dir": Path(run_dir).resolve(strict=False),
        "repo_root": Path(repo_root).resolve(strict=False),
    }
    for key in ("ordered_input_artifacts", "ordered_output_artifacts"):
        for value in manifest[key]:
            item = ArtifactDescriptor.from_mapping(value)
            base = bases[item.path_base]
            target = (base / PurePosixPath(item.path)).resolve(strict=False)
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise ManifestValidationError(
                    f"Artifact escapes {item.path_base}: {item.path}."
                ) from exc
            if not target.is_file():
                raise ManifestValidationError(f"Artifact is missing: {item.path}.")
            if sha256_file(target) != item.sha256:
                raise ManifestValidationError(
                    f"Artifact checksum mismatch: {item.path}."
                )
            if target.stat().st_size != item.size_bytes:
                raise ManifestValidationError(f"Artifact size mismatch: {item.path}.")


def ordered_column_contract_from_feature_manifest(
    feature_manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Return the contracted keys/context/features/provenance in CSV order."""

    try:
        sections = (
            feature_manifest["sample_keys"],
            feature_manifest["context_fields"],
            feature_manifest["features"],
            feature_manifest["provenance_columns"],
        )
    except KeyError as exc:
        raise ManifestValidationError(
            f"Feature manifest is missing ordered column section {exc}."
        ) from exc
    fields = tuple(dict(field) for section in sections for field in section)
    if feature_manifest.get("total_column_count") != len(fields):
        raise ManifestValidationError("total_column_count does not match ordered fields.")
    names = [field.get("name") for field in fields]
    if any(not isinstance(name, str) or not name for name in names):
        raise ManifestValidationError("Every ordered field must have a name.")
    if len(names) != len(set(names)):
        raise ManifestValidationError("Ordered feature columns must be unique.")
    return fields


def validate_ordered_column_contract(
    actual_fields: Sequence[Mapping[str, Any]],
    expected_fields: Sequence[Mapping[str, Any]],
) -> None:
    """Validate exact field order and all declared type/unit/nullability metadata."""

    if len(actual_fields) != len(expected_fields):
        raise ManifestValidationError(
            f"Column count mismatch: expected {len(expected_fields)}, "
            f"received {len(actual_fields)}."
        )
    always = ("name", "dtype", "nullable")
    optional_when_declared = ("unit", "class", "constant_value")
    for position, (actual, expected) in enumerate(
        zip(actual_fields, expected_fields, strict=True), start=1
    ):
        for attribute in always:
            if attribute not in expected:
                raise ManifestValidationError(
                    f"Expected field {position} lacks {attribute}."
                )
            if actual.get(attribute) != expected[attribute]:
                raise ManifestValidationError(
                    f"Column {position} {attribute} mismatch for "
                    f"{expected.get('name')!r}: expected {expected[attribute]!r}, "
                    f"received {actual.get(attribute)!r}."
                )
        for attribute in optional_when_declared:
            if attribute in expected and actual.get(attribute) != expected[attribute]:
                raise ManifestValidationError(
                    f"Column {position} {attribute} mismatch for "
                    f"{expected.get('name')!r}: expected {expected[attribute]!r}, "
                    f"received {actual.get(attribute)!r}."
                )
