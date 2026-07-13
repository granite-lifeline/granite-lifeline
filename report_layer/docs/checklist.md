# Report Layer Checklist

Last updated: 2026-07-13
Aligned with `INTERFACE.md` v0.7 and GL-213 prompt rule updates.

## Interface Check

- Model Layer input follows `ModelLayerOutput` in `INTERFACE.md` v0.7.
- Required pass-through fields are present:
  - `timestamp`
  - `risk_score`
  - `risk_level`
  - `component`
  - `prediction_confidence`
  - `key_signals`
  - `estimated_cycles_to_failure`
  - `estimated_failure_probability`
  - `notes`
- `estimated_cycles_to_failure` and `estimated_failure_probability` are allowed to be `null`.
- If failure prediction fields are `null`, the report does not invent cycle counts, dates, mileage, or failure probability.
- `notes` is always treated as Model Layer validation or fallback information, not as a mechanical fault cause.
- `key_signals` uses only `feature`, `value`, `unit`, and `reference_range`.
- Report Layer output follows `ReportLayerOutput` in `INTERFACE.md` v0.7.
- Generated fields are present:
  - `anomaly_description`
  - `possible_cause`
  - `recommended_action`
- Report Layer maintained field `risk_history` is passed through when available.
- The final output does not include fields outside `INTERFACE.md`.

## RAG Grounding Check

- Retrieved fault knowledge is used only as supporting background.
- The input context is treated as the main source of truth.
- If retrieved fault knowledge conflicts with sensor data or risk fields, the report follows the input context.
- Layer 2 does not use a knowledge-base cause unless the current context supports it.
- Layer 3 does not use a retrieved action if it does not match the current risk level or key signals.
- If no matching RAG knowledge is found, the report still uses the input context and gives a safe fallback explanation or action.

## Prompt Check

- Layer 1 only describes what the data shows.
- Layer 1 does not include possible causes or repair actions.
- Layer 2 uses careful words like "may indicate", "could suggest", or "could be related to".
- Layer 2 does not say the cause is confirmed.
- Layer 3 gives 2 to 4 clear actions for the vehicle owner.
- High risk gives prompt but calm action wording.
- Medium risk suggests checking the vehicle soon.
- Low risk gives monitoring or simple check wording.
- Low confidence avoids sounding too certain.
- High confidence may use stronger predictive wording, but still does not confirm a real fault.
- Failure Projection values are mentioned only when present in context.
- Model Layer Notes are used only to explain data-quality limits when helpful.
- The prompt does not ask the model to create missing values.

## JSON Output Check

- Each layer returns exactly one valid JSON object.
- The output does not include Markdown, code fences, commentary, or extra keys.
- Layer 1 returns only:
  - `anomaly_description`
- Layer 2 returns only:
  - `possible_cause`
- Layer 3 returns only:
  - `recommended_action`
- `recommended_action` is a JSON array with 2 to 4 plain strings.
- Output can be parsed automatically without manual cleanup.

## Plain Language Check

- The report is understandable for a non-technical vehicle owner.
- Technical terms are explained if they are used.
- Raw field names are avoided in user-facing text when possible.
- The report avoids saying a fault is confirmed.
- The user can understand what is happening.
- The user can understand how urgent it is.
- The user can understand what to do next.

## Safety Check

- The report does not cause unnecessary panic.
- The report does not recommend unsafe roadside actions.
- The report does not tell the user to keep driving normally when risk is High.
- For High risk, the report suggests prompt inspection and avoiding heavy driving if safe.
- If evidence is limited, the report says so and recommends monitoring or collecting more data.
