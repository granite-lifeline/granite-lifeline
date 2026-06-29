# Data Layer Reference

**Purpose:** Document the domain grounding, supporting evidence, and rationale behind selected signals, derived features, and proxy failure definitions.

```
Signal
  (KIT Automotive OBD-II Dataset)
    │
    ▼
Feature
  (Derived Features)
    │
    ▼  [Fault Signature Knowledge]
Proxy Failure
  (failure_signatures)
```

## 1. Raw Signals

Document the meaning and expected behaviour of original OBD-II variables.

| KIT Raw Fields                       | Output         | Unit     |
| ------------------------------------ | -------------- | -------- |
| Time                                 | timestamp      | ISO 8601 |
| Engine Coolant Temperature           | coolant_temp   | °C       |
| Intake Manifold Absolute Pressure    | map            | kPa      |
| Engine RPM                           | rpm            | rpm      |
| Vehicle Speed Sensor                 | speed          | km/h     |
| Intake Air Temperature               | intake_temp    | °C       |
| Air Flow Rate from Mass Flow Sensor  | maf            | g/s      |
| Absolute Throttle Position           | tps            | %        |
| Ambient Air Temperature              | ambient_temp   | °C       |
| Accelerator Pedal Position D         | accel_pedal_d  | %        |
| Accelerator Pedal Position E         | accel_pedal_e  | %        |

For each signal include:

* Physical meaning
* Physical Relationship
* Failure Interpretation

### 1.1 Time

Recording the timestamp of each OBD-II data collection serves as the reference axis for the entire time-series analysis. The frequency after resampling is 1 Hz.

### 1.2 Engine Coolant Temperature

**Physical Meaning:** Reflects the overall thermal state of the engine. Normal operation typically manifests as:
* Cold start: Gradual temperature increase.
* Steady-state cruising: Relatively stable temperature.
* High load: Slight temperature increase.

**Physical Relationship**   

An increase in throttle opening leads to increased air intake, which increases fuel combustion and engine load. This causes higher heat generation, resulting in an increase in coolant temperature.  

Simultaneously, as vehicle speed increases, heat dissipation efficiency improves, causing the coolant temperature to either decrease or stabilise.

**Failure Interpretation**   

* Abnormal increase: Radiator blockage, water pump inefficiency, or insufficient coolant.
* Abnormaldecrease: Thermostat failure or unstable cooling circulation.
* Abnormal fluctuations: Thermostat stuck open or temperature sensor malfunction.

### 1.3 Intake Manifold Absolute Pressure

**Physical Meaning:** Indicates the absolute pressure inside the intake manifold, reflecting the air intake capacity and load state of the engine. High pressure means more air enters the cylinder, while low pressure indicates a stronger vacuum when the throttle is closed.  

**Physical Relationship**   

An increase in throttle opening expands the manifold opening, which increases the Intake Manifold Absolute Pressure (MAP). This delivers more air to the cylinder, leading to an increase in Engine RPM.  

Under normal operating conditions, the Mass Air Flow (MAF) and MAP change synchronously.  

**Failure Interpretation**    

* Persistently high MAP: Vacuum leakage or throttle abnormality.
* Low MAP: Intake system blockage(such as a contaminated air filter).
* Desynchronisation between MAP and MAF: Sensor drift or air-intake abnormality.

### 1.4 Engine RPM

**Physical Meaning:** Represents the rotational speed of the engine crankshaft. It is one of the most critical indicators of engine power output.  

**Physical Relationship**  

Pressing the accelerator pedal increases the Throttle Position Sensor (TPS) output, which increases the Mass Air Flow (MAF). This enhances combustion, resulting in higher Engine RPM.  

If the accelerator pedal remains constant while the engine load increases, the Engine RPM will decrease.  

**Failure Interpretation**   

* RPM fluctuations: Unstable combustion.
* High RPM with low vehicle speed: Transmission slipping or other powertrain issues.
* Abnormal drop in RPM: Insufficient intake air, increasing the risk of engine stalling.

### 1.5 Vehicle Speed Sensor

**Physical Meaning:** Measures the actual traveling speed of the vehicle, representing the final output effect of the engine performance.  

**Physical Relationship**  

An increase in Engine RPM drives the transmission, which increases the vehicle speed.  

Driving at high speeds increases air-cooling efficiency, which leads to a decrease in engine coolant temperature.  

**Failure Interpretation**   

* Low vehicle speed with high RPM: Power loss or transmission abnormality.
* Abnormal jumps in speed readings: Vehicle Speed Sensor (VSS) malfunction.

### 1.6 Intake Air Temperature

**Physical Meaning:** Indicates the temperature of the air entering the engine, which directly affects air density. Colder air features higher density.  

**Physical Relationship**  

An increase in intake air temperature decreases air density, reducing the effective oxygen content and lowering combustion efficiency.  

An increase in ambient air temperature leads to an increase in intake air temperature.  

**Failure Interpretation**   

* Abnormally high: Heat soak effect (e.g., during prolonged idling) or insufficient intake air cooling (e.g., intercooler inefficiency).
* Abnormally low: Sensor failure.
* Mismatch with MAF data: Air intake path abnormality.

### 1.7 Air Flow Rate from Mass Flow Sensor

**Physical Meaning:** Measures the mass of air entering the engine per unit of time, directly reflecting the current engine load.  

**Physical Relationship**  

An increase in throttle opening increases the Intake Manifold Absolute Pressure (MAP) and the Mass Air Flow (MAF), which demands more fuel injection and increases Engine RPM.  

**Failure Interpretation**   

Same as 1.3 Intake Manifold Absolute Pressure  

### 1.8 Absolute Throttle Position

**Physical Meaning:** Represents the opening degree of the throttle valve, which dictates the driver's or ECU's intake air request.  

**Physical Relationship**  

Pressing the accelerator pedal increases the Throttle Position Sensor (TPS) signal, which increases MAP and MAF. This drives up Engine RPM and subsequently raises the engine coolant temperature.  

**Failure Interpretation** 

* TPS stuck or jammed: Abnormal powertrain response.
* Severe TPS fluctuations: Control system malfunction.
* High TPS with low MAF: Intake system restriction or blockage.

### 1.9 Ambient Air Temperature

**Physical Meaning:** Represents the external environmental temperature surrounding the vehicle, serving as an external environmental baseline variable.  

**Physical Relationship**  

An increase in ambient temperature raises the intake air temperature and reduces the baseline cooling efficiency. To counteract this, the ECU automatically commands maximum cooling fan speed and enriches the fuel mixture for component protection.  

**Failure Interpretation**  

Deviations in this value typically do not represent a mechanical fault, but serves as a reference baseline for temperature normalization and environmental compensation variables.  

### 1.10 Accelerator Pedal Position D

**Physical Meaning:** Represents the driver's throttle input via Channel D.   

**Physical Relationship**  

Pressing the accelerator pedal increases Channel D output, which raises the ECU torque request. The ECU then increases the throttle position (TPS) and MAF, ultimately driving up Engine RPM.  

**Failure Interpretation** 

* Signal Mismatch: Large deviation between Channel D and Channel E, leading to pedal redundancy failure.
* Delayed response: ECU control system abnormality.

### 1.11 Accelerator Pedal Position E

**Physical Meaning:** Represents the secondary channel (Channel E) of the accelerator pedal sensor, specifically utilized for cross-validation and fault detection.  

**Physical Relationship**   

Channel E must change synchronously with Channel D. Pressing the accelerator pedal increases both channel outputs.  

**Failure Interpretation** 

* Single-channel signal drift: Hardware Degradation caused by sensor aging.

* Sudden signal dropouts or cliffs: Electrical Fault due to poor electrical contact.


## 2. Derived Features

Document engineered features and why they are introduced.  

For each feature include:

* Inputs
* Formula
* Unit
* Physical Meaning
* Supporting source

### 2.1 coolant_slope

**Inputs:** `coolant_temp`, `timestamp`  

**Formula:** `Δcoolant_temp / Δtime`  

**Unit:** °C/s  

**Physical Meaning:** The rate at which coolant temperature accumulates or decreases.  

**Source:** Bosch Automotive Handbook  

### 2.2 coolant_ambient_delta

**Inputs:** `coolant_temp`, `ambient_temp`  

**Formula:** `coolant_temp - ambient_temp`   

**Unit:** °C

**Physical Meaning:** The available temperature difference for the cooling system and the engine thermal state relative to ambient conditions.  

**Source:** Bosch Automotive Handbook  

### 2.3 coolant_stability

**Inputs:** `coolant_temp`  

**Formula:** `coolant_stability(t) = rolling_std(coolant_temp, W_stability)`  
  where:
    - `W_stability = 60 s`
    - `window_samples = W_stability × sampling_rate`
    - At `sampling_rate = 1 Hz`, `window_samples = 60`
    - Valid only after `coolant_temp >= 70°C` for at least 60 consecutive seconds within the same segment.   

**Unit:** °C

**Physical Meaning:** The regulation stability of coolant temperature after engine warm-up is complete(`coolant_temp` ≥ `T_warmup`, `T_warmup` = 70°C).   

