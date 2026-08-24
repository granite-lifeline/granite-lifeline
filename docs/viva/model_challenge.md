# Viva — Challenge 2: Anomaly Detection Without Ground Truth

**Speakers:** Ray Wang, Lucca Zhou · **Time:** Challenge 2 full version ~1.5 minutes, plus a ~17-second Report handoff
**Transition in:** "Without faulty training examples, how could we know that drift meant risk?"
**Transition out:** "How could we explain the evidence without inventing a diagnosis?"

**Register: markers likely know nothing about cars or mechanics.** Speak the plain phrases; technical terms appear in [brackets] only for mapping back to code/docs — don't say them aloud unless asked.

**All Model Layer user stories 1–8 are complete** (Story 9 is the group-report chapters, still in progress — the completeness claim here is about the pipeline, not the write-up). Evaluation numbers below are measured figures from the committed artefacts. The separate Story 8 contract sample uses a synthetic rising history; the viva handoff instead uses 22 committed Model windows from six real Seat Leon trips. Neither supplies labelled degradation-to-failure evidence.

**Last verified on 2026-08-24** against Model repo HEAD `a1fc299`, live main-repo contract v1.6, `gl-406-viva-slides-polish-0-1` tip `e26e064`, and report tip `59ea88e`. The recorded full-suite Model test evidence remains **209 passed, 16 skipped, three warnings** from 2026-08-10; this review also reran 41 targeted batch, ranking, history, and estimator tests. If the pipeline changes again, re-check the Evaluation, ranked-output, estimator, and TTM-configuration sections first.

**Suggested speaker split:** Lucca — "why specific" + the data-checking half of the solution (input validation is her work); Ray — the model half of the solution + "why better" + evaluation (TTM and scoring are his work).

---

## Why This Challenge Is Specific to This Project

*(~20s. Say 2 of these 3; the first is mandatory.)*

- Standard anomaly detection is taught with labelled examples: you show the model both normal and faulty data, and you test it against verified faults. **We had zero verified faulty examples** — the 81 trips record ordinary driving and provide no mechanically verified fault or repair outcomes. Nothing to train a supervised fault classifier on, and no real failure event against which to test it.
- The only "fault labels" that exist in this project are stand-in rules the data team wrote themselves. If we used only the same rules to detect faults, our testing would be marking our own homework — the forecast evidence had to remain independent of those labels.
- And "normal" isn't one fixed range: what's normal on a motorway is abnormal at a standstill, and an engine still warming up looks different from one that's warm. Simple limits either false-alarm constantly or miss real problems.

## Our Solution

*(~35s. Bullets 1–2 are the core; 3–4 as time allows.)*

- We flipped the problem: instead of teaching a model what *faults* look like, we use a model that predicts what *normal* looks like. IBM's pre-trained forecasting model [Granite TTM] watches about 8.5 minutes of six engine readings and predicts the next 1.5 minutes — and it works straight out of the box, no fault examples needed. *[zero-shot, 512→96 steps at 1 Hz, channels rpm/speed/coolant_temp/map/maf/tps]*
- On quality-gated ordinary driving, prediction should stay close to reality. When behaviour changes, reality can drift away from the prediction — and the *size of that gap* becomes independent anomaly evidence. A gap can reveal a temporal change that no single reading explains on its own, but we did not measure real mechanical lead time. *[forecast residuals]*
- Even healthy engines never match perfectly, so we scale each signal's mean forecast gap by its healthy reference-range width. We then set the shared alarm line by rule rather than by taste: pick the line that detects the most, subject to raising no more than one false alarm in ten healthy trips. That landed at 0.41, and it cut false alarms on healthy driving from three-in-eleven to one-in-eleven. *[residual mean ÷ healthy reference span; alarm threshold 0.4129 = max macro F1 s.t. healthy FPR ≤ 0.10]*
- Before anything reaches the model, incoming data is checked in two tiers: physically impossible values (an engine temperature below −40) are repaired or rejected with a clear message — but values that are merely *unusual* pass through untouched, because deleting the unusual would delete the very anomalies we're hunting. On top of that the file's own contract is enforced: one reading per second on every row, and the expected data version — a mismatch stops the run before the model ever sees it. *[two-tier range mechanism, Story 3; hard contract assertions on `dt_seconds == 1.0`, `schema_version`, `calibration_version`, operating-state form]*
- We combine the forecast gaps with physically grounded engineered features to score the most likely system, producing a risk score, risk level, and problem type in the agreed format. Five problem types are defined; we score three and relay the data team's verdict for the other two. The Data Layer owns the proxy definitions and frozen transforms; the Model Layer owns its continuous scoring path. *[residual + physical attribution → interface JSON; 3 Model-scored + 2 Data-forwarded]*

