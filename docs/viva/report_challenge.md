# Challenge 3: Grounded Language Generation

**Speaker:** Charlotte Yu, Jintong He
**Time:** ~2 minutes
**Transition in:** "We had a risk score — but a number means nothing to a car owner."
**Transition out:** "So how do we know our reports are actually accurate?"

---

## Why This Challenge Is Specific to This Project

- **A Model Layer output is a JSON object — `risk_score`, `anomaly_type`, `key_signals`.** On its own, a car owner cannot tell what is actually happening, how urgent it is, or what to do about it. Those numbers need a translator into plain language, not just a template — which is exactly why this stage needs an LLM at all, not a simple report generator.
- **Generic LLM text is risky in this domain because it can hallucinate a mechanical cause, or word a prediction so confidently it reads as a confirmed fault.** In a diagnostic tool, an invented cause is not a cosmetic error — it can send an owner to fix the wrong thing or ignore a real one.
- **The translation has to be grounded, understandable, and actionable at the same time.** It has to use the current sensor evidence, stay readable without any automotive expertise, and end in something the owner can actually do — three things a general-purpose chatbot answer does not have to satisfy together.

## Our Solution

Two design decisions carry almost the whole story; everything else supports one of them.

1. **Base architecture: a three-layer prompt chain, not one prompt.** Layer 1 explains what the data shows, Layer 2 explains the possible cause, Layer 3 returns 2–4 concrete recommended actions — each generated and validated as its own JSON object. This single structural choice already buys two things at once: an owner reads three short, separated answers instead of one blended paragraph (**understandable**), and "what to do" gets its own dedicated, format-enforced slot instead of being an afterthought (half of **actionable**).
2. **Grounding: RAG retrieval over a curated fault-knowledge base (ChromaDB).** Layers 1–2 retrieve description-and-causes; Layer 3 retrieves risk-level-specific action guidance — all keyed by the Model Layer's already-confirmed `anomaly_type` via an exact metadata match, across five active anomaly types. This is what stops "possible cause" and "recommended action" from being the model's own guess (**credible**), and it's what turns Layer 3's action slot into specific, technically grounded steps instead of generic advice (the other half of **actionable**).
3. **Certainty control: `prediction_confidence` drives wording strength, not just content.** High confidence allows clearer, more definite language; low confidence forces hedged phrases such as "may indicate" and "could suggest." This supports both **credible** (never overclaiming past what the evidence supports) and **understandable** (the owner's sense of urgency matches the model's actual certainty).
4. **Guardrails live inside the prompt itself — reinforcing mechanisms 1–2, not a third mechanism.** Every prompt is hardened to never invent a missing failure-projection value (probability, date, mileage, cycle count), and to treat Model Layer notes as data-quality information only, never as mechanical-fault evidence.
5. **Supporting evidence: the LLM itself was chosen empirically, not assumed.** We compared four Granite models (granite3.3:2b, granite3.3:8b, granite4.1:3b, granite4.1:8b) against a weighted five-dimension rubric (plain language 30%, grounding 25%, JSON reliability 20%, action quality 15%, hedging 10%) — granite4.1:8b scored highest at 4.85/5.0.

**Credible / understandable / actionable are not three things we built — they are three outcomes we check for, produced jointly by mechanisms 1–2.** That mapping is exactly what the Evaluation section below verifies.

## Why Our Approach Is Better Than Alternatives

Both mechanisms above were deliberate choices against the most obvious alternative — this is the defence for each, not a new topic.

- **RAG is safer than fine-tuning the language model for this project.** Our automotive knowledge base can be inspected, updated, and traced back to a source document, while fine-tuning would bury that knowledge inside model weights and require far more labelled diagnostic text than we have.
- **A three-layer prompt chain is more controllable than one large prompt.** It stops the model from mixing observation, cause, and action into one blended answer, and lets us validate each JSON output separately rather than accepting or rejecting an entire report at once.

## Evaluation

Evaluation checks whether mechanisms 1–2 actually delivered the three outcomes above — three lenses on the same RAG-vs-baseline comparison, not three separate tests.

