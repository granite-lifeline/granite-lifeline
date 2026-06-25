# Failure-Type Research (Model Layer — Anomaly Detection Epic)

Dataset: KIT Automotive OBD-II Dataset (81 trips, single Seat Leon, various driving conditions)

## The core problem
The dataset has **no real failure labels** — it's all healthy-vehicle driving data. The
dataset documentation (RADAR DOI: 10.35097/1130) describes road conditions via filename
suffixes (Normal, Frei, Stau, Messfehler) but does not explicitly state that the vehicle
was fault-free. We therefore treat this as a proxy healthy baseline, justified by:
1. No DTC/MIL fault codes are present in the logged signals.
2. Core sensor statistics (see Healthy Baseline Reference Table below) fall within
   Seat Leon manufacturer-normal ranges and automotive industry standards [M1][M2].
3. Cross-signal correlations (e.g. MAF–MAP ~0.83) are consistent with normal engine
   behaviour [R3][R4].

Per the brief ("Define a proxy 'failure condition' if real labels are missing"), we analysed
the available sensor signals across all 81 trips to find behaviours that plausibly indicate
component degradation, even though we cannot validate against an actual labelled failure.

---

## Confirmed anomaly types (interface_table v3)

### 1. `cooling_system_stress`

> *Proxy condition. The KIT dataset contains no real fault labels — this definition is based
> on expected sensor behaviour from automotive engineering literature, not labelled failures.*

