# Viva — Challenge 2: Anomaly Detection Without Ground Truth

**Speaker:** Ray Wang, Lucca Zhou · **Time:** ~1.5 minutes
**Transition in:** "With clean, structured data, we could now detect anomalies — but that brought its own challenge."
**Transition out:** "We had a risk score — but a number means nothing to a car owner."

**Register: markers likely know nothing about cars or mechanics.** Speak the plain phrases; technical terms appear in [brackets] only for mapping back to code/docs — don't say them aloud unless asked.

Per the team's framing, this draft speaks as if **all Model Layer user stories (1–8) are complete**. Slots marked [fill: …] take the real numbers from the finished work (fine-tuning comparison table, evaluation note) — insert them before the viva.

**Suggested speaker split:** Lucca — "why specific" + the data-checking half of the solution (input validation is her work); Ray — the model half of the solution + "why better" + evaluation (TTM and scoring are his work).

---

## Why This Challenge Is Specific to This Project

*(~20s. Say 2 of these 3; the first is mandatory.)*

- Standard anomaly detection is taught with labelled examples: you show the model both normal and faulty data, and you test it against verified faults. **We had zero faulty examples** — all 81 trips in our dataset are healthy driving. Nothing to train a fault-detector on, and nothing to test it against either.
- The only "fault labels" that exist in this project are stand-in rules the data team wrote themselves. If we used the same rules to *detect* faults, our testing would be marking our own homework — the detector had to be independent of the labels.
- And "normal" isn't one fixed range: what's normal on a motorway is abnormal at a standstill, and an engine still warming up looks different from one that's warm. Simple limits either false-alarm constantly or miss real problems.

## Our Solution

*(~35s. Bullets 1–2 are the core; 3–4 as time allows.)*

- We flipped the problem: instead of teaching a model what *faults* look like, we use a model that predicts what *normal* looks like. IBM's pre-trained forecasting model [Granite TTM] watches about 8.5 minutes of six engine readings and predicts the next 1.5 minutes — and it works straight out of the box, no fault examples needed. *[zero-shot, 512→96 steps at 1 Hz, channels rpm/speed/coolant_temp/map/maf/tps]*
- On a healthy engine, prediction matches reality. When a part degrades, reality drifts away from the prediction — and the *size of that gap* becomes our anomaly score. Crucially, the drift shows up while every reading still looks individually acceptable. *[forecast residuals]*
- Even healthy engines never match perfectly, so we measured how big the gap normally is on healthy trips — per reading, per driving situation — and only raise a flag clearly above that. *[residuals normalised against healthy-window baselines; triggers calibrated on healthy distribution]*
- Before anything reaches the model, incoming data is checked in two tiers: physically impossible values (an engine temperature below −40) are repaired or rejected with a clear message — but values that are merely *unusual* pass through untouched, because deleting the unusual would delete the very anomalies we're hunting. *[two-tier range mechanism, Story 3]*
- Simple physical rules then point the flagged pattern at a specific component, producing a risk score, a risk level, and a most-likely problem type in the agreed team format. *[rule-based attribution → interface JSON]*

## Why Our Approach Is Better Than Alternatives

*(~15s. One bullet aloud; the second is backup.)*

- A classifier [e.g. random forest] needs fault examples to learn from — we have none. A network trained from scratch [e.g. LSTM] would have to learn "normal" from one car's limited data, with weeks of tuning by two machine-learning beginners. The pre-trained model already knows general time-series behaviour, so we had a working end-to-end pipeline early — the other teams could integrate against it from week one — and extra training on this car's data is an *improvement step*, not a prerequisite. *[zero-shot first, fine-tuning in Story 6]*
- Because the model never sees the rule-based labels, detection stays independent of labelling — so when testing says it works, that actually means something. *[non-circular evaluation]*

## Evaluation

*(~20s.)*

