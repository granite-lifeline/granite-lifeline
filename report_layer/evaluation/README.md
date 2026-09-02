# Report Layer Evaluation Directory

This directory contains current release evidence and historical experiments for
the Granite Lifeline Report Layer. Historical scores describe the code and
prompts used at that time; they must not be quoted as results from the current
pipeline.

## Current evidence

The current production evidence is in
[`v5-rag-final-ablation/`](v5-rag-final-ablation/README.md). It uses
`granite4.1:8b`, the production prompts, the current Validator and the targeted
correction path. The final controlled run contains five anomaly types under
four knowledge conditions (20 reports), with no fallback.

Use these files for current claims:

| Evidence | File |
|---|---|
| Machine-readable inputs, prompts and outputs | `v5-rag-final-ablation/final_rag_ablation_raw.json` |
| Automated screening summary | `v5-rag-final-ablation/final_rag_ablation_results.md` |
| Case-level manual labels | `v5-rag-final-ablation/final_rag_multidimensional_review.json` |
| Manual review summary | `v5-rag-final-ablation/final_rag_multidimensional_summary.md` |

The automated score checks implemented report rules. It does not establish
mechanical accuracy, because the fixtures do not contain technician-verified
faults or repair outcomes.

## Historical experiments

The directories below are retained to show how the design developed. They are
not current release evidence.

| Directory | Purpose | Status |
|---|---|---|
| `v1-initial-evaluation/` | Early pre-RAG scenario exploration | Historical |
| `v2-model-selection/` | Four-model comparison used during model selection | Historical decision evidence |
| `v3-rag-baseline-comparison/` | Early baseline/RAG comparison | Historical; predates current prompts and Validator |
| `v4-meta-semantic-comparison/` | Retrieval-strategy comparison | Historical; predates final retrieval design |
| `prompt_refinement/` | Failure discovery and regression fixtures | Supporting development evidence |
| `qa_cross_validation/` | Evaluator/Validator and stability investigations | Supporting development evidence |
| `perturbation_regression/` | Wording and negation regression checks | Current regression support |
| `user_testing_ab/` | User-testing stimulus preparation | Historical study preparation |
| `viva_real_case/` | Saved demonstration case | Demonstration evidence, not the final evaluation |

## Directory Structure

```
evaluation/
├── README.md                           # This file
├── __init__.py
├── report_quality_evaluator.py         # Automated quality assessment tool
│
├── test_scenarios/                     # Test scenario data files
│   ├── typical_cooling_stress.json
│   ├── atypical_cooling_stress.json
│   └── contradictory_cooling_stress.json
│
├── v1-initial-evaluation/              # V1: Initial scenario evaluation (pre-RAG)
│   └── scenario_comparison.md          # Evaluation with granite4.1:8b (no RAG)
│
├── v2-model-selection/                 # V2: Model selection evaluation
│   ├── model_comparison.md             # Comparison across 4 Granite models
│   └── model_comparison.py             # Model comparison script
│
├── v3-rag-baseline-comparison/         # V3: historical RAG/baseline comparison
│   ├── rag_evaluation_criteria.md      # Evaluation framework
│   ├── scenario_comparison_baseline.md # Baseline reports (no RAG)
│   └── scenario_comparison_rag.md      # RAG-enhanced reports
├── v4-meta-semantic-comparison/        # Historical retrieval comparison
└── v5-rag-final-ablation/              # Current controlled evidence
```

---

## Evaluation History

### V1: Initial Scenario Evaluation (June 2026)
**Location**: `v1-initial-evaluation/scenario_comparison.md`

- **Model**: granite4.1:8b
- **Mode**: No RAG (pre-RAG implementation)
- **Scenarios**: 3 cooling stress scenarios (typical, atypical, contradictory)
- **Objective**: Validate Story 2 AC3 requirement (distinguish typical from atypical faults)
- **Result**: Historical exploratory output retained for design provenance;
  it is not current release evidence

