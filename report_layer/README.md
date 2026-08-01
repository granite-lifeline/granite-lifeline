# Report Layer

**Owner:** Report Team
**Status:** Active Development
**Last Updated:** 2026-07-28

---

## Overview

The Report Layer is the third stage in the Granite Lifeline predictive
maintenance pipeline. It transforms Model Layer predictions into
human-readable diagnostic reports using IBM Granite LLM, RAG-grounded
fault knowledge, and a three-layer prompt chain.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Core Responsibilities

1. **Context Injection**: Format Model Layer output for LLM consumption
2. **Report Generation**: Use Granite LLM to generate plain-language diagnostic reports
3. **Pass-Through**: Forward Model Layer fields unchanged to Dashboard
4. **History Management**: Build `risk_history` for trend visualization from the Model Layer's batch envelope (`{summary, windows}`) at request time — synthesized per request, not separately persisted
5. **RAG Grounding**: Retrieve anomaly-specific fault knowledge and risk-level action guidance

### Generated Report Sections

- **anomaly_description**: Human-readable explanation of detected anomalous behavior
- **possible_cause**: Likely root cause inferred from key signals and anomaly type
- **recommended_action**: Suggested inspection or maintenance actions

---

## Current Implementation Status

### [COMPLETED]

| Component | Ticket | Description |
|-----------|--------|-------------|
| Context Injection | GL-27 | Format Model Layer output for LLM prompts |
| Prompt Templates | GL-49, GL-55 | Three-layer prompt chain (description, cause, action) |
| Model Comparison | GL-76 | Evaluate 4 Granite models, select granite4.1:8b |
| Scenario Evaluation | GL-30 | Test granite4.1:8b on typical/atypical/contradictory scenarios |
| ADR 301 | GL-27 | Document context injection design |
| ADR 302 | GL-76 | Document model selection rationale |
| Test Cases | GL-27, GL-30 | 3 JSON scenarios for evaluation |
| RAG Knowledge Indexer | GL-111 | ChromaDB indexer for fault knowledge base |
| RAG Retriever | GL-112 | Metadata-filtered retrieval functions |
| RAG Unit Tests | GL-113 | 33 test cases for RAG retriever |
| RAG Integration | GL-114 | RAG knowledge injection into context |
| RAG Prompt Integration | GL-115 | Inject RAG knowledge into LLM prompts |
| RAG Sample Reports | GL-116 | Sample RAG reports for 3 required scenarios |
| RAG Language Review | GL-117 | Verify plain language and no confirmed fault claims |
| Confidence Guidance | GL-135 | Certainty language based on prediction_confidence |
| Signal Correlation | GL-136 | Multi-signal correlation analysis |
| Failure Projection Context | GL-190, GL-192 | Inject estimated failure probability and cycles into prompts when available |
| Prompt Rule Hardening | GL-213 | Enforce context-first grounding, strict JSON output, safe use of notes, and no invented failure projection values |
| ADR 303 | GL-110 | Document RAG knowledge base design |
| Report Generation Pipeline | GL-241–245 | `pipeline/report_generator.py::generate_report()` orchestrates the full three-layer chain against a live Ollama instance, with per-layer retry and a graceful empty-report fallback on failure (never raises) |
| Dashboard Wiring | GL-365 | Dashboard's CSV-upload flow calls the real pipeline end-to-end (Data Layer → Model Layer subprocess → `generate_report()`); verified with a real, unmocked run producing a grounded report |
| Timeout Surfacing Fix | GL-261 | Dashboard now detects `generate_report()`'s silent empty-report fallback and shows an "Analysis Timed Out" error card instead of rendering a blank report |

### [IN PROGRESS]

*(none — the P0 items previously listed here are complete; see Completed above)*

### [PLANNED]

