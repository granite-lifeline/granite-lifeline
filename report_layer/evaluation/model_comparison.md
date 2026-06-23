# Model Comparison Report

## Test Input Summary

- Anomaly Type: cooling_system_stress
- Risk Score: 82%
- Risk Level: High
- Key Signal: coolant_temp = 102.0°C (reference: 90.0-95.0°C) [ABNORMAL]

## granite3.3:2b

### Anomaly Description

Your vehicle's cooling system is currently under high stress, which means there might be an issue that requires attention. The engine's temperature is running slightly elevated at 102.0°C, which is above the normal range of 90.0-95.0°C. This indicates that your cooling system might not be effectively managing the engine's heat, potentially leading to overheating if not addressed promptly.

### Possible Cause

*JSON parsing failed. Raw response:*

```
{
  "possible_cause": "Your vehicle's cooling system may be facing issues that could lead to the elevated engine temperature. This might be due to a few possible causes, such as:

  - Low Coolant Level: The coolant is essential for absorbing heat from the engine and transferring it away. If there isn't enough coolant, the engine might overheat.
  - Faulty Cooling Fan: The fan helps dissipate the heat by circulating air around the radiator. If it's not working correctly or not turning on, it can cause the engine to overheat.
  - Thermostat Malfunction: The thermostat regulates the flow of coolant into the engine. If it's stuck open or closed, it could result in improper cooling and overheating.

  These issues could be related to the key signal values you've noticed, like the high coolant temperature (102.0°C) which is above the normal range (90.0-95.0°C)."
}
```

### Recommended Action

- Please have your vehicle inspected by a professional mechanic as soon as possible.
- Check the coolant level and top up if necessary. Make sure to use the correct type of coolant recommended for your vehicle.
- Examine the cooling fan and radiator for any visible damage or obstructions, ensuring they are functioning properly.
- Consider having a diagnostic test performed on the thermostat to ensure it's operating correctly.

## granite3.3:8b

### Anomaly Description

Your vehicle's cooling system is currently operating with a high risk. The engine temperature has exceeded the recommended range, reaching 102.0°C compared to the normal range of 90.0-95.0°C. This indicates that your engine might be overheating, which could potentially lead to serious issues if not addressed promptly.

### Possible Cause

The high coolant temperature may indicate that your vehicle's cooling system is not functioning efficiently. This could be due to a few reasons such as low coolant level, a malfunctioning cooling fan, or a faulty thermostat. The coolant might have leaked out, causing insufficient cooling for the engine. Alternatively, the fan that helps cool the engine when it's idling or moving slowly might not be working properly. Lastly, the thermostat, which regulates the flow of coolant, could be malfunctioning and not opening as it should to allow hot coolant into the radiator for cooling. However, further diagnostic testing is needed to confirm these possibilities.

### Recommended Action

- Stop driving your vehicle immediately if it's safe to do so and have it towed to a trusted mechanic for an urgent inspection of the cooling system. The high engine temperature could lead to serious damage if not addressed promptly.
- Ensure that you understand the warning signs of overheating, such as unusual engine noises, rapid temperature gauge drop, or seeing steam from under the hood. If these occur, pull over safely and turn off the engine to prevent potential damage.
- Avoid heavy driving until your vehicle's cooling system issue has been diagnosed and resolved by a professional mechanic.
- While waiting for the inspection, monitor your vehicle's temperature gauge regularly to keep track of any unusual behavior.

## granite4.1:3b

### Anomaly Description

Your vehicle's cooling system is running much hotter than it should be. The coolant temperature is at 102°C right now (normal range is 90-95°C), which is marked as abnormal and indicates the engine might be overheating soon if not already. This high temperature level, combined with a risk score of 82% and predicted confidence of 87%, means the issue is serious enough to warrant prompt attention. In practical terms, this is a High risk situation, so you should consider checking your cooling system as soon as possible to prevent potential damage to your engine.

### Possible Cause

The coolant temperature being at 102°C (which is higher than the normal range of 90-95°C) may indicate that your vehicle's cooling system is not effectively dissipating heat from the engine. This could be related to issues such as a malfunctioning thermostat, a blocked radiator, low coolant levels, or a failing water pump. These problems can cause the engine to overheat, leading to the high temperature reading you're seeing. However, since we don't have more information about the vehicle's condition, this is just one possible explanation for the observed pattern, and further inspection would be needed to confirm the exact cause.