### V2: Model Selection Evaluation (June 2026)
**Location**: `v2-model-selection/`

- **Models Compared**: granite3.3:2b, granite3.3:8b, granite4.1:3b, granite4.1:8b
- **Evaluation Dimensions**: Factual grounding, readability, hedging, actionability
- **Selected Model**: granite4.1:8b for the production Report Layer
- **Script**: `model_comparison.py` - Automated model comparison tool

### V3: RAG vs Baseline Evaluation (July 2026)
**Location**: `v3-rag-baseline-comparison/`

#### Evaluation Framework
**File**: `rag_evaluation_criteria.md`

Defines 4-dimensional evaluation framework:
1. **Factual Grounding** (0.0-1.0): Traceability to input data
2. **Readability** (0.0-1.0): Plain language for non-technical users
3. **Hedging Appropriateness** (0.0-1.0): Uncertainty language calibration
4. **Actionability** (0.0-1.0): Concrete, risk-appropriate actions

Academic grounding: Huang et al. 2025 (hallucination), Qi et al. 2025 (fault diagnosis), ADR 302 (weighted scoring)

#### Baseline vs RAG Reports
**Files**: 
- `scenario_comparison_baseline.md` - Reports without RAG knowledge retrieval
- `scenario_comparison_rag.md` - Reports with RAG fault knowledge

**Key Differences**:
- **Baseline**: Generic automotive knowledge, less specific technical details
- **RAG**: Retrieved fault knowledge, specific parameters (e.g., "thermostat opens at 82°C"), more detailed diagnostic steps

---

## Test Scenarios

### Location: `test_scenarios/`

Three cooling degradation scenarios designed to test model behavior:

1. **typical_cooling_stress.json**
   - Risk: High (82%), Confidence: 87%
   - Signal: coolant_temp = 102°C (ABNORMAL, reference: 90-95°C)
   - Expected: Urgent, specific recommendations

2. **atypical_cooling_stress.json**
   - Risk: Medium (55%), Confidence: 51%
   - Signal: coolant_temp = 93°C (NORMAL, reference: 90-95°C)
   - Expected: Acknowledge uncertainty, recommend monitoring

3. **contradictory_cooling_stress.json**
   - Risk: Low (38%), Confidence: 31%
   - Signal: coolant_temp = 108°C (ABNORMAL, reference: 90-95°C)
   - Expected: Note contradiction without force-fitting explanation

---

## Quality Assessment Tool

### report_quality_evaluator.py

Automated quality assessment across 4 dimensions:
- Factual grounding
- Readability
- Hedging appropriateness
- Actionability

**Usage**:
```python
from report_layer.evaluation.report_quality_evaluator import evaluate_report

score = evaluate_report(report, context, anomaly_type, risk_level)
print(f"Overall Score: {score.overall_score:.2f}")
```

---

## Related Documentation

- **ADR 302**: Granite LLM Model Selection (`docs/adr/302-granite-llm-model-selection.md`)
- **ADR 303**: RAG Knowledge Base Design (`docs/adr/303-rag-knowledge-base-design.md`)
- **RAG Sample Reports**: `report_layer/docs/rag_sample_reports.md`
- **RAG Language Quality Review**: `report_layer/docs/rag_language_quality_review.md`

---

## Running the current evaluation

The V1--V4 commands and outputs are retained for historical investigation.
Use V5 for claims about the current Report Layer:

```bash
uv run python report_layer/evaluation/v5-rag-final-ablation/run_final_rag_ablation.py
uv run python report_layer/evaluation/v5-rag-final-ablation/run_owner_decision_smoke.py
```

The standalone quality-evaluator and model-comparison scripts belong to the
historical evaluation stages. Their committed outputs preserve those earlier
decisions; they are not the commands used to produce current release evidence.

---

**Last Updated**: September 2026
**Project**: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)
