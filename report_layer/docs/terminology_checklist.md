# Terminology Checklist for Diagnostic Reports

This checklist is used to review report text for a non-technical vehicle owner.
If a diagnostic report uses a technical term, the report should either replace it
with a simple phrase or explain it immediately.

## Main Rule

- Do not use unexplained technical jargon.
- If a technical term is needed, explain it in plain language.
- The owner should understand what is happening, how serious it is, and what to do next.
- Avoid vague action wording such as "check related components".

## Term Replacement Guide

| Technical term | Plain-language wording to use | Example in a report |
|---|---|---|
| MAF | airflow reading | "The airflow reading is higher than expected." |
| MAF sensor | airflow sensor | "The airflow sensor may need to be inspected." |
| MAP | intake pressure reading | "The intake pressure reading is still within its normal range." |
| TPS | throttle position | "The throttle position changed quickly during this period." |
| RPM | engine speed | "The engine speed stayed high for a long time." |
| coolant_temp | engine coolant temperature | "The engine coolant temperature is above its reference range." |
| coolant_slope | how fast the engine temperature is rising | "The engine temperature is rising faster than expected." |
| coolant_stability | how stable the engine temperature is | "The engine temperature is not staying stable after warm-up." |
| intake_temp | intake air temperature | "The intake air temperature is higher than expected." |
| ambient_temp | outside air temperature | "The outside air temperature is used for comparison." |
| intake_ambient_delta | difference between intake air and outside air temperature | "The intake air is much hotter than the outside air." |
| map_slope | how quickly intake pressure changes | "The intake pressure is changing too sharply." |
| accel_pedal_channel_delta | difference between the two accelerator pedal sensor readings | "The two accelerator pedal readings do not match closely." |
| pedal_throttle_gap | difference between pedal demand and throttle opening | "The throttle opening is not following the pedal demand closely." |
| idle_flag | whether the vehicle is idling | "The vehicle is idling, so engine speed should stay steady." |
| idle_rpm_stability | how stable engine speed is while idling | "The engine speed is not stable while the vehicle is idling." |
| rpm_slope | how quickly engine speed changes | "The engine speed is changing faster than expected." |
| reference_range | normal range | "This value is outside the normal range." |
| risk_score | risk estimate | "The system risk estimate is 72%." |
| risk_level | risk level | "Medium risk means the vehicle should be checked soon." |
| prediction_confidence | system confidence | "The system confidence is 84%." |
| key_signals | important readings | "The important readings are coolant temperature and engine speed." |
| anomaly | unusual pattern | "The system found an unusual pattern in the engine data." |
| component | vehicle part or system | "The affected vehicle system is the cooling system." |

## Component Wording

| Interface value | Plain-language wording to use |
|---|---|
| cooling_degradation | cooling system degradation |
| air_intake_maf_anomaly | air intake or airflow issue |
| accelerator_pedal_sensor | accelerator pedal sensor issue |
| intake_air_temperature_sensor_or_heat_soak_fault | intake air temperature or heat soak issue |
| map_load_signal_plausibility_fault | intake pressure or engine load signal issue |
| electronic_throttle_tracking_fault | electronic throttle tracking issue |
| idle_speed_control_or_surge_degradation | idle speed control or engine surge issue |

## Report Section Checks

### Anomaly Description

- Does it describe the observed data instead of claiming a confirmed fault?
- Does it explain the risk level in practical words?
- Does it avoid raw field names such as `coolant_temp` or `risk_score`?
- Does it translate newer raw signal names such as `pedal_throttle_gap` or `idle_rpm_stability` into plain language?
- If a technical term appears, is it explained in the same sentence?

### Possible Cause

- Does it use careful wording such as "may indicate" or "could be related to"?
- Does it avoid saying the cause is confirmed?
- Does it connect the cause to the important readings?
- Does it avoid unexplained terms such as "MAF sensor"?

### Recommended Action

- Is each action concrete and specific?
- Can a vehicle owner understand what to do next?
- Does the action match the risk level?
- Does it avoid vague wording such as "check related components"?

## Quick Pass or Fail Checklist

- The report uses plain language.
- The report explains any necessary technical term.
- The report does not show raw JSON or raw field names to the owner.
- The report gives specific next steps.
- The report does not sound more certain than the data supports.
- The report can be understood without Model Layer or Data Layer knowledge.
