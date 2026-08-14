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

## Final-pipeline run completed on 14 August 2026

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
| Controlled baseline | 0.950 |
| Cause-only RAG | 0.915 |
| Current full RAG | 0.915 |
| Owner-safe RAG | 0.930 |

These numbers do **not** establish that the baseline was better. Direct
inspection found several lexical false positives. For example, the evaluator
treated the explained terms “mass airflow (MAF) sensor” and “intake manifold
pressure sensor (MAP sensor)” as unexplained raw fields. It also treated
“before treating it as a confirmed fault” as a confirmed-fault claim and did
not recognise “could indicate” as hedging. These rule-coverage effects account
for much of the numerical ordering. The score is therefore reported as an
output of the evaluated implementation, not as the final judgement of RAG
quality.

## Manual review against the separated measures

| Measure | Finding |
|---|---|
| Input faithfulness | Values and risk fields were generally preserved in all conditions. However, both High-risk fixtures also carried a 0.31% probability of *crossing* the High-risk threshold. None of the four conditions explicitly resolved this upstream inconsistency. |
| Retrieval relevance | MAF, accelerator-pedal, IAT and MAP fault knowledge was relevant to the named component. Cooling retrieval was over-broad: it mixed the low-temperature fixture with a long list dominated by overheating and workshop fault possibilities. |
| Knowledge utilisation | Cause RAG added component function and source-backed candidate causes. Current full RAG used retrieved action material most clearly for cooling, MAF and accelerator-pedal cases, but appropriately ignored the IAT knowledge base's unsupported replacement-only actions. |
| Audience suitability | Cause knowledge often improved explanation, although it also introduced acronyms. Current action RAG sometimes addressed workshop steps directly to the owner, including scan-tool use and connector or harness inspection. |
| Action safety | No output instructed dismantling in this run. Nevertheless, the current condition blurred owner and technician roles in several reports. The owner-safe condition consistently redirected technical diagnosis to a qualified mechanic while retaining observation and stopping advice for the owner. |
| Uncertainty handling | The reports generally avoided presenting a predicted mechanical cause as certain. The main unresolved issue was the contradiction between a current High risk and a low probability of later crossing the High-risk threshold. |
| Release outcome | 20/20 reports reached release without fallback. This demonstrates pipeline completion for these fixtures, not diagnostic validity or deployment readiness. |

The most defensible conclusion is therefore conditional rather than a single
ranking. Retrieved **cause knowledge** improved traceability and component-
specific explanation in several cases, but the current retrieval corpus was
not uniformly relevant. Retrieved **action knowledge** could make advice more
specific, but workshop procedures require an explicit audience transformation.
The owner-safe condition corrected that role boundary, especially in the IAT
case, but did not solve irrelevant retrieval or contradictory upstream risk
fields. The next design change should therefore combine risk-aware retrieval,
separate `owner_action` and `technician_request` fields, and a validator rule
that stops or clearly discloses inconsistent risk statements.

## Proposed RAG redesign: decision support rather than self-repair

The intended user outcome is not for an owner to repair the vehicle alone.
The report should reduce avoidable uncertainty by explaining what the system
observed, how strongly the evidence supports a concern, and how soon qualified
inspection should be arranged. The owner needs a small set of safe decisions:
continue normal observation, book routine service, arrange prompt inspection,
or stop driving and seek assistance.

The next RAG design should therefore use two separately governed knowledge
collections:

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
