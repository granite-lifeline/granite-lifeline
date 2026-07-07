# Baseline Diagnostic Reports - GL-120

**Generated:** [To be filled after running script]  
**Model:** granite4.1:8b  
**Mode:** Baseline (without RAG knowledge retrieval)

## Overview

These reports were generated using `build_context()` only, without RAG fault knowledge retrieval. This provides a baseline for comparing against RAG-enhanced reports to evaluate the impact of retrieved automotive knowledge on report quality.

**Generation Command:**
```bash
python report_layer/pipeline/scenario_evaluation.py --mode baseline
```

---

## Scenario 1: typical_cooling_stress

### Input Summary

- **Risk Score:** 82%
- **Risk Level:** High
- **Prediction Confidence:** 87%
- **Key Signals:**
  - coolant_temp = 102.0°C (reference: 90.0-95.0°C) [ABNORMAL]

### Generated Report

**Anomaly Description:**

[To be filled after running script]

**Possible Cause:**

[To be filled after running script]

**Recommended Action:**

[To be filled after running script]

### Automated Quality Scores

Run `report_quality_evaluator.py` on the generated report to get scores:

- **Factual Grounding:** [TBD]
- **Readability:** [TBD]
- **Hedging Appropriateness:** [TBD]
- **Actionability:** [TBD]
- **Overall Score:** [TBD]

---

## Scenario 2: atypical_cooling_stress

### Input Summary

- **Risk Score:** 55%
- **Risk Level:** Medium
- **Prediction Confidence:** 51%
- **Key Signals:**
  - coolant_temp = 93.0°C (reference: 90.0-95.0°C) [NORMAL]

### Generated Report

**Anomaly Description:**

[To be filled after running script]

**Possible Cause:**

[To be filled after running script]

**Recommended Action:**

[To be filled after running script]

### Automated Quality Scores

- **Factual Grounding:** [TBD]
- **Readability:** [TBD]
- **Hedging Appropriateness:** [TBD]
- **Actionability:** [TBD]
- **Overall Score:** [TBD]

---

## Scenario 3: contradictory_cooling_stress

### Input Summary

- **Risk Score:** 38%
- **Risk Level:** Low
- **Prediction Confidence:** 31%
- **Key Signals:**
  - coolant_temp = 108.0°C (reference: 90.0-95.0°C) [ABNORMAL]

### Generated Report

**Anomaly Description:**

[To be filled after running script]

**Possible Cause:**

[To be filled after running script]

**Recommended Action:**

[To be filled after running script]

### Automated Quality Scores

- **Factual Grounding:** [TBD]
- **Readability:** [TBD]
- **Hedging Appropriateness:** [TBD]
- **Actionability:** [TBD]
- **Overall Score:** [TBD]

---

## Summary Comparison Table

| Scenario | Factual Grounding | Readability | Hedging | Actionability | Overall |
|----------|-------------------|-------------|---------|---------------|---------|
| typical_cooling_stress | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| atypical_cooling_stress | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| contradictory_cooling_stress | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Instructions for Completion

1. **Start Ollama service:**
   ```bash
   ollama serve
   ```

2. **Run baseline evaluation:**
   ```bash
   cd /Users/charlotteyu/Desktop/IBM/granite-lifeline
   source .venv/bin/activate
   python report_layer/pipeline/scenario_evaluation.py --mode baseline
   ```

3. **Copy generated reports** from terminal output to this file

4. **Run quality evaluator:**
   ```bash
   python report_layer/evaluation/report_quality_evaluator.py
   ```

5. **Fill in quality scores** in the tables above

6. **Compare with RAG reports** in `scenario_comparison.md` to evaluate RAG impact

---

## Expected Differences from RAG Reports

Without RAG knowledge retrieval, baseline reports are expected to show:

- **Lower Factual Grounding:** Less connection to automotive domain knowledge
- **Lower Readability:** May use more technical jargon without plain language explanations
- **Similar Hedging:** Should still use appropriate uncertainty language (this is in the prompt templates)
- **Lower Actionability:** Less specific, concrete actions without retrieved action guidance

The comparison will validate whether RAG knowledge retrieval provides measurable improvements in report quality across these four dimensions.