# Challenge 1: No Fault Labels in the Data

**Speaker:** Lei Pei, Qiuting Fu
**Time:** ~1.5 minutes
**Transition in:** "Layla and Qiuting will now explain how they processed that data."
**Transition out:** "Next, Lucca and Ray will explain how these outputs were used for model."

---

# Speech Script v2.0:

##### Lei Pei: challenge and solution

Our starting point was the KIT Automotive OBD-II Dataset recommended by IBM. The reason we chose it is because it follows one car across many continuous trips offers enough consistent data to build a reliable normal baseline. But the problem is none of these trips actually contain a confirmed vehicle fault. That leaves us with no way to train or even evaluate a conventional fault classifier. A fixed global threshold is not a viable alternative either, because the same sensor reading can be healthy in one situation and abnormal in another. So we built a context-aware labelling pipeline. We begin by cleaning each trip and resampling it onto a uniform time base.  From there, we identify the vehicle's operating state — such as steady cruising or high load — and finally derive the features that describe every moment of the drive. Each rule then runs only where it is physically meaningful. We require an abnormal pattern to persist before treating it as evidence, and we return "not evaluable" whenever the data is insufficient. The result is traceable fault evidence the rest of the system can build on. Qiuting will now explain how we defined and validated these rules.

##### Qiuting Fu: basis and verification

To implement this approach, we developed five proxy fault families containing 14 individual checks. These rules are grounded in standard OBD-II fault codes and published automotive guidance. However, these proxy rules still needed validation. We therefore used controlled fault injection, changing one relevant signal at three severity levels across three different journeys. On the usable healthy data, none of the checks produced a fault decision. At the strongest injected level, every check responded on all three trips. This shows that the rules are consistent and reachable end to end. However, simulated signals are not real mechanical failures. We therefore cannot claim real-world accuracy or recall. Next, Lucca and Ray will explain how these outputs were used for model.

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

- **A single threshold would confuse operating context with failure.** Fixed limits cannot distinguish a healthy cold start from slow warm-up, or normal low airflow at idle from under-reading at high load. Our state-conditioned rules test a signal only when its physical preconditions are satisfied, then use persistence to reject isolated artefacts in the 1 Hz data.
- **Replacing the dataset would not solve the project-specific labelling problem.** Public fault datasets usually come from different vehicles, sensors, sampling rates, and driving conditions, so their labels and thresholds cannot be transferred safely to this car. Our proxy labels are generated from frozen, documented rules, retain `not_evaluable` outcomes when evidence is insufficient, and provide an auditable path from source signal to proxy decision and DTC candidate.

<!-- TODO: Lei Pei, Qiuting Fu -->

<!-- Why not just use a simple threshold?
     Why not use a different dataset?
     1-2 bullet points. -->

## Evaluation

- **Operating-condition coverage:** across the processed data, 77.85 % of rows are classified as post-warm-up, 18.63 % as warm-up, and 3.51 % as engine-off; 96.48 % receive a high-confidence operating-condition label. This shows that most observations enter downstream checks with a usable physical context.
- **Healthy-data specificity:** none of the 14 executable sub-checks produced a positive decision on its healthy evaluable units. Depending on the sub-check, the healthy baseline contained 12–81 evaluable trip- or episode-level units. This is observed zero-positive performance on this dataset, not a claim of perfect population-level specificity.
- **Stage-4 fault-injection validation:** all 14 executable sub-checks across the five proxy families were tested at three ordered severity levels and on three independent trips per level. The complete campaign contained 42 end-to-end injected runs and 126 scoped observations.
- **Acceptance results:** every case met the registered criteria. Detection rate was non-decreasing as severity increased, and the strongest severity was detected in 3/3 trips for every executable case. The checks also produced the expected result state, DTC identity, and emission or non-emission behaviour.
- **Physical and semantic plausibility:** each injection modified only its declared source signal. Affected derived features were recalculated, and the frozen production decision stages were rerun. Every injected result was paired with its healthy baseline so that a pre-existing positive decision could not be counted as a successful detection.

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

