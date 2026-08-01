"""Contract tests for script 70 proxy decisions."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.manifests import (  # noqa: E402
    load_json_object,
)
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402


def _load_script70():
    path = (
        REPO_ROOT
        / "data_layer/proxy_failure/src/70_proxy_decision_builder.py"
    )
    spec = importlib.util.spec_from_file_location("script70", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["script70"] = module
    spec.loader.exec_module(module)
    return module


script70 = _load_script70()
REGISTRY = load_json_object(
    RunLayout.for_run_id("t", repo_root=REPO_ROOT).calibration_registry
)

T = "2026-07-19T10:{:02d}:{:02d}Z"


def ts(minute: int, second: int = 0) -> str:
    return T.format(minute, second)


def make_rule_state(n: int = 5, trip: str = "T1") -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "timestamp": [ts(0, i) for i in range(n)],
            "trip_id": trip,
            "segment_id": f"{trip}-S1",
            "row_in_segment": range(n),
            "intake_temp": 20.0,
            "s4s3_evaluable": False,
            "s4s3_below_range": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "s4s3_above_range": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "coldstart_first_row": False,
            "coldstart_not_evaluable_reason": pd.Series(
                pd.NA, index=range(n), dtype="string"),
            "s1s4_eligible": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "s1s4_ect_aat_abs_delta": pd.Series(
                pd.NA, index=range(n), dtype="Float64"),
            "s1s4_exceed": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "s4s2_eligible": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "s4s2_iat_aat_abs_delta": pd.Series(
                pd.NA, index=range(n), dtype="Float64"),
            "s4s2_exceed": pd.Series(
                pd.NA, index=range(n), dtype="boolean"),
            "s4s2_cap_active": False,
        }
    )
    return frame


EPISODE_COLUMNS = [
    "rule_id", "episode_kind", "trip_id", "segment_id",
    "continuity_block_id", "start_timestamp", "end_timestamp",
    "start_row_in_segment", "end_row_in_segment", "sample_count",
    "duration_seconds", "elapsed_span_seconds",
    "persistence_required_s", "meets_persistence", "margin_seconds",
    "episode_index",
]


def episode(rule_id, kind, *, trip="T1", seg="T1-S1", start=ts(1),
            end=ts(2), duration=10.0, required=None, meets=None,
            margin=None):
    return {
        "rule_id": rule_id, "episode_kind": kind, "trip_id": trip,
        "segment_id": seg, "continuity_block_id": 1.0,
        "start_timestamp": start, "end_timestamp": end,
        "start_row_in_segment": 0, "end_row_in_segment": 1,
        "sample_count": int(duration),
        "duration_seconds": float(duration),
        "elapsed_span_seconds": float(duration) - 1.0,
        "persistence_required_s": required,
        "meets_persistence": meets, "margin_seconds": margin,
        "episode_index": 1,
    }


def episodes_frame(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=EPISODE_COLUMNS)
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)


EVENT_COLUMNS = [
    "timestamp", "trip_id", "segment_id", "row_in_segment",
    "window_complete", "evaluable", "event_result",
    "no_response_count_recent_n", "m_of_n_triggered",
]


def event(*, trip="T1", seg="T1-S1", stamp=ts(3), result="response",
          count=0, triggered=False, complete=True, evaluable=True):
    return {
        "timestamp": stamp, "trip_id": trip, "segment_id": seg,
        "row_in_segment": 0, "window_complete": complete,
        "evaluable": evaluable, "event_result": result,
        "no_response_count_recent_n": count,
        "m_of_n_triggered": triggered,
    }


def events_frame(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


ENGINE_START_COLUMNS = [
    "engine_start_episode_id", "trip_id", "segment_id",
    "start_timestamp", "end_timestamp", "episode_duration_seconds",
    "termination_reason", "ect_start", "aat_start",
    "s1s1_start_quality_valid", "s1s1_eligible", "ambient_bin",
    "budget_seconds", "budget_in_domain", "time_to_target_79c",
    "time_to_target_79c_is_right_censored",
    "time_to_target_79c_censor_time_s", "maf_integral_at_expiry",
    "heat_guard_passed", "s1s4_evaluable", "s1s4_exceed",
    "s1s4_not_evaluable_reason",
]


def start_episode(episode_id, *, eligible=True, in_domain=True,
                  budget=900.0, reached=None, censored=False,
                  heat=True, s14_evaluable=False, s14_exceed=False,
                  s14_reason="cold_soak_gap_unavailable"):
    return {
        "engine_start_episode_id": episode_id, "trip_id": "T1",
        "segment_id": "T1-S1", "start_timestamp": ts(0),
        "end_timestamp": ts(20), "episode_duration_seconds": 1200.0,
        "termination_reason": "continuity_break", "ect_start": 20.0,
        "aat_start": 10.0, "s1s1_start_quality_valid": True,
        "s1s1_eligible": eligible, "ambient_bin": ">5",
        "budget_seconds": budget, "budget_in_domain": in_domain,
        "time_to_target_79c": reached,
        "time_to_target_79c_is_right_censored": censored,
        "time_to_target_79c_censor_time_s": pd.NA,
        "maf_integral_at_expiry": 5000.0,
        "heat_guard_passed": heat, "s1s4_evaluable": s14_evaluable,
        "s1s4_exceed": s14_exceed,
        "s1s4_not_evaluable_reason": (
            s14_reason if not s14_evaluable else pd.NA
        ),
    }


def engine_start_frame(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=ENGINE_START_COLUMNS)
    return pd.DataFrame(rows, columns=ENGINE_START_COLUMNS)


def build(rule_state=None, engine_start=None, events=None,
          episode_rows=None) -> pd.DataFrame:
    evidence = {
        "rule_state": (
            rule_state if rule_state is not None else make_rule_state()
        ),
        "engine_start": engine_start_frame(engine_start or []),
        "events": events_frame(events or []),
        "episodes": episodes_frame(episode_rows or []),
    }
    return script70.build_proxy_decisions(evidence, REGISTRY)


def pick(frame, sub_check, trip="T1"):
    rows = frame[
        (frame["sub_check_id"] == sub_check)
        & (frame["trip_id"] == trip)
    ]
    assert len(rows) == 1, f"{sub_check}: {len(rows)} rows"
    return rows.iloc[0]


def full_opportunity_episodes():
    return [
        episode("1-S2", "eligible", start=ts(1), end=ts(2),
                duration=100.0, required=180.0, meets=False,
                margin=-80.0),
        episode("1-S2", "eligible", start=ts(3), end=ts(4),
                duration=90.0, required=180.0, meets=False,
                margin=-90.0),
        episode("1-S3", "eligible", duration=360.0, required=360.0,
                meets=True, margin=0.0),
        episode("2-S2", "eligible", duration=10.0, required=None),
        episode("2-S3b", "eligible", duration=10.0, required=None),
        episode("3-S1a", "eligible", duration=30.0, required=30.0,
                meets=True, margin=0.0),
        episode("3-S1b", "eligible", duration=2.0, required=None),
        episode("4-S1", "eligible", duration=240.0, required=240.0,
                meets=True, margin=0.0),
        episode("4-S1", "context_opportunity", duration=30.0),
        episode("5-S2", "eligible", duration=30.0, required=30.0,
                meets=True, margin=0.0),
        episode("5-S3", "eligible", duration=240.0, required=240.0,
                meets=True, margin=0.0),
        episode("5-S3", "context_opportunity", duration=30.0),
    ]


def opportunity_episode_for(rule_id):
    mapping = {
        "2-S2": episode("2-S2", "eligible", duration=10.0,
                        required=None),
        "5-S2": episode("5-S2", "eligible", duration=30.0,
                        required=30.0, meets=True, margin=0.0),
        "2-S3b": episode("2-S3b", "eligible", duration=10.0,
                         required=None),
    }
    return mapping[rule_id]


def test_healthy_trip_passes_where_opportunity_exists() -> None:
    rule_state = make_rule_state()
    rule_state["s4s3_evaluable"] = True
    decisions = build(
        rule_state=rule_state,
        events=[event()],
        episode_rows=full_opportunity_episodes(),
    )

    for sub_check in ["1-S2", "2-S2", "2-S3b", "3-S1a", "3-S1b",
                      "4-S1", "4-S3", "5-S1", "5-S2", "5-S3", "1-S3"]:
        row = pick(decisions, sub_check)
        assert row["result_state"] == "pass", sub_check
        assert not row["dtc_emitted"], sub_check
    assert (
        pick(decisions, "1-S2")["opportunity_present"]
    )  # 100 + 90 >= 180 total-eligible convention


def test_no_opportunity_yields_specific_not_evaluable_reasons() -> None:
    decisions = build()

    expected = {
        "1-S2": "insufficient_evaluable_time",
        "1-S3": "below_minimum_evaluable_window",
        "2-S2": "no_qualifying_opportunity",
        "3-S1a": "no_qualifying_masked_opportunity",
        "4-S1": "no_context_opportunity",
        "4-S3": "signal_unavailable",
        "5-S1": "no_valid_events",
        "5-S2": "outside_steady_domain",
        "5-S3": "no_context_opportunity",
    }
    for sub_check, reason in expected.items():
        row = pick(decisions, sub_check)
        assert row["result_state"] == "not_evaluable", sub_check
        assert row["decision_reason"] == reason, sub_check


def test_triggered_residual_routes_to_maf_when_witnesses_pass() -> None:
    rows = full_opportunity_episodes() + [
        episode("2-S2", "residual_low", start=ts(5), end=ts(6),
                duration=12.0, required=10.0, meets=True, margin=2.0),
    ]
    decisions = build(events=[event()], episode_rows=rows)

    row = pick(decisions, "2-S2")
    assert row["result_state"] == "triggered"
    assert row["decision_margin"] == 2.0
    assert row["direction"] == "low"
    assert row["routing_attribution"] == "MAF"
    assert row["routed_dtc"] == "P0101"
    assert row["dtc_emitted"]
    assert row["segment_id"] == "T1-S1"
    assert row["evidence_start_timestamp"] == ts(5)
    assert row["evidence_end_timestamp"] == ts(6)


def test_triggered_residual_routes_to_map_when_witness_abnormal(
) -> None:
    rows = full_opportunity_episodes() + [
        episode("2-S2", "residual_low", duration=12.0, required=10.0,
                meets=True, margin=2.0),
        episode("5-S3", "flat_under_context", duration=130.0,
                required=120.0, meets=True, margin=10.0),
    ]
    decisions = build(events=[event()], episode_rows=rows)

    assert pick(decisions, "5-S3")["result_state"] == "triggered"
    row = pick(decisions, "2-S2")
    assert row["routing_attribution"] == "MAP"
    assert row["routed_dtc"] == "P0106"


def test_triggered_residual_unisolated_without_witnesses() -> None:
    rows = [
        opportunity_episode_for("2-S2"),
        episode("2-S2", "residual_low", duration=12.0, required=10.0,
                meets=True, margin=2.0),
    ]
    decisions = build(episode_rows=rows)

    row = pick(decisions, "2-S2")
    assert row["result_state"] == "triggered"
    assert row["routing_attribution"] == "unisolated"
    assert row["routed_dtc"] == "P006A"


def test_zero_maf_bypasses_arbitration() -> None:
    rows = [
        opportunity_episode_for("2-S3b"),
        episode("2-S3b", "zero_maf_firing", duration=11.0,
                required=10.0, meets=True, margin=1.0),
    ]
    decisions = build(episode_rows=rows)

    row = pick(decisions, "2-S3b")
    assert row["result_state"] == "triggered"
    assert row["routing_attribution"] == "direct"
    assert row["routed_dtc"] == "P0102"
    assert row["dtc_emitted"]


def test_precursor_returns_pending_and_never_triggered() -> None:
    rows = [
        episode("1-S3", "eligible", duration=400.0, required=360.0,
                meets=True, margin=40.0),
        episode("1-S3", "precursor", duration=200.0, required=180.0,
                meets=True, margin=20.0),
    ]
    decisions = build(episode_rows=rows)

    row = pick(decisions, "1-S3")
    assert row["result_state"] == "pending"
    assert not row["dtc_emitted"]
    assert row["decision_role"] == "pending_precursor"


def test_arbitration_evidence_never_emits_a_dtc() -> None:
    rows = [
        opportunity_episode_for("5-S2"),
        episode("5-S2", "residual_high", duration=35.0, required=30.0,
                meets=True, margin=5.0),
    ]
    decisions = build(episode_rows=rows)

    row = pick(decisions, "5-S2")
    assert row["result_state"] == "triggered"
    assert row["decision_role"] == "arbitration_evidence"
    assert not row["dtc_emitted"]
    assert row["routing_attribution"] == "unisolated"


def test_cap_lowers_confidence_of_triggered_residual_evidence(
) -> None:
    rule_state = make_rule_state()
    rule_state.loc[2, "s4s2_cap_active"] = True
    rows = [
        opportunity_episode_for("2-S2"),
        episode("2-S2", "residual_low", duration=12.0, required=10.0,
                meets=True, margin=2.0),
    ]
    decisions = build(rule_state=rule_state, episode_rows=rows)

    row = pick(decisions, "2-S2")
    assert row["confidence"] == "low"
    assert row["confidence_capped_low"]


def test_step_response_m_of_n_verdict() -> None:
    decisions = build(events=[
        event(stamp=ts(3), result="no_response", count=1),
        event(stamp=ts(4), result="no_response", count=2),
        event(stamp=ts(5), result="no_response", count=3,
              triggered=True),
    ])

    row = pick(decisions, "5-S1")
    assert row["result_state"] == "triggered"
    assert row["decision_reason"] == "m_of_n_met"
    assert row["decision_margin"] == 0.0
    assert row["dtc_emitted"]
    assert row["routed_dtc"] == "P0106"


def test_engine_start_wiring_matrix() -> None:
    engine_start = [
        start_episode("e1", reached=600.0, s14_evaluable=True,
                      s14_exceed=False),
        start_episode("e2", reached=600.0,
                      s14_reason="cold_soak_gap_unavailable"),
        start_episode("e3", reached=600.0, s14_evaluable=True,
                      s14_exceed=True),
        start_episode("e4", reached=None, heat=True,
                      s14_reason="cold_soak_gap_unavailable"),
        start_episode("e5", reached=None, censored=True),
        start_episode("e6", eligible=False),
        start_episode("e7", reached=None, heat=False),
    ]
    decisions = build(engine_start=engine_start)
    rows = decisions[decisions["sub_check_id"] == "1-S1"]
    by_id = rows.set_index("engine_start_episode_id")

    assert by_id.loc["e1", "result_state"] == "pass"
    assert by_id.loc["e1", "decision_margin"] == 300.0
    assert by_id.loc["e2", "result_state"] == "not_evaluable"
    assert by_id.loc["e2", "decision_reason"] == (
        "support_cold_soak_unavailable_pass_forbidden"
    )
    assert by_id.loc["e3", "result_state"] == "not_evaluable"
    assert by_id.loc["e3", "decision_reason"] == "ect_plausibility"
    assert by_id.loc["e4", "result_state"] == "triggered"
    assert by_id.loc["e4", "dtc_emitted"]
    assert by_id.loc["e5", "result_state"] == "not_evaluable"
    assert by_id.loc["e5", "decision_reason"] == "right_censored"
    assert by_id.loc["e6", "decision_reason"] == "start_guards_failed"
    assert by_id.loc["e7", "decision_reason"] == (
        "insufficient_heat_input"
    )


def test_cold_start_support_rows() -> None:
    rule_state = make_rule_state()
    rule_state.loc[0, "coldstart_first_row"] = True
    rule_state.loc[0, "s1s4_eligible"] = True
    rule_state.loc[0, "s1s4_ect_aat_abs_delta"] = 20.0
    rule_state.loc[0, "s1s4_exceed"] = True
    rule_state.loc[0, "s4s2_eligible"] = True
    rule_state.loc[0, "s4s2_iat_aat_abs_delta"] = 3.0
    rule_state.loc[0, "s4s2_exceed"] = False
    decisions = build(rule_state=rule_state)

    s14 = pick(decisions, "1-S4")
    assert s14["result_state"] == "triggered"
    assert s14["decision_role"] == "support"
    assert not s14["dtc_emitted"]
    assert s14["decision_margin"] == 5.0
    assert s14["confidence"] == "low"
    s42 = pick(decisions, "4-S2")
    assert s42["result_state"] == "pass"
    assert s42["decision_margin"] == -4.0


def test_every_row_carries_alignment_columns() -> None:
    rule_state = make_rule_state()
    rule_state["s4s3_evaluable"] = True
    decisions = build(
        rule_state=rule_state,
        engine_start=[start_episode("e1", reached=600.0,
                                    s14_evaluable=True)],
        events=[event()],
        episode_rows=full_opportunity_episodes(),
    )

    assert decisions["trip_id"].notna().all()
    assert decisions["evidence_start_timestamp"].notna().all()
    assert decisions["evidence_end_timestamp"].notna().all()
    assert set(decisions["decision_role"]) <= {
        "verdict", "pending_precursor", "support",
        "arbitration_evidence",
    }
    assert set(decisions["result_state"]) <= {
        "pass", "triggered", "not_evaluable", "pending",
    }


def test_determinism() -> None:
    rule_state = make_rule_state()
    rule_state["s4s3_evaluable"] = True
    kwargs = dict(
        rule_state=rule_state,
        engine_start=[start_episode("e1", reached=600.0,
                                    s14_evaluable=True)],
        events=[event()],
        episode_rows=full_opportunity_episodes(),
    )

    first = build(**kwargs)
    second = build(**kwargs)

    pd.testing.assert_frame_equal(first, second)
