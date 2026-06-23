# Report Layer

## Overview

The Report Layer is the third stage in the Granite Lifeline predictive maintenance pipeline:

```
Data Layer → Model Layer → Report Layer → Dashboard
```

This layer receives predictions from the Model Layer (anomaly type, risk scores, key signals) and transforms them into human-readable diagnostic reports using IBM Granite LLM. It generates:

- **anomaly_description**: Human-readable explanation of detected anomalous behavior
- **possible_cause**: Likely root cause inferred from key signals and anomaly type
- **recommended_action**: Suggested inspection or maintenance actions

The Report Layer also maintains `risk_history` via local persistent storage for trend visualization and passes all Model Layer fields through to the Dashboard unchanged.

## Current Implementation Status

### Completed Components

#### 1. Context Injection (`pipeline/context_injection.py`)

Formats Model Layer output into structured text for Granite LLM prompt injection.

**Features:**
- Converts risk_score and prediction_confidence to percentages
- Handles optional risk_level field (defaults to "Unknown" if None)
- Formats key signals with abnormality detection (NORMAL/ABNORMAL based on reference_range)
- Omits empty unit strings for cleaner output

**Output format:**
```
Vehicle Status:
- Component: {component}
- Risk Level: {risk_level}
- Risk Score: {risk_score}%
- Prediction Confidence: {confidence}%

Key Signals:
- {feature}: {value}{unit} (reference: {lower}-{upper}{unit}) [{status}]
```

#### 2. Prompt Templates (`prompts/`)

Three-layer prompt chain for diagnostic report generation:

- **layer1_description.txt**: Generates anomaly_description
  - Describes what is happening based on input context
  - Uses risk_level to convey urgency in plain language
  - References key signals as evidence
  - Distinguishes NORMAL vs ABNORMAL signals

- **layer2_cause.txt**: Generates possible_cause
  - Explains why the observed pattern might be happening
  - Uses careful wording ("may indicate", "could suggest")
  - Connects possible cause to key signal values
  - Avoids claiming confirmed faults

- **layer3_action.txt**: Generates recommended_action
  - Returns 2-4 clear, concrete action items
  - Matches urgency to risk_level (Low/Medium/High)
  - Matches wording strength to prediction_confidence
  - Provides practical guidance for vehicle owners

All prompts enforce plain language requirements for non-technical vehicle owners.

#### 3. Model Comparison Script (`pipeline/model_comparison.py`)

Automated comparison of four Granite models on diagnostic report generation quality:

**Models tested:**
- granite3.3:2b
- granite3.3:8b
- granite4.1:3b
- granite4.1:8b

**Features:**
- Loads test input from `evaluation/typical_cooling_stress.json`
- Runs three-layer prompt chain for each model via Ollama HTTP API
- Handles JSON parsing with fallback extraction
- Generates comprehensive comparison report in markdown format

**Selected model:** `granite4.1:8b`
- Highest weighted score (4.85/5.0)
- Most actionable recommendations
- 100% JSON parsing success rate
- Latest IBM Granite version

See `evaluation/model_comparison.md` for full evaluation results.

#### 4. Evaluation Test Cases (`evaluation/`)

Three JSON mock data files representing different diagnostic scenarios:

1. **typical_cooling_stress.json**: Typical fault pattern
   - coolant_temp: 102°C (clearly ABNORMAL, above 90-95°C reference range)
   - risk_score: 0.82 (high), risk_level: "High"
   - prediction_confidence: 0.87 (high)
   - Signal clearly matches expected cooling_system_stress pattern

2. **atypical_cooling_stress.json**: Atypical/feature-conflict case
   - coolant_temp: 93°C (NORMAL, within 90-95°C reference range)
   - risk_score: 0.55 (moderate), risk_level: "Medium"
   - prediction_confidence: 0.51 (low)
   - Model flagged anomaly but primary signal doesn't support classification

3. **contradictory_cooling_stress.json**: Contradictory signals case
   - coolant_temp: 108°C (severely ABNORMAL, well above reference range)
   - risk_score: 0.38 (unexpectedly low), risk_level: "Low"
   - prediction_confidence: 0.31 (very low)
   - Sensor data and model risk assessment contradict each other

These files test how Granite LLM handles different diagnostic scenarios, particularly the distinction between typical and atypical fault patterns (Story 2 AC3 requirement).

#### 5. Documentation (`docs/`)

- **checklist.md**: Interface compliance, prompt quality, and plain language checklist
- **sample_reports.md**: Example reports for Low/Medium/High risk scenarios
- **model_comparison.md**: Comprehensive evaluation of four Granite models with weighted scoring framework

#### 6. Output Schema (`report_output_schema.json`)