### Fault-Injection Validation Detail

The fault-injection campaign was designed to test whether the frozen proxy rules respond consistently to controlled fault-like changes. It does not retrain the rules or recalibrate their thresholds.

1. **Scope.** The campaign covers all 14 executable runtime sub-checks across the five proxy families: cooling degradation, mass-air-flow anomaly, accelerator-pedal sensor disagreement, intake-air-temperature sensor fault, and manifold-pressure/load-signal plausibility.
2. **Eligible source data.** Each injection is placed only in an existing trip or episode that already satisfies the unmodified operating-state, confidence, signal-quality, and continuity guards of the target rule.
3. **Single-signal intervention.** Only the declared raw signal is changed. Guard signals are not modified to manufacture an easier detection opportunity.
4. **Severity and replication.** Each sub-check is tested at three ordered severity points, with three independent trips at each point. This produces 9 scoped observations per sub-check and 126 observations overall.
5. **Frozen end-to-end execution.** After injection, all affected derived features are recomputed and the same rule-state, event-evidence, duration-evidence, and proxy-decision stages used in normal processing are rerun.
6. **Paired adjudication.** An injected result is compared with the corresponding healthy result. It is accepted only if the healthy result was not already positive and the injected output has the expected state, DTC identity, and emission semantics.
7. **Campaign acceptance.** Each case must have at least three severity points, at least three independent trips per point, a non-decreasing detection rate, and a strongest-severity detection rate of at least 0.8. All 14 executable cases passed; each achieved 3/3 detection at its strongest severity.

---

### Limitations

<!-- TODO: Lei Pei, Qiuting Fu -->

<!-- What are the honest limitations
     of your approach?
     What would you do differently
     with more time or data? -->

