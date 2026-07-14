# Operating Condition Analysis

## 1. Purpose

The cleaned OBD dataset has already gone through timestamp alignment, 1 Hz resampling, missing-value handling, suspicious-value flagging, and basic quality auditing. However, vehicle signals should not be interpreted only from their global distributions, because the same signal can have different physical meanings under different thermal states and driving conditions.

The analysis has the following objectives:

- Build a reproducible hierarchical operating-condition state machine based on engine thermal state and vehicle motion state.
- Provide row-level operating-condition labels and auditable intermediate variables for the downstream feature window generator.
- Provide operating-condition evidence for `validity_condition` rules used in derived-feature calculation.
- Record the impact of missing critical fields on state-machine inference, and separate high-, medium-, and low-confidence samples.
- Summarize signal distributions by operating condition, so that normal behavior under different physical states is not mistaken for abnormal behavior.

## 2. Methodology

The script first reads the cleaned 1 Hz dataset. It then resets time differencing, moving-average smoothing, cumulative intake-air-mass integration, and short-segment cleanup within each `segment_id`. This prevents acceleration or accumulated thermal-energy proxies from being computed across segment boundaries, which would otherwise create artificial state transitions.

### 2.1 Primary State: Engine Thermal State

The primary state uses a hierarchical state machine.[^1] The script first determines engine and thermal state, then activates the lower-level driving child-state machine. The primary states are:

- **engine_off:** the engine is off.
- **warmup:** the engine is running but has not yet reached a thermally stable state.
- **post_warmup:** the engine has entered the post-warmup operating state.
- **unknown:** critical fields are missing, so the current row cannot be inferred reliably.

The core primary-state rules are:

- If `rpm < 50 rpm`, classify the row as `engine_off`.
- If the engine is running but the post-warmup criteria are not yet satisfied, classify the row as `warmup`.
- `post_warmup` is inferred using a proxy method: `coolant_temp >= 75 degC` is used as the baseline condition, combined with at least one of the following auxiliary conditions:
  - During idle, `rpm < 850 rpm`.[^2]
  - During moving operation, cumulative intake air mass satisfies `cumulative_air_mass_g > 1500 g`.[^3]
  - Intake air temperature is significantly higher than ambient temperature: `intake_temp - ambient_temp > 8 degC`.[^4]

Because the dataset does not include catalyst temperature, `post_warmup` is not a directly measured catalyst thermal state. It is a proxy-based thermal state inferred from coolant temperature, cumulative MAF, and heat-soak behavior.

### 2.2 Child State: Kinematic Operating Condition

The child state is active only when the primary state is not `engine_off`. The child-state categories and rules are:[^5]

- **idle:** idle operation. `speed_smooth_kmh < 1 km/h` and `|accel_ms2_smooth| < 0.15 m/s2`.
- **acceleration:** normal acceleration. `speed_smooth_kmh >= 1 km/h` and `accel_ms2_smooth >= 0.15 m/s2`, while not satisfying the high-load criteria.
- **deceleration:** deceleration. `speed_smooth_kmh >= 1 km/h` and `accel_ms2_smooth <= -0.15 m/s2`.
- **high_load:** high-load operation. `speed_smooth_kmh >= 1 km/h`, and either `VSP >= 20 kW/t` or `accel_ms2_smooth >= 1.2 m/s2`.
- **steady_driving:** cruise or steady driving. The vehicle is moving but does not satisfy the idle, high-load, acceleration, or deceleration criteria.
- **inactive_engine_off:** the child-state machine is inactive when the engine is off.
- **unknown:** the child state cannot be inferred reliably.

The child-state precedence is:

```text
Idle > High_Load > Acceleration > Deceleration > Steady_Driving
```

Before child-state classification, the script applies a centered 3-second moving average to the base vehicle-speed signal:

```text
speed_smooth_kmh = centered moving average(speed, 3 s)
```

The smoothed speed is then used to compute acceleration:

```text
accel_ms2_smooth = diff(speed_smooth_kmh / 3.6) / dt
```

High-load classification uses the Vehicle Specific Power (VSP) method:[^6]

```text
VSP = v * (1.1 * a + 0.132) + 0.000302 * v^3
```

where `v` is in `m/s`, `a` is in `m/s2`, and VSP is expressed in `kW/t`.

To reduce isolated one-second state jumps caused by discrete 1 Hz speed readings, the script applies a 3-second minimum-duration cleanup to `child_state`. Isolated child-state fragments shorter than 3 seconds are merged into neighboring stable states. This cleanup is also performed only within the same `segment_id`.

### 2.3 Quality Flags and Confidence

`condition_quality_flags` stores row-level quality flags as a string list:

- `OK`: no critical field is missing.
- `MISSING_ECT`: `coolant_temp` is missing, so the primary thermal state must rely on cumulative intake air mass, heat-soak evidence, or state memory for degraded inference.
- `MISSING_MAF`: `maf` is missing, so cumulative intake air mass cannot be used to support `post_warmup` inference.
- `MISSING_RPM`: `rpm` is missing, so `engine_off` cannot be determined accurately, and hot-idle RPM cannot be used to confirm warm-up completion.
- `MISSING_SPEED`: `speed` is missing, so smoothed speed, acceleration, and kinematic child state cannot be computed reliably.

`condition_confidence` has three levels:

- `high`: all four critical fields, `rpm`, `speed`, `coolant_temp`, and `maf`, are complete.
- `medium`: a non-fatal field such as `coolant_temp` or `maf` is missing, but the state machine can continue through a degraded inference path.
- `low`: a fatal field such as `speed` or `rpm` is missing, so the row must rely on forward state inheritance within the same `segment_id`.

## 3. Output Files

### 3.1 operating_condition_enriched.csv

