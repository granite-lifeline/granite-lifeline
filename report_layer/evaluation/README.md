# Report Layer Evaluation Directory

This directory contains evaluation reports, test scenarios, and quality assessment tools for the Granite Lifeline diagnostic report generation system.

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
└── v3-rag-comparison/                  # V3: RAG vs Baseline comparison
    ├── rag_evaluation_criteria.md      # Evaluation framework
    ├── scenario_comparison_baseline.md # Baseline reports (no RAG)
    └── scenario_comparison_rag.md      # RAG-enhanced reports
```

---

## Evaluation History

### V1: Initial Scenario Evaluation (June 2026)
**Location**: `v1-initial-evaluation/scenario_comparison.md`

- **Model**: granite4.1:8b
- **Mode**: No RAG (pre-RAG implementation)
- **Scenarios**: 3 cooling stress scenarios (typical, atypical, contradictory)
- **Objective**: Validate Story 2 AC3 requirement (distinguish typical from atypical faults)
- **Result**: Model successfully distinguishes scenarios with appropriate language adaptation

### V2: Model Selection Evaluation (June 2026)
**Location**: `v2-model-selection/`

- **Models Compared**: granite3.1:8b, granite3.1:2b, granite4.1:8b, granite4.1:3b
- **Evaluation Dimensions**: Factual grounding, readability, hedging, actionability
- **Selected Model**: granite3.1:8b (best balance of quality and speed)
- **Script**: `model_comparison.py` - Automated model comparison tool

### V3: RAG vs Baseline Evaluation (July 2026)
**Location**: `v3-rag-comparison/`

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

## Running Evaluations

### Generate Baseline Reports
```bash
python report_layer/pipeline/scenario_evaluation.py --mode baseline
```

### Generate RAG-Enhanced Reports
```bash
python report_layer/pipeline/scenario_evaluation.py --mode rag
```

### Run Quality Evaluator
```bash
python report_layer/evaluation/report_quality_evaluator.py
```

### Run Model Comparison
```bash
python report_layer/evaluation/v2-model-selection/model_comparison.py
```

---

**Last Updated**: July 2026  
**Project**: Granite Lifeline MSc Project, University of Bristol (IBM-sponsored)