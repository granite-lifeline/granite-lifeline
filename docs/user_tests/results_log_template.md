# Google Forms Results and Analysis Template

**Version 4.0 — 2026-08-18**
**Stimulus sources:** entry-flow screens from build `74e58d0`; dashboard-state
screens and both reports from the Report-layer handoff. Both are recorded in
`protocol.md` §4, which also carries the image manifest.

The Google Forms response export is the raw record. Keep one untouched copy,
then create a separate working analysis sheet. Never add names or emails to
either sheet.

The owner-only Google Forms `Responses > Summary` charts may be used for a
first-pass view of counts and distributions. Do not treat them as the final
analysis: they include pilot, form-test, non-consent, and other excluded rows,
and raw answer charts do not calculate correctness or either composite score.
Create reported tables and charts from the linked Google Sheet or CSV only after
applying the inclusion log and scoring rules below.

## 1. Inclusion log

Assign `P01`, `P02`, … only after exporting valid responses. These are row
labels, not identifiers supplied by participants.

| response_id | include | exclusion_reason | notes |
| --- | --- | --- | --- |
| P01 | Y | | |

Allowed exclusion reasons are:

- `pilot`
- `did_not_consent`
- `form_test`
- `submitted_during_form_fault`
- `other_protocol_deviation` with an explanation in `notes`

Do not exclude a response because its answers are incorrect, unclear, or
critical of the dashboard or a report.

## 2. Working response schema

Create these columns in this order after the raw Google Forms columns. Preserve
the raw item text in the original export so every derived value remains
traceable.

| Column | Type / allowed value |
| --- | --- |
| `response_id` | `P01`, `P02`, … |
| `include` | `Y` or `N` |
| `age_band` | Form response |
| `mechanical_knowledge` | Form response |
| `software_confidence` | Integer 1–5 |
| `obd_experience` | Form response |
| `q1_correct` … `q10_correct` | Integer `1` or `0` |
| `comprehension_total` | Integer 0–10 |
| `cl1_overview` | Integer 1–5 |
| `cl2_cooling` | Integer 1–5 |
| `cl3_air_intake` | Integer 1–5 |
| `cl4_export` | Integer 1–5 |
| `u1_risk_index` | One of the four U1 options |
| `u2_trip_estimate` | One of the four U2 options |
| `rc1_correct` … `rc4_correct` | Integer `1` or `0` |
| `report_comprehension_total` | Integer 0–4 |
| `rcl1_cooling_ease` | Integer 1–5 |
| `rrn1_cooling_reasonableness` | Integer 1–5 |
| `rcl2_air_intake_ease` | Integer 1–5 |
| `rrn2_air_intake_reasonableness` | Integer 1–5 |
| `o1_comment` | Optional text |
| `protocol_note` | Blank unless an administration issue applies |

## 3. Scoring formulas

Place the ten dashboard correctness flags together, and the four report flags
together. Anchor both ranges once against the actual export — do not copy column
letters from this document, because they shift whenever a question is added or
removed.

### Per-response scores

With the dashboard flags in the first range and the report flags in the second:

```text
comprehension_total:        =SUM(<ten dashboard flag cells>)
report_comprehension_total: =SUM(<four report flag cells>)
```

The first must be an integer from 0 through 10 and the second from 0 through 4.
Never score U1, U2, clarity, rating, background, or open-comment responses.
Never add the two totals together: they measure different media, and Q1–Q2 come
from a different build than Q3–Q10.

### Per-item correct count and proportion

For a correctness column such as `H`, using only included rows:

