"""Shared repository and per-run path contracts for the Data Layer.

Runtime stages receive one explicit :class:`RunLayout`.  They must not scan
the runs directory, select a "latest" run, or write generated artifacts next
to source code or frozen contracts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class PathContractError(ValueError):
    """Raised when a path violates the repository or run-layout contract."""


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RUNS_DIR = PROCESSED_DIR / "runs"
CONTRACTS_DIR = REPO_ROOT / "data_layer" / "contracts"
CALIBRATION_DIR = REPO_ROOT / "data_layer" / "calibration"

_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RESERVED_RUN_IDS = frozenset({"latest", "current"})


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _require_within(path: Path, parent: Path, *, label: str) -> Path:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise PathContractError(
            f"{label} must remain under {parent}; received {path}."
        ) from exc
    return path


def resolve_repo_path(
    path: str | Path,
    *,
    repo_root: str | Path = REPO_ROOT,
    must_exist: bool = False,
) -> Path:
    """Resolve an absolute path or a path relative to ``repo_root``."""

    root = _resolved(repo_root)
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = root / target
    target = target.resolve(strict=False)
    if must_exist and not target.exists():
        raise FileNotFoundError(target)
    return target


def repo_relative_posix(
    path: str | Path, *, repo_root: str | Path = REPO_ROOT
) -> str:
    """Return a repository-relative POSIX path, rejecting external paths."""

    root = _resolved(repo_root)
    target = resolve_repo_path(path, repo_root=root)
    _require_within(target, root, label="Repository artifact")
    return target.relative_to(root).as_posix()


@dataclass(frozen=True, slots=True)
class RunLayout:
    """All stable input/output locations for one Data Layer run."""

    repo_root: Path
    run_dir: Path

    def __post_init__(self) -> None:
        root = _resolved(self.repo_root)
        run_dir = _resolved(self.run_dir)
        runs_dir = root / "data" / "processed" / "runs"
        _require_within(run_dir, runs_dir, label="Run directory")
        if run_dir.parent != runs_dir:
            raise PathContractError(
                "run_dir must be one direct child of data/processed/runs."
            )
        if not _RUN_ID_PATTERN.fullmatch(run_dir.name):
            raise PathContractError(f"Invalid run_id: {run_dir.name!r}.")
        if run_dir.name.casefold() in _RESERVED_RUN_IDS:
            raise PathContractError(
                f"Reserved run_id {run_dir.name!r} cannot identify a run."
            )
        if run_dir.exists() and not run_dir.is_dir():
            raise PathContractError(f"run_dir is not a directory: {run_dir}")
        object.__setattr__(self, "repo_root", root)
        object.__setattr__(self, "run_dir", run_dir)

    @classmethod
    def for_run_id(
        cls,
        run_id: str,
        *,
        repo_root: str | Path = REPO_ROOT,
    ) -> "RunLayout":
        """Build a layout for an explicit run identifier without creating it."""

        root = _resolved(repo_root)
        return cls(root, root / "data" / "processed" / "runs" / run_id)

    @classmethod
    def from_run_dir(
        cls,
        run_dir: str | Path,
        *,
        repo_root: str | Path = REPO_ROOT,
    ) -> "RunLayout":
        """Build a layout from an explicit absolute or repo-relative run path."""

        root = _resolved(repo_root)
        return cls(root, resolve_repo_path(run_dir, repo_root=root))

    @property
    def run_id(self) -> str:
        return self.run_dir.name

    @property
    def cleaning_dir(self) -> Path:
        return self.run_dir / "cleaning"

    @property
    def cleaned_dataset(self) -> Path:
        return self.cleaning_dir / "cleaned_dataset.csv"

    @property
    def cleaning_enriched(self) -> Path:
        return self.cleaning_dir / "cleaning_enriched.csv"

    @property
    def cleaning_quality(self) -> Path:
        return self.cleaning_dir / "cleaning_quality.csv"

    @property
    def cleaning_report(self) -> Path:
        return self.cleaning_dir / "cleaning_report.json"

    @property
    def operating_conditions_dir(self) -> Path:
        return self.run_dir / "operating_conditions"

    @property
    def operating_condition_enriched(self) -> Path:
        return self.operating_conditions_dir / "operating_condition_enriched.csv"

    @property
    def operating_condition_counts(self) -> Path:
        return self.operating_conditions_dir / "operating_condition_counts_overall.csv"

    @property
    def operating_condition_signal_summary(self) -> Path:
        return self.operating_conditions_dir / "operating_condition_signal_summary.csv"

    @property
    def operating_condition_rules(self) -> Path:
        return self.operating_conditions_dir / "operating_condition_rules.csv"

    @property
    def features_dir(self) -> Path:
        return self.run_dir / "features"

    @property
    def input_contract_dir(self) -> Path:
        return self.features_dir / "00_input_contract"

    @property
    def input_contract_manifest(self) -> Path:
        return self.input_contract_dir / "input_contract_manifest.json"

    @property
    def atomic_dir(self) -> Path:
        return self.features_dir / "10_atomic"

    @property
    def atomic_features(self) -> Path:
        return self.atomic_dir / "atomic_features.csv"

    @property
    def atomic_features_manifest(self) -> Path:
        return self.atomic_dir / "atomic_features_manifest.json"

    @property
    def engine_start_dir(self) -> Path:
        return self.features_dir / "20_engine_start"

    @property
    def engine_start_context(self) -> Path:
        return self.engine_start_dir / "engine_start_context.csv"

    @property
    def engine_start_episodes(self) -> Path:
        return self.engine_start_dir / "engine_start_episodes.csv"

    @property
    def engine_start_context_manifest(self) -> Path:
        return self.engine_start_dir / "engine_start_context_manifest.json"

    @property
    def windows_dir(self) -> Path:
        return self.features_dir / "30_windows"

    @property
    def window_features(self) -> Path:
        return self.windows_dir / "window_features.csv"

    @property
    def window_features_manifest(self) -> Path:
        return self.windows_dir / "window_features_manifest.json"

    @property
    def calibrated_dir(self) -> Path:
        return self.features_dir / "40_calibrated"

    @property
    def calibrated_features(self) -> Path:
        return self.calibrated_dir / "calibrated_features.csv"

    @property
    def calibrated_features_manifest(self) -> Path:
        return self.calibrated_dir / "calibrated_features_manifest.json"

    @property
    def production_dir(self) -> Path:
        return self.features_dir / "41_production"

    @property
    def production_features(self) -> Path:
        return self.production_dir / "production_features.csv"

    @property
    def production_feature_manifest(self) -> Path:
        return self.production_dir / "production_feature_manifest.json"

    @property
    def proxy_dir(self) -> Path:
        return self.run_dir / "proxy"

    @property
    def rule_state_dir(self) -> Path:
        return self.proxy_dir / "50_rule_state"

    @property
    def event_evidence_dir(self) -> Path:
        return self.proxy_dir / "60_event_evidence"

    @property
    def duration_evidence_dir(self) -> Path:
        return self.proxy_dir / "61_duration_evidence"

    @property
    def decisions_dir(self) -> Path:
        return self.proxy_dir / "70_decisions"

    @property
    def feature_contract(self) -> Path:
        return self.repo_root / "data_layer" / "contracts" / "feature_manifest.v1.json"

    @property
    def calibration_registry(self) -> Path:
        return (
            self.repo_root
            / "data_layer"
            / "calibration"
            / "calibration_registry.v1.json"
        )

    @property
    def calibration_release_manifest(self) -> Path:
        return (
            self.repo_root
            / "data_layer"
            / "calibration"
            / "calibration_registry.v1.manifest.json"
        )

    @property
    def stage_directories(self) -> tuple[Path, ...]:
        return (
            self.cleaning_dir,
            self.operating_conditions_dir,
            self.input_contract_dir,
            self.atomic_dir,
            self.engine_start_dir,
            self.windows_dir,
            self.calibrated_dir,
            self.production_dir,
            self.rule_state_dir,
            self.event_evidence_dir,
            self.duration_evidence_dir,
            self.decisions_dir,
        )

    def create_directories(self) -> None:
        """Explicitly create the run root and all contracted stage directories."""

        for directory in self.stage_directories:
            directory.mkdir(parents=True, exist_ok=True)

    def require_runtime_output(self, path: str | Path) -> Path:
        """Resolve and validate a generated-artifact path under this run."""

        target = Path(path).expanduser()
        if not target.is_absolute():
            target = self.run_dir / target
        target = target.resolve(strict=False)
        return _require_within(target, self.run_dir, label="Runtime output")

    def run_relative_posix(self, path: str | Path) -> str:
        """Return a run-relative POSIX artifact path."""

        target = self.require_runtime_output(path)
        return target.relative_to(self.run_dir).as_posix()