## Why Our Approach Is Better Than Alternatives

*(~15s. One bullet aloud; the second is backup.)*

- A classifier [e.g. random forest] needs fault examples to learn from — we have none. A network trained from scratch [e.g. LSTM] would have to learn "normal" from one car's limited data, with weeks of tuning by two machine-learning beginners. The pre-trained model already knows general time-series behaviour, so we had a working end-to-end pipeline early — the other teams could integrate against it from week one — and extra training on this car's data is an *improvement step*, not a prerequisite. *[zero-shot first, fine-tuning in Story 6]*
- Because TTM never sees the rule-based labels as training targets, its forecast evidence is separate from the proxy decision. Synthetic injection then supplies a traceable expected family. This reduces circularity, although synthetic proxies still cannot replace real ground truth. *[partially independent evaluation]*

## Evaluation

*(~20s.)*

- **Synthetic-change testing — and the results split sharply by type.** We defined 14 controlled perturbation settings and applied them across 11 usable held-out stretches, giving **154 injected cases**. **Overheating: caught every time — 33 out of 33, with no false alarms.** **Pedal sensor: never wrong when it does alarm, but it only catches the bigger changes.** **Air intake: the proportional under-read is almost never caught.** We report that as a finding, not a footnote: the airflow shift barely moves a forecast that already tracks airflow loosely, so it needs different evidence, not a stricter shared alarm. *[per-type P/R: cooling 1.000/1.000, pedal 1.000/0.325, MAF 0.200/0.045; macro F1 0.521; Story 7]*
- **Before/after extra training:** we compared the model out-of-the-box against the version trained on this car's healthy trips, on held-out data — everyday prediction error dropped **5.2%**, with 5 of the 6 readings no worse. *[MAE 58.00 → 54.97; e5/lr5e-5/bs8; Story 6. Note: this trained model is what the evaluation ran on; the pipeline itself still loads the out-of-the-box model — see Q13.]*
- **Honest limitation (always say this):** all of this proves detection of *planted* faults defined by stand-in rules. It does not prove the system catches real mechanical failures — that would need data from actually broken cars, which our dataset doesn't contain. And one held-out healthy stretch still scores maximum risk; no alarm setting removes that one without switching off detection entirely, so it's an open problem we've written down rather than tuned away.

**Numbers to have ready, but not to say unprompted:** macro F1 0.521, micro F1 0.541, exact hit rate 0.390, attribution accuracy ignoring the alarm line 0.565, healthy false-positive rate 0.091, 154 planted cases across 11 held-out stretches, calibration moved the line 0.30 → 0.4129 and macro F1 barely moved (0.533 → 0.521) while false alarms fell threefold.

**Canonical viva handoff case:** `report_layer/evaluation/viva_real_case/real_case_input.json` carries `cooling_degradation`, risk `0.5021` / `Medium`, confidence `0.842`, coolant `85.0 °C` against `90–95`, and coolant rise `5.0486 °C/min` against `0–2`. Its associated 22-window, six-trip history projects the risk score crossing the High line in five trips, with probability `0.7502` within ten trips. This is the one case shown continuously from Model stage 4 through the Report slide. The older `kit_residual_sample.json` values (`0.585`, `98 °C`, four trips, `1.0`) remain a separate synthetic contract demonstration and are not the viva case.

## References

