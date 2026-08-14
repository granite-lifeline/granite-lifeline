# Full local pipeline smoke test — 14 August 2026

## Scope

This test ran real KIT OBD-II CSV files through the production upload path:

1. Data Layer validation and feature engineering;
2. Model Layer Granite TTM inference and risk calculation;
3. Report Layer local Granite 4.1 8B generation and validation; and
4. transformation into Dashboard-ready data.

No Data, Model, Report, or Dashboard boundary was mocked. The environment
readiness check confirmed the main Python environment, cached TTM model, RAG
index (20 documents), and local Granite 4.1 8B service before execution.

## Reproducible command

Run `scripts/verify_local_pipeline.py` first, then invoke
`scripts/run_full_pipeline_smoke.py` with one or more raw KIT CSV paths. The
smoke-test script records the duration, selected component, risk result,
confidence, and whether all three generated report fields were populated.

## Integration defect found and corrected

The first repeated run exposed a cross-upload state defect. Separate uploads
were all assigned the Data Layer identifier `trip_0001`, while the Model Layer
appended them to one repository-wide risk-history file. Uploading an older
recording after a newer one therefore failed the chronological-history check.

The production upload path now supplies a history file inside that upload's
temporary directory. Separate uploads cannot contaminate one another, while
the Dashboard's separate multi-file history builder still combines trips for
trend display. An automated regression test checks the isolated history-file
argument.

## Final results

All three runs passed. The machine-readable values are stored in
`docs/evidence/full_pipeline_smoke_results.json`.

| Input file | Result | Time (s) | Risk | Confidence | Three report fields |
| --- | --- | ---: | --- | ---: | --- |
| `2017-07-05_Seat_Leon_RT_S_Stau.csv` | Pass | 81.49 | High (1.0000) | 0.6534 | Populated |
| `2017-07-11_Seat_Leon_S_RT_Frei.csv` | Pass | 79.26 | Medium (0.5236) | 0.8270 | Populated |
| `2018-03-01_Seat_Leon_RT_S_Normal.csv` | Pass | 32.99 | Medium (0.7577) | 0.7435 | Populated |

## What this evidence does and does not establish

The results show that the submitted production path can repeatedly process
different real recordings in one configured local environment and that a
cross-run defect discovered by this testing was corrected. They do not prove
diagnostic accuracy against mechanically confirmed vehicle faults, behaviour
on hardware or operating systems not tested here, or long-duration deployment
reliability. Those questions require labelled fault vehicles, additional test
machines, and a longer field study.
