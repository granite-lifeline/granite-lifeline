# ADR 302: Granite LLM Model Selection for Diagnostic Report Generation

## Status

Accepted

## Date

2026-06-23

## Context

The Report Layer needs to select a Granite LLM for generating three-section diagnostic reports (anomaly description, possible cause, recommended action) from context-injected OBD-II sensor data. The model must produce plain-language output suitable for non-technical vehicle owners while maintaining high accuracy and reliability.

Four candidate models were evaluated using a typical cooling system stress scenario (coolant_temp 102°C, risk_score 82%, risk_level High) with the three-layer prompt chain developed in GL-55:

- **granite3.3:2b** - Granite 3.3 series, 2 billion parameters
- **granite3.3:8b** - Granite 3.3 series, 8 billion parameters
- **granite4.1:3b** - Granite 4.1 series, 3 billion parameters
- **granite4.1:8b** - Granite 4.1 series, 8 billion parameters

All models are IBM Granite instruct variants available via Ollama for local development and IBM watsonx.ai for production deployment.

## Decision

**granite4.1:8b** is selected as the primary model for the Granite Lifeline diagnostic report generation pipeline.

**granite4.1:3b** is noted as a viable fallback if inference speed or hardware constraints become a factor in later sprints.

## Evaluation Framework

A weighted scoring framework was applied across five dimensions informed by academic research on LLM-based fault diagnosis systems:

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| **Plain language quality** | 30% | Core Story 3 AC: report must be understandable by non-technical vehicle owners |
| **Specificity and data grounding** | 25% | Story 2 AC1: report must reference actual sensor values; prevents faithfulness hallucination |
| **JSON parse success rate** | 20% | Determines pipeline reliability; parse failure breaks the three-layer chain |
| **Recommended action quality** | 15% | Story 1 AC3/AC4: actions must be concrete, specific, and matched to risk level |
| **Avoiding over-certainty** | 10% | Model output is a prediction, not confirmed diagnosis; prevents overclaim hallucination |

**Theoretical foundation:**
- Qi et al. (2025): LLM-based fault diagnosis systems should be evaluated across task-level output quality, process quality, and human-AI collaboration efficiency
- Huang et al. (2025): Distinguishes between faithfulness hallucination (unfaithful use of context) and factuality hallucination (unsupported claims)

## Evaluation Results

| Dimension | Weight | granite3.3:2b | granite3.3:8b | granite4.1:3b | granite4.1:8b |
|-----------|--------|---------------|---------------|---------------|---------------|
| Plain language quality | 30% | 3 | 4 | 4 | **5** |
| Specificity and data grounding | 25% | 4 | 4 | 4 | **5** |
| JSON parse success rate | 20% | 2 | 5 | 5 | **5** |
| Recommended action quality | 15% | 3 | 3 | 4 | **5** |
| Avoiding over-certainty | 10% | 4 | 4 | 4 | 4 |
| **Weighted Total** | **100%** | **3.15** | **4.05** | **4.15** | **4.85** |

**Scoring scale:** 1-5 (1 = Poor, 5 = Excellent)

Full evaluation results and qualitative analysis are documented in `report_layer/evaluation/model_comparison.md`.

## Rationale

granite4.1:8b achieved the highest weighted score (4.85/5.00) across all five evaluation dimensions. Key differentiators over other candidates:

### Output Quality
- Produced the most specific and actionable recommended actions, including precise guidance such as "wait 30 minutes before checking coolant" and "locate the MIN/MAX marks on the reservoir"
- Demonstrated superior plain language quality with clear explanations suitable for non-technical vehicle owners
- Consistently referenced actual sensor values (102.0°C) and reference ranges (90.0-95.0°C) in all three report sections

### Technical Reliability
- Successfully parsed valid JSON for all three prompt layers without error, ensuring pipeline reliability
- 100% JSON parse success rate across the three-layer chain (layer 1: anomaly_description, layer 2: possible_cause, layer 3: recommended_action)

### Model Maturity
- Uses the most recent IBM Granite version (4.1), consistent with IBM's recommendation to use production-ready instruct models
- Latest version benefits from improved instruction-following and reduced hallucination rates

### Alignment with Requirements
- Output quality aligns with Qi et al. (2025) evaluation criteria for LLM-based fault diagnosis: task-level output quality, process quality, and human-AI collaboration efficiency
- Avoids over-certainty through appropriate hedging language ("may indicate", "could suggest"), addressing Huang et al. (2025) factuality hallucination concerns

### Eliminated Candidates
- **granite3.3:2b**: JSON parse failure on layer 2 (multi-line string in JSON value) and lower action quality scores (weighted total: 3.15)
- **granite3.3:8b**: Acceptable performance but less specific guidance compared to 4.1 series (weighted total: 4.05)
- **granite4.1:3b**: Strong performance and viable fallback option, but slightly lower specificity than 8B variant (weighted total: 4.15)

## Consequences

### Positive

- **High-quality reports**: granite4.1:8b produces the most actionable and specific diagnostic reports for non-technical vehicle owners
- **Pipeline reliability**: 100% JSON parsing success ensures stable three-layer prompt chain execution
- **Future-proof**: Latest Granite version (4.1) provides foundation for future enhancements
- **Reusable methodology**: Weighted evaluation framework can be applied to future model selection decisions

### Negative

- **Inference cost**: 8B parameter model requires more computational resources than smaller variants
- **Latency**: Larger model may have higher inference latency compared to 3B variants
- **Hardware requirements**: May require GPU acceleration for acceptable performance in production

### Mitigation Strategies

- granite4.1:3b is documented as a viable fallback if inference speed or hardware constraints become critical
- Production deployment via IBM watsonx.ai provides managed infrastructure with optimized inference
- Future optimization work can explore quantization or distillation if performance becomes a bottleneck

## Implementation

### Development Environment
- Model: `granite4.1:8b` via Ollama
- API endpoint: `http://localhost:11434/api/generate`
- Configuration: `stream=False` for synchronous responses

### Production Environment
- Model: IBM Granite 4.1 8B instruct via IBM watsonx.ai
- A try/except pattern will be implemented in a future sprint to support switching between Ollama (development) and watsonx.ai (production) without code changes

### Code Location
- Primary implementation: `report_layer/pipeline/report_generator.py` (to be implemented)
- Model comparison script: `report_layer/pipeline/model_comparison.py`
- Evaluation results: `report_layer/evaluation/model_comparison.md`

## Related Decisions

- ADR 301: Context Injection Design for Granite LLM Prompt
- GL-55: Three-layer prompt template design
- GL-76: Model comparison evaluation

## References

- Qi et al. (2025). Large Language Models for Fault Diagnosis. 2025 IEEE International Conference on Big Data.
- Huang et al. (2025). A Survey on Hallucination in Large Language Models. ACM Transactions on Information Systems.
- IBM Granite 4.1 Language Models: https://huggingface.co/collections/ibm-granite/granite-41-language-models
- Full evaluation results: `report_layer/evaluation/model_comparison.md`