- Ekambaram et al. (2024) — *Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series* (NeurIPS 2024) — the model we use; establishes zero-/few-shot forecasting capability.
- Cherdo et al. (2023) — prediction-based anomaly detection on multivariate time series — the "forecast, then treat prediction error as the anomaly signal" paradigm as we apply it.
- Malhotra et al. (2015) — *Long Short Term Memory Networks for Anomaly Detection in Time Series* (ESANN) — earlier precedent for the same approach.
- Blázquez-García et al. (2021) — *A Review on Outlier/Anomaly Detection in Time Series Data* (ACM Computing Surveys) — survey placing prediction-based detection among standard methods.
- Nyberg (1997) — model-based diagnosis via consistency checking — the basis for comparing measured airflow against an independent estimate computed from pressure, engine speed and intake temperature.
- Bosch *Automotive Handbook* — coolant regulation within a narrow band; dual-channel redundancy in electronic throttle control.
- Proxy-definition evidence base (Data Layer's standard, cited in our evaluation note): SAE 2000-01-0939 (coolant), SAE 970209 (intake), SAE J2012 and ISO 26262-5:2018 (pedal rationality). These support the diagnostic architecture, **not** the strengths of the faults we planted.
- Weber, Marc (2019) — *Automotive OBD-II Dataset*, Karlsruhe Institute of Technology (KIT), DOI `10.5445/IR/1000085073`.

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
4. **Window selection** — pick an unbroken stretch of ≥700 seconds that also passes the quality gate [61 of 118 segments across 59 trips are eligible; 49 train segments across 47 trips and 12 validation segments/trips are retained]; windows never cross recording breaks [segment-safe windowing].
5. **Forecast** — the pre-trained model predicts 96 seconds of six readings from 512 seconds of context [TTM zero-shot, `ibm-granite/granite-timeseries-ttm-r2`; channels rpm/speed/coolant_temp/map/maf/tps].
6. **Gap measurement** — absolute predicted-versus-actual gap, averaged per signal and divided by that signal's healthy reference-range width so different readings are comparable [mean absolute residual; normalisation vs `REFERENCE_RANGES` span].
7. **Risk scoring** — the Model Layer's continuous evidence ramps combine forecast gaps with Data-owned engineered features into a score per problem type. Current ramps: cooling — absolute coolant 95→110 °C, plus heating rate 2→8 °C/min once the engine is warm [`ect_rate_180s`, gated on coolant > 85 °C]; air intake — measured airflow against an independent estimate from pressure/speed/intake temperature, 18→35 g/s [`speed_density_maf_residual`]; pedal — disagreement between the two redundant pedal sensors, 2→10 percentage points. These ramps support attribution but are not the Data Layer's frozen binary proxy triggers.
8. **Output** — all five types are scored and stably ranked. The strongest becomes the top-level problem [`anomaly_type` + mirrored `component`]; contract v1.6 also emits the complete second-ranked distinct component as optional `secondary_risk`, even when its level is Low. Both positions carry score 0–1, level [`risk_level`: **Medium ≥ 0.4129, High ≥ 0.9**, versioned in `config/risk_level_calibration.v1.json`, status `provisional_synthetic_only`], confidence, key signals, notes, provenance, and their own forward-looking fields [`estimated_cycles_to_failure`, `estimated_failure_probability` — Story 8]. A checking script confirms the format [`validate_output.py`].
9. **Batch mode and dashboard contract** — `--batch` sweeps every window of a trip and emits `{summary, windows}`. Each window carries its primary result plus `secondary_risk`; `summary` is the window with the highest *primary* risk and preserves that same ranked shape. Persistence is visible but is not a diagnosis gate. Component histories are assembled from both ranking positions, averaging each component's appearances per trip before fitting a separate projection; primary and secondary estimates are then annotated independently. Histories remain deduped on trip + window. Expected failures exit non-zero with a single `ERROR: <message>` line on stderr and no traceback.
10. **Verdict forwarding** — with `--proxy-decisions`, the two problem types we do not score carry the data team's already-computed verdict instead of a hard zero. **This is relaying, not scoring:** we compute none of their decision logic, we map their result onto our score and confidence fields and record where it came from in `notes`.

**Exact runtime enum:** `cooling_degradation`, `air_intake_maf_anomaly`, and `accelerator_pedal_sensor` are Model-scored; `intake_air_temperature_sensor_fault` and `map_load_signal_plausibility_fault` are Data-scored and Model-forwarded. The retired throttle and idle candidates are not runtime values.

**Contract v1.6 added optional `secondary_risk` without changing the established top-level primary fields.** Older consumers can continue reading the primary result, while updated consumers can retain evidence for a second component.

## Deep Dive: TTM Architecture

- **What it is:** Granite TTM ["Tiny Time Mixer", `ibm-granite/granite-timeseries-ttm-r2`] is a small, pre-trained time-series forecasting model from IBM — millions of parameters, not billions, so it runs on an ordinary laptop CPU. It is *not* a language model: it's built from lightweight mixing layers [TSMixer-style MLP blocks] specialised for numeric sequences.
- **How zero-shot works:** TTM was pre-trained on large public collections of time series, learning reusable temporal patterns such as trends and cycles. "Zero-shot" means applying those weights directly to the engine signals with no KIT-specific training, using 512 input steps and 96 forecast steps.
- **Configuration boundary:** the shipped zero-shot model and official epoch-five artefact both use TTM's `common_channel` path with forecast-channel mixing disabled. Shared weights forecast each of the six signals independently; the backbone does **not** learn MAP--MAF or pedal-channel correlations. Those relationships are interpreted downstream through engineered physical evidence.
- **Why residuals detect anomalies:** the model learns plausible temporal continuation. If what happens next differs, prediction error becomes anomaly evidence. Extra healthy-only training reduced held-out forecast MAE by 5.2%; whether that improves fault detection is a separate question answered by the synthetic campaign, not by MAE alone.
- **Where forecast quality and detection quality part company:** a lower prediction error improves the baseline the detector works from, but it does not automatically improve detection of every fault. Fine-tuning reduced overall error with five of six signals no worse, yet MAF detection stayed near zero because that fault's signature was barely visible in the forecast error. Two connected measures, two different evaluation criteria — worth saying if a marker conflates them.
- **Channel-mixing ablation:** an opt-in forecast-channel mixer made one signal's forecast respond to another, but it worsened held-out overall MAE from 54.9666 to 55.6532 and mean cross-signal correlation error from 0.4366 to 0.5311 across the same 250 validation windows. We rejected it and did not replace or recalibrate the official common-channel model. This is a development-set ablation, not an independent final test.

## Limitations

- **Strong planted-fault performance does not guarantee real fault detection.** Our faults are simple, sudden changes [scale/offset perturbations]; real degradation is gradual, noisy, and messier. Our "correct answers" are stand-in rules, not verified mechanical failures.
- **One car, one driver.** Everything — the healthy baseline, the alarm levels — is calibrated on a single vehicle's data. No evidence it transfers to another car without re-calibration.
- **Coverage is partial, and the split is by evidence type.** Five problem types are executable on this dataset; we score three. The other two are decided by the data team's rule pipeline, which already produces a verdict for all five — so building our own scoring for those two would have duplicated an existing decision path rather than adding capability. That division also matches the methods: our approach finds *gradual drift* away from a prediction, while both of those faults are a sensor getting *stuck*, which a "hasn't changed in two minutes" rule tests for directly. For intake air temperature there's a hard boundary on top of that — it isn't one of the six channels the model forecasts, so no residual exists for it at all. **Don't claim we proved the method can't do it:** we never ran a clean test of residual detection on those two, because the scoring was retired before one existed.
- **MAF detection is inadequate by our own measurement** — recall 0.045. Fixing it needs different evidence or different scoring logic, not a different alarm threshold, and we say so rather than reporting only the macro average.
- **One healthy stretch still alarms at maximum risk.** In the calibration hold-out, one of three healthy segments scores 1.0, and no threshold at or below 1.0 removes it without disabling all detection. That's why the published alarm policy is marked provisional.
- **The failure projection is not a remaining-useful-life model.** It assumes risk continues in a straight line. Real degradation plateaus, recovers, jumps, or depends on maintenance. A genuine RUL model needs labelled degradation-to-failure histories, which we don't have.
- **Repeated windows do not currently confirm persistence.** Batch mode retains every window so a sequence can be inspected, while the current diagnostic summary simply selects the highest-risk window. Only the Story 8 estimator aggregates window scores into trip means and fits a longer-term trend.
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

**Direct answer:** Rules are good at testing declared physical boundaries; TTM adds a different question: given the recent history, did the next 96 seconds continue as expected? That temporal forecast error gives us evidence independent of the proxy labels. We did not measure real mechanical lead time, so do not claim the model proved earlier warning.

Supporting points (pick 2–3):

1. **Forecast error supplies continuous evidence.** The final risk score combines residual and physical evidence; its history can be projected, but the projection is of the score crossing the High line, not time until a mechanical failure.
2. **"Normal" depends on the driving situation.** One fixed limit must survive city, motorway and warm-up at once — loose enough to never false-alarm on the motorway means missing real problems at idle. The model conditions "normal" on the last 8.5 minutes of actual driving.
3. **Cross-signal relationships are handled explicitly downstream.** The official TTM configuration forecasts each signal independently through shared weights; it does not learn channel correlations. Engineered features compare airflow with pressure and engine speed, and compare the two pedal channels.
4. **We reduce circularity.** TTM never receives the proxy type or DTC as a training target. Physical attribution still uses declared features and the evaluation is synthetic, so this is partial independence rather than perfectly independent ground truth.

**Honest concession (say it):** We also use physically grounded scoring for attribution because forecast error alone cannot name a component. The result is a hybrid research detector, not proof that TTM predicts a real fault before a physical rule could see it. *(If pushed: the brief lists "train a model to predict component failure" as a Must.)*

### ★ Isn't your JSON output too deterministic — it names one definite anomaly type?

**Direct answer:** The top-level name is the strongest candidate, not an unqualified diagnosis. Contract v1.6 carries its risk score and confidence and also exposes the complete second-ranked distinct component in `secondary_risk`, with its own score, level, confidence, evidence, provenance, and estimate fields. *[risk_score, prediction_confidence, secondary_risk; INTERFACE.md v1.6]*

Supporting points:

1. **The type only means something together with its score.** We score all five types, expose the top two, and retain Low results as weak evidence rather than diagnoses. *[stable five-type ranking → primary + secondary]*
2. **Deterministic in the other sense is deliberate.** Same input always gives the same output — that's reproducibility, so any result can be re-run and audited. The real question is whether uncertainty is *expressed*, and that's what the score and confidence fields are for.

**Honest concession (say it):** v1.6 fixed the loss of the second candidate, but it exposes only the top two of five scores. Lower-ranked evidence is not returned, the component families are predefined, and we still have no real multi-fault validation. The ranked output represents model evidence, not proof that two mechanical faults are present.

### Q1. Why a forecasting model instead of training a fault classifier?

A classifier needs verified fault examples to learn from and we have none — the corpus is ordinary driving with no mechanically verified failure or repair outcomes. A prediction model can instead learn a normal-operation baseline; departures show up as forecast error. It also works straight out of the box, which let two beginners get the whole pipeline running before any training. *[zero-shot TTM]*

### Q2. How do you know it works with no real faults?

We plant controlled synthetic changes in a quality-gated ordinary-driving baseline — because we applied them, we know the expected family. Fourteen perturbation settings at varying strength: engine-temperature offsets of +5, +10, +15 °C; airflow under-reads at 95%, 90%, 80%, 70% of true; and pedal changes as one-channel offsets of 2, 5, 10, 20 percentage points plus gain errors of 1.05, 1.10, 1.20. Each runs over 11 usable held-out stretches, giving 154 injected cases. A separate intake-pressure ×1.25 attribution control and 11 unchanged controls are excluded from that 154-positive denominator. Upfront limitation: this proves response to artificial changes, not real breakdowns. *[synthetic injection; precision/recall]*

### Q3. What is a "proxy failure condition"?

A stand-in definition of failure based on known engine behaviour — e.g. once warmed up, the engine's cooling liquid should sit around 90–95°; past ~100°, or still climbing when it should level off, counts as our stand-in for a cooling problem. Every rule has a written physical justification — a team rule in our shared contract.

### Q3a. Isn't the "no labels" problem the Data Layer's challenge?

Creating the stand-in rules and decision outputs is Group 1's job, and we don't claim it. The fine-tuning split does **not** use a proxy-label file: it relies on the dataset's ordinary-driving status plus a segment-quality gate. The formal detection answer key comes from our controlled injection harness, while Group 1's decision file is used for forwarding the two Data-scored types. None of those proxy decisions is a mechanically verified fault label.

### Q3b. If the car passed health validation, what are the labels even for — what is there to label?

The Data Layer's verdicts are *computed, not discovered*: its rules turn physical plausibility, duration, and supporting evidence into `proxy_decisions.csv`. Those results make all five runtime types executable and let us forward the two types we do not score. They are still engineering proxies, not verified negatives or proof that the training set is mechanically fault-free. Our formal Model evaluation therefore uses traceable synthetic changes with known expected families rather than treating Data's own rule output as independent ground truth.

### Q4. Why train only on healthy data?

The model's job is to learn ordinary continuation. Training on known faulty trajectories could teach it to forecast the fault and shrink the gap. Our corpus contains ordinary driving only, and the split also removes low-quality segments. Measured on 12 held-out trips, extra training cut forecast error by 5.2%; whether faults stand out is assessed separately by the synthetic detector evaluation. *[healthy-only fine-tuning, Story 6; 49 training segments across 47 trips / 12 validation segments and trips; trip-disjoint split]*

### Q5. Why 8.5 minutes in, 1.5 minutes out?

The model's built-in window lengths — at one reading per second, 512 in and 96 out; enough to cover warm-up and steady driving. It also set a requirement we negotiated with the data team: each unbroken recording stretch must have at least 700 rows and pass the quality gate. The committed split retains 61 of 118 segments across 59 trips.

### Q6. How does this become "N% probability within X trips"?

For each component, we average the windows where it appears in either the primary or secondary position, so one noisy window cannot swing a whole trip. We fit a separate straight line through each component's chronological trip averages. If it is rising, the number of trips left is how far the latest score sits below the High line, divided by the per-trip rise: `ceil((0.9 − latest) / slope)`. The probability is the chance that fitted line has crossed 0.9 ten trips from now, under a normal error model around the fit.

It refuses to invent a cycle estimate: with fewer than five trips, both fields are `null`; if the latest risk is already at least 0.9, the result is zero cycles and probability 1.0. A flat or falling trend, or a projected crossing more than 50 trips away, makes only the cycle estimate `null`—the ten-trip threshold-crossing probability is still returned.

**Say this plainly if asked about the viva case:** the slide uses 22 real Model windows from six chronological Seat Leon trips. Their trip-level mean risks happen to produce a rising fitted line, but all source trips are ordinary driving and there is no validated failure event. Five trips and `0.7502` project *our risk score* crossing 0.9; they are not remaining useful life or a calibrated probability that the car breaks. The separate committed contract sample uses a hand-built rising history and returns four trips / `1.0`; it is not shown as the viva case. *[Story 8; `failure_estimation.py`; High threshold 0.9]*

### Q7. What happens with bad input data?

Two levels: missing/non-numeric required columns stop with a clear error — bad data never reaches the model silently. Physically impossible values are repaired with a note, or the file rejected if too much is affected. Merely *unusual* values pass untouched — otherwise the checks would delete the anomalies we're looking for. Separately, the file's own contract is enforced before anything else: one reading per second on every row, and the expected schema and calibration versions — a mismatch stops the run, because a file that isn't what it claims to be will produce confident nonsense downstream. *[two-tier validation; >5% rejection; notes field; contract assertions on `dt_seconds`/`schema_version`/`calibration_version`/operating-state form]*

### Q8. Why were fault types removed?

Two were, both on evidence, both recorded as documented scope decisions rather than quiet omissions. The first needed a reliable reading of the valve letting air into the engine, but in this dataset that reading is stuck at maximum most of the time — the fault can't be judged from this data. The second was about the engine's idle-speed control: nothing in the data tells us what idle speed the car was *aiming* for, and healthy idle legitimately sits at several different speeds, so there's no stable "normal" to compare against. Each time the data team made the call, the change went into the shared contract and both teams cleaned code in step — the fault list went from seven candidates to five executable ones. *[electronic_throttle_tracking_fault, tps saturation, 2026-07-13; idle_speed_control_or_surge_degradation, 2026-07-19]*

### Q9. How do you avoid false alarms?

We measure "normal wrongness" on healthy data itself and trigger only clearly above it, and the boundary is picked by a written rule, not by taste: sweep candidate alarm lines, keep the one that detects the most, subject to no more than one false alarm in ten healthy trips. That gave 0.41 for the alarm line and 0.9 for High. Calibration was performed on the official epoch-five evaluation checkpoint after training changed its residual scale; it does not calibrate the separate zero-shot model loaded by the shipped detector.

The measured effect: false alarms on healthy driving fell from three-in-eleven to one-in-eleven, while overall detection quality barely moved. **Say the cost too:** it did that partly by suppressing weak pedal detections, so it's a trade-off, not a free win. **And the honest one:** one held-out healthy stretch still scores maximum risk, and no threshold at or below 1.0 removes it without switching detection off entirely. That's why the policy is published as provisional. *[thresholds 0.4129 / 0.9, `risk_level_calibration.v1.json`, status `provisional_synthetic_only`; Story 7]*

### Q10. Hardest cross-team problem?

A unit mix-up: one measurement delivered as change per *second* while our documents said per *minute* — a silent sixty-times error if unnoticed. Caught in contract review; alarm levels rescaled. That's why the shared format is version-numbered and never changed casually. *[coolant_slope °C/min → °C/s. Historical — that column was later replaced in the schema rewrite, so don't offer it as a live example.]*

