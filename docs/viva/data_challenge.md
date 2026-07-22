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

- The dataset *contains no faults at all* — every trip is a healthy car. The KIT OBD-II data is normal commuter driving, and the only labels it carries describe traffic density (Frei / Normal / Stau), not mechanical condition. Unlike a typical ML project that has at least a handful of positive examples or a labelled test set, we have zero fault instances to train on or to measure recall against. Supervised fault classification is simply off the table.
- In this domain, a signal has no *fixed "normal"* — normality is defined by context. A coolant temperature of 70 °C is healthy two minutes after a cold start but abnormal after twenty minutes of driving; the same MAF reading is normal at idle and a fault at high load. Because normal driving legitimately spans a huge range of operating conditions, any single global threshold either fires constantly (false alarms) or never fires (blind). "Abnormal" only exists relative to the physical situation the car is in.
- The raw data is low-rate, quantized, and uncontrollable. Signals are logged at 1 Hz and integer-quantized, trips are short and often end mid-warm-up (right-censored), and — unlike a lab benchmark — we cannot inject a real fault into someone's engine to generate ground truth. This makes both detection and validation fragile in ways a clean benchmark dataset never is.

## Our Solution

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- What did we build to solve this?
     Explain the key ideas simply:
     - Operating condition state machine
     - Proxy failure conditions
     - Sliding window majority voting
     Write 3-5 bullet points.
     Avoid layer names and jargon. -->

- **We give every second of data a "situation" label first.** A two-level state machine tags each row by engine thermal state (warming up vs. fully warmed up) and by how the car is being driven (idle, steady cruise, acceleration, high load). This means 77.85 % of the data is confidently identified as fully warmed-up running, and ~96 % of rows are high-confidence — so downstream checks always know the physical context.
- **We define "abnormal" relative to that situation, not globally.** Each fault check only runs inside the operating state where it is physically meaningful — overheating is only judged once the engine is warm; an air-flow under-read only at high load — and each threshold is calibrated to sit just outside the healthy range actually observed in that state. Healthy false positives are therefore essentially zero by construction, not by luck.
- **We require a condition to persist, not just flicker once.** A check only fires if the abnormal behaviour holds continuously for a set time (e.g. ≥30 s) or repeats across most of the recent events (e.g. 3 of the last 4). This is what defeats the single-sample noise you get from 1 Hz quantized signals. (This is the real mechanism behind the "majority voting" note in the template.)
- **When we aren't sure, we abstain instead of guessing.** If required signals are missing or the car is outside the range we calibrated on, the check returns "not evaluable" rather than a normal/abnormal verdict — so a label is only emitted when it can be trusted.
- **Every label is anchored to a real diagnostic code.** Each proxy maps to an established OBD-II trouble code (slow warm-up P0128, overheating P0217, MAF under-read P0101, and so on), so the labels we generate are grounded in standard automotive fault definitions rather than invented from scratch.

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

- SAE International (2007), J2012 — standard diagnostic trouble code definitions; grounds our proxy-to-DTC mapping.
- SAE International, J1979 — OBD-II PID physical ranges (e.g. intake air temp −40…215 °C) used for range-plausibility checks.
- California Air Resources Board (2019), Title 13 CCR §1968.2 — OBD-II monitor requirements; source of the regulatory warm-up / thermostat / overheat threshold forms used as guards.
- AUTOSAR (2020), CP Release 20-11 — hierarchical state-machine design pattern.

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

1. **Visual 1 (core) — The operating-condition state machine.** A clean hierarchical flowchart: top level = thermal state (engine_off → warmup → post_warmup); second level = kinematic child state branching from any running state (idle / steady / acceleration / deceleration / high_load). This carries the whole "we label every second by situation" idea in one picture.

2. **Visual 2 — "Why one global threshold fails."** A single coolant-temperature trace over one trip. Overlay (a) a flat global threshold line that falsely trips during the warm-up ramp, versus (b) the same trace split into condition bands, where the overheating check only becomes active in the post-warmup zone and fires only there. This sells both the challenge and the solution in one before/after image.

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
