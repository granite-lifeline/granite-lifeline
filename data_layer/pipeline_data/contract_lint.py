"""Read-only cross-contract lint for the frozen Data Layer release bundle."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from data_layer.pipeline_data.manifests import (
    ManifestValidationError,
    load_json_object,
    ordered_column_contract_from_feature_manifest,
    sha256_file,
)


EXPECTED_ANOMALY_TYPES = (
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault",
)
EXPECTED_RUNTIME_ROLES = {
    "1-S1": "verdict",
    "1-S2": "verdict",
    "1-S3": "pending_precursor",
    "1-S4": "support",
    "2-S2": "verdict",
    "2-S3b": "verdict",
    "3-S1a": "verdict",
    "3-S1b": "verdict",
    "4-S1": "verdict",
    "4-S2": "support",
    "4-S3": "verdict",
    "5-S1": "verdict",
    "5-S2": "arbitration_evidence",
    "5-S3": "verdict",
}
EXPECTED_EXCLUDED = {
    "2-S1", "2-S3a", "3-S2", "3-S3", "4-S4", "failure-6"
}
RULE_ID_PATTERN = re.compile(r"^[1-5]-S\d+[a-z]?")


def _resolve_json_pointer(root: dict[str, Any], pointer: str) -> Any:
    current: Any = root
    for raw_part in pointer.removeprefix("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ManifestValidationError(
                f"Calibration reference does not resolve: #/{pointer}."
            )
        current = current[part]
    return current


def _collect_source_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "source_ids" and isinstance(child, list):
                found.update(str(item) for item in child)
            else:
                found.update(_collect_source_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_source_ids(child))
    return found


def run_cross_contract_lint(repo_root: str | Path) -> dict[str, Any]:
    """Validate schema, feature, proxy, registry, and release identities."""

    root = Path(repo_root).resolve(strict=False)
    paths = {
        "registry": root / "data_layer/calibration/calibration_registry.v1.json",
        "release": root / "data_layer/calibration/calibration_registry.v1.manifest.json",
        "feature_manifest": root / "data_layer/contracts/feature_manifest.v1.json",
        "feature_schema": root / "data_layer/feature_engineering/feature_schema.md",
        "proxy_definition": root / "data_layer/proxy_failure/proxy_failure_definition.md",
        "proxy_support": root / "data_layer/proxy_failure/proxy_support.md",
    }
    registry = load_json_object(paths["registry"])
    release = load_json_object(paths["release"])
    feature = load_json_object(paths["feature_manifest"])
    schema_text = paths["feature_schema"].read_text(encoding="utf-8")
    proxy_definition = paths["proxy_definition"].read_text(encoding="utf-8")
    proxy_support = paths["proxy_support"].read_text(encoding="utf-8")

    if registry.get("status") != "frozen" or release.get("status") != "frozen":
        raise ManifestValidationError("Registry and release manifest must be frozen.")
    if release.get("calibration_version") != registry.get("calibration_version"):
        raise ManifestValidationError("Calibration versions differ.")
    release_records = {
        release["registry"]["path"]: release["registry"]["sha256"],
        release["feature_contract"]["path"]: release["feature_contract"]["sha256"],
        **{item["path"]: item["sha256"] for item in release["authoritative_documents"]},
    }
    for relative_path, expected_hash in release_records.items():
        if sha256_file(root / relative_path) != expected_hash:
            raise ManifestValidationError(
                f"Release checksum mismatch: {relative_path}."
            )

    ordered = ordered_column_contract_from_feature_manifest(feature)
    names = [item["name"] for item in ordered]
    if len(names) != 46 or feature.get("feature_count") != 24:
        raise ManifestValidationError("Frozen 46-column/24-feature contract drifted.")
    if len(names) != len(set(names)):
        raise ManifestValidationError("Frozen production columns are not unique.")
    required_path_terms = (
        "data/processed/runs/<run_id>/",
        "operating_conditions/operating_condition_enriched.csv",
        "cleaning/cleaning_quality.csv",
        "features/41_production/production_feature_manifest.json",
        "RunLayout",
        "latest",
    )
    missing_terms = [term for term in required_path_terms if term not in schema_text]
    if missing_terms:
        raise ManifestValidationError(
            f"Authoritative path contract is incomplete: {missing_terms}."
        )
    missing_schema_fields = [
        name
        for name in names
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", schema_text)
        is None
    ]
    if missing_schema_fields:
        raise ManifestValidationError(
            f"Feature schema omits contracted fields: {missing_schema_fields}."
        )

    for item in feature["features"]:
        reference = item.get("calibration_reference")
        if reference is None:
            continue
        path_text, pointer = reference.split("#", 1)
        if path_text != "data_layer/calibration/calibration_registry.v1.json":
            raise ManifestValidationError(f"Unexpected calibration path: {path_text}.")
        target = _resolve_json_pointer(registry, pointer)
        if not isinstance(target, dict) or target.get("output_feature") != item["name"]:
            raise ManifestValidationError(
                f"Calibration transform does not produce {item['name']}."
            )
    referenced_rules: set[str] = set()
    for item in feature["features"]:
        for consumer in item.get("consumers", []):
            match = RULE_ID_PATTERN.match(consumer)
            if match:
                referenced_rules.add(match.group(0))
    runtime_rules = registry.get("proxy_rules", {})
    if set(runtime_rules) != set(EXPECTED_RUNTIME_ROLES):
        raise ManifestValidationError("Runtime proxy-rule identity set drifted.")
    roles = {rule: body.get("decision_role") for rule, body in runtime_rules.items()}
    if roles != EXPECTED_RUNTIME_ROLES:
        raise ManifestValidationError("Proxy decision-role contract drifted.")
    if not referenced_rules.issubset(runtime_rules):
        raise ManifestValidationError("Feature consumers reference unknown runtime rules.")
    if set(registry.get("excluded_runtime_designs", [])) != EXPECTED_EXCLUDED:
        raise ManifestValidationError("Excluded runtime design set drifted.")
    for rule in EXPECTED_RUNTIME_ROLES:
        short_rule = rule.split("-", 1)[1]
        support_mentions_rule = (
            rule in proxy_support
            or f"| {short_rule} |" in proxy_support
            or f"**{short_rule}" in proxy_support
        )
        if rule not in proxy_definition or not support_mentions_rule:
            raise ManifestValidationError(f"Proxy documents omit runtime rule {rule}.")
    for anomaly in EXPECTED_ANOMALY_TYPES:
        if anomaly not in proxy_definition or anomaly not in proxy_support:
            raise ManifestValidationError(f"Proxy documents omit anomaly {anomaly}.")
    for rule in ("1-S3", "1-S4", "4-S2", "5-S2"):
        if runtime_rules[rule].get("dtc_emitted", False) is not False:
            raise ManifestValidationError(f"Non-verdict DTC permission drifted for {rule}.")

    available_sources = {
        item["id"] for item in release.get("source_artifacts", [])
    } | {item["id"] for item in release.get("authoritative_documents", [])}
    unresolved_sources = _collect_source_ids(registry) - available_sources
    if unresolved_sources:
        raise ManifestValidationError(
            f"Registry source IDs do not resolve: {sorted(unresolved_sources)}."
        )
    return {
        "ordered_column_count": len(names),
        "feature_count": feature["feature_count"],
        "anomaly_type_count": len(EXPECTED_ANOMALY_TYPES),
        "runtime_rule_count": len(runtime_rules),
        "excluded_design_count": len(EXPECTED_EXCLUDED),
        "release_artifact_count": len(release_records),
        "release_bundle_complete": True,
        "cross_contract_lint_passed": True,
    }