A current one, if you want something still in the codebase: verifying the data team's decision file end-to-end, we found we'd attributed two diagnostic trouble codes to the wrong fault type in our own notes and in the shared contract — both actually belong to the cooling family. We corrected both documents. The point worth making is that the verification work caught our own error, not just theirs. *[GL-366; P0116/P0128 → cooling_degradation; corrected 2026-08-01]*

### Q11. What are the two problem types you don't score?

**Direct answer:** they are the intake-air-temperature sensor fault and the MAP/load plausibility fault [`intake_air_temperature_sensor_fault`, `map_load_signal_plausibility_fault`]. They are not unfinished work: the Data Layer computes their decision paths, and the Model Layer validates and forwards those verdicts into the shared five-type output.

The split also follows the available evidence. Their direct paths include no-response and hard-stuck checks, cold-start or physical plausibility, and MAP--MAF arbitration. A flat stuck signal can be easy to forecast, and intake-air temperature is not one of our six forecast channels at all. Direct persistence and plausibility logic is therefore clearer than duplicating it as another residual score. Do not reduce both types to "stuck sensors," because each has additional executable paths.

As of the final sprint our output *relays* their verdict rather than reporting a hard zero, so the dashboard sees a real answer for all five types. **That's relaying, not scoring** — we compute none of their logic and we don't claim their result as ours.

