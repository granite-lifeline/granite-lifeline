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
