# Report Layer Checklist

## Interface Check

- Model Layer input uses only timestamp, anomaly_type, risk_score, risk_level, component, prediction_confidence, and key_signals.
- Report Layer output uses only timestamp, risk_score, risk_level, component, prediction_confidence, key_signals, risk_history, anomaly_description, possible_cause, and recommended_action.
- key_signals uses only feature, value, unit, and reference_range.
- The final report does not include anomaly_type because Dashboard output does not list it.
- The final report does not include any field outside INTERFACE.md.

## Prompt Check

- Layer 1 only describes what the data shows.
- Layer 2 uses careful words like "may indicate" or "could suggest".
- Layer 3 gives clear actions for the vehicle owner.
- High risk gives stronger action wording.
- Low risk gives monitoring or simple check wording.
- Low confidence avoids sounding too certain.

## Plain Language Check

- The report is understandable for a non-technical vehicle owner.
- Technical terms are explained if they are used.
- The report avoids saying a fault is confirmed.
- The user can understand what is happening.
- The user can understand how urgent it is.
- The user can understand what to do next.