**Component**: Cooling system / thermostat / water pump
**Primary signals**: `coolant_temp` (Master Table #4), `coolant_slope` (Master Table #12)

**Findings (across 81 trips):**
- Steady-state coolant temp is typically **90–95°C** (normal thermostat range); a few trips
  reach **100–103°C**. Normal operating temperature is manufacturer-confirmed at 80–120°C
  (oil temperature equivalent, thermally coupled to coolant) [M1].
- Warm-up rate is **10–16°C/min** during cold start, dropping to ~0°C/min once warm.
- Cooling system operates under pressure, which raises the boiling point above 100°C —
  temperatures at or slightly above 100°C are therefore within normal operating range
  for a pressurised system with G12++/G13 coolant additive [M2, §4.30].

**Proxy definition**: After the initial warm-up phase (coolant temp has exceeded ~85°C at
least once), flag elevated risk if:
- `coolant_temp` exceeds **~100°C**, and/or
- `coolant_slope` remains **>2–3°C/min** instead of plateauing

This directly matches the brief's worked example: *"Coolant temperature rising faster than
normal — possible water pump degradation."* The detection target is the transition from
normal Zone B toward the warning Zone C as defined in the Seat Leon owner's manual [M1].
One-class classification approaches have been applied to this exact problem — coolant
sensor anomaly detection — using engineered features derived from the temperature time
series [R6].

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `coolant_temp` | 85–105°C steady state [M1][M2] | Rising above 100°C | Sustained increase post warm-up, not returning to baseline |
| `coolant_slope` | ~0°C/min once warm | >2–3°C/min | Persistent positive slope after warm-up phase ends |

**Simulator implementation (`data_simulator.py`):**
`generate_normal_sequence()` models warm-up as `20 + 70 × (1 − exp(−t/30))`, clipped to
[20, 95] °C. `generate_cooling_degradation()` injects a 0.05 °C/s linear rise on all
post-85°C samples, mimicking water pump degradation. Story 6 uses this sequence as the
`cooling_system_stress` ground-truth fault scenario.

---

### 2. `air_intake_maf_anomaly`

> *Proxy condition. The KIT dataset contains no real fault labels — this definition is based
> on expected sensor behaviour from automotive engineering literature, not labelled failures.*

**Component**: MAF sensor / air intake (air filter, vacuum leak)
**Primary signals**: `maf` (Master Table #6), `map` (Master Table #5), `maf_map_cohesion` (Master Table #15)

**Findings:**
- `maf` correlates with `map` at **~0.83 average** (range 0.6–0.9) — fairly consistent
  across trips [R3][R4].
- `maf` correlates with `rpm × tps` load estimate at only **~0.66 average**, and much noisier
  (range 0.12–0.85). MAF is consistently the hardest OBD-II signal to predict: ARIMA
  achieves only MAPE 37.71% on it, and LSTM achieves R² 60.7%, both the worst in their
  respective studies [R4][R3].
- **MAP range (turbocharged vehicle):** The Seat Leon 1.4 TSI is a turbocharged engine.
  Manifold pressure regularly exceeds atmospheric (~101 kPa) under boost. KIT dataset shows
  MAP median 115.8 kPa, P99 225 kPa, range 36–237 kPa [KIT baseline]. The commonly cited
  "20–100 kPa" range applies to naturally aspirated engines only and is **not valid** for
  this vehicle. The correct normal operating range for MAP is 36–237 kPa (full KIT range),
  with a maf/map ratio of 0.1–0.3 indicating healthy air flow.

**Proxy definition**: Flag when `maf_map_cohesion` (normalised MAF-vs-MAP deviation) is
large or sustained — indicates MAF sensor drift, dirty air filter, or vacuum leak [R5].

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `maf` | Tracks MAP closely (~0.83 correlation) [R3] | Lower than MAP-predicted value | Sustained negative residual from MAP-expected baseline |
| `map` | 36–237 kPa, turbocharged; median ~116 kPa [KIT baseline] | Higher than MAF-consistent value | Elevated relative to actual air flow |
| `maf_map_cohesion` | 0.1–0.3 ratio (normal operating) | Deviation outside 0.1–0.3 band | Persistent high or low cohesion value |

**Simulator implementation (`data_simulator.py`) — updated 2026-06-25:**
The original simulator used MAP formula `30 + (rpm − 800) / 100` (peak ~52 kPa at
RPM 3000), which was incorrect for a turbocharged vehicle and caused `maf_map_cohesion`
to compute to ~0.5 — outside the normal band — on all simulated normal driving data,
producing false `air_intake_maf_anomaly` triggers. The formula was corrected to
`100 + (rpm − 800) / 30` clipped to [36, 237] kPa, and MAF updated to `map × 0.2 +
noise` clipped to [0, 123] g/s, keeping the cohesion ratio in the 0.1–0.3 normal band.
`generate_vacuum_leak()` applies `map × 1.3` (elevated MAP) and `tps × 0.7` (reduced
throttle). `generate_intake_blockage()` applies `maf × 0.7` (reduced air flow).

---

### 3. `accelerator_pedal_sensor`

> *Proxy condition. The KIT dataset contains no real fault labels — this definition is based
> on expected sensor behaviour from automotive engineering literature, not labelled failures.*

**Component**: Accelerator pedal position sensors (dual/redundant)
**Primary signals**: `accel_pedal_d` (Master Table #8), `accel_pedal_e` (Master Table #9)

**Findings:**
- Correlation is high (0.96–0.99) and consistent across all 81 trips — mean absolute
  difference ~0.8 percentage points.
- Brief spikes >10pp occur in ~1% of samples across all trips (likely sensor response lag
  during fast pedal movements, not faults).
- Both channels are SAE J1979 PID 0x49 (`accel_pedal_d`) and PID 0x4A (`accel_pedal_e`),
  reporting 0–100% [S1]. They are redundant by design — dual-channel agreement is a
  built-in safety feature of the pedal assembly.

**Proxy definition**: Flag **sustained** divergence between `accel_pedal_d` and
`accel_pedal_e` (>10pp persisting beyond momentary spikes), which indicates dual-sensor
disagreement inconsistent with normal pedal lag [S1][R7].

**Note on this dataset**: Because brief spikes are uniform across every trip, momentary
divergence is not a useful discriminator here. The detection target is sustained divergence
only — a pattern that does not appear in normal driving.

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `accel_pedal_d` | Closely tracks `accel_pedal_e` (correlation 0.96–0.99) | Sustained divergence from E | Difference >10pp lasting more than a few samples |
| `accel_pedal_e` | Closely tracks `accel_pedal_d` | Sustained divergence from D | Difference >10pp lasting more than a few samples |

**Simulator implementation (`data_simulator.py`) — updated 2026-06-25:**
`accel_pedal_d` and `accel_pedal_e` were not present in the original simulator, making
Story 6 `accelerator_pedal_sensor` testing impossible. Both signals are now generated in
`generate_normal_sequence()` from a shared base signal `clip(10 + (rpm − 800) / 100,
14, 85)` plus independent ±1% noise, producing ~0.97 correlation under normal operation
(consistent with KIT data). `generate_pedal_sensor_fault()` injects a sustained 15 pp
drop on pedal E from the quarter-way point, simulating the dual-sensor disagreement
fault target for Story 6.

---

## Master Table Field Reference
All field names align with the Master Table (Data Layer / interface_table v3):
- `coolant_temp` (Master Table #4)
- `coolant_slope` (Master Table #12)
- `maf` (Master Table #6)
- `map` (Master Table #5)
- `tps` (Master Table #7)
- `rpm` (Master Table #2)
- `load_stress` (Master Table #14)
- `maf_map_cohesion` (Master Table #15)

---

## External Standards — Signal Bounds and Operating Ranges

The normal operating ranges used in this project are grounded in two external sources,
independent of the KIT dataset:

### SAE J1979 OBD-II PID standard (measurement bounds)

Source: Wikipedia, "OBD-II PIDs" — https://en.wikipedia.org/wiki/OBD-II_PIDs
(Standard: SAE J1979 — defines mandatory OBD-II PIDs for all petrol/diesel vehicles)

These are the physical measurement bounds the sensor hardware can report.
Our normal operating ranges are a subset of these bounds.

| PID | Signal | Unit | SAE J1979 Min | SAE J1979 Max | Formula |
|-----|--------|------|---------------|---------------|---------|
| 0x05 | `coolant_temp` | °C | -40 | 215 | A − 40 |
| 0x0B | `map` | kPa | 0 | 255 | A |
| 0x0C | `rpm` | RPM | 0 | 16,383 | (256A+B)/4 |
| 0x0D | `speed` | km/h | 0 | 255 | A |
| 0x10 | `maf` | g/s | 0 | 655 | (256A+B)/100 |
| 0x11 | `tps` | % | 0 | 100 | (100/255)×A |
| 0x49 | `accel_pedal_d` | % | 0 | 100 | (100/255)×A |
| 0x4A | `accel_pedal_e` | % | 0 | 100 | (100/255)×A |

### Seat Leon MK3 owner's manual (normal operating zone and engine temperature range)

Sources:
- Seat Leon owner's manual coolant gauge — https://www.seatia.com/secon-482.html
- Seat Leon 2017 Owner's Manual (`Seat-Leon_2017_EN__3f5b99c0a7.pdf`) — engine oil
  temperature display section
- Seat Leon MK3 Workshop Maintenance Manual (`seat-leon-3-maintenance-eng.pdf`,
  EIGG000421, Edition 07.2018) — Sections 1.1, 4.29, 4.30

**Coolant temperature gauge — three zones (owner's manual):**
- **Zone A (cold):** Avoid high engine speeds and heavy loads.
- **Zone B (normal):** Needle in middle section of scale during normal driving. Temperature
  may rise under heavy load or high outside temperature; this is normal provided no warning
  lamp lights.
- **Zone C (warning):** Warning lamp illuminates. Stop the engine immediately and check
  coolant level. Do not continue driving. Exact °C threshold for Zone C not stated in
  owner's manual — qualitative zones only.

**Engine operating temperature — confirmed range (owner's manual, oil temperature display):**
> "The engine reaches its operating temperature when in normal driving conditions, the oil
> temperature is between **80°C and 120°C**. If the engine is required to work hard and the
> outside temperature is high, the engine oil temperature can increase. This does not
> present any problem as long as the warning lamps do not appear."

Coolant and oil temperature are thermally coupled. The 80–120°C engine operating envelope
from the manufacturer directly supports and bounds the 90–105°C normal coolant range
observed in the KIT dataset.

**Cooling system design (maintenance manual, Section 4.30):**
- Cooling system operates under pressure — raises the boiling point above 100°C, which
  is why normal coolant temperature can reach 100–105°C without boiling.
- Coolant additive further raises the boiling point (G12++/G13 specification).

**RPM operating range (maintenance manual, Section 1.1 — 1.4 TSI engines):**
- Peak power delivered between **4500–6000 RPM** depending on engine code (CZEA,
  CZCA, CHPA, CZDA variants).
- Torque band: **1400–4000 RPM** (lower variants) / **1500–3500 RPM** (higher variants).
- Normal driving RPM range: ~700 RPM idle to ~6000 RPM at full power.

This directly supports our proxy definition for `cooling_system_stress`: predictive
detection aims to flag the transition from Zone B toward Zone C — sustained elevated
coolant temp and rising slope — before the warning lamp triggers. The manufacturer
confirms the engine is designed to operate in the 80–120°C thermal range; readings
persistently above 105°C with a positive slope after warm-up are the anomaly target.

---

## Data Health Validation Summary

Source: KIT Automotive OBD-II Dataset (Seat Leon MK3)
Validation by: Ray — Story 1 baseline analysis (`ttm-related/src/model/clean_obd2_normal_frei.py`,
`ttm-related/src/model/analyze_obd2_normal_frei.py`)

The dataset contains ten OBD-II signals collected from operating vehicles: engine RPM,
vehicle speed, coolant temperature, intake manifold absolute pressure (MAP), mass air flow
(MAF), throttle position, ambient temperature, intake air temperature, and two accelerator
pedal position signals (D and E). The dataset description does not provide explicit
diagnostic labels, fault-event annotations, DTC records, or MIL status. Therefore, this
validation does not attempt to prove that every vehicle record is mechanically healthy.
Instead, the aim is to confirm that the selected subset is stable and physically plausible
enough to serve as a healthy baseline for proxy threshold calibration.

### Dataset selection

Only files labelled `Normal` and `Frei` were retained, representing regular and free-flow
driving. Traffic jam files, measurement-error files (`Messfehler`), and invalid filenames
were excluded. The remaining 66 trips are treated as the healthy baseline for all proxy
threshold definitions.

| Item | Result |
|---|---:|
| Raw files inspected | 81 |
| Baseline files retained (`Normal` + `Frei`) | 66 |
| Rows after duplicate checking | 2,089,290 |
| Rows removed because all core signals were missing | 0 |
| Resampled analysis frequency | 1 second |

### Missing-value profile (after cleaning)

The missing-value profile is low for all primary model signals. `intake_air_temp` has the
highest rate because physically invalid values were set to missing during range filtering;
this signal is not used in the model layer and does not affect the anomaly detection pipeline.

| Signal | Missing after cleaning |
|---|---:|
| `rpm` | 0.0067% |
| `speed` | 0.0093% |
| `coolant_temp` | 0.0003% |
| `map` | 0.0035% |
| `maf` | 0.0157% |
| `tps` | 0.0188% |
| `intake_air_temp` | 1.1661% |
| `ambient_temp` | 0.0220% |
| `accel_pedal_d` | 0.0256% |
| `accel_pedal_e` | 0.0282% |

### Descriptive statistics (signal plausibility)

The major operating signals remain within physically reasonable ranges for normal vehicle
operation, supporting the plausibility of the cleaned subset.

| Signal | Median | P99 | Min–Max | Interpretation |
|---|---|---|---|---|
| `rpm` | 1,560 RPM | 2,664 RPM | 0–3,682 RPM | Plausible for stops, cruising, and normal acceleration |
| `speed` | 66 km/h | 157 km/h | 0–218 km/h | Plausible for mixed road driving |
| `coolant_temp` | 90°C | 94°C | −1–103°C | Stable warmed-up engine range |
| `map` | 115.8 kPa | 225 kPa | 36–236.9 kPa | Plausible intake pressure for turbocharged engine |
| `maf` | 19.3 g/s | 83.0 g/s | 0–122.7 g/s | Plausible airflow range under changing load |
| `tps` | 83.5% | 89% | 13.7–89% | Within valid percentage bounds |
| `accel_pedal_d/e` | 14.1/14.5% | 63.9/64.1% | 14.1–85.1% / 14.1–84.3% | Two pedal channels remain consistent |

### Correlation summary (Spearman, across all 66 healthy trips)

Key relationships confirmed consistent with normal engine behaviour:

| Pair | Spearman correlation | Interpretation |
|---|---|---|
| `rpm` vs `maf` | strong positive | Higher RPM draws more air — expected |
| `map` vs `maf` | strong positive | Higher manifold pressure → higher air flow |
| `tps` vs `maf` | moderate positive | Throttle opening drives air flow |
| `rpm` vs `speed` | moderate positive | Speed broadly tracks engine demand |
| `accel_pedal_d` vs `accel_pedal_e` | very strong positive (~0.96–0.99) | Dual-channel consistency confirmed |

The MAF–MAP strong positive correlation (~0.83 average) directly grounds the
`air_intake_maf_anomaly` proxy definition — a large or sustained deviation from this
relationship is the detection target.

The near-perfect `accel_pedal_d` / `accel_pedal_e` correlation grounds the
`accelerator_pedal_sensor` proxy definition — sustained divergence above 10 pp is the
detection target.

Throttle position shows weak negative correlations with pedal position and MAF and should
be interpreted cautiously. This likely reflects absolute throttle position calibration or
ECU control behaviour rather than a dataset issue, and is consistent with the known
difficulty of using TPS as a standalone anomaly signal [R4].

![Spearman correlation heatmap](image/obd2_spearman_correlation_heatmap.png)

### Coolant temperature warm-up profile

The coolant-temperature plots provide the clearest single-signal health evidence. Median
coolant temperature rises from a low initial value to approximately 90°C within ~14 minutes,
then stabilises in the 90–95°C band — consistent with normal engine thermal behaviour and
the Seat Leon owner's manual Zone B [M1].

- **Normal warm-up rate:** ~10–16°C/min during cold start, falling to ~0°C/min once warm.
- **Normal steady-state:** 90–95°C (consistent with Seat Leon MK3 owner's manual Zone B).
- **Proxy anomaly boundary:** Sustained `coolant_temp` above ~100°C and/or `coolant_slope`
  persistently above 2–3°C/min after warm-up (i.e., outside the stabilised band).

> **Note:** The warm-up summary pools all 66 trips regardless of starting temperature.
> Trips where the engine was already warm pull up the minute-0 median and compress the
> apparent warm-up curve. The "~14 minutes to 90°C" figure is a blended average across all
> starting conditions, not a pure cold-start warm-up time.

Plots generated by `analyze_obd2_normal_frei.py`:

![Coolant temperature warm-up profile](image/obd2_coolant_temp_warmup_0_30min.png)

![Coolant temperature stable period](image/obd2_coolant_temp_stable_15_60min.png)

### Overall validation conclusion

The `Normal` + `Frei` subset shows low missingness, physically plausible signal ranges,
normal coolant warm-up and stabilisation behaviour, and strong expected relationships among
RPM, speed, MAP, MAF, and accelerator pedal signals. These results support using this
cleaned subset as a stable baseline dataset for subsequent time-series modelling and proxy
threshold calibration. The dataset does not contain diagnostic labels and therefore cannot
prove complete mechanical health — all failure conditions defined in this document remain
proxy definitions, not verified faults.

---

## Healthy Baseline Reference Table

Source: KIT Automotive OBD-II Dataset (Seat Leon MK3, Normal/Frei trips, Messfehler excluded)
Computed by: Ray — Story 1 baseline analysis
Industry ranges: Seat Leon MK3 owner's manual + SAE J1979 standard (see External Standards above)

Computed from the 1-second resampled cleaned CSV (`obd2_normal_frei_cleaned_1s.csv`, 66
Normal/Frei trips). Derived features (`coolant_slope`, `maf_map_cohesion`, `load_stress`,
`rpm_variation`) are not directly present in the raw CSV; their reference ranges come from
automotive engineering literature and cross-signal reasoning (see External Standards above).

| Signal | Unit | SAE J1979 bound | Industry / Seat Leon normal range | KIT Mean | KIT Std | KIT P5 | KIT P95 | KIT Median | KIT P99 | KIT Min | KIT Max |
|--------|------|-----------------|----------------------------------|----------|---------|--------|---------|------------|---------|---------|---------|
| `coolant_temp` | °C | -40 to 215 | 85–105 (gauge Zone B) | 81.19 | 18.35 | 37.00 | 92.00 | 90.00 | 94.00 | −1.00 | 103.00 |
| `rpm` | RPM | 0 to 16,383 | 600–6500 | 1,520 | 517 | 770 | 2,190 | 1,560 | 2,664 | 0 | 3,682 |
| `speed` | km/h | 0 to 255 | 0–130 | 64.75 | 45.50 | 0.00 | 128.73 | 66.00 | 157.00 | 0 | 218 |
| `map` | kPa | 0 to 255 | 20–100 | 126.65 | 31.20 | 98.00 | 196.18 | 115.82 | 225.00 | 36.00 | 236.90 |
| `maf` | g/s | 0 to 655 | 2–25 | 23.34 | 16.06 | 7.03 | 54.61 | 19.31 | 83.03 | 0.00 | 122.72 |
| `tps` | % | 0 to 100 | 0–80 | 81.24 | 10.68 | 69.18 | 83.50 | 83.50 | 89.00 | 13.70 | 89.00 |
| `accel_pedal_d` | % | 0 to 100 | 0–100 | 21.60 | 12.44 | 14.10 | 47.68 | 14.10 | 63.88 | 14.10 | 85.10 |
| `accel_pedal_e` | % | 0 to 100 | 0–100 | 21.92 | 12.47 | 14.50 | 48.35 | 14.50 | 64.10 | 14.10 | 84.30 |
| `coolant_slope` | °C/min | — | 0–2 (steady state) | *derived* | *derived* | — | — | — | — | — | — |
| `maf_map_cohesion` | ratio | — | 0.1–0.3 | *derived* | *derived* | — | — | — | — | — | — |
| `load_stress` | rpm×% | — | 0–200,000 | *derived* | *derived* | — | — | — | — | — | — |
| `rpm_variation` | RPM | — | 0–500 | *derived* | *derived* | — | — | — | — | — | — |

**Notes on KIT observations vs. reference ranges:**

- `map` median (115.8 kPa) exceeds the nominal `REFERENCE_RANGES` upper bound of 100 kPa.
  The KIT dataset includes manifold pressures above atmospheric (turbocharged Seat Leon 1.4 TSI),
  which can exceed 100 kPa under boost. The `REFERENCE_RANGES` value should be reviewed and
  widened if needed to avoid false positives on normal boosted driving.
- `speed` P99 (157 km/h) and Max (218 km/h) exceed the current `REFERENCE_RANGES` cap of
  120 km/h. These represent highway driving present in `Frei` trips and are not anomalous.
  The cap can be raised to ~160 km/h without affecting anomaly detection fidelity.
- `tps` median (83.5%) sits near the `REFERENCE_RANGES` upper bound of 80%. Absolute throttle
  position in this dataset appears to use a different zero/scale calibration than expected.
  Throttle position should be interpreted cautiously and correlated with MAF rather than used
  as a standalone threshold signal.
- `coolant_temp` Max of 103°C falls within the pressurised coolant system's normal operating
  ceiling (see External Standards — Seat Leon MK3 Workshop Manual, Section 4.30). The proxy
  anomaly threshold of ~100°C with sustained positive slope remains valid.

---

## References

### Manuals

**[M1]** SEAT, *León Owner's Manual*, 2017.
File: `documetation/相关论文/manual/Seat-Leon_2017_EN__3f5b99c0a7.pdf`
Cited for: coolant temperature gauge zones (A/B/C), engine oil operating temperature
range (80–120°C).

**[M2]** SEAT, *León / León ST Workshop Maintenance Manual*, Edition 07.2018,
Reference EIGG000421. File: `documetation/相关论文/manual/seat-leon-3-maintenance-eng.pdf`
Cited for: 1.4 TSI engine codes and RPM ranges (§1.1); cooling system pressure and
boiling point rationale (§4.30); coolant additive specification G12++/G13 (§4.30).

### Standards

**[S1]** SAE International, *SAE J1979: E/E Diagnostic Test Modes* (OBD-II PID standard).
Reference via: "OBD-II PIDs," Wikipedia, https://en.wikipedia.org/wiki/OBD-II_PIDs.
Cited for: signal physical measurement bounds (PID 0x05 coolant_temp, 0x0B MAP, 0x0C RPM,
0x0D speed, 0x10 MAF, 0x11 TPS, 0x49 accel_pedal_d, 0x4A accel_pedal_e); MAF upper
bound corrected to 655 g/s from SAE maximum.

### Academic Papers

**[R1]** V. Ekambaram et al., "Tiny Time Mixers (TTMs): Fast Pre-trained Models for
Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series," IBM Research, *NeurIPS
2024*. File: `documetation/相关论文/ttm.pdf`
Cited for: TTM zero-shot forecasting methodology; prediction residual as anomaly score;
multivariate OBD-II channel modelling; exogenous variable (driver-controlled signals)
treatment.

**[R2]** Z. Darban et al., "Deep Learning for Time Series Anomaly Detection: A
Comprehensive Survey," *ACM Computing Surveys*, Vol. 57, No. 1, Article 15, Oct 2024.
File: `documetation/相关论文/Deep Learning for Time Series Anomaly Detection.pdf`
Cited for: prediction-based anomaly detection taxonomy; trend anomaly definition
(persistent slope shift); F1/AU-PR evaluation metrics for imbalanced fault data; NDT/POT
thresholding methods.

**[R3]** A. Errezgouny et al., "An Integrated Deep Learning Approach for Predictive
Vehicle Maintenance," *Decision Analytics Journal*, 16, 2025, 100597.
File: `documetation/相关论文/an_intergrated_deep_learning_approac_predictive_vehicle_maintence.pdf`
Cited for: MAF R² 60.7% (hardest OBD-II signal to predict); MAF–TPS correlation 92%;
feature selection confirming RPM, Engine Load, MAF, TPS as core OBD-II signals; LSTM
baseline R² ~89–90% as comparison target.

**[R4]** (Author not stated in summary), "Data Modeling and Prediction of OBD-II Time
Series." File: `documetation/相关论文/Data_modeling_and_prediction.pdf`
Cited for: ARIMA MAPE results — MAF 37.71% (worst), MAP 22.89%, RPM 13.81%;
MAF–TPS correlation 92.3%; driver-controlled vs engine-response signal predictability
distinction.

**[R5]** (Multiple authors), "A Review of OBD-II-Based Machine Learning Applications for
Sustainable, Efficient, Secure, and Safe Vehicle Driving," *Sensors*, 2025.
File: `documetation/相关论文/A Review of OBD-II-Based Machine Learning Applications for Sustainable, Efficient, Secure, and Safe Vehicle Driving.pdf`
Cited for: key OBD-II features for health monitoring (coolant temp, RPM, engine load,
MAF); vehicle health monitoring section (§4.4); evaluation metric conventions.

**[R6]** (Author not stated in summary), "Detecting Anomalies in the Engine Coolant
Sensor Using One-Class Classifiers."
File: `documetation/相关论文/Detecting_Anomalies_in_the_Engine_Coolant_Sensor_Using_One-Class_Classifiers.pdf`
Cited for: coolant sensor anomaly detection using engineered time-series features;
direct precedent for the `cooling_system_stress` proxy condition.

**[R7]** (Author not stated in summary), "Advancing Vehicle Diagnostics: Exploring the
Application of Large Language Models in the Automotive Industry."
File: `documetation/相关论文/Advancing Vehicle Diagnostic Exploring the Application of Large Language Models in the Automotive Industry.pdf`
Cited for: LLM role as explainability layer (not core detector); capability limits of
LLMs in complex real-world fault classification.

**[R8]** Hermawan et al., "OBD-II Driving Behavior Survey," 2020.
File: `documetation/相关论文/Hermawan_2020_OBDII_driving_behavior_survey.pdf`
Cited for: OBD-II system definition and monitored component scope; sensor data role in
vehicle and driver state characterisation.

**[R9]** Z. Darban et al., "Unsupervised Anomaly Detection in Time-Series: An Extensive
Evaluation and Analysis of State-of-the-Art Methods," 2024.
File: `documetation/相关论文/Unsupervised anomaly detection in time-series- An extensive evaluation and analysis of state-of-the-art methods.pdf`
Cited for: unsupervised anomaly detection method benchmarks; evaluation on unlabelled
time-series data consistent with KIT dataset constraints.