**Source:** Bosch Automotive Handbook  

### 2.4 intake_ambient_delta

**Inputs:** `intake_temp`, `ambient_temp`  

**Formula:** `intake_temp - ambient_temp`     

**Unit:** °C

**Physical Meaning:** The degree of intake-air heating or heat soak before the air enters the engine.  

**Source:** Bosch Automotive Handbook  

### 2.5 intake_temp_slope

**Inputs:** `intake_temp`, `timestamp`  

**Formula:** `Δintake_temp / Δtime`  

**Unit:** °C/s

**Physical Meaning:** The dynamic rate of intake-air heat soak or cooling.  

**Source:** Bosch Automotive Handbook  

### 2.6 maf_derived_air_load

**Inputs:** `maf`, `rpm`  

**Formula:** `maf / max(rpm / 60, ε)`   

**Unit:** g/rev

**Physical Meaning:** A proxy for air mass per revolution directly converted from the MAF sensor.  

**Source:** Bosch Automotive Handbook  

### 2.7 map_derived_air_load

**Inputs:** `map`, `intake_temp`, `rpm`  

**Formula:** `f_dataset(map, intake_temp, rpm)`; a simplified raw proxy can use `rpm * map / (intake_temp + 273.15)` and must then be standardized or calibrated; `f_dataset` is a dataset normal-reference baseline model.  

**Unit:** dimensionless or model-scaled

**Physical Meaning:** An air-load proxy derived from MAP, intake temperature, and engine speed.  

**Source:** Bosch Automotive Handbook  

### 2.8 maf_map_cohesion

**Inputs:** `maf_derived_air_load`, `map_derived_air_load`  

**Formula:** `abs(zscore_dataset(maf_derived_air_load) - zscore_dataset(map_derived_air_load))`

**Unit:** dimensionless

**Physical Meaning:** The standardized deviation between the MAF-side air-load estimate and the MAP-side air-load estimate.  

**Source:** Bosch Automotive Handbook  

### 2.9 speed_density_maf_residual

**Inputs:** `maf`, `map`, `intake_temp`, `rpm`  

**Formula:** `maf - f_dataset(map, intake_temp, rpm)`   

**Unit:** g/s  

**Physical Meaning:** The residual between the mass air flow sensor reading and the speed-density baseline built from MAP, intake temperature, and engine speed.  

**Source:** Bosch Automotive Handbook  

### 2.10 map_slope

**Inputs:**  `map`, `timestamp`  

**Formula:** `Δmap / Δtime`   

**Unit:** kPa/s  

**Physical Meaning:** The dynamic change of intake manifold pressure.  

**Source:** Bosch Automotive Handbook  

### 2.11 accel_pedal_mean

**Inputs:** `accel_pedal_d`, `accel_pedal_e`  

**Formula:** `(accel_pedal_d + accel_pedal_e) / 2`    

**Unit:** % 

**Physical Meaning:**  The fused value of the dual-channel accelerator pedal, used as a proxy for driver torque demand.  

**Supporting source:** Bosch Automotive Handbook  

### 2.12 pedal_throttle_gap

**Inputs:** `accel_pedal_mean`, `tps`, `rpm`, `operating_state`  

**Formula:** `tps_normalized - g_dataset(accel_pedal_mean, rpm, operating_state)` (percentage points); `g_dataset` is the expected throttle model fitted from dataset normal-reference conditions.  

**Unit:** %  

**Physical Meaning:** The residual between the actual throttle position and the expected value based on driver demand and the current operating state.  

**Source:** Bosch Automotive Handbook  

### 2.13 pedal_to_throttle_delay

**Inputs:** `pedal_slope`, `tps_slope`  

**Formula:** Within an event window, calculate the `τ` (s) that maximizes `corr(pedal_slope(t), tps_slope(t + τ))`  

**Unit:** s  

**Physical Meaning:** The estimated delay between a driver pedal change and the throttle response.  

**Source:** Bosch Automotive Handbook

### 2.14 tps_slope

**Inputs:** `tps`, `timestamp`  

**Formula:** `Δtps / Δtime`   

**Unit:** %/s  

**Physical Meaning:** Throttle actuation speed. It can be combined with `pedal_slope` to distinguish driver command changes from ECU/actuator control changes of the throttle.  

**Source:** Bosch Automotive Handbook

### 2.15 accel_pedal_channel_delta

**Inputs:** `accel_pedal_d`, `accel_pedal_e`  

**Formula:** `abs(accel_pedal_d - accel_pedal_e)`   

**Unit:** %    

**Physical Meaning:** The degree of inconsistency between the dual-channel pedal sensors.  

**Source:** Bosch Automotive Handbook  

### 2.16 accel_pedal_channel_ratio

**Inputs:** `accel_pedal_d`, `accel_pedal_e`  

**Formula:** `(accel_pedal_d + ε) / (accel_pedal_e + ε)`   

**Unit:** dimensionless  

**Physical Meaning:** Monitoring of the proportional relationship between the two pedal channels.  

**Source:** Bosch Automotive Handbook  

### 2.17 pedal_slope

**Inputs:** `accel_pedal_mean`, `timestamp`  

**Formula:** `Δaccel_pedal_mean / Δtime`  

**Unit:** %/s  

**Physical Meaning:** The rate of change in driver demand.  

**Source:** Bosch Automotive Handbook  

### 2.18 engine_on_flag

**Inputs:** `rpm`  

**Formula:** `1 if rpm > rpm_engine_on_threshold else 0`  

**Physical Meaning:** Distinguishes between engine stopped and engine running states, and provides the basis for warm-up, idle, trip segmentation, and temperature feature calculation.  

**Source:** Bosch Automotive Handbook  

### 2.19 rpm_slope

**Inputs:** `rpm`, `timestamp`  

**Formula:** `Δrpm / Δtime`   

**Unit:** rpm/s    

**Physical Meaning:** The rate of change in engine speed.  

**Source:** Bosch Automotive Handbook  

### 2.20 idle_flag

**Inputs:** `engine_on_flag`, `speed`, `rpm`, `tps`, `accel_pedal_mean`  

**Formula:** `engine_on_flag = 1 & speed < v_idle & rpm within calibrated_idle_band & accel_pedal_mean <= calibrated_idle_pedal_threshold & tps <= calibrated_idle_tps_threshold`  

**Unit:** dimensionless

**Physical Meaning:** Identifies the engine idle state and is used to establish independent baselines for idle RPM stability, air flow, MAP, and temperature.  

**Source:** Bosch Automotive Handbook  

### 2.21 idle_rpm_stability

**Inputs:** `rpm`, `idle_flag`  

**Formula:** `rolling_std(rpm | idle_flag = 1, W_idle_stability)` where `W_idle_stability = 30 s` at 1 Hz.  

**Unit:** rpm  

**Physical Meaning:** Idle-speed stability.  

**Source:** Bosch Automotive Handbook   
 

# 3. Proxy Failure Definitions

Document proxy failures and supporting evidence.  

For each proxy include:

* Component
* Supporting signals/features
* Proxy Definition
* Expected Pattern
* Physical Logic
* Source

### 3.1 cooling_degradation

**Component:** Cooling system (Radiator / Water Pump / Thermostat / Coolant Circulation)  

**Supporting Features:** `coolant_temp`, `ambient_temp`, `speed`, `rpm`, `coolant_slope`, `coolant_ambient_delta`, `coolant_stability`  

**Proxy Definition:** Flag abnormal coolant thermal behavior, including sustained overheating after warm-up, coolant temperature rising without plateau, abnormally slow warm-up and coolant temperature implausible relative to ambient temperature after cold soak.  

**Expected Pattern:** 
- Overheating: coolant_temp > 105°C for 3-5 min after warm-up
- Rising without plateau: coolant_slope > 2°C/min for 2-3 min
- Slow warm-up: coolant_temp < 70-75°C after 10-15 min running
- Sensor plausibility: abs(coolant_temp - ambient_temp) > 10-15°C after cold soak

**Physical Logic:** The cooling system prevents thermal overload, lubricating-oil burn-off, and abnormal combustion caused by excessive component temperatures. Coolant and engine temperatures need to remain stable within a narrow range. If the temperature stays above the stable post-warm-up range for an extended period, heat input and heat dissipation capacity are out of balance.  

**Source:** Bosch Automotive Handbook

### 3.2 intake_air_temperature_sensor_or_heat_soak_fault

**Component:** Intake-air temperature sensing / intake-air temperature regulation  

**Supporting Features:** `intake_temp`, `ambient_temp`, `speed`, `rpm`, `tps`, `intake_ambient_delta`, `intake_temp_slope`  

**Proxy Definition:** Intake temperature is abnormally high or low relative to ambient temperature, or does not vary with vehicle speed/load. This can proxy intake-air temperature sensor faults, severe heat soak, intake preheating/temperature regulation faults, or poor thermal management in the intake path.  

**Expected Pattern:** After stable driving at `speed > 40 km/h` for 5 min, `intake_temp - ambient_temp > 25-35°C`; or after extended running following cold start, `intake_temp < ambient_temp - 5°C`; or under high load, `intake_temp > 60°C`.  

