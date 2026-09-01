"""
Tests for report_layer.pipeline.prompt_chain_validator.

This module previously had no dedicated test coverage — only the
if __name__ == "__main__" demo block in the module itself. These
tests focus on the negation-aware confirmed-language check, since a
bare substring match previously flagged correctly-hedged text such as
"no confirmed fault yet" as an unhedged claim, and cover the other
existing checks that had no regression protection.
"""

from report_layer.pipeline.prompt_chain_validator import (
    _find_unnegated_phrases,
    validate_chain,
    validate_layer1,
    validate_layer2,
    validate_layer3,
)


GOOD_LAYER1 = (
    "The engine cooling system is showing signs of stress. The "
    "coolant temperature has been running higher than normal, "
    "reaching 105 degrees when the typical range is 85 to 95 "
    "degrees. This suggests the cooling system may not be operating "
    "at full efficiency."
)
GOOD_LAYER2 = (
    "This pattern could suggest a partially blocked radiator or a "
    "failing thermostat. The elevated temperatures may indicate that "
    "coolant flow is restricted, preventing proper heat dissipation "
    "from the engine."
)
GOOD_LAYER3 = [
    "Now: Watch the temperature gauge and avoid placing unusual load on "
    "the vehicle while arranging an inspection.",
    "Service timing: Arrange a prompt professional cooling-system "
    "inspection.",
    "Stop driving and seek help if: A red temperature warning appears, "
    "the engine overheats, or the vehicle loses power.",
    "Tell the mechanic: Ask them to inspect the radiator, thermostat and "
    "coolant flow using appropriate diagnostic equipment.",
]


class TestFindUnnegatedPhrases:
    def test_bare_phrase_is_a_hit(self):
        assert _find_unnegated_phrases(
            "The fault is confirmed.", ["confirmed"]
        ) == ["confirmed"]

    def test_negated_phrase_is_not_a_hit(self):
        assert _find_unnegated_phrases(
            "There is no confirmed fault yet.", ["confirmed"]
        ) == []

    def test_not_confirmed_is_not_a_hit(self):
        assert _find_unnegated_phrases(
            "This is not confirmed as a mechanical failure.",
            ["confirmed"],
        ) == []

    def test_phrase_embedded_in_larger_word_is_not_matched(self):
        # "unconfirmed" should not match "confirmed" at all — this is
        # a word-boundary match, not a substring match.
        assert _find_unnegated_phrases(
            "This remains unconfirmed for now.", ["confirmed"]
        ) == []

    def test_one_negated_and_one_bare_occurrence_still_hits(self):
        text = "It is not confirmed here, but later it is confirmed."
        assert _find_unnegated_phrases(text, ["confirmed"]) == [
            "confirmed"
        ]

    def test_negation_in_a_different_sentence_does_not_suppress(self):
        # The "No" belongs to an earlier, separate sentence (clause
        # boundary at the period), so it must not be treated as
        # negating "confirmed" in the following sentence.
        text = (
            "No, that reading is unrelated. The thermostat fault is "
            "confirmed by three separate diagnostic checks today."
        )
        assert _find_unnegated_phrases(text, ["confirmed"]) == [
            "confirmed"
        ]

    def test_negation_several_words_before_phrase_still_suppresses(self):
        # Real sentences often put several words between the negation
        # and the phrase — a fixed small word-count window would miss
        # this; clause-scoped negation should not.
        text = "No specific fault has been confirmed yet."
        assert _find_unnegated_phrases(text, ["confirmed"]) == []

    def test_no_doubt_is_not_treated_as_negation(self):
        # "no doubt" contains the negation trigger "no" but actually
        # intensifies certainty rather than negating it — a
        # pseudo-negation, analogous to NegEx's pseudo-negation phrase
        # list for clinical negation detection.
        text = (
            "There is no doubt this fault is confirmed by the "
            "diagnostic scan."
        )
        assert _find_unnegated_phrases(text, ["confirmed"]) == [
            "confirmed"
        ]


