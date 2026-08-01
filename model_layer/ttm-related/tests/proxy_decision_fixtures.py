"""
Decision-row fixture builders for the proxy-forwarding tests (GL-368).

The real corpus cannot exercise the forwarding path: all 81 KIT trips
are healthy driving, so every row in a live `proxy_decisions.csv` is
`pass` or `not_evaluable` and no `triggered` verdict exists anywhere.
These builders produce the same 21-column decision grain by hand so the
triggered branches can be tested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.proxy_decision_forwarding import (  # noqa: E402
    DECISION_REQUIRED_COLUMNS,
)

IAT_PROXY = "intake_air_temperature_sensor_fault"
MAP_PROXY = "map_load_signal_plausibility_fault"

# Defaults describe a healthy trip-scoped verdict row: the shape every
# row in the real delivery has.
_DEFAULTS: dict[str, object] = {
    "proxy_id": IAT_PROXY,
    "sub_check_id": "4-S1",
    "unit_scope": "trip",
    "trip_id": "trip_0001",
    "segment_id": "trip_0001_seg_001",
    "engine_start_episode_id": None,
    "evidence_start_timestamp": "2017-07-05T05:16:56Z",
    "evidence_end_timestamp": "2017-07-05T06:22:15Z",
    "direction": None,
    "decision_role": "verdict",
    "result_state": "pass",
    "decision_reason": "no_trigger_with_opportunity",
    "decision_margin": -1.0,
    "dtc_candidate_label": "P0111",
    "dtc_emitted": False,
    "routing_attribution": None,
    "routed_dtc": None,
    "confidence": "high",
    "confidence_capped_low": False,
    "evidence_count": 4,
    "opportunity_present": True,
}


def make_decision_row(**overrides: object) -> dict[str, object]:
    """One decision row, healthy by default."""
    row = dict(_DEFAULTS)
    row.update(overrides)
    return row


def make_triggered_row(**overrides: object) -> dict[str, object]:
    """A verdict row that emitted its DTC (the 0.9 branch)."""
    triggered = {
        "result_state": "triggered",
        "dtc_emitted": True,
        "routed_dtc": _DEFAULTS["dtc_candidate_label"],
    }
    triggered.update(overrides)
    return make_decision_row(**triggered)


def make_decision_frame(
    rows: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    """Assemble decision rows into the frozen 21-column frame."""
    if rows is None:
        rows = [make_decision_row()]
    frame = pd.DataFrame(rows)
    for column in DECISION_REQUIRED_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    return frame[DECISION_REQUIRED_COLUMNS]


def write_decisions_csv(
    path: Path,
    rows: list[dict[str, object]] | None = None,
    drop_columns: tuple[str, ...] = (),
) -> Path:
    """Write a decision CSV, optionally missing required columns."""
    frame = make_decision_frame(rows)
    if drop_columns:
        frame = frame.drop(columns=list(drop_columns))
    frame.to_csv(path, index=False)
    return path
