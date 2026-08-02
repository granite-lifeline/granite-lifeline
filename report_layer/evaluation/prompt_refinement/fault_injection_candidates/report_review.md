# Selected Window Report Review

Generated from:

```text
report_layer/evaluation/prompt_refinement/fault_injection_candidates/
  selected_window_model_outputs/
  selected_window_reports/
```

## Coverage

The selected window report set covers all five current anomaly types:

- `cooling_degradation`
- `air_intake_maf_anomaly`
- `accelerator_pedal_sensor`
- `intake_air_temperature_sensor_fault`
- `map_load_signal_plausibility_fault`

The IAT and MAP examples come from Data Layer fault-injection
`proxy_decisions.csv` evidence forwarded by the Model Layer. They are not
native TTM residual top-summary cases.

## Prompt Issues Found

1. Failure projection wording can be misleading.

   Several selected cases have `estimated_failure_probability: 0.0031` and
   `estimated_cycles_to_failure: null`. The report should describe this as a
   very low model-estimated probability of crossing the High-risk threshold
   within the configured horizon, not as "no failure probability".

2. Low-risk descriptions can sound too certain.

   The low-risk cooling case used wording like "showing signs of degradation"
   even though `risk_level` is `Low` and `risk_score` is about `0.18`. Low-risk
   cases should be framed as weak or early patterns, not active degradation.

3. Proxy-forwarded provenance is not explicit enough.

   The IAT and MAP reports mention fault indications, but they do not clearly
   explain that the case was forwarded from Data Layer rule-based
   `proxy_decisions.csv` evidence rather than native TTM residual scoring.

4. Normal key signals need more careful handling.

   The IAT case has high proxy risk, but its listed key signals are mostly
   within reference range. The report should say the rule/proxy evidence may
   reflect an intermittent or decision-level diagnostic pattern, instead of
   implying that the displayed window signals alone prove the issue.

5. Cause wording sometimes overreaches.

   The low-risk cooling report suggested specific mechanical causes too
   strongly. Prompt wording should prevent unsupported claims such as a
   specific thermostat failure mode unless the signal direction supports it.

6. Cause sections can repeat description content.

   The MAF possible-cause section repeated the description's exact signal
   value, normal range, Low risk level, and `0.31%` projection. Cause sections
   should be shorter and explain what the pattern may mean, instead of
   re-listing the same evidence from the anomaly description.

7. MAF wording should preserve useful vehicle terminology.

   Manual review decided that `mass airflow sensor` is acceptable report text
   for this project audience. The report should not force a parenthetical
   explanation every time. Dashboard glossary/tooltip treatment is a better
   place to help users who do not know the term.

8. Low-risk cause sections should start with concrete explanations.

   For the MAF case, the sentence "This may indicate a minor early variation"
   did not connect clearly to the rest of the section. Low-risk cause text
   should start directly with possible explanations and avoid ending with a
   repeated "monitor without immediate concern" summary.

9. Action text should avoid clunky parenthetical punctuation.

   Prefer natural wording such as "such as rough idle or hesitation" instead
   of parenthetical forms like "(e.g., rough idle, hesitation)". Do not use
   `e.g.` or `i.e.` in owner-facing action text.

10. Risk level must stay consistent across sections.

   The accelerator-pedal possible-cause section changed a Medium-risk case to
   Low risk. `possible_cause` should avoid restating risk level by default; if
   it does mention risk, it must exactly match the input context. Normal key
   signal readings must not cause the report to downgrade the Model Layer
   risk level.

11. `possible_cause` may be too close to `anomaly_description`.

   Manual review questioned whether the sections are distinct enough. Keep the
   field because the interface/dashboard expects "what happened / why / what
   should I do", but make `possible_cause` shorter: 1-3 concise sentences that
   explain plausible reasons without repeating signal values, risk level, or
   probability.

12. Failure projection horizons must be specific.

   The accelerator-pedal description used "in the near future" even though the
   Model Layer notes provide a specific horizon: `within the next 10 trips`.
   Reports should use the exact horizon when available and avoid vague time
   phrases. Reports also should not convert model probabilities into odds or
   per-trip wording such as "1 in 322 trips"; preserve the model-provided
   percentage and horizon.

13. Dual-channel sensor wording needs plain-language framing.

   `Channel D` and `Channel E` are not immediately meaningful to a normal
   vehicle owner. Reports should first describe them as the two internal
   sensors inside the accelerator pedal, and only include raw channel labels
   after that if useful.

14. `possible_cause` should not end with generic monitoring advice.

   Cause text should end after explaining plausible reasons. Sentences such as
   "this pattern warrants monitoring" repeat the description/action sections
   and make the section feel less distinct.