- **Planted-fault testing:** we took healthy data and planted three known faults — engine temperature +15 °C, air intake −30%, intake pressure +25% — then checked whether the detector names the right problem. It identified the correct fault in [fill: X] of 3 scenarios; its alarms were right [fill: precision] of the time and it caught [fill: recall] of the planted faults. *[synthetic injection; numbers from evaluation_note.md; Story 7]*
- **Before/after extra training:** we compared the model out-of-the-box against the version trained on this car's healthy trips, on held-out data — the trained version's everyday prediction errors are smaller by [fill: from comparison table], so real problems stand out more. *[zero-shot vs fine-tuned residual comparison table; Story 6]*
- **Honest limitation (always say this):** all of this proves detection of *planted* faults defined by stand-in rules. It does not prove the system catches real mechanical failures — that would need data from actually broken cars, which our dataset doesn't contain.

## References
[Need to be verified. TBD]
- Ekambaram et al. (2024) — *Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series* (NeurIPS 2024) — the model we use; establishes zero-/few-shot forecasting capability.
- Malhotra et al. (2015) — *Long Short Term Memory Networks for Anomaly Detection in Time Series* (ESANN) — precedent for the "forecast, then treat prediction error as the anomaly signal" approach.
- Blázquez-García et al. (2021) — *A Review on Outlier/Anomaly Detection in Time Series Data* (ACM Computing Surveys) — survey placing prediction-based detection among standard methods.
- KIT Automotive OBD-II dataset — **TODO: get the exact citation from the Data Layer group** (they own the dataset reference).

## Visuals

**Main visual (pick one):**

1. **Two-panel "prediction vs reality" chart (recommended):** left panel = healthy stretch: predicted line and actual line almost overlapping, small shaded gap. Right panel = same stretch with the planted +15 °C temperature fault: actual line pulls away from predicted, large shaded gap, risk score bar rising below. One caption: "The model predicts normal; faults appear as the gap." — This can be generated from our real pipeline output [run the detector on a healthy vs coolant-perturbed segment and plot forecast vs actual with the residual shaded].
2. Timeline diagram of the window: a strip of 8.5 minutes labelled "model watches" flowing into 1.5 minutes labelled "model predicts", with "compare against what actually happened" beneath. Simpler, but less compelling than real data.

---

# BACKUP SECTION

*(For Q&A — not part of the main talk.)*

## Full Pipeline Detail

End-to-end, in order:

1. **Load** Group 1's feature file [`feature_dataset.csv`: 249,694 rows, 81 trips, 118 segments; 41 columns incl. identity columns `trip_id`/`segment_id`/`timestamp`].
2. **Validate input** — required columns present and numeric; the data team's documented "by-design blanks" are tolerated [policy NaNs: `pedal_to_throttle_delay` ≈99.6%, `idle_rpm_stability` ≈98.6%, `coolant_stability` ≈29%]. Missing/non-numeric required columns → hard error.
3. **Two-tier range check** — physically impossible values repaired to blank + filled by interpolation with a message in the output [`notes` field]; a column with >5% impossible values → file rejected. Unusual-but-possible values pass untouched.
4. **Window selection** — pick an unbroken stretch of ≥700 seconds [segments ≥700 rows: 83 of 118]; windows never cross recording breaks [segment-safe windowing].
5. **Forecast** — the pre-trained model predicts 96 seconds of six readings from 512 seconds of context [TTM zero-shot; channels rpm/speed/coolant_temp/map/maf/tps].
6. **Gap measurement** — actual minus predicted, per reading; sized against healthy-window baselines so different readings are comparable [residuals; normalisation vs healthy medians].
7. **Risk scoring** — physically grounded rules combine the gaps with the data team's engineered features into a score per problem type [e.g. cooling: coolant thresholds in °C/s (0.033–0.133); air intake: agreement between two air measurements, trigger calibrated on healthy data (z≈1.8); pedal: disagreement between the two redundant pedal sensors, scored 2–10 percentage points].
8. **Output** — highest-scoring type becomes the named problem [`anomaly_type` + mirrored `component`], plus score 0–1 [`risk_score`], level [`risk_level` Low/Med/High — boundaries calibrated in Story 7], confidence [`prediction_confidence`], the top contributing readings [`key_signals`], any degradation messages [`notes`], and two forward-looking fields extrapolated from the accumulated per-trip risk-score history — trips remaining until the projected risk crosses the failure threshold, and the probability of failure within that horizon [`estimated_cycles_to_failure`, `estimated_failure_probability` — Story 8]. A checking script confirms the format [`validate_output.py`].

