# Sampling Stability Test

5 identical calls to `generate_report()` on the same real fixture (cooling_degradation, Low — `selected_window_model_outputs/cooling_degradation__trip_0040_seg_001__w003.json`), same prompt, same `temperature: 0` setting already used in production. Checks whether every prior cross-validation and perturbation-test comparison's implicit assumption — that a single generated report represents "what generate_report() produces for this input" — actually holds.

## Results

| Run | Time (s) | Description length | Evaluator overall | Validator warnings |
|---|---|---|---|---|
| 1 | 39.7 | 827 | 1.00 | 0 |
| 2 | 11.3 | 827 | 1.00 | 0 |
| 3 | 11.3 | 827 | 1.00 | 0 |
| 4 | 11.3 | 827 | 1.00 | 0 |
| 5 | 11.3 | 827 | 1.00 | 0 |

## Stability summary

- Unique anomaly_description texts across 5 runs: **1**
- Unique possible_cause texts: **1**
- Unique recommended_action lists: **1**
- Unique evaluator overall scores: **1** ([1.0])
- Unique validator warning counts: **1** ([0])

**temperature=0 produced byte-identical text across all 5 runs.** The single-sample comparisons in qa_cross_validation and perturbation_regression are representative, not one lucky draw out of a distribution.

## Per-run text

### Run 1

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

- evaluator: overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00
- validator warnings: (none)

### Run 2

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

- evaluator: overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00
- validator warnings: (none)

### Run 3

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

- evaluator: overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00
- validator warnings: (none)

### Run 4

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

- evaluator: overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00
- validator warnings: (none)

### Run 5

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

- evaluator: overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00
- validator warnings: (none)

