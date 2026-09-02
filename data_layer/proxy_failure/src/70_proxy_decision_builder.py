"""Apply the frozen runtime rules and produce proxy decisions.

Script 70 consumes only the versioned evidence outputs of scripts 50,
60, and 61 plus the frozen calibration registry.  It never reads
canonical or production-feature tables.  It applies the 14 executable
runtime rules with their frozen decision-role semantics, persistence
comparisons, sensor-trust wiring, confidence caps, margins, DTC
attribution, and MAF/MAP routing.

Decision grain (one row per sub-check x evaluation unit):

- trip-scoped rules (1-S2, 1-S3, 2-S2, 2-S3b, 3-S1a, 3-S1b, 4-S1,
  4-S3, 5-S1, 5-S2, 5-S3): one row per trip;
- 1-S1: one row per engine-start episode;
- 1-S4 and 4-S2: one row per canonical segment first row.

Every row carries ``trip_id``, ``segment_id`` (null when the evaluated
evidence spans several segments), and evidence start/end timestamps so
the Model Layer can align decisions with its fixed windows by
time-range overlap.

Output (under ``proxy/70_decisions/``):

- ``proxy_decisions.csv`` — decision grain.
- ``proxy_decision_manifest.json`` — stage manifest with the explicit
  decision schema and semantics.

The frozen registry is loaded read-only; no threshold is fitted,
selected, or modified here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.manifests import (  # noqa: E402
    ArtifactDescriptor,
    build_stage_manifest,
    load_json_object,
    sha256_file,
    validate_stage_manifest,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

SCRIPT_VERSION = "1.0.0"
SCHEMA_VERSION = "feature_schema.v1"
STAGE_ID = "70"
KEYS = ["timestamp", "trip_id", "segment_id", "row_in_segment"]

PROXY_IDS = {
    "1": "cooling_degradation",
    "2": "air_intake_maf_anomaly",
    "3": "accelerator_pedal_sensor",
    "4": "intake_air_temperature_sensor_fault",
    "5": "map_load_signal_plausibility_fault",
}

DECISION_COLUMNS = [
    "proxy_id", "sub_check_id", "unit_scope", "trip_id", "segment_id",
    "engine_start_episode_id", "evidence_start_timestamp",
    "evidence_end_timestamp", "direction", "decision_role",
    "result_state", "decision_reason", "decision_margin",
    "dtc_candidate_label", "dtc_emitted", "routing_attribution",
    "routed_dtc", "confidence", "confidence_capped_low",
    "evidence_count", "opportunity_present",
]

RULE_STATE_COLUMNS = KEYS + [
    "intake_temp",
    "s4s3_evaluable", "s4s3_below_range", "s4s3_above_range",
    "coldstart_first_row", "coldstart_not_evaluable_reason",
    "s1s4_eligible", "s1s4_ect_aat_abs_delta", "s1s4_exceed",
    "s4s2_eligible", "s4s2_iat_aat_abs_delta", "s4s2_exceed",
    "s4s2_cap_active",
]

COLD_SOAK_ONLY_REASONS = {
    "cold_soak_gap_unavailable",
    "first_row_engine_on",
    "no_observed_start_in_block",
}


class ProxyDecisionContractError(RuntimeError):
    """Raised when script 70 inputs violate the frozen contract."""


def _verify_input(path: Path, expected_sha: str, *, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected_sha:
        raise ProxyDecisionContractError(
            f"{label} checksum drift: expected {expected_sha}, "
            f"found {actual}."
        )


def load_registry(layout: RunLayout) -> dict[str, Any]:
    """Load the frozen registry after verifying its release checksum."""

    release = load_json_object(layout.calibration_release_manifest)
    _verify_input(
        layout.calibration_registry,
        release["registry"]["sha256"],
        label="calibration registry",
    )
    registry = load_json_object(layout.calibration_registry)
    policy = registry.get("online_policy", {})
    if not policy.get("read_only") or policy.get("fit_allowed"):
        raise ProxyDecisionContractError(
            "Registry online policy must be read-only with fitting "
            "disabled."
        )
    return registry


def load_evidence(
    layout: RunLayout,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Load and checksum-verify the 50/60/61 evidence tables."""

    rule_state_manifest = load_json_object(layout.rule_state_manifest)
    event_manifest = load_json_object(layout.event_evidence_manifest)
    duration_manifest = load_json_object(
        layout.duration_evidence_manifest
    )
    identities = {
        "50": rule_state_manifest["source_dataset_identity"],
        "60": event_manifest["source_dataset_identity"],
        "61": duration_manifest["source_dataset_identity"],
    }
    if len(set(identities.values())) != 1:
        raise ProxyDecisionContractError(
            f"Evidence stages disagree on source identity: {identities}."
        )
    _verify_input(
        layout.rule_state,
        rule_state_manifest["artifact_sha256"][
            "proxy/50_rule_state/rule_state.csv"
        ],
        label="rule_state.csv",
    )
    _verify_input(
        layout.engine_start_rule_state,
        rule_state_manifest["artifact_sha256"][
            "proxy/50_rule_state/engine_start_rule_state.csv"
        ],
        label="engine_start_rule_state.csv",
    )
    _verify_input(
        layout.pedal_step_events,
        event_manifest["artifact_sha256"][
            "proxy/60_event_evidence/pedal_step_events.csv"
        ],
        label="pedal_step_events.csv",
    )
    _verify_input(
        layout.duration_episodes,
        duration_manifest["artifact_sha256"][
            "proxy/61_duration_evidence/duration_episodes.csv"
        ],
        label="duration_episodes.csv",
    )
    evidence = {
        "rule_state": pd.read_csv(
            layout.rule_state, usecols=RULE_STATE_COLUMNS,
            low_memory=False,
        ),
        "engine_start": pd.read_csv(
            layout.engine_start_rule_state, low_memory=False
        ),
        "events": pd.read_csv(layout.pedal_step_events,
                              low_memory=False),
        "episodes": pd.read_csv(layout.duration_episodes,
                                low_memory=False),
    }
    return evidence, {
        "source_dataset_identity": identities["50"],
    }


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype("boolean").fillna(False).astype(bool)


