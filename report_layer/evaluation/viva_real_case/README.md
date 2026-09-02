# Viva real report case

This folder makes the Challenge 3 slide example reproducible.

## Source

The example uses 22 committed model windows from six chronological Seat Leon
drives:

- `2017-07-24_Seat_Leon_RT_KA_Normal.json`
- `2017-07-26_Seat_Leon_RT_S_Stau.json`
- `2017-07-26_Seat_Leon_S_KA_Normal.json`
- `2017-07-27_Seat_Leon_KA_KA_Normal.json`
- `2017-07-27_Seat_Leon_KA_KA_2_Normal.json`
- `2017-07-28_Seat_Leon_KA_KA_Normal.json`

The corresponding raw CSV drives are in `data/raw/OBD-II-Dataset/`. The
committed window outputs are in
`report_layer/evaluation/prompt_refinement/raw_model_outputs/`.

## Derived result

`failure_estimation.py` aggregates the windows to one mean risk per trip and
projects the risk trend to the configured High-risk threshold. For this case:

- projected threshold crossing: **5 trips**;
- model-based probability of crossing that threshold within 10 trips:
  **0.7502**.

This is not a calibrated probability of mechanical failure and must not be
presented as one.

`baseline_report.json` and `rag_report.json` were produced locally with the
repository's three-stage report pipeline and `granite4.1:8b`. The validation
artifact records the separate quality evaluator output. That evaluator is an
analysis tool; production release is controlled by the prompt-chain Validator
and its input-aware policies.

## Dashboard-ready file

`dashboard_report.json` is the complete `ReportLayerOutput` list for the
dashboard. It combines the final grounded report with the six chronological
trip-level mean risk scores from `real_case_projection.json`. Loading this
file displays the current Medium risk, the six-point Risk Score Trend, and the
five-trip High-risk-threshold projection. The history values are aggregations
of the 22 committed model windows; they are not duplicated or invented
readings.
