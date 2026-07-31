"""
Forward Data Layer proxy decisions into Model Layer risk scores (GL-368).

The Data Layer's scripts 50-70 own the DTC decision logic for the two
anomaly types the Model Layer never scores itself
(`intake_air_temperature_sensor_fault`,
`map_load_signal_plausibility_fault`, INTERFACE.md 2.3). Their verdicts
land in `proxy_decisions.csv` (21 columns, decision grain). This module
relays those verdicts into our own interface JSON — it computes no
decision logic of its own, it only maps an already-decided
`result_state`/`dtc_emitted` onto a `risk_score` and a
`prediction_confidence`.

Grain mismatch: decisions are one row per sub-check x evaluation unit
(trip, engine-start episode, or segment first row), while our output is
per 512+96-row window. A decision is therefore matched by `trip_id`,
plus `segment_id` for segment-scoped rows, and every window in a trip
inherits that trip's verdict. Documented limitation, INTERFACE.md 2.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    from model.input_validation import validate_required_columns
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import validate_required_columns


# Decision-grain contract frozen by the Data Layer in
# `70_proxy_decision_builder.py` (`DECISION_COLUMNS`); Master Field
# Table rows 50a-50e name the subset we are allowed to read.
DECISION_REQUIRED_COLUMNS: list[str] = [
    "proxy_id",
    "sub_check_id",
    "unit_scope",
    "trip_id",
    "segment_id",
    "engine_start_episode_id",
    "evidence_start_timestamp",
    "evidence_end_timestamp",
    "direction",
    "decision_role",
    "result_state",
    "decision_reason",
    "decision_margin",
    "dtc_candidate_label",
    "dtc_emitted",
    "routing_attribution",
    "routed_dtc",
    "confidence",
    "confidence_capped_low",
    "evidence_count",
    "opportunity_present",
]

# The only two anomaly types we forward. The file also carries
# decisions for our three residual-scored types; those stay with the
# TTM detector (GL-294/GL-295 retirement, unchanged).
FORWARDED_PROXY_IDS: tuple[str, ...] = (
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault",
)

BOOLEAN_COLUMNS = (
    "dtc_emitted",
    "confidence_capped_low",
    "opportunity_present",
)

# Only `verdict` rows can raise a DTC on their own; `support` and
# `arbitration_evidence` rows are corroborating evidence and score
# lower (INTERFACE.md 2.4, calibration_registry.v1.json proxy_rules).
VERDICT_ROLE = "verdict"
EVIDENCE_ROLES = ("support", "arbitration_evidence", "pending_precursor")

SCORE_DTC_EMITTED = 0.9
SCORE_VERDICT_TRIGGERED = 0.6
SCORE_EVIDENCE_TRIGGERED = 0.5
SCORE_NONE = 0.0

# Data Layer confidence is categorical; 0.35 matches the floor
# `calculate_risk` already applies to its residual-based confidence.
CONFIDENCE_SCALE = {
    "high": 0.9,
    "provisional": 0.6,
    "low": 0.35,
}
DEFAULT_CONFIDENCE = 0.35

# Shared MAF/MAP residual evidence is attributed by independent MAP
# witnesses, never by residual sign
# (calibration_registry.v1.json routing.maf_map_arbitration). A 5-S2
# row routed to MAF is evidence against the MAF sensor, so it must not
# raise the MAP type's score.
ARBITRATION_SUB_CHECK = "5-S2"
ARBITRATION_ATTRIBUTION = "MAP"


@dataclass
class ForwardedVerdict:
    """One anomaly type's relayed Data Layer decision."""

    score: float
    confidence: float
    note: str | None = None


def load_proxy_decisions(csv_path: Path | str) -> pd.DataFrame:
    """Load and validate the Data Layer's `proxy_decisions.csv`.

    Returns only the rows for the two forwarded anomaly types. Raises
    ValueError with a single clear message on any contract breach, so
    the dashboard can show it directly (INTERFACE.md 2.5).
    """
    path = Path(csv_path)
    if not path.exists():
        raise ValueError(f"Proxy decisions CSV not found: {path}")
    try:
        raw = pd.read_csv(path, low_memory=False)
    except pd.errors.ParserError as exc:
        raise ValueError(
            f"Could not parse proxy decisions CSV {path}: {exc}"
        ) from exc

    validate_required_columns(
        raw.columns, DECISION_REQUIRED_COLUMNS, str(path)
    )

    df = raw.copy()
    for column in BOOLEAN_COLUMNS:
        df[column] = _coerce_bool(df[column], column, path)

    return df[df["proxy_id"].isin(FORWARDED_PROXY_IDS)].reset_index(
        drop=True
    )


def _coerce_bool(
    series: pd.Series, column: str, path: Path
) -> pd.Series:
    """Parse the Data Layer's True/False strings into real booleans."""
    if series.dtype == bool:
        return series
    mapping = {
        "true": True, "True": True, True: True, 1: True, "1": True,
        "false": False, "False": False, False: False, 0: False,
        "0": False,
    }
    coerced = series.map(mapping)
    if coerced.isna().any():
        bad = sorted(set(series[coerced.isna()].astype(str)))[:5]
        raise ValueError(
            f"Non-boolean values in column '{column}' of {path}: {bad}"
        )
    return coerced.astype(bool)