**Physical Logic:** Colder air has higher density, while heated intake air reduces density and output. Passenger-car air cleaners/intake systems can regulate intake temperature, affecting performance, fuel consumption, and emissions. For diesel engines, higher intake temperature increases combustion temperature and NOx emissions.  

**Source:** Bosch Automotive Handbook  

### 3.3 air_intake_maf_anomaly

**Component:** MAF sensor / intake air measurement path  

**Supporting Features:** `maf`, `map`, `rpm`, `intake_temp`, `maf_derived_air_load`, `map_derived_air_load`, `maf_map_cohesion`  

**Proxy Definition:** Triggered when `maf_map_cohesion` remains high. This proxy identifies inconsistency between the MAF-side air-load estimate and the MAP-side air-load estimate, mainly indicating MAF sensor drift, contamination, response delay, or abnormalities in the intake measurement chain.  

**Expected Pattern:** `maf_map_cohesion` > 0.25-0.30 for 5-10 s as an initial proxy hint, not a final decision threshold; or under steady-state conditions, the standardized deviation between `maf_derived_air_load` and `map_derived_air_load` exceeds 25-30%. Transient acceleration, gear shifts, and rapid throttle-change windows should be down-weighted or masked.  

**Physical Logic:** Under the same operating condition, MAF-based load and MAP-based load should remain physically consistent. Persistent deviation between the two indicates a plausibility abnormality in the air-mass measurement chain.  

**Source:** Bosch Automotive Handbook  

### 3.4 map_load_signal_plausibility_fault

**Component:** Intake manifold absolute pressure sensor / load signal  

**Supporting Features:** `map`, `maf`, `rpm`, `tps`, `intake_temp`, `speed_density_maf_residual`, `map_slope`  

**Proxy Definition:** MAP cannot reasonably reflect load changes, or its relationship with MAF, throttle position, and engine speed is inconsistent. This proxies MAP sensor drift, blockage, hose issues, signal sticking, or load-measurement abnormalities.  

**Expected Pattern:** After a `tps` step change greater than 15 percentage points, `abs(map_slope)` remains close to 0 within 1 s; or under steady-state conditions, the air amount derived from MAP differs from MAF by more than 25-30%; or `map` remains near an unreasonable fixed value for an extended period while the engine is running.  

**Physical Logic:** Intake manifold absolute pressure is a preferred method for monitoring load, and relative charge can be determined from available measurement signals such as MAF or MAP through an intake manifold model. If MAP is distorted, load, ignition, fuel injection, and torque calculations will all be biased.  

**Source:** Bosch Automotive Handbook  

### 3.5 electronic_throttle_tracking_fault

**Component:** Electronic throttle control / throttle actuator  

**Supporting Features:** `accel_pedal_d`, `accel_pedal_e`, `tps`, `rpm`, `map`, `maf`, `pedal_throttle_gap`, `pedal_to_throttle_delay`, `tps_slope`  

**Proxy Definition:** After pedal demand increases, throttle opening does not change accordingly, or the actual throttle position remains offset from the expected value based on pedal/load for an extended period. This proxies electronic throttle actuator sticking, position-control abnormalities, or ETC entering a restricted-control mode.  

**Expected Pattern:** After `accel_pedal_mean` increases by more than 20 percentage points, `tps` changes by less than 5 percentage points within 0.5-1.0 s; or `pedal_throttle_gap > 15-20 percentage points` for 2 s as an initial proxy hint, not a final decision threshold. Confidence is higher if `map`/`maf` also show no response.  

**Physical Logic:** ETC calculates throttle opening through the ECU based on pedal position and current operating conditions, and uses the throttle angle sensor to monitor whether the actual position matches the expected position. OBD diagnostic targets include the ETC throttle-valve actuator.  

**Source:** Bosch Automotive Handbook  

### 3.6 accelerator_pedal_sensor

**Component:** Accelerator pedal position sensors (dual/redundant)   

**Supporting Features:** `accel_pedal_d`, `accel_pedal_e`, `accel_pedal_channel_delta`, `accel_pedal_channel_ratio`, `pedal_slope`  

**Proxy Definition:** The proportional relationship, correlation, or dynamic behavior between pedal channels D/E is inconsistent. This proxies pedal sensor channel drift, contact abnormalities, or redundancy-monitoring failure.  

**Expected Pattern:** First learn the dataset normal-reference mapping `accel_pedal_e = a * accel_pedal_d + b`; trigger if the residual remains above 5-10 percentage points, the channel correlation coefficient is below 0.95, or one channel changes while the other channel freezes for more than 1 s.  

**Physical Logic:** The ETC system uses two potentiometers on the pedal and throttle device to provide redundancy, and continuously checks all sensors and calculations that affect throttle opening while the engine is running.  

**Source:** Bosch Automotive Handbook  

### 3.7 idle_speed_control_or_surge_degradation

**Component:** Idle-speed control / engine-speed control  

**Supporting Features:**  `rpm`, `speed`, `tps`, `accel_pedal_d`, `accel_pedal_e`, `maf`, `map`, `idle_flag`, `idle_rpm_stability`, `rpm_slope`  

**Proxy Definition:** Under idle conditions, RPM fluctuation is excessive, cyclic surging occurs, or the engine cannot stabilize near the target idle speed. This proxies idle-control degradation, intake/fuel-injection/ignition disturbances, excessive EGR, or insufficient load compensation.  

**Expected Pattern:** Within an idle window where `speed < 3 km/h`, `tps <= calibrated_idle_tps_threshold`, and pedal position is at or below the calibrated idle pedal threshold, `rpm` standard deviation > 50-100 rpm for 30 s, or peak amplitude > 150-200 rpm.  

**Physical Logic:** The goal of idle control is to maintain the desired idle speed under all conditions. The advantages of EDC electronic control include better speed control, anti-surge, and smooth-running behavior. Persistent high fluctuation within the idle window directly reflects control or combustion-stability issues.  

**Source:** Bosch Automotive Handbook  


## 4. References

### Literature

...

### Automotive Resources

Bosch Automotive Handbook

### Dataset Notes

KIT Automotive OBD-II Dataset



## 4. Report Layer Knowledge

Document description, causes, and recommended actions for each proxy failure to support report generation.

### 4.1 cooling_degradation

#### Description

> "With thermostat-controlled cooling, the coolant temperatures range from 95°C to 110°C in the partial-load range and from 85°C to 95°C in the full-load range."

Source: MAHLE "Vehicle Cooling: A Compact Guide for the Workshop" (2021), p.42, "Coolant temperature level"

> "the cooling circuit is under a pressure of 1.0 to 1.5 bar. We are talking about a closed cooling system."

Source: MAHLE (2021), p.7, "Modern engine cooling"

> "use is now made of the fact that pressurized water starts to boil not at 100°C but at 115°C to 130°C"

Source: MAHLE (2021), p.7, "Modern engine cooling"

> "Valve opening temperature: 82°C (180°F)"

> "Maximum valve lift: 10.0 mm/95°C"

> "Valve closing temperature: 77°C (171°F)"

Source: Nissan Patrol Y62 Workshop Manual, "Service Data and Specifications", "Thermostat"

#### Causes

> "Water pump malfunction"

> "Worn or loose drive belt"

> "Thermostat stuck closed"

> "Damaged fins"

> "Dust contamination or paper clogging"

> "Physical damage"

> "Clogged radiator cooling tube"

> "Excess foreign material (rust, dirt, sand, etc.)"

> "Cooling fan does not operate"

> "Damaged fan blades"

> "Damaged radiator shroud"

> "Improper engine coolant mixture ratio"

> "Poor engine coolant quality"

> "Insufficient engine coolant"

> "Cooling hose — Loose clamp"

> "Cracked hose"

> "Water pump — Poor sealing"

> "Radiator cap — Loose"

> "Poor sealing"

> "Radiator — O-ring for damage, deterioration or improper fitting"

> "Cracked radiator tank"

> "Cracked radiator core"

> "Reservoir tank — Cracked reservoir tank"

> "Exhaust gas leakage into cooling system"

> "Cylinder head deterioration"

> "Cylinder head gasket deterioration"

Source: Nissan Patrol Y62 Workshop Manual, "Overheating Cause Analysis", Troubleshooting Chart

> "Overload on engine"

> "Abusive driving"

> "High engine rpm under no load"

> "Driving in low gear for extended time"

> "Driving at extremely high speed"

> "Installed improper size wheels and tires"

> "Dragging brakes"

> "Improper ignition timing"

> "Blocked bumper"

> "Blocked radiator grille"

> "Mud contamination or paper clogging"

> "Blocked condenser"

Source: Nissan Patrol Y62 Workshop Manual, "Overheating Cause Analysis", "Except cooling system parts malfunction"

> "Is the radiator and upstream components (air conditioning condenser) free from contamination, in order to ensure an unrestricted flow of air?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Are the radiator fan and auxiliary fan working?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Does the thermostat open?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Is the radiator clogged?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Is the coolant pump working?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Are the pressure-relief and vacuum valves of the radiator filler cap and expansion tank working?"

Source: MAHLE, p.39–40, "Engine overheats" diagnostic checklist

