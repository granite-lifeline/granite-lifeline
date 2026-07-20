# Challenge 3: Grounded Language Generation

**Speaker:** Charlotte Yu, Jintong He
**Time:** ~2 minutes
**Transition in:** "We had a risk score — but a number means nothing to a car owner."
**Transition out:** "So how do we know our reports are actually accurate?"

---

## Why This Challenge Is Specific to This Project

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Why is generating grounded diagnostic
     reports harder than general LLM text
     generation?
     - LLMs hallucinate
     - No technical expert to verify output
     - Reports must be safe and actionable
       for non-technical users
     Write 2-3 bullet points. -->

## Our Solution

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- What did we build to solve this?
     Explain simply:
     - Why we chose Granite 4.1 8B
       (4-model empirical evaluation)
     - RAG pipeline with ChromaDB
     - Three-layer prompt chain
     - Certainty guidance from
       prediction confidence
     Write 3-5 bullet points. -->

## Why Our Approach Is Better Than Alternatives

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Why RAG rather than fine-tuning
     the LLM on automotive knowledge?
     Why three-layer prompt chain rather
     than single-shot generation?
     1-2 bullet points. -->

## Evaluation

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- How do we know our reports are
     accurate without a technical expert?
     - RAG vs baseline comparison results
       (factual grounding, readability,
        hedging appropriateness,
        actionability scores)
     - Four-way retrieval comparison
     - Prompt chain validator results
     - Honest limitation: automated
       evaluation cannot fully replace
       domain expert review
     Write 3-5 bullet points with
     actual scores where possible. -->

## References

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- List papers supporting design decisions.
     At minimum:
     - Huang et al. 2025 (hallucination)
     - Qi et al. 2025 (LLMs for fault diagnosis)
     - ADR 302 (model selection)
     - ADR 303 (RAG architecture)
     Format: Author (Year) — one line
     description of relevance. -->

## Visuals

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Describe what diagram or image
     you want on the slide.
     Examples:
     - "RAG pipeline diagram showing
       ChromaDB → context injection →
       three-layer prompt chain → report"
     - "Side-by-side comparison table:
       baseline report vs RAG report
       with quality scores"
     If you can draft it, attach or
     describe in detail. -->

---

## BACKUP SECTION

### (For Q&A — not on main slides)

### Full Pipeline Detail

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Describe the complete Report Layer
     pipeline: context injection,
     signal name mapping, KNOWN_CORRELATIONS,
     failure projection, RAG retrieval,
     certainty guidance, three-layer
     prompt chain, JSON validation.
     Be as detailed as possible. -->

### Deep Dive: RAG vs Baseline Results

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Full evaluation results table.
     All four dimensions across all
     three scenarios. Four-way retrieval
     comparison results. Explanation of
     why section-level chunking was
     retained. -->

### Limitations

<!-- TODO: Charlotte Yu, Jintong He -->
<!-- Honest limitations:
     - Automated evaluation cannot
       replace domain expert review
     - Proxy labels affect report quality
     - What would you do differently? -->