def _applicable_rows(
    decisions: pd.DataFrame, trip_id: str, segment_id: str | None
) -> pd.DataFrame:
    """Rows whose evaluation unit covers this window's trip/segment.

    Trip- and episode-scoped decisions apply to the whole trip.
    `segment_first_row` decisions apply only to their own segment; a
    null `segment_id` there means the evidence spanned several
    segments, so it is treated as trip-wide.
    """
    rows = decisions[decisions["trip_id"] == trip_id]
    if rows.empty:
        return rows
    segment_scoped = rows["unit_scope"] == "segment_first_row"
    named_segment = rows["segment_id"].notna()
    mismatched = (
        segment_scoped
        & named_segment
        & (rows["segment_id"] != segment_id)
    )
    return rows[~mismatched]


def _countable(rows: pd.DataFrame) -> pd.DataFrame:
    """Drop rows the frozen arbitration routing forbids us to count."""
    routed_elsewhere = (
        (rows["sub_check_id"] == ARBITRATION_SUB_CHECK)
        & rows["routing_attribution"].notna()
        & (rows["routing_attribution"] != ARBITRATION_ATTRIBUTION)
    )
    return rows[~routed_elsewhere]


def _confidence_of(rows: pd.DataFrame) -> float:
    """Map the winning rows' categorical confidence onto 0-1."""
    if rows.empty:
        return DEFAULT_CONFIDENCE
    if rows["confidence_capped_low"].any():
        return CONFIDENCE_SCALE["low"]
    labels = [
        str(value) for value in rows["confidence"].dropna().unique()
    ]
    if not labels:
        return DEFAULT_CONFIDENCE
    # Several rows can back one verdict; report the weakest.
    return min(
        CONFIDENCE_SCALE.get(label, DEFAULT_CONFIDENCE)
        for label in labels
    )


def _describe(proxy_id: str, rows: pd.DataFrame) -> str:
    """Human-readable provenance for the interface JSON `notes`."""
    checks = ", ".join(sorted(rows["sub_check_id"].astype(str)))
    codes = sorted(
        {
            str(value)
            for value in pd.concat(
                [rows["routed_dtc"], rows["dtc_candidate_label"]]
            ).dropna()
        }
    )
    code_text = f", DTC {'/'.join(codes)}" if codes else ""
    confidence = ", ".join(
        sorted({str(value) for value in rows["confidence"].dropna()})
    )
    return (
        f"{proxy_id} forwarded from Data Layer proxy_decisions.csv: "
        f"{checks} triggered{code_text}, confidence {confidence}"
    )


def forward_verdicts(
    decisions: pd.DataFrame,
    trip_id: str,
    segment_id: str | None = None,
) -> dict[str, ForwardedVerdict]:
    """Relay both forwarded types' verdicts for one window.

    `decisions` is the frame returned by `load_proxy_decisions`. The
    result always carries an entry per forwarded anomaly type so the
    caller can drop it straight into its score table; healthy and
    non-evaluable trips score 0.0, exactly as the placeholder did.
    """
    verdicts: dict[str, ForwardedVerdict] = {}
    for proxy_id in FORWARDED_PROXY_IDS:
        rows = _countable(
            _applicable_rows(decisions, trip_id, segment_id)
        )
        rows = rows[rows["proxy_id"] == proxy_id]
        verdicts[proxy_id] = _verdict_for(proxy_id, rows)
    return verdicts


def _verdict_for(
    proxy_id: str, rows: pd.DataFrame
) -> ForwardedVerdict:
    """Score one anomaly type from its applicable decision rows."""
    if rows.empty:
        return ForwardedVerdict(SCORE_NONE, DEFAULT_CONFIDENCE)

    triggered = rows[rows["result_state"] == "triggered"]
    verdicts = triggered[triggered["decision_role"] == VERDICT_ROLE]
    emitted = verdicts[verdicts["dtc_emitted"]]
    if not emitted.empty:
        return ForwardedVerdict(
            SCORE_DTC_EMITTED,
            _confidence_of(emitted),
            _describe(proxy_id, emitted),
        )
    if not verdicts.empty:
        return ForwardedVerdict(
            SCORE_VERDICT_TRIGGERED,
            _confidence_of(verdicts),
            _describe(proxy_id, verdicts),
        )
    evidence = triggered[
        triggered["decision_role"].isin(EVIDENCE_ROLES)
    ]
    if not evidence.empty:
        return ForwardedVerdict(
            SCORE_EVIDENCE_TRIGGERED,
            _confidence_of(evidence),
            _describe(proxy_id, evidence),
        )
    return ForwardedVerdict(SCORE_NONE, DEFAULT_CONFIDENCE)
