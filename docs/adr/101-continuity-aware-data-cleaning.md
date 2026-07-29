# ADR 101: Continuity-Aware Data Cleaning and Trip Segmentation

## Status

Accepted

## Date

2026-07-07

## Context

The Data Layer needs to convert the raw KIT Automotive OBD-II CSV files into a consistent dataset for operating-condition classification, feature engineering, proxy checks, and Model Layer consumption. The source records contain heterogeneous timestamps, duplicate samples, short missing intervals, physically invalid values, and observations recorded at an irregular rate.

Initial cleaning aligned timestamps and signals and resampled the observations to a uniform 1 Hz grid. A post-cleaning quality review then found that some source records contained multiple temporally discontinuous sections. Treating each source file, or the combined dataset, as one continuous time series would create observations across periods in which no measurements were recorded.

This is unsafe for downstream calculations. Interpolation could bridge a long recording break; rolling windows could combine measurements from unrelated driving periods; slopes and duration counters could include elapsed time in which the vehicle state was unknown; and train/test windows could cross a real continuity boundary.

The cleaned dataset therefore requires both a stable driving-record identity and an explicit representation of continuity within that record.

## Decision

The cleaning pipeline adopts a two-level temporal identity:

1. Each chronologically ordered raw driving file is assigned a stable `trip_id` in the form `trip_<four-digit ordinal>`.
2. Within each trip, a timestamp gap greater than 3 seconds starts a new `segment_id` in the form `<trip_id>_seg_<three-digit ordinal>`.
3. Resampling, missing-value treatment, and all later time-dependent calculations are bounded by `segment_id`; no interpolation or rolling state is allowed to cross a segment boundary.
4. Samples are resampled to 1 Hz within each continuous segment. Missing runs of at most 2 seconds may be treated using the configured per-signal strategy; longer missing periods are retained rather than filled.
5. Duplicate timestamps keep the last source observation.
6. Physically impossible values are replaced with missing values and explicitly flagged. Unusual but physically possible values are retained with suspicious-value flags so that cleaning does not remove potential anomaly evidence.
7. The output retains `trip_id`, `segment_id`, timestamp, row position within the segment, and field-level quality provenance as part of the public data contract.

The resulting reference dataset contains 81 trips and 118 continuous segments. A trip is the stable identity of a source driving record; a segment is the continuity boundary used for time-series operations.

## Rationale

### Why retain both `trip_id` and `segment_id`?

`trip_id` preserves the identity and ordering of the original driving record, which is useful for dataset splitting, trip-level evaluation, and report traceability. However, one source record is not guaranteed to be temporally continuous. `segment_id` records the continuity discovered during quality assessment and provides the correct boundary for interpolation, rolling features, persistence checks, and state machines.

Using only `trip_id` would incorrectly imply that every row within a source file is adjacent in time. Using only `segment_id` would discard the higher-level driving-record identity required by downstream trip-level decisions. The two identifiers represent different concepts and are therefore both retained.

### Why use a 3-second segmentation threshold?

The target dataset is resampled at 1 Hz and the cleaning configuration permits treatment of missing runs only up to 2 seconds. A raw gap greater than 3 seconds is therefore treated as a recording discontinuity rather than a small sampling irregularity. This keeps the imputation allowance strictly below the segmentation boundary and prevents a missing-value strategy from reconstructing long unobserved periods.

### Why preserve suspicious values?

The Data Layer supports anomaly and proxy-failure detection. Removing every unusual value during cleaning would risk deleting the evidence that later stages are intended to assess. The cleaning policy therefore distinguishes between:

- values outside a physical sensor range, which are invalid and replaced with missing values; and
- unusual but physically possible values, which are retained and marked as suspicious.

This preserves anomaly evidence while allowing downstream rules to decide whether a flagged value is evaluable.

## Alternatives Considered

### Treat Every Source File as One Continuous Trip

**Rejected.** This preserves source-file identity but ignores internal timestamp discontinuities. Interpolation, slopes, rolling windows, and persistence logic could cross recording breaks and create synthetic behaviour that was never observed.

### Concatenate and Resample the Entire Dataset as One Time Series

**Rejected.** This would erase trip boundaries and could connect different days, routes, and engine-start contexts. It would also introduce serious leakage risks when generating model windows or train/test splits.

### Split Only by Trip and Discard Segment Identity

**Rejected.** Trip-level separation is necessary but insufficient because the quality review found multiple continuous sections inside some trips. Downstream time-series operations require the finer `segment_id` boundary.

### Drop All Rows After a Large Gap

**Rejected.** Later observations remain valid even when they are not continuous with the earlier portion of the same trip. Assigning a new segment preserves usable data without pretending that continuity exists.

### Interpolate Across Every Gap

**Rejected.** Long gaps contain no observed vehicle behaviour. Interpolating across them would fabricate sensor trajectories, thermal evolution, and fault persistence.

## Consequences

### Positive

- Time-series features, operating states, and proxy persistence cannot leak across known recording breaks.
- Trip-level traceability is preserved while discontinuous sections remain usable.
- Short-gap treatment is deterministic and separated from long-gap segmentation.
- Quality provenance allows downstream stages to abstain when a value is imputed, suspicious, invalid, or unavailable.
- Dataset splitting can use `trip_id`, while rolling calculations use `segment_id`.
- The identity and continuity rules form a testable contract shared by all Data Layer stages.

### Negative

- Downstream components must retain and group by both `trip_id` and `segment_id`.
- Some trips produce multiple segments, which makes trip-level aggregation more complex.
- Features that require a long continuous history lose coverage near each segment boundary.
- The 3-second threshold is a project-specific cleaning decision tied to the 1 Hz target frequency and 2-second imputation policy.

### Mitigation Strategies

- Input-contract and continuity tests reject missing keys, duplicate keys, non-contiguous row numbering, and windows that cross a declared boundary.
- Cleaning reports record the number of continuous segments and the maximum raw gap for every trip.
- Feature engineering resets differences, rolling windows, integrals, and stateful calculations inside each `segment_id`.
- The segmentation and imputation thresholds are stored in versioned cleaning configuration rather than hidden in analysis code.

## Implementation

### Configuration

- Cleaning configuration: `data_layer/data_cleaning/src/cleaning_config.yaml`
- Resample frequency: `1s`
- Segment threshold: `segment_gap_seconds: 3`
- Maximum treated missing run: `imputation_max_seconds: 2`
- Duplicate policy: `duplicate_keep: last`

### Code Location

- Cleaning implementation: `data_layer/data_cleaning/src/cleaning_core.py`
- Cleaning entry point: `data_layer/data_cleaning/src/data_cleaning.py`
- Quality audit: `data_layer/data_cleaning/src/quality_audit.py`
- Continuity contract: `data_layer/pipeline_data/continuity.py`
- Continuity tests: `data_layer/tests/pipeline_data_test/test_continuity_contract.py`

### Output Contract

The cleaned output includes stable temporal keys and provenance fields, including:

- `trip_id`
- `segment_id`
- `timestamp`
- `row_in_segment`
- source/imputation/suspicious/hard-invalid quality flags

## Related Decisions

- ADR 104: Graded Synthetic Fault-Injection Validation for Proxy Checks
- ADR 201: Residual Detection over Classification
- `data_layer/contracts/feature_manifest.v1.json`: production feature and identity contract
- `docs/INTERFACE.md`: cross-layer data interface
