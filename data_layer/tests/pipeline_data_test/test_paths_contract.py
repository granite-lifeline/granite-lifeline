from pathlib import Path

import pytest

from data_layer.pipeline_data.paths import (
    PathContractError,
    RunLayout,
    repo_relative_posix,
    resolve_repo_path,
)


def test_run_layout_uses_the_frozen_directory_contract(tmp_path: Path) -> None:
    layout = RunLayout.for_run_id("run_20260719_001", repo_root=tmp_path)

    assert layout.run_dir == (
        tmp_path / "data" / "processed" / "runs" / "run_20260719_001"
    ).resolve()
    assert layout.cleaning_quality == layout.run_dir / "cleaning/cleaning_quality.csv"
    assert layout.operating_condition_enriched == (
        layout.run_dir
        / "operating_conditions/operating_condition_enriched.csv"
    )
    assert layout.input_contract_manifest == (
        layout.run_dir / "features/00_input_contract/input_contract_manifest.json"
    )
    assert layout.production_features == (
        layout.run_dir / "features/41_production/production_features.csv"
    )
    assert layout.calibration_registry == (
        tmp_path / "data_layer/calibration/calibration_registry.v1.json"
    ).resolve()
    assert not layout.run_dir.exists()


def test_directory_creation_is_explicit_and_complete(tmp_path: Path) -> None:
    layout = RunLayout.for_run_id("contract-test", repo_root=tmp_path)

    layout.create_directories()

    assert layout.run_dir.is_dir()
    assert all(path.is_dir() for path in layout.stage_directories)


@pytest.mark.parametrize("run_id", ["latest", "current", "../escape", "bad/name", ""])
def test_invalid_or_implicit_run_ids_are_rejected(
    tmp_path: Path, run_id: str
) -> None:
    with pytest.raises(PathContractError):
        RunLayout.for_run_id(run_id, repo_root=tmp_path)


def test_run_dir_must_be_a_direct_child_of_runs(tmp_path: Path) -> None:
    nested = tmp_path / "data/processed/runs/group/run_1"

    with pytest.raises(PathContractError, match="direct child"):
        RunLayout.from_run_dir(nested, repo_root=tmp_path)


def test_runtime_output_cannot_escape_run_dir(tmp_path: Path) -> None:
    layout = RunLayout.for_run_id("run_1", repo_root=tmp_path)

    assert layout.run_relative_posix(layout.atomic_features) == (
        "features/10_atomic/atomic_features.csv"
    )
    with pytest.raises(PathContractError, match="must remain under"):
        layout.require_runtime_output("../outside.csv")


def test_repo_relative_paths_are_portable_and_external_paths_fail(
    tmp_path: Path,
) -> None:
    target = resolve_repo_path("data/raw/example.csv", repo_root=tmp_path)

    assert target == (tmp_path / "data/raw/example.csv").resolve()
    assert repo_relative_posix(target, repo_root=tmp_path) == "data/raw/example.csv"
    with pytest.raises(PathContractError):
        repo_relative_posix(tmp_path.parent / "external.csv", repo_root=tmp_path)
