"""Centralized project paths for the data cleaning pipeline.

Keep filesystem layout decisions here
so scripts, notebooks, and CI do not need to duplicate path calculations.
"""

from __future__ import annotations

import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[2]

# Support both direct script execution and package imports from the repo root.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_layer.pipeline_data.paths import (  # noqa: E402
    RunLayout,
    repo_relative_posix,
)

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

CONFIG_PATH = BASE_DIR / "cleaning_config.yaml"


def resolve_from_repo(path: str | Path) -> Path:
    """Resolve an absolute path or a path relative to the repo root."""
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = REPO_ROOT / target
    return target.resolve()


def display_path(path: str | Path) -> str:
    """Return a repo-relative path when possible for portable reports."""
    try:
        return repo_relative_posix(path, repo_root=REPO_ROOT)
    except ValueError:
        return str(Path(path).resolve())


def build_run_layout(run_dir: str | Path) -> RunLayout:
    """Resolve one explicit repo-relative or absolute Data Layer run path."""

    return RunLayout.from_run_dir(run_dir, repo_root=REPO_ROOT)