## Deep Dive: TTM Architecture

- **What it is:** Granite TTM ["Tiny Time Mixer", `ibm-granite/granite-timeseries-ttm-r2`] is a small, pre-trained time-series forecasting model from IBM — millions of parameters, not billions, so it runs on an ordinary laptop CPU. It is *not* a language model: it's built from lightweight mixing layers [TSMixer-style MLP blocks] specialised for numeric sequences.
- **How zero-shot works:** it was pre-trained on large public collections of time series from many domains, learning general temporal patterns — trends, cycles, correlations between channels. "Zero-shot" means we apply those pre-trained weights directly to our engine data with no additional training, using its native window sizes [512 in, 96 out].
- **Why residuals detect anomalies:** the model has effectively learned "how healthy time series continue." Feed it 8.5 minutes of healthy engine behaviour and its 96-second forecast is close to what happens. If a component is degrading, what actually happens is no longer a typical continuation — the model is *surprised*, and the surprise (prediction error) is exactly our anomaly signal. Extra training on this car's healthy trips [fine-tuning, Story 6] sharpens the healthy prediction, making the surprise on genuine anomalies stand out more.

## Limitations

- **Strong planted-fault performance does not guarantee real fault detection.** Our faults are simple, sudden changes [scale/offset perturbations]; real degradation is gradual, noisy, and messier. Our "correct answers" are stand-in rules, not verified mechanical failures.
- **One car, one driver.** Everything — the healthy baseline, the alarm levels — is calibrated on a single vehicle's data. No evidence it transfers to another car without re-calibration.
- **Coverage is partial.** 3 of 6 problem types are scored; the other 3 are output as zero-score placeholders — the physical research on them belongs to the data team, who own the label definitions, and our scoring logic follows once those are final.
- **What we'd do differently:** hunt for an externally labelled fault dataset from the start rather than late; design gradual, realistic fault injections instead of step changes; and plan a second vehicle's data for transfer testing.

## Plain-words glossary

Use the plain phrase first; add the technical word only if the marker asks.

| Don't say | Say instead |
|---|---|
| residual | "the gap between what the model predicted and what actually happened" |
| coolant temperature | "engine temperature — the liquid that keeps the engine cool" |
| MAP / manifold pressure | "the air pressure inside the engine's intake" |
| MAF / mass airflow | "how much air the engine is breathing in" |
| TPS / throttle position | "how far open the valve that lets air into the engine is" |
| RPM | "engine speed" |
| zero-shot | "using the model straight out of the box, no training" |
| fine-tuning | "extra training on this specific car's healthy data" |
| proxy failure condition | "a stand-in definition of failure" |
| precision / recall | "how often the alarms are right / how many planted faults it catches" |
| drive cycle | "one trip" |
| segment | "one unbroken stretch of recording" |
| inference | "running the model" |
| 512/96 window | "about 8.5 minutes in, 1.5 minutes out" |

---

# Q&A BANK

*(★ questions were actually asked by our tutor.)*

**Answer technique:** direct answer first (one sentence) → one concrete supporting fact → honest limitation or next step. Never bluff a number.

**Who fields what:** Lucca — data interface / validation / fault injection; Ray — model / scoring / training. Architecture: either.

### ★ Why TTM at all? Simple if-else rules could tell which component is out of range.

**Direct answer:** A simple rule is a smoke alarm — it goes off when there's already smoke. Our job is prediction: saying how likely a failure is *before* it happens. A rule only tells you a limit has already been crossed; the model spots readings drifting away from normal while still inside every limit.

Supporting points (pick 2–3):

