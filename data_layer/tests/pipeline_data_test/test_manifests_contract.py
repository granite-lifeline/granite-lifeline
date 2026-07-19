from pathlib import Path

import pytest

from data_layer.pipeline_data.manifests import (
    ArtifactDescriptor,
    ManifestError,
    ManifestValidationError,
    build_stage_manifest,
    canonical_json_bytes,
    compute_source_dataset_identity,
    load_json_object,
    ordered_column_contract_from_feature_manifest,
    sha256_file,
    validate_ordered_column_contract,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)


def _descriptor(
    path: Path,
    *,
    artifact_id: str,
    manifest_path: str,
    path_base: str = "run_dir",
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path,
        artifact_id=artifact_id,
        manifest_path=manifest_path,
        path_base=path_base,
    )


def test_sha256_and_canonical_json_are_deterministic(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.csv"
    artifact.write_bytes(b"a,b\n1,2\n")

    assert sha256_file(artifact) == (
        "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470"
    )
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_atomic_json_round_trip_is_stable(tmp_path: Path) -> None:
    target = tmp_path / "nested/manifest.json"
    value = {"z": 1, "a": {"unicode": "温度"}}

    write_json_atomic(target, value)
    first = target.read_bytes()
    write_json_atomic(target, value)

    assert target.read_bytes() == first
    assert first.endswith(b"\n")
    assert b"\r\n" not in first
    assert load_json_object(target) == value
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []


def test_json_loader_rejects_non_object_root(tmp_path: Path) -> None:
    target = tmp_path / "array.json"
    target.write_text("[]", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="root must be an object"):
        load_json_object(target)


def test_dataset_identity_ignores_input_order_and_local_paths(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    a = _descriptor(
        first,
        artifact_id="operating_condition_enriched",
        manifest_path="operating_conditions/operating_condition_enriched.csv",
    )
    b = _descriptor(
        second,
        artifact_id="cleaning_quality",
        manifest_path="cleaning/cleaning_quality.csv",
    )
    relocated = ArtifactDescriptor(
        artifact_id=a.artifact_id,
        path="some_other_run/renamed.csv",
        path_base="repo_root",
        sha256=a.sha256,
        size_bytes=a.size_bytes,
    )

    assert compute_source_dataset_identity([a, b]) == compute_source_dataset_identity(
        [b, relocated]
    )


def test_dataset_identity_requires_at_least_one_artifact() -> None:
    with pytest.raises(ManifestValidationError, match="At least one artifact"):
        compute_source_dataset_identity([])


def test_stage_manifest_build_validate_and_verify(tmp_path: Path) -> None:
    run_dir = tmp_path / "data/processed/runs/run_1"
    repo_contract = tmp_path / "data_layer/contracts/feature_manifest.v1.json"
    input_path = run_dir / "cleaning/cleaning_quality.csv"
    output_path = run_dir / "features/10_atomic/atomic_features.csv"
    for path, text in (
        (repo_contract, "{}\n"),
        (input_path, "quality\n"),
        (output_path, "atomic\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    contract = _descriptor(
        repo_contract,
        artifact_id="feature_contract",
        manifest_path="data_layer/contracts/feature_manifest.v1.json",
        path_base="repo_root",
    )
    source = _descriptor(
        input_path,
        artifact_id="cleaning_quality",
        manifest_path="cleaning/cleaning_quality.csv",
    )
    output = _descriptor(
        output_path,
        artifact_id="atomic_features",
        manifest_path="features/10_atomic/atomic_features.csv",
    )
    dataset_id = compute_source_dataset_identity([source])
    manifest = build_stage_manifest(
        stage_id="10",
        schema_version="feature_schema.v1",
        script_version="10.0.0",
        source_dataset_identity=dataset_id,
        input_artifacts=[contract, source],
        output_artifacts=[output],
        calibration_version=None,
        creation_time_utc="2026-07-19T12:00:00Z",
    )

    validate_stage_manifest(
        manifest,
        expected_schema_version="feature_schema.v1",
        expected_calibration_version="not_applicable",
    )
    verify_manifest_artifacts(manifest, run_dir=run_dir, repo_root=tmp_path)
    assert manifest["calibration_version"] == "not_applicable"
    assert list(manifest["artifact_sha256"]) == [
        "data_layer/contracts/feature_manifest.v1.json",
        "cleaning/cleaning_quality.csv",
        "features/10_atomic/atomic_features.csv",
    ]

    output_path.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        verify_manifest_artifacts(manifest, run_dir=run_dir, repo_root=tmp_path)


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escape.csv",
        "/absolute.csv",
        "C:/absolute.csv",
        "bad\\windows.csv",
        "not//normalized.csv",
    ],
)
def test_artifact_descriptor_rejects_nonportable_paths(bad_path: str) -> None:
    with pytest.raises(ManifestValidationError, match="relative POSIX"):
        ArtifactDescriptor(
            artifact_id="bad",
            path=bad_path,
            path_base="run_dir",
            sha256="0" * 64,
            size_bytes=0,
        )


def test_stage_manifest_rejects_hash_map_drift(tmp_path: Path) -> None:
    output_path = tmp_path / "output.csv"
    output_path.write_text("output", encoding="utf-8")
    output = _descriptor(
        output_path,
        artifact_id="output",
        manifest_path="features/10_atomic/output.csv",
    )
    manifest = build_stage_manifest(
        stage_id="10",
        schema_version="feature_schema.v1",
        script_version="1.0.0",
        source_dataset_identity="sha256:" + "1" * 64,
        input_artifacts=[],
        output_artifacts=[output],
        creation_time_utc="2026-07-19T12:00:00Z",
    )
    manifest["artifact_sha256"][output.path] = "2" * 64

    with pytest.raises(ManifestValidationError, match="artifact_sha256"):
        validate_stage_manifest(manifest)


def test_validation_only_stage_may_have_no_non_manifest_output(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "quality.csv"
    source_path.write_text("quality", encoding="utf-8")
    source = _descriptor(
        source_path,
        artifact_id="cleaning_quality",
        manifest_path="cleaning/cleaning_quality.csv",
    )

    manifest = build_stage_manifest(
        stage_id="00",
        schema_version="feature_schema.v1",
        script_version="1.0.0",
        source_dataset_identity=compute_source_dataset_identity([source]),
        input_artifacts=[source],
        output_artifacts=[],
        creation_time_utc="2026-07-19T12:00:00Z",
    )

    validate_stage_manifest(manifest)
    assert manifest["ordered_output_artifacts"] == []


def test_ordered_feature_contract_rejects_order_and_dtype_changes() -> None:
    feature_manifest = {
        "sample_keys": [
            {"name": "timestamp", "dtype": "datetime64[ns, UTC]", "unit": "UTC", "nullable": False}
        ],
        "context_fields": [
            {"name": "dt_seconds", "dtype": "float64", "unit": "s", "nullable": False}
        ],
        "features": [
            {"name": "engine_on_flag", "dtype": "boolean", "unit": "boolean", "nullable": True}
        ],
        "provenance_columns": [
            {"name": "schema_version", "dtype": "string", "nullable": False, "constant_value": "feature_schema.v1"}
        ],
        "total_column_count": 4,
    }
    expected = ordered_column_contract_from_feature_manifest(feature_manifest)

    validate_ordered_column_contract([dict(field) for field in expected], expected)
    reordered = [dict(field) for field in expected]
    reordered[1], reordered[2] = reordered[2], reordered[1]
    with pytest.raises(ManifestValidationError, match="name mismatch"):
        validate_ordered_column_contract(reordered, expected)
    wrong_dtype = [dict(field) for field in expected]
    wrong_dtype[2]["dtype"] = "float64"
    with pytest.raises(ManifestValidationError, match="dtype mismatch"):
        validate_ordered_column_contract(wrong_dtype, expected)


def test_atomic_writer_rejects_non_json_values(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="Cannot atomically write"):
        write_json_atomic(tmp_path / "bad.json", {"bad": float("nan")})
