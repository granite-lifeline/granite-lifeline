# Challenge 2: Anomaly Detection Without Ground Truth

**Speaker:** Ray Wang, Lucca Zhou
**Time:** ~1.5 minutes
**Transition in:** "With clean, structured data, we could now detect anomalies — but that brought its own challenge."
**Transition out:** "We had a risk score — but a number means nothing to a car owner."

---

## Why This Challenge Is Specific to This Project

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- Why is anomaly detection harder
     when you have no verified fault
     examples to train or test against?
     What makes this different from
     standard supervised anomaly detection?
     Write 2-3 bullet points. -->

## Our Solution

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- What did we build to solve this?
     Explain simply:
     - IBM Granite TTM zero-shot forecasting
     - Residual-based scoring
     - Two-tier range mechanism
     Write 3-5 bullet points.
     Avoid jargon. -->

## Why Our Approach Is Better Than Alternatives

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- Why TTM rather than LSTM or
     random forest?
     Why zero-shot rather than training
     from scratch?
     1-2 bullet points. -->

## Evaluation

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- How do we know the anomaly
     detection works?
     - Zero-shot vs fine-tuned comparison
     - Residual scoring results
     - What we cannot verify (honest
       limitation: proxy ≠ real fault)
     Write 2-3 bullet points with
     actual numbers where possible. -->

## References

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- List papers or sources supporting
     your design decisions.
     Format: Author (Year) — one line
     description of relevance. -->

## Visuals

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- Describe what diagram or image
     you want on the slide.
     Examples:
     - "A diagram showing TTM context
       window and forecast horizon"
     - "A graph showing residual score
       vs actual signal for a
       cooling anomaly"
     If you can draft it, attach or
     describe in detail. -->

---

## BACKUP SECTION

### (For Q&A — not on main slides)

### Full Pipeline Detail

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- Describe the complete Model Layer
     pipeline in detail: input validation,
     two-tier ranges, TTM inference,
     z-score normalisation, residual
     calculation, risk scoring,
     confidence calculation.
     Be as detailed as possible. -->

### Deep Dive: TTM Architecture

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- Explain what Granite TTM is,
     how zero-shot forecasting works,
     and why the residual approach
     detects anomalies. -->

### Limitations

<!-- TODO: Ray Wang, Lucca Zhou -->
<!-- What are the honest limitations?
     Strong proxy performance does not
     guarantee real fault detection.
     What would you do differently? -->
