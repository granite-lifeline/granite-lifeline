# Report Layer

**Owner:** Report Team  
**Status:** Active Development  
**Last Updated:** 2026-06-23

---

## Overview

The Report Layer is the third stage in the Granite Lifeline predictive maintenance pipeline, responsible for transforming Model Layer predictions into human-readable diagnostic reports using IBM Granite LLM.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Core Responsibilities

1. **Context Injection**: Format Model Layer output for LLM consumption
2. **Report Generation**: Use Granite LLM to generate plain-language diagnostic reports
3. **Pass-Through**: Forward Model Layer fields unchanged to Dashboard
4. **History Management**: Maintain risk_history for trend visualization (planned)

### Generated Report Sections

- **anomaly_description**: Human-readable explanation of detected anomalous behavior
- **possible_cause**: Likely root cause inferred from key signals and anomaly type
- **recommended_action**: Suggested inspection or maintenance actions

---

## Current Implementation Status

### [COMPLETED] Sprint 1

| Component | Ticket | Description |
|-----------|--------|-------------|
| Context Injection | GL-27 | Format Model Layer output for LLM prompts |
| Prompt Templates | GL-49, GL-55 | Three-layer prompt chain (description, cause, action) |
| Model Comparison | GL-76 | Evaluate 4 Granite models, select granite4.1:8b |
| Scenario Evaluation | GL-30 | Test granite4.1:8b on typical/atypical/contradictory scenarios |
| ADR 301 | GL-27 | Document context injection design |
| ADR 302 | GL-76 | Document model selection rationale |
| Test Cases | GL-27, GL-30 | 3 JSON scenarios for evaluation |

### [IN PROGRESS]

| Component | Ticket | Status |
|-----------|--------|--------|
| Dashboard Integration | GL-41, GL-42 | Dashboard UI complete, API integration pending |

### [PLANNED] Sprint 2+

| Component | Priority | Description |
|-----------|----------|-------------|
| Report Generation Pipeline | P0 | Orchestrate three-layer Granite LLM chain |
| Risk History Storage | P0 | Persist risk_history for trend charts |
| RAG Knowledge Base | P1 | Enhance prompts with fault diagnosis knowledge |
| Unit Tests | P1 | Test coverage for all components |
| Integration Tests | P1 | End-to-end pipeline testing |

---

## Architecture

### Data Flow

```
ModelLayerOutput (from Model Layer)
    ↓
Context Injection (build_context)
    ↓
Granite LLM Three-Layer Chain
    ├─ Layer 1: anomaly_description
    ├─ Layer 2: possible_cause
    └─ Layer 3: recommended_action
    ↓
ReportLayerOutput (to Dashboard)
    ├─ Pass-through: timestamp, risk_score, risk_level, component,
    │                prediction_confidence, key_signals
    ├─ Generated: anomaly_description, possible_cause, recommended_action
    └─ Maintained: risk_history
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | IBM Granite 4.1:8b | Report generation |
| Inference | Ollama (dev) / watsonx.ai (prod) | LLM serving |
| Data Models | Pydantic | Type-safe data contracts |
| HTTP Client | requests | Ollama API communication |

---

## Directory Structure

```
report_layer/
├── docs/                           # Documentation
│   ├── checklist.md                # Quality assurance checklist
│   └── sample_reports.md           # Example reports
├── evaluation/                     # Test cases and results
│   ├── __init__.py
│   ├── typical_cooling_stress.json         # Typical fault scenario
│   ├── atypical_cooling_stress.json        # Atypical scenario
│   ├── contradictory_cooling_stress.json   # Contradictory scenario
│   ├── model_comparison.md                 # GL-76 evaluation results
│   └── scenario_comparison.md              # GL-30 evaluation results
├── pipeline/                       # Core logic
│   ├── __init__.py
│   ├── context_injection.py        # Format Model Layer output
│   ├── model_comparison.py         # GL-76 model evaluation script
│   └── scenario_evaluation.py      # GL-30 scenario testing script
├── prompts/                        # LLM prompt templates
│   ├── layer1_description.txt      # Anomaly description prompt
│   ├── layer2_cause.txt            # Possible cause prompt
│   └── layer3_action.txt           # Recommended action prompt
├── tests/                          # Unit tests (planned)
│   └── .gitkeep
└── README.md                       # This file
```

---

## Completed Components

### 1. Context Injection (`pipeline/context_injection.py`)

**Purpose:** Format Model Layer output into structured text for Granite LLM prompt injection.

**Function:** `build_context(ttm_output: ModelLayerOutput) -> str`

**Features:**
- Converts risk_score and prediction_confidence to percentages
- Handles optional risk_level field (defaults to "Unknown" if None)
- Classifies signals as NORMAL/ABNORMAL based on reference_range
- Omits empty unit strings for cleaner output

**Output Format:**
```
Vehicle Status:
- Component: cooling_system_stress
- Risk Level: High
- Risk Score: 82%
- Prediction Confidence: 87%

