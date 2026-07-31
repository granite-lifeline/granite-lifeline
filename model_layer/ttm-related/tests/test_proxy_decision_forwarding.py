"""
Tests for forwarding Data Layer proxy decisions (GL-368).

Covers the loader contract, the verdict -> risk_score mapping, the
confidence mapping, trip/segment matching across the three unit scopes,
and the MAF/MAP arbitration gate on 5-S2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.proxy_decision_forwarding import (  # noqa: E402
    DECISION_REQUIRED_COLUMNS,
    FORWARDED_PROXY_IDS,
    SCORE_DTC_EMITTED,
    SCORE_EVIDENCE_TRIGGERED,
    SCORE_NONE,
    SCORE_VERDICT_TRIGGERED,
    forward_verdicts,
    load_proxy_decisions,
)
from proxy_decision_fixtures import (  # noqa: E402
    IAT_PROXY,
    MAP_PROXY,
    make_decision_frame,
    make_decision_row,
    make_triggered_row,
    write_decisions_csv,
)


def verdict_for(rows, proxy_id=IAT_PROXY, trip="trip_0001", segment=None):
    """Score one proxy type from handcrafted decision rows."""
    frame = make_decision_frame(rows)
    return forward_verdicts(frame, trip, segment)[proxy_id]


class TestLoadProxyDecisions:
    def test_reads_the_frozen_21_column_contract(self, tmp_path):
        path = write_decisions_csv(tmp_path / "decisions.csv")

        decisions = load_proxy_decisions(path)

        assert list(decisions.columns) == DECISION_REQUIRED_COLUMNS
        assert len(decisions) == 1

    def test_missing_file_raises_clear_error(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            load_proxy_decisions(tmp_path / "absent.csv")

    def test_missing_column_names_the_offender(self, tmp_path):
        path = write_decisions_csv(
            tmp_path / "decisions.csv", drop_columns=("result_state",)
        )

        with pytest.raises(ValueError, match="result_state"):
            load_proxy_decisions(path)

    def test_boolean_columns_are_real_booleans(self, tmp_path):
        path = write_decisions_csv(
            tmp_path / "decisions.csv", [make_triggered_row()]
        )

        decisions = load_proxy_decisions(path)

        assert decisions["dtc_emitted"].dtype == bool
        assert bool(decisions["dtc_emitted"].iloc[0]) is True

    def test_non_boolean_value_is_rejected(self, tmp_path):
        path = write_decisions_csv(
            tmp_path / "decisions.csv",
            [make_decision_row(dtc_emitted="maybe")],
        )

        with pytest.raises(ValueError, match="dtc_emitted"):
            load_proxy_decisions(path)

    def test_other_proxy_ids_are_filtered_out(self, tmp_path):
        path = write_decisions_csv(
            tmp_path / "decisions.csv",
            [
                make_decision_row(),
                make_decision_row(
                    proxy_id="cooling_degradation", sub_check_id="1-S1"
                ),
            ],
        )

        decisions = load_proxy_decisions(path)

        assert set(decisions["proxy_id"]) == {IAT_PROXY}


class TestScoreMapping:
    def test_emitted_dtc_scores_high(self):
        verdict = verdict_for([make_triggered_row()])

        assert verdict.score == SCORE_DTC_EMITTED

    def test_triggered_verdict_without_dtc_scores_medium(self):
        verdict = verdict_for([
            make_triggered_row(dtc_emitted=False, routed_dtc=None)
        ])

        assert verdict.score == SCORE_VERDICT_TRIGGERED

    def test_triggered_support_evidence_scores_lower(self):
        verdict = verdict_for([
            make_triggered_row(
                sub_check_id="4-S2",
                unit_scope="segment_first_row",
                decision_role="support",
                dtc_emitted=False,
                routed_dtc=None,
                confidence="low",
            )
        ], segment="trip_0001_seg_001")

        assert verdict.score == SCORE_EVIDENCE_TRIGGERED

    def test_verdict_outranks_support_in_the_same_trip(self):
        verdict = verdict_for(
            [
                make_triggered_row(
                    sub_check_id="4-S2",
                    decision_role="support",
                    dtc_emitted=False,
                    confidence="low",
                ),
                make_triggered_row(),
            ]
        )

        assert verdict.score == SCORE_DTC_EMITTED

    def test_all_pass_scores_zero(self):
        verdict = verdict_for([make_decision_row()])

        assert verdict.score == SCORE_NONE
        assert verdict.note is None

    def test_not_evaluable_scores_zero(self):
        verdict = verdict_for([
            make_decision_row(
                result_state="not_evaluable",
                decision_reason="insufficient_evaluable_time",
            )
        ])

        assert verdict.score == SCORE_NONE

    def test_both_types_are_always_present(self):
        verdicts = forward_verdicts(
            make_decision_frame([make_triggered_row()]), "trip_0001"
        )

        assert set(verdicts) == set(FORWARDED_PROXY_IDS)
        assert verdicts[MAP_PROXY].score == SCORE_NONE

    def test_note_carries_dtc_and_sub_check(self):
        verdict = verdict_for([make_triggered_row()])

        assert "P0111" in verdict.note
        assert "4-S1" in verdict.note
        assert IAT_PROXY in verdict.note


class TestConfidenceMapping:
    def test_high_confidence_maps_to_090(self):
        verdict = verdict_for([make_triggered_row(confidence="high")])

        assert verdict.confidence == 0.9

    def test_provisional_maps_to_060(self):
        verdict = verdict_for([
            make_triggered_row(confidence="provisional")
        ])

        assert verdict.confidence == 0.6

    def test_capped_low_overrides_the_stated_label(self):
        verdict = verdict_for([
            make_triggered_row(
                confidence="high", confidence_capped_low=True
            )
        ])

        assert verdict.confidence == 0.35

    def test_weakest_backing_row_wins(self):
        verdict = verdict_for([
            make_triggered_row(confidence="high"),
            make_triggered_row(
                sub_check_id="4-S3", confidence="provisional"
            ),
        ])

        assert verdict.confidence == 0.6


class TestUnitScopeMatching:
    def test_other_trips_are_ignored(self):
        verdict = verdict_for(
            [make_triggered_row(trip_id="trip_0002")], trip="trip_0001"
        )

        assert verdict.score == SCORE_NONE

    def test_trip_scope_applies_to_any_segment(self):
        verdict = verdict_for(
            [make_triggered_row(segment_id="trip_0001_seg_001")],
            segment="trip_0001_seg_004",
        )

        assert verdict.score == SCORE_DTC_EMITTED

    def test_segment_scope_only_applies_to_its_own_segment(self):
        rows = [
            make_triggered_row(
                sub_check_id="4-S2",
                unit_scope="segment_first_row",
                segment_id="trip_0001_seg_001",
                decision_role="support",
                dtc_emitted=False,
            )
        ]

        assert verdict_for(
            rows, segment="trip_0001_seg_002"
        ).score == SCORE_NONE
        assert verdict_for(
            rows, segment="trip_0001_seg_001"
        ).score == SCORE_EVIDENCE_TRIGGERED

    def test_segment_scope_without_a_segment_id_is_trip_wide(self):
        verdict = verdict_for(
            [
                make_triggered_row(
                    sub_check_id="4-S2",
                    unit_scope="segment_first_row",
                    segment_id=None,
                    decision_role="support",
                    dtc_emitted=False,
                )
            ],
            segment="trip_0001_seg_009",
        )

        assert verdict.score == SCORE_EVIDENCE_TRIGGERED


class TestArbitrationRouting:
    def test_5s2_routed_to_map_counts(self):
        verdict = verdict_for(
            [
                make_triggered_row(
                    proxy_id=MAP_PROXY,
                    sub_check_id="5-S2",
                    decision_role="arbitration_evidence",
                    dtc_emitted=False,
                    routing_attribution="MAP",
                    routed_dtc="P0106",
                )
            ],
            proxy_id=MAP_PROXY,
        )

        assert verdict.score == SCORE_EVIDENCE_TRIGGERED
        assert "P0106" in verdict.note

    def test_5s2_routed_to_maf_is_not_counted(self):
        verdict = verdict_for(
            [
                make_triggered_row(
                    proxy_id=MAP_PROXY,
                    sub_check_id="5-S2",
                    decision_role="arbitration_evidence",
                    dtc_emitted=False,
                    routing_attribution="MAF",
                    routed_dtc="P0101",
                )
            ],
            proxy_id=MAP_PROXY,
        )

        assert verdict.score == SCORE_NONE

    def test_map_verdict_sub_checks_are_unaffected_by_routing(self):
        verdict = verdict_for(
            [
                make_triggered_row(
                    proxy_id=MAP_PROXY,
                    sub_check_id="5-S1",
                    dtc_candidate_label="P0106",
                    routed_dtc="P0106",
                    routing_attribution="MAF",
                )
            ],
            proxy_id=MAP_PROXY,
        )

        assert verdict.score == SCORE_DTC_EMITTED


class TestRealDelivery:
    """Guards against drift in the Data Layer's actual output."""

    DECISIONS = Path(
        "data/processed/runs/gl366_verify/proxy/70_decisions/"
        "proxy_decisions.csv"
    )

    def _resolve(self):
        for base in Path(__file__).resolve().parents:
            candidate = base / self.DECISIONS
            if candidate.exists():
                return candidate
        return None

    def test_healthy_corpus_forwards_zero_risk(self):
        path = self._resolve()
        if path is None:
            pytest.skip("GL-366 verification run directory not present")

        decisions = load_proxy_decisions(path)
        trip = decisions["trip_id"].iloc[0]
        verdicts = forward_verdicts(decisions, trip)

        assert set(verdicts) == set(FORWARDED_PROXY_IDS)
        assert all(v.score == SCORE_NONE for v in verdicts.values())

    def test_no_triggered_rows_exist_in_the_healthy_corpus(self):
        path = self._resolve()
        if path is None:
            pytest.skip("GL-366 verification run directory not present")

        decisions = load_proxy_decisions(path)

        assert set(decisions["result_state"]) <= {
            "pass", "not_evaluable"
        }
        assert not decisions["dtc_emitted"].any()


def test_forward_verdicts_leaves_the_input_frame_untouched():
    frame = make_decision_frame([make_triggered_row()])
    before = frame.copy()

    forward_verdicts(frame, "trip_0001")

    pd.testing.assert_frame_equal(frame, before)
