# Readability Evaluation and Improvements

This document supports GL-59: Document readability issues and improvements.

It records readability problems found while reviewing the sample diagnostic
reports and explains how the wording was improved for a non-technical vehicle
owner.

Related files:

- `report_layer/docs/terminology_checklist.md`
- `report_layer/docs/sample_report_review.md`
- `report_layer/prompts/layer1_description.txt`
- `report_layer/prompts/layer2_cause.txt`
- `report_layer/prompts/layer3_action.txt`

## Evaluation Goal

The diagnostic report should help a vehicle owner understand:

- what is happening;
- how serious it is;
- why it may be happening;
- what action to take next.

The report should not require the owner to understand Model Layer or Data Layer
terms.

## Issue 1: Raw Field Names Could Confuse Vehicle Owners

Original issue:

Some model output fields use technical names such as `coolant_temp`,
`risk_score`, `prediction_confidence`, and `key_signals`.

Why this is a problem:

A non-technical vehicle owner may not know these names. If the report shows raw
field names, the report feels like a data dump instead of a helpful diagnostic
summary.

Improvement:

The sample reports use plain-language replacements:

| Raw term | Improved wording |
|---|---|
| `coolant_temp` | engine coolant temperature |
| `risk_score` | risk estimate |
| `prediction_confidence` | system confidence |
| `key_signals` | important readings |

Result:

The report now explains the same information without requiring the owner to
understand raw interface fields.

## Issue 2: Technical Terms Needed Simple Explanations

Original issue:

Technical terms such as "cooling system stress" and "sensor reading" could be
unclear if used without context.

Why this is a problem:

The user story asks for plain language, so necessary technical terms should be
explained or replaced with simpler wording.

Improvement:

The terminology checklist was used to guide replacements. For example:

- "cooling_system_stress" became "cooling system issue".
- "sensor reading" was written as "temperature reading" where possible.
- "reference range" was explained as "normal range".

Result:

The report still contains useful diagnostic meaning, but the wording is easier
for a vehicle owner to understand.

## Issue 3: The Report Could Sound Too Certain

Original issue:

Some diagnostic wording could sound like the system has confirmed a real fault.

Why this is a problem:

The model output is a prediction, not a confirmed mechanical diagnosis. If the
report sounds too certain, the vehicle owner may misunderstand the result.

Improvement:

The possible cause section uses careful wording such as:

- "could be related to";
- "may indicate";
- "does not confirm the exact fault";
- "the evidence is not strong enough".

Result:

The report now explains possible causes without pretending that the fault is
confirmed.

## Issue 4: Recommended Actions Could Be Too Vague

Original issue:

Advice such as "check related components" is too general.

Why this is a problem:

A vehicle owner may not know what "related components" means or what action to
take next.

Improvement:

The recommended actions were changed to concrete steps, such as:

- "Check the coolant level only when the engine is cool."
- "Ask a mechanic to inspect the cooling system as soon as possible."
- "Continue monitoring the dashboard for repeated warnings."

Result:

The owner can understand what to do next without needing extra technical
knowledge.

## Issue 5: Conflicting Evidence Needed Clear Explanation

Original issue:

The contradictory cooling case has a high temperature reading but low system
confidence. This could confuse the owner if the report only says "Low risk".

Why this is a problem:

The owner might ignore a high temperature reading because the risk level is low,
or they might panic because the temperature is high.

Improvement:

The sample report explains both sides:

- the engine coolant temperature is much higher than normal;
- the system confidence is low;
- the result should be treated as a warning that needs checking, not a confirmed
  diagnosis.

Result:

The report gives a balanced explanation and still recommends a practical next
step.

## Before and After Examples

| Before | After |
|---|---|
| `coolant_temp is 102 C` | The engine coolant temperature is 102 C. |
| `risk_score is high` | High risk means the vehicle may need prompt attention. |
| `possible cooling_system_stress` | This could be related to a cooling system issue. |
| `check related components` | Ask a mechanic to inspect the cooling system. |
| `prediction_confidence is low` | The system confidence is low, so the result should be treated carefully. |

## Final Evaluation Result

The GL-58 sample reports were updated and reviewed using the GL-57 terminology
checklist.

Final result:

- The reports avoid unexplained technical jargon.
- The reports avoid raw field names in owner-facing text.
- The reports explain risk level in practical words.
- The reports use careful wording for possible causes.
- The reports provide concrete recommended actions.
- The reports are suitable for a non-technical vehicle owner.
