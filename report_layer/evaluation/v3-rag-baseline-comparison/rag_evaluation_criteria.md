# RAG Evaluation Framework

**Task**: GL-119 (sub-task of GL-118: RAG vs Baseline Evaluation)  
**Project**: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)

## Overview

This framework evaluates diagnostic report quality across four dimensions to compare RAG-enhanced reports (with fault knowledge retrieval) against baseline reports (without retrieval). The evaluation criteria are grounded in academic research on LLM hallucination and the weighted scoring approach used in our model selection process.

**Academic Grounding**:
- Huang et al. 2025 — *A Survey on Hallucination in Large Language Models*
- Qi et al. 2025 — *Large Language Models for Fault Diagnosis*
- ADR 302 — Granite LLM Model Selection (weighted evaluation framework)

**Automated Implementation**: `report_layer/evaluation/report_quality_evaluator.py` (GL-140)

---

## Evaluation Dimensions

### 1. Factual Grounding (0.0–1.0)

**Academic Grounding**: Huang et al. 2025 — *faithfulness hallucination* (model output unfaithful to provided source context)

**Definition**: The degree to which the report content is traceable to specific values in the ModelLayerOutput context. Faithfulness hallucination occurs when the LLM generates content that contradicts or ignores the input sensor data.

**What Counts as Good**:
- Specific signal values cited with units
- Reference ranges provided for context
- All ABNORMAL signals explicitly mentioned
- Quantitative evidence for every claim

**What Counts as Bad**:
- Generic statements without signal values
- Claims not supported by input data
- Ignoring key ABNORMAL signals
- Inventing signal values not in the input

**Scoring Rubric**:
- **0.0–0.3**: No signal values referenced, generic statements only
- **0.4–0.6**: Some signal values mentioned but without reference ranges
- **0.7–0.9**: Specific values and reference ranges cited correctly
- **1.0**: All ABNORMAL signals cited with values, units, and reference ranges

**Examples**:

**Low-Scoring Example** (Score: 0.1):
> "The engine is experiencing some issues."

*Why this fails*: No specific signal values, no reference to input data, completely generic statement that could apply to any vehicle.

**High-Scoring Example** (Score: 0.9):
> "The coolant temperature is 104°C, above the safe range of 90–95°C, and rising at 3.4°C/min, which exceeds the normal rate of 0–2°C/min."

*Why this succeeds*: Cites specific values (104°C, 3.4°C/min), provides reference ranges (90–95°C, 0–2°C/min), directly traceable to ModelLayerOutput.

---

### 2. Readability (0.0–1.0)

**Academic Grounding**: Qi et al. 2025 — plain language requirement for non-technical vehicle owners

**Definition**: The degree to which the report is understandable by a non-technical vehicle owner with no automotive engineering background.

**What Counts as Good**:
- No raw field names (coolant_temp → "coolant temperature")
- Technical terms explained in plain language
- Acronyms expanded on first use
- Sentence structure accessible to general audience

**What Counts as Bad**:
- Raw field names from code (coolant_temp, maf, accel_pedal_d)
- Unexplained acronyms (OBD, ECM, DTC, MAF, MAP)
- Technical jargon without context
- Overly complex sentence structure

**Scoring Rubric**:
- **0.0–0.3**: Multiple unexplained technical terms, raw field names present (coolant_temp, maf, accel_pedal_d), unexplained acronyms (OBD, ECM, DTC, MAF, MAP)
- **0.4–0.6**: Some technical terms explained, some raw field names remain
- **0.7–0.9**: No raw field names, technical terms explained in plain language
- **1.0**: Fully accessible to a non-technical vehicle owner, no jargon

**Examples**:

**Low-Scoring Example** (Score: 0.2):
> "The coolant_temp reading and MAF sensor output suggest ECM intervention may be required."

*Why this fails*: Raw field name (coolant_temp), unexplained acronyms (MAF, ECM), technical jargon ("sensor output", "intervention").

**High-Scoring Example** (Score: 0.9):
> "Your engine cooling system is running hotter than normal. The sensor that measures how much air enters the engine is also showing an unusual reading."

*Why this succeeds*: Plain language throughout, technical concepts explained in accessible terms, no raw field names or unexplained acronyms.

---

### 3. Hedging Appropriateness (0.0–1.0)

**Academic Grounding**: Huang et al. 2025 — *factuality hallucination* (model presents uncertain predictions as confirmed facts)