1. **Prediction needs a score that rises gradually.** A rule answers yes/no — no trend to project forward. Our required output is "N% chance of failure within the next X trips"; you can only extend a curve if you have one.
2. **"Normal" depends on the driving situation.** One fixed limit must survive city, motorway and warm-up at once — loose enough to never false-alarm on the motorway means missing real problems at idle. The model conditions "normal" on the last 8.5 minutes of actual driving.
3. **Some faults keep every reading in range** while readings stop agreeing with *each other* — air intake no longer matching pressure and engine speed. Per-reading rules can't see that; a model predicting all six together can.
4. **We'd be marking our own homework.** The test answers were made with rules; detecting with the same rules would always pass. The model is an independent detection channel, so the evaluation proves something.

**Honest concession (say it):** We do also use simple rules — for naming *which* part is at fault and defining what counts as failure — because rules are easy to understand and defend. The design is deliberately a combination: the model finds and grades the problem early; the rules explain it. *(If pushed: the brief lists "train a model to predict component failure" as a Must.)*

### ★ Isn't your JSON output too deterministic — it names one definite anomaly type?

**Direct answer:** The name looks definite, but it never travels alone. Every output also carries a risk score from 0 to 1 and a separate confidence number — and the report generated downstream words its advice more or less strongly depending on that confidence: high confidence gives specific actions, low confidence gives "keep an eye on it" wording. So the *certainty* is graded, even though the label is not. *[risk_score, prediction_confidence; Report Layer wording rule, INTERFACE.md §3.3]*

Supporting points:

1. **The type only means something together with its score.** Internally we score *every* fault type and name the highest — a healthy engine simply gets a low score everywhere, so "cooling problem, risk 0.1, level Low" reads as "nothing to worry about", not as a diagnosis. *[per-type scores → highest wins]*
2. **Deterministic in the other sense is deliberate.** Same input always gives the same output — that's reproducibility, so any result can be re-run and audited. The real question is whether uncertainty is *expressed*, and that's what the score and confidence fields are for.

**Honest concession (say it):** it's a fair point that only the top candidate is named. When two fault types score close together, that ambiguity is invisible in the output — and a real car can have two problems at once, which a single label masks. The clean fix is additive: also report the ranked scores of all types as an extra field. Adding a field doesn't break the agreed format, but mid-project we prioritised contract stability for the downstream team — so it's recorded as future work rather than changed now. *[additive schema change; contract stability rule]*

### Q1. Why a forecasting model instead of training a fault classifier?

A classifier needs fault examples to learn from and we have none — it's all healthy driving. A prediction model only needs to learn normal; anything abnormal shows up on its own as a bad prediction. It also works straight out of the box, which let two beginners get the whole pipeline running before any training. *[zero-shot TTM]*

### Q2. How do you know it works with no real faults?

We plant faults ourselves in healthy data (temperature +15°, air intake −30%, pressure +25%) — since we planted them we know the right answers and can score the detector properly. Upfront limitation: this proves it catches artificial faults; real breakdowns would need real fault data. *[synthetic injection; precision/recall]*

### Q3. What is a "proxy failure condition"?

A stand-in definition of failure based on known engine behaviour — e.g. once warmed up, the engine's cooling liquid should sit around 90–95°; past ~100°, or still climbing when it should level off, counts as our stand-in for a cooling problem. Every rule has a written physical justification — a team rule in our shared contract.

### Q3a. Isn't the "no labels" problem the Data Layer's challenge?

Creating the stand-in labels is Group 1's job, and we don't claim it. Our side is what to *do* with them: we use their labels only to pick healthy training data and as the answer key in testing — never to train the model, which must learn normal behaviour, not label boundaries. What missing labels means for *us* is different: setting alarm levels with zero real-problem examples, solved by measuring healthy data and planting artificial faults.

### Q3b. If the car passed health validation, what are the labels even for — what is there to label?

