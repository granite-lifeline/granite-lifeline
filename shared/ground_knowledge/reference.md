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

