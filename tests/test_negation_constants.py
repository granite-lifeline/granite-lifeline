"""
Tests for report_layer.negation_constants — the shared data extracted
from prompt_chain_validator.py and report_quality_evaluator.py after
their independently-maintained copies of these constants had already
drifted once (see the "rpm" raw-field-name bug found via
qa_cross_validation, in a related but separate list).
"""

from report_layer.evaluation.report_quality_evaluator import (
    _find_unnegated_phrases as evaluator_find_unnegated_phrases,
)
from report_layer.negation_constants import (
    CLAUSE_BOUNDARY,
    NEGATION_WORDS,
    PSEUDO_NEGATIONS,
)
from report_layer.pipeline.prompt_chain_validator import (
    _find_unnegated_phrases as validator_find_unnegated_phrases,
)


def test_negation_words_is_nonempty_set():
    assert isinstance(NEGATION_WORDS, set)
    assert "no" in NEGATION_WORDS
    assert "not" in NEGATION_WORDS


def test_pseudo_negations_is_nonempty_tuple():
    assert isinstance(PSEUDO_NEGATIONS, tuple)
    assert "no doubt" in PSEUDO_NEGATIONS


def test_clause_boundary_matches_common_boundaries():
    assert CLAUSE_BOUNDARY.search("a, b")
    assert CLAUSE_BOUNDARY.search("a. b")
    assert CLAUSE_BOUNDARY.search("a but b")
    assert not CLAUSE_BOUNDARY.search("a b")


def test_both_modules_share_the_same_constant_objects():
    """
    Both modules import from report_layer.negation_constants rather
    than each defining their own copy — this asserts they're actually
    using the same objects, not just equal-by-value copies that could
    silently diverge again the way the old duplicated raw_fields list
    did.
    """
    import report_layer.evaluation.report_quality_evaluator as evaluator
    import report_layer.pipeline.prompt_chain_validator as validator

    assert evaluator.NEGATION_WORDS is validator.NEGATION_WORDS
    assert evaluator.PSEUDO_NEGATIONS is validator.PSEUDO_NEGATIONS
    assert evaluator.CLAUSE_BOUNDARY is validator.CLAUSE_BOUNDARY


def test_both_modules_agree_on_a_pseudo_negation_case():
    text = "There is no doubt this is confirmed."
    assert (
        validator_find_unnegated_phrases(text, ["confirmed"])
        == evaluator_find_unnegated_phrases(text, ["confirmed"])
        == ["confirmed"]
    )


def test_words_containing_negation_substrings_do_not_hide_claims():
    cases = (
        "Normal readings confirmed the fault.",
        "The notable evidence confirmed the fault.",
    )
    for text in cases:
        expected = ["confirmed"]
        assert validator_find_unnegated_phrases(
            text, ["confirmed"]
        ) == expected
        assert evaluator_find_unnegated_phrases(
            text, ["confirmed"]
        ) == expected


def test_contracted_negation_suppresses_the_claim():
    text = "The fault isn't confirmed by the available readings."
    assert validator_find_unnegated_phrases(text, ["confirmed"]) == []
    assert evaluator_find_unnegated_phrases(text, ["confirmed"]) == []