This is the main row-level auditable output table. It is also the primary input for downstream window generation and derived-feature calculation.

The main field groups are:

- Original index fields.
- Original signal fields.
- Intermediate calculation fields.
- State fields.
- Quality fields.

The downstream window generator can directly use this table to summarize operating-condition proportions, dominant operating condition, confidence distribution, maximum VSP, cumulative thermal-state proxies, and related quantities within each window.

### 3.2 operating_condition_counts_overall.csv

This file summarizes the overall distribution of the states produced by the new state machine.

The main fields are:

- `state_type`: the type of object being summarized, such as `thermal_state`.
- `state`: the specific state or quality flag.
- `row_count`: number of rows.
- `duration_seconds`: duration. Since the cleaned dataset is sampled at 1 Hz, this value is usually equal to the row count.
- `row_rate`: proportion of rows.
- `duration_rate`: proportion of duration.

### 3.3 operating_condition_signal_summary.csv

This file contains signal statistics after stratification by operating condition. Each signal is summarized under the following grouping dimensions:

- `thermal_state`
- `child_state`
- `operating_state`
- `condition_confidence`

The main fields are:

- `group_type`: grouping dimension.
- `group_value`: specific state or group value.
- `signal`: signal name.
- `unit`: signal unit.
- Completeness statistics.
- Distribution statistics.

This file supports downstream definition of `validity_condition` rules and reference ranges. For example, the reasonable range of the same `maf` or `map` signal differs across idle, steady driving, and high-load operation, so these signals should not be interpreted only through global means or global quantiles.

### 3.4 operating_condition_rules.csv

This file records the rule constants and formulas used by the new state machine for reproducibility and auditing.

The main fields are:

- `rule_name`: rule name.
- `value`: threshold value or formula.
- `unit`: unit.
- `description`: rule description.

## 4. Main Findings

The current results show that the primary state is dominated by `post_warmup`, which accounts for about 77.85% of the data. `warmup` accounts for about 18.63%, and `engine_off` accounts for about 3.51%. Among child states, `steady_driving`, `deceleration`, `acceleration`, and `high_load` are the major driving states.

The missing rate of critical fields is very low. In terms of quality confidence, almost all samples are labeled as `high`; only a very small number of rows are labeled as `low` because of missing `rpm` or `speed`. This indicates that the cleaned dataset is generally suitable for downstream window generation, operating-condition-stratified analysis, and derived-feature calculation.

The small number of `medium` and `low` samples should not materially affect the overall analysis. However, the downstream window generator should still record the proportion of low-confidence samples within each window. If a window contains many `low` samples, it should be used cautiously for model training or physical interpretation.

## 5. Downstream Impact

### 5.1 Impact on the Feature Window Generator

The downstream window generator does not need to recompute operating conditions. It can read `operating_condition_enriched.csv` directly. Within each window, it should aggregate:

- Proportion and dominant state of `thermal_state`.
- Proportion and dominant state of `child_state`.
- Proportion and purity of `operating_state`.
- Distribution of `condition_confidence`.
- Summary statistics of `speed_smooth_kmh`, `accel_ms2_smooth`, and `vsp_kw_per_t`.
- `cumulative_air_mass_g`, or the change in cumulative intake air mass within the window.

Windows should not cross `segment_id` boundaries. If a window contains severe operating-condition mixing or a high proportion of low-confidence samples, it should be marked as a low-quality window or mixed-operating-condition window in the window index.

### 5.2 Impact on Derived-Feature Calculation

Derived features should be interpreted together with operating condition. Some features have stable physical meaning only under specific states:

- Thermal-management features are more appropriate to interpret under `post_warmup` or an explicit `warmup` phase.
- MAF/MAP/TPS response features need to distinguish `steady_driving`, `acceleration`, and `high_load`.
- Idle-stability features should primarily be computed under `idle`.
- High-load-related features should preferentially use `high_load` windows, rather than simply relying on high MAF or high accelerator-pedal values.

Therefore, operating condition should be treated as a validity condition in downstream feature engineering, not merely as an ordinary descriptive field.

### 5.3 Impact on Baseline Experiments

Baseline results should be interpreted in the context of operating condition. If the modeling target involves signal quality, anomaly detection, or vehicle-behavior prediction, the model should not be allowed to learn only the operating-condition distribution itself. Train, validation, and test splits should also consider `trip_id`, `segment_id`, and operating-condition distribution to avoid information leakage between neighboring windows.

## 6. References

[^1]: AUTOSAR. (2020). Specification of basic software manager (AUTOSAR CP Release 20-11). AUTOSAR Development Partnership.

[^2]: California Air Resources Board. (2019). Malfunction and diagnostic system requirements--1968.2 and subsequent model-year passenger cars, light-duty trucks, and medium-duty vehicles and engines (OBD II) (Title 13, California Code of Regulations, Section 1968.2). California Secretary of State.

[^3]: Mondal, S., & Shaver, G. M. (2001). Model-based estimation of catalyst temperature for OBD systems (SAE Technical Paper No. 2001-01-0935). SAE International. https://doi.org/10.4271/2001-01-0935

[^4]: Heywood, J. B. (2018). Internal combustion engine fundamentals (2nd ed.). McGraw-Hill Education.

[^5]: Ligterink, N. E., van de Burgwal, E., & Kastijn, H. (2009). VERSIT+: A statistical model for forecasting road traffic emissions (Report No. TNO-034-UT-2009-01396/RPT). TNO Science and Industry.

[^6]: Jimenez-Palacios, J. L. (1999). Understanding and quantifying motor vehicle emissions with vehicle specific power (VSP) [Doctoral dissertation, Massachusetts Institute of Technology]. MIT DSpace.
