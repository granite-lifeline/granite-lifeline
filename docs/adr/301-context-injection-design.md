# ADR 301: Context Injection Design for Granite LLM Prompt

## Status

Accepted

## Context

The Report Layer needs to format Model Layer output (ModelLayerOutput) into a structured text string before injecting it into the Granite LLM three-layer prompt chain. The format of this context string directly affects the quality and specificity of the generated diagnostic reports.

## Decision

The `build_context()` function in `report_layer/pipeline/context_injection.py` formats ModelLayerOutput into structured sections with the following rules:

1. Output uses labelled sections (Vehicle Status / Key Signals) rather than plain paragraphs or bullet points
2. `risk_score` and `prediction_confidence` are converted to percentages (e.g., 0.82 → 82%) for more natural language generation
3. Each key signal is explicitly labelled ABNORMAL or NORMAL by comparing its value against `reference_range` bounds
4. Unit is omitted if empty or None

## Rationale

**Structured sections** make it easier for Granite to identify which part of the context to reference when generating each section of the diagnostic report. The clear separation between Vehicle Status and Key Signals allows the LLM to distinguish between high-level risk information and detailed signal-level diagnostics.

**Percentage conversion** produces more natural language output (e.g., "confidence of 82%" rather than "confidence of 0.82"). This aligns with how humans typically express probabilities and makes the generated reports more readable.

**Explicit ABNORMAL/NORMAL labelling** is required by Diagnostic Report Generation Story 2 AC3 — without it, Granite cannot reliably distinguish typical from atypical fault scenarios, which is the core test of Story 2. By pre-computing the abnormality status in the context injection layer, we ensure consistent signal classification across all three prompt layers.

**Unit omission** prevents awkward formatting like "35.0 (reference: 0.0-100.0)" when units are not applicable or unknown. This keeps the context string clean and focused on the data values.

## Alternatives Considered

### Plain Paragraph Format

**Rejected.** A plain paragraph format (e.g., "The vehicle has a cooling_system_stress anomaly with risk score 0.82 and confidence 0.84. The coolant_temp signal is 102°C...") was considered but rejected because it makes it harder for Granite to locate specific data points when generating targeted sections of the report. The structured format with clear labels acts as a lightweight schema that guides the LLM's attention.

### Only Listing Anomalous Signals

**Rejected.** Omitting normal signals and only including abnormal ones was considered to reduce context length. However, Story 2 AC3 requires the report to describe which signals are normal and which are abnormal — omitting normal signals would prevent Granite from making this distinction. Including all signals provides complete context for the LLM to generate comprehensive diagnostic explanations.

### Letting Granite Judge Abnormality

**Rejected.** Leaving ABNORMAL/NORMAL unlabelled and letting Granite judge based on the raw values and reference ranges was considered to reduce preprocessing. However, this introduces instability in the output across repeated runs, as the LLM might interpret the same signal differently depending on prompt variations or model temperature. Pre-computing the status ensures deterministic classification.

## Consequences

### Positive

- The context format is now a defined contract between `context_injection.py` and the prompt templates in `report_layer/prompts/`
- Signal abnormality classification is deterministic and testable
- The structured format makes it easier to debug prompt issues by inspecting the injected context
- Percentage formatting improves readability of generated reports

### Negative

- Any changes to the output format of `build_context()` may require corresponding updates to the prompt templates
- The function assumes `reference_range` is always a two-element list `[lower, upper]` — if this changes, the abnormality logic must be updated
- Unit handling assumes empty string or None for missing units — other sentinel values (e.g., "N/A") would require code changes

## Related Decisions

- ModelLayerOutput structure is defined in `shared/interface_models.py` and `docs/INTERFACE.md` v0.2
- The ABNORMAL/NORMAL labelling requirement derives from the need for diagnostic reports to distinguish typical from atypical fault scenarios — a core requirement of the Diagnostic Report Generation epic