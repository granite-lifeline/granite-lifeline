"""Contract tests for the cross-contract lint, incl. drift negative cases."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from data_layer.pipeline_data.contract_lint import run_cross_contract_lint
from data_layer.pipeline_data.manifests import (
    ManifestValidationError,
    sha256_file,
)


REPO_ROOT = Path(__file__).resolve().parents[3]

_BUNDLE_FILES = (
    "data_layer/calibration/calibration_registry.v1.json",
    "data_layer/calibration/calibration_registry.v1.manifest.json",
    "data_layer/contracts/feature_manifest.v1.json",
    "data_layer/feature_engineering/feature_schema.md",
    "data_layer/proxy_failure/proxy_failure_definition.md",
    "data_layer/proxy_failure/proxy_support.md",
)
REGISTRY_REL = "data_layer/calibration/calibration_registry.v1.json"
RELEASE_REL = "data_layer/calibration/calibration_registry.v1.manifest.json"
FEATURE_REL = "data_layer/contracts/feature_manifest.v1.json"


def _make_bundle(tmp_path: Path) -> Path:
    for rel in _BUNDLE_FILES:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / rel, dst)
    return tmp_path


def _read_json(root: Path, rel: str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _write_json(root: Path, rel: str, obj: object) -> None:
    (root / rel).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _repoint_release_hash(root: Path, key: str, rel: str) -> None:
    # Recompute a mutated bundle file's sha256 and repoint the release
    # record so the checksum gate passes and a downstream semantic check
    # is the branch that actually fires.
    release = _read_json(root, RELEASE_REL)
    release[key]["sha256"] = sha256_file(root / rel)
    _write_json(root, RELEASE_REL, release)


def test_frozen_release_bundle_passes_cross_contract_lint() -> None:
    result = run_cross_contract_lint(REPO_ROOT)

    assert result == {
        "ordered_column_count": 46,
        "feature_count": 24,
        "anomaly_type_count": 5,
        "runtime_rule_count": 14,
        "excluded_design_count": 6,
        "release_artifact_count": 5,
        "release_bundle_complete": True,
        "cross_contract_lint_passed": True,
    }


def test_copied_bundle_passes(tmp_path: Path) -> None:
    # Guards the harness itself: a byte-faithful copy must still pass, so any
    # failure below is caused by the mutation under test, not by the copy.
    root = _make_bundle(tmp_path)
    assert run_cross_contract_lint(root)["cross_contract_lint_passed"] is True


def test_detects_release_checksum_drift(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    target = root / REGISTRY_REL
    target.write_text(
        target.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    with pytest.raises(ManifestValidationError, match="checksum mismatch"):
        run_cross_contract_lint(root)


def test_detects_unfrozen_release(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    release = _read_json(root, RELEASE_REL)
    release["status"] = "draft"
    _write_json(root, RELEASE_REL, release)
    with pytest.raises(ManifestValidationError, match="must be frozen"):
        run_cross_contract_lint(root)


def test_detects_calibration_version_mismatch(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    release = _read_json(root, RELEASE_REL)
    release["calibration_version"] = "calibration.v2"
    _write_json(root, RELEASE_REL, release)
    with pytest.raises(
        ManifestValidationError, match="Calibration versions differ"
    ):
        run_cross_contract_lint(root)


def test_detects_column_contract_drift(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    feature = _read_json(root, FEATURE_REL)
    feature["feature_count"] = 23
    _write_json(root, FEATURE_REL, feature)
    _repoint_release_hash(root, "feature_contract", FEATURE_REL)
    with pytest.raises(
        ManifestValidationError,
        match="46-column/24-feature contract drifted",
    ):
        run_cross_contract_lint(root)


def test_detects_decision_role_drift(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    registry = _read_json(root, REGISTRY_REL)
    registry["proxy_rules"]["4-S3"]["decision_role"] = "support"
    _write_json(root, REGISTRY_REL, registry)
    _repoint_release_hash(root, "registry", REGISTRY_REL)
    with pytest.raises(
        ManifestValidationError, match="decision-role contract drifted"
    ):
        run_cross_contract_lint(root)


def test_detects_dtc_permission_drift(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    registry = _read_json(root, REGISTRY_REL)
    registry["proxy_rules"]["5-S2"]["dtc_emitted"] = True
    _write_json(root, REGISTRY_REL, registry)
    _repoint_release_hash(root, "registry", REGISTRY_REL)
    with pytest.raises(
        ManifestValidationError, match="Non-verdict DTC permission drifted"
    ):
        run_cross_contract_lint(root)


def test_detects_excluded_design_drift(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    registry = _read_json(root, REGISTRY_REL)
    registry["excluded_runtime_designs"] = (
        list(registry["excluded_runtime_designs"]) + ["9-S9"]
    )
    _write_json(root, REGISTRY_REL, registry)
    _repoint_release_hash(root, "registry", REGISTRY_REL)
    with pytest.raises(
        ManifestValidationError, match="Excluded runtime design set drifted"
    ):
        run_cross_contract_lint(root)


def test_detects_unresolved_registry_source_ids(tmp_path: Path) -> None:
    root = _make_bundle(tmp_path)
    release = _read_json(root, RELEASE_REL)
    release["source_artifacts"] = [
        item
        for item in release["source_artifacts"]
        if item["id"] != "feature_baselines"
    ]
    _write_json(root, RELEASE_REL, release)
    with pytest.raises(
        ManifestValidationError, match="source IDs do not resolve"
    ):
        run_cross_contract_lint(root)
