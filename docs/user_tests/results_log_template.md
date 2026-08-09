# Google Forms Results and Analysis Template

**Version 2.0 — 2026-08-09**  
**Build represented:** `granite-lifeline` `develop` @ `74e58d0`

The Google Forms response export is the raw record. Keep one untouched copy,
then analyse a working copy. Never add names or emails to either sheet.

The owner-only Google Forms `Responses > Summary` charts may be used for a
first-pass view of counts and distributions. Do not treat them as the final
analysis: they include pilot, form-test, non-consent, and other excluded rows,
and raw Q1--Q8 answer charts do not calculate correctness or the composite
score. Create reported tables and charts from the linked Google Sheet or CSV
only after applying the inclusion log and scoring rules below.

## 1. Inclusion log

Assign `P01`, `P02`, … only after exporting valid responses. These are row
labels, not identifiers supplied by participants.

| response_id | include | exclusion_reason | build_sha | notes |
| --- | --- | --- | --- | --- |
| P01 | Y | | `74e58d0` | |

Allowed exclusion reasons are:

- `pilot`
- `did_not_consent`
- `form_test`
- `submitted_during_form_fault`
- `other_protocol_deviation` with an explanation in `notes`

Do not exclude a response because its answers are incorrect, unclear, or
critical of the dashboard.

## 2. Working response schema

Create these columns in this order after the raw Google Forms columns. Preserve
the raw item text in the original export so every derived value remains
traceable.

| Column | Type / allowed value |
| --- | --- |
| `response_id` | `P01`, `P02`, … |
| `include` | `Y` or `N` |
| `build_sha` | `74e58d0` for this capture set |
| `age_band` | Form response |
| `licence_history` | Form response |
| `mechanical_knowledge` | Form response |
| `software_confidence` | Integer 1–5 |
| `obd_experience` | Form response |
| `q1_correct` … `q8_correct` | Integer `1` or `0` |
| `comprehension_total` | Integer 0–8 |
| `cl1_demo_entry` | Integer 1–5 |
| `cl2_upload_setup` | Integer 1–5 |
| `cl3_overview` | Integer 1–5 |
| `cl4_risk_detail` | Integer 1–5 |
| `cl5_explanation` | Integer 1–5 |
| `cl6_export` | Integer 1–5 |
| `u1_least_clear_step` | One of the five U1 options |
| `u2_failure_interpretation` | One of the four U2 options |
| `o1_comment` | Optional text |
| `protocol_note` | Blank unless an administration issue applies |

## 3. Scoring formulas

Assume the eight correctness flags occupy columns `J:Q` in the working sheet.
Adjust the range once if the actual export places them elsewhere, then use the
same range for every row.

### Per-response score

```text
=SUM(J2:Q2)
```

The result must be an integer from 0 through 8. Never score U1, U2, clarity,
background, or open-comment responses.

### Per-item correct count and proportion

For a correctness column such as `J`, using only included rows:

```text
Correct n: =COUNTIFS($B$2:$B,"Y",J$2:J,1)
Valid N:   =COUNTIF($B$2:$B,"Y")
Proportion:=correct_n/valid_N
```

### Wilson 95% confidence interval

With `p` as the correct proportion, `n` as valid N, and `z = 1.959964`:

```text
centre = (p + z^2/(2*n)) / (1 + z^2/n)
margin = z*SQRT((p*(1-p) + z^2/(4*n))/n) / (1 + z^2/n)
lower  = MAX(0, centre - margin)
upper  = MIN(1, centre + margin)
```

Show the result as `n/N (percentage%; 95% CI lower–upper)` so the small
denominator is always visible.

### Median and interquartile range

For included rows, filter the relevant numeric column first, then use:

```text
=MEDIAN(FILTER(score_range,$B$2:$B="Y"))
=QUARTILE(FILTER(score_range,$B$2:$B="Y"),1)
=QUARTILE(FILTER(score_range,$B$2:$B="Y"),3)
```

Use these formulas for `comprehension_total` and each CL1–CL6 column.

## 4. Per-response table

| response_id | q1 | q2 | q3 | q4 | q5 | q6 | q7 | q8 | total / 8 | CL1 | CL2 | CL3 | CL4 | CL5 | CL6 | U1 | U2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| P01 | | | | | | | | | | | | | | | | | |

## 5. Objective-comprehension summary

| Item | Correct n / N | Correct % | Wilson 95% CI |
| --- | ---: | ---: | --- |
| Q1 Demo entry | | | |
| Q2 History upload | | | |
| Q3 Overall condition | | | |
| Q4 Priority component | | | |
| Q5 Data-source notice | | | |
| Q6 Trend direction | | | |
| Q7 Recommended response | | | |
| Q8 Default export scope | | | |

| Composite measure | Value |
| --- | --- |
| Valid N | |
| Median score / 8 | |
| IQR | |
| Observed range | |

## 6. Clarity summary

| Screen group | Median | IQR | Clear/Very clear n / N |
| --- | ---: | ---: | ---: |
| CL1 Demo entry | | | |
| CL2 Upload and local setup | | | |
| CL3 Vehicle overview | | | |
| CL4 Risk detail | | | |
| CL5 Explanation and action | | | |
| CL6 Export | | | |

Treat clarity responses as ordinal. Do not calculate or report a combined
clarity average or compare it with a published usability benchmark.

## 7. Ambiguity probes

### U1 — Least-clear local setup step

| Response | n / N |
| --- | ---: |
| Prepare project | |
| Install tools | |
| Start Granite | |
| Open dashboard | |
| None — all four steps are clear | |

### U2 — Failure-label interpretation

| Response | n / N |
| --- | ---: |
| Mechanical failure within 15 trips | |
| Projected risk crossing the High threshold | |
| Model confidence interpretation | |
| Cannot tell what “failure” means | |

Do not mark U2 responses correct or incorrect. Report the mechanical-failure
and cannot-tell counts explicitly as evidence about the current label.

## 8. Background description

Report counts for each response category. With 10–14 participants, do not run
driver/non-driver comparisons, correlations, significance tests, or model
fitting.

## 9. Optional comments

Copy non-empty O1 comments into the table below after checking that they do
not contain identifying details. If a comment unexpectedly contains a name or
contact detail, redact it in the analysis copy and restrict access to the raw
response.

| response_id | comment | concise descriptive category |
| --- | --- | --- |
| P__ | | |

Summarise recurring points in plain language. Do not call this a formal
thematic analysis and do not use isolated quotations to imply prevalence.

## 10. Report-ready results checklist

- [ ] Valid N and every denominator are stated.
- [ ] Per-item comprehension results use `n/N` and Wilson intervals.
- [ ] The 0–8 total is reported with median, IQR, and range.
- [ ] Clarity is reported per screen using medians and IQRs.
- [ ] U1 and U2 are unscored response distributions.
- [ ] Background variables describe the sample only.
- [ ] Screenshot viewing is never described as dashboard use.
- [ ] The illustrative-data and failure-threshold limitations are explicit.
- [ ] The build is identified as `74e58d0`.