def _true(value: Any) -> bool:
    """Robust scalar truth test over numpy/Python bools and NA."""

    return bool(value) if pd.notna(value) else False


def _row(**fields: Any) -> dict[str, Any]:
    row = {column: None for column in DECISION_COLUMNS}
    row.update(fields)
    missing = set(fields) - set(DECISION_COLUMNS)
    if missing:
        raise ProxyDecisionContractError(
            f"Unknown decision fields: {sorted(missing)}."
        )
    return row


class _TripEvidence:
    """Per-trip views over the 61 episode table and trip spans."""

    def __init__(self, episodes: pd.DataFrame,
                 rule_state: pd.DataFrame) -> None:
        self._episodes = episodes
        spans = rule_state.groupby("trip_id", sort=True).agg(
            start=("timestamp", "min"), end=("timestamp", "max"),
        )
        self.trip_ids = list(spans.index)
        self._spans = spans

    def trip_span(self, trip_id: str) -> tuple[str, str]:
        row = self._spans.loc[trip_id]
        return str(row["start"]), str(row["end"])

    def episodes(self, trip_id: str, rule_id: str,
                 kind: str) -> pd.DataFrame:
        e = self._episodes
        return e[
            (e["trip_id"] == trip_id)
            & (e["rule_id"] == rule_id)
            & (e["episode_kind"] == kind)
        ]

    def segment_of(self, frame: pd.DataFrame) -> "str | None":
        segments = frame["segment_id"].unique()
        return str(segments[0]) if len(segments) == 1 else None

    def span_of(self, frame: pd.DataFrame) -> tuple[Any, Any]:
        if frame.empty:
            return None, None
        return (
            frame["start_timestamp"].min(),
            frame["end_timestamp"].max(),
        )


