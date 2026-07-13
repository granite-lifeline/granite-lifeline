"""
Mock Group 1 `feature_dataset.csv` builders (Story 4, Lucca).

Column set is GROUP1_REQUIRED_COLUMNS (INTERFACE.md v0.6 Section 1).
Constant values sit inside the healthy reference ranges so Ray's
Story 4 range tests can reuse the same builders. Bad-input cases
(missing column, wrong type) derive from the correct frame so the
fixture variants cannot drift apart.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.input_validation import (  # noqa: E402
    GROUP1_REQUIRED_COLUMNS,
)

# Constant healthy per-row values; `timestamp` and `row_in_segment`
# are generated per row in make_group1_frame. Values follow the
# INTERFACE.md v0.6 Section 1 examples and the healthy baseline
# reference table (failure_type_research.md).
GROUP1_COLUMN_DEFAULTS: dict[str, object] = {
    "trip_id": "trip_0001",
    "segment_id": "trip_0001_seg_001",
    "dt_seconds": 1.0,
    "thermal_state": "post_warmup",
    "child_state": "steady_driving",
    "operating_state": "post_warmup_steady_driving",
    "condition_confidence": "high",
    "condition_quality_flags": "OK",
    "coolant_temp": 92.0,
    "map": 110.0,
    "rpm": 1500.0,
    "speed": 60.0,
    "intake_temp": 35.0,
    "maf": 20.0,
    "tps": 30.0,
    "ambient_temp": 22.0,
    "accel_pedal_d": 25.0,
    "accel_pedal_e": 25.5,
    "coolant_slope": 0.01,
    "coolant_ambient_delta": 70.0,
    "coolant_stability": 0.4,
    "intake_ambient_delta": 13.0,
    "intake_temp_slope": 0.05,
    "maf_derived_air_load_raw": 0.8,
    "map_derived_air_load_raw": 110.0,
    "maf_map_cohesion": 0.18,
    "speed_density_maf_residual": 1.2,
    "map_slope": 0.5,
    "accel_pedal_mean": 25.25,
    "pedal_throttle_gap": 2.1,
    "pedal_to_throttle_delay": 1.0,
    "tps_slope": 0.3,
    "accel_pedal_channel_delta": 0.5,
    "accel_pedal_channel_ratio": 0.98,
    "pedal_slope": 0.4,
    "engine_on_flag": 1.0,
    "rpm_slope": 12.0,
    "idle_flag": 0.0,
    "idle_rpm_stability": 55.0,
}


def make_group1_frame(rows: int = 30) -> pd.DataFrame:
    """Correct-format mock of Group 1's feature_dataset.csv."""
    timestamps = pd.date_range(
        "2026-06-16 10:00:00", periods=rows, freq="1s"
    )
    data: dict[str, object] = {
        "timestamp": timestamps.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row_in_segment": list(range(1, rows + 1)),
    }
    for column, value in GROUP1_COLUMN_DEFAULTS.items():
        data[column] = [value] * rows
    return pd.DataFrame(data)[GROUP1_REQUIRED_COLUMNS]


def write_group1_csv(
    path: Path,
    rows: int = 30,
    drop_columns: Sequence[str] = (),
    wrong_type_columns: Sequence[str] = (),
    extra_bookkeeping: bool = False,
) -> Path:
    """Write a mock Group 1 CSV, optionally degraded.

    ``drop_columns`` builds the missing-column case;
    ``wrong_type_columns`` fills the named columns with a
    non-numeric string (wrong-type case); ``extra_bookkeeping``
    appends provenance columns present in Group 1's real output
    but absent from the interface — consumers must tolerate them.
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
