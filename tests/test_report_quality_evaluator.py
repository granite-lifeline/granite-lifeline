"""
Tests for report_layer.evaluation.report_quality_evaluator.

This module previously had no dedicated test coverage. These tests
focus on the negation-aware confirmed-fault-language check in
evaluate_hedging_appropriateness(), which is the exact bug documented
in report_challenge.md's Limitations section: "It penalised the
baseline for the negated phrase 'no confirmed fault yet' as if it
were overconfident." Also covers the other three dimensions with
basic cases so the module has some regression protection.
"""

from report_layer.evaluation.report_quality_evaluator import (
    _find_unnegated_phrases,
    evaluate_actionability,
    evaluate_factual_grounding,
    evaluate_hedging_appropriateness,
    evaluate_readability,
    evaluate_report,
)


class TestFindUnnegatedPhrases:
    def test_bare_phrase_is_a_hit(self):
        assert _find_unnegated_phrases(
            "the fault is confirmed", ["confirmed"]
        ) == ["confirmed"]

    def test_negated_phrase_is_not_a_hit(self):
        assert _find_unnegated_phrases(
            "no confirmed fault yet", ["confirmed"]
        ) == []


class TestEvaluateHedgingAppropriateness:
    def test_no_confirmed_fault_yet_is_not_penalised(self):
        """
        The exact known-bug case from report_challenge.md: "no
        confirmed fault yet" must not be scored as an unhedged claim.
        """
        report = {
            "anomaly_description": (
                "The coolant temperature is running slightly higher "
                "than expected. There is no confirmed fault yet, but "
                "the pattern should be checked soon."
            ),
            "possible_cause": (
                "This may indicate early signs of thermostat wear, "
                "though the evidence could also suggest normal "
                "variation."
            ),
        }
        score, notes = evaluate_hedging_appropriateness(report)
        assert not any("confirmed fault language" in n for n in notes)
        assert score == 1.0

    def test_genuinely_unhedged_confirmed_language_is_penalised(self):
        report = {
            "anomaly_description": (
                "The thermostat has failed and the fault is "
                "confirmed by the sensor readings."
            ),
            "possible_cause": "The radiator is definitely broken.",
        }
        score, notes = evaluate_hedging_appropriateness(report)
        assert any("confirmed fault language" in n for n in notes)
        assert score < 1.0

    def test_missing_hedging_in_cause_is_penalised(self):
        report = {
            "anomaly_description": "Coolant temperature is elevated.",
            "possible_cause": (
                "The radiator is clogged and the thermostat is stuck."
            ),
        }
        score, notes = evaluate_hedging_appropriateness(report)
        assert any("lacks hedging" in n for n in notes)


class TestEvaluateFactualGrounding:
    def test_report_with_no_numbers_is_penalised(self):
        context = "Coolant temperature: 98 degrees (reference: 90-95)"
        report = {
            "anomaly_description": "The engine seems to be running warm.",
            "possible_cause": "This could relate to the cooling system.",
            "recommended_action": ["Check the cooling system soon."],
        }
        score, notes = evaluate_factual_grounding(report, context)
        assert any("does not reference" in n for n in notes)


class TestEvaluateReadability:
    def test_unexplained_raw_field_name_is_penalised(self):
        report = {
            "anomaly_description": "coolant_temp is above range.",
            "possible_cause": "Could relate to the radiator.",
        }
        score, notes = evaluate_readability(report)
        assert any("raw field names" in n for n in notes)


class TestEvaluateActionability:
    def test_appropriate_action_count_and_urgency(self):
        report = {
            "recommended_action": [
                "Book a mechanic appointment soon to check the "
                "cooling system for leaks or blockages.",
                "Monitor the temperature gauge during the next few "
                "drives and note any warning lights.",
            ]
        }
        score, notes = evaluate_actionability(report, "Medium")
        assert any("urgency language" in n for n in notes)


class TestEvaluateReport:
    def test_returns_populated_score(self):
        context = "Coolant temperature: 98 degrees (reference: 90-95)"
        report = {
            "anomaly_description": (
                "The coolant temperature reading of 98 degrees "
                "exceeds the normal 90-95 degree range."
            ),
            "possible_cause": (
                "This may indicate reduced coolant flow or a "
                "partially blocked radiator."
            ),
            "recommended_action": [
                "Check the cooling system soon for leaks or "
                "blockages.",
                "Monitor the temperature gauge on future drives.",
            ],
        }
        result = evaluate_report(
            report, context, "cooling_degradation", "Medium"
        )
        assert 0.0 <= result.overall_score <= 1.0
        assert result.anomaly_type == "cooling_degradation"
        assert result.risk_level == "Medium"
