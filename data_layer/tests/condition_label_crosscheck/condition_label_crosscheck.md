# Condition Label Cross-Check: Filename Traffic Labels vs. Derived `child_state`

**Type:** research/validation note, not a production contract.
**Run used:** `2026-07-19-data-layer-v1`
**Script:** `crosscheck_condition_labels.py` (this directory)
**Outputs:** `trip_condition_labels.csv` (per-trip), `condition_label_crosscheck_summary.json` (grouped summary)

## 1. Motivation

Every raw KIT source file name encodes a human-assigned, trip-level traffic label — `Normal`, `Frei` ("free-flowing"), or `Stau` ("congested") — describing the driver's overall impression of that trip's traffic conditions. This label is never read into the cleaning or feature pipeline: it is filename metadata, not a decodable OBD-II signal, and the Data Layer's own operating-condition taxonomy (`thermal_state` × `child_state`, with `child_state` ∈ `{idle, steady_driving, acceleration, deceleration, high_load, ...}`) is derived entirely and independently from RPM, speed, and pedal telemetry at 1 Hz, per sample.

Because both describe "how the vehicle was being driven," it is worth asking whether the filename label is simply going unused, or whether it can serve as an independent, low-cost sanity check on the operating-condition classifier: if trips labelled `Stau` do not look meaningfully different from trips labelled `Frei` in their derived `child_state` mix, that would be worth investigating; if they do differ in a physically sensible way, that corroborates the classifier and gives the Dataset Selection section (Section 2.4 of the report) a concrete, data-backed detail to cite rather than an assertion.

This check does not feed the production pipeline, does not gate any script, and is not required for scripts 00–41 or the planned 50–70 proxy engine. It exists solely to support the report's methodology discussion.

## 2. Method

1. **Recover each raw file's start timestamp in UTC.** 
   Every raw CSV's `Time` column is a local time-of-day only (no date, no timezone). For each of the 81 raw files, the script reads the first data row's time, combines it with the date encoded in the filename, applies the source timezone (`Europe/Berlin`, correctly handling the CEST/CET boundary), and converts to UTC.

2. **Match each raw file to its assigned `trip_id`.** 
   The script reads `operating_conditions/operating_condition_enriched.csv` for the run above, takes the earliest timestamp recorded under each `trip_id`, and matches each raw file's computed start time to the nearest trip start (within a 120-second tolerance, generously wide compared to the sub-second agreement actually observed). This sidesteps re-deriving the pipeline's internal trip-ordering rule (Section 2.2 of `feature_schema.md`) — it matches on absolute time instead, which is authoritative by construction. All 81 raw files matched a unique `trip_id`; none were left unmatched or ambiguous.

3. **Extract the condition label.** 
   The filename remainder after the date is split on `_`, and the first token found among `Normal`, `Frei`, `Stau` is taken as that trip's label.

4. **Compute the per-trip `child_state` distribution.** 
   For each `trip_id`, the script computes the fraction of 1 Hz samples in each `child_state` category using `operating_condition_enriched.csv` directly — the same field the production pipeline delivers in `production_features.csv` via `operating_state`.

5. **Aggregate by condition label.** 
   Per-trip `child_state` shares are averaged within each of the three condition-label groups.

Re-running: `python -m data_layer.tests.condition_label_crosscheck.crosscheck_condition_labels --run-dir data/processed/runs/2026-07-19-data-layer-v1`

## 3. Results

81 trips: 56 `Normal`, 14 `Frei`, 11 `Stau`.

| condition_label | n_trips | acceleration | deceleration | high_load | idle | inactive_engine_off | steady_driving |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frei   | 14 | 0.180 | 0.268 | 0.085 | 0.109 | 0.023 | 0.335 |
| Normal | 56 | 0.173 | 0.259 | 0.096 | 0.077 | 0.034 | 0.362 |
| Stau   | 11 | 0.204 | 0.282 | 0.083 | 0.061 | 0.070 | 0.299 |

(Figures are mean per-trip `child_state` share within each group; `unknown` omitted, ≤0.0001 in all groups.)

## 4. Analysis and Conclusion

The naive prediction — that `Stau` trips should show the highest `idle` share — is **not** what the data shows: `idle` is actually lowest for `Stau` (0.061) and highest for `Frei` (0.109), with `Normal` in between (0.077). Read on its own, this looks like a mismatch between the filename label and the derived state.

Two other columns resolve this. `inactive_engine_off` is monotonic with the congestion ordering (`Frei` 0.023 < `Normal` 0.034 < `Stau` 0.070), and the combined "actively changing speed" share (`acceleration` + `deceleration`) is also highest for `Stau` (0.486) and lowest for `Normal` (0.432), with `Frei` in between (0.448). Taken together, this is a physically coherent picture of stop-and-go driving: a driver genuinely stuck in traffic is more likely to switch the engine off while queued — recorded as `inactive_engine_off`, a category distinct from `idle` (engine running, vehicle stationary) — and to cycle through short acceleration/deceleration bursts while creeping forward, rather than sustain a long `idle` state. `idle` in the strict engine-on, stationary sense is, if anything, more characteristic of `Frei` trips pausing briefly at lights or junctions on an otherwise free-flowing route.

## 5. Conclusion

The coarse, human-assigned filename label and the fine-grained, telemetry-derived `child_state` classification are not measuring the same thing, and do not simply collapse onto one another — but they are not independent either: the filename label correlates with derived state in a way that has a sensible physical explanation once
`inactive_engine_off` and the combined transition share are considered alongside `idle` in isolation. This is a mild but real corroboration of the operating-condition classifier, and — more importantly for the report — it is itself evidence for why per-sample derivation is necessary in the first place: a single trip-level label conflates several distinct driving behaviours that only a 1 Hz classifier can tell apart. This supports the claim in Section 2.4 that a single coarse label could not have served as a substitute for the Data Layer's own operating-condition taxonomy.

**Caveats.** Group sizes are small and unbalanced (11–56 trips per group), so these are descriptive comparisons, not a statistically tested claim of significance. The condition label itself is a subjective, driver-assigned impression of a whole trip, not a controlled experimental condition, so some noise in this comparison is expected regardless of classifier quality.