The labelling is *computed, not discovered*: the data team runs their stand-in rules over every trip and records, window by window, where a condition fires and whether it lasts long enough to count — a brief temperature spike flags a row, but only an episode that persists becomes a label. *[proxy_flag_* → duration rule → final_label_*; duration tables 3–600 s]* Passing health validation doesn't make that pointless, because the two checks work at different levels: health validation is coarse — "this car isn't broken" (no trouble codes, readings in range) — while labels are fine-grained episodes of abnormal *behaviour*, and a perfectly healthy car can still have genuine sustained episodes (real heat build-up after a hill climb, rough idling on a cold morning). And if everything still labels healthy, that's a useful result, not a failure: it certifies our entire training set as clean and gives verified negatives. Our evaluation never depended on their labels finding anything — that's exactly why it's built on planted faults. *[healthy-training filter keys off final_label_*; all 81 trips currently healthy]*

### Q4. Why train only on healthy data?

The model's whole job is predicting what a *healthy* engine does. Trained on faulty data, it would learn to predict faults accurately too — the gap would shrink and the fault becomes invisible. Healthy-only training sharpens the healthy prediction so real problems stand out more. *[healthy-only fine-tuning, Story 6]*

### Q5. Why 8.5 minutes in, 1.5 minutes out?

The model's built-in window lengths — at one reading per second, 512 in and 96 out; enough to cover warm-up and steady driving. It also set a requirement we negotiated with the data team: each unbroken recording stretch ≥700 seconds; 83 of 118 delivered stretches qualify.

### Q6. How does this become "N% probability within X trips"?

Each trip gets a risk score, and across trips those scores form a curve. If the curve is rising, we extend it forward to estimate how many trips until it crosses the danger line, then convert that horizon into a probability. A flat, healthy history degrades gracefully — capped horizon, low probability — rather than giving a misleading estimate. *[Story 8; risk history by trip_id; threshold-crossing extrapolation]*

### Q7. What happens with bad input data?

Two levels: missing/non-numeric required columns stop with a clear error — bad data never reaches the model silently. Physically impossible values are repaired with a note, or the file rejected if too much is affected. Merely *unusual* values pass untouched — otherwise the checks would delete the anomalies we're looking for. *[two-tier validation; >5% rejection; notes field]*

### Q8. Why was a fault type removed?

One planned type needed a reliable reading of the valve letting air into the engine, but in this dataset that reading is stuck at maximum most of the time — the fault can't be judged from this data. The data team removed it, the change went into the shared contract, both teams cleaned code in step. *[electronic_throttle_tracking_fault; tps saturation; 2026-07-13]*

### Q9. How do you avoid false alarms?

We measure "normal wrongness" on healthy data itself and trigger only clearly above it. Final Low/Medium/High boundaries are set *after* the extra training step, because training changes typical gap sizes — calibrate once, on the final model. *[healthy-distribution calibration; Story 7]*

### Q10. Hardest cross-team problem?

A unit mix-up: one measurement delivered as change per *second* while our documents said per *minute* — a silent sixty-times error if unnoticed. Caught in contract review; alarm levels rescaled. That's why the shared format is version-numbered and never changed casually. *[coolant_slope °C/min → °C/s]*

### Q11. What are the "pending" problem types?

Three types are defined by the data team's research — they own the labels, so the physical research on these types is their work, not ours. Our model outputs them with a fixed score of zero so the agreed format stays stable for the next team; our scoring logic follows once their definitions are final. *[0.0-score placeholders]*

### Q12. With more time?

Test on genuinely labelled fault data — an external dataset, or the data team's labelled deliveries; add scoring for the three pending types once the data team's definitions are final; design gradual, realistic fault injections instead of sudden step changes; and try a second vehicle's data to test transfer.

### Questions to be careful with

- **"What's your detection accuracy?"** — Give the real evaluation numbers [fill: X of 3 correct; precision/recall per type] and immediately scope them: measured on planted faults, not real breakdowns.
- **"Deployable to a real car?"** — No; the brief explicitly rules out real-time vehicle integration. Offline pipeline over recorded trips.
- **"Did it predict any real failures?"** — No; all 81 trips are healthy. Keep everything framed as stand-in definitions and planted-fault testing.