> "Coolant loss due to radiator damage (stone chip, accident)"

> "Coolant loss due to corrosion or leaky connections"

Source: MAHLE, p.50, "Radiator / Possible causes"

> "Poor heat exchange due to external or internal contamination (dirt, insects, limescale deposits)"

Source: MAHLE, p.50, "Radiator / Possible causes"

> "Contaminated or stale cooling water"

Source: MAHLE, p.50, "Radiator / Possible causes"

> "Impeller loose/broken"

> "Bearing or seal defective"

> "Drive wheel damaged"

> "Cross section narrowing due to corrosion or sealant"

> "Cavitation: Damage to the impeller due to formation and disintegration of vapor bubbles in the coolant"

Source: MAHLE, p.56, "Coolant pumps / Possible causes"

> "They function by means of an expanding wax element that opens a valve and returns the coolant to the radiator for cooling."

> "The thermostat opens at a certain temperature that is predefined for the system and cannot be changed."

Source: MAHLE, p.13, "Thermostats"

#### Actions

**Low Priority (Preventive checks and monitoring):**

> "Check if the reservoir tank engine coolant level is within the 'MIN' to 'MAX' when the engine is cool."

> "Never remove reservoir tank cap when engine is hot."

Source: Nissan Patrol Y62 Workshop Manual, "Engine Coolant", "Inspection" (Classification by Bob based on maintenance urgency)

> "Check coolant temperature sensor and display instrument if necessary"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

> "Measuring the coolant inlet and outlet temperature using an infrared thermometer"

Source: MAHLE, p.50, "Radiator / Troubleshooting" (Classification by Bob based on maintenance urgency)

**Medium Priority (Cleaning, adjustment, and deeper diagnostics):**

> "The mixing proportion of water to antifreeze should be 60:40 to 50:50."

Source: MAHLE, p.36, "Coolant, antifreeze, and corrosion protection" (Classification by Bob based on maintenance urgency)

> "Check radiator for mud or clogging."

> "Apply water by hose to the back side of the radiator core vertically downward."

> "Blow air into the back side of radiator core vertically downward. Use compressed air lower than 490 kPa (5 kg/cm2, 71 psi) and keep distance more than 30 cm (11.8 in)."

Source: Nissan Patrol Y62 Workshop Manual, "Radiator", "Inspection" (Classification by Bob based on maintenance urgency)

> "Clean components if necessary"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

> "Check switch-on point, fuse, thermal switch, and fan control unit, check for mechanical damage"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

> "Check radiator for external contamination, clean with reduced compressed air or a water jet if necessary"

> "Check radiator for external damage and leaks (hose connections, flanges, fins, plastic housing)"

Source: MAHLE, p.50, "Radiator / Troubleshooting" (Classification by Bob based on maintenance urgency)

> "Check coolant for discoloration/contamination (e.g., oil due to defective head gasket) and antifreeze content"

Source: MAHLE, p.50, "Radiator / Troubleshooting" (Classification by Bob based on maintenance urgency)

> "Check temperature at inlet and outlet of the radiator, check flow rate"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and major repairs):**

> "Visually check that there is no significant dirt or rusting on water pump body and vane."

> "Check there is no slack in vane shaft, and that it turns smoothly when rotated by hand."

> "If anything is found, replace water pump."

Source: Nissan Patrol Y62 Workshop Manual, "Water Pump", "Inspection After Removal" (Classification by Bob based on maintenance urgency)

> "Check that valve in thermostat is completely closing at normal temperature."

> "The valve opening temperature is the temperature at which the valve opens and falls from the thread."

> "If the malfunctioning condition, when valve seating at ordinary room temperature, or measured values are out of the standard, replace thermostat."

Source: Nissan Patrol Y62 Workshop Manual, "Water Inlet and Thermostat Assembly", "Inspection After Removal" (Classification by Bob based on maintenance urgency)

> "Measure temperature in front of and behind the thermostat; if necessary, remove thermostat and check in water bath"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

> "Check that the pump wheel is not loose on the drive shaft"

Source: MAHLE, p.39–40, "Engine overheats" troubleshooting (Classification by Bob based on maintenance urgency)

### 4.2 air_intake_maf_anomaly

#### Description

> "It measures the precise amount of air entering the engine so the ECU can calculate the correct amount of fuel needed for an optimal air-fuel balance."

Source: ELTA TechASSIST Bulletin 03, "Understanding the Role of the Mass Airflow Sensor"

> "Because air density changes with temperature, pressure, and humidity, the MAF sensor constantly adjusts these readings in real time."

Source: ELTA TechASSIST Bulletin 03, "Understanding the Role of the Mass Airflow Sensor"

> "the MAF sensor tells the engine how much air is coming in so it can mix the right amount of fuel for smooth, efficient running."

Source: ELTA TechASSIST Bulletin 03, "Understanding the Role of the Mass Airflow Sensor"

> "With the engine at idle, the MAF's PID value should read anywhere from 2 to 7 grams/second (g/s) at idle and rise to between 15 to 25 g/s at 2500 rpm, depending on engine size."

Source: MAF Sensor Testing, Tech-Assist Team

> "A MAF sensor works dynamically, so the question becomes: Is the MAF accurate throughout the engine's rpm range? If it is not linear, various drivability problems can occur."

Source: MAF Sensor Testing, Tech-Assist Team

#### Causes

> "The most common is contamination from oil, dirt, or pollen — often caused by re-oiled aftermarket air filters."

Source: ELTA TechASSIST Bulletin 03, "Why does it fail?"

> "Wiring damage or corrosion at the connector can also interrupt the sensor's signal"

Source: ELTA TechASSIST Bulletin 03, "Why does it fail?"

> "age and vibration can lead to internal degradation of the sensing element itself"

Source: ELTA TechASSIST Bulletin 03, "Why does it fail?"

> "moisture ingress or condensation can distort readings, resulting in incorrect air–fuel ratio calculations and poor engine performance"

Source: ELTA TechASSIST Bulletin 03, "Why does it fail?"

#### Actions

**Low Priority (Preventive checks and monitoring):**

> "Connect a scan tool to see the MAF sensor Parameter Identification Data (PID) information."

Source: MAF Sensor Testing, Tech-Assist Team (Classification by Bob based on maintenance urgency)

> "The most effective way to verify the MAF's signal to the PCM is to graph the sensor's output while running the engine between 1000 and 2250 rpm."

> "A good MAF sensor should show a steady linear rise from 1000 to 2250."

Source: MAF Sensor Testing, Tech-Assist Team (Classification by Bob based on maintenance urgency)

**Medium Priority (Cleaning, adjustment, and deeper diagnostics):**

> "It is highly recommended to change the air filter before replacing the MAF sensors. Dirty, sub standard or worn out air filters can contaminate the element of the sensor and cause it to fail. The air filter should be changed every 15,000 miles to ensure efficiency and durability of the MAF sensors."

Source: ELTA TechASSIST Bulletin 03, "General Fitting Advice — Before Fitting" (Classification by Bob based on maintenance urgency)

> "carefully check the wiring and connectors for any signs of damage or corrosion. Frayed wires, loose connections, or corroded terminals can interrupt the sensor's signal, leading to inaccurate readings or even a complete failure."

Source: ELTA TechASSIST Bulletin 03, "General Fitting Advice — During Fitting" (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and major repairs):**

> "After replacing engine management components, many vehicles will require a reset of the parameters to tell the ECU that a new part has been fitted."

Source: ELTA TechASSIST Bulletin 03, "General Fitting Advice — After Fitting" (Classification by Bob based on maintenance urgency)

### 4.3 accelerator_pedal_sensor

#### Description

> "The accelerator pedal position sensor (APPS) sends an electronic signal to the engine or powertrain control module (ECM/PCM) indicating the position of the accelerator pedal."

> "The ECM/PCM uses that signal to determine the throttle position demanded by the driver."

> "This sensor is most commonly used in vehicles with 'drive by wire' throttle systems, which do not have a cable connecting the accelerator pedal to the throttle."

Source: Innova.com R&D, "Accelerator Pedal Position Sensor", March 5, 2024

> "its function is consistent: it provides the Engine Control Module (ECM) with precise information about the driver's throttle input."

> "This information is essential for the ECM to determine how much air and fuel to deliver to the engine, ensuring the vehicle accelerates smoothly and efficiently."

Source: Innova.com R&D, "Accelerator Pedal Position Sensor: Understanding the Overview, Symptoms, Diagnosis, and Costs", December 26, 2023

> "The typical accelerator pedal position sensor consists of two or three potentiometers, a type of variable resistor. Resistance to voltage passing through the resistor varies with the position of the accelerator pedal."

Source: Innova.com R&D, "Accelerator Pedal Position Sensor", March 5, 2024

> "The APP sensor comprises two individual sensors, with both sensors designed to have individual sensor return wiring. Each sensor has a varying voltage range."

Source: AZoSensors, Kalwinder Kaur, "Accelerator Pedal Position Sensors vs. Throttle Position Sensors", 2019

> "The accelerator pedal position sensor (main) outputs voltage which corresponds to the accelerator pedal depression."