class TestValidateLayer1:
    def test_good_output_has_no_confirmed_language_warning(self):
        result = validate_layer1(GOOD_LAYER1)
        assert not any(
            "confirmed fault language" in w for w in result.warnings
        )

    def test_below_threshold_score_is_not_passed(self):
        result = validate_layer1(
            "The cooling system has failed and coolant_temp is high."
        )

        assert result.score < 0.8
        assert result.passed is False

    def test_threshold_score_is_passed(self):
        text = " ".join(["reading"] * 19 + ["coolant_temp"])

        result = validate_layer1(text)

        assert result.score == 0.8
        assert result.passed is True

    def test_negated_confirmed_language_is_not_flagged(self):
        text = (
            "The cooling system pattern is not confirmed as a fault, "
            "but the coolant temperature reading exceeds the normal "
            "range and should be checked soon by a mechanic to rule "
            "out thermostat or radiator issues during the next "
            "scheduled service visit."
        )
        result = validate_layer1(text)
        assert not any(
            "confirmed fault language" in w for w in result.warnings
        )

    def test_unhedged_confirmed_language_is_still_flagged(self):
        text = (
            "The coolant temperature reading confirmed the "
            "thermostat has failed completely and the vehicle cannot "
            "be driven under any circumstances at all please stop "
            "now immediately today."
        )
        result = validate_layer1(text)
        assert any(
            "confirmed fault language" in w for w in result.warnings
        )

    def test_empty_output_fails(self):
        result = validate_layer1("")
        assert result.passed is False
        assert result.score == 0.0

    def test_unexplained_raw_field_name_is_flagged(self):
        result = validate_layer1(
            "coolant_temp is high right now during this drive cycle "
            "and should be watched over the next several trips before "
            "any conclusions are drawn about the cause."
        )
        assert any("coolant_temp" in w for w in result.warnings)

    def test_explained_maf_and_map_acronyms_are_not_flagged(self):
        text = (
            "The mass airflow (MAF) sensor and manifold pressure (MAP) "
            "sensor readings are being compared with their expected "
            "ranges. This relationship helps show whether the current "
            "air-intake measurements agree, but it does not confirm a "
            "mechanical fault and should be checked with further evidence."
        )
        result = validate_layer1(text)
        assert not any(
            "unexplained raw field name" in warning
            for warning in result.warnings
        )

    def test_map_inside_mapping_is_not_treated_as_raw_field(self):
        text = (
            "The current signal mapping compares the air-intake readings "
            "with the expected operating pattern. The relationship does "
            "not confirm a mechanical fault, but it provides useful "
            "evidence for a professional inspection if the pattern "
            "continues over later trips."
        )
        result = validate_layer1(text)
        assert not any("map" in warning for warning in result.warnings)

    def test_short_output_is_flagged(self):
        result = validate_layer1("Coolant is warm.")
        assert any("too short" in w for w in result.warnings)

    def test_long_output_is_flagged(self):
        text = " ".join(["clear"] * 61)
        result = validate_layer1(text)
        assert any("too long" in w for w in result.warnings)

    def test_machine_precision_and_metric_repetition_are_flagged(self):
        text = (
            "The cooling system is High risk. Coolant is 84.0 degrees "
            "against a 90.0 to 95.0 range and rises at 5.5069 degrees per "
            "minute against a 0.0 to 2.0 reference, so it needs attention."
        )
        result = validate_layer1(text)
        assert any("numerical precision" in w for w in result.warnings)
        assert any("too many measurements" in w for w in result.warnings)

    def test_risk_score_restatement_is_flagged(self):
        text = (
            "The mass airflow sensor has a Medium risk category. The 85% "
            "risk score is an internal severity measure, while the current "
            "airflow comparison should be checked soon by a professional."
        )
        result = validate_layer1(text)
        assert any("risk score" in w for w in result.warnings)

    def test_parenthesised_percentage_after_risk_is_blocked(self):
        text = (
            "The mass airflow sensor shows medium risk (85%) because its "
            "internal comparison is unusual. This pattern should be checked "
            "soon by a professional, although no fault is confirmed."
        )
        result = validate_layer1(text)
        assert result.score < 0.8
        assert any("risk score" in w for w in result.warnings)


class TestValidateLayer2:
    def test_negated_confirmed_language_is_not_flagged(self):
        text = (
            "There is no confirmed fault yet, but the pattern may "
            "indicate early signs of thermostat wear or a partially "
            "blocked radiator, and could suggest reduced coolant flow "
            "under load."
        )
        result = validate_layer2(text, GOOD_LAYER1)
        assert not any(
            "confirmed fault language" in w for w in result.warnings
        )

    def test_unhedged_confirmed_language_is_still_flagged(self):
        result = validate_layer2(
            "The thermostat is confirmed broken beyond any doubt.",
            GOOD_LAYER1,
        )
        assert any(
            "confirmed fault language" in w for w in result.warnings
        )

    def test_negated_certainty_counts_as_hedging(self):
        text = (
            "No specific fault has been confirmed yet, but the "
            "elevated coolant temperature is consistent with the "
            "cooling system not effectively removing heat from the "
            "engine during normal driving conditions."
        )
        result = validate_layer2(text, GOOD_LAYER1)
        assert not any("hedging" in w.lower() for w in result.warnings)

    def test_missing_hedging_is_flagged(self):
        result = validate_layer2(
            "The radiator is clogged and the thermostat is stuck, "
            "causing the engine to run hot during normal driving "
            "conditions on the motorway.",
            GOOD_LAYER1,
        )
        assert any("hedging" in w.lower() for w in result.warnings)

    def test_possible_explanation_counts_as_hedging(self):
        # layer2_cause.txt's own "Good example" blocks open with this
        # exact phrasing in five different scenarios — real generated
        # output using it was previously scored as having no hedging.
        result = validate_layer2(
            "Possible explanations include light dust or oil on the "
            "mass airflow sensor surface, a slightly loose connector, "
            "or normal variation during driving.",
            GOOD_LAYER1,
        )
        assert not any("hedging" in w.lower() for w in result.warnings)

    def test_overlong_cause_is_flagged(self):
        text = "This may indicate " + " ".join(["detail"] * 130)
        result = validate_layer2(text, GOOD_LAYER1)
        assert any("too long" in w for w in result.warnings)


