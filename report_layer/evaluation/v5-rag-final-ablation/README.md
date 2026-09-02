# Final-pipeline RAG ablation audit

## Reproduce the automated runs

Run both commands from the repository root with local Ollama serving
`granite4.1:8b` and the production RAG index available:

```bash
uv run python report_layer/evaluation/v5-rag-final-ablation/run_final_rag_ablation.py
uv run python report_layer/evaluation/v5-rag-final-ablation/run_owner_decision_smoke.py
```

The first command regenerates the controlled 20-report comparison. The second
regenerates one production report for each supported anomaly type. Generated
scores and heuristic counts are screening evidence; the multidimensional
manual review must be checked again whenever report text changes.

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

The subsequent production design distinguishes two action roles:

- `owner_action`: safe observation, stopping conditions and simple
  checks that need no dismantling or specialist tools;
- `technician_request`: a specific inspection that the owner should ask
  a mechanic to perform.

Technical workshop steps should not be copied or paraphrased as actions
for the owner.

## Controlled comparison design

All conditions must use the same final model, prompt templates, input
context, confidence guidance, temperature and validator. Only the stated
knowledge field should change.

| Condition | Fault knowledge | Action knowledge | Purpose |
|---|---|---|---|
| A: controlled baseline | neutral placeholder | neutral placeholder | Establish performance without retrieval |
| B: cause RAG | retrieved description and causes | neutral placeholder | Isolate the value of retrieved diagnostic knowledge |
| C: current action RAG | retrieved description and causes | current risk-filtered workshop actions | Measure the current design and expose audience-safety failures |
| D: owner-safe RAG | retrieved description and causes | actions separated into owner actions and technician requests | Test the proposed correction |

The implemented comparison covers all five current anomaly types. Saved
prompts, retrieved passages and raw outputs are retained for every condition.

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

## Final-pipeline automated run regenerated on 1 September 2026

The controlled comparison was run on one saved real-pipeline fixture for
each of the five supported anomaly types. This produced 20 reports (five
fixtures by four conditions). All reports used `granite4.1:8b`, temperature
zero, the final three prompt templates, identical certainty guidance and the
same validator/correction path. All 20 reports were released without a
fallback. The complete inputs, retrieved text, rendered prompts, reports,
validator records and evaluator outputs are retained in
`final_rag_ablation_raw.json`.

The auditable seven-dimension labels are retained separately in
`final_rag_multidimensional_review.json`, with aggregate counts in
`final_rag_multidimensional_summary.md`. The separation is deliberate:
machine-checkable release facts are not mixed with manual judgements about
relevance, audience and safety.

The legacy four-dimension evaluator produced the following means:

| Condition | Mean legacy score |
|---|---:|
| Controlled baseline | 0.860 |
| Cause-only RAG | 0.930 |
| Current full RAG | 0.930 |
| Owner-safe RAG | 0.930 |

These numbers do **not** establish a general ranking of the four conditions.
Review of the evaluator records found several lexical false positives. For example, the evaluator
treated the explained terms “mass airflow (MAF) sensor” and “intake manifold
pressure sensor (MAP sensor)” as unexplained raw fields. It also treated
“before treating it as a confirmed fault” as a confirmed-fault claim and did
not recognise “could indicate” as hedging. These rule-coverage effects account
for much of the numerical ordering. The score is therefore reported as an
output of the evaluated implementation, not as the final judgement of RAG
quality.

## Manual review against the separated measures

The regenerated 1 September outputs were reviewed case by case. All 20 kept
technical work with a mechanic, supporting the production owner/mechanic
action boundary. Retrieved knowledge improved the specificity of several
reports, but did not by itself ensure that each possible cause was strongly
connected to the current signal direction or that every term was suitable for
a non-technical reader.

The final regeneration removed the four issues found in the earlier manual
review: unrelated pedal stopping conditions, unexplained MAF or PID terms,
whole-system normal-operation claims, and strong IAT fault wording based only
on rule evidence. Neither IAT nor MAP described a future crossing into High
risk.