> "The ECM checks whether the voltage is within a specified range."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Technical Description"

> "Output voltage should be between 0.9 and 1.1 volts when foot is released from accelerator pedal."

> "Output voltage should be 4.0 volts or higher when accelerator pedal is fully depressed."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Diagnosis", Step 1

> "Accelerator pedal position sensor (main) output voltage is more than 4.8 volts for 0.3 second."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "DTC Set Conditions — Judgement Criterion"

#### Causes

> "Accelerator pedal position sensor failed."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Troubleshooting Hints"

> "Open accelerator pedal position sensor (main) circuit, harness damage or connector damage."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Troubleshooting Hints"

> "ECM failed."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Troubleshooting Hints"

> "Failure of the APP sensor will most commonly result from continuous exposure to high heat levels because of its location on the floorboard, which is adjacent to the vehicle firewall."

Source: AZoSensors, Kalwinder Kaur, 2019

> "If there is a discrepancy between either the output voltage signal by the potentiometers monitoring the pedal position or the sensor itself, the PCM unit will reduce the performance of the vehicle, thereby setting the APP unit into a 'limp-home-mode'."

Source: AZoSensors, Kalwinder Kaur, 2019

#### Actions

**Low Priority (Preventive checks and monitoring):**

> "Use a diagnostic tool called an OBD2 Scan Tool to check for DTCs related to the sensor."

Source: Innova.com R&D, December 26, 2023 (Classification by Bob based on maintenance urgency)

> "Use a multimeter or an oscilloscope to test the sensor's electrical signals."

Source: Innova.com R&D, December 26, 2023 (Classification by Bob based on maintenance urgency)

**Medium Priority (Cleaning, adjustment, and deeper diagnostics):**

> "Check accelerator pedal moves smoothly within the whole operation range when it is fully depressed and released."

> "Check accelerator pedal securely returns to the fully released position."

Source: Nissan Patrol Y62 Workshop Manual, "Accelerator Control System", "Inspection After Installation" (Classification by Bob based on maintenance urgency)

> "Check harness connector at accelerator pedal position sensor for damage."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Diagnosis", Step 2 (Classification by Bob based on maintenance urgency)

> "Inspect the wires and connectors connected to the sensor to ensure they are not loose or damaged."

Source: Innova.com R&D, December 26, 2023 (Classification by Bob based on maintenance urgency)

> "Check for open circuit and harness damage between accelerator pedal position sensor connector and ECM connector."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Diagnosis", Step 5 (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and major repairs):**

> "Replace the accelerator pedal position sensor."

Source: Mitsubishi Eclipse Cross 2018 Workshop Manual, DTC P2123, "Diagnosis", Step 7 (Classification by Bob based on maintenance urgency)

> "When harness connector of accelerator pedal position sensor is disconnected, perform 'Accelerator Pedal Released Position Learning'."

Source: Nissan Patrol Y62 Workshop Manual, "Accelerator Control System", "Inspection After Installation" (Classification by Bob based on maintenance urgency)

> "a relearn procedure must be performed on Nissan vehicles whenever the APPS is replaced, consisting of turning the ignition key on and off and operating the accelerator pedal in a specific sequence varying with model."

Source: Innova.com R&D, "Accelerator Pedal Position Sensor", March 5, 2024 (Classification by Bob based on maintenance urgency)

> "The APPS is part of the accelerator pedal assembly, so replacement requires replacing the entire pedal assembly."

Source: Innova.com R&D, "Accelerator Pedal Position Sensor", March 5, 2024 (Classification by Bob based on maintenance urgency)


### 4.4 intake_air_temperature_sensor_or_heat_soak_fault

#### Description

> "Air-temperature sensor: This sensor is installed in the air-intake tract. Together with the signal from the boost-pressure sensor, its signal is applied in calculating the intake-air mass."

> "Apart from this, setpoint values for the various control loops (e.g. EGR, boost-pressure control) can be adapted to the air temperature (measuring range –40 to +120 °C)."

Source: Bosch Automotive Handbook, p.327, "Temperature sensors — Application"

> "Its job is simple but crucial: provide accurate air temperature readings to the car's engine control unit (ECU) or powertrain control module (PCM)."

> "Cold air is denser and contains more oxygen, so your car needs more fuel for combustion. On the flip side, warm air requires less fuel."

> "It is used by the Powertrain Control Module to assist with the calculation of idle speed, fuel mixture, and spark advance."

Source: OBDeleven, "P0113 — Intake air temperature sensor 1 circuit high input", December 17, 2024; AutoCodes.com, "P0112 Code"

> "A temperature-dependent semiconductor measuring shunt is fitted inside a housing. This resistor is usually of the NTC (Negative Temperature Coefficient) type."

> "With NTC, there is a sharp drop in resistance when the temperature rises."

> "The measuring shunt is part of a voltage-divider circuit to which 5 V is applied. The voltage measured across the measuring shunt is therefore temperature-dependent."

> "A characteristic curve is stored in the control unit which allocates a specific temperature to every resistance or output voltage value."

Source: Bosch Automotive Handbook, p.327, "Temperature sensors — Application"

> "The sensor operates using a thermistor — a component that measures temperature by changing its resistance. Its resistance decreases as the air temperature rises."

> "The temperature sensing unit uses a thermistor which is sensitive to the change in temperature. The electrical resistance of the thermistor decreases in response to the temperature rise."

Source: OBDeleven, "P0113", December 17, 2024; AutoCodes.com, "P0112 Code"

> "Intake air temperature sensor is built into the mass airflow sensor."

> "The sensor signal is inputted to the ECM connector terminal number 78 from the mass airflow sensor connector terminal number 2."

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Circuit Operation"

> "The intake air temperature sensor converts the intake air temperature into a voltage and inputs the voltage signal to the engine-ECU."

> "In response to the signal, the engine-ECU corrects the fuel injection amount, etc."

> "The intake air temperature sensor is a kind of resistor, which has characteristics to reduce its resistance as the intake air temperature rises. Therefore, the sensor output voltage varies with the intake air temperature, and becomes lower as the intake air temperature rises."

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113 (earlier document), "Function"

> "Intake air temperature sensor output voltage is more than 4.6 V (corresponding to an intake air temperature of -40°C or less) for 2 seconds."

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113 (earlier document), "Trouble Judgement — Judgement Criterion"

> "The sensor output temperature is more than 200°C (392°F) for 2 seconds or more."

> "When the sensor malfunction signal (1h) is output for 2 seconds or more as an intake air temperature sensor malfunction signal."

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "DTC Set Conditions — Judgement Criterion"

> "The intake air temperature sensor monitors the state inside the intake air temperature sensor."

> "Anomalies detected inside the sensor are transmitted to the ECM."

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Technical Description"

#### Causes

> "Faulty IAT sensor: The most common culprit"

> "Failed intake air temperature sensor"

> "Intake air temperature sensor (built into the mass airflow sensor) failed."

Source: OBDeleven, "P0113", December 17, 2024; Mitsubishi Eclipse Cross Workshop Manual, DTC P0113 (earlier document), "Probable Causes"; Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Troubleshooting Hints"

> "Wiring issues: Broken, shorted, or corroded wires"

> "Connector problems: Damaged, corroded, or moisture-filled connectors"

> "Open circuit or harness damage in intake air temperature sensor circuit or loose connector contact"

> "Intake Air Temperature Sensor harness is open or shorted"

> "Intake Air Temperature Sensor circuit poor electrical connection"

Source: OBDeleven, "P0113", December 17, 2024; Mitsubishi Eclipse Cross Workshop Manual, DTC P0113 (earlier document), "Probable Causes"; AutoCodes.com, "P0112 Code"

> "Dirty air filter: Restricts airflow and disrupts sensor readings"

> "Dirty Air Filter"

Source: OBDeleven, "P0113", December 17, 2024; AutoCodes.com, "P0112 Code"

> "ECM failed."

> "Failed engine-ECU"

> "Faulty Powertrain Control Module (PCM)"

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Troubleshooting Hints"; Mitsubishi Eclipse Cross Workshop Manual, DTC P0113 (earlier document), "Probable Causes"; AutoCodes.com, "P0112 Code"

#### Actions

**Low Priority (Preventive checks and monitoring):**

> "Use scan tool (M.U.T.-III SE) to check the data list. Item number 50: Air Temperature Sensor"

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Diagnosis", Step 1 (Classification by Bob based on maintenance urgency)

> "Use an OBD2 scanner to look for any other related trouble codes."

Source: OBDeleven, "P0113", December 17, 2024 (Classification by Bob based on maintenance urgency)

> "Use your scan tool to clear the fault codes."

> "After erasing the DTC, carry out test drive with the drive cycle pattern, and recheck the DTC."

Source: OBDeleven, "P0113", December 17, 2024; Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Diagnosis", Step 2 (Classification by Bob based on maintenance urgency)

> "Normally, the intake air temperature should be similar to or higher than the outside air temperature. If it is significantly lower, it confirms that the issue is still ongoing."

Source: OBDeleven, "P0113", December 17, 2024 (Classification by Bob based on maintenance urgency)