def _duration_rule_decision(
    trips: _TripEvidence,
    trip_id: str,
    *,
    rule_id: str,
    condition_kinds: list[tuple[str, str, "str | None"]],
    opportunity: str,
    opportunity_seconds: float,
    decision_role: str,
    dtc_candidate_label: "str | None",
    active_state: str = "triggered",
    confidence: str = "high",
    no_opportunity_reason: str = "no_qualifying_opportunity",
) -> dict[str, Any]:
    """Shared trip-level decision for the duration-gated rules.

    ``condition_kinds`` lists ``(episode_kind, direction,
    override_required)`` tuples; ``opportunity`` is one of
    ``"run_meets"`` (a single eligible run of at least
    ``opportunity_seconds``), ``"total_eligible"`` (total eligible
    seconds meet ``opportunity_seconds``), or
    ``"run_meets_and_context"`` (adds at least one
    context-opportunity episode).
    """

    sub_check = rule_id
    proxy_id = PROXY_IDS[rule_id.split("-")[0]]
    eligible = trips.episodes(trip_id, rule_id, "eligible")

    if opportunity == "total_eligible":
        opportunity_present = bool(
            not eligible.empty
            and eligible["duration_seconds"].sum()
            >= opportunity_seconds
        )
    else:
        opportunity_present = bool(
            eligible["duration_seconds"].ge(opportunity_seconds).any()
        )
        if opportunity == "run_meets_and_context":
            context = trips.episodes(
                trip_id, rule_id, "context_opportunity"
            )
            opportunity_present = opportunity_present and not context.empty

    best_margin = None
    best_kind = None
    best_direction = None
    triggered = False
    trigger_frame = None
    trigger_direction = None
    trigger_margin = None
    evidence_count = 0
    for kind, direction, _override in condition_kinds:
        runs = trips.episodes(trip_id, rule_id, kind)
        evidence_count += len(runs)
        if runs.empty:
            continue
        margin = runs["margin_seconds"].max()
        if best_margin is None or margin > best_margin:
            best_margin = margin
            best_kind = kind
            best_direction = direction
        meeting = runs[_as_bool(runs["meets_persistence"])]
        if not meeting.empty and not triggered:
            triggered = True
            trigger_frame = meeting
            trigger_direction = direction
            trigger_margin = meeting["margin_seconds"].max()

    start, end = trips.span_of(eligible)
    segment_id = (
        trips.segment_of(eligible) if not eligible.empty else None
    )
    if triggered:
        start, end = trips.span_of(trigger_frame)
        segment_id = trips.segment_of(trigger_frame)
        return _row(
            proxy_id=proxy_id, sub_check_id=sub_check,
            unit_scope="trip", trip_id=trip_id, segment_id=segment_id,
            evidence_start_timestamp=start, evidence_end_timestamp=end,
            direction=trigger_direction, decision_role=decision_role,
            result_state=active_state,
            decision_reason="condition_persistence_met",
            decision_margin=float(trigger_margin),
            dtc_candidate_label=dtc_candidate_label,
            dtc_emitted=False, confidence=confidence,
            confidence_capped_low=False,
            evidence_count=int(evidence_count),
            opportunity_present=bool(opportunity_present),
        )
    if not opportunity_present:
        trip_start, trip_end = trips.trip_span(trip_id)
        return _row(
            proxy_id=proxy_id, sub_check_id=sub_check,
            unit_scope="trip", trip_id=trip_id, segment_id=segment_id,
            evidence_start_timestamp=(start or trip_start),
            evidence_end_timestamp=(end or trip_end),
            direction=None, decision_role=decision_role,
            result_state="not_evaluable",
            decision_reason=no_opportunity_reason,
            decision_margin=None,
            dtc_candidate_label=dtc_candidate_label,
            dtc_emitted=False, confidence=confidence,
            confidence_capped_low=False,
            evidence_count=int(evidence_count),
            opportunity_present=False,
        )
    return _row(
        proxy_id=proxy_id, sub_check_id=sub_check,
        unit_scope="trip", trip_id=trip_id, segment_id=segment_id,
        evidence_start_timestamp=start, evidence_end_timestamp=end,
        direction=best_direction if best_kind else None,
        decision_role=decision_role, result_state="pass",
        decision_reason="no_trigger_with_opportunity",
        decision_margin=(
            float(best_margin) if best_margin is not None else None
        ),
        dtc_candidate_label=dtc_candidate_label,
        dtc_emitted=False, confidence=confidence,
        confidence_capped_low=False,
        evidence_count=int(evidence_count),
        opportunity_present=True,
    )


