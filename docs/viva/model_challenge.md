# Viva — Challenge 2: Anomaly Detection Without Ground Truth

**Speaker:** Ray Wang, Lucca Zhou · **Time:** ~1.5 minutes
**Transition in:** "With clean, structured data, we could now detect anomalies — but that brought its own challenge."
**Transition out:** "We had a risk score — but a number means nothing to a car owner."

**Register: markers likely know nothing about cars or mechanics.** Speak the plain phrases; technical terms appear in [brackets] only for mapping back to code/docs — don't say them aloud unless asked.

**All Model Layer user stories 1–8 are complete** (Story 9 is the group-report chapters, still in progress — the completeness claim here is about the pipeline, not the write-up). Every number below is now a real measured figure, taken from the fine-tuning comparison table, the threshold calibration, and the evaluation note. No placeholders remain.

**Last verified against the code on 2026-08-01** (HEAD `ed84e6c`). If the pipeline changes again, re-check the Evaluation section first — it is the part most tightly coupled to specific artefacts.

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
- Even healthy engines never match perfectly, so we measured how big the gap normally is on healthy trips, and set the alarm line by rule rather than by taste: pick the line that detects the most, subject to raising no more than one false alarm in ten healthy trips. That landed at 0.41, and it cut false alarms on healthy driving from three-in-eleven to one-in-eleven. *[residuals normalised against healthy-window baselines; alarm threshold 0.4129 = max macro F1 s.t. healthy FPR ≤ 0.10]*
- Before anything reaches the model, incoming data is checked in two tiers: physically impossible values (an engine temperature below −40) are repaired or rejected with a clear message — but values that are merely *unusual* pass through untouched, because deleting the unusual would delete the very anomalies we're hunting. On top of that the file's own contract is enforced: one reading per second on every row, and the expected data version — a mismatch stops the run before the model ever sees it. *[two-tier range mechanism, Story 3; hard contract assertions on `dt_seconds == 1.0`, `schema_version`, `calibration_version`, operating-state form]*
- Simple physical rules then point the flagged pattern at a specific component, producing a risk score, a risk level, and a most-likely problem type in the agreed team format. Five problem types are defined on this dataset; we score three of them ourselves and pass through the data team's own verdict for the other two. *[rule-based attribution → interface JSON; 3 self-scored + 2 forwarded]*

## Why Our Approach Is Better Than Alternatives

*(~15s. One bullet aloud; the second is backup.)*

- A classifier [e.g. random forest] needs fault examples to learn from — we have none. A network trained from scratch [e.g. LSTM] would have to learn "normal" from one car's limited data, with weeks of tuning by two machine-learning beginners. The pre-trained model already knows general time-series behaviour, so we had a working end-to-end pipeline early — the other teams could integrate against it from week one — and extra training on this car's data is an *improvement step*, not a prerequisite. *[zero-shot first, fine-tuning in Story 6]*
- Because the model never sees the rule-based labels, detection stays independent of labelling — so when testing says it works, that actually means something. *[non-circular evaluation]*

## Evaluation

*(~20s.)*

- **Planted-fault testing — and the results split sharply by fault type.** We planted 14 known faults of varying strength into healthy data and checked whether the detector names the right problem. **Overheating: caught every time — 33 out of 33, with no false alarms.** **Pedal sensor: never wrong when it does alarm, but it only catches the bigger faults** — a large disagreement between the two pedal sensors is found almost always, a small one never. **Air intake: our planted version is almost never caught.** We report that as a finding, not a footnote: a gradual airflow under-read barely moves a forecast that already tracks airflow loosely, so it needs a different kind of evidence, not a stricter alarm. *[per-type P/R: cooling 1.000/1.000, pedal 1.000/0.325, MAF 0.200/0.045; macro F1 0.521; Story 7]*
- **Before/after extra training:** we compared the model out-of-the-box against the version trained on this car's healthy trips, on held-out data — everyday prediction error dropped **5.2%**, with 5 of the 6 readings no worse. *[MAE 58.00 → 54.97; e5/lr5e-5/bs8; Story 6. Note: this trained model is what the evaluation ran on; the pipeline itself still loads the out-of-the-box model — see Q13.]*
- **Honest limitation (always say this):** all of this proves detection of *planted* faults defined by stand-in rules. It does not prove the system catches real mechanical failures — that would need data from actually broken cars, which our dataset doesn't contain. And one held-out healthy stretch still scores maximum risk; no alarm setting removes that one without switching off detection entirely, so it's an open problem we've written down rather than tuned away.

