# Report Quality Evaluation - GL-140

Automated quality assessment of generated diagnostic reports.

---

## Summary

| Anomaly Type | Risk Level | Factual Grounding | Readability | Hedging | Actionability | Overall |
|--------------|------------|-------------------|-------------|---------|---------------|----------|
| typical_cooling_stress | High | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| atypical_cooling_stress | Medium | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| contradictory_cooling_stress | Low | 1.00 | 1.00 | 0.60 | 1.00 | 0.90 |

---

## Detailed Evaluation

### typical_cooling_stress (High risk)

**Overall Score:** 1.00

**Notes:**

- Factual Grounding: 1.00
- anomaly_description references specific signal values from context
- Readability: 1.00
- Average sentence length is 10.9 words (acceptable)
- Hedging: 1.00
- Uses appropriate hedging: might
- Actionability: 1.00
- 4 actions provided (appropriate)
- Contains High risk urgency language: soon

### atypical_cooling_stress (Medium risk)

**Overall Score:** 1.00

**Notes:**

- Factual Grounding: 1.00
- anomaly_description references specific signal values from context
- Readability: 1.00
- Average sentence length is 14.7 words (acceptable)
- Hedging: 1.00
- Uses appropriate hedging: could suggest, might
- Actionability: 1.00
- 4 actions provided (appropriate)
- Contains Medium risk urgency language: check, inspect

### contradictory_cooling_stress (Low risk)

**Overall Score:** 0.90

**Notes:**

- Factual Grounding: 1.00
- Readability: 1.00
- Average sentence length is 19.2 words (acceptable)
- Hedging: 0.60
- possible_cause lacks hedging language (may indicate, could suggest, etc.)
- Actionability: 1.00
- 4 actions provided (appropriate)
- Contains Low risk urgency language: monitor

