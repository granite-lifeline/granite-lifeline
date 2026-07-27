"""
Production-feature fixture builders for Model Layer input tests.

The source of truth is Data Layer's tracked representative output:
`data_layer/tests/fixtures/production_features.v1.fixture.csv`.
Synthetic variants used by bad-input tests are derived from that file
so the tests stay aligned with INTERFACE.md v0.13 / feature_schema.v1.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.input_validation import (  # noqa: E402
    PRODUCTION_FEATURE_REQUIRED_COLUMNS,
)

_FIXTURE_REL_PATH = Path(
    "data_layer/tests/fixtures/production_features.v1.fixture.csv"
)


def _find_repo_root(start: Path) -> Path:
    """Walk up from `start` to the checkout root.

    `ttm-related/` sits directly at the repo root in the Model
    Layer's working repo but is nested under `model_layer/` in the
    main team repo, so the root can't be a fixed number of parents
    above this file — locate it by the shared `data_layer/` fixture
    instead.
    """
    for candidate in (start, *start.parents):
        if (candidate / _FIXTURE_REL_PATH).exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {_FIXTURE_REL_PATH} above {start}"
    )


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
PRODUCTION_FIXTURE_CSV = REPO_ROOT / _FIXTURE_REL_PATH


def load_production_fixture() -> pd.DataFrame:
    """Read Data Layer's tracked production_features v1 fixture."""
    return pd.read_csv(PRODUCTION_FIXTURE_CSV)


def _repeat_fixture_rows(rows: int) -> pd.DataFrame:
    source = load_production_fixture()
    repeats = (rows + len(source) - 1) // len(source)
    return pd.concat([source] * repeats, ignore_index=True).iloc[:rows].copy()


def make_group1_frame(rows: int = 30) -> pd.DataFrame:
    """Correct-format frame following production_features.csv v1."""
    frame = _repeat_fixture_rows(rows)
    timestamps = pd.date_range(
        "2026-06-16 10:00:00", periods=rows, freq="1s"
    )
    frame["timestamp"] = timestamps.strftime("%Y-%m-%dT%H:%M:%SZ")
    frame["trip_id"] = "trip_0001"
    frame["segment_id"] = "trip_0001_seg_001"
    frame["row_in_segment"] = list(range(1, rows + 1))
    frame["dt_seconds"] = 1.0
    frame["schema_version"] = "feature_schema.v1"
    frame["calibration_version"] = "calibration.v1"
    return frame[PRODUCTION_FEATURE_REQUIRED_COLUMNS]


def write_group1_csv(
    path: Path,
    rows: int = 30,
    drop_columns: Sequence[str] = (),
    wrong_type_columns: Sequence[str] = (),
    extra_bookkeeping: bool = False,
) -> Path:
    """Write a production-feature CSV, optionally degraded.

    ``drop_columns`` builds the missing-column case;
    ``wrong_type_columns`` fills the named columns with a
    non-numeric string (wrong-type case); ``extra_bookkeeping``
    appends non-contract bookkeeping columns — consumers must tolerate them.
    """
    frame = make_group1_frame(rows).drop(
        columns=list(drop_columns)
    )
    for column in wrong_type_columns:
        frame[column] = "sensor_error"
    if extra_bookkeeping:
        frame["source_file"] = (
            "2017-07-05_Seat_Leon_RT_S_Stau.csv"
        )
        frame["brand"] = "Seat"
        frame["model"] = "Leon"
    frame.to_csv(path, index=False)
    return path


def make_multi_segment_frame(
    segments: Sequence[tuple[str, str, int]],
) -> pd.DataFrame:
    """Concatenate production-feature frames as multiple segments.

    ``segments`` is a sequence of (trip_id, segment_id, rows).
    Timestamps run sequentially across segments with a gap so
    per-trip ordering matches real Group 1 output.
    """
    frames = []
    start = pd.Timestamp("2026-06-16 10:00:00")
    for trip_id, segment_id, rows in segments:
        frame = make_group1_frame(rows)
        frame["trip_id"] = trip_id
        frame["segment_id"] = segment_id
        stamps = pd.date_range(start, periods=rows, freq="1s")
        frame["timestamp"] = stamps.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        start = stamps[-1] + pd.Timedelta(seconds=61)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