**Numbers to have ready, but not to say unprompted:** macro F1 0.521, micro F1 0.541, exact hit rate 0.390, attribution accuracy ignoring the alarm line 0.565, healthy false-positive rate 0.091, 154 planted cases across 11 held-out stretches, calibration moved the line 0.30 → 0.4129 and macro F1 barely moved (0.533 → 0.521) while false alarms fell threefold.

## References

- Ekambaram et al. (2024) — *Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series* (NeurIPS 2024) — the model we use; establishes zero-/few-shot forecasting capability.
- Cherdo et al. (2023) — prediction-based anomaly detection on multivariate time series — the "forecast, then treat prediction error as the anomaly signal" paradigm as we apply it.
- Malhotra et al. (2015) — *Long Short Term Memory Networks for Anomaly Detection in Time Series* (ESANN) — earlier precedent for the same approach.
- Blázquez-García et al. (2021) — *A Review on Outlier/Anomaly Detection in Time Series Data* (ACM Computing Surveys) — survey placing prediction-based detection among standard methods.
- Nyberg (1997) — model-based diagnosis via consistency checking — the basis for comparing measured airflow against an independent estimate computed from pressure, engine speed and intake temperature.
- Bosch *Automotive Handbook* — coolant regulation within a narrow band; dual-channel redundancy in electronic throttle control.
- Proxy-definition evidence base (Data Layer's standard, cited in our evaluation note): SAE 2000-01-0939 (coolant), SAE 970209 (intake), SAE J2012 and ISO 26262-5:2018 (pedal rationality). These support the diagnostic architecture, **not** the strengths of the faults we planted.
- KIT Automotive OBD-II dataset — **TODO: get the exact citation from the Data Layer group** (they own the dataset reference).

## Visuals

**Main visual (pick one):**

1. **Two-panel "prediction vs reality" chart (recommended):** left panel = healthy stretch: predicted line and actual line almost overlapping, small shaded gap. Right panel = same stretch with the planted +15 °C temperature fault: actual line pulls away from predicted, large shaded gap, risk score bar rising below. One caption: "The model predicts normal; faults appear as the gap." — This can be generated from our real pipeline output [run the detector on a healthy vs coolant-perturbed segment and plot forecast vs actual with the residual shaded].
2. Timeline diagram of the window: a strip of 8.5 minutes labelled "model watches" flowing into 1.5 minutes labelled "model predicts", with "compare against what actually happened" beneath. Simpler, but less compelling than real data.
3. **Severity-response chart (strongest support for the honest evaluation framing):** risk score on the vertical axis, planted-fault strength on the horizontal, one line per fault family. Cooling saturates at maximum risk from the smallest fault we planted; pedal climbs steeply between the small and large offsets; air intake stays flat at ~0.22 across every strength. One picture makes the "it works here, it doesn't work there, and here's the boundary" point without a single number spoken. Generatable directly from the severity table in `synthetic_eval_metrics_e5_lr5e-5_calibrated.md`.

---

# BACKUP SECTION

*(For Q&A — not part of the main talk.)*

## Full Pipeline Detail

End-to-end, in order:

1. **Load** Group 1's feature file [`production_features.csv`: 249,694 rows, 81 trips, 118 segments; **46 columns** under `feature_schema.v1`, incl. identity columns `trip_id`/`segment_id`/`timestamp`].
2. **Validate input** — required columns present and numeric, plus four hard contract assertions that stop the run outright: sampling is exactly 1 Hz on every row [`dt_seconds == 1.0`], `schema_version == feature_schema.v1`, `calibration_version == calibration.v1`, and operating states use the agreed double-underscore form [`post_warmup__high_load`, not `post_warmup_high_load`]. Missing/non-numeric required columns → hard error.
3. **Two-tier range check** — physically impossible values repaired to blank + filled by interpolation with a message in the output [`notes` field]; a column with >5% impossible values → file rejected. Unusual-but-possible values pass untouched.
4. **Window selection** — pick an unbroken stretch of ≥700 seconds [segments ≥700 rows: 83 of 118]; windows never cross recording breaks [segment-safe windowing].
5. **Forecast** — the pre-trained model predicts 96 seconds of six readings from 512 seconds of context [TTM zero-shot, `ibm-granite/granite-timeseries-ttm-r2`; channels rpm/speed/coolant_temp/map/maf/tps].
6. **Gap measurement** — actual minus predicted, per reading; sized against healthy-window baselines so different readings are comparable [residuals; normalisation vs healthy reference spans].
7. **Risk scoring** — physically grounded rules combine the gaps with the data team's engineered features into a score per problem type. Current thresholds: cooling — absolute coolant 95→110 °C, plus heating rate 2→8 °C/min once the engine is warm [`ect_rate_180s`, gated on coolant > 85 °C]; air intake — measured airflow against an independent estimate from pressure/speed/intake temperature, 18→35 g/s [`speed_density_maf_residual`]; pedal — disagreement between the two redundant pedal sensors, 2→10 percentage points. Each ramp starts *below* its formal trigger, so a window approaching a fault already carries a non-zero score.
8. **Output** — highest-scoring type becomes the named problem [`anomaly_type` + mirrored `component`], plus score 0–1 [`risk_score`], level [`risk_level`: **Medium ≥ 0.4129, High ≥ 0.9**, versioned in `config/risk_level_calibration.v1.json`, status `provisional_synthetic_only`], confidence [`prediction_confidence`], the top contributing readings [`key_signals`], any degradation messages [`notes`], and two forward-looking fields projected from the accumulated per-trip risk history [`estimated_cycles_to_failure`, `estimated_failure_probability` — Story 8; these now carry real values, having been `null` placeholders since v0.5]. A checking script confirms the format [`validate_output.py`].
9. **Batch mode and dashboard contract** — `--batch` sweeps every window of a trip and emits `{summary, windows}`, where `summary` is the worst-risk window in the *unchanged* single-window shape, so an existing parser reads it without modification. Every run appends its windows to `risk_history.csv` [deduped on trip + window], which is what feeds step 8's projection. Expected failures exit non-zero with a single `ERROR: <message>` line on stderr and no traceback, because Group 3's dashboard shows stderr straight to the user.
10. **Verdict forwarding** — with `--proxy-decisions`, the two problem types we do not score carry the data team's already-computed verdict instead of a hard zero. **This is relaying, not scoring:** we compute none of their decision logic, we map their result onto our score and confidence fields and record where it came from in `notes`.

**No output field was added, removed or renamed** in any of this. The interface shape has been stable throughout; what changed is which values it can carry.

## Deep Dive: TTM Architecture

- **What it is:** Granite TTM ["Tiny Time Mixer", `ibm-granite/granite-timeseries-ttm-r2`] is a small, pre-trained time-series forecasting model from IBM — millions of parameters, not billions, so it runs on an ordinary laptop CPU. It is *not* a language model: it's built from lightweight mixing layers [TSMixer-style MLP blocks] specialised for numeric sequences.
- **How zero-shot works:** it was pre-trained on large public collections of time series from many domains, learning general temporal patterns — trends, cycles, correlations between channels. "Zero-shot" means we apply those pre-trained weights directly to our engine data with no additional training, using its native window sizes [512 in, 96 out].
- **Why residuals detect anomalies:** the model has effectively learned "how healthy time series continue." Feed it 8.5 minutes of healthy engine behaviour and its 96-second forecast is close to what happens. If a component is degrading, what actually happens is no longer a typical continuation — the model is *surprised*, and the surprise (prediction error) is exactly our anomaly signal. Extra training on this car's healthy trips [fine-tuning, Story 6] sharpens the healthy prediction by 5.2%, making the surprise on genuine anomalies stand out more.
- **Where forecast quality and detection quality part company:** a lower prediction error improves the baseline the detector works from, but it does not automatically improve detection of every fault. Our own results show it: fine-tuning improved forecasting across the board, yet MAF detection stayed near zero, because that fault's signature was never really visible in the forecast error to begin with. Two connected measures, two different evaluation criteria — worth saying if a marker conflates them.

## Limitations

- **Strong planted-fault performance does not guarantee real fault detection.** Our faults are simple, sudden changes [scale/offset perturbations]; real degradation is gradual, noisy, and messier. Our "correct answers" are stand-in rules, not verified mechanical failures.
- **One car, one driver.** Everything — the healthy baseline, the alarm levels — is calibrated on a single vehicle's data. No evidence it transfers to another car without re-calibration.
- **Coverage is partial, and the split is by evidence type.** Five problem types are executable on this dataset; we score three. The other two are decided by the data team's rule pipeline, which already produces a verdict for all five — so building our own scoring for those two would have duplicated an existing decision path rather than adding capability. That division also matches the methods: our approach finds *gradual drift* away from a prediction, while both of those faults are a sensor getting *stuck*, which a "hasn't changed in two minutes" rule tests for directly. For intake air temperature there's a hard boundary on top of that — it isn't one of the six channels the model forecasts, so no residual exists for it at all. **Don't claim we proved the method can't do it:** we never ran a clean test of residual detection on those two, because the scoring was retired before one existed.
- **MAF detection is inadequate by our own measurement** — recall 0.045. Fixing it needs different evidence or different scoring logic, not a different alarm threshold, and we say so rather than reporting only the macro average.
- **One healthy stretch still alarms at maximum risk.** In the calibration hold-out, one of three healthy segments scores 1.0, and no threshold at or below 1.0 removes it without disabling all detection. That's why the published alarm policy is marked provisional.
- **The failure projection is not a remaining-useful-life model.** It assumes risk continues in a straight line. Real degradation plateaus, recovers, jumps, or depends on maintenance. A genuine RUL model needs labelled degradation-to-failure histories, which we don't have.
- **What we'd do differently:** hunt for an externally labelled fault dataset from the start rather than late; design gradual, realistic fault injections instead of step changes; plan a second vehicle's data for transfer testing; and promote the fine-tuned model into the shipped pipeline rather than leaving it in the evaluation path.

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
| MAE | "the average size of the prediction error" |
| false-positive rate | "how often it cries wolf on a perfectly healthy trip" |
| verdict forwarding | "passing on the data team's own decision without redoing it ourselves" |
| batch envelope | "one file covering every window of a trip, plus the worst one called out at the top" |
| speed-density residual | "measured airflow versus what the pressure and engine speed say it should be" |

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

We plant faults ourselves in healthy data — since we planted them we know the right answers and can score the detector properly. Fourteen scenarios at varying strength: engine temperature offsets of +5, +10, +15 °C; airflow under-reads at 95%, 90%, 80%, 70% of true; and pedal faults as one-channel offsets of 2, 5, 10, 20 percentage points plus gain errors of 1.05, 1.10, 1.20. Plus an intake-pressure ×1.25 control and a healthy control. Each runs over 11 held-out stretches — 154 planted cases in total. Upfront limitation: this proves it catches artificial faults; real breakdowns would need real fault data. *[synthetic injection; precision/recall]*

### Q3. What is a "proxy failure condition"?

A stand-in definition of failure based on known engine behaviour — e.g. once warmed up, the engine's cooling liquid should sit around 90–95°; past ~100°, or still climbing when it should level off, counts as our stand-in for a cooling problem. Every rule has a written physical justification — a team rule in our shared contract.

### Q3a. Isn't the "no labels" problem the Data Layer's challenge?

Creating the stand-in labels is Group 1's job, and we don't claim it. Our side is what to *do* with them: we use their labels only to pick healthy training data and as the answer key in testing — never to train the model, which must learn normal behaviour, not label boundaries. What missing labels means for *us* is different: setting alarm levels with zero real-problem examples, solved by measuring healthy data and planting artificial faults.

### Q3b. If the car passed health validation, what are the labels even for — what is there to label?

The labelling is *computed, not discovered*: the data team runs their stand-in rules over every trip and records, window by window, where a condition fires and whether it lasts long enough to count — a brief temperature spike flags a row, but only an episode that persists becomes a label. *[proxy_flag_* → duration rule → final_label_*; duration tables 3–600 s]* Passing health validation doesn't make that pointless, because the two checks work at different levels: health validation is coarse — "this car isn't broken" (no trouble codes, readings in range) — while labels are fine-grained episodes of abnormal *behaviour*, and a perfectly healthy car can still have genuine sustained episodes (real heat build-up after a hill climb, rough idling on a cold morning). And if everything still labels healthy, that's a useful result, not a failure: it certifies our entire training set as clean and gives verified negatives. Our evaluation never depended on their labels finding anything — that's exactly why it's built on planted faults. *[healthy-training filter keys off final_label_*; all 81 trips currently healthy]*

### Q4. Why train only on healthy data?

The model's whole job is predicting what a *healthy* engine does. Trained on faulty data, it would learn to predict faults accurately too — the gap would shrink and the fault becomes invisible. Healthy-only training sharpens the healthy prediction so real problems stand out more; measured, it cut prediction error 5.2%. *[healthy-only fine-tuning, Story 6; 49 training segments / 12 validation, split by trip so no trip appears in both]*

### Q5. Why 8.5 minutes in, 1.5 minutes out?

The model's built-in window lengths — at one reading per second, 512 in and 96 out; enough to cover warm-up and steady driving. It also set a requirement we negotiated with the data team: each unbroken recording stretch ≥700 seconds; 83 of 118 delivered stretches qualify.

### Q6. How does this become "N% probability within X trips"?

Each trip is summarised by the average risk of its windows — averaging so one noisy window can't swing a whole trip. We fit a straight line through those trip averages in order. If it's rising, the number of trips left is how far the latest score sits below the High line, divided by the per-trip rise: `ceil((0.9 − latest) / slope)`. The probability is then the chance that line has crossed 0.9 ten trips from now, under a normal error model around the fit.

It refuses to guess rather than guessing badly: fewer than five trips, or a flat or falling trend, or a crossing more than 50 trips away, and both fields come back empty with a reason.

**Say this plainly if asked to demo it:** our worked example runs on a hand-built rising history, not real trips — because all 81 real trips are healthy and produce no rising trend to extrapolate. And the number is a projection of *our risk score*, not a calibrated probability that a car breaks. *[Story 8; `failure_estimation.py`; High threshold 0.9]*

### Q7. What happens with bad input data?

Two levels: missing/non-numeric required columns stop with a clear error — bad data never reaches the model silently. Physically impossible values are repaired with a note, or the file rejected if too much is affected. Merely *unusual* values pass untouched — otherwise the checks would delete the anomalies we're looking for. Separately, the file's own contract is enforced before anything else: one reading per second on every row, and the expected schema and calibration versions — a mismatch stops the run, because a file that isn't what it claims to be will produce confident nonsense downstream. *[two-tier validation; >5% rejection; notes field; contract assertions on `dt_seconds`/`schema_version`/`calibration_version`/operating-state form]*

### Q8. Why were fault types removed?

Two were, both on evidence, both recorded as documented scope decisions rather than quiet omissions. The first needed a reliable reading of the valve letting air into the engine, but in this dataset that reading is stuck at maximum most of the time — the fault can't be judged from this data. The second was about the engine's idle-speed control: nothing in the data tells us what idle speed the car was *aiming* for, and healthy idle legitimately sits at several different speeds, so there's no stable "normal" to compare against. Each time the data team made the call, the change went into the shared contract and both teams cleaned code in step — the fault list went from seven candidates to five executable ones. *[electronic_throttle_tracking_fault, tps saturation, 2026-07-13; idle_speed_control_or_surge_degradation, 2026-07-19]*

### Q9. How do you avoid false alarms?

We measure "normal wrongness" on healthy data itself and trigger only clearly above it, and the boundary is picked by a written rule, not by taste: sweep candidate alarm lines, keep the one that detects the most, subject to no more than one false alarm in ten healthy trips. That gave 0.41 for the alarm line and 0.9 for High. Calibration happens *after* the extra training step, because training changes typical gap sizes — calibrate once, on the final model.

The measured effect: false alarms on healthy driving fell from three-in-eleven to one-in-eleven, while overall detection quality barely moved. **Say the cost too:** it did that partly by suppressing weak pedal detections, so it's a trade-off, not a free win. **And the honest one:** one held-out healthy stretch still scores maximum risk, and no threshold at or below 1.0 removes it without switching detection off entirely. That's why the policy is published as provisional. *[thresholds 0.4129 / 0.9, `risk_level_calibration.v1.json`, status `provisional_synthetic_only`; Story 7]*

### Q10. Hardest cross-team problem?

A unit mix-up: one measurement delivered as change per *second* while our documents said per *minute* — a silent sixty-times error if unnoticed. Caught in contract review; alarm levels rescaled. That's why the shared format is version-numbered and never changed casually. *[coolant_slope °C/min → °C/s. Historical — that column was later replaced in the schema rewrite, so don't offer it as a live example.]*