**If pushed on evidence, concede this cleanly:** we can't claim we *proved* the residual method fails on those two. We did run them through the injection harness early on and they scored no differently from healthy — but that was before any scoring existed for them, so the detector was returning zero by construction. It shows the absence of an implementation, not the limit of the method. The argument for the split is the reasoning above and the ownership decision, not that measurement. *[`--proxy-decisions` forwarding; pre-scoring baseline sweep, 2026-07-18]*

### Q12. With more time?

Test on an external dataset with mechanically verified fault labels; use the Data Layer's proxy decisions for integration evidence, not as a substitute for real ground truth; redesign the airflow evidence; promote the fine-tuned model into the shipped pipeline; design gradual, realistic fault injections instead of sudden step changes; and try a second vehicle's data to test transfer.

### Q13. Which model produced those evaluation numbers — the one you ship?

**Answer straight, don't dodge:** no. The evaluation ran on the fine-tuned model; the pipeline as it stands still loads the out-of-the-box one. Wiring the fine-tuned checkpoint into the detector is a small change we haven't made yet, so the honest statement is "the detection numbers describe the fine-tuned model, and promoting it into the pipeline is outstanding work." The forecasting improvement (5.2%) and the detection results both come from the same fine-tuned artefact, so they're consistent with each other — they just describe the better model rather than the shipped one.

