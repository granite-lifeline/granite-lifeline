from pathlib import Path

from data_layer.pipeline_data.contract_lint import run_cross_contract_lint


REPO_ROOT = Path(__file__).resolve().parents[3]


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
