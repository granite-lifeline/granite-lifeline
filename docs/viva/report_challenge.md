# Challenge 3: Grounded Language Generation

**Speaker:** Charlotte Yu, Jintong He
**Time:** ~2 minutes
**Transition in:** "We had a risk score — but a number means nothing to a car owner."
**Transition out:** "So how do we know our reports are actually accurate?"

---

## Why This Challenge Is Specific to This Project

- **A risk score is useful to the system, but not to a normal car owner.** The user needs to know what is happening, how urgent it is, and what to do next — a number on its own answers none of that.
- **Generic LLM text is risky in this domain because it can hallucinate a mechanical cause, or word a prediction so confidently it reads as a confirmed fault.** In a diagnostic tool, an invented cause is not a cosmetic error — it can send an owner to fix the wrong thing or ignore a real one.
- **The report must be grounded, cautious, and actionable at the same time.** It has to use the current sensor evidence, avoid unsupported claims, and stay understandable without any automotive expertise — three constraints a general-purpose chatbot answer does not have to satisfy together.

## Our Solution

- **Model selection was empirical, not assumed.** We compared four Granite models (granite3.3:2b, granite3.3:8b, granite4.1:3b, granite4.1:8b) against a weighted five-dimension rubric (plain language 30%, grounding 25%, JSON reliability 20%, action quality 15%, hedging 10%). granite4.1:8b scored highest overall at 4.85/5.0, giving the strongest balance of JSON reliability, plain language, and useful actions.
- **Before calling Granite, we convert the Model Layer output into a structured context**: component, risk level, risk score, confidence, key signals, failure projection fields, and Model Layer notes — so the LLM only ever reasons over data that actually exists.
- **We use RAG with ChromaDB to retrieve fault knowledge for the predicted anomaly type.** The current contract covers five active anomaly types, stored as section-level documents, so each prompt layer retrieves only the knowledge it needs.
- **Generation is split into a three-layer prompt chain**: Layer 1 explains what the data shows, Layer 2 explains possible causes, and Layer 3 returns 2–4 recommended actions — each layer is a separate, independently validated JSON call.
- **Prediction confidence controls certainty of wording**, not just content: high confidence allows stronger language, while low confidence forces careful phrases such as "may indicate" and "could suggest."

## Why Our Approach Is Better Than Alternatives

- **RAG is safer than fine-tuning the language model for this project.** Our automotive knowledge base can be inspected, updated, and traced back to a source document, while fine-tuning would bury that knowledge inside model weights and require far more labelled diagnostic text than we have.
- **A three-layer prompt chain is more controllable than one large prompt.** It stops the model from mixing observation, cause, and action into one blended answer, and lets us validate each JSON output separately rather than accepting or rejecting an entire report at once.

## Evaluation

- **Earlier RAG vs baseline evaluation used three fixed cooling-system scenarios**: a typical high-risk case (102°C, 87% confidence), an atypical medium-risk case (93°C — normal — but anomaly flagged, 51% confidence), and a contradictory low-risk case where coolant temperature was abnormal (108°C) but the risk level was Low (31% confidence).
- **Overall result: the RAG-enhanced pipeline scored slightly higher than baseline, 0.95 vs 0.93 average.** Both pipelines scored a perfect 1.00 on factual grounding in all three scenarios, meaning both correctly used the risk score, confidence, and sensor values from the input context — RAG's gain came from elsewhere, not from fixing a grounding problem.
- **RAG's main benefit was in low-confidence and mixed-signal cases.** It scored 1.00 on hedging appropriateness in both the atypical and contradictory scenarios, versus 0.60 for baseline. This matters directly for the challenge above: the report must not present a low-confidence prediction as a confirmed mechanical fault.
- **We also compared metadata-filtered retrieval against semantic vector search.** Metadata filtering achieved 100% retrieval accuracy and was roughly 180x faster than semantic search, supporting the design choice: the Model Layer already provides a confirmed `anomaly_type`, so an exact metadata lookup is more reliable than a similarity search that can retrieve the wrong fault's knowledge. *(That comparison was run before the Data Layer retired two anomaly types from the executable enum — see Limitations.)*
- **Honest limitation: our evaluation is partly automated and keyword-based.** It can check factual grounding, readability, hedging, and actionability at scale, but it cannot fully replace review by an automotive domain expert. The system should be presented as a decision-support tool, not a confirmed mechanical diagnosis.

## References

- Huang et al. (2025) — Explains hallucination risks in large language models, supporting our use of RAG and structured context to keep Granite-generated reports grounded.
- Qi et al. (2025) — Discusses how large language models can support fault diagnosis, providing background for using Granite to generate diagnostic explanations.
- Bello et al. (2025) — *A Three-level Framework for LLM-enhanced Explainable AI: From Technical Explanations to Natural Language* — supports our approach of translating technical prediction outputs into user-friendly natural language.
- Qu et al. (2026) — *Explainable AI for remaining useful life prediction in industrial systems: a survey* — supports the need to explain predictive-maintenance results rather than only showing a risk score.
- Michailidis et al. (2025) — *A Review of OBD-II-Based Machine Learning Applications for Sustainable, Efficient, Secure, and Safe Vehicle Driving* — supports the use of vehicle sensor data for fault prediction and driver-facing diagnostics.

## Visuals

