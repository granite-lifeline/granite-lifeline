# QA Cross-Validation: All 5 Anomaly Types

prompt_chain_validator.validate_chain() and report_quality_evaluator.evaluate_report() run against the SAME real, LLM-generated report, for each of the 5 current anomaly types, using the real per-type fixtures in report_layer/evaluation/prompt_refinement/fault_injection_candidates/selected_window_model_outputs/. Neither QA mechanism had previously been run outside cooling_degradation, and they had never been run against the same report before this. Re-scored after fixing one cross-mechanism inconsistency found on the first pass (see below).

| Anomaly type | Risk | Validator all-passed | Validator warnings | Evaluator overall | Agreement |
|---|---|---|---|---|---|
| cooling_degradation | Low | True | 0 | 1.00 | both clean |
| air_intake_maf_anomaly | Low | True | 2 | 0.75 | both flag |
| accelerator_pedal_sensor | Medium | True | 0 | 1.00 | both clean |
| intake_air_temperature_sensor_fault | High | True | 1 | 0.93 | both flag |
| map_load_signal_plausibility_fault | High | True | 1 | 0.93 | both flag |

## Fix applied between first and second pass

The first pass found one real cross-mechanism disagreement: accelerator_pedal_sensor (Medium) scored validator=clean but evaluator overall=0.93, readability=0.70. Cause: evaluate_readability()'s raw_fields list included lowercase "rpm" and matched case-insensitively against "Vehicle speed and engine RPM are also normal" in the real generated text — flagging plain, commonly-understood English as unexplained jargon. prompt_chain_validator.py's equivalent list already excluded "rpm" for this reason (unlike coolant_temp/maf/map, which are genuine internal field names). Removed "rpm" from the evaluator's list for consistency; this changed the accelerator_pedal_sensor score from overall=0.93/readability=0.70 to overall=1.00/readability=1.00, resolving the disagreement.

(A second apparent disagreement in the first pass — air_intake_maf_anomaly showing as DISAGREE — was actually a bug in this script's own agreement classification, which only checked validator `passed` and not `warnings`. validate_layer1/2/3's `passed` field is only False for empty/malformed output; content-quality issues like a raw field name leak only add warnings and reduce `score`, leaving `passed=True`. Fixed the classification logic here; air_intake_maf_anomaly correctly shows as "both flag" below — the validator did catch the same issue the evaluator scored low, they were never actually in disagreement.)

## Details

### cooling_degradation (Low)

Generation time: 40.1s

**Validator warnings:**

(none)

**Evaluator scores:** overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00

**Generated report:**

- anomaly_description: The cooling system is showing a low-risk pattern where several key signals are outside their normal ranges. Specifically, the coolant temperature is slightly below the expected range at 89.0°C (normal 90.0-95.0°C), and the rate at which it is changing is unusual (–0.2951°C/min instead of 0.0-2.0°C/min). Additionally, the mass airflow sensor reading exceeds its normal limit (3266.3368g vs. 0.0-2500.0g). Despite these abnormal readings, the overall risk level is classified as Low, meaning there is no urgent concern at this time. The model estimates only a very low 0.31% probability of reaching a higher-risk threshold within the next 10 trips. In plain terms, while the cooling system shows some weak signals that should be monitored, it does not indicate an imminent problem and can be checked during routine maintenance.

- possible_cause: The slightly lower-than-expected coolant temperature and unusually slow cooling rate may indicate a minor sensor reading issue or an early sign of reduced cooling fan effectiveness. The elevated mass airflow sensor reading suggests possible light contamination on the sensor surface, but overall risk remains low with no strong evidence of a mechanical fault.

- recommended_action:
  - Check the coolant level in the reservoir tank when the engine is cool and ensure it's between the MIN and MAX marks.
  - Inspect the mass airflow sensor for any visible dirt or contamination; gently clean if needed, but avoid touching the sensing element directly.
  - Monitor the vehicle’s temperature gauge during normal driving to see if the reading stabilizes within the expected range (90–95 °C).
  - If the warning light reappears or you notice any unusual engine behavior, have a mechanic inspect the cooling system and sensor wiring for potential issues.

### air_intake_maf_anomaly (Low)

Generation time: 36.5s

**Validator warnings:**

- Contains unexplained raw field name: maf
- Missing hedging language (may indicate, could suggest, etc.)

**Evaluator scores:** overall=0.75, factual_grounding=1.00, readability=0.70, hedging_appropriateness=0.60, actionability=0.70

**Generated report:**

- anomaly_description: The mass airflow (MAF) sensor, which measures how much air enters the engine to help maintain the proper fuel mixture, is showing a slightly elevated reading of 31.41 grams per second. This value falls within the normal operating range (0.0–123.0 g/s), so no immediate abnormality is detected in the airflow itself. The risk level associated with this sensor anomaly is Low, indicating that while there is a minor pattern worth monitoring, it does not suggest an urgent problem. The model estimates only a 0.31% probability of crossing into a higher-risk threshold within the next 10 trips, reinforcing that any potential issue is unlikely to develop soon. Overall, the MAF sensor appears functional, and no prompt action is required beyond routine checks.

- possible_cause: Possible explanations include light dust or oil on the mass airflow sensor surface, a slightly loose connector, or normal variation during driving. Because related readings are still normal, there is not enough evidence to identify a specific intake-system fault.

- recommended_action:
  - Connect a scan tool to view the MAF sensor's Parameter Identification Data (PID) while the engine runs between 1000 and 2250 rpm. A healthy MAF should show a steady, linear increase in airflow reading during this range.
  - Inspect the air intake hose and filter area for any visible dirt, oil, or debris that could be lightly contaminating the MAF sensor surface.
  - Check the electrical connector of the MAF sensor for signs of corrosion, loose pins, or damage. Ensure it is securely plugged in.
  - If you notice no improvement after these checks or if the scan tool shows an abnormal MAF signal, schedule a visit to a mechanic for further diagnostic confirmation.

