# Sample Report Review for Non-Technical Wording

This document supports GL-58: Review sample reports for non-technical wording.

The review uses the terminology checklist in
`report_layer/docs/terminology_checklist.md`.

## Review Criteria

- The report avoids unexplained technical jargon.
- Any necessary technical term is explained in plain language.
- The report does not show raw field names to the vehicle owner.
- The report explains what is happening.
- The report explains how serious it is.
- The recommended actions are concrete and specific.
- The report does not claim that a real mechanical fault is confirmed.

## Sample 1: Typical Cooling Degradation

Source input:
`report_layer/evaluation/typical_cooling_stress.json`

### Sample report

Risk level: High

Prediction confidence: 87%

Anomaly description:
The engine coolant temperature is higher than the normal range. It is 102 C,
while the expected range is 90 C to 95 C. High risk means the vehicle may need
prompt attention.

Possible cause:
This could be related to cooling system degradation. For example, the vehicle
may have low coolant, a radiator problem, or another cooling system issue. The
data does not confirm the exact fault, but the temperature reading is clearly
higher than expected.

Recommended action:
- Avoid heavy driving if it is safe to do so.
- Check the coolant level only when the engine is cool.
- Ask a mechanic to inspect the cooling system as soon as possible.

### Non-technical wording review

| Check | Result |
|---|---|
| No unexplained jargon | Pass |
| No raw field names shown to owner | Pass |
| Risk level explained in practical words | Pass |
| Recommended actions are specific | Pass |
| Does not claim confirmed fault | Pass |

Review note:
This sample is suitable for a non-technical vehicle owner. The report uses
"engine coolant temperature" and "cooling system" instead of raw field names.

## Sample 2: Atypical Cooling Degradation

Source input:
`report_layer/evaluation/atypical_cooling_stress.json`

### Sample report

Risk level: Medium

Prediction confidence: 51%

Anomaly description:
The system shows medium risk for the cooling system, but the engine coolant
temperature is still inside the normal range. It is 93 C, while the expected
range is 90 C to 95 C. This means the evidence is not strong enough to say the
cooling system is definitely abnormal.

Possible cause:
This could be an early warning or a model uncertainty issue. The temperature
reading does not strongly support a cooling fault right now, so the result
should be treated carefully.

Recommended action:
- Continue monitoring the dashboard for repeated warnings.
- If the warning appears again, ask a mechanic to check the cooling system.
- Do not assume there is a confirmed fault based on this single reading.

### Non-technical wording review

| Check | Result |
|---|---|
| No unexplained jargon | Pass |
| No raw field names shown to owner | Pass |
| Risk level explained in practical words | Pass |
| Recommended actions are specific | Pass |
| Does not claim confirmed fault | Pass |

Review note:
This sample is suitable for a non-technical vehicle owner because it clearly
explains that the evidence is limited. The wording avoids sounding too certain.

## Sample 3: Contradictory Cooling Degradation

Source input:
`report_layer/evaluation/contradictory_cooling_stress.json`

### Sample report

Risk level: Low

Prediction confidence: 31%

Anomaly description:
The engine coolant temperature is much higher than the normal range. It is
108 C, while the expected range is 90 C to 95 C. However, the system confidence
is low, so the report should be treated as a warning that needs checking rather
than a confirmed diagnosis.

Possible cause:
The high temperature reading could be related to a cooling system issue, but the
low system confidence means the evidence is not fully reliable. It may also be
worth checking whether the sensor reading is accurate.

Recommended action:
- Avoid heavy driving until the temperature reading is checked.
- Let the engine cool before checking coolant level.
- Ask a mechanic to inspect the cooling system and confirm whether the
  temperature reading is reliable.

### Non-technical wording review

| Check | Result |
|---|---|
| No unexplained jargon | Pass |
| No raw field names shown to owner | Pass |
| Risk level explained in practical words | Pass |
| Recommended actions are specific | Pass |
| Does not claim confirmed fault | Pass |

Review note:
This sample is suitable for a non-technical vehicle owner. It explains the
contradiction between a high temperature reading and low system confidence in
simple wording.

## Overall GL-58 Result

All three sample reports pass the non-technical wording review.

The reports:

- avoid unexplained technical jargon;
- avoid raw field names such as `coolant_temp`;
- explain risk in practical language;
- give concrete next steps;
- avoid claiming that a real mechanical fault is confirmed.
