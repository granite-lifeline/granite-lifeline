# Proxy Failure Stage 4 Validation Report

## Overview

This report documents the Stage 4 fault injection validation for the 5 proxy failure definitions.
It supplements the Stage 4 sections in `proxy_support.md` with the actual implementation results.

The proxy_support.md describes a 4-step Stage 4 protocol per proxy:

- TBD-1: Injection design
- TBD-2: Detectability curve (detection rate vs. graded severity)
- TBD-3: False-positive rate on held-out healthy trips
- TBD-4: Acceptance criteria and threshold revision cycle

The current fault injection framework implements TBD-1 fully (11 injection cases across 5 proxies)
and establishes the infrastructure for TBD-2 through TBD-4. The remaining steps are marked as open work.

## Validation Framework

### Implementation

| Component | Location |
|---|---|
| Case definitions | `data_layer/fault_injection/configs/fault_injection_cases.v1.json` |
| Injection engine | `data_layer/fault_injection/src/run_fault_injection.py` |
| Latest results | `data_layer/fault_injection/outputs/fault_injection_summary_20260724T184919Z.json` |
| Experimental design | `data_layer/fault_injection/experimental_design.md` |

### How Injection Works

1. Load a completed healthy pipeline run (production_features.csv + proxy stages)
2. Select a temporal window matching the target sub-check eligibility (via selector filters)
3. Copy the production_features.csv to a new run directory
4. Modify the target signal in the copied CSV (e.g., set coolant_temp to 106 C)
5. Recompute all dependent features (speed-density residual, pedal-mapping residual, stability metrics)
6. Rerun proxy stages 50, 60, 61, 70
7. Read the proxy_decisions.csv and compare against the expected result

### Framework Status

The run_fault_injection.py framework is a complete, repeatable tool. It supports 6 injection strategies (set_constant, multiply, add_offset, freeze_to_first, linear_ramp, force_pedal_delta, suppress_map_step_response) and 10 selectors for finding injection windows in the healthy data.

## Results by Proxy

### 1. cooling_degradation

#### 1-S2 — Overheating (P0217)

| Field | Value |
|---|---|
| Target signal | coolant_temp |
| Injection | Set to 106 C for 200 s (post-warmup) |
| Expected | triggered |
| Actual | triggered (margin=20s) |
| DTC emitted | P0217 |
| **Result** | **PASS** |

#### 1-S3 — Rising without plateau (pending precursor)

| Field | Value |
|---|---|
| Target signal | coolant_temp |
| Injection | Linear ramp from 100 C at 0.8 C/min for 220 s (post-warmup) |
| Expected | pending |
| Actual | pending (margin=40s) |
| DTC emitted | false |
| **Result** | **PASS** |

### 2. air_intake_maf_anomaly

#### 2-S2 — High-load under-read (P0101)

| Field | Value |
|---|---|
| Target signal | maf |
| Injection | Multiply by 0.35 for 15 s (post-warmup, high-load) |
| Expected | triggered |
| Actual | triggered (margin=2s) |
| DTC emitted | P0101 |
| **Result** | **PASS** |

#### 2-S3b — Zero MAF while firing (P0102)

| Field | Value |
|---|---|
| Target signal | maf |
| Injection | Set to 0.0 for 12 s (engine firing, rpm >= 500) |
| Expected | triggered |
| Actual | triggered (margin=2s) |
| DTC emitted | P0102 |
| **Result** | **PASS** |

### 3. accelerator_pedal_sensor

#### 3-S1a — Channel-relation residual (P2138)

| Field | Value |
|---|---|
| Target signal | accel_pedal_e |
| Injection | Add 5% offset for 35 s (low-motion mask) |
| Expected | triggered |
| Actual | triggered (margin=2s) |
| DTC emitted | P2138 |
| **Result** | **PASS** |

#### 3-S1b — Extreme disagreement (P2138, high tier)

| Field | Value |
|---|---|
| Target signal | accel_pedal_e |
| Injection | Force D/E delta to 70% for 3 s (engine firing) |
| Expected | triggered |
| Actual | triggered (margin=1s) |
| DTC emitted | P2138 |
| **Result** | **PASS** |

### 4. intake_air_temperature_sensor_fault

#### 4-S1 — Stuck/no-response IAT (P0111)

| Field | Value |
|---|---|
| Target signal | intake_temp |
| Injection | Freeze to first value for 250 s (context-change window) |
| Expected | triggered |
| Actual | triggered (margin=73s) |
| DTC emitted | P0111 |
| **Result** | **PASS** |

Note: Extended to 250 s because intake_temp_stability is a 60-sample rolling std. At 1 Hz, the stability metric takes 60 s to reach the 0.1 C threshold after the freeze begins, leaving 190 s of measurable flatness against the 120 s requirement.