**Medium Priority (Cleaning, adjustment, and deeper diagnostics):**

> "Look for physical damage, corrosion, or disconnections in the IAT sensor and its wiring. Also, check the air filter for excessive dirt or debris."

Source: OBDeleven, "P0113", December 17, 2024 (Classification by Bob based on maintenance urgency)

> "Remove the IAT sensor. Set the multimeter to measure resistance (Ω). Connect the multimeter to the sensor terminals. Use a hair dryer to blow hot air onto the sensor while observing changes in its resistance."

> "Under normal conditions, the sensor's resistance should decrease as it warms up. However, if the resistance remains unchanged as the temperature increases, this indicates that the sensor is faulty and needs replacement."

Source: OBDeleven, "P0113", December 17, 2024 (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and major repairs):**

> "Replace the mass airflow sensor"

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Diagnosis", Step 1 (Classification by Bob based on maintenance urgency)

> "Replace the ECM"

Source: Mitsubishi Eclipse Cross Workshop Manual, DTC P0113-00, "Diagnosis", Step 2 (Classification by Bob based on maintenance urgency)


#### Heat Soak Supplement

**Description — Heat soak definition:**

> "Engine heat soak happens when heat from the engine, exhaust, turbo or cooling system builds up under the bonnet and is absorbed by surrounding components."

> "Heat soak means components are absorbing heat faster than they can get rid of it."

> "When the car is moving, airflow helps carry heat out of the engine bay. When you stop in traffic, sit in a queue or shut the engine off, airflow drops. Hot parts keep radiating heat, but that heat has nowhere useful to go."

> "Hot intake air is less dense, more knock-prone and more likely to make the ECU pull timing or reduce boost."

Source: Exoracing, "Engine Heat Soak: Symptoms, Causes and Fixes", Matthew Marks, May 19, 2026

**Symptoms — Heat soak:**

> "Sluggish after sitting in traffic: The intake system may be pulling in warmer air after sitting still."

> "Power fades after hard pulls: The intercooler, pipework or airbox may not be recovering quickly enough."

> "ECU pulls timing: Hotter air increases knock risk, so the ECU reduces performance to protect the engine."

> "Does IAT climb quickly and recover slowly? If the intake air temperature stays high after traffic or repeated pulls, the intake system is likely soaking up heat."

> "Does the ECU pull performance when hot? Timing reduction or boost reduction after heat build-up supports a heat soak diagnosis."

Source: Exoracing, "Engine Heat Soak: Symptoms, Causes and Fixes", Matthew Marks, May 19, 2026

**Causes — Heat soak sources:**

> "The main heat sources are usually the exhaust manifold, headers, turbocharger, downpipe, radiator, engine block and charge pipework."

> "Heat soak is usually worse on turbocharged cars because the turbocharger adds a concentrated heat source to the engine bay."

> "The turbine housing is driven by hot exhaust gas. Under hard use, the turbo, manifold and downpipe radiate a lot of heat into the surrounding area."

Source: Exoracing, "Engine Heat Soak: Symptoms, Causes and Fixes", Matthew Marks, May 19, 2026

**Actions — Heat soak diagnosis and mitigation:**

> "Check intake air temperatures and intake location."

> "OBD intake air temperature: Does IAT climb quickly and recover slowly?"

> "Ignition timing or boost: Does the ECU pull performance when hot?"

> "Visual inspection: Are parts too close to the heat source? Look for brittle wiring, cooked hoses, melted clips, discoloured sleeving or lines routed close to the turbo or downpipe."

> "After hard driving, especially in a turbo car, avoid switching the engine off immediately. Let it idle gently for a minute or two so oil, coolant and air can keep moving heat away from the turbo, head and block."

Source: Exoracing, "Engine Heat Soak: Symptoms, Causes and Fixes", Matthew Marks, May 19, 2026 (Classification by Bob based on maintenance urgency: Low priority for monitoring, Medium priority for mitigation)


### 4.5 map_load_signal_plausibility_fault

#### Description

> "Intake manifold pressure sensors, also known as MAP sensors (from the English 'Manifold Absolute Pressure'), are used together with the values of the throttle potentiometer to calculate the intake air mass of uncharged gasoline engines."

> "In turbo engines (diesel and petrol) the sensor is mainly used to control the turbocharging system."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin

> "by monitoring the manifold pressure, the MAP sensor continuously provides real-time data to the ECU. This data is used to adjust the air/fuel ratio, the ignition timing, and other parameters for optimal power output and fuel efficiency."

> "It measures the air pressure inside the intake manifold and sends this data to the Engine Control Unit (ECU), which then adjusts fuel injection and ignition timing accordingly."

Source: Innova.com, Joe Ballard, February 16, 2024; Allelco, January 31, 2024

> "There is a diaphragm in the sensor which curves according to the applied pressure. Strain gauges are attached to the diaphragm, which are stretched or compressed according to the curvature. The electrical resistance of the strain gauges changes with elongation."

> "The MAP sensor operates using a diaphragm and strain gauge, which work together to detect changes in pressure between the intake manifold and the outside air."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin; Allelco, January 31, 2024

> "A pressure sensor has 3 electrical connections. One pin has the supply voltage of 5 volts, the second pin has the signal voltage, which is normally between 0.2 V and 4.8 V. The signal ground is located on the third pin."

> "The MAP sensor operates on a 5-volt reference system, meaning it has three electrical connections: a reference voltage, a signal return, and a ground wire."

> "If the pressure is high (more air entering the engine, such as during acceleration), the sensor increases the output voltage. If the pressure is low (less air entering, such as when idling or decelerating), the voltage decreases."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin; Allelco, January 31, 2024

> "For sparkignition engines without supercharging, the vacuum at idle should be between 400 and 500 mbar absolute. When the accelerator pedal is fully depressed, the pressure should be 900 to 1000 mbar absolute."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin

> "the MAP sensor voltage is continuously monitored and compared to predefined values, which helps to detect engine faults. Any deviation from the predefined voltage range may indicate an issue with the sensor or other engine management system components."

Source: Innova.com, Joe Ballard, February 16, 2024

> "Plausibility algorithms address this gap by asking: 'Does this value make sense compared to other measurements and physical expectations?'"

> "an ECU estimating airflow using: Engine speed (RPM), Manifold absolute pressure (MAP), Intake air temperature (IAT), Volumetric efficiency tables. This estimate is compared to the measured MAF signal. If the difference exceeds limits for a calibrated duration, the ECU may conclude that either the MAF or MAP system is unreliable."

> "Stuck detection: Signal remains constant despite operating changes."

> "a mismatch must persist for several seconds or a specific number of drive cycles before triggering a diagnostic trouble code (DTC)."

Source: MOTOR Magazine, Pam Oakes, February 2, 2026

> "If redundancy exists, isolation is straightforward: the system flags the sensor that deviates from the group."

> "if our MAF fails its plausibility check, the ECU may compensate by relying upon MAP and RPM to continue operating with reduced efficiency."

Source: MOTOR Magazine, Pam Oakes, February 2, 2026

#### Causes

> "Possible causes are a lack of voltage supply, cable breaks, defective connectors or a failure of the sensor electronics."

> "Common error messages are: 'Suction pipe pressure or boost pressure signal implausible', 'too low' or 'too high'."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin

> "Contamination: these include contamination from oil or debris."

> "The MAP sensor's sensitive element can be affected by dirt, oil or dust, which disrupts pressure measurement and engine performance."

> "Contamination from Dirt, Oil, and Debris: Dirt, oil, and carbon buildup can clog the MAP sensor, affecting its ability to measure pressure accurately."

Source: Innova.com, Joe Ballard, February 16, 2024; Foxwell, BennettLyle, February 13, 2025; Allelco, January 31, 2024

> "Electrical Issues: a faulty wiring connection or a blown fuse."

> "Faulty Wiring, Loose Connections, or Improper Installation: Damaged wires, corroded connectors, or improper installation can interfere with signal transmission."

Source: Innova.com, Joe Ballard, February 16, 2024; Allelco, January 31, 2024

> "Physical Damage: excessive heat or vibration."

Source: Innova.com, Joe Ballard, February 16, 2024

> "Sensor Age and Wear Over Time: the internal components, including the diaphragm and electronic circuits, can degrade, leading to inaccurate pressure readings."

Source: Allelco, January 31, 2024

> "Vacuum Leaks in the Intake System: If there is a leak in the vacuum hose or intake system, the sensor may detect false pressure levels, causing the ECU to miscalculate fuel delivery and ignition timing."

> "Leaks in the intake system, like cracks or loose joints, make the measured pressure different from the actual one."

Source: Allelco, January 31, 2024; Foxwell, BennettLyle, February 13, 2025

> "If the damping is changed, the control unit calculates incorrect mean values for the suction pipe pressure. Check the function of the throttle and use a hose of the same length and inner diameter when replacing the connecting hose."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin

#### Actions

**Low Priority (Preventive checks and monitoring):**

> "Use a Scan Tool to check the MAP value at several conditions, such as Key ON Engine OFF (KOEO), idling, or Wide-Open Throttle (WOT)."

