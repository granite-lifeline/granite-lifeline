# Perturbation Regression Results — All 5 Anomaly Types

Extends run_perturbation_test.py (cooling_degradation only, 3 hand-written scenarios) to all 5 current anomaly types, using the real generated reports from qa_cross_validation/cross_validation_raw.json. Run after the pseudo-negation fix (PSEUDO_NEGATIONS).

## cooling_degradation (Low)

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| synonym | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| punctuation | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## air_intake_maf_anomaly (Low)

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 0.70 | 1.00 | 0.70 | 0.85 |
| synonym | 1.00 | 0.70 | 0.60 | 0.70 | 0.75 |
| punctuation | 1.00 | 0.70 | 1.00 | 0.70 | 0.85 |
| negation_rephrase | 1.00 | 0.70 | 1.00 | 0.70 | 0.85 |

## accelerator_pedal_sensor (Medium)

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| synonym | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| punctuation | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## intake_air_temperature_sensor_fault (High)

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 1.00 | 1.00 | 0.70 | 0.93 |
| synonym | 1.00 | 1.00 | 1.00 | 0.70 | 0.93 |
| punctuation | 1.00 | 1.00 | 1.00 | 0.70 | 0.93 |
| negation_rephrase | 1.00 | 1.00 | 1.00 | 0.70 | 0.93 |

## map_load_signal_plausibility_fault (High)

| Variant | factual_grounding | readability | hedging_appropriateness | actionability | overall_score |
|---|---|---|---|---|---|
| original | 1.00 | 0.70 | 1.00 | 1.00 | 0.93 |
| synonym | 1.00 | 0.70 | 1.00 | 1.00 | 0.93 |
| punctuation | 1.00 | 0.70 | 1.00 | 1.00 | 0.93 |
| negation_rephrase | 1.00 | 0.70 | 1.00 | 1.00 | 0.93 |

## Summary

Consistency rate across all anomaly-type x variant x dimension checks: **73/75 (97.3%)**.

Combined with the original 3-scenario cooling_degradation run (41/45, 91.1%), this covers all 5 anomaly types rather than one, and uses reports actually produced by the live pipeline (generate_report(), with the validator wired in) rather than only hand-authored scenario text.