def build_trip_decisions(
    trips: _TripEvidence,
    events: pd.DataFrame,
    rule_state: pd.DataFrame,
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decision rows for the eleven trip-scoped sub-checks."""

    rules = registry["proxy_rules"]

    def seconds(rule_id: str, *keys: str) -> float:
        node: Any = rules[rule_id]
        for key in keys:
            node = node[key]
        if isinstance(node, dict):
            node = node["value"]
        return float(node)

    rows: list[dict[str, Any]] = []
    for trip_id in trips.trip_ids:
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="1-S2",
            condition_kinds=[
                ("exceed_high", "high", None),
                ("exceed_critical", "high", None),
            ],
            opportunity="total_eligible",
            opportunity_seconds=seconds(
                "1-S2", "minimum_evaluable_seconds"),
            decision_role="verdict",
            dtc_candidate_label="P0217",
            no_opportunity_reason="insufficient_evaluable_time",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="1-S3",
            condition_kinds=[("precursor", "high", None)],
            opportunity="run_meets",
            opportunity_seconds=seconds(
                "1-S3", "minimum_evaluable_seconds"),
            decision_role="pending_precursor",
            dtc_candidate_label="P0217", active_state="pending",
            no_opportunity_reason="below_minimum_evaluable_window",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="2-S2",
            condition_kinds=[("residual_low", "low", None)],
            opportunity="run_meets",
            opportunity_seconds=seconds("2-S2", "persistence"),
            decision_role="verdict",
            dtc_candidate_label="P0101",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="2-S3b",
            condition_kinds=[("zero_maf_firing", "low", None)],
            opportunity="run_meets",
            opportunity_seconds=seconds("2-S3b", "persistence"),
            decision_role="verdict",
            dtc_candidate_label="P0102",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="3-S1a",
            condition_kinds=[
                ("residual_low", "low", None),
                ("residual_high", "high", None),
            ],
            opportunity="run_meets",
            opportunity_seconds=seconds(
                "3-S1a", "same_side_persistence"),
            decision_role="verdict",
            dtc_candidate_label="P2138",
            no_opportunity_reason="no_qualifying_masked_opportunity",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="3-S1b",
            condition_kinds=[("extreme_delta", "high", None)],
            opportunity="run_meets",
            opportunity_seconds=seconds("3-S1b", "persistence"),
            decision_role="verdict",
            dtc_candidate_label="P2138", confidence="provisional",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="4-S1",
            condition_kinds=[("flat_under_context", None, None)],
            opportunity="run_meets_and_context",
            opportunity_seconds=seconds(
                "4-S1", "minimum_evaluable_seconds"),
            decision_role="verdict", dtc_candidate_label="P0111",
            no_opportunity_reason="no_context_opportunity",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="5-S2",
            condition_kinds=[
                ("residual_low", "low", None),
                ("residual_high", "high", None),
            ],
            opportunity="run_meets",
            opportunity_seconds=seconds(
                "5-S2", "same_side_persistence"),
            decision_role="arbitration_evidence",
            dtc_candidate_label=None,
            no_opportunity_reason="outside_steady_domain",
        ))
        rows.append(_duration_rule_decision(
            trips, trip_id, rule_id="5-S3",
            condition_kinds=[("flat_under_context", None, None)],
            opportunity="run_meets_and_context",
            opportunity_seconds=seconds(
                "5-S3", "minimum_evaluable_seconds"),
            decision_role="verdict", dtc_candidate_label="P0106",
            no_opportunity_reason="no_context_opportunity",
        ))
        rows.append(_range_rule_decision(trip_id, trips, rule_state,
                                         rules["4-S3"]))
        rows.append(_step_response_decision(trip_id, trips, events,
                                            rules["5-S1"]))
    return rows


def _range_rule_decision(
    trip_id: str,
    trips: _TripEvidence,
    rule_state: pd.DataFrame,
    rule: dict[str, Any],
) -> dict[str, Any]:
    """4-S3 physical-range verdict (instantaneous, trip-scoped)."""

    samples = rule_state[rule_state["trip_id"] == trip_id]
    evaluable = _as_bool(samples["s4s3_evaluable"])
    below = _as_bool(samples["s4s3_below_range"])
    above = _as_bool(samples["s4s3_above_range"])
    trip_start, trip_end = trips.trip_span(trip_id)
    common = {
        "proxy_id": PROXY_IDS["4"], "sub_check_id": "4-S3",
        "unit_scope": "trip", "trip_id": trip_id,
        "decision_role": "verdict", "dtc_emitted": False,
        "confidence": "high", "confidence_capped_low": False,
    }
    if not evaluable.any():
        return _row(
            **common, segment_id=None,
            evidence_start_timestamp=trip_start,
            evidence_end_timestamp=trip_end, direction=None,
            result_state="not_evaluable",
            decision_reason="signal_unavailable",
            decision_margin=None, dtc_candidate_label=None,
            evidence_count=0, opportunity_present=False,
        )
    violation = below | above
    if violation.any():
        hits = samples[violation]
        direction = "low" if below.any() else "high"
        label = (
            rule["low"]["dtc_candidate_label"] if direction == "low"
            else rule["high"]["dtc_candidate_label"]
        )
        bound = (
            float(rule["low"]["value"]) if direction == "low"
            else float(rule["high"]["value"])
        )
        temps = hits["intake_temp"].astype(float)
        margin = float(
            (bound - temps).max() if direction == "low"
            else (temps - bound).max()
        )
        segments = hits["segment_id"].unique()
        return _row(
            **common,
            segment_id=(
                str(segments[0]) if len(segments) == 1 else None
            ),
            evidence_start_timestamp=hits["timestamp"].min(),
            evidence_end_timestamp=hits["timestamp"].max(),
            direction=direction, result_state="triggered",
            decision_reason="range_violation", decision_margin=margin,
            dtc_candidate_label=label, evidence_count=int(len(hits)),
            opportunity_present=True,
        )
    spans = samples[evaluable]
    segments = spans["segment_id"].unique()
    return _row(
        **common,
        segment_id=str(segments[0]) if len(segments) == 1 else None,
        evidence_start_timestamp=spans["timestamp"].min(),
        evidence_end_timestamp=spans["timestamp"].max(),
        direction=None, result_state="pass",
        decision_reason="no_trigger_with_opportunity",
        decision_margin=None, dtc_candidate_label=None,
        evidence_count=int(evaluable.sum()), opportunity_present=True,
    )


def _step_response_decision(
    trip_id: str,
    trips: _TripEvidence,
    events: pd.DataFrame,
    rule: dict[str, Any],
) -> dict[str, Any]:
    """5-S1 pedal-step m-of-n verdict (event evidence, trip-scoped)."""

    m_required = int(rule["m_of_n"]["m"])
    trip_events = events[events["trip_id"] == trip_id]
    evaluable = trip_events[_as_bool(trip_events["evaluable"])]
    trip_start, trip_end = trips.trip_span(trip_id)
    common = {
        "proxy_id": PROXY_IDS["5"], "sub_check_id": "5-S1",
        "unit_scope": "trip", "trip_id": trip_id,
        "decision_role": "verdict", "dtc_emitted": False,
        "confidence": "high", "confidence_capped_low": False,
    }
    if evaluable.empty:
        return _row(
            **common, segment_id=None,
            evidence_start_timestamp=trip_start,
            evidence_end_timestamp=trip_end, direction=None,
            result_state="not_evaluable",
            decision_reason="no_valid_events", decision_margin=None,
            dtc_candidate_label="P0106", evidence_count=0,
            opportunity_present=False,
        )
    complete = trip_events[_as_bool(trip_events["window_complete"])]
    counts = complete["no_response_count_recent_n"].astype("Float64")
    max_count = float(counts.max()) if counts.notna().any() else 0.0
    triggered = bool(
        _as_bool(complete["m_of_n_triggered"]).any()
    )
    segments = evaluable["segment_id"].unique()
    segment_id = str(segments[0]) if len(segments) == 1 else None
    return _row(
        **common, segment_id=segment_id,
        evidence_start_timestamp=evaluable["timestamp"].min(),
        evidence_end_timestamp=evaluable["timestamp"].max(),
        direction=None,
        result_state="triggered" if triggered else "pass",
        decision_reason=(
            "m_of_n_met" if triggered
            else "no_trigger_with_opportunity"
        ),
        decision_margin=float(max_count - m_required),
        dtc_candidate_label="P0106",
        evidence_count=int(len(evaluable)),
        opportunity_present=True,
    )


def build_engine_start_decisions(
    engine_start: pd.DataFrame,
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    """1-S1 decision rows (one per engine-start episode)."""

    wiring = registry["proxy_rules"]["1-S1"]["sensor_trust_wiring"]
    rows: list[dict[str, Any]] = []
    for episode in engine_start.itertuples(index=False):
        common = {
            "proxy_id": PROXY_IDS["1"], "sub_check_id": "1-S1",
            "unit_scope": "engine_start_episode",
            "trip_id": episode.trip_id,
            "segment_id": episode.segment_id,
            "engine_start_episode_id": episode.engine_start_episode_id,
            "evidence_start_timestamp": episode.start_timestamp,
            "evidence_end_timestamp": episode.end_timestamp,
            "direction": "low", "decision_role": "verdict",
            "dtc_candidate_label": "P0128", "dtc_emitted": False,
            "confidence": "high", "confidence_capped_low": False,
            "evidence_count": 1,
        }

        def not_evaluable(reason: str) -> dict[str, Any]:
            return _row(
                **common, result_state="not_evaluable",
                decision_reason=reason, decision_margin=None,
                opportunity_present=False,
            )

        if not _true(episode.s1s1_eligible):
            rows.append(not_evaluable("start_guards_failed"))
            continue
        if not _true(episode.budget_in_domain):
            rows.append(not_evaluable("budget_out_of_domain"))
            continue

        budget = float(episode.budget_seconds)
        time_to_target = episode.time_to_target_79c
        reached_in_budget = (
            pd.notna(time_to_target)
            and float(time_to_target) <= budget
        )
        support_evaluable = _true(episode.s1s4_evaluable)
        support_triggered = (
            support_evaluable and _true(episode.s1s4_exceed)
        )
        support_pass = (
            support_evaluable and not _true(episode.s1s4_exceed)
        )
        support_cold_soak_only = (
            not support_evaluable
            and episode.s1s4_not_evaluable_reason
            in COLD_SOAK_ONLY_REASONS
        )

        if support_triggered:
            rows.append(not_evaluable(
                wiring["support_trigger_reason"]
            ))
            continue
        if reached_in_budget:
            if support_pass:
                rows.append(_row(
                    **common, result_state="pass",
                    decision_reason="target_reached_within_budget",
                    decision_margin=budget - float(time_to_target),
                    opportunity_present=True,
                ))
            elif support_cold_soak_only:
                rows.append(not_evaluable(
                    "support_cold_soak_unavailable_pass_forbidden"
                ))
            else:
                rows.append(not_evaluable("support_not_evaluable"))
            continue
        if _true(episode.time_to_target_79c_is_right_censored):
            rows.append(not_evaluable("right_censored"))
            continue
        if not _true(episode.heat_guard_passed):
            rows.append(not_evaluable("insufficient_heat_input"))
            continue
        if support_pass or support_cold_soak_only:
            margin = (
                float(time_to_target) - budget
                if pd.notna(time_to_target) else None
            )
            rows.append(_row(
                **common, result_state="triggered",
                decision_reason="budget_expired_below_target",
                decision_margin=margin, opportunity_present=True,
            ))
            continue
        rows.append(not_evaluable("support_not_evaluable"))
    return rows


def build_cold_start_decisions(
    rule_state: pd.DataFrame,
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    """1-S4 and 4-S2 support rows (one per segment first row)."""

    first_rows = rule_state[_as_bool(rule_state["coldstart_first_row"])]
    thresholds = {
        "1-S4": float(
            registry["proxy_rules"]["1-S4"]["ect_abs_delta_c"]["value"]
        ),
        "4-S2": float(
            registry["proxy_rules"]["4-S2"]["iat_abs_delta_c"]["value"]
        ),
    }
    labels = {"1-S4": "P0116", "4-S2": "P0111"}
    proxies = {"1-S4": PROXY_IDS["1"], "4-S2": PROXY_IDS["4"]}
    columns = {
        "1-S4": ("s1s4_eligible", "s1s4_ect_aat_abs_delta",
                 "s1s4_exceed"),
        "4-S2": ("s4s2_eligible", "s4s2_iat_aat_abs_delta",
                 "s4s2_exceed"),
    }
    rows: list[dict[str, Any]] = []
    for sub_check in ("1-S4", "4-S2"):
        eligible_col, delta_col, exceed_col = columns[sub_check]
        for sample in first_rows.itertuples(index=False):
            common = {
                "proxy_id": proxies[sub_check],
                "sub_check_id": sub_check,
                "unit_scope": "segment_first_row",
                "trip_id": sample.trip_id,
                "segment_id": sample.segment_id,
                "evidence_start_timestamp": sample.timestamp,
                "evidence_end_timestamp": sample.timestamp,
                "direction": None, "decision_role": "support",
                "dtc_candidate_label": labels[sub_check],
                "dtc_emitted": False, "confidence": "low",
                "confidence_capped_low": False, "evidence_count": 1,
            }
            eligible = _true(getattr(sample, eligible_col))
            if not eligible:
                reason = sample.coldstart_not_evaluable_reason
                rows.append(_row(
                    **common, result_state="not_evaluable",
                    decision_reason=(
                        reason if isinstance(reason, str) and reason
                        else "witness_or_quality_failed"
                    ),
                    decision_margin=None, opportunity_present=False,
                ))
                continue
            delta = float(getattr(sample, delta_col))
            margin = delta - thresholds[sub_check]
            if _true(getattr(sample, exceed_col)):
                rows.append(_row(
                    **common, result_state="triggered",
                    decision_reason="cold_start_delta_exceeded",
                    decision_margin=margin, opportunity_present=True,
                ))
            else:
                rows.append(_row(
                    **common, result_state="pass",
                    decision_reason="cold_start_delta_within_bound",
                    decision_margin=margin, opportunity_present=True,
                ))
    return rows


def apply_routing_and_caps(
    decisions: pd.DataFrame,
    rule_state: pd.DataFrame,
    registry: dict[str, Any],
) -> pd.DataFrame:
    """Apply MAF/MAP arbitration and the 4-S2 confidence cap."""

    routing = registry["routing"]["maf_map_arbitration"]
    frame = decisions.copy()

    def witness_states(trip_id: str) -> dict[str, str]:
        rows = frame[
            (frame["trip_id"] == trip_id)
            & (frame["sub_check_id"].isin(routing["map_witnesses"]))
        ]
        return dict(zip(rows["sub_check_id"], rows["result_state"]))

    cap_trips = set(
        rule_state.loc[
            _as_bool(rule_state["s4s2_cap_active"]), "trip_id"
        ].unique()
    )

    for index, row in frame.iterrows():
        sub_check = row["sub_check_id"]
        if sub_check == "2-S3b":
            if row["result_state"] == "triggered":
                frame.at[index, "routing_attribution"] = "direct"
                frame.at[index, "routed_dtc"] = (
                    routing["direct_bypass"]["2-S3b"]
                )
                frame.at[index, "dtc_emitted"] = True
            continue
        if sub_check in routing["residual_evidence_checks"]:
            if row["result_state"] != "triggered":
                continue
            states = witness_states(row["trip_id"])
            witness_abnormal = any(
                states.get(check) == "triggered"
                for check in routing["map_witnesses"]
            )
            witnesses_evaluable = all(
                states.get(check) in {"pass", "triggered"}
                for check in routing["map_witnesses"]
            )
            if witness_abnormal:
                node = routing["map_witness_abnormal"]
            elif witnesses_evaluable:
                node = routing["map_witnesses_normal_and_evaluable"]
            else:
                node = routing["required_witnesses_not_evaluable"]
            frame.at[index, "routing_attribution"] = node["attribution"]
            frame.at[index, "routed_dtc"] = node["dtc"]
            if sub_check == "2-S2":
                frame.at[index, "dtc_emitted"] = True
            if row["trip_id"] in cap_trips:
                frame.at[index, "confidence"] = "low"
                frame.at[index, "confidence_capped_low"] = True
            continue
        if (
            row["decision_role"] == "verdict"
            and row["result_state"] == "triggered"
        ):
            frame.at[index, "dtc_emitted"] = True
            frame.at[index, "routed_dtc"] = row["dtc_candidate_label"]
    return frame


def build_proxy_decisions(
    evidence: dict[str, pd.DataFrame],
    registry: dict[str, Any],
) -> pd.DataFrame:
    """Assemble the full decision table (decision grain)."""

    rule_state = evidence["rule_state"]
    trips = _TripEvidence(evidence["episodes"], rule_state)
    rows = build_trip_decisions(
        trips, evidence["events"], rule_state, registry
    )
    rows += build_engine_start_decisions(
        evidence["engine_start"], registry
    )
    rows += build_cold_start_decisions(rule_state, registry)

    frame = pd.DataFrame(rows, columns=DECISION_COLUMNS)
    frame = apply_routing_and_caps(frame, rule_state, registry)
    frame = frame.sort_values(
        ["proxy_id", "sub_check_id", "trip_id",
         "evidence_start_timestamp"],
        kind="mergesort",
    ).reset_index(drop=True)
    frame["dtc_emitted"] = frame["dtc_emitted"].astype(bool)
    frame["confidence_capped_low"] = (
        frame["confidence_capped_low"].astype(bool)
    )
    frame["opportunity_present"] = (
        frame["opportunity_present"].astype(bool)
    )
    frame["evidence_count"] = frame["evidence_count"].astype("Int64")
    return frame


def _column_names(frame: pd.DataFrame) -> list[str]:
    return [str(column) for column in frame.columns]


def run_proxy_decision_builder(
    layout: RunLayout,
    *,
    creation_time_utc: str | None = None,
) -> dict[str, Any]:
    """Execute script 70 and write the output plus the manifest."""

    registry = load_registry(layout)
    evidence, meta = load_evidence(layout)

    decisions = build_proxy_decisions(evidence, registry)

    layout.decisions_dir.mkdir(parents=True, exist_ok=True)
    decisions.to_csv(
        layout.proxy_decisions, index=False, float_format="%.15g",
        lineterminator="\n",
    )

    def run_descriptor(path: Path, artifact_id: str) -> ArtifactDescriptor:
        return ArtifactDescriptor.from_file(
            path, artifact_id=artifact_id,
            manifest_path=layout.run_relative_posix(path),
            path_base="run_dir",
        )

    registry_descriptor = ArtifactDescriptor.from_file(
        layout.calibration_registry,
        artifact_id="calibration_registry",
        manifest_path=(
            "data_layer/calibration/calibration_registry.v1.json"
        ),
        path_base="repo_root",
    )
    manifest = build_stage_manifest(
        stage_id=STAGE_ID,
        schema_version=SCHEMA_VERSION,
        script_version=SCRIPT_VERSION,
        source_dataset_identity=meta["source_dataset_identity"],
        input_artifacts=[
            run_descriptor(layout.rule_state, "rule_state"),
            run_descriptor(
                layout.engine_start_rule_state,
                "engine_start_rule_state",
            ),
            run_descriptor(layout.pedal_step_events,
                           "pedal_step_events"),
            run_descriptor(layout.duration_episodes,
                           "duration_episodes"),
            registry_descriptor,
        ],
        output_artifacts=[
            run_descriptor(layout.proxy_decisions, "proxy_decisions"),
        ],
        calibration_version=registry["calibration_version"],
        creation_time_utc=creation_time_utc,
    )
    state_counts = (
        decisions.groupby(["sub_check_id", "result_state"])
        .size().to_dict()
    )
    manifest["decision_schema"] = {
        "proxy_decisions": {
            "grain": "decision",
            "ordered_columns": _column_names(decisions),
            "row_count": len(decisions),
        },
        "decision_semantics": {
            "unit_scopes": {
                "trip": (
                    "1-S2, 1-S3, 2-S2, 2-S3b, 3-S1a, 3-S1b, 4-S1, "
                    "4-S3, 5-S1, 5-S2, 5-S3 — one row per trip"
                ),
                "engine_start_episode": "1-S1 — one row per episode",
                "segment_first_row": (
                    "1-S4, 4-S2 — one row per canonical segment "
                    "first row"
                ),
            },
            "alignment": (
                "every row carries trip_id, evidence start/end "
                "timestamps, and segment_id (null when the evaluated "
                "evidence spans several segments); triggered rows "
                "always localize to the triggering evidence span"
            ),
            "opportunity_conventions": {
                "1-S2": (
                    "total eligible seconds >= 180 (definition: '180 s "
                    "of evaluable post-warm-up time')"
                ),
                "1-S3": "a single eligible run >= 360 s",
                "2-S2/2-S3b/3-S1b": (
                    "a single eligible run >= the rule's frozen "
                    "persistence (the minimal window in which a "
                    "trigger could occur); implementation choice, "
                    "documented — not an explicit frozen criterion"
                ),
                "3-S1a/5-S2": "a single eligible run >= 30 s",
                "4-S1/5-S3": (
                    "a single eligible run >= 240 s and at least one "
                    "context-opportunity episode"
                ),
                "5-S1": "at least one evaluable pedal-step event",
            },
            "routing": (
                "frozen maf_map_arbitration: 2-S3b bypasses directly "
                "to P0102; triggered 2-S2/5-S2 residual evidence is "
                "attributed via the 5-S1/5-S3 witnesses (abnormal -> "
                "MAP P0106, normal+evaluable -> MAF P0101, not "
                "evaluable -> unisolated P006A); residual sign alone "
                "never attributes"
            ),
            "confidence": (
                "high for frozen verdicts, provisional for 3-S1b, low "
                "for 1-S4/4-S2 support; triggered 2-S2/5-S2 residual "
                "evidence in a trip with an active 4-S2 cap is capped "
                "to low with confidence_capped_low = true"
            ),
        },
        "result_state_counts": {
            f"{key[0]}:{key[1]}": int(value)
            for key, value in sorted(state_counts.items())
        },
    }
    validate_stage_manifest(manifest)
    write_json_atomic(layout.proxy_decision_manifest, manifest)
    return {
        "decision_rows": len(decisions),
        "triggered_rows": int(
            (decisions["result_state"] == "triggered").sum()
        ),
        "manifest": layout.run_relative_posix(
            layout.proxy_decision_manifest
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    layout = RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT)
    summary = run_proxy_decision_builder(layout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
