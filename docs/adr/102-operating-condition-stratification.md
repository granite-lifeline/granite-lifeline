# ADR 102: Hierarchical Operating-Condition State Machine and Stratified Analysis

## Status

Accepted

## Date

2026-07-15

## Context

The cleaned OBD-II dataset produced under ADR 101 has already been timestamp-aligned, resampled to a uniform 1 Hz grid, missing-value treated, suspicious-value flagged, and quality-audited within stable `trip_id`/`segment_id` boundaries. It is not yet interpretable at the level required by downstream feature engineering, proxy checks, and Model Layer consumption.

The reason is physical, not procedural. The same raw signal carries different meaning under different engine thermal states and driving conditions. A `maf`, `map`, or `intake_temp` value that is entirely normal at high load can be abnormal at idle, and a coolant temperature that is expected after warm-up would be implausible at a cold start. Interpreting each signal only from its global distribution — a global mean, a global quantile, or a single fixed threshold — would therefore mistake normal state-dependent behaviour for anomalous behaviour, and vice versa.

The Data Layer consequently needs a reproducible, auditable assignment of operating condition to every cleaned row, together with signal statistics stratified by that condition. This assignment must serve three downstream consumers: the feature window generator, which aggregates condition proportions and purity per window; derived-feature calculation, which needs operating condition as a `validity_condition` rather than an ordinary descriptive field; and the proxy failure checks (ADR 103), whose enable windows are defined in terms of thermal and kinematic state (for example `post_warmup__high_load` or `post_warmup__steady_driving`).

A complication is that the dataset does not expose every physical quantity the ideal state definition would use. There is no catalyst-temperature channel, so a true catalyst thermal state cannot be measured directly. Critical inference fields can also be individually missing on a small number of rows, and the state machine must degrade rather than fail when that happens.

## Decision

The Data Layer adopts a two-level hierarchical operating-condition state machine, computed within `segment_id` boundaries, with explicit quality and confidence provenance:

1. **Primary state — engine thermal state.** Each row is assigned one of `engine_off`, `warmup`, `post_warmup`, or `unknown`. `rpm < 50 rpm` classifies the row as `engine_off`. A running engine that has not met the post-warm-up criteria is `warmup`. `unknown` is used when critical fields are missing and the row cannot be inferred reliably.

2. **Proxy-based `post_warmup` inference.** Because catalyst temperature is not measured, `post_warmup` is inferred, not observed. It uses `coolant_temp >= 75 degC` as the baseline condition combined with at least one auxiliary condition: during idle `rpm < 850 rpm`; during moving operation `cumulative_air_mass_g > 1500 g`; or intake-to-ambient heat soak `intake_temp - ambient_temp > 8 degC`. `post_warmup` is documented explicitly as a proxy thermal state derived from coolant temperature, cumulative MAF, and heat-soak behaviour — not a directly measured catalyst state.

3. **Child state — kinematic operating condition.** The child-state machine is active only when the engine is not off. Its categories are `idle`, `acceleration`, `deceleration`, `high_load`, `steady_driving`, `inactive_engine_off`, and `unknown`, resolved under the fixed precedence `Idle > High_Load > Acceleration > Deceleration > Steady_Driving`. Rules: `idle` when `speed_smooth_kmh < 1 km/h` and `|accel_ms2_smooth| < 0.15 m/s2`; `acceleration` when moving with `accel_ms2_smooth >= 0.15 m/s2` and not high-load; `deceleration` when moving with `accel_ms2_smooth <= -0.15 m/s2`; `high_load` when moving with `VSP >= 20 kW/t` or `accel_ms2_smooth >= 1.2 m/s2`; `steady_driving` when moving but satisfying none of the above.

4. **Smoothing and high-load physics.** Vehicle speed is first passed through a centered 3-second moving average (`speed_smooth_kmh`), and acceleration is computed from the smoothed speed (`accel_ms2_smooth = diff(speed_smooth_kmh / 3.6) / dt`). High-load classification uses the Vehicle Specific Power method `VSP = v * (1.1 * a + 0.132) + 0.000302 * v^3` (`v` in m/s, `a` in m/s2, VSP in kW/t).

5. **Continuity discipline.** Time differencing, moving-average smoothing, cumulative intake-air-mass integration, and short-fragment cleanup are all reset within each `segment_id`, so no stateful calculation crosses a recording break declared under ADR 101. A 3-second minimum-duration cleanup merges isolated child-state fragments shorter than 3 seconds into neighbouring stable states, again only within the same `segment_id`.

6. **Quality flags and confidence.** `condition_quality_flags` records row-level flags (`OK`, `MISSING_ECT`, `MISSING_MAF`, `MISSING_RPM`, `MISSING_SPEED`). `condition_confidence` has three levels: `high` when all four critical fields (`rpm`, `speed`, `coolant_temp`, `maf`) are complete; `medium` when a non-fatal field such as `coolant_temp` or `maf` is missing but a degraded inference path can continue; and `low` when a fatal field such as `speed` or `rpm` is missing and the row must rely on forward state inheritance within the same `segment_id`.