Key Signals:
- coolant_temp: 102.0°C (reference: 90.0-95.0°C) [ABNORMAL]
```

**Documentation:** See `docs/adr/301-context-injection-design.md`

### 2. Prompt Templates (`prompts/`)

Three-layer prompt chain designed for plain-language diagnostic reports:

**Layer 1: Anomaly Description** (`layer1_description.txt`)
- Describes what is happening based on input context
- Uses risk_level to convey urgency appropriately
- References key signals as evidence
- Distinguishes NORMAL vs ABNORMAL signals

**Layer 2: Possible Cause** (`layer2_cause.txt`)
- Explains why the observed pattern might be happening
- Uses careful wording ("may indicate", "could suggest")
- Connects possible cause to key signal values
- Avoids claiming confirmed faults

**Layer 3: Recommended Action** (`layer3_action.txt`)
- Returns 2-4 clear, concrete action items in JSON array format
- Matches urgency to risk_level (Low/Medium/High)
- Matches wording strength to prediction_confidence
- Provides practical guidance for vehicle owners

**Design Principles:**
- Plain language for non-technical vehicle owners (Story 3 AC)
- No automotive jargon without explanation
- Appropriate hedging for predictions (not confirmed diagnoses)
- Risk-level-appropriate urgency

**Documentation:** See GL-49, GL-55 tickets and `docs/sample_reports.md`

### 3. Model Comparison (`pipeline/model_comparison.py`)

**Purpose:** Evaluate four Granite models to select the best for production.

**Models Tested:**
- granite3.3:2b (2B parameters, Granite 3.3 series)
- granite3.3:8b (8B parameters, Granite 3.3 series)
- granite4.1:3b (3B parameters, Granite 4.1 series)
- granite4.1:8b (8B parameters, Granite 4.1 series)

**Evaluation Framework:**

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Plain language quality | 30% | Core Story 3 AC requirement |
| Specificity and data grounding | 25% | Story 2 AC1: reference actual sensor values |
| JSON parse success rate | 20% | Pipeline reliability |
| Recommended action quality | 15% | Story 1 AC3/AC4: concrete, specific actions |
| Avoiding over-certainty | 10% | Appropriate hedging for predictions |

**Selected Model:** `granite4.1:8b`
- **Weighted Score:** 4.85/5.0 (highest)
- **Strengths:** Most actionable recommendations, 100% JSON parsing, latest IBM Granite version
- **Fallback:** granite4.1:3b (4.55/5.0) if speed/hardware constraints arise

**Results:** See `evaluation/model_comparison.md` and `docs/adr/302-granite-llm-model-selection.md`

### 4. Scenario Evaluation (`pipeline/scenario_evaluation.py`)

**Purpose:** Test granite4.1:8b on three diagnostic scenarios to validate Story 2 AC3 (distinguish typical from atypical fault patterns).

**Test Scenarios:**

1. **typical_cooling_stress.json**
   - coolant_temp: 102°C (ABNORMAL, above 90-95°C reference)
   - risk_score: 0.82 (High), confidence: 0.87
   - Expected: Confident, specific recommendations

2. **atypical_cooling_stress.json**
   - coolant_temp: 93°C (NORMAL, within 90-95°C reference)
   - risk_score: 0.55 (Medium), confidence: 0.51
   - Expected: Acknowledge low confidence and mixed signals

3. **contradictory_cooling_stress.json**
   - coolant_temp: 108°C (severely ABNORMAL)
   - risk_score: 0.38 (Low), confidence: 0.31
   - Expected: Note contradiction without force-fitting

**Features:**
- Runs three-layer prompt chain for each scenario
- Handles JSON parsing with fallback extraction
- Generates comparative analysis report
- Validates Story 2 AC3 requirement

**Results:** See `evaluation/scenario_comparison.md`

### 5. Test Cases (`evaluation/*.json`)

Three JSON mock data files representing different diagnostic scenarios:

**typical_cooling_stress.json**
- Typical fault pattern with clear ABNORMAL signal
- Tests standard diagnostic flow

**atypical_cooling_stress.json**
- Atypical pattern: NORMAL signal but anomaly flagged
- Tests model's ability to handle feature conflicts

**contradictory_cooling_stress.json**
- Contradictory signals: severe ABNORMAL but low risk score
- Tests model's ability to note contradictions

These files validate the model's ability to distinguish typical from atypical fault patterns (Story 2 AC3).

---

## Dependencies

### Input: Model Layer Output

Consumes `ModelLayerOutput` from `shared/interface_models.py`:

```python
class ModelLayerOutput(BaseModel):
    timestamp: str                      # ISO 8601
    anomaly_type: str                   # e.g., "cooling_system_stress"
    risk_score: float                   # 0.0 - 1.0
    risk_level: Optional[str]           # "Low" | "Medium" | "High"
    component: str                      # Affected component
    prediction_confidence: float        # 0.0 - 1.0
    key_signals: List[KeySignal]        # Signal details
```

See `docs/INTERFACE.md` Section 2 for complete field definitions.

### Output: Report Layer Output

Produces `ReportLayerOutput` for Dashboard consumption:

```python
class ReportLayerOutput(BaseModel):
    # Pass-through from Model Layer
    timestamp: str
    risk_score: float
    risk_level: Optional[str]
    component: str
    prediction_confidence: float
    key_signals: List[KeySignal]
    
    # Report Layer maintained
    risk_history: Optional[List[RiskHistoryEntry]]
    
    # Generated by Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]
```

See `docs/INTERFACE.md` Section 3 for complete field definitions.

### External Dependencies

- **Python Packages:** `pydantic`, `requests` (see root `requirements.txt`)
- **Ollama:** Local LLM inference server (http://localhost:11434)
- **Granite Models:** granite4.1:8b (production), granite4.1:3b (fallback)

---

## How to Run

All commands must be executed from the repository root.

### Prerequisites

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install Ollama (if not already installed)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh
# Windows: Download from https://ollama.com/download

# Pull required Granite models
ollama pull granite4.1:8b
```

### Run Model Comparison (GL-76)

```bash
# Ensure Ollama is running
ollama serve  # In separate terminal if not running as service

# Pull all models for comparison
ollama pull granite3.3:2b
ollama pull granite3.3:8b
ollama pull granite4.1:3b
ollama pull granite4.1:8b

# Run comparison script
python report_layer/pipeline/model_comparison.py
```

**Output:** `report_layer/evaluation/model_comparison.md`

### Run Scenario Evaluation (GL-30)

```bash
# Ensure Ollama is running with granite4.1:8b
ollama pull granite4.1:8b

# Run scenario evaluation
python report_layer/pipeline/scenario_evaluation.py
```

**Output:** `report_layer/evaluation/scenario_comparison.md`

### Run Tests

```bash
# Run all project tests
pytest tests/ -v

# Run Report Layer tests only (when implemented)
pytest report_layer/tests/ -v
```

---

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

**Theoretical Foundation:**
- Qi et al. (2025): LLM-based fault diagnosis evaluation framework
- Huang et al. (2025): Faithfulness vs factuality hallucination distinction

See `evaluation/model_comparison.md` for detailed methodology.

### Compliance Checklist

All generated reports must satisfy:

- ✅ **Interface compliance**: Uses only fields defined in INTERFACE.md
- ✅ **Prompt quality**: Appropriate wording for each layer and risk level
- ✅ **Plain language**: Understandable without automotive expertise
- ✅ **Accuracy**: Distinguishes NORMAL vs ABNORMAL signals correctly
- ✅ **Safety**: Avoids overclaiming or causing unnecessary panic
- ✅ **Story 2 AC3**: Distinguishes typical from atypical fault patterns

See `docs/checklist.md` for full quality checklist.

---

## Planned Implementation

### Sprint 2 Priorities

**1. Report Generation Pipeline** (P0)
- `pipeline/report_generator.py`: Orchestrate three-layer Granite LLM chain
- Integrate with granite4.1:8b via Ollama API
- Handle error cases and retries
- Validate output against schema

**2. Risk History Storage** (P0)
- `storage/history_manager.py`: Manage risk_history persistence
- Append `{timestamp, risk_score}` entries on each inference
- Retrieve historical data for Dashboard trend visualization
- Implement efficient storage (SQLite or JSON file)

**3. Unit Tests** (P1)
- Test `context_injection.py` with various inputs
- Test prompt template variable substitution
- Mock Ollama API for testing without live calls
- Test atypical and contradictory scenario handling

**4. Integration Tests** (P1)
- End-to-end pipeline testing
- Model Layer → Report Layer → Dashboard flow
- Error handling and retry logic
- Performance benchmarks

### Future Enhancements

**RAG Components** (P2)
- `rag/knowledge_base/`: Fault diagnosis knowledge base
- `rag/retriever.py`: Knowledge retrieval for prompt enhancement
- Improve diagnostic accuracy for edge cases
- Reduce hallucination risk

**Production Deployment** (P3)
- Migrate from Ollama to IBM watsonx.ai
- API authentication and rate limiting
- Monitoring and logging
- A/B testing framework

---

## Troubleshooting

### Ollama Connection Error

**Error:** `requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`

**Solution:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# Verify API is accessible
curl http://localhost:11434/api/tags
```

### Model Not Found

**Error:** `model 'granite4.1:8b' not found`

**Solution:**
```bash
# Pull the model
ollama pull granite4.1:8b

# Verify installation
ollama list | grep granite
```

### JSON Parsing Failure

**Issue:** Script shows "Warning: Layer X JSON parse failed"

**Explanation:** This is expected behavior. The script includes fallback extraction that searches for JSON within the response text. Check the output markdown file to verify the extracted content is valid.

**If persistent:**
- Check prompt templates for correct JSON format examples
- Verify model is granite4.1:8b (highest JSON parse success rate)
- Review Ollama logs for errors

### Import Error

**Error:** `ModuleNotFoundError: No module named 'shared'`

**Solution:**
```bash
# Ensure you're running from project root
cd /path/to/granite-lifeline

# Verify virtual environment is activated
which python  # Should show .venv/bin/python

# Run script from root
python report_layer/pipeline/model_comparison.py
```

---

## Team & Contact

**Report Team:**
- Charlotte Yu
- Jintong He

**Project:** Granite Lifeline  
**Institution:** University of Bristol MSc Computer Science  
**Sponsor:** IBM

For questions or contributions, please refer to the main project README or create a Jira ticket.

---

## References

- [IBM Granite Models](https://www.ibm.com/granite)
- [Ollama Documentation](https://ollama.com/docs)
- [Project INTERFACE.md](../docs/INTERFACE.md) - Data contracts
- [ADR 301](../docs/adr/301-context-injection-design.md) - Context injection design
- [ADR 302](../docs/adr/302-granite-llm-model-selection.md) - Model selection rationale
- [Project README.md](../README.md) - Overall architecture