*(Say the first one unprompted — it's the honest core.)*

- **Observed zero positives are dataset-specific.** The healthy-data result demonstrates zero positive decisions among the evaluable units in this dataset. It must not be presented as perfect specificity for the wider vehicle population.
- **Proxies indicate symptoms rather than proving root cause.** Slow warm-up may indicate thermostat degradation but cannot exclude a temperature-sensor fault. Likewise, disagreement between two estimators can reveal inconsistency without always identifying which sensor is responsible.
- **The calibration is vehicle- and dataset-specific.** The thresholds were calibrated using one vehicle, 1 Hz integer-quantized signals, and relatively short trips. The same values should not be transferred to another vehicle without recalibration and validation.
- **Some designs were honestly dropped, not hidden.** Several candidate checks (stuck-MAF, single-channel pedal freeze, MAF/MAP cohesion band) were found **infeasible on this dataset** — no healthy opportunity met the margin/coverage bar — and are documented as non-executed rather than forced through. `tps` is excluded entirely (saturated at ~83 %), with pedal demand substituted.
- **Synthetic detectability is not real-fault recall.** Fault-Injection validation shows that all 14 executable checks respond correctly to the specified synthetic fault shapes, including their severity behaviour and diagnostic-output contracts. It does not prove that every physical component failure will create the same signal pattern. Labelled real-fault data is still required before reporting field recall or overall fault-detection accuracy.
- **Not every candidate design became an executable check.** Candidate checks without sufficient healthy coverage, physical observability, or decision margin remain documented as non-executed rather than being forced into the runtime system.
- **What we would do next:** obtain labelled real-fault trips to estimate recall, repeat calibration and fault injection on a second vehicle to assess transferability, and evaluate higher-rate data where short persistence margins are currently limited by 1 Hz resolution.

---

## Q&A Bank

**Answer technique:** direct answer (one sentence) → one concrete fact/number → honest limitation. Never bluff a number.
**Who fields what:** Lei Pei / Qiuting Fu split by check family — but both should be ready for the ★ questions below.

1. **★ How can you trust labels you can't validate against real faults?**

> We separate what has been demonstrated from what has not. On healthy data, every executable sub-check had zero positive decisions; in Fault-Injection stage, all 14 executable checks passed a 126-observation synthetic campaign, with 3/3 detection at strongest severity and correct diagnostic semantics. This supports healthy-data specificity and controlled synthetic detectability, but labelled physical faults are still required to estimate real-world recall.

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

8. **★ What is your fault-detection accuracy?**

> We do not report one combined accuracy number because the dataset contains no real positive faults. Instead, we report zero positive decisions on healthy evaluable units and, separately, 3/3 strongest-severity detection for each of the 14 executable synthetic cases. These are specificity and synthetic-detectability results, not field recall.

9. **★ Why is synthetic fault injection meaningful if it is not a real mechanical fault?**

> It tests whether the frozen end-to-end decision logic reacts to the exact signal behaviour it was designed to detect. Because only one declared source signal is changed and all derived features and decisions are recomputed, it validates rule reachability, persistence, severity response, and DTC semantics. It cannot validate the probability that a real component failure will generate that signal shape.

10. **What exactly counts as a successful injected detection?**

> A trigger alone is not enough. The decision must belong to the injected trip and episode, the healthy baseline must not already be positive, the result state and DTC candidate must match the registered expectation, and the rule must either emit or suppress the DTC according to its decision role.

11. **Did you find any real faults in the source data?**

> No. The source trips are treated as healthy driving data. The project demonstrates condition-aware proxy labelling, healthy-data specificity, and controlled synthetic detectability; it does not claim discovery of confirmed physical faults in those trips.

---

## Plain-words glossary

Use the plain phrase first; add the technical word only if the marker asks. A `triggered` row is not automatically a diagnosed fault: always read `result_state` together with `decision_role` and `dtc_emitted`.

### Pipeline and feature terms

| Don't say | Say instead |
|-----------|-------------|
| ingest | "read the raw trip files into one controlled pipeline" |
| resampling to 1 Hz | "putting every signal onto one reading-per-second timeline" |
| interpolation | "filling only a short missing run from the readings on either side" |
| `trip_id` | "the ID of one source drive" |
| `segment_id` | "the ID of one unbroken stretch within a drive; a recording gap starts a new one" |
| continuity boundary | "a point we do not calculate across, because the recording was interrupted" |
| quality flag | "a note saying a value was missing, filled in, suspicious, or otherwise degraded" |
| operating-condition label | "the driving and engine state in which that second occurred" |
| thermal state | "whether the engine is off, warming up, or already warm" |
| kinematic / child state | "whether the car is idling, steady, accelerating, slowing down, or under high load" |
| feature engineering | "turning cleaned sensor readings into extra measurements that make physical checks possible" |
| staged feature engineering | "building those measurements in a fixed order, with each stage checking the previous stage's output" |
| contract-validated | "checked against an agreed list of columns, units, order, versions, keys, and input files before use" |
| manifest | "a receipt recording what a stage read and produced, including versions and file fingerprints" |
| checksum / SHA-256 | "a file fingerprint used to prove that an input has not silently changed" |
| A-class context | "the cleaned sensor readings and operating-condition information carried through for the model" |
| B-class feature | "one of the 24 derived measurements deliberately delivered for modelling and proxy rules" |
| B1 sample-level feature | "a value that can be attached to one particular second" |
| B1a deterministic / atomic feature | "a direct calculation from the current or immediately previous valid readings, with no learned parameters" |
| B1b frozen-calibration transform | "a comparison with a relationship fitted once on the reference healthy data and then locked" |
| B2 engine-start context | "information tied to an observed engine start, such as starting temperatures and time since start" |
| B3 window-level feature | "a summary of a continuous recent period, such as the last 60, 120, or 180 seconds" |
| calibrated feature | "a derived value whose expected relationship comes from the locked healthy reference" |
| calibration registry | "the versioned rulebook containing the locked equations, thresholds, and valid operating ranges" |
| frozen calibration | "parameters learned or selected once and reused unchanged on every uploaded trip" |
| production assembly | "joining the approved context and 24 features into the final table handed downstream" |
| `production_features.csv` | "the final one-row-per-second Data Layer handoff to the Model Layer" |
| sample grain | "one row represents one second" |
| episode grain | "one row represents one continuous qualifying period, such as an engine start or sustained exceedance" |
| event grain | "one row represents one discrete occurrence, such as a pedal step" |
| residual | "the gap between what was measured and what an independent physical relationship expected" |
| persistence | "requiring the evidence to last, rather than reacting to one noisy second" |
| right-censored | "the recording ended before the required observation time, so the outcome is unknown rather than a pass or failure" |

### Proxy evidence and decision terms

| Don't say | Say instead |
|---|---|
| proxy failure | "a transparent stand-in definition of fault-like behaviour, not a mechanically confirmed failure" |
| `proxy_id` | "the broad component problem being checked, such as cooling or airflow" |
| `sub_check_id` | "one specific test inside that broad problem, such as slow warm-up or sustained overheating" |
| enable condition / guard | "the conditions that must be true before the test is allowed to judge" |
| rule-state builder | "the stage that decides whether each rule has valid data and a genuine opportunity to run" |
| event evidence | "evidence built around a discrete action, such as whether pressure responded to a pedal step" |
| duration evidence | "evidence showing how long an abnormal condition continued" |
| decision builder | "the final stage that combines evidence, assigns its role and state, routes attribution, and controls code emission" |
| `pass` | "this particular check had a valid opportunity to run and its fault criterion was not met; it does not prove the whole vehicle is healthy" |
| `triggered` | "this check's active condition was met; whether that becomes a fault decision depends on the evidence role" |
| `not_evaluable` | "the check exists and ran, but this input lacked valid data, context, opportunity, or calibration coverage, so it refused to guess" |
| `pending` | "an early warning pattern is present, but the separate confirmation condition has not been met" |
| `verdict` | "a check authorised to make an executable diagnostic decision; only a permitted verdict can emit a DTC" |
| `pending_precursor` | "early evidence worth retaining, but not enough to declare or emit a fault" |
| `support` | "secondary evidence used to judge sensor trust or confidence; it can activate but never emits a code by itself" |
| `arbitration_evidence` | "shared inconsistency evidence that proves two measurements disagree but needs other witnesses to decide which side to blame" |
| `decision_role` | "what authority this evidence has: final decision, early warning, supporting witness, or attribution evidence" |
| `result_state` | "what happened when that evidence role was evaluated: clear, active, unavailable, or awaiting confirmation" |
| `decision_reason` | "the recorded plain explanation for why the row received that state" |
| `direction` | "the shape of the evidence, such as too high, too low, stuck, or inconsistent" |
| `decision_margin` | "the rule-specific amount of headroom beyond or short of its registered decision boundary" |
| `dtc_candidate_label` | "the real OBD-II code associated with the evidence; naming it does not mean it was emitted" |
| `dtc_emitted` | "the final yes/no record of whether routing authorised the diagnostic code" |
| DTC | "a standard on-board diagnostic trouble code" |
| attribution / routing | "using independent evidence to decide which component should receive shared symptoms" |
| confidence tier | "how strongly the available data supports the result, kept separate from pass or trigger state" |
| evaluable unit | "a trip, start, event, or episode that actually met a check's requirements and could be judged" |
| non-executed / infeasible design | "a proposed check that was removed before runtime because the dataset could not support it; this is not `not_evaluable`" |
| condition-stratified baseline | "the healthy reference for the same operating state, rather than one global normal range" |
| threshold outside the healthy envelope | "a boundary placed beyond what the reference healthy trips showed in that condition" |
| 3-of-4 event rule | "trigger only when at least three of the four latest valid events fail to respond" |
| DTC arbitration | "do not blame MAF or MAP from their disagreement alone; use an independent witness or report the mismatch without guessing" |
| synthetic fault injection | "deliberately changing one recorded signal to test whether the frozen end-to-end rule reaches the expected output" |
| healthy-data specificity | "how well the rules avoid positive decisions on the available healthy recordings" |
| synthetic detectability | "whether the rules catch the planted signal changes; it is not recall on real mechanical faults" |