7. **Stratified output contract.** The stage emits a row-level enriched table plus overall state counts, per-condition signal statistics, and a rule-constant table, and publishes `thermal_state`, `child_state`, `operating_state`, `condition_confidence`, and `condition_quality_flags` as part of the cross-layer data contract.

On the current reference dataset the primary state is dominated by `post_warmup` (about 77.85% of rows), with `warmup` about 18.63% and `engine_off` about 3.51%. Among child states, `steady_driving` (about 35.4%), `deceleration` (about 26.1%), `acceleration` (about 17.1%), `high_load` (about 10.5%), and `idle` (about 7.3%) are the major driving states. Almost all rows carry `high` confidence (about 99.99%); only a handful are `medium` or `low` because of missing `rpm` or `speed`.

## Rationale

### Why a two-level hierarchical state machine?

Thermal state and driving state answer different questions and have different valid interpretations, so they cannot be collapsed into one flat label without losing information. Thermal state governs whether a signal should be read against a warm-up trajectory or a regulated plateau; driving state governs whether load-dependent signals are being sampled under idle, cruise, or high load. Making the thermal state primary and activating the kinematic child state beneath it lets each downstream consumer group by whichever level it needs. It also produces the combined `operating_state` (for example `post_warmup__high_load`) that ADR 103's proxy enable windows are written against.

### Why is `post_warmup` a proxy thermal state?

The physically ideal warm-up indicator would be catalyst temperature, which the dataset does not contain. Rather than omit the concept, the state machine infers it from coolant temperature as a baseline plus at least one corroborating auxiliary condition — hot-idle RPM, cumulative intake air mass, or intake-air heat soak. Requiring the baseline plus corroboration reduces the chance of promoting a row to `post_warmup` on coolant temperature alone. The document is explicit that this is an inferred proxy, so downstream stages do not treat it as a measured catalyst state.

### Why smooth speed and use VSP for high load?

At 1 Hz with integer-quantized speed, raw sample-to-sample differences produce noisy, isolated acceleration spikes. A centered 3-second moving average before differencing suppresses these discretization artefacts, and the 3-second minimum-duration cleanup removes isolated one-second state jumps that would otherwise fragment the child state. Vehicle Specific Power is used for high-load classification because it combines speed and acceleration into a single physically grounded power-demand measure, so high load is defined by actual power demand rather than by a high value on any single raw channel such as MAF or accelerator pedal.

### Why stratify signal statistics by operating condition?

The per-condition signal summary is what allows downstream stages to define `validity_condition` rules and reference ranges that respect physical state. The reasonable range of `maf` or `map` at idle differs from its range in steady driving or at high load, so a single global range would be simultaneously too loose in one state and too tight in another. Stratified statistics make that difference explicit and available to feature engineering and the proxy checks.

### Why the confidence and quality tiers?

Critical inference fields are occasionally missing on individual rows. Failing the whole state machine on those rows would discard usable data; silently guessing would hide the degradation from downstream stages. The three-tier `condition_confidence`, together with the specific `MISSING_*` flags, lets each row continue through the most reliable available inference path while recording how much to trust the result — so the window generator can down-weight or mark windows that contain many low-confidence rows.

## Alternatives Considered

### Interpret Signals Only from Global Distributions

**Rejected.** Applying global means, global quantiles, or fixed thresholds ignores that the same signal has different physical meaning across thermal and driving states. It would flag normal high-load airflow as abnormal and miss genuinely abnormal idle behaviour, defeating the purpose of downstream anomaly and proxy work.

### A Single Flat State Label

**Rejected.** Merging thermal and kinematic state into one flat category discards the distinction downstream consumers depend on. Proxy enable windows, warm-up-phase features, and idle-stability features each need one level or the other; a flat label would force every consumer to re-derive the missing dimension.

### Unsupervised Clustering of Operating Conditions

**Rejected.** Data-driven clusters are not physically labelled, are not reproducible as a fixed contract, and cannot be audited against explicit rule constants. The downstream layers require named, stable states (`post_warmup`, `high_load`, and so on) with published thresholds, which a clustering partition does not provide.

### Measure Catalyst Thermal State Directly

**Rejected — not available.** The dataset contains no catalyst-temperature channel, so a directly measured post-warm-up thermal state is impossible. The proxy inference from coolant temperature, cumulative MAF, and heat soak is the available substitute, and is documented as such rather than presented as a measured state.

### Drop Low-Confidence Rows

**Rejected.** Rows with a missing non-fatal field remain usable through a degraded inference path, and even fatal-field rows can inherit state forward within a segment. Discarding them would lose data and coverage; recording confidence instead preserves the rows while letting downstream stages decide how much to trust them.

## Consequences

### Positive

