# Report Prompt Regression Checklist

This checklist converts manual prompt-review findings into repeatable
regression criteria for Granite Lifeline report outputs.

Scope:

- `anomaly_description`
- `possible_cause`
- `recommended_action`
- dashboard-visible `notes`

The raw Model Layer JSON may still contain technical provenance details. This
checklist applies to owner-facing Report Layer output.

## Owner-Facing Language

- Do not expose internal pipeline filenames such as `proxy_decisions.csv`.
- Do not expose raw diagnostic trouble codes such as `P0113` or `P0106`.
- Do not use unexplained acronyms such as `DTC` or `IAT`.
- Avoid pipeline wording such as `this window`.
- Avoid vague timing such as `near future` when a concrete horizon is present.
- Avoid clunky example notation such as `e.g.` or `i.e.`; use natural wording
  like "such as rough idle or hesitation."
- Do not include Markdown emphasis markers in generated text.

## Projection Semantics

- Treat `risk_score` as current anomaly severity, not future mechanical
  failure probability.
- Treat `estimated_failure_probability` as the model-estimated probability of
  crossing the High-risk threshold within the stated horizon, not a calibrated
  mechanical failure probability.
- Do not convert model probabilities into odds or per-trip language.
- If projected probability is very low and no cycle estimate exists, do not
  say the component is likely to fail soon.

## Signal Consistency

- If all key signals are `NORMAL`, generated text must not say a signal is
  outside its normal range.
- If any key signal is `ABNORMAL`, generated text must not say current readings
  are all normal.
- If a proxy-forwarded case has normal displayed key signals, describe the rule
  as evidence to verify, not proof of a confirmed fault.
- If a proxy-forwarded case has abnormal displayed key signals, acknowledge the
  abnormal signal rather than using normal-signal proxy wording.

## Section Boundaries

- `anomaly_description` should explain what was detected and how urgent it is.
- `possible_cause` should explain plausible reasons without repeating exact
  values, full signal lists, risk level, or projection details already stated
  in `anomaly_description`.
- `possible_cause` should not end with generic monitoring advice; put monitoring
  guidance in `recommended_action`.
- `recommended_action` should provide 2 to 4 concrete owner actions.

## Action Safety

- For Low risk, prefer monitoring, rechecking, and simple visual checks unless
  strong abnormal evidence exists.
- For Medium risk, suggest checking the vehicle soon.
- For High risk, recommend prompt diagnostic confirmation or inspection, while
  avoiding unnecessary panic.
- For proxy-forwarded cases with normal displayed key signals and very low
  projected probability, do not recommend immediate part replacement or heavy
  driving restrictions unless symptoms or abnormal signals are present.
- If key signals are normal, action text must not tell the owner or mechanic
  that the sensor is outside its normal range.