### Recommended Action

- 1. Have your vehicle towed to a trusted mechanic or auto repair shop immediately to inspect the cooling system for any signs of overheating, such as leaking coolant, damaged hoses, or a malfunctioning thermostat.
- 2. While driving (if it is safe to do so), avoid heavy loads and high-speed driving that could increase engine temperature further. Allow the engine to cool down periodically if you notice it running hot.
- 3. Check the coolant level in the reservoir; top off with distilled water and coolant mixture if it’s low, but only add fluid at the bottom fill cap marked for coolant.
- 4. Ask a mechanic to test the radiator hoses and pressure cap for leaks, as well as inspect the water pump and thermostat operation to identify any mechanical failures causing excessive heat.

## granite4.1:8b

### Anomaly Description

Your vehicle's cooling system is experiencing high stress. The coolant temperature reading shows **102.0°C**, which is above the normal range of **90.0–95.0°C**. This elevated temperature indicates that the engine may be overheating or struggling to dissipate heat effectively. Because the risk level is **High**, this situation could potentially lead to engine damage if not addressed promptly. It's advisable to have a professional inspect the cooling system soon to ensure your vehicle remains safe and operational.

### Possible Cause

The elevated coolant temperature reading of **102.0°C**, which exceeds the normal range of **90.0–95.0°C**, may indicate that your vehicle's cooling system is not functioning properly. This could be due to several factors, such as a malfunctioning thermostat that fails to open and allow coolant flow, a leak in the radiator or hoses reducing coolant volume, a faulty water pump that isn't circulating coolant efficiently, or air pockets within the cooling system causing inadequate heat exchange. Essentially, any issue that hinders the engine's ability to expel excess heat could lead to this high temperature reading. Since the risk level is assessed as **High**, it’s important to have a professional inspect these components soon to prevent potential engine damage.

### Recommended Action

- 1. **Stop driving immediately** if the temperature warning light or gauge indicates overheating to prevent further damage.
- 2. **Allow the engine to cool down** for at least 30 minutes before attempting any checks or inspections.
- 3. **Check the coolant level** once cooled: locate the coolant reservoir (usually a translucent plastic tank near the radiator) and ensure the coolant is between the 'MIN' and 'MAX' marks. If low, add a mixture of water and coolant as specified in your vehicle’s manual.
- 4. **Take your vehicle to a trusted mechanic or service center** for a professional inspection of the cooling system, including thermostat, radiator, hoses, and water pump.

## Comparison Notes

### JSON Parsing

granite3.3:2b returned a multi-line string inside the possible_cause JSON
value, which caused the parser to fail. The raw response content was
correct but could not be automatically extracted. The other three models
returned valid JSON for all three layers.

### Language Quality

All four models produced plain-language output suitable for a non-technical
vehicle owner. No model used unexplained technical jargon or raw field
names. All four models referenced the concrete signal value (102.0°C) and
the normal range (90.0-95.0°C), confirming that context injection
successfully grounded the report in the actual sensor data.

### Scenario Distinction

All four models used careful wording such as "may indicate" and "could be
related to", avoiding any claim that a fault is confirmed. This is
consistent with Story 2 AC requirements for avoiding force-fitting anomalies
into known fault categories.

### Model Size Comparison

granite4.1:8b produced the most specific and actionable recommended actions,
including precise guidance such as waiting 30 minutes before checking
coolant and locating the MIN/MAX marks on the reservoir. granite4.1:3b
produced natural, readable output with numbered steps. granite3.3:8b
produced clear output but with less specific guidance. granite3.3:2b
produced acceptable output but encountered a JSON parsing failure.

### Selected Model for Production

granite4.1:8b is selected for the Granite Lifeline report generation
pipeline. Rationale: highest output quality and most actionable
recommendations for non-technical vehicle owners; latest IBM Granite
version (4.1); successfully parsed all three layers without error.

granite4.1:3b is noted as a viable alternative if inference speed or
hardware constraints become a factor in later sprints.

### Limitations

The two model series (3.3 and 4.1) differ in both version and parameter
count, meaning version improvements and size effects cannot be fully
separated in this comparison. A controlled comparison using the same
version at different sizes (e.g. granite4.1:3b vs granite4.1:8b only)
would provide a cleaner evaluation of model size effects. This is
acknowledged as a limitation of the current evaluation scope.