15. Owner-facing report text should not expose diagnostic codes or pipeline files.

   The IAT proxy-forwarded report exposed `P0113` and `proxy_decisions.csv`.
   These are useful technical provenance details, but they make the main
   report harder for a normal vehicle owner to read. Prompt rules should
   preserve the meaning as "rule-based Data Layer evidence" or "a rule-based
   diagnostic flag" while leaving exact codes and filenames for a technical
   details view.

16. Proxy-forwarded actions should confirm before replacing parts.

   The IAT action list recommended replacing the mass airflow sensor even
   though the current displayed key signals were normal and the detection came
   from rule-based proxy evidence. For proxy-forwarded cases with normal
   current readings, actions should focus on inspection, wiring/connector
   checks, and diagnostic confirmation before replacement.

17. Risk score must not be phrased as future failure probability.

   The IAT report correctly removed the raw code, but then said the sensor
   "could fail soon" because the current risk score was 90%, even though the
   model-estimated projection was only `0.31%` within the next 10 trips and no
   cycle estimate was available. Prompt rules should separate current severity
   from future failure projection.

18. Actions must not contradict NORMAL key signals.

   The IAT action text told the mechanic the sensor may be "outside its normal
   range" even though the displayed key signals were normal. For proxy-forwarded
   cases with normal readings, action text should ask for verification of the
   rule-based flag against live readings and wiring condition, not claim that a
   current signal is already out of range.

19. Proxy wording must match the actual signal status.

   The MAP report copied normal-signal proxy wording even though the MAP
   pressure-range signal was abnormal. Prompt rules should allow
   "current readings are normal" only when every displayed key signal is
   NORMAL. For abnormal proxy cases, the cause should acknowledge the abnormal
   signal and explain plausible component-specific reasons.

## Prompt Refinement Targets

- Preserve provenance notes when Model Layer notes mention Data Layer proxy
  forwarding.
- Explain failure projection fields precisely:
  - non-null probability is not a calibrated mechanical failure probability;
  - null cycles means no cycle estimate is available;
  - very small probabilities should be called very low, not absent.
- Match certainty to `risk_level`:
  - Low: monitor / weak pattern;
  - Medium: check soon;
  - High: prompt inspection, but still not confirmed failure.
- Avoid using normal key signals as abnormal evidence.
- Avoid unsupported specific mechanical causes.
- Keep `possible_cause` distinct from `anomaly_description`: do not repeat
  exact values, full signal lists, or projection details unless they are needed
  to explain a cause.
- Preserve clear real component names such as `mass airflow sensor`; rely on
  Dashboard glossary/tooltip support for extra term explanations.
- For Low-risk possible-cause text, start directly with possible explanations
  and avoid repeated monitoring summaries.
- Keep risk-level wording consistent across sections. `possible_cause` should
  not reclassify risk and usually should not mention risk level at all.
- Treat `possible_cause` as a short interpretation note, not a second
  diagnostic summary.
- Use exact failure-projection horizons such as `within the next 10 trips`
  when provided. Avoid vague wording like "near future".
- Explain dual-channel sensors in plain language before using raw channel
  labels.
- End `possible_cause` after plausible explanations. Put monitoring language in
  `recommended_action`.
- Do not expose raw diagnostic trouble codes or internal filenames in
  owner-facing report sections. Translate them into plain component language
  and keep exact codes/files for technical details.
- For proxy-forwarded cases with normal displayed key signals, avoid immediate
  replacement recommendations. Recommend confirmation first.
- Treat `risk_score` as current anomaly severity, not future mechanical
  failure probability. Very low projected probability should not be translated
  into "could fail soon."
- Keep action wording consistent with signal status. If key signals are
  NORMAL, do not say a sensor is outside normal range.
- Keep cause wording consistent with signal status. Do not say current
  readings are normal when any key signal is ABNORMAL.

## Refinement Pass Result

The first refinement pass updated prompt rules and context injection. Final
selected-window reports now:

- preserve the small projection value as approximately `0.31%` instead of
  rounding it to `0%`;
- explain IAT/MAP proxy-forwarded detections as rule-based Data Layer
  evidence when the generated text follows provenance guidance;
- keep the low-risk cooling case cautious and avoid unsupported
  thermostat/coolant-flow failure claims;
- keep Low-risk cases framed as monitoring cases rather than urgent repairs.

Residual issue to monitor:

- Granite occasionally fails to return parseable JSON on the first attempt;
  the current Report Layer retry logic recovers, but JSON-format reliability
  remains a useful future prompt-hardening target.