**Definition**: The degree to which the report uses appropriately uncertain language that does not present model predictions as confirmed mechanical faults.

**What Counts as Good**:
- Hedging phrases: "may indicate", "could suggest", "might be related to"
- Uncertainty calibrated to prediction_confidence level
- Clear distinction between observed symptoms and possible causes
- No claims of confirmed diagnosis

**What Counts as Bad**:
- Confirmed fault language: "the fault is", "has failed", "is broken"
- Overconfident statements: "definitely", "confirmed", "certainly"
- Presenting predictions as mechanical diagnoses
- Ignoring prediction_confidence level

**Scoring Rubric**:
- **0.0–0.3**: Confirmed fault language present ("the fault is", "confirmed failure", "is definitely broken", "has failed")
- **0.4–0.6**: Mixed — some hedging present but some overconfident statements remain
- **0.7–0.9**: Consistent hedging throughout, no confirmed fault claims
- **1.0**: Perfectly calibrated uncertainty language matched to prediction_confidence level

**Examples**:

**Low-Scoring Example** (Score: 0.0):
> "Your cooling system has failed and the water pump is broken."

*Why this fails*: Presents model prediction as confirmed mechanical diagnosis, uses definitive language ("has failed", "is broken"), no hedging.

**High-Scoring Example** (Score: 0.9):
> "This could be related to cooling system stress. Possible causes include low coolant fluid, a blocked radiator, or a worn water pump, though this has not been confirmed."

*Why this succeeds*: Uses hedging ("could be related to", "possible causes"), explicitly states uncertainty ("has not been confirmed"), presents multiple possibilities.

---

### 4. Actionability (0.0–1.0)

**Academic Grounding**: ADR 302 weighted scoring framework — action quality as a key evaluation dimension in model selection

**Definition**: The degree to which the recommended actions are specific, concrete, and appropriately matched to the risk level.

**What Counts as Good**:
- 2–4 specific, concrete actions
- Urgency language matches risk_level (High/Medium/Low)
- Vehicle owner knows exactly what to do
- Clear guidance on what to tell a mechanic

**What Counts as Bad**:
- Fewer than 2 actions or more than 4
- Vague actions: "check the engine", "consult a mechanic"
- Urgency mismatch (High risk with "when convenient")
- No practical guidance

**Scoring Rubric**:
- **0.0–0.3**: Fewer than 2 actions, or vague actions ("check the engine", "consult a mechanic")
- **0.4–0.6**: 2–4 actions but some are vague or risk level mismatch
- **0.7–0.9**: 2–4 specific actions, urgency matches risk level
- **1.0**: 2–4 specific actions, urgency perfectly matched, vehicle owner knows exactly what to do and what to say to a mechanic

**Examples**:

**Low-Scoring Example** (Score: 0.1, High risk):
> "Check your car and take it to a garage if needed."

*Why this fails*: Only one vague action, no specific guidance, urgency doesn't match High risk level, vehicle owner doesn't know what to check or tell mechanic.

**High-Scoring Example** (Score: 0.95, High risk):
> "1. Avoid heavy driving or motorway speeds until this is checked. 2. When the engine is completely cold, check the coolant reservoir — a small plastic tank under the bonnet with MIN and MAX markings. 3. Take your car to a mechanic as soon as possible and tell them the coolant temperature warning appeared."

*Why this succeeds*: Three specific actions, urgency matches High risk ("as soon as possible", "avoid"), practical guidance (how to check coolant, what to tell mechanic), vehicle owner knows exactly what to do.

---

## Overall Score

The **overall score** is the mean of the four dimension scores:

```
overall_score = (factual_grounding + readability + 
                 hedging_appropriateness + actionability) / 4
```

**Quality Threshold**: A report scoring **above 0.7 overall** is considered acceptable quality for production use.

---

## Evaluation Procedure

1. **Generate the report** using the pipeline (with or without RAG)
2. **Run automated evaluation**: Execute `report_quality_evaluator.py` to get automated scores for all four dimensions
3. **Manual review**: Manually review the report to verify automated scores and add qualitative notes
4. **Record results**: Document findings in `rag_comparison_table.md` with scores, notes, and examples

---

## References

- Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions*. ACM Transactions on Information Systems.

- Qi, Y., Zhang, X., & Wang, L. (2025). *Large Language Models for Fault Diagnosis: A Survey and Benchmark*. IEEE BigData 2025.

- ADR 302: Granite LLM Model Selection. `docs/adr/302-granite-llm-model-selection.md`