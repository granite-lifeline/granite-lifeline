# Challenge 1: No Fault Labels in the Data

**Speaker:** Lei Pei, Qiuting Fu
**Time:** ~1.5 minutes
**Transition in:** "The first challenge was in the data."
**Transition out:** "With clean, structured data, we could now detect anomalies — but that brought its own challenge."

---

## Why This Challenge Is Specific to This Project

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Why is the absence of fault labels
     a harder problem here than in typical
     ML projects? What makes OBD-II data
     from normal driving particularly
     difficult to work with?
     Write 2-3 bullet points. -->

## Our Solution

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- What did we build to solve this?
     Explain the key ideas simply:
     - Operating condition state machine
     - Proxy failure conditions
     - Sliding window majority voting
     Write 3-5 bullet points.
     Avoid layer names and jargon. -->

## Why Our Approach Is Better Than Alternatives

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Why not just use a simple threshold?
     Why not use a different dataset?
     1-2 bullet points. -->

## Evaluation

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- How do we know our proxy labels
     are valid?
     - Fault injection testing results
     - Operating condition statistics
       (post_warmup 77.85%,
        high-confidence 96.48%)
     - Physical plausibility checks
     Write 2-3 bullet points with
     actual numbers where possible. -->

## References

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- List any papers or sources that
     support your design decisions.
     Format: Author (Year) — one line
     description of relevance. -->

## Visuals

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Describe what diagram or image
     you want on the slide.
     Examples:
     - "A flowchart of the state machine"
     - "A before/after showing raw signal
       vs labelled anomaly window"
     If you can draft the diagram,
     attach it or describe it in detail. -->

---

## BACKUP SECTION

### (For Q&A — not on main slides)

### Full Pipeline Detail

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Describe the complete data pipeline
     in detail: cleaning, resampling,
     feature engineering, baseline design,
     proxy label generation.
     Be as detailed as possible.
     This is your reference during Q&A. -->

### Deep Dive: Proxy Label Design

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Explain the full proxy label
     methodology: condition-stratified
     thresholds, sliding window majority
     voting, fault injection validation.
     Include specific numbers and
     threshold values. -->

### Limitations

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- What are the honest limitations
     of your approach?
     What would you do differently
     with more time or data? -->
