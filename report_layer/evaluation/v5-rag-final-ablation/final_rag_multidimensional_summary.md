# Multidimensional review of the regenerated reports

The 20 reports regenerated on 1 September 2026 were manually compared with
their saved Model Layer context, retrieved knowledge, Validator result and
automatic audit. Counts are kept separate because the dimensions answer
different questions. A `partial` result identifies a material limitation; it
does not mean that the whole report failed release. Retrieval dimensions do
not apply to the controlled baseline.

| Condition | Input faithfulness pass/partial | Retrieval relevance pass/partial | Knowledge use pass/partial | Audience pass/partial | Action safety pass/partial | Uncertainty pass/partial | Released |
|---|---:|---:|---:|---:|---:|---:|---:|
| Controlled baseline | 3/2 | N/A | N/A | 4/1 | 5/0 | 4/1 | 5/5 |
| Cause RAG | 3/2 | 4/1 | 2/3 | 3/2 | 5/0 | 4/1 | 5/5 |
| Current full RAG | 3/2 | 4/1 | 4/1 | 3/2 | 5/0 | 4/1 | 5/5 |
| Owner-safe RAG | 3/2 | 4/1 | 3/2 | 2/3 | 5/0 | 4/1 | 5/5 |

## Findings

- All 20 reports were released and all 20 kept technical work with a mechanic.
  The owner-action rules therefore worked across the five saved cases.
- RAG improved the specificity of possible causes, but cause-only retrieval
  often produced several category-relevant possibilities without enough
  signal evidence to distinguish among them. This explains its three partial
  knowledge-use results.
- The current full condition used action knowledge effectively in four cases.
  The owner-safe condition remained safe, but safety transformation did not
  automatically improve relevance or plain language. Its Cooling output added
  an unrelated pedal-response condition, and its Air Intake output retained
  unexplained MAF and PID terminology.
- All four conditions inherited the same description for each fixture. The
  Accelerator Pedal description broadened normal listed signals into a claim
  that the system was operating normally. The IAT description used strong
  fault wording despite normal displayed signals and rule-based provenance.
  These shared issues account for the repeated partial faithfulness and
  uncertainty results.
- The High-risk projection rule worked in the regenerated reports: neither IAT
  nor MAP exposed a future crossing into High risk. The remaining IAT issue is
  the relationship between normal displayed signals, rule-based evidence and
  the strength of the generated wording.

The review supports the production action boundary and the use of retrieved
knowledge as qualified background. It also identifies remaining work on
acronym expansion, anomaly-description wording and checks that relate the
generated claim to the direction and strength of the supplied evidence. These
labels do not measure mechanical accuracy; that requires technician-verified
fault and repair cases.