- **Setup: three fixed cooling-system scenarios** — a typical high-risk case (102°C, 87% confidence), an atypical medium-risk case (93°C — normal — but anomaly flagged, 51% confidence), and a contradictory low-risk case where coolant temperature was abnormal (108°C) but the risk level was Low (31% confidence).
- **Credible — verified, no regression.** Both pipelines scored a perfect 1.00 on factual grounding in all three scenarios: every report correctly referenced the actual risk score, confidence, and sensor values from the input context.
- **Understandable — mostly verified, one concrete regression.** RAG's readability matched or beat baseline in two of three scenarios, but dropped to 0.70 in the high-risk case because the retrieved snippet echoed the raw field name `coolant_temp` instead of "coolant temperature" — a specific, fixable failure of the grounding mechanism leaking into plain-language output.
- **Actionable — real, and it shows the mechanism-dependency we flagged.** RAG's actionability also dropped to 0.70 in that same high-risk scenario — not for being vague, but for lacking urgency wording ("soon") despite giving a more technically specific action (checking the thermostat at ~82°C) than baseline's generic "see a mechanic soon." Actionability moved together with readability because both come from the same retrieved content: it inherited RAG's weakness in that scenario rather than failing independently.
- **Where RAG won clearly: hedging in low-confidence cases.** RAG scored 1.00 on hedging appropriateness in both the atypical and contradictory scenarios, versus 0.60 for baseline — directly from the confidence-driven certainty control (mechanism 3).
- **Overall: 0.95 (RAG) vs 0.93 (baseline)**, a modest but consistent edge concentrated exactly where grounding matters most — low-confidence and contradictory cases.
- **Retrieval comparison: metadata-filtered exact match hit 100% accuracy and was roughly 180x faster than semantic search** — supporting mechanism 2's design choice: since `anomaly_type` is already confirmed by the Model Layer, an exact lookup beats a similarity guess that could retrieve the wrong fault's knowledge. *(That specific comparison predates the Data Layer's retirement of two anomaly types from the executable enum — see Limitations.)*
- **Honest limitation: the evaluator is automated and keyword-based.** It can score grounding, readability, hedging, and actionability at scale, but it misjudges nuance in both directions (see Limitations) and cannot fully replace review by an automotive domain expert.

## References

- Huang et al. (2025) — Explains hallucination risks in large language models, supporting our use of RAG and structured context to keep Granite-generated reports grounded.
- Qi et al. (2025) — Discusses how large language models can support fault diagnosis, providing background for using Granite to generate diagnostic explanations.
- Bello et al. (2025) — *A Three-level Framework for LLM-enhanced Explainable AI: From Technical Explanations to Natural Language* — supports our approach of translating technical prediction outputs into user-friendly natural language.
- Qu et al. (2026) — *Explainable AI for remaining useful life prediction in industrial systems: a survey* — supports the need to explain predictive-maintenance results rather than only showing a risk score.
- Michailidis et al. (2025) — *A Review of OBD-II-Based Machine Learning Applications for Sustainable, Efficient, Secure, and Safe Vehicle Driving* — supports the use of vehicle sensor data for fault prediction and driver-facing diagnostics.

## Visuals

1. **Diagram 1 (core) — two mechanisms converging on three outcomes.** Two boxes on the left, "Three-layer prompt chain" and "RAG fault-knowledge retrieval (ChromaDB)", each with an arrow into the middle labelled with what it contributes; both converge into three outcome labels on the right — Credible, Understandable, Actionable — with Actionable shown fed by *both* boxes (not a third independent box) to make the mechanism-dependency point visually, not just verbally.
2. **Diagram 2 (Evaluation visual).** A side-by-side baseline vs RAG table showing overall score, hedging score, and one example of generic advice versus a more grounded recommended action.
3. **Optional small UI visual.** Dashboard detail page showing risk score, failure projection, key signals, diagnostic report, and data-quality notes.

---

## BACKUP SECTION

### (For Q&A — not on main slides)

### Full Pipeline Detail

1. The Model Layer sends a `ModelLayerOutput` object containing `timestamp`, `anomaly_type`, `component`, `risk_score`, `risk_level`, `prediction_confidence`, `key_signals`, failure projection fields, and `notes`.
2. Context injection converts the raw fields into readable prompt context. For example, `risk_score` becomes a percentage, raw signal names are mapped to owner-readable names, and each key signal is marked NORMAL or ABNORMAL against its reference range.
3. Failure projection fields are included only when the Model Layer provides real values. If `estimated_failure_probability` or `estimated_cycles_to_failure` is null, the prompt explicitly forbids inventing a probability, date, mileage, or cycle count.
4. Model Layer notes are passed through as data-quality information, not as mechanical causes. This stops the LLM from treating a repaired input value as proof of a fault.
5. RAG retrieval uses the predicted anomaly type as an exact metadata key. Description and causes are retrieved for Layers 1 and 2; risk-level-specific action guidance is retrieved for Layer 3.
6. Certainty guidance is generated from `prediction_confidence`. Low confidence instructs Granite to say the evidence is limited; high confidence allows clearer but still non-confirming wording.
7. The three-layer prompt chain returns strict JSON objects — `anomaly_description`, `possible_cause`, `recommended_action` — with per-layer retry logic on timeout or parse failure. The report generator validates and assembles these with the pass-through fields for the Dashboard.

### Deep Dive: RAG vs Baseline Results

| Scenario | Baseline overall | RAG overall | Key interpretation |
|---|---|---|---|
| Typical cooling, High risk | 1.00 | 0.85 | RAG was more technically specific but received a readability penalty because its output kept the raw field name `coolant_temp` instead of "coolant temperature." |
| Atypical cooling, Medium risk | 0.90 | 1.00 | RAG handled low confidence better and used more cautious language. |
| Contradictory cooling, Low risk | 0.90 | 1.00 | RAG used better hedging when an abnormal signal conflicted with a low risk score. |
| **Average** | **0.93** | **0.95** | RAG gave a small but consistent improvement, strongest in low-confidence or mixed-signal cases. |

### Limitations

*(Say the first one unprompted — it's the honest core.)*

- **Neither pipeline explicitly flags a contradictory signal to the owner.** In the contradictory scenario (coolant_temp ABNORMAL at 108°C, risk_level Low), neither the baseline nor the RAG report called out that the raw signal and the risk classification disagree — both wrote around it rather than naming the contradiction. This is a real gap, not just a scoring artefact.
- **Actionability is not an independently engineered outcome — it inherits whatever the prompt chain and RAG grounding produce.** We have not built a dedicated safeguard to protect action quality on its own; when RAG's grounding regressed in the high-risk scenario, actionability regressed with it (0.70), even though the underlying action was more technically specific than baseline's. If we want actionability to be more robust, it needs its own mechanism, not a free ride on the other two.
- **Report accuracy is bounded by the accuracy of the upstream risk score and anomaly type.** The Report Layer never sees raw sensor data or the Data Layer's proxy rules — it only reasons over the Model Layer's already-computed classification. If that classification is wrong, the report will narrate the wrong story fluently and confidently; the Report Layer has no independent way to catch that.
- **The automated evaluator is keyword-based and has known blind spots.** It penalised the baseline for the negated phrase "no confirmed fault yet" as if it were overconfident, and penalised RAG's specific thermostat-check wording for lacking urgency words despite being more actionable in content. Both cases needed manual review to interpret correctly — automated scoring cannot fully replace a domain-expert read.
- **The retrieval-method comparison (100% accuracy, ~180x speed advantage) predates the Data Layer's schema-v1 retirement of two anomaly types** (`electronic_throttle_tracking_fault`, `idle_speed_control_or_surge_degradation`). Metadata-filter retrieval is an exact-match lookup, so shrinking the collection to five types should not change the accuracy result — but the timing/accuracy numbers have not been re-measured on the current five-type knowledge base, only asserted by extension.
- **`estimated_failure_probability` / `estimated_cycles_to_failure` are null for every report today**, because the Model Layer's trend estimator (Story 8) is not yet implemented. The prompt correctly refuses to invent these values rather than guessing, but this means the brief's "N% probability within X trips" phrasing cannot appear in any report yet — the gap is currently a missing feature, not just a hedging choice.
- **The live pipeline currently requires local installation — it is not a zero-setup web experience for a non-technical owner.** The Report Layer calls a local Ollama instance and the Model Layer runs local TTM inference (torch/transformers), so a genuine end user would need to install both before uploading a CSV. We deliberately did not move either off the user's machine: we have no IBM watsonx.ai access, and the project has no budget for a paid hosted LLM (e.g. Replicate, ~$0.0005/report on `ibm-granite/granite-4.1-8b` by rate but still a real recurring cost with no funding source) or a self-hosted server (Ollama's memory footprint for the 8B model does not fit free-tier hosting). This was a considered trade-off given a zero-budget summer project, not an oversight — the public dashboard demo instead shows curated pre-computed sample reports, and the real upload-your-own-CSV pipeline is documented and supported as a local run.

---

## Q&A Bank

**Answer technique:** direct answer (one sentence) → one concrete fact/number → honest limitation. Never bluff a number.
**Who fields what:** Charlotte Yu / Jintong He — either can take model/RAG questions or dashboard-integration questions.
**Note:** none of these have been asked by the supervisor yet — update with ★ markers after the first practice run, following the other two groups' convention.

1. **Why did you pick Granite over other LLM families (GPT, Claude, etc.)?**

> The LLM family itself was set by the client — IBM's brief requires the Granite model family, since IBM sponsors the project. What we chose ourselves is which Granite model: we compared four sizes empirically rather than assuming bigger is better — granite3.3:2b, granite3.3:8b, granite4.1:3b, granite4.1:8b — across a weighted five-dimension rubric, and granite4.1:8b won at 4.85/5.0 with granite4.1:3b as a documented fallback at 4.55/5.0.

2. **Why RAG instead of fine-tuning the LLM on automotive knowledge?**

> Fine-tuning would bury our fault knowledge inside opaque model weights and need far more labelled diagnostic text than we have. RAG keeps that knowledge in an inspectable, updatable ChromaDB collection — validated by our retrieval comparison, where exact metadata lookup hit 100% accuracy and was about 180x faster than semantic search. Honest limitation: that specific comparison was run before two anomaly types were retired, so it hasn't been re-measured on today's five-type collection.

3. **How do you know your reports are accurate without a domain expert reviewing every one?**

> We use an automated four-dimension evaluator — factual grounding, readability, hedging appropriateness, actionability — run against three fixed scenarios. RAG averaged 0.95 versus baseline's 0.93, with both hitting a perfect 1.00 on factual grounding. Honest limitation: it's keyword-based, so it can misjudge nuance — it wrongly flagged a negated phrase ("no confirmed fault yet") as overconfident, which manual review caught but automated scoring alone would not.

4. **If the overall RAG score is barely higher than baseline (0.95 vs 0.93), what's the real benefit?**

> The averages are close, but the improvement concentrates exactly where it matters: low-confidence and contradictory cases, where RAG scored 1.00 on hedging versus baseline's 0.60. Honest limitation: RAG actually scored lower in the high-risk scenario (0.85 vs 1.00) because a retrieved snippet leaked the raw field name `coolant_temp` into the output, and its actionability score dropped in step (0.70) — grounding introduced a wording regression that dragged actionability down with it, because actionability isn't protected independently.

5. **Isn't "actionable" just a label — what did you specifically build for it?**

> Honestly, nothing built specifically for it. Actionability comes from Layer 3's dedicated, format-enforced slot for 2–4 concrete steps, combined with RAG retrieving risk-level-specific action guidance instead of generic advice — the same two mechanisms that produce "understandable" and "credible." Fact: this shows up directly in the evaluation — RAG's actionability score moved together with its readability score in the high-risk scenario, both dropping to 0.70, because both came from the same retrieved content. Honest limitation: we have no independent safeguard for actionability alone, so it rises and falls with the other two rather than being separately protected.

6. **Why a three-layer prompt chain instead of one prompt?**

> It keeps observation, cause, and action independently generated and validated as separate JSON objects, so the model can't blend "what's happening" with "what to do" into one unstructured answer, and a bad layer can be retried without discarding the whole report. Honest limitation: three sequential LLM calls means three times the latency and three separate chances for a JSON-parse failure per report versus one call — the pipeline covers this with per-layer retries, but it is a real complexity cost versus single-shot generation.

7. **What happens with the "N% probability of failure within X trips" feature the brief asks for?**

> The prompt is hardened to never invent a probability, date, mileage, or cycle count when those Model Layer fields are null. Right now they are null in every report, because the Model Layer's trend estimator (Story 8) isn't built yet — so the report correctly says nothing rather than guessing, but that also means this specific client-facing feature doesn't exist yet, not just that it's hedged.

8. **Does the LLM ever see raw sensor data or the Data Layer's proxy rules?**

> No — it only sees the Model Layer's already-computed output (risk score, key signals, notes) formatted as plain-text context; RAG retrieval is keyed on `anomaly_type` and `risk_level` metadata, never on raw signals. Honest limitation: this means report quality is entirely dependent on the Model Layer's classification being correct — the Report Layer has no independent way to catch an upstream misclassification.

9. **What's the path to production — is this running on Ollama forever, and can a non-technical owner actually use it?**

> Today, both AI calls run locally: Ollama serving granite4.1:8b, and the Model Layer's TTM inference (torch/transformers). A genuine zero-install experience for a car owner would mean moving both off the user's machine to hosted services the Dashboard calls over HTTP — we scoped this, including a specific option (Replicate's hosted `ibm-granite/granite-4.1-8b`, the exact model our own evaluation selected, at a genuinely small per-report cost). Honest limitation: we have no IBM watsonx.ai access and this is an unfunded summer project, so we deliberately did not pursue paid hosting — the public dashboard demo shows curated pre-computed reports instead, and the real live pipeline is a documented local run. None of the evaluation numbers above have been re-verified against any hosted model; they are all measured on local Ollama.

### Plain-words glossary

Use the plain phrase first; add the technical word only if the marker asks.

| Don't say | Say instead |
|---|---|
| RAG | "we let the AI look up a written fault-knowledge sheet before it answers" |
| ChromaDB | "the fault-knowledge database" |
| context injection | "packaging the model's numbers into a plain-text briefing for the AI" |
| hallucination | "the AI making up a cause that isn't actually supported by the numbers" |
| metadata-filtered retrieval | "looking up the exact matching knowledge sheet by name" |
| semantic search | "guessing the closest-sounding knowledge sheet" |
| three-layer prompt chain | "three separate questions to the AI: what's happening, why, and what to do" |
| hedging appropriateness | "whether the wording is cautious enough to match how sure we actually are" |
| prediction confidence | "how sure the risk score itself is" |
| factual grounding | "whether the report only talks about numbers that are actually in the data" |
| JSON | "a strict, computer-readable answer format" |
