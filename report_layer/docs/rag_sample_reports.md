# RAG Sample Reports - GL-116

This document provides sample RAG-enhanced diagnostic reports for three
scenarios:

- cooling system high risk;
- air intake medium risk;
- accelerator pedal low risk.

The samples show how retrieved fault knowledge should be used together with
Model Layer context. They are written for a non-technical vehicle owner and do
not present predictions as confirmed faults.

## Sample 1: Cooling System High Risk

### Input summary

| Field | Value |
|---|---|
| Component | Cooling system |
| Risk level | High |
| Risk score | 82% |
| Prediction confidence | 87% |
| Key signals | Coolant temperature: 102 C, normal range: 90-95 C |

### Retrieved fault knowledge used

- The cooling system helps prevent excessive engine heat.
- Possible causes include low coolant, radiator restriction, thermostat
  problems, water pump issues, fan problems, or heavy engine load.
- High-risk action guidance includes prompt inspection of the water pump,
  thermostat, radiator flow, and cooling system condition.

### RAG-enhanced report

**Anomaly description**

The engine coolant temperature is higher than the expected range. It is 102 C,
while the normal range shown in the data is 90 C to 95 C. This is marked as
abnormal. Because the risk level is High, the vehicle may need prompt attention,
especially if the temperature continues to rise during driving.

**Possible cause**

This may indicate that the cooling system is having difficulty moving heat away
from the engine. Based on the retrieved cooling-system knowledge, possible
reasons could include low coolant, a thermostat that is not opening correctly, a
radiator blockage, a cooling fan issue, or a water pump problem. The data does
not confirm which part is faulty, but the high coolant temperature supports a
cooling-system inspection.

**Recommended action**

- Avoid heavy driving if it is safe to do so, and stop if the vehicle shows an
  overheating warning.
- Let the engine cool before checking the coolant level. Do not open the
  coolant cap while the engine is hot.
- Ask a mechanic to inspect the cooling system soon, including the radiator,
  thermostat, fan operation, and water pump.

## Sample 2: Air Intake Medium Risk

### Input summary

| Field | Value |
|---|---|
| Component | Air intake system |
| Risk level | Medium |
| Risk score | 61% |
| Prediction confidence | 76% |
| Key signals | Mass airflow: 28.5 g/s, normal range: 10-22 g/s; intake pressure: 82 kPa, normal range: 60-90 kPa |

### Retrieved fault knowledge used

- The mass airflow sensor measures how much air enters the engine so the engine
  control unit can calculate fuel delivery.
- Possible causes include sensor contamination, dirty air filter, connector
  corrosion, wiring damage, moisture, or sensor aging.
- Medium-risk action guidance includes checking the air filter and inspecting
  wiring/connectors before replacing the MAF sensor.

### RAG-enhanced report

**Anomaly description**

The mass airflow reading is above its expected range. It is 28.5 g/s, while the
normal range shown in the data is 10 g/s to 22 g/s. The intake pressure reading
is still inside its normal range. Medium risk means the issue should be checked
soon, but the current data does not suggest an immediate emergency.

**Possible cause**

This could suggest an issue in the air-intake measurement path. Based on the
retrieved MAF sensor knowledge, possible causes include a dirty or contaminated
MAF sensor, a dirty air filter, wiring or connector damage, or moisture affecting
the sensor reading. Since the intake pressure is normal, the evidence points more
toward the airflow measurement path than a confirmed mechanical blockage.

**Recommended action**

- Check whether the air filter is dirty or due for replacement.
- Ask a mechanic to inspect the MAF sensor wiring and connector for loose,
  damaged, or corroded connections.
- If the warning repeats, use a scan tool to review MAF sensor live data before
  replacing parts.

## Sample 3: Accelerator Pedal Low Risk

### Input summary

| Field | Value |
|---|---|
| Component | Accelerator pedal sensor |
| Risk level | Low |
| Risk score | 22% |
| Prediction confidence | 62% |
| Key signals | Pedal sensor D: 35%, normal range: 0-100%; pedal sensor E: 37.5%, normal range: 0-100% |

### Retrieved fault knowledge used

- The accelerator pedal position sensor sends the driver's pedal input to the
  engine control module.
- This system often uses two sensor channels so the vehicle can compare them for
  safety.
- Low-risk action guidance includes checking for diagnostic trouble codes and
  monitoring electrical signals before assuming a sensor fault.

### RAG-enhanced report

**Anomaly description**

The accelerator pedal sensor readings are both inside their expected range. One
reading is 35%, and the other is 37.5%. The difference is small, and the current
risk level is Low. This means the issue does not look urgent right now.

**Possible cause**

This could be normal sensor variation or a small delay between the two pedal
sensor channels. Retrieved accelerator-pedal knowledge shows that these systems
often use two channels for safety checking, so a large or repeated mismatch would
matter more. In this sample, the readings do not strongly support a confirmed
sensor fault.

**Recommended action**

- Continue monitoring the dashboard for repeated warnings.
- If the warning appears again, use an OBD2 scan tool to check for related
  diagnostic trouble codes.
- If the pedal response feels unusual, ask a mechanic to inspect the pedal sensor
  signals and wiring.

## GL-116 Result

These three samples demonstrate that the RAG prompt design can:

- include retrieved fault knowledge in the explanation;
- connect recommendations to risk level;
- keep wording understandable for a non-technical vehicle owner;
- avoid confirmed-fault claims.