Source: Innova.com, Joe Ballard, February 16, 2024 (Classification by Bob based on maintenance urgency)

> "When the MAP sensor malfunctions, an OBD2 scanner can be used to quickly diagnose the problem. It can read the fault codes and monitor the sensor's data stream."

Source: Foxwell, BennettLyle, February 13, 2025 (Classification by Bob based on maintenance urgency)

> "Use a Digital Multimeter (DMM) to check the voltage from the MAP sensor connector (between power wiring and ground wiring). The voltage should be around 5V."

> "Turn on the ignition switch (without starting the engine) and measure whether the sensor's reference voltage (usually 5V) is normal."

Source: Innova.com, Joe Ballard, February 16, 2024; Foxwell, BennettLyle, February 13, 2025 (Classification by Bob based on maintenance urgency)

> "After replacement, you need to use a diagnostic tool to clear the historical fault codes."

Source: Foxwell, BennettLyle, February 13, 2025 (Classification by Bob based on maintenance urgency)

**Medium Priority (Cleaning, adjustment, and deeper diagnostics):**

> "Before replacing the sensor, please check the voltage supply (setpoint 5 V) and the lines to the control unit for continuity and ground fault."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin (Classification by Bob based on maintenance urgency)

> "Check the electrical power wiring connections to the sensor to ensure they are secure and not damaged."

> "Check if the sensor's appearance is damaged, whether there are cracks or detachments in the vacuum hoses. Also, confirm whether the wiring harness plug is firmly connected."

Source: Innova.com, Joe Ballard, February 16, 2024; Foxwell, BennettLyle, February 13, 2025 (Classification by Bob based on maintenance urgency)

> "Clean the sensor wire connectors by using an electronic cleaner."

Source: Innova.com, Joe Ballard, February 16, 2024 (Classification by Bob based on maintenance urgency)

> "wiggle the MAP sensor wiring harness while applying vacuum to ensure it isn't contributing to the issue. Always inspect the MAP Sensor vacuum hose, and if the MAP sensor directly plugs into the intake manifold, check its seal for potential splits."

Source: Innova.com, Joe Ballard, February 16, 2024 (Classification by Bob based on maintenance urgency)

> "check the entire intake manifold for leaks by spraying the intake manifold with suitable liquid. If the test liquid hits the leak, the motor reacts with unstable running. Common causes are the intake manifold gasket, vacuum lines and the brake booster."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin (Classification by Bob based on maintenance urgency)

> "Display the suction pipe pressure in the data list and connect a hand pump to the pressure sensor. The display in the data list should correspond over the entire measuring range of the sensor to the pressure or vacuum that you have set on the hand pump."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and major repairs):**

> "In turbo engines, too low boost pressure leads to a loss of power. If the boost pressure sensor is OK, follow the path of the intake air through the engine and check the air filter, the turbocharger, the charge air lines with the charge air cooler and the exhaust gas recirculation and the particle filter, if present."

Source: NGK Spark Plug Europe, "MAP Sensor", Technical Bulletin (Classification by Bob based on maintenance urgency)


### 4.6 electronic_throttle_tracking_fault

**Description:**

> "Electronic throttle control (ETC), also known as drive-by-wire throttle, is an automotive technology that replaces mechanical cables linking the accelerator pedal to the throttle valve with electronic sensors, an engine control unit (ECU), and actuators to precisely regulate engine air intake based on driver input and other vehicle parameters."

> "The system interprets pedal position via potentiometers or Hall effect sensors, processes the signal through the ECU—often integrating data from throttle position sensors, mass airflow sensors, and vehicle dynamics—and drives a DC motor or stepper motor to adjust the throttle plate's angle."

Source: Wikipedia, "Electronic throttle control"

> "A typical ETC system includes the following components: electronic throttle body, accelerator pedal module and electronic control unit."

> "An electric throttle actuator control (TAC) is made of a throttle control motor and two throttle position sensors. When the throttle valve moves, the two throttle position sensors respond with a signal to verify position."

> "These sensors act as potentiometers to convert the throttle valve position into a voltage signal that is sent to the ECM."

Source: Bosch Motorsport, "Electronic Throttle Body"; AutoSuccess, Brendan Baker, December 18, 2019

> "the TAC turns two reduction gears inside the throttle body that link the drive gear from the motor to the throttle plate shaft. On most systems, idle speed is entirely controlled by throttle plate angle."

> "The ECM calculates the opening angle of the throttle valve from these signals and then commands the throttle control motor to make the proper throttle valve opening angle in response to the driving conditions."

Source: AutoSuccess, Brendan Baker, December 18, 2019

> "The ECM then commands the throttle actuator, usually a DC brushless motor or gear-driven stepper motor integrated into the throttle body, via pulse-width modulation (PWM) or H-bridge circuitry to precisely position the butterfly valve."

> "Throttle position sensors (TPS), often dual-redundant for fault detection, provide closed-loop feedback by monitoring the valve's actual angle and relaying it back to the ECM, enabling proportional-integral-derivative (PID) control algorithms to minimize positioning errors within milliseconds."

> "the system achieves rapid response times—typically under 100 ms for full travel"

Source: Wikipedia, "Electronic throttle control"

> "Calibration maps stored in ECM firmware correlate pedal position to throttle opening nonlinearly; for instance, light pedal inputs yield minimal airflow for idle stability, while full depression commands wide-open throttle under safe conditions."

Source: Wikipedia, "Electronic throttle control"

> "Two redundant sensors control the up to date throttle position."

> "All ETBs have an idle air position."

> "Output signal I: 0 to 5 V for 0 to 90°"

> "Output signal II: 5 to 0 V for 0 to 90°"

Source: Bosch Motorsport, "Electronic Throttle Body", Technical Specification

> "The accelerator pedal position sensor is also involved in converting the acceleration movement when the pedal is pressed into an electronic signal, which then initiates throttle body control either as opening or closing movements."

> "The APP sensor comprises two individual sensors, with both sensors designed to have individual sensor return wiring. Each sensor has a varying voltage range."

> "If there is a discrepancy between either the output voltage signal by the potentiometers monitoring the pedal position or the sensor itself, the PCM unit will reduce the performance of the vehicle, thereby setting the APP unit into a 'limp-home-mode'."

Source: AZoSensors, Kalwinder Kaur, 2019

**Causes:**

> "Faulty TAC motor: The motor may have internal electrical or mechanical issues."

> "Faulty Electronic Throttle Body (Very Common) — The entire throttle body unit fails due to internal electronic failure of the actuator motor or position sensors."

Source: ZipTuning, "P2101"; Go-Parts, "P2104"

> "Dirty or Obstructed Throttle Body (Common) — Carbon and grime buildup around the throttle plate causes it to bind."

> "Carbon buildup can accumulate over time around the throttle plate, which the computer responds to by adjusting the home position."

Source: Go-Parts, "P2104"; AutoSuccess, Brendan Baker, December 18, 2019

> "Damaged wiring or poor electrical connections in the TAC motor circuit."

> "Wiring or Connector Issues (Common) — The wiring harness between the throttle body, pedal sensor, and PCM becomes damaged, corroded, or loose."

Source: ZipTuning, "P2101"; Go-Parts, "P2104"

> "Malfunctioning TPS: Incorrect throttle position feedback can cause the ECM to detect an issue."

> "TPS malfunctions often result from electrical wear, contamination, or calibration drift."

Source: ZipTuning, "P2101"; Wikipedia, "Electronic throttle control"

> "Faulty Accelerator Pedal Position (APP) Sensor (Common) — The sensor connected to the gas pedal sends erratic signals that don't match its redundant internal sensors."

Source: Go-Parts, "P2104"

> "Issues with the power or ground circuit for the TAC motor."

Source: ZipTuning, "P2101"

> "Low System Voltage (Rare) — A weak battery or failing alternator starves the electronic throttle control system of power."

Source: Go-Parts, "P2104"

> "Faulty PCM or ECM (rare)."

Source: ZipTuning, "P2101"

**Actions:**

**Low Priority (Diagnostic checks and monitoring):**

> "Retrieve freeze frame data to identify the conditions present when the code was set."

> "Scan for All Trouble Codes and Analyse Freeze Frame Data."

Source: ZipTuning, "P2101"; Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

> "OBD II trouble codes for accelerator pedal position (APP) sensor faults include P0120 – P0124, P0220 – P0229."

> "Any fault that occur in the motor on the throttle body will be detected by the feedback signals from the throttle position sensors. OBD II codes for this kind of problem include P0638 and P0639."

Source: AutoSuccess, Brendan Baker, December 18, 2019 (Classification by Bob based on maintenance urgency)

> "Monitor the voltage readings from APP Sensor 1 and APP Sensor 2 using a scan tool with live data."

> "Check Throttle Position: 10-15% at idle, ~100% fully open."

Source: Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

**Medium Priority (Inspection, cleaning, and electrical testing):**

> "Visually inspect the throttle body, wiring harness, and electrical connections for damage or corrosion."

> "Visually Inspect the Wiring Harness. Check the wiring harness going to the throttle body and accelerator pedal. Look for signs of damage, corrosion, loose connectors, or cracked insulation."

