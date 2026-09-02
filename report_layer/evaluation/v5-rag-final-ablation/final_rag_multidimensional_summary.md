# Multidimensional review of the regenerated reports

The 20 reports regenerated on 1 September 2026 were manually compared with
their saved Model Layer context, retrieved knowledge, Validator result and
automatic audit. A `partial` result records a material limitation in one
dimension; it does not mean that the complete report failed release. Retrieval
dimensions do not apply to the controlled baseline.

| Condition | Input faithfulness pass/partial | Retrieval relevance pass/partial | Knowledge use pass/partial | Audience pass/partial | Action safety pass/partial | Uncertainty pass/partial | Released |
|---|---:|---:|---:|---:|---:|---:|---:|
| Controlled baseline | 5/0 | N/A | N/A | 5/0 | 5/0 | 5/0 | 5/5 |
| Cause RAG | 5/0 | 4/1 | 1/4 | 3/2 | 5/0 | 5/0 | 5/5 |
| Current full RAG | 5/0 | 4/1 | 1/4 | 3/2 | 5/0 | 5/0 | 5/5 |
| Owner-safe RAG | 5/0 | 4/1 | 1/4 | 3/2 | 5/0 | 5/0 | 5/5 |

## Findings

- All 20 reports were released without fallback. They retained the upstream
  risk category and evidence boundary, and all technical work remained with a
  mechanic.
- The four issues found in the earlier manual review were removed. The final
  outputs no longer use unrelated pedal stopping conditions, unexplained MAF
  or PID terms, whole-system normal-operation claims, or strong IAT fault
  wording based only on rule evidence.
- Retrieved knowledge made possible causes and mechanic requests more
  specific. In four of the five cases, however, the displayed signals could
  not distinguish among all category-relevant causes. These cases therefore
  remain `partial` for knowledge use.
- Intake-air-temperature retrieval remains `partial` for relevance because
  all displayed temperatures are within range. The report states this
  limitation and requests professional verification, but the saved evidence
  cannot select between the retrieved circuit and connector possibilities.
- Air-intake and intake-temperature RAG explanations remain relatively dense
  for a non-technical reader, so their audience rating remains `partial` even
  though internal acronyms and provenance language were cleaned.

The review supports the current release controls and the owner/mechanic action
boundary. It does not measure mechanical accuracy or generalisation; those
claims require technician-verified faults, repair outcomes and data from more
vehicles.
