# Multidimensional review data

The table below aggregates the 20 auditable case labels in
`final_rag_multidimensional_review.json`. Counts are reported instead of a
weighted total because the dimensions answer different questions. Retrieval
columns are not applicable to the controlled baseline.

| Condition | Input faithfulness P/F | Retrieval relevance P/Partial | Knowledge utilisation P/Partial | Audience P/Partial | Action safety P/Partial | Uncertainty P/F | Released |
|---|---:|---:|---:|---:|---:|---:|---:|
| Controlled baseline | 3/2 | N/A | N/A | 5/0 | 5/0 | 3/2 | 5/5 |
| Cause RAG | 3/2 | 4/1 | 4/1 | 4/1 | 4/1 | 3/2 | 5/5 |
| Current full RAG | 3/2 | 2/3 | 3/2 | 1/4 | 1/4 | 3/2 | 5/5 |
| Owner-safe RAG | 3/2 | 2/3 | 3/2 | 5/0 | 5/0 | 3/2 | 5/5 |

## What this data shows

- Cause RAG achieved relevant retrieval and useful knowledge use in four of
  five cases. Cooling was partial because its retrieved fault list poorly
  matched the Low-risk, lower-temperature pattern.
- Adding current workshop actions reduced audience suitability and action-role
  safety to one clear pass out of five. This does not mean four reports were
  immediately dangerous; it means technical work was addressed directly to
  the assumed non-technical owner.
- The owner-safe transformation restored five of five audience and action-
  safety passes, while leaving retrieval relevance unchanged. Prompt-level
  role transformation can therefore control who receives an action, but cannot
  make an irrelevant passage relevant.
- All conditions failed relationship-level input faithfulness and uncertainty
  handling for the same two High-risk fixtures. This shared failure came from
  an unresolved combination of current High risk and a low probability of
  later crossing the High-risk threshold, rather than from retrieval alone.
- All 20 reports were released, demonstrating that the present validator does
  not detect the relationship-level contradiction.

These are manual, evidence-linked labels. They should not be presented as an
automatically validated diagnostic accuracy score or averaged into one number.