A current one, if you want something still in the codebase: verifying the data team's decision file end-to-end, we found we'd attributed two diagnostic trouble codes to the wrong fault type in our own notes and in the shared contract — both actually belong to the cooling family. We corrected both documents. The point worth making is that the verification work caught our own error, not just theirs. *[GL-366; P0116/P0128 → cooling_degradation; corrected 2026-08-01]*

### Q11. What are the two problem types you don't score?

**Direct answer:** they're not unfinished work — they're a division of labour. The data team's rule pipeline already produces a decision for all five problem types, so us building scoring for those two would have rebuilt something that already worked, not added anything.

And the split follows the methods, which is the interesting part. Our approach finds a *gradual drift away* from what was predicted. But both of those faults are a sensor getting **stuck** — and a stuck signal is perfectly predictable. It's a flat line; the model predicts a flat line; there's no gap to measure. A rule that asks "has this value not changed in two minutes?" tests for exactly that, and it's the right tool where ours is the wrong one. For one of them there's a harder limit still: it's a temperature the model doesn't forecast at all, so there is no prediction to compare against in the first place.

As of the final sprint our output *relays* their verdict rather than reporting a hard zero, so the dashboard sees a real answer for all five types. **That's relaying, not scoring** — we compute none of their logic and we don't claim their result as ours.

