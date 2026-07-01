"""Centralized project paths for the data cleaning pipeline.

Keep filesystem layout decisions here 
so scripts, notebooks, and CI do not need to duplicate path calculations.
"""

from __future__ import annotations

from pathlib import Path


CLEANING_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLEANING_DIR.parents[2]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

CONFIG_PATH = CLEANING_DIR / "cleaning_config.yaml"

CLEANED_DATASET = PROCESSED_DIR / "cleaned_dataset.csv"
ENRICHED_DATASET = CLEANING_DIR / "cleaning_enriched.csv"
QUALITY_CSV = CLEANING_DIR / "cleaning_quality.csv"
REPORT_JSON = CLEANING_DIR / "cleaning_report.json"


def resolve_from_repo(path: str | Path) -> Path:
    """Resolve an absolute path or a path relative to the repo root."""
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = REPO_ROOT / target
    return target.resolve()


def display_path(path: str | Path) -> str:
    """Return a repo-relative path when possible for portable reports."""
    target = Path(path).resolve()
    try:
        return target.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(target)