- Every cleaned row carries an auditable thermal state, kinematic state, combined operating state, confidence level, and quality flags.
- Signal statistics stratified by operating condition let downstream stages define state-aware reference ranges and `validity_condition` rules instead of global thresholds.
- The combined `operating_state` labels provide the enable-window vocabulary that ADR 103's proxy checks are written against.
- All stateful calculations are bounded by `segment_id`, so operating-condition inference inherits ADR 101's continuity guarantees and cannot leak across recording breaks.
- Rule constants and the VSP formula are published in a dedicated table, making the state machine reproducible and auditable rather than hidden in analysis code.
- The window generator can consume the enriched table directly and does not need to recompute operating conditions.

### Negative

- `post_warmup` is a proxy thermal state, not a measured catalyst state, so its precision is limited by the corroborating signals available.
- The threshold constants (75 degC, 850 rpm, 1500 g, 8 degC, VSP 20 kW/t, and so on) are project-specific and tied to this dataset and its 1 Hz frequency.
- The 3-second smoothing and cleanup reduce fragmentation but slightly blur genuine short transitions near their boundaries.
- Downstream stages must carry and reason about five additional state/quality fields, and must handle `medium`/`low` confidence rows appropriately.

### Mitigation Strategies

- Rule constants and the VSP formula are stored in `operating_condition_rules.csv` for reproducibility and auditing.
- Per-condition signal statistics are published so reference ranges can be derived per state rather than globally.
- The window generator records the proportion of low-confidence samples per window and marks mixed-operating-condition or low-quality windows in the window index.
- Train/validation/test splits are advised to consider `trip_id`, `segment_id`, and operating-condition distribution together to avoid leakage between neighbouring windows.

## Implementation

### Code Location

- Analysis implementation: `data_layer/operating_condition_statistics/src/operating_condition_analysis.py`
- Methodology write-up: `data_layer/operating_condition_statistics/operating_condition_analysis.md`

### Rule Constants

Published in `data_layer/operating_condition_statistics/operating_condition_rules.csv`, including:

- `engine_off_rpm_max = 50 rpm`
- `post_warmup_ect_min = 75 degC`
- `post_warmup_cumulative_air_min = 1500 g`
- `post_warmup_iat_aat_delta_min = 8 degC`
- `hot_idle_rpm_max = 850 rpm`
- `idle_speed_max = 1 km/h`, `moving_speed_min = 1 km/h`
- `accel_abs_deadband = 0.15 m/s2`
- `high_load_vsp_min = 20 kW/t`, `high_load_accel_min = 1.2 m/s2`
- `speed_smoothing_window = 3 s`, `min_state_duration = 3 s`
- `vsp_formula = v*(1.1*a+0.132)+0.000302*v^3` (kW/t)

### Output Files

- `operating_condition_enriched.csv` — row-level auditable table (index, raw signals, intermediate calculations, state fields, quality fields); the primary input to window generation and derived-feature calculation.
- `operating_condition_counts_overall.csv` — overall distribution of thermal state, child state, operating state, confidence, and quality flags.
- `operating_condition_signal_summary.csv` — per-condition signal statistics grouped by `thermal_state`, `child_state`, `operating_state`, and `condition_confidence`.
- `operating_condition_rules.csv` — rule constants and formulas.

### Data Contract Fields

Published to the cross-layer contract (see `docs/INTERFACE.md`): `thermal_state`, `child_state`, `operating_state`, `condition_confidence`, and `condition_quality_flags`.

## Related Decisions

- ADR 101: Continuity-Aware Data Cleaning and Trip Segmentation — provides the cleaned, segmented dataset and the `segment_id` continuity boundary this stage reuses.
- ADR 103: Proxy Failure Screening and Theoretical-Basis Collection — proxy enable windows are defined in terms of the thermal and kinematic states assigned here.
- ADR 104: Graded Synthetic Fault-Injection Validation for Proxy Checks — injection windows and derived-feature recomputation respect these operating-condition boundaries.
- ADR 201: Residual Detection over Classification — the Model Layer consumes the operating-condition fields as forwarded context.
- `docs/INTERFACE.md`: cross-layer field definitions (§1.1 operating-condition fields).

## References

- AUTOSAR. (2020). Specification of basic software manager (AUTOSAR CP Release 20-11) — hierarchical state-machine structure.
- California Air Resources Board. (2019). §1968.2 (OBD II), Title 13 CCR — hot-idle RPM as a warm-up corroboration reference.
- Mondal, S., & Shaver, G. M. (2001). Model-based estimation of catalyst temperature for OBD systems (SAE 2001-01-0935) — cumulative intake-air-mass proxy for catalyst warm-up when catalyst temperature is unavailable.
- Heywood, J. B. (2018). Internal combustion engine fundamentals (2nd ed.) — intake-air heat-soak indicator.
- Ligterink, N. E., van de Burgwal, E., & Kastijn, H. (2009). VERSIT+ (TNO) — kinematic operating-condition categorization.
- Jimenez-Palacios, J. L. (1999). Understanding and quantifying motor vehicle emissions with Vehicle Specific Power (VSP) (MIT) — VSP method for high-load classification.
