# RAG Language Quality Review - GL-117

This document reviews the GL-116 RAG sample reports for plain language and
safe diagnostic wording.

Reviewed file:

- `report_layer/docs/rag_sample_reports.md`

## Review Criteria

The review uses the same owner-facing wording rules as
`report_layer/docs/checklist.md` and
`report_layer/docs/terminology_checklist.md`.

| Check | Meaning |
|---|---|
| Plain language | A non-technical vehicle owner can understand the report. |
| No raw fields | The report avoids raw field names such as `coolant_temp` or `risk_score`. |
| Technical terms explained or replaced | Terms such as MAF and OBD2 are replaced with clearer wording. |
| No confirmed fault claims | The report does not say a predicted issue is a confirmed mechanical fault. |
| Concrete actions | Recommended actions tell the owner what to do next. |
| Risk-appropriate wording | High risk sounds urgent, medium risk suggests checking soon, and low risk suggests monitoring. |

## Sample 1: Cooling System High Risk

| Check | Result | Note |
|---|---|---|
| Plain language | Pass | Uses "engine coolant temperature" and "cooling system". |
| No raw fields | Pass | Does not show raw interface names. |
| Technical terms explained or replaced | Pass | Uses familiar terms such as coolant, radiator, thermostat, fan, and water pump. |
| No confirmed fault claims | Pass | Says "may indicate", "possible reasons", and "does not confirm". |
| Concrete actions | Pass | Advises avoiding heavy driving, cooling the engine first, and asking a mechanic to inspect named parts. |
| Risk-appropriate wording | Pass | High risk is described as needing prompt attention without causing panic. |

## Sample 2: Air Intake Medium Risk

| Check | Result | Note |
|---|---|---|
| Plain language | Pass | Uses "airflow reading", "air filter", and "airflow sensor". |
| No raw fields | Pass | Does not show raw signal names such as `maf` or `map`. |
| Technical terms explained or replaced | Pass | Replaces "MAF sensor" with "airflow sensor" and "scan tool" with "diagnostic scan tool". |
| No confirmed fault claims | Pass | Says "could suggest", "possible causes", and "not a confirmed mechanical blockage". |
| Concrete actions | Pass | Gives specific checks for the air filter, sensor wiring, connector, and repeated warnings. |
| Risk-appropriate wording | Pass | Medium risk is framed as "should be checked soon" rather than urgent danger. |

## Sample 3: Accelerator Pedal Low Risk

| Check | Result | Note |
|---|---|---|
| Plain language | Pass | Explains the two pedal readings and says the difference is small. |
| No raw fields | Pass | Does not show raw field names such as `accel_pedal_d`. |
| Technical terms explained or replaced | Pass | Uses "diagnostic scan tool" and "stored warning codes" instead of unexplained OBD2 wording. |
| No confirmed fault claims | Pass | Says readings do not strongly support a confirmed sensor fault. |
| Concrete actions | Pass | Advises monitoring, checking warning codes, and inspecting signals/wiring if pedal response feels unusual. |
| Risk-appropriate wording | Pass | Low risk is handled as monitoring, not immediate repair. |

## Wording Improvements Made

During review, the air intake and accelerator pedal samples were adjusted to
improve owner-facing clarity:

| Original wording | Updated wording | Reason |
|---|---|---|
| MAF sensor | airflow sensor | Easier for a non-technical owner to understand. |
| MAF sensor live data | airflow sensor readings | Avoids unexplained acronym. |
| OBD2 scan tool | diagnostic scan tool | More familiar wording. |
| diagnostic trouble codes | stored warning codes | Avoids repair-shop jargon. |

## GL-117 Result

All three RAG sample reports pass the language quality review.

The reports:

- use plain language for a vehicle owner;
- avoid raw interface field names;
- replace or explain technical terms;
- use careful wording such as "may indicate" and "could suggest";
- do not present predictions as confirmed faults;
- provide concrete next steps matched to risk level.