| Component | Priority | Description |
|-----------|----------|-------------|
| Unit Tests | P1 | Broaden coverage for `report_generator.py`'s retry logic, timeout handling, and multi-layer failure paths |
| Integration Tests | P1 | Automated (mocked) end-to-end test for the Data → Model → Report → Dashboard chain — currently only verified once by hand |
| Retrieval Re-verification | P1 | Re-run the metadata-filter vs. semantic-search comparison on the current 5-type knowledge base (existing 100%/~180x numbers predate the retirement of two anomaly types) |

---

## Architecture

### Data Flow

```
ModelLayerOutput (from Model Layer)
    ↓
Context Injection (build_context)
    ↓
RAG Retrieval (build_context_with_rag)
    ↓
Granite LLM Three-Layer Chain
    ├─ Layer 1: anomaly_description
    ├─ Layer 2: possible_cause
    └─ Layer 3: recommended_action
    ↓
ReportLayerOutput (to Dashboard)
    ├─ Pass-through: timestamp, risk_score, risk_level, component,
    │                prediction_confidence, key_signals,
    │                estimated_cycles_to_failure,
    │                estimated_failure_probability, notes
    ├─ Generated: anomaly_description, possible_cause, recommended_action
    └─ Maintained: risk_history
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | IBM Granite 4.1:8b | Report generation |
| Inference | Ollama (local only) | LLM serving — a hosted/production inference path (IBM watsonx.ai, Replicate) was scoped but not pursued: no watsonx access and no project budget for paid hosted inference or a self-hosted server (see `docs/viva/report_challenge.md` Limitations) |
| Data Models | Pydantic | Type-safe data contracts |
| HTTP Client | requests | Ollama API communication |

---

## Directory Structure

```
report_layer/
├── docs/                           # Documentation
│   ├── checklist.md                # Quality assurance checklist
│   ├── rag_language_quality_review.md
│   ├── rag_sample_reports.md
│   ├── readability_evaluation.md   # Readability assessment
│   ├── sample_report_review.md     # Sample report analysis
│   ├── sample_reports.md           # Example reports
│   └── terminology_checklist.md    # Terminology validation
├── evaluation/                     # Evaluation results and test scenarios
│   ├── __init__.py
│   ├── report_quality_evaluator.py         # Automated quality scoring
│   ├── test_scenarios/                     # JSON inputs for evaluation runs
│   │   ├── typical_cooling_stress.json
│   │   ├── atypical_cooling_stress.json
│   │   └── contradictory_cooling_stress.json
│   ├── v1-initial-evaluation/              # GL-30 baseline results
│   ├── v2-model-selection/                 # GL-76 model comparison results
│   ├── v3-rag-baseline-comparison/         # RAG vs no-RAG results
│   └── v4-meta-semantic-comparison/        # Meta-semantic evaluation results
├── pipeline/                       # Core logic
│   ├── __init__.py
│   ├── context_injection.py        # Format Model Layer output + RAG integration
│   ├── report_generator.py         # generate_report(): production three-layer chain (GL-241–245)
│   ├── prompt_chain_validator.py   # Validate prompt chain outputs
│   └── scenario_evaluation.py      # GL-30 scenario testing script
├── prompts/                        # LLM prompt templates
│   ├── layer1_description.txt      # Anomaly description prompt
│   ├── layer2_cause.txt            # Possible cause prompt
│   └── layer3_action.txt           # Recommended action prompt
├── rag/                            # RAG knowledge base (GL-110)
│   ├── knowledge_indexer.py        # ChromaDB indexer
│   ├── rag_retriever.py            # Metadata-filtered retrieval
│   ├── symptom_knowledge_indexer.py # Document-level chunking variant (GL-156 comparison)
│   └── chroma_db/                  # ChromaDB storage (gitignored)
├── tests/                          # Unit tests
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
- Maps raw signal IDs to owner-readable signal names
- Includes Failure Projection when estimated values are available
- Includes Model Layer Notes as data-quality information only
- Adds signal correlation notes when abnormal signals match known patterns