1. **Diagram 1 (core).** Model Layer risk score → context injection → ChromaDB fault knowledge retrieval → three-layer Granite prompt chain → owner-friendly diagnostic report.
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
- **Report accuracy is bounded by the accuracy of the upstream risk score and anomaly type.** The Report Layer never sees raw sensor data or the Data Layer's proxy rules — it only reasons over the Model Layer's already-computed classification. If that classification is wrong, the report will narrate the wrong story fluently and confidently; the Report Layer has no independent way to catch that.
- **The automated evaluator is keyword-based and has known blind spots.** It penalised the baseline for the negated phrase "no confirmed fault yet" as if it were overconfident, and penalised RAG's specific thermostat-check wording for lacking urgency words despite being more actionable in content. Both cases needed manual review to interpret correctly — automated scoring cannot fully replace a domain-expert read.
- **The retrieval-method comparison (100% accuracy, ~180x speed advantage) predates the Data Layer's schema-v1 retirement of two anomaly types** (`electronic_throttle_tracking_fault`, `idle_speed_control_or_surge_degradation`). Metadata-filter retrieval is an exact-match lookup, so shrinking the collection to five types should not change the accuracy result — but the timing/accuracy numbers have not been re-measured on the current five-type knowledge base, only asserted by extension.
- **`estimated_failure_probability` / `estimated_cycles_to_failure` are null for every report today**, because the Model Layer's trend estimator (Story 8) is not yet implemented. The prompt correctly refuses to invent these values rather than guessing, but this means the brief's "N% probability within X trips" phrasing cannot appear in any report yet — the gap is currently a missing feature, not just a hedging choice.

---

## Q&A Bank

**Answer technique:** direct answer (one sentence) → one concrete fact/number → honest limitation. Never bluff a number.
**Who fields what:** Charlotte Yu / Jintong He — either can take model/RAG questions or dashboard-integration questions.
**Note:** none of these have been asked by the supervisor yet — update with ★ markers after the first practice run, following the other two groups' convention.

1. **Why did you pick Granite over other LLM families (GPT, Claude, etc.)?**

> We compared four Granite model sizes empirically rather than assuming bigger is better — granite3.3:2b, granite3.3:8b, granite4.1:3b, granite4.1:8b — across a weighted five-dimension rubric, and granite4.1:8b won at 4.85/5.0 with granite4.1:3b as a documented fallback at 4.55/5.0. *(If pushed on why the comparison set was Granite-only rather than including non-IBM models, defer to the project brief / IBM sponsorship constraint — confirm the exact wording with the team before the viva.)*

2. **Why RAG instead of fine-tuning the LLM on automotive knowledge?**

> Fine-tuning would bury our fault knowledge inside opaque model weights and need far more labelled diagnostic text than we have. RAG keeps that knowledge in an inspectable, updatable ChromaDB collection — validated by our retrieval comparison, where exact metadata lookup hit 100% accuracy and was about 180x faster than semantic search. Honest limitation: that specific comparison was run before two anomaly types were retired, so it hasn't been re-measured on today's five-type collection.

3. **How do you know your reports are accurate without a domain expert reviewing every one?**

> We use an automated four-dimension evaluator — factual grounding, readability, hedging appropriateness, actionability — run against three fixed scenarios. RAG averaged 0.95 versus baseline's 0.93, with both hitting a perfect 1.00 on factual grounding. Honest limitation: it's keyword-based, so it can misjudge nuance — it wrongly flagged a negated phrase ("no confirmed fault yet") as overconfident, which manual review caught but automated scoring alone would not.

4. **If the overall RAG score is barely higher than baseline (0.95 vs 0.93), what's the real benefit?**

> The averages are close, but the improvement concentrates exactly where it matters: low-confidence and contradictory cases, where RAG scored 1.00 on hedging versus baseline's 0.60. Honest limitation: RAG actually scored lower in the high-risk scenario (0.85 vs 1.00) because a retrieved snippet leaked the raw field name `coolant_temp` into the output — grounding introduced a wording regression that still needs a prompt fix.

5. **Why a three-layer prompt chain instead of one prompt?**

> It keeps observation, cause, and action independently generated and validated as separate JSON objects, so the model can't blend "what's happening" with "what to do" into one unstructured answer, and a bad layer can be retried without discarding the whole report. Honest limitation: three sequential LLM calls means three times the latency and three separate chances for a JSON-parse failure per report versus one call — the pipeline covers this with per-layer retries, but it is a real complexity cost versus single-shot generation.

6. **What happens with the "N% probability of failure within X trips" feature the brief asks for?**

> The prompt is hardened to never invent a probability, date, mileage, or cycle count when those Model Layer fields are null. Right now they are null in every report, because the Model Layer's trend estimator (Story 8) isn't built yet — so the report correctly says nothing rather than guessing, but that also means this specific client-facing feature doesn't exist yet, not just that it's hedged.

7. **Does the LLM ever see raw sensor data or the Data Layer's proxy rules?**

> No — it only sees the Model Layer's already-computed output (risk score, key signals, notes) formatted as plain-text context; RAG retrieval is keyed on `anomaly_type` and `risk_level` metadata, never on raw signals. Honest limitation: this means report quality is entirely dependent on the Model Layer's classification being correct — the Report Layer has no independent way to catch an upstream misclassification.

8. **What's the path to production — is this running on Ollama forever?**

> Development runs on local Ollama serving granite4.1:8b; the plan is to migrate to IBM watsonx.ai for production, with authentication, rate limiting, and monitoring still open work. Honest limitation: none of the evaluation numbers above have been re-verified against a watsonx.ai-hosted model — they are all measured on local Ollama.

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
