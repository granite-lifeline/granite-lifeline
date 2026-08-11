# Google Forms Results and Analysis Template

**Version 3.0 — 2026-08-11**  
**Build represented:** `granite-lifeline` `develop` @ `74e58d0`

**Report-pair status:** no report pair is approved or captured in this version

The two Google Forms response exports are the raw records. Keep one untouched
copy of each, then combine copies into one working analysis sheet. Never add
names or emails to either raw or working sheet.

The owner-only Google Forms `Responses > Summary` charts may be used for a
first-pass view of counts and distributions. Do not treat them as the final
analysis: they include pilot, form-test, non-consent, and other excluded rows,
and raw Q1--Q8 answer charts do not calculate correctness or the composite
score. Create reported tables and charts from the linked Google Sheet or CSV
only after applying the inclusion log and scoring rules below.

## 1. Inclusion log

Assign `P01`, `P02`, … only after exporting valid responses. These are row
labels, not identifiers supplied by participants.

| response_id | include | exclusion_reason | form_version | build_sha | notes |
| --- | --- | --- | --- | --- |
| P01 | Y | | `rag_first` | `74e58d0` | |

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
| `form_version` | `rag_first` or `baseline_first` |
| `build_sha` | `74e58d0` for this capture set |
| `report_a_condition` | `RAG` or `baseline`, decoded from `form_version` |
| `report_b_condition` | `RAG` or `baseline`, decoded from `form_version` |
| `report_source_commit` | Full Report-layer source commit from the capture log |
| `report_fixture` | Named common model-input fixture from the capture log |
| `report_rag_pdf_sha256` | SHA-256 recorded in `assets/README.md` |
| `report_baseline_pdf_sha256` | SHA-256 recorded in `assets/README.md` |
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
| `rcl1_report_a_ease` | Integer 1–5 |
| `rrn1_report_a_reasonableness` | Integer 1–5 |
| `rcl2_report_b_ease` | Integer 1–5 |
| `rrn2_report_b_reasonableness` | Integer 1–5 |
| `rp1_easier_report` | `Report A`, `Report B`, or equal option |
| `rp2_more_reasonable_report` | `Report A`, `Report B`, or equal option |
| `ro1_report_comment` | Optional text |
| `rag_ease` | Integer 1–5, decoded from the matching Report A/B rating |
| `baseline_ease` | Integer 1–5, decoded from the matching Report A/B rating |
| `ease_difference_rag_minus_baseline` | Integer −4 through 4 |
| `rag_reasonableness` | Integer 1–5, decoded from the matching Report A/B rating |
| `baseline_reasonableness` | Integer 1–5, decoded from the matching Report A/B rating |
| `reasonableness_difference_rag_minus_baseline` | Integer −4 through 4 |
| `easier_condition` | `RAG`, `baseline`, or `equal`, decoded from RP1 |
| `more_reasonable_condition` | `RAG`, `baseline`, or `equal`, decoded from RP2 |
| `o1_comment` | Optional text |
| `protocol_note` | Blank unless an administration issue applies |

## 3. Dashboard scoring formulas

Place the eight correctness flags together in the working sheet. Set their
range once after combining the two exports, then use the same range for every
row. For example, if the flags occupy `J:Q`:

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

## 4. Report-condition decoding and paired calculations

Complete the administration fields from the capture log before calculating any
report results. Do not infer a condition from the participant-facing Report A
or Report B label.

| `form_version` | `report_a_condition` | `report_b_condition` |
| --- | --- | --- |
| `rag_first` | `RAG` | `baseline` |
| `baseline_first` | `baseline` | `RAG` |

For each row, copy the Report A or Report B rating into its decoded condition
column. For example, with Report A ease in `T2`, Report B ease in `V2`, and
Report A condition in `D2`:

```text
rag_ease:      =IF($D2="RAG",T2,V2)
baseline_ease: =IF($D2="baseline",T2,V2)
difference:    =rag_ease-baseline_ease
```

Apply the same mapping to reasonableness. Decode RP1 and RP2 against the same
condition mapping; retain `equal` when the participant selects an equal
option. Do not score a report-comprehension total.

## 5. Per-response dashboard table

| response_id | q1 | q2 | q3 | q4 | q5 | q6 | q7 | q8 | total / 8 | CL1 | CL2 | CL3 | CL4 | CL5 | CL6 | U1 | U2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| P01 | | | | | | | | | | | | | | | | | |

## 6. Dashboard objective-comprehension summary

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

## 7. Dashboard clarity summary

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

## 8. Dashboard ambiguity probes

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

## 9. Report paired-comparison summary

Use only included responses. The total target is 12, with six responses from
each Form version. Treat ordinal ratings as ordinal; report medians and ranges,
not means or standard deviations.

| Measure | RAG median | Baseline median | RAG − baseline median | Observed paired range |
| --- | ---: | ---: | ---: | --- |
| Ease of understanding | | | | |
| Reasonableness | | | | |

| Blind preference | RAG n / N | Baseline n / N | Equal n / N |
| --- | ---: | ---: | ---: |
| Easier to understand | | | |
| More reasonable | | | |

| Form version | Valid N | Ease RAG − baseline: median (range) | Reasonableness RAG − baseline: median (range) |
| --- | ---: | --- | --- |
| `rag_first` | | | |
| `baseline_first` | | | |

Do not apply a significance test, effect-size calculation, or formal
between-order comparison. The order rows reveal possible carryover only.

## 10. Background description

Report counts for each response category. With 12 participants, do not run
driver/non-driver comparisons, correlations, significance tests, or model
fitting.

## 11. Optional comments

Copy non-empty O1 comments into the table below after checking that they do
not contain identifying details. If a comment unexpectedly contains a name or
contact detail, redact it in the analysis copy and restrict access to the raw
response.

| response_id | comment | concise descriptive category |
| --- | --- | --- |
| P__ | | |

Apply the same privacy check and descriptive treatment to RO1 report comments.
Summarise recurring points in plain language. Do not call this a formal
thematic analysis and do not use isolated quotations to imply prevalence.

## 12. Report-ready results checklist

- [ ] Valid N and every denominator are stated.
- [ ] Per-item comprehension results use `n/N` and Wilson intervals.
- [ ] The 0–8 total is reported with median, IQR, and range.
- [ ] Clarity is reported per screen using medians and IQRs.
- [ ] U1 and U2 are unscored response distributions.
- [ ] Background variables describe the sample only.
- [ ] Screenshot viewing is never described as dashboard use.
- [ ] The illustrative-data and failure-threshold limitations are explicit.
- [ ] The build is identified as `74e58d0`.
- [ ] The report source commit, fixture, PDF hashes, and condition mapping are
      identified.
- [ ] Report ratings are decoded from Form version before analysis.
- [ ] Report results include paired differences, preference `n/N`, and the two
      six-person order-group summaries.
- [ ] Report findings are descriptive and do not claim retrieval improved
      comprehension, mechanical accuracy, or predictive validity.
