# ADR 304: Negation Scope Detection Design for Report Quality Checks

## Status

Accepted

## Date

2026-08-07

## Context

Two independent quality mechanisms — `prompt_chain_validator.py` (runs per generated report, after each of the three prompt-chain layers) and `report_quality_evaluator.py` (runs offline, scoring RAG vs baseline on a fixed evaluation set) — both need to detect two related things in generated report text:

1. **Unhedged assertion language** ("confirmed", "is definitely", "has failed", "is broken") that should not appear in a report about a *predicted* risk, since the Report Layer's own prompts (`layer1_description.txt`, `layer2_cause.txt`) explicitly forbid claiming a confirmed mechanical fault.
2. **Hedging language** ("may indicate", "could suggest", etc.) that a well-behaved report should contain when discussing a possible cause.

Both checks originally used a bare substring/word match against a fixed phrase list. This is unreliable in one specific, common way: negation. "There is no confirmed fault yet" and "This is not confirmed" both contain the literal word "confirmed", but both are *correctly hedged* text — the opposite of what a bare match reports. This exact case ("no confirmed fault yet") is documented as a known limitation in `docs/viva/report_challenge.md`'s Limitations section and was independently found affecting real generated output during the report-layer hardening work on this branch.

## Decision

Negation detection is implemented as `_find_unnegated_phrases(text, phrases)`, duplicated with identical logic in both `prompt_chain_validator.py` and `report_quality_evaluator.py`, but sharing its underlying constants from a single module, `report_layer/negation_constants.py`:

```python
NEGATION_WORDS = {"no", "not", "never", "without", "n't", "unconfirmed"}
CLAUSE_BOUNDARY = re.compile(r"[.,;:]|\bbut\b|\bhowever\b|\balthough\b")
PSEUDO_NEGATIONS = ("no doubt", "without doubt", "without question", "no question")
```

For a candidate phrase match (e.g. "confirmed"), the function:

1. Masks out any `PSEUDO_NEGATIONS` phrase from the text first.
2. Finds the phrase via word-boundary regex match (so "confirmed" inside "unconfirmed" is never matched at all).
3. Scans backward from the match to the nearest preceding clause boundary (`.`, `,`, `;`, `:`, "but", "however", "although") — not a fixed word count.
4. If any word in that clause span is a `NEGATION_WORDS` member, the match is treated as negated and excluded from the result.

`prompt_chain_validator.py` and `report_quality_evaluator.py` each keep their own copy of the function body and their own phrase lists (`confirmed_phrases`, `hedging_phrases`, `fault_claims`, `raw_fields`, etc.) — only the three constants above are shared.

## Rationale

### Why not a fixed word-count window?

The first implementation used a fixed 3-word window before the matched phrase. Testing against real generated text immediately falsified this: "No specific fault has been confirmed yet" places four words (`specific fault has been`) between "no" and "confirmed", outside a 3-word window. Widening the window to a literature-precedented value (NegEx's own tuned scope is a 0–5 token window; Chapman et al., 2001) would have caught this specific case, but any fixed word count is a magic number that the next real sentence can just as easily exceed. Clause-scoped detection removes the need to pick a number at all: it scans back exactly to where the current clause starts, however many words that is.

### Why mask pseudo-negations?

Once clause-scoped detection was in place, a further real case surfaced: "There is no doubt this fault is confirmed" contains the negation trigger "no", but "no doubt" *intensifies* certainty rather than negating it — the opposite problem from the one this feature exists to solve. This is the same phenomenon NegEx's pseudo-negation phrase list addresses for clinical-note negation (phrases that look like negation triggers but aren't), adapted here for certainty/hedging language rather than clinical finding-presence. The `PSEUDO_NEGATIONS` list is deliberately small and specific (four phrases) rather than an attempt at an exhaustive list; it is data, not an algorithm, and can grow the same way `NEGATION_WORDS` can.

### Why share the constants but not the function?