*(If this gets fixed before the viva, delete this and say the pipeline runs the fine-tuned model.)*

### Q14. How does the dashboard actually consume this?

One command per uploaded file. In batch mode we sweep every window and return the highest-primary-risk window as `summary` plus the full per-window list. Each result preserves the top-level primary fields and can include a complete `secondary_risk`; component-specific estimates are built from both positions. The dashboard and report can therefore retain a Medium or High candidate even when it ranks second. Failures come back as one plain `ERROR:` line and a non-zero exit, never a stack trace, because whatever we print on the error channel is what the user sees.

**Integration status (this was an open gap until 2026-08-02, now closed):** the upload path passes both of the data team's outputs through to us — the feature file and the decision file — so verdict forwarding does activate in a live demo, and the dashboard sees a real answer for all five problem types. *[`dashboard/csv_pipeline.py` appends `--proxy-decisions`; GL-398 `e4d4443`, GL-399 `cd01115`. If asked what changed: the orchestrator used to hand us the feature file alone.]*

### Q15. Why is the airflow fault detected so poorly?

Because the fault we planted is a *proportional* under-read — airflow reads 90% of true, say — and the model's airflow forecast was never tight enough for a 10% shift to stand out against ordinary driving variation. The prediction error moves, but not past where healthy driving already sits. That's a mismatch between the fault's signature and the evidence we're measuring, so a stricter alarm doesn't help — you'd just lose the other two fault types. The fix is different evidence: compare measured airflow against the independent pressure-and-speed estimate directly, which is what the data team's rule does, rather than routing it through forecast error. We report the number as it is [recall 0.045] because a macro average would have hidden it.