**Output Format:**
```
Vehicle Status:
- Component: cooling_degradation
- Risk Level: High
- Risk Score: 82%
- Prediction Confidence: 87%

Key Signals:
- Coolant Temperature: 102.0°C (reference: 90.0-95.0°C) [ABNORMAL]

Failure Projection:
- Failure probability: 72%
- Estimated cycles to failure: 120 drive cycles

Model Layer Notes:
- These notes describe input data quality, repaired values, or disabled
  detections. They are not mechanical fault causes by themselves.
```

**Documentation:** See `docs/adr/301-context-injection-design.md`

### 2. Prompt Templates (`prompts/`)

Three-layer prompt chain designed for plain-language diagnostic reports:

**Layer 1: Anomaly Description** (`layer1_description.txt`)
- Describes what is happening based on input context
- Uses risk_level to convey urgency appropriately
- References key signals as evidence
- Distinguishes NORMAL vs ABNORMAL signals
- Uses Failure Projection only when values are present

**Layer 2: Possible Cause** (`layer2_cause.txt`)
- Explains why the observed pattern might be happening
- Uses careful wording ("may indicate", "could suggest")
- Connects possible cause to key signal values
- Avoids claiming confirmed faults
- Uses retrieved fault knowledge only when supported by current context

**Layer 3: Recommended Action** (`layer3_action.txt`)
- Returns 2-4 clear, concrete action items in JSON array format
- Matches urgency to risk_level (Low/Medium/High)
- Matches wording strength to prediction_confidence
- Provides practical guidance for vehicle owners
- Uses retrieved action guidance only when it matches current risk and signals

**Design Principles:**
- Plain language for non-technical vehicle owners (Story 3 AC)
- No automotive jargon without explanation
- Appropriate hedging for predictions (not confirmed diagnoses)
- Risk-level-appropriate urgency
- Input context is the main source of truth; RAG knowledge is supporting background
- Do not invent missing failure probabilities, cycles, dates, mileage, or deadlines
- Treat Model Layer Notes as data-quality notes, not mechanical causes
- Return exactly one valid JSON object per prompt layer, with no Markdown or extra keys

**Documentation:** See GL-49, GL-55, GL-213, `docs/sample_reports.md`,
and `docs/checklist.md`.

### 3. Model Comparison (`evaluation/v2-model-selection/model_comparison.py`)

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

**Results:** See `evaluation/v2-model-selection/model_comparison.md`
and `docs/adr/302-granite-llm-model-selection.md`

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

**Results:** See `evaluation/v1-initial-evaluation/scenario_comparison.md`
and the RAG comparison files under
`evaluation/v3-rag-baseline-comparison/`.

### 5. Test Cases (`evaluation/test_scenarios/*.json`)

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

### 6. RAG Knowledge Base (`rag/`)

**Purpose:** Provide grounded fault diagnosis knowledge to reduce LLM hallucination and improve diagnostic accuracy.

**Components:**

**knowledge_indexer.py** (GL-111)
- Indexes 7 anomaly types from `shared/ground_knowledge/grounded_knowledge.yaml`
- Creates 28 documents (7 types × 4 documents each):
  - description_causes
  - actions_low
  - actions_medium
  - actions_high
- Stores in ChromaDB with metadata: `{"anomaly_type": "<type>", "risk_level": "<level>"}`
- Validates all expected anomaly types are present
- Skips re-indexing if already up to date

**rag_retriever.py** (GL-112)
- Three retrieval functions with graceful error handling:
  - `retrieve_description_causes(anomaly_type)`: Returns description and causes
  - `retrieve_actions(anomaly_type, risk_level)`: Returns risk-appropriate actions
  - `retrieve_all(anomaly_type, risk_level)`: Returns both as dict
- Uses exact metadata filtering (not semantic search)
- Fallback messages for missing documents

**Integration** (GL-114, GL-135, GL-136)
- `build_context_with_rag()` in `context_injection.py` combines:
  - Model Layer output formatting
  - RAG knowledge retrieval
  - Confidence-based certainty guidance
  - Multi-signal correlation analysis
