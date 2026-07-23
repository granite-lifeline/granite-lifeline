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

1. **Ingest & clean.** Raw KIT OBD-II CSVs (81 trips) are parsed, timestamp-aligned, and resampled to a uniform *1 Hz* grid. Recording breaks longer than 3 s split the log into segment_ids; gaps ≤2 s are interpolated, duplicates keep the last value. Each signal gets a *two-level range policy*: a physical range (e.g. coolant −40…215 °C) and a tighter suspicious range (e.g. coolant −20…125 °C) — out-of-physical values are repaired/flagged, merely-suspicious values are *kept but flagged*, never deleted (deleting the unusual would delete the anomalies we're hunting). Every row carries per-signal missing / imputed / suspicious quality flags.
2. **Operating-condition labelling.** A two-level state machine tags every second by *thermal state* (engine_off → warmup → post_warmup, inferred from coolant temp + cumulative intake air + heat-soak, since the dataset has no catalyst temperature) and *kinematic state* (idle / steady / acceleration / deceleration / high-load, using 3 s-smoothed speed and the Vehicle Specific Power formula). Segment-bounded, with a 3 s minimum-duration cleanup to kill 1-second jitter. Result: *77.85 % post-warmup, 18.63 % warm-up, 3.51 % engine-off*, and near-universal high-confidence rows. This is what lets everything downstream know the physical context of each reading.
3. **Feature engineering (staged, contract-validated).** A numbered chain builds features in layers: input-contract validation → atomic per-row features → engine-start context → windowed features → calibrated features → production assembly. The production handoff to the model/rule team is a versioned set (schema v1: the cleaned raw signals + 5 operating-condition fields + 24 reusable B-class features). Thresholds/baselines are frozen in a calibration registry and applied to new data — never re-fitted on user-uploaded data.
4. **Proxy evidence & decision.** A second numbered chain turns features into labels: rule-state builder → event evidence → duration evidence → decision builder. Every executed row records a full audit contract — `proxy_id`, `sub_check_id`, `result_state` (pass / triggered / not_evaluable / pending), `decision_role` (verdict / pending_precursor / support / arbitration_evidence), `dtc_candidate_label`, `dtc_emitted`, and `decision_margin`. Only a permitted verdict row can emit a diagnostic code; support and arbitration-evidence rows never do.

### Deep Dive: Proxy Label Design

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- Explain the full proxy label
     methodology: condition-stratified
     thresholds, sliding window majority
     voting, fault injection validation.
     Include specific numbers and
     threshold values. -->

- **Condition-stratified, not global.** Each check only runs inside the operating state where it is physically meaningful, and its threshold is calibrated to sit just *outside* the healthy envelope observed **in that state**. Because the trigger lives beyond anything a healthy car does in that condition, healthy false positives are ~0 *by construction*. Worked examples:

     - **Slow warm-up (P0128).** At a cold start, assign a warm-up time budget by ambient bin (16.5–26.9 min at ≤5 °C; 8.3–18.2 min at >5 °C, from the regulatory 90 °C target minus an 11 °C form). Failing to reach 79 °C within budget *with sufficient heat input* triggers. Coverage 20/51 qualified starts (39.2 %); **0/20 healthy false positives**.
     - **Overheating (P0217).** In post-warmup, `coolant_temp ≥ 105 °C` for ≥180 s (or ≥110 °C for ≥30 s). Evaluable on 57/66 trips (86 %); healthy max was 101 °C, longest healthy ≥100 °C episode 87 s — so the threshold sits above the healthy envelope with persistence headroom.
     - **MAF under-read (P0101).** Only under `post_warmup__high_load`: airflow-vs-model residual `< −18.495 g/s` at every 1 Hz sample for ≥10 s. 52/66 trips; longest healthy run 3 s (7 s headroom).
     - **Redundant pedal disagreement (P2138).** Inside a low-motion mask, the two pedal channels must obey a fixed linear relationship; residual outside the band for ≥30 s triggers. 66/66 trips, **zero healthy triggers**.

- **Persistence beats single spikes.** A check fires only if the abnormal condition holds *continuously* for a set duration (e.g. ≥30 s), or — for the MAP step-response check (P0106) — recurs across **3 of the 4 most recent events**. *This "3-of-4" rule is the real mechanism behind the template's "majority voting" note.* It exists because 1 Hz integer-quantized signals produce isolated one-sample spikes that mean nothing physically.

- **Abstain, don't guess.** Missing signals, failed guards, or being outside the calibrated domain return **`not_evaluable`** with an explicit reason — never a normal/abnormal verdict. Short logs that end mid-warm-up are **right-censored** and marked, not counted as failures.

- **Arbitration when two sensors disagree.** A MAF-vs-MAP mismatch doesn't say *which* side is wrong, so shared "arbitration-evidence" is routed using independent witnesses: MAP-side witness normal → blame MAF (P0101); witness abnormal → blame MAP (P0106); witnesses unavailable → report an un-isolated fault (P006A) rather than guessing.

- **Everything maps to a real OBD-II code** (P0128, P0217, P0101/P0102, P2138, P0106, P0111/P0112/P0113…), so labels are grounded in SAE/CARB fault definitions, not invented.

---

### Limitations

<!-- TODO: Lei Pei, Qiuting Fu -->
<!-- What are the honest limitations
     of your approach?
     What would you do differently
     with more time or data? -->

*(Say the first one unprompted — it's the honest core.)*

- **Zero healthy false positives proves *specificity*, not *recall*.** Every threshold was calibrated to sit outside the healthy envelope, so of course healthy cars don't trip it. What we have **not** yet proven is that a real fault *would* trip it — the **fault-injection validation (Stage 4) is still open/TBD**. Some proxies (e.g. the extreme-pedal and stuck-MAP checks) sit above the healthy maximum and are explicitly *specificity-only* until injection testing runs.
- **Proxies indicate, they don't isolate.** Slow warm-up points at the thermostat but can't exclude a sensor fault; a two-estimator disagreement flags a problem without always naming the faulty sensor. Reports should read "condition indicated, sensor fault not excluded."
- **One car, low-rate, short logs.** All thresholds are calibrated on a single vehicle's data at 1 Hz with integer-quantized signals; several checks have persistence margins of only a few seconds (resolution-borderline). Coverage varies (39–100 % of trips) because short trips and heat-input guards shrink the evaluable population.
- **Some designs were honestly dropped, not hidden.** Several candidate checks (stuck-MAF, single-channel pedal freeze, MAF/MAP cohesion band) were found **infeasible on this dataset** — no healthy opportunity met the margin/coverage bar — and are documented as non-executed rather than forced through. `tps` is excluded entirely (saturated at ~83 %), with pedal demand substituted.
- **What we'd do differently:** run the fault-injection program early rather than last; seek an externally labelled fault dataset for real recall numbers; and plan a second vehicle for transfer testing.

---

## Q&A Bank

**Answer technique:** direct answer (one sentence) → one concrete fact/number → honest limitation. Never bluff a number.
**Who fields what:** Lei Pei / Qiuting Fu split by check family — but both should be ready for the ★ questions below.

1. **★ How can you trust labels you can't validate against real faults?**
> We can't claim real-fault recall yet — and we say so. What we *can* prove is **specificity**: on 66 healthy trips, zero checks trigger, with measured persistence headroom (e.g. overheating threshold 105 °C vs. healthy max 101 °C). Recall validation via fault injection is designed but still pending — that's our stated Stage-4 work.

2. **★ Isn't a simple threshold enough? Why all this machinery?**
> A single global threshold can't survive cold-start, idle, and motorway at once — loose enough to never false-alarm at speed means blind at idle. The same coolant temp is healthy during warm-up and a fault after 20 minutes. So we condition *every* threshold on the operating state and require persistence; that's what buys zero healthy false positives *and* physical meaning.

3. **★ Aren't you marking your own homework — the model team tests against your labels?**
> Deliberately not. Our labels are used only to (a) select healthy training data and (b) act as the answer key. The detector — IBM's forecasting model — **never sees our rules**; it learns "normal" independently. So when its evaluation passes, it means something. (This is the same non-circularity the model team relies on.)

4. **Why is `post_warmup` a "proxy" state — isn't the engine just warm or not?**
> The dataset has no catalyst temperature, so we can't measure true thermal readiness. We infer it from coolant temp ≥75 °C plus at least one corroborating signal (hot-idle RPM, cumulative intake air >1500 g, or intake-vs-ambient heat soak). It's an inferred state, and we label it as such.

5. **Why did you drop `tps` (throttle position)?**
> In this dataset it's stuck near 83 % and lacks its expected physical relationships — unusable as a trigger. We substitute accelerator-pedal demand, which is the frozen replacement across the MAP checks.

6. **How do you avoid single-second sensor glitches becoming faults?**
> Persistence gating: a trigger requires the condition to hold continuously (typically ≥30 s) or recur in 3 of the 4 most recent events. At 1 Hz with integer signals, isolated one-sample spikes are physically meaningless, so they're rejected by design.

7. **What happens when required signals are missing?**
> The check returns `not_evaluable` with an explicit reason rather than guessing — and the confidence system separates high / medium / low rows so downstream never treats a degraded inference as certain.

8. **Careful-with questions:**
- *"What's your fault-detection accuracy?"* → We report **specificity** (0 healthy false positives across 66 trips); recall is not yet measured — fault injection pending.
- *"Is this deployable in a real car?"* → No; offline analysis of recorded trips, calibration frozen, not real-time.
- *"Did you find any real faults?"* → No; all 81 trips are healthy. Everything is framed as stand-in definitions and specificity evidence.