**If pushed on evidence, concede this cleanly:** we can't claim we *proved* the residual method fails on those two. We did run them through the injection harness early on and they scored no differently from healthy — but that was before any scoring existed for them, so the detector was returning zero by construction. It shows the absence of an implementation, not the limit of the method. The argument for the split is the reasoning above and the ownership decision, not that measurement. *[`--proxy-decisions` forwarding; pre-scoring baseline sweep, 2026-07-18]*

### Q12. With more time?

Test on genuinely labelled fault data — an external dataset, or the data team's labelled deliveries; redesign the airflow evidence, since we've shown a threshold change won't fix that one; promote the fine-tuned model into the shipped pipeline; design gradual, realistic fault injections instead of sudden step changes; and try a second vehicle's data to test transfer.

### Q13. Which model produced those evaluation numbers — the one you ship?

**Answer straight, don't dodge:** no. The evaluation ran on the fine-tuned model; the pipeline as it stands still loads the out-of-the-box one. Wiring the fine-tuned checkpoint into the detector is a small change we haven't made yet, so the honest statement is "the detection numbers describe the fine-tuned model, and promoting it into the pipeline is outstanding work." The forecasting improvement (5.2%) and the detection results both come from the same fine-tuned artefact, so they're consistent with each other — they just describe the better model rather than the shipped one.

