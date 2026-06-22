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

## Current Implementation

### Directory Structure

```
report_layer/
├── evaluation/        # Mock data for testing Granite LLM report generation
│   ├── __init__.py
│   ├── typical_cooling_stress.json
│   ├── atypical_cooling_stress.json
│   └── contradictory_cooling_stress.json
├── pipeline/          # Core report generation logic
│   ├── __init__.py
│   └── context_injection.py    # Format Model Layer output for LLM prompts
└── tests/             # Unit tests (to be implemented)
```

### Implemented Components

#### evaluation/

Contains three JSON mock data files representing `ModelLayerOutput` instances for testing Granite LLM diagnostic report generation. All files use `anomaly_type: "cooling_system_stress"` with varying signal patterns:

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

These files are used to test how Granite LLM handles different diagnostic scenarios, particularly the distinction between typical and atypical fault patterns (Story 2 AC3 requirement).

#### pipeline/context_injection.py

Contains `build_context(ttm_output: ModelLayerOutput) -> str` function that formats Model Layer output into structured text for Granite LLM prompt injection.

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

- **Python packages**: `pydantic` (see `requirements.txt`)
- **Replicate API**: Required for Granite LLM calls (to be implemented)

## How to Run

All commands must be executed from the repository root using `uv run`:

### Run Tests

```bash
# Run all tests
uv run pytest tests/

# Run Report Layer tests only (when implemented)
uv run pytest report_layer/tests/ -v
```

## Future Implementation Plan

The following components are planned for future sprints:

### 1. Report Generation Pipeline
- **pipeline/report_generator.py**: Orchestrate three-layer Granite LLM prompt chain
  - Layer 1: Generate anomaly_description
  - Layer 2: Generate possible_cause
  - Layer 3: Generate recommended_action

### 2. Prompt Templates
- **prompts/layer1_description.txt**: Prompt for anomaly description generation
- **prompts/layer2_cause.txt**: Prompt for root cause analysis
- **prompts/layer3_action.txt**: Prompt for recommended actions

### 3. RAG Components
- **rag/knowledge_base/**: Fault diagnosis knowledge base
- **rag/retriever.py**: Knowledge retrieval for prompt enhancement

### 4. Storage Layer
- **storage/history_manager.py**: Manage risk_history persistence
  - Append `{timestamp, risk_score}` entries on each inference
  - Retrieve historical data for trend visualization

### 5. Testing
- Unit tests for context_injection.py
- Integration tests for full report generation pipeline
- Mock data for testing without live Granite API calls

## Output Format

The Report Layer will output `ReportLayerOutput` (defined in `shared/interface_models.py`), which includes:

- All Model Layer fields (pass-through)
- `risk_history`: Array of `{timestamp, risk_score}` entries
- `anomaly_description`: Generated by Granite Layer 1
- `possible_cause`: Generated by Granite Layer 2
- `recommended_action`: Array of action strings generated by Granite Layer 3

This output will be consumed by the Dashboard for visualization and user interaction.