- Returns dict with `context`, `fault_knowledge`, and `actions_knowledge`

**Documentation:** See `docs/adr/303-rag-knowledge-base-design.md`

**Tests:** 33 test cases in `tests/test_rag_retriever.py` (GL-113)

---

## Dependencies

### Input: Model Layer Output

Consumes `ModelLayerOutput` from `shared/interface_models.py`:

```python
class ModelLayerOutput(BaseModel):
    timestamp: str                      # ISO 8601
    anomaly_type: str                   # e.g., "cooling_degradation"
    risk_score: float                   # 0.0 - 1.0
    risk_level: Optional[str]           # "Low" | "Medium" | "High"
    component: str                      # Mirrors anomaly_type
    prediction_confidence: float        # 0.0 - 1.0
    key_signals: List[KeySignal]        # Signal details
    estimated_cycles_to_failure: Optional[int]
    estimated_failure_probability: Optional[float]
    notes: List[str]                    # Empty list if no messages
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
    estimated_cycles_to_failure: Optional[int]       # None if not yet available
    estimated_failure_probability: Optional[float]   # None if not yet available
    notes: List[str]                                 # Empty list if no messages

    # Report Layer maintained
    risk_history: Optional[List[RiskHistoryEntry]]

    # Generated by Granite LLM
    anomaly_description: str
    possible_cause: str
    recommended_action: List[str]
```

See `docs/INTERFACE.md` Section 3 for complete field definitions.

### External Dependencies

- **Python Packages:** `pydantic`, `requests`, `chromadb`, `langchain`,
  `langchain-community`, `pyyaml` (see root `requirements.txt`)
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

### Run Scenario Evaluation (GL-30)

```bash
# Ensure Ollama is running with granite4.1:8b
ollama pull granite4.1:8b

# Run scenario evaluation
python report_layer/pipeline/scenario_evaluation.py

# Or explicitly choose baseline / RAG mode
python report_layer/pipeline/scenario_evaluation.py --mode rag
```

**Output:** `report_layer/evaluation/scenario_comparison.md`

### Run Tests

```bash
# Run all project tests
pytest tests/ -v

# Run RAG retriever tests
pytest tests/test_rag_retriever.py -v

# Run interface and dashboard data loading contract tests
pytest tests/test_interface.py tests/test_data_loader.py -v
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

See `evaluation/v2-model-selection/model_comparison.md` for detailed methodology.

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

## Remaining Work

**1. Unit Tests and Prompt Regression Tests** (P1)
- Broaden `report_generator.py` coverage: multi-layer failure, partial failure, and the GL-261 fallback-detection path
- Test Failure Projection present/null cases
- Test Model Layer Notes are treated as data-quality notes only
- Mock Ollama API for testing without live calls

**2. Integration Tests** (P1)
- Automated (mocked) end-to-end test for Data Layer → Model Layer → Report Layer → Dashboard — currently only verified once by hand with real data (real KIT CSV, real TTM inference, real Ollama call)
- Performance benchmarks

**3. Retrieval Re-verification** (P1)
- Re-run the metadata-filter vs. semantic-search comparison (`rag_baseline_comparison_table.md` §6) on the current 5-type knowledge base — the existing 100% accuracy / ~180x speed numbers were measured before two anomaly types were retired from the executable enum

### Deliberately Out of Scope

**Hosted/zero-install deployment** — considered (IBM watsonx.ai, Replicate's hosted `ibm-granite/granite-4.1-8b`) but not pursued: no IBM watsonx.ai access, and this is an unfunded summer project with no budget for paid hosted inference or a self-hosted server. The public dashboard demo shows curated pre-computed reports instead of live inference; the real upload-your-own-CSV pipeline is a documented local run (`setup.sh` / `setup.ps1`). See `docs/viva/report_challenge.md` Limitations for the full reasoning.

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
python report_layer/evaluation/v2-model-selection/model_comparison.py
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