*(If this gets fixed before the viva, delete this and say the pipeline runs the fine-tuned model.)*

### Q14. How does the dashboard actually consume this?

One command per uploaded file. In batch mode we sweep every window of a trip and return one object containing the worst-risk window plus the full per-window list — the worst-risk part is in exactly the same shape as our single-window output, so the existing parser needed no changes. Failures come back as one plain `ERROR:` line and a non-zero exit, never a stack trace, because whatever we print on the error channel is what the user sees.

**Known open gap, say it if asked about integration:** the upload path currently passes only the feature file through to us, not the data team's decision file — so verdict forwarding won't activate in a live demo until that one path is plumbed through. It's flagged with the integration team.

### Q15. Why is the airflow fault detected so poorly?

Because the fault we planted is a *proportional* under-read — airflow reads 90% of true, say — and the model's airflow forecast was never tight enough for a 10% shift to stand out against ordinary driving variation. The prediction error moves, but not past where healthy driving already sits. That's a mismatch between the fault's signature and the evidence we're measuring, so a stricter alarm doesn't help — you'd just lose the other two fault types. The fix is different evidence: compare measured airflow against the independent pressure-and-speed estimate directly, which is what the data team's rule does, rather than routing it through forecast error. We report the number as it is [recall 0.045] because a macro average would have hidden it.

### Questions to be careful with

- **"What's your detection accuracy?"** — Don't give one number; there isn't an honest one. Give it per fault type — overheating perfect, pedal precise but insensitive to small faults, airflow near zero — and immediately scope all of it: measured on planted faults, not real breakdowns.
- **"Deployable to a real car?"** — No; the brief explicitly rules out real-time vehicle integration. Offline pipeline over recorded trips.
- **"Did it predict any real failures?"** — No; all 81 trips are healthy. Keep everything framed as stand-in definitions and planted-fault testing.