The remaining limitations concern the strength of the available evidence.
Several retrieved causes fit the anomaly category but cannot be distinguished
by the displayed signals, and two RAG explanations remain relatively dense for
the intended reader. Full labels and evidence are in
`final_rag_multidimensional_review.json`; aggregate counts and interpretation
are in `final_rag_multidimensional_summary.md`. These findings assess report
behaviour, not mechanical accuracy or generalisation.

## RAG redesign: decision support rather than self-repair

The intended user outcome is not for an owner to repair the vehicle alone.
The report should reduce avoidable uncertainty by explaining what the system
observed, how strongly the evidence supports a concern, and how soon qualified
inspection should be arranged. The owner needs a small set of safe decisions:
continue normal observation, book routine service, arrange prompt inspection,
or stop driving and seek assistance.

The design separates knowledge into two governed roles:

1. `diagnostic_evidence`: component purpose, signal interpretation, plausible
   causes and what evidence a technician could use to distinguish them;
2. `action_policy`: owner observations, driving restrictions, service urgency,
   stop-driving conditions and technician requests.

Every action passage should carry metadata including `actor` (`owner` or
`technician`), `urgency`, `requires_tools`, `requires_disassembly`,
`anomaly_type`, `risk_level` and `source`. Retrieval for the owner-facing
section must exclude tool-dependent and dismantling procedures. Those passages
may still be retrieved for a separate `what_to_tell_the_mechanic` field, but
must be rewritten as a request rather than an instruction to the owner.

The generated contract should explicitly separate:

- `what_happened`;
- `what_it_may_mean`;
- `what_the_owner_should_do_now`;
- `when_to_book_service`;
- `when_to_stop_driving`;
- `what_to_tell_the_mechanic`.

Before generation, a consistency gate should compare current risk, threshold
probability, confidence and abnormal signals. Contradictory combinations must
not enter the ordinary report path. After retrieval, a relevance gate should
reject passages that do not match the anomaly pattern and risk context rather
than asking the LLM to ignore a long irrelevant list. If no suitable passage
remains, the report should disclose that the available evidence is
insufficient instead of filling the gap from general model knowledge.

Evaluation of this redesign should measure whether owners correctly identify
the current condition, uncertainty, service urgency and stop-driving trigger.
Reduced anxiety is desirable only when it is calibrated to the evidence; a
reassuring Low-risk report and an appropriately urgent High-risk report can
both be successful. Technician review is still required to judge whether the
requested workshop checks are diagnostically appropriate.

## Backward-compatible implementation and verification

The redesign was implemented without changing the Dashboard contract. The
Report Layer still returns `anomaly_description`, `possible_cause` and the
`recommended_action` list. Layer 3 now requires exactly four ordered items:
`Now`, `Service timing`, `Stop driving and seek help if`, and
`Tell the mechanic`.

Retrieved workshop actions are retained only as technician evidence. A
deterministic policy supplies component-specific owner observations, service
urgency and stopping conditions. Replacement-only instructions, code-clearing
steps and vehicle-specific turbo procedures without matching vehicle context
are removed before the prompt. Low/falling Low-risk cooling inputs also reject
the retrieved overheating fault list. High-risk inputs no longer expose a
probability of later crossing the threshold they already occupy.

The final smoke test generated one production report for each of the five
supported anomaly types. All five reports were released, contained all four
action roles, and contained no detected technical instruction addressed to the
owner. The raw reports are stored in `owner_decision_smoke_raw.json` and the
summary in `owner_decision_smoke_results.md`. The full automated suite completed
with 758 tests passed, 19 environment-dependent tests skipped and one
model-download test deselected. Because the three generated report fields and
the wider `ReportLayerOutput` schema were preserved, no Dashboard or
viva-slide migration was required.
