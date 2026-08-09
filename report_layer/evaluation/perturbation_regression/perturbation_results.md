# Perturbation Regression Results

Consistency of report_quality_evaluator.py's four dimension scores across synonym, punctuation, and negation-rephrase variants of the same three real RAG-generated reports (scenario_comparison_rag.md). Run after the negation-aware fix to evaluate_hedging_appropriateness().

## typical_cooling_stress

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| synonym | 1.00 | 1.00 | 0.60 | 1.00 | 0.90 |
| punctuation | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## atypical_cooling_stress

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| synonym | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| punctuation | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## contradictory_cooling_stress

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| synonym | 1.00 | 1.00 | 0.60 | 1.00 | 0.90 |
| punctuation | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Summary

Consistency rate across all scenario x variant x dimension checks: **41/45 (91.1%)**.

The negation_rephrase variants specifically exercise the negation-aware fix in evaluate_hedging_appropriateness(): each one rewrites a hedged sentence to explicitly use negated wording ('no ... confirmed', 'unconfirmed') instead of 'may indicate' style hedging, while preserving the same claim. Before the fix, these would have been penalised by the bare 'confirmed' substring match; after the fix, hedging_appropriateness should be unaffected by this rewrite.
