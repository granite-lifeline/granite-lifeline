# Report Quality Evaluation - GL-140

Automated quality assessment of generated diagnostic reports.

---

## Summary

| Anomaly Type | Risk Level | Factual Grounding | Readability | Hedging | Actionability | Overall |
|--------------|------------|-------------------|-------------|---------|---------------|----------|
| typical_cooling_stress | High | 1.00 | 0.70 | 1.00 | 0.70 | 0.85 |
| atypical_cooling_stress | Medium | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| contradictory_cooling_stress | Low | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

---

## Detailed Evaluation

### typical_cooling_stress (High risk)

**Overall Score:** 0.85

**Notes:**

- Factual Grounding: 1.00
- Readability: 0.70
- Contains unexplained raw field names: coolant_temp
- Average sentence length is 20.5 words (acceptable)
- Hedging: 1.00
- Uses appropriate hedging: may indicate
- Actionability: 0.70
- 4 actions provided (appropriate)
- Lacks High risk urgency language (expected: soon, prompt, immediately)

### atypical_cooling_stress (Medium risk)

**Overall Score:** 1.00

**Notes:**

- Factual Grounding: 1.00
- anomaly_description references specific signal values from context
- Readability: 1.00
- Average sentence length is 16.0 words (acceptable)
- Hedging: 1.00
- Uses appropriate hedging: could suggest, might
- Actionability: 1.00
- 4 actions provided (appropriate)
- Contains Medium risk urgency language: check, inspect

### contradictory_cooling_stress (Low risk)

**Overall Score:** 1.00

**Notes:**

- Factual Grounding: 1.00
- anomaly_description references specific signal values from context
- Readability: 1.00
- Average sentence length is 14.0 words (acceptable)
- Hedging: 1.00
- Uses appropriate hedging: may indicate
- Actionability: 1.00
- 4 actions provided (appropriate)
- Contains Low risk urgency language: monitor