### Q16. Does TTM learn relationships between the six engine signals?

**Not in the official configuration.** The shipped zero-shot model and the official epoch-five model both use TTM's common-channel path: the same weights are reused across signals, but each signal is forecast independently. MAP--MAF consistency and pedal-channel agreement are added later through engineered physical features; do not say the backbone learned those correlations.

We tested TTM's optional forecast-channel mixer as a development ablation. It did make the airflow forecast respond when another channel changed, proving cross-signal dependence entered the path. But on the same 250 held-out windows it worsened overall MAE from 54.9666 to 55.6532, worsened every signal relative to the official fine-tuned model, and increased mean correlation error from 0.4366 to 0.5311. We therefore kept the common-channel model and did not rerun calibration or synthetic detection on the rejected mixer. *[`notes/2026-08-05-channel-mixing-experiment.md`; opt-in mixer added in `20aa335`]*

### Questions to be careful with

- **"What's your detection accuracy?"** — Don't give one number; there isn't an honest one. Give it per fault type — overheating perfect, pedal precise but insensitive to small faults, airflow near zero — and immediately scope all of it: measured on planted faults, not real breakdowns.
- **"Deployable to a real car?"** — No; the brief explicitly rules out real-time vehicle integration. Offline pipeline over recorded trips.
- **"Did it predict any real failures?"** — No; none of the 81 ordinary-driving trips has a mechanically verified fault, repair outcome, or observed failure event. Keep everything framed as proxy definitions and planted-fault testing.
- **"How many tests pass?"** — The fresh 2026-08-10 Model run is 209 passed, 16 skipped, three warnings across 225 collected tests. The viva backup nodes now use the same result.
- **"Does 75.02% mean the car will fail?"** — No. The viva case uses 22 real Model windows from six ordinary Seat Leon trips. Five trips is the fitted point where their risk-score trend reaches 0.9; `0.7502` is the fitted probability of crossing that score within ten trips. It is not a probability of mechanical failure. If asked about the separate committed contract sample, its four trips / `1.0` values come from a deliberately rising synthetic history and have the same threshold-only meaning.