`prompt_chain_validator.py` is production pipeline code, called from `report_generator.generate_report()`. `report_quality_evaluator.py` is a standalone offline evaluation script with no dependency on the pipeline package. Keeping `_find_unnegated_phrases()` itself as two independent implementations means either module can be modified, tested, or deployed without a coupling dependency on the other.

However, this "independently maintained" pattern already produced one real bug in a *different, structurally identical* list pair: `report_quality_evaluator.py`'s `raw_fields` list included `"rpm"`, while `prompt_chain_validator.py`'s equivalent list never did — and the discrepancy was only found when a cross-validation run happened to score the same real generated report with both mechanisms and got different verdicts. `NEGATION_WORDS`, `CLAUSE_BOUNDARY`, and `PSEUDO_NEGATIONS` were, at the time of writing, byte-identical between the two files — exactly the situation that produced the `raw_fields` drift. Sharing this specific data removes that drift risk for negation detection without forcing the two modules' other, already-divergent phrase lists (`confirmed_phrases`, `hedging_phrases`, `raw_fields`) to be merged, which would be a separate and larger design decision.

## Implementation

- `report_layer/negation_constants.py` — shared constants.
- `report_layer/pipeline/prompt_chain_validator.py::_find_unnegated_phrases()` — used in `validate_layer1()` and `validate_layer2()`'s confirmed-phrase and hedging checks.
- `report_layer/evaluation/report_quality_evaluator.py::_find_unnegated_phrases()` — used in `evaluate_hedging_appropriateness()`'s confirmed-phrase, fault-claim, and hedging checks.
- `tests/test_negation_constants.py`, `tests/test_prompt_chain_validator.py`, `tests/test_report_quality_evaluator.py` — regression coverage, including a test asserting both modules import the same constant objects (not equal-by-value copies).
- `report_layer/evaluation/perturbation_regression/` — the regression methodology (synonym, punctuation, and negation-rephrase text variants scored before/after each fix) that found the window-size and pseudo-negation gaps in the first place, and that continues to guard against regressions.

## Consequences

### Positive

- Negated hedging language ("not confirmed", "no ... confirmed yet") is no longer misread as an unhedged claim, in either the production validator or the offline evaluator.
- Detection scope is not sensitive to sentence length or exact word count.
- A known false-positive class (pseudo-negation, "no doubt") is handled without weakening detection of genuine negation elsewhere.
- The shared-constants module removes one specific, previously-demonstrated class of cross-module drift, without forcing a larger unification of the two modules' other phrase lists.

### Negative

- `_find_unnegated_phrases()` itself remains duplicated logic in two files; a change to the detection *algorithm* (as opposed to its constants) must still be made twice and kept in sync manually.
- `PSEUDO_NEGATIONS` is a short, manually curated list, not derived from any corpus or algorithm — it will miss pseudo-negation phrases not yet observed in real generated text, the same bounded-coverage tradeoff already accepted for `confirmed_phrases`/`hedging_phrases`.
- Clause-boundary scanning uses a fixed set of boundary markers (`.`, `,`, `;`, `:`, "but", "however", "although"); a negation separated from its target by a different construction (e.g. a relative clause with no punctuation) would not be caught by this design either.

## Related Decisions

- GL-140: Automated report quality evaluator (`report_quality_evaluator.py`)
- GL-148: Prompt chain quality validator (`prompt_chain_validator.py`)

## References

- Chapman, W. W., Bridewell, W., Hanbury, P., Cooper, G. F., & Buchanan, B. G. (2001). *A Simple Algorithm for Identifying Negated Findings and Diseases in Discharge Summaries.* Journal of Biomedical Informatics — source of the pseudo-negation phrase list concept and the empirically-tuned negation scope window this design was informed by (adapted, not copied verbatim: this design uses clause-scoped rather than fixed-window detection).
- `docs/viva/report_challenge.md` — documents the "no confirmed fault yet" false positive as a known limitation prior to this fix.