JSON schema defining the complete Report Layer output structure, including all Model Layer pass-through fields plus generated report sections.

## Directory Structure

```
report_layer/
├── docs/                  # Documentation
│   ├── checklist.md       # Quality checklist
│   └── sample_reports.md  # Example reports
├── evaluation/            # Test cases and evaluation results
│   ├── __init__.py
│   ├── typical_cooling_stress.json
│   ├── atypical_cooling_stress.json
│   ├── contradictory_cooling_stress.json
│   └── model_comparison.md
├── pipeline/              # Core report generation logic
│   ├── __init__.py
│   ├── context_injection.py
│   └── model_comparison.py
├── prompts/               # LLM prompt templates
│   ├── layer1_description.txt
│   ├── layer2_cause.txt
│   └── layer3_action.txt
├── tests/                 # Unit tests (to be implemented)
└── report_output_schema.json
```

## Dependencies

### Model Layer Output

This layer consumes `ModelLayerOutput` from `shared/interface_models.py`, which includes:

- `timestamp`: ISO 8601 timestamp
- `anomaly_type`: Fault classification (e.g., `cooling_system_stress`)
- `risk_score`: Probability/severity (0-1)
- `risk_level`: Risk classification (Low/Medium/High)
- `component`: Affected component
- `prediction_confidence`: Model confidence (0-1)
- `key_signals`: Array of signal objects with feature, value, unit, reference_range

### External Dependencies

- **Python packages**: `pydantic`, `requests` (see `requirements.txt`)
- **Ollama**: Local LLM inference server (http://localhost:11434)
- **Granite models**: granite4.1:8b (selected for production)

## How to Run

All commands must be executed from the repository root.

### Run Model Comparison

```bash
# Ensure Ollama is running with required models
ollama pull granite3.3:2b
ollama pull granite3.3:8b
ollama pull granite4.1:3b
ollama pull granite4.1:8b

# Run comparison script
python report_layer/pipeline/model_comparison.py
```

This generates `report_layer/evaluation/model_comparison.md` with detailed evaluation results.

### Run Tests

```bash
# Run all tests
pytest tests/

# Run Report Layer tests only (when implemented)
pytest report_layer/tests/ -v
```

## Future Implementation Plan

The following components are planned for future sprints:

### 1. Report Generation Pipeline
- **pipeline/report_generator.py**: Orchestrate three-layer Granite LLM prompt chain
  - Integrate with selected model (granite4.1:8b)
  - Handle error cases and retries
  - Validate output against schema

### 2. RAG Components
- **rag/knowledge_base/**: Fault diagnosis knowledge base
- **rag/retriever.py**: Knowledge retrieval for prompt enhancement
  - Enhance prompts with relevant fault patterns
  - Improve diagnostic accuracy for edge cases

### 3. Storage Layer
- **storage/history_manager.py**: Manage risk_history persistence
  - Append `{timestamp, risk_score}` entries on each inference
  - Retrieve historical data for trend visualization
  - Implement efficient storage and retrieval

### 4. Testing
- Unit tests for context_injection.py
- Integration tests for full report generation pipeline
- Mock data for testing without live Granite API calls
- Test coverage for atypical and contradictory scenarios

## Output Format

The Report Layer outputs `ReportLayerOutput` (defined in `shared/interface_models.py`), which includes:

- All Model Layer fields (pass-through)
- `risk_history`: Array of `{timestamp, risk_score}` entries
- `anomaly_description`: Generated by Granite Layer 1
- `possible_cause`: Generated by Granite Layer 2
- `recommended_action`: Array of action strings generated by Granite Layer 3

This output is consumed by the Dashboard for visualization and user interaction.

## Quality Assurance

### Evaluation Framework

Model outputs are evaluated across five dimensions with weighted scoring:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Plain language quality | 30% | Understandable by non-technical vehicle owners |
| Specificity and data grounding | 25% | References actual sensor values from context |
| JSON parse success rate | 20% | Pipeline reliability and stability |
| Recommended action quality | 15% | Concrete, specific, matched to risk level |
| Avoiding over-certainty | 10% | Appropriate hedging for predictions |

See `evaluation/model_comparison.md` for detailed evaluation methodology and results.

### Compliance Checklist

All generated reports must satisfy:

- **Interface compliance**: Uses only fields defined in INTERFACE.md
- **Prompt quality**: Appropriate wording for each layer and risk level
- **Plain language**: Understandable without automotive expertise
- **Accuracy**: Distinguishes NORMAL vs ABNORMAL signals correctly
- **Safety**: Avoids overclaiming or causing unnecessary panic

See `docs/checklist.md` for full quality checklist.