#### 4-S3 — Physical range low (P0112)

| Field | Value |
|---|---|
| Target signal | intake_temp |
| Injection | Set to -41 C for 1 s (engine firing) |
| Expected | triggered |
| Actual | triggered (margin=1s) |
| DTC emitted | P0112 |
| **Result** | **PASS** |

### 5. map_load_signal_plausibility_fault

#### 5-S1 — Step response (P0106)

| Field | Value |
|---|---|
| Target signal | map |
| Injection | Suppress MAP response across 4 pedal-step events |
| Expected | triggered |
| Actual | triggered (margin=0s) |
| DTC emitted | P0106 |
| **Result** | **PASS** |

#### 5-S2 — Steady-state residual (arbitration evidence)

| Field | Value |
|---|---|
| Target signal | maf |
| Injection | Multiply by 3.0 for 45 s (steady driving, pedal signals frozen to ensure guard mask) |
| Expected | triggered |
| Actual | triggered (margin=12s) |
| DTC emitted | false (arbitration evidence) |
| **Result** | **PASS** |

Note: The injection modifies MAF (not MAP). Because the speed-density residual = maf - expected_maf (from MAP/RPM/IAT), multiplying MAF by 3.0 creates a large positive residual that exceeds the +16.71 g/s band threshold. The auxiliary pedal signals are frozen to maintain the pedal_slope == 0 guard condition required by the 5-S2 steady mask.

#### 5-S3 — Stuck MAP (P0106)

| Field | Value |
|---|---|
| Target signal | map |
| Injection | Freeze to first value for 250 s (context-change window) |
| Expected | triggered |
| Actual | triggered (margin=71s) |
| DTC emitted | P0106 |
| **Result** | **PASS** |

Note: Same rolling-window consideration as 4-S1. map_range_60s requires 60 s to reach zero after the freeze starts.

## Summary

| Case | Injection | Expected | Actual | Margin | Result |
|---|---|---|---|---|---|
| 1-S2 coolant overheat | set_constant 106 C, 200 s | triggered | triggered | 20 s | PASS |
| 1-S3 rising precursor | linear_ramp 0.8 C/min, 220 s | pending | pending | 40 s | PASS |
| 2-S2 MAF under-read | multiply 0.35, 15 s | triggered | triggered | 2 s | PASS |
| 2-S3b MAF zero | set_constant 0.0, 12 s | triggered | triggered | 2 s | PASS |
| 3-S1a pedal offset | add_offset 5%, 35 s | triggered | triggered | 2 s | PASS |
| 3-S1b extreme delta | force_delta 70%, 3 s | triggered | triggered | 1 s | PASS |
| 4-S1 IAT frozen | freeze_to_first, 250 s | triggered | triggered | 73 s | PASS |
| 4-S3 IAT range low | set_constant -41 C | triggered | triggered | 1 s | PASS |
| 5-S1 MAP suppressed | suppress, 4 events | triggered | triggered | 0 s | PASS |
| 5-S2 steady residual | maf multiply 3.0, 45 s | triggered | triggered | 12 s | PASS |
| 5-S3 MAP frozen | freeze_to_first, 250 s | triggered | triggered | 71 s | PASS |

**Overall: 11/11 PASS**

All 11 synthetic fault injection cases produced the expected result_state. The proxy decision engine correctly detects injected faults across all 5 proxy types and all executed sub-checks.

## Deviations from the Stage 4 Protocol

The proxy_support.md describes a 4-step Stage 4 protocol. The current implementation status:

| Protocol step | Status | Details |
|---|---|---|
| TBD-1: Injection design | **Complete** | 11 cases covering all executable sub-checks with physical injection strategies |
| TBD-2: Detectability curve | **Not done** | Only single-severity injection per sub-check. A graded severity sweep (e.g., 1-S2 at 102 C, 105 C, 108 C, 110 C) would produce a detection-rate curve with decision_margin as the x-axis companion |
| TBD-3: False-positive rate | **Not done** | No held-out healthy trips were tested under the frozen rules. The LOTO machinery from script 91 could be reused for this |
| TBD-4: Acceptance criteria | **Partial** | PASS/FAIL per case is implemented, but no formal acceptance criteria or threshold revision cycle has been applied. Per protocol, Stage 3 thresholds may be revised once after Stage 4 results |

## Future Work

1. Graded severity injection to produce detectability curves (TBD-2)
2. False-positive rate measurement on held-out trips (TBD-3)
3. One revision cycle for Stage 3 thresholds based on TBD-2/3 results (TBD-4)
4. Cold-start support checks (1-S4, 4-S2) — require strict 6-hour segment gaps and observed starts; window availability is limited