class TestValidateLayer3:
    def test_good_actions_pass_without_warnings(self):
        result = validate_layer3(GOOD_LAYER3, "High")
        assert result.warnings == []
        assert result.score == 1.0

    def test_too_few_actions_is_flagged(self):
        result = validate_layer3(["Check it soon."], "Medium")
        assert any("Too few actions" in w for w in result.warnings)

    def test_high_risk_without_urgency_is_flagged(self):
        result = validate_layer3(
            [
                "Check the coolant level at your convenience some "
                "time this month.",
                "Consider looking at the radiator when you get a "
                "chance eventually.",
            ],
            "High",
        )
        assert any("urgency" in w for w in result.warnings)

    def test_low_risk_with_panic_language_is_flagged(self):
        result = validate_layer3(
            [
                "Stop driving immediately, this is an emergency "
                "situation requiring urgent attention right away.",
                "Call a tow truck now before doing anything else at "
                "all today.",
            ],
            "Low",
        )
        assert any("panic language" in w for w in result.warnings)

    def test_invented_numeric_service_interval_is_flagged(self):
        actions = list(GOOD_LAYER3)
        actions[1] = (
            "Service timing: Arrange an inspection within 3 months if "
            "the pattern remains present."
        )
        result = validate_layer3(actions, "Low")
        assert any("numeric service interval" in w for w in result.warnings)

    def test_unverified_replacement_is_flagged(self):
        actions = list(GOOD_LAYER3)
        actions[3] = (
            "Tell the mechanic: Ask them to replace the sensor after "
            "reading this report."
        )
        result = validate_layer3(actions, "High")
        assert any("replacement" in w for w in result.warnings)

    def test_owner_sensor_inspection_is_flagged(self):
        actions = list(GOOD_LAYER3)
        actions[0] = (
            "Now: Inspect the sensor wiring and connector for visible "
            "damage before continuing to drive."
        )
        result = validate_layer3(actions, "Medium")
        assert any("technical component check" in w for w in result.warnings)


class TestValidateChain:
    def test_returns_three_results_in_layer_order(self):
        results = validate_chain(
            GOOD_LAYER1, GOOD_LAYER2, GOOD_LAYER3, "High"
        )
        assert [r.layer for r in results] == [1, 2, 3]

    def test_all_pass_on_good_input(self):
        results = validate_chain(
            GOOD_LAYER1, GOOD_LAYER2, GOOD_LAYER3, "High"
        )
        assert all(r.passed for r in results)

    def test_high_risk_cause_cannot_predict_crossing_high_threshold(self):
        cause = (
            "This pattern could be related to restricted coolant flow. "
            "There is a 0.31% chance of crossing into High risk within "
            "the next 10 trips."
        )

        results = validate_chain(
            GOOD_LAYER1, cause, GOOD_LAYER3, "High"
        )

        assert not results[1].passed
        assert results[1].score < 0.8
        assert any(
            "already High risk" in warning
            for warning in results[1].warnings
        )

    def test_high_risk_action_cannot_give_trips_until_high_risk(self):
        actions = list(GOOD_LAYER3)
        actions[1] = (
            "Service timing: High risk is expected around trip 4, so "
            "arrange a professional inspection before then."
        )

        results = validate_chain(
            GOOD_LAYER1, GOOD_LAYER2, actions, "High"
        )

        assert not results[2].passed
        assert results[2].score < 0.8
        assert any(
            "already High risk" in warning
            for warning in results[2].warnings
        )

    def test_medium_risk_can_describe_a_future_high_threshold(self):
        observation = (
            "The current readings show a rising cooling-system risk "
            "pattern across recent trips. If the trend continues, it "
            "may reach High risk in about four trips."
        )

        results = validate_chain(
            observation, GOOD_LAYER2, GOOD_LAYER3, "Medium"
        )

        assert not any(
            "already High risk" in warning
            for result in results
            for warning in result.warnings
        )