```text
Correct n: =COUNTIFS($B$2:$B,"Y",H$2:H,1)
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

Use these formulas for both composite totals, each CL1–CL4 column, and each
RCL/RRN column.

## 4. Per-response table

| response_id | q1 | q2 | q3 | q4 | q5 | q6 | q7 | q8 | q9 | q10 | total / 10 | CL1 | CL2 | CL3 | CL4 | U1 | U2 | rc1 | rc2 | rc3 | rc4 | report total / 4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| P01 | | | | | | | | | | | | | | | | | | | | | | |

## 5. Dashboard objective-comprehension summary

Q1 and Q2 read the entry-flow captures from build `74e58d0`; Q3–Q10 read the
current dashboard state. Keep the source column so no reader pools them.

| Item | Source | Correct n / N | Correct % | Wilson 95% CI |
| --- | --- | ---: | ---: | --- |
| Q1 Demo entry | entry flow | | | |
| Q2 Trip-history upload requirement | entry flow | | | |
| Q3 Overall condition | dashboard | | | |
| Q4 Priority component | dashboard | | | |
| Q5 Cooling failure prediction | dashboard | | | |
| Q6 Cooling abnormal signals | dashboard | | | |
| Q7 Cooling stop-driving trigger | dashboard | | | |
| Q8 Air Intake failure prediction | dashboard | | | |
| Q9 Air Intake abnormal signal | dashboard | | | |
| Q10 Default export scope | dashboard | | | |

| Composite measure | Value |
| --- | --- |
| Valid N | |
| Median score / 10 | |
| IQR | |
| Observed range | |

## 6. Dashboard clarity summary

| Screen | Median | IQR | Clear/Very clear n / N |
| --- | ---: | ---: | ---: |
| CL1 Vehicle overview | | | |
| CL2 Cooling System page | | | |
| CL3 Air Intake System page | | | |
| CL4 Export | | | |

Each item rates the single screen shown directly above it. CL2 and CL3 share
wording because the two component pages share a layout; report them separately
and never average them.

No clarity item covers the entry-flow screens, so state plainly that this study
produced no clarity evidence for the starting page, the upload message, or the
setup guide. Do not substitute Q1 or Q2 correctness for it.

Treat clarity responses as ordinal. Do not calculate or report a combined
clarity average or compare it with a published usability benchmark.

## 7. Dashboard ambiguity probes

### U1 — What the 0 to 1 risk index means

| Response | n / N |
| --- | ---: |
| Probability of a mechanical breakdown | |
| An internal index supporting Low/Medium/High | |
| Proportion of trips completed | |
| Cannot tell | |

### U2 — What "High risk expected around trip 20" means

| Response | n / N |
| --- | ---: |
| Mechanical failure on about the twentieth trip | |
| Risk score crossing the High threshold at about trip 20 | |
| Twenty trips recorded so far | |
| Cannot tell | |

Do not mark U1 or U2 responses correct or incorrect. For both, report
the mechanical-failure and cannot-tell counts explicitly as evidence about the
current wording.

## 8. Report results

Use only included responses.

| Item | Correct n / N | Correct % | Wilson 95% CI |
| --- | ---: | ---: | --- |
| RC1 Locating the evidence | | | |
| RC2 Model confidence | | | |
| RC3 Immediate advice | | | |
| RC4 Information for the mechanic | | | |

| Composite measure | Value |
| --- | --- |
| Valid N | |
| Median score / 4 | |
| IQR | |
| Observed range | |

Treat the ordinal ratings as ordinal; report medians and ranges, not means or
standard deviations. Report each report separately.

| Report | Ease: median (IQR, range) | Reasonableness: median (IQR, range) |
| --- | --- | --- |
| Cooling System | | |
| Air Intake System | | |

**Do not compare the two reports against each other.** They describe different
components at different risk levels with different prediction wording, so a
difference in ratings between them is uninterpretable. Do not compute a
difference column, a preference count, or a pooled report rating.

Every participant reads the dashboard sections before either report, and both
media describe the same vehicle case. State that carryover alongside the report
results, per `protocol.md` §9.

## 9. Background description

Report counts for each response category across the four background items,
B1–B4. With 12 participants, do not run subgroup comparisons, correlations,
significance tests, or model fitting.

Every valid respondent holds or has held a driving licence, so licence status is
a constant, not a variable. State it once when describing the sample and never
treat it as a comparison group.

## 10. Optional comments

Copy non-empty comments into the table below after checking that they do not
contain identifying details. If a comment unexpectedly contains a name or
contact detail, redact it in the analysis copy and restrict access to the raw
response.

| response_id | item | comment | concise descriptive category |
| --- | --- | --- | --- |
| P__ | `O1` | | |

Summarise recurring points in plain language. Do not call this a formal thematic
analysis and do not use isolated quotations to imply prevalence.

## 11. Report-ready results checklist

- [ ] Valid N and every denominator are stated.
- [ ] Per-item results use `n/N` and Wilson intervals.
- [ ] The 0–10 dashboard total and the 0–4 report total are each reported with
      median, IQR, and range, and are never added together.
- [ ] Q1–Q2 are identified as entry-flow items from build `74e58d0` wherever
      dashboard results appear, and are never pooled with Q3–Q10.
- [ ] No entry-flow result is described as installation or setup success.
- [ ] Clarity is reported per screen using medians and IQRs.
- [ ] U1 and U2 are unscored response distributions.
- [ ] The two reports are reported separately and never compared.
- [ ] Dashboard-to-report carryover is stated wherever report results appear.
- [ ] Background variables describe the sample only.
- [ ] The licence-holder-only sample is stated, and no result is split by
      licence status.
- [ ] Viewing images is never described as dashboard use or as opening a PDF.
- [ ] The illustrative-data, risk-index, and risk-pattern-estimate limitations
      are explicit.
- [ ] The stimulus source is identified as the Report-layer handoff, with the
      image hashes recorded in `protocol.md` §4.
- [ ] No result depends on the Air Intake model confidence, which disagrees
      between the dashboard and the report.
- [ ] Findings are descriptive and claim no mechanical accuracy or predictive
      validity.
