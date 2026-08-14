# Final-pipeline RAG ablation audit

## Why the July comparison cannot evaluate the final pipeline

The saved baseline and RAG reports in
`v3-rag-baseline-comparison/` were generated on 7 July 2026. The
production prompts changed again on 13 July, 20 July and 2 August, and
the evaluator's negation and phrase handling changed on 7 August.
Re-scoring the July text with the August evaluator is useful for finding
evaluator defects, but it does not measure the final Report Layer.

The comparison also changes two variables at once. The RAG condition
receives both retrieved knowledge and confidence-specific
`certainty_guidance`; the baseline receives neither retrieved knowledge
nor the same guidance. A difference in hedging therefore cannot be
attributed to retrieval alone.

Finally, the four-dimension evaluator does not directly measure the
main expected benefit of RAG. Its factual-grounding rules mainly check
whether input numbers are repeated, while its actionability rules mainly
check action count and urgency words. It does not establish whether the
retrieved knowledge is relevant, whether generated claims are supported
by that knowledge, or whether a technically specific action is safe for
an untrained vehicle owner.

## RAG design issue found during manual review

The knowledge base was derived from technical references and workshop
manuals. Some High-risk cooling actions are technician procedures, such
as removing a thermostat for a water-bath test or inspecting a removed
water pump by hand. The Layer 3 prompt says both that retrieved action
guidance should be the main source and that actions must be safe and
practical for a non-technical owner. Those instructions can conflict.

The final design should distinguish at least two action roles:

- `owner_action`: safe observation, stopping conditions and simple
  checks that need no dismantling or specialist tools;
- `technician_request`: a specific inspection that the owner should ask
  a mechanic to perform.

Technical workshop steps should not be copied or paraphrased as actions
for the owner.

## Required controlled comparison

All conditions must use the same final model, prompt templates, input
context, confidence guidance, temperature and validator. Only the stated
knowledge field should change.

| Condition | Fault knowledge | Action knowledge | Purpose |
|---|---|---|---|
| A: controlled baseline | neutral placeholder | neutral placeholder | Establish performance without retrieval |
| B: cause RAG | retrieved description and causes | neutral placeholder | Isolate the value of retrieved diagnostic knowledge |
| C: current action RAG | retrieved description and causes | current risk-filtered workshop actions | Measure the current design and expose audience-safety failures |
| D: owner-safe RAG | retrieved description and causes | actions separated into owner actions and technician requests | Test the proposed correction |

At minimum, the comparison should cover all five current anomaly types.
Where feasible, each type should include Low, Medium and High risk, plus
one inconsistent-evidence case. Saved prompts, retrieved passages and
raw outputs must be retained for every condition.

## Measures

The existing four dimensions remain useful but are insufficient. The
final comparison should report the following separately rather than
collapsing them into one score:

1. **Input faithfulness**: every sensor value, risk field and uncertainty
   statement agrees with Model Layer input.
2. **Retrieval relevance**: the retrieved passage belongs to the supplied
   anomaly type and risk level.
3. **Knowledge utilisation**: useful retrieved information appears in the
   report without unsupported additions.
4. **Audience suitability**: no raw fields or unexplained technical
   procedures are directed at the owner.
5. **Action safety**: invasive, tool-dependent or potentially hazardous
   steps are assigned to a mechanic rather than the owner.
6. **Uncertainty handling**: wording reflects confidence and explicitly
   identifies inconsistent evidence.
7. **Stability and release outcome**: repeated output, validator warnings,
   correction attempts and final release/fallback status.

Automated rules can screen these properties, but action safety and the
correct interpretation of contradictory evidence require manual review
until technician-grounded labels are available.

## Reporting rule

The July 0.93/0.95 comparison and the negation-corrected 0.97/0.95
comparison must be described as historical evaluator evidence, not as a
ranking of the final baseline and RAG pipelines. No claim that RAG is
better or worse should be made until the controlled final-pipeline
comparison above has been run.
