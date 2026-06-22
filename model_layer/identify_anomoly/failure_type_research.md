# Failure-Type Research (Model Layer — Anomaly Detection Epic)

Dataset: KIT Automotive OBD-II Dataset (81 trips, single Seat Leon, various driving conditions)

## The core problem
The dataset has **no real failure labels** — it's all healthy-vehicle driving data. The
dataset documentation (RADAR DOI: 10.35097/1130) describes road conditions via filename
suffixes (Normal, Frei, Stau, Messfehler) but does not explicitly state that the vehicle
was fault-free. We therefore treat this as a proxy healthy baseline, justified by:
1. No DTC/MIL fault codes are present in the logged signals.
2. Core sensor statistics (see Healthy Baseline Reference Table below) fall within
   Seat Leon manufacturer-normal ranges and automotive industry standards.
3. Cross-signal correlations (e.g. MAF–MAP ~0.83) are consistent with normal engine behaviour.

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
  reach **100–103°C**.
- Warm-up rate is **10–16°C/min** during cold start, dropping to ~0°C/min once warm.

**Proxy definition**: After the initial warm-up phase (coolant temp has exceeded ~85°C at
least once), flag elevated risk if:
- `coolant_temp` exceeds **~100°C**, and/or
- `coolant_slope` remains **>2–3°C/min** instead of plateauing

This directly matches the brief's worked example: *"Coolant temperature rising faster than
normal — possible water pump degradation."*

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `coolant_temp` | 85–105°C steady state | Rising above 100°C | Sustained increase post warm-up, not returning to baseline |
| `coolant_slope` | ~0°C/min once warm | >2–3°C/min | Persistent positive slope after warm-up phase ends |

---

### 2. `air_intake_maf_anomaly`

> *Proxy condition. The KIT dataset contains no real fault labels — this definition is based
> on expected sensor behaviour from automotive engineering literature, not labelled failures.*

**Component**: MAF sensor / air intake (air filter, vacuum leak)
**Primary signals**: `maf` (Master Table #6), `map` (Master Table #5), `maf_map_cohesion` (Master Table #15)

**Findings:**
- `maf` correlates with `map` at **~0.83 average** (range 0.6–0.9) — fairly consistent across trips.
- `maf` correlates with `rpm × tps` load estimate at only **~0.66 average**, and much noisier
  (range 0.12–0.85).

**Proxy definition**: Flag when `maf_map_cohesion` (normalised MAF-vs-MAP deviation) is
large or sustained — indicates MAF sensor drift, dirty air filter, or vacuum leak.

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `maf` | Tracks MAP closely (~0.83 correlation) | Lower than MAP-predicted value | Sustained negative residual from MAP-expected baseline |
| `map` | 20–100 kPa, tracks engine load | Higher than MAF-consistent value | Elevated relative to actual air flow |
| `maf_map_cohesion` | 0.1–0.3 ratio (normal operating) | Deviation outside 0.1–0.3 band | Persistent high or low cohesion value |

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

**Proxy definition**: Flag **sustained** divergence between `accel_pedal_d` and
`accel_pedal_e` (>10pp persisting beyond momentary spikes), which indicates dual-sensor
disagreement inconsistent with normal pedal lag.

**Note on this dataset**: Because brief spikes are uniform across every trip, momentary
divergence is not a useful discriminator here. The detection target is sustained divergence
only — a pattern that does not appear in normal driving.

**Signal deviation patterns:**

| Signal | Normal behaviour | Anomaly direction | Pattern |
|--------|-----------------|-------------------|---------|
| `accel_pedal_d` | Closely tracks `accel_pedal_e` (correlation 0.96–0.99) | Sustained divergence from E | Difference >10pp lasting more than a few samples |
| `accel_pedal_e` | Closely tracks `accel_pedal_d` | Sustained divergence from D | Difference >10pp lasting more than a few samples |

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

### Dataset selection

| Item | Result |
|---|---:|
| Raw files inspected | 81 |
| Baseline files retained (`Normal` + `Frei`) | 66 |
| Rows after duplicate checking | 2,089,290 |
| Rows removed because all core signals were missing | 0 |
| Resampled analysis frequency | 1 second |

`Messfehler` (measurement-error) files and traffic-jam files were excluded. The remaining 66
Normal/Frei trips are treated as the healthy baseline for all proxy threshold definitions.

### Missing-value profile (after cleaning)

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

All primary model signals have missing rates below 0.02%. `intake_air_temp` has the highest
rate (1.17%) because physically invalid values were set to missing during range filtering;
this signal is not used in the model layer and does not affect the anomaly detection pipeline.

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

### Coolant temperature warm-up profile

Across Normal/Frei trips, median coolant temperature rises from a low starting value to
approximately 90°C within ~14 minutes, then stabilises in the 90–95°C band for the remainder
of the trip. This confirms:

- **Normal warm-up rate:** ~10–16°C/min during cold start, falling to ~0°C/min once warm.
- **Normal steady-state:** 90–95°C (consistent with Seat Leon MK3 owner's manual Zone B).
- **Proxy anomaly boundary:** Sustained coolant_temp above ~100°C and/or coolant_slope
  persistently above 2–3°C/min after warm-up (i.e., outside the stabilised band).

Plots generated by `analyze_obd2_normal_frei.py`:

![Coolant temperature warm-up profile](../../ttm-related/outputs/obd2_coolant_temp_warmup_0_30min.png)

![Coolant temperature stable period](../../ttm-related/outputs/obd2_coolant_temp_stable_15_60min.png)

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