Source: ZipTuning, "P2101"; Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

> "Inspect and Clean the Throttle Body."

Source: Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

> "Test the TAC motor circuit for proper voltage and ground signals using a digital multimeter."

> "Check Power and Ground at the Throttle Body. verify the power supply wire has battery voltage (~12V). Check the resistance between the ground wire and the battery's negative terminal; it must be less than 0.5 Ohms."

Source: ZipTuning, "P2101"; Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

> "Command the throttle plate to open and close using a bidirectional scan tool. If the scanner sends the command but the plate doesn't move, the throttle body assembly is faulty."

Source: Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)

> "Test the TPS and compare readings to manufacturer specifications."

> "Diagnosis involves reading the fault codes to determine the circuit that is experiencing the problem. Then you should check the voltage or resistance of the pedal or throttle position sensors with a DVOM."

Source: ZipTuning, "P2101"; AutoSuccess, Brendan Baker, December 18, 2019 (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and calibration):**

> "Replacing the TAC motor if it fails pinpoint tests."

> "Repairing damaged wiring or connectors in the TAC motor circuit."

> "Replacing the TPS if it is found to be faulty."

Source: ZipTuning, "P2101" (Classification by Bob based on maintenance urgency)

> "If you replace the throttle body, the ECM continues to use the adaptive settings as if the carbon buildup is still there until it is recalibrated. A relearn procedure is necessary to allow the ECM to relearn the baseline idle."

> "Perform the required 'Throttle Relearn' procedure after repair."

Source: AutoSuccess, Brendan Baker, December 18, 2019; Go-Parts, "P2104" (Classification by Bob based on maintenance urgency)


### 4.7 idle_speed_control_or_surge_degradation

**Description:**

> "The speed of vehicle engine at idle state is called an idle speed. An idle speed is basically a rotational speed of an engine when the engine is uncoupled to the drivetrain and the throttle pedal is up to the combustion engine."

Source: Chaturvedi, "Idle Speed Control of an Engine Model Using PID Control System", IJARIIT

> "The aim of idle speed control is to maintain the desired engine speed or rpm to avoid any sort of disturbances such as torque disturbance which arises due to accessory loads on an engine such as air conditioning, power steering/alternators, automatic transmissions, etc."

> "To optimize vehicle and powertrain operations at idle conditions a control has to be established especially when there are conflicting requirements such as improved fuel economy, reduced emissions, and stable combustions."

Source: Chaturvedi, IJARIIT

> "The desired main input of the idle speed controller is the engine speed. In addition, inputs are described as throttle position, vehicle speed, feedforward indicators from automatic transmission, air conditioning, power steering and battery charging system with some environmental measurements such as engine coolant temperature and barometric pressure."

> "The main control output is achieved by controlling the amount of air supplied to the engine."

Source: Chaturvedi, IJARIIT

> "the amount of air controlled by a throttle bypass valve turns the intake manifold air towards the closed primary throttle plate. During the stages of sudden deacceleration air, the bypass valve supplies some additional amount of air in the start and end of damper work which prevents stalling of the engine and provides a smooth transition from higher speed rpm to idle speed rpm."

Source: Chaturvedi, IJARIIT

> "This code is often triggered in vehicles with an electronic throttle control rather than a throttle cable going from the accelerator pedal to the engine."

> "This code usually presents itself when the Powertrain control module detects a lower engine idle speed than what is pre-programmed for the RPM."

> "The P0506 check engine error code means that the Idle Air Control System RPM is lower than expected. The code is triggered when the engine control module detects that your engine's idle speed is lower than the programmed threshold."

> "That speed is measured by either the idle air control system or by the electronic throttle control on newer vehicles. The latter system adjusts how much air is allowed into the engine when the throttle is closed."

Source: AutoZone, "P0506"; Edmunds, "P0506", August 13, 2025

> "When your idle speed is higher than a preset threshold, it triggers error code P0507. Depending on the vehicle, it could be as much as 200 RPMs over the expected rate."

Source: AutoZone, "P0507"

**Causes:**

> "If extra air sneaks in through a cracked hose, loose intake tube, leaking gasket, or PCV system problem, the computer may struggle to maintain the correct idle speed."

> "a vacuum leak could cause an imbalance in the air/fuel ratio, which would affect your RPMs."

> "trouble code P0506 could stem from a vacuum leak or a failed Powertrain control module."

Source: Marble Falls Auto Center, Tyler Ellis; AutoZone, "P0507"; AutoZone, "P0506"

> "carbon buildup can collect around the throttle plate and affect airflow at idle. The engine may surge, dip, or feel like it is trying to correct itself repeatedly."

> "The throttle body could be dirty or damaged."

Source: Marble Falls Auto Center, Tyler Ellis; AutoZone, "P0507"

> "If that valve sticks, clogs, or fails, the engine may not receive the correct amount of air when the throttle is closed. That can lead to idle hunting, stalling, or high idle."

Source: Marble Falls Auto Center, Tyler Ellis

> "a faulty positive crankcase ventilation valve could be the sole cause or part of the problem."

> "Check the positive crankcase ventilation valve and the EGR valve. Any electrical or physical damage to these valves will alter your idle air control."

Source: AutoZone, "P0506"; AutoZone, "P0507"

> "If the mass airflow sensor is dirty or reading incorrectly, the engine may receive the wrong fuel mixture, causing the idle to fluctuate."

Source: Marble Falls Auto Center, Tyler Ellis

> "If the EVAP purge valve sticks open, the engine may receive extra vapor at the wrong time, creating a rough or surging idle."

Source: Marble Falls Auto Center, Tyler Ellis

> "Low fuel pressure, dirty injectors, a weak fuel pump, or poor injector spray patterns can make the engine struggle to maintain a steady idle."

Source: Marble Falls Auto Center, Tyler Ellis

> "Worn spark plugs, weak ignition coils, or misfires can cause the RPM to dip, shake, or bounce because one or more cylinders are not contributing evenly."

Source: Marble Falls Auto Center, Tyler Ellis

> "Loose connections, frayed wires or damaged sensors could give you a false reading or cause your electronic throttle control to behave erratically."

Source: AutoZone, "P0507"

> "the intake exhaust or air path could be restricted."

Source: AutoZone, "P0506"

> "a failed Powertrain control module."

> "Your entire powertrain control module could also have an issue, which would affect the entire communication system and the sensors related to P0507."

Source: AutoZone, "P0506"; AutoZone, "P0507"

**Actions:**

**Low Priority (Diagnostic checks and monitoring):**

> "Scan for diagnostic trouble codes. Codes for lean conditions, rich conditions, misfires, throttle control, EVAP, airflow, or temperature sensors can point the inspection in the right direction."

> "You can use an OBD scanner tool to retrieve and confirm the error code."

> "Check live engine data. Fuel trims, airflow readings, coolant temperature, throttle position, oxygen sensor activity, and idle speed data can show what the computer is seeing."

Source: Marble Falls Auto Center, Tyler Ellis; Edmunds, "P0506", August 13, 2025 (Classification by Bob based on maintenance urgency)

> "Verify the repair with a road test and idle test. A proper fix means the idle stays stable with the engine cold, warm, in gear, parked, and with accessories like AC turned on."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

**Medium Priority (Inspection, cleaning, and testing):**

> "Inspect for vacuum leaks. Intake hoses, PCV hoses, brake booster lines, intake gaskets, and vacuum connections should be checked for cracks, looseness, or leaks."

> "checking intake hoses and gaskets for air leaks."

Source: Marble Falls Auto Center, Tyler Ellis; Edmunds, "P0506", August 13, 2025 (Classification by Bob based on maintenance urgency)

> "Inspect and clean the throttle body if needed. Carbon buildup around the throttle plate can affect idle airflow. Some vehicles may require a relearn procedure after cleaning."

> "You may be able to clean the throttle body and idle air control valve to get them back in working order."

Source: Marble Falls Auto Center, Tyler Ellis; Edmunds, "P0506", August 13, 2025 (Classification by Bob based on maintenance urgency)

> "Test the idle air control system if equipped. If the vehicle uses an idle air control valve, it should be checked for sticking, clogging, or electrical failure."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

> "Inspect the mass airflow sensor. A dirty or failing airflow sensor can cause incorrect fuel calculations and unstable idle."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

> "Check the EVAP purge valve. A stuck-open purge valve can create rough idle, hard starts after fueling, or RPM fluctuation."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

> "Inspect ignition components. Spark plugs, ignition coils, and misfire data should be checked if the engine shakes or runs rough."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

> "Check fuel pressure and injector performance. Fuel delivery problems can cause idle instability, hesitation, and stalling."

Source: Marble Falls Auto Center, Tyler Ellis (Classification by Bob based on maintenance urgency)

> "testing your vehicle's electrical system, and checking wires and connectors to ensure they aren't damaged."

Source: Edmunds, "P0506", August 13, 2025 (Classification by Bob based on maintenance urgency)

**High Priority (Component replacement and repair):**

> "If that doesn't work, you may need to repair or replace the idle air control valve."

Source: Edmunds, "P0506", August 13, 2025 (Classification by Bob based on maintenance urgency)