### accelerator_pedal_sensor (Medium)

Generation time: 36.3s

**Validator warnings:**

(none)

**Evaluator scores:** overall=1.00, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=1.00

**Generated report:**

- anomaly_description: The accelerator pedal position sensor (APPS) is showing a medium risk level based on its current readings. Both internal sensors report normal pedal positions at about 14% when lightly pressed, and the difference between them is within acceptable limits. Vehicle speed and engine RPM are also normal. The model estimates a low probability—about 0.31%—of reaching a high-risk condition within the next 10 trips. In plain terms, this suggests that while the sensor should be monitored, there is no immediate cause for concern or urgent action required.

- possible_cause: The slight variation between the two accelerator pedal sensor channels could be due to normal sensor tolerance, a minor wiring or connector issue, or early signs of sensor wear.

- recommended_action:
  - Inspect the wiring harness and connector at the accelerator pedal position sensor for any damage or loose connections.
  - Check that the accelerator pedal moves smoothly from fully released to fully depressed and returns securely to the released position.
  - If you notice any unusual behavior, such as delayed response or inconsistent readings, have a mechanic perform a diagnostic scan on the sensor.
  - Monitor the vehicle's performance over the next few trips; if symptoms persist, schedule an appointment with a service center for further evaluation.

### intake_air_temperature_sensor_fault (High)

Generation time: 39.0s

**Validator warnings:**

- High risk actions lack urgency language (soon, prompt, immediately, avoid, urgent)

**Evaluator scores:** overall=0.93, factual_grounding=1.00, readability=1.00, hedging_appropriateness=1.00, actionability=0.70

**Generated report:**

- anomaly_description: The diagnostic system has flagged a potential issue with the intake air temperature sensor. Although all measured key signals—such as intake air temperature, intake temperature stability, and ambient temperature—are within their normal ranges such as intake air temperature at 19.0°C or intake temperature stability at 1.5177°C, the rule-based Data Layer evidence indicates a fault in the sensor's circuit or signal plausibility. This flag is marked with a High risk level, suggesting that while no immediate abnormal readings are observed, the condition should be monitored closely. The model estimates only a very low 0.31% probability of crossing the high-risk threshold within the next 10 trips, meaning failure is unlikely soon but warrants attention to prevent potential future issues.

- possible_cause: The high-risk flag for the intake air temperature sensor may indicate an intermittent sensor signal, a loose or corroded connector, or early sensor drift. Although all measured key signals—such as intake air temperature, intake temperature stability, and ambient temperature—are within their normal ranges such as intake air temperature at 19.0°C, the rule-based Data Layer evidence suggests that the sensor’s circuit or signal plausibility could be compromised. This proxy-forwarded detection should be verified by a mechanic before confirming a sensor fault.

- recommended_action:
  - Inspect the intake air temperature sensor and its wiring harness for loose connections or damage. The sensor is typically located near the air filter box or within the intake tube.
  - If you notice any warning lights or unusual engine behavior after driving, let the vehicle cool down for about 30 minutes before checking again, as heat can temporarily affect sensor readings.
  - Schedule a visit to a mechanic who can use a diagnostic tool to verify the sensor’s signal and confirm whether it is functioning correctly. Mention that the rule‑based system flagged a potential fault in the sensor circuit.
  - Drive normally while watching for warning lights or unusual engine behavior until the sensor is verified.

### map_load_signal_plausibility_fault (High)

Generation time: 43.8s

**Validator warnings:**

- Contains unexplained raw field name: map

**Evaluator scores:** overall=0.93, factual_grounding=1.00, readability=0.70, hedging_appropriateness=1.00, actionability=1.00

**Generated report:**

- anomaly_description: The diagnostic system has flagged a potential issue with the intake manifold pressure (MAP) sensor. The key signal 'Manifold Pressure Range' is marked as ABNORMAL, reading 98.0 kPa while the expected range is 0.0–80.0 kPa, indicating the sensor may not be measuring pressure correctly. Other signals such as Manifold Air Pressure and RPM Rate of Change are within normal limits, suggesting no immediate mechanical failure but pointing to a possible sensor problem. The risk level for this anomaly is High, meaning it should be monitored closely. The model estimates only a very low 0.31% probability of crossing the high-risk threshold within the next 10 trips, so while prompt attention is advised, an imminent failure is unlikely. This detection was forwarded from rule-based Data Layer proxy evidence rather than direct TTM residual scoring.

- possible_cause: The abnormal manifold pressure range reading suggests a potential issue with the intake manifold pressure (MAP) sensor. This could be due to an intermittent MAP sensor signal, a loose or corroded connector, a damaged vacuum hose, or early sensor drift. Although other key signals like Manifold Air Pressure and RPM Rate of Change are within normal limits, the rule-based diagnostic flag indicates that the MAP sensor's plausibility calculation is out of expected bounds. Therefore, this pattern should be verified by a mechanic before confirming a sensor failure.

- recommended_action:
  - Avoid heavy acceleration or high-speed driving until this issue is checked, as an inaccurate manifold pressure reading can affect engine performance and fuel efficiency.
  - Ask a mechanic to inspect the intake manifold pressure (MAP) sensor and its wiring connections. The MAP sensor is typically mounted on the intake manifold near the throttle body.
  - Check the vacuum hoses connected to the MAP sensor for cracks, splits, or loose fittings, as these can cause incorrect pressure readings.
  - Schedule an appointment with a mechanic within the next few days to verify the sensor’s operation and ensure the engine control system is receiving accurate data.

