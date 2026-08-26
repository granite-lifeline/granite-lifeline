# User Test Analysis Report

**Study:** Granite Lifeline Dashboard and Report Communication Study
**Protocol version:** 4.0
**Analysis date:** 2026-08-24
**Valid responses:** 12
**Analysis type:** Descriptive

## 1. Analysis status and data handling

All 12 submitted responses were confirmed to be valid study responses. No
pilot, form-test, non-consenting, form-fault, or other
protocol-deviation rows were present, so all 12 responses were included.
Anonymous row identifiers `P01`–`P12` were assigned in timestamp order.

The read-only Google Forms response spreadsheet remains the raw record. Analysis
was performed on a separate working copy. The scored-item mappings came from
`answer_key.csv`, and response-column meanings and never-score rules came from
`codebook.csv`. Dashboard comprehension and report comprehension were analysed
as separate constructs and were not combined.

The XLSX export stored the RC2 response `65%` as the numeric value `0.65`.
Scoring therefore accepted both representations as the same response. Without
this normalisation, RC2 would have been incorrectly marked as wrong for 11
participants.

## 2. Participant background

The sample comprised 12 adults who held or had previously held a driving
licence and consented to participate.

| Measure                    | Category |  n |
| -------------------------- | -------- | -: |
| Age band                   | 18–24   |  6 |
|                            | 25–34   |  5 |
|                            | 35–44   |  1 |
| Mechanical knowledge       | None     |  1 |
|                            | A little |  5 |
|                            | Moderate |  3 |
|                            | Good     |  3 |
| Software confidence        | 2 / 5    |  2 |
|                            | 3 / 5    |  3 |
|                            | 4 / 5    |  3 |
|                            | 5 / 5    |  4 |
| Previous OBD-II experience | No       | 10 |
|                            | Not sure |  1 |
|                            | Yes      |  1 |

The sample was therefore predominantly young and inexperienced with OBD-II
tools. These variables describe the sample only; no subgroup comparisons,
correlations, or significance tests were performed.

## 3. Dashboard objective comprehension

The median dashboard comprehension score was **9/10** (IQR 8.75–10; observed
range 5–10).

| Item                                | Correct n/N | Correct % | Wilson 95% CI |
| ----------------------------------- | ----------: | --------: | ------------: |
| Q1 — Demo entry                    |        7/12 |     58.3% |  32.0%–80.7% |
| Q2 — History-upload requirement    |       10/12 |     83.3% |  55.2%–95.3% |
| Q3 — Overall vehicle status        |       12/12 |    100.0% | 75.8%–100.0% |
| Q4 — Priority component            |       10/12 |     83.3% |  55.2%–95.3% |
| Q5 — Cooling failure prediction    |       10/12 |     83.3% |  55.2%–95.3% |
| Q6 — Cooling abnormal signals      |       12/12 |    100.0% | 75.8%–100.0% |
| Q7 — Stop-driving trigger          |       12/12 |    100.0% | 75.8%–100.0% |
| Q8 — Air Intake failure prediction |       11/12 |     91.7% |  64.6%–98.5% |
| Q9 — Air Intake abnormal signal    |       11/12 |     91.7% |  64.6%–98.5% |
| Q10 — Default PDF export scope     |       11/12 |     91.7% |  64.6%–98.5% |

Participants correctly identified most dashboard messages. The weakest item was
Q1: only 7/12 participants identified the visible demo-data entry option. Q1
and Q2 used entry-flow captures from build `74e58d0`, whereas Q3–Q10 used the
controlled dashboard state; the per-item results are therefore reported rather
than treating all ten items as evidence from one interface build.

## 4. Dashboard clarity

| Rating item              | Median |     IQR | Clear/Very clear n/N |
| ------------------------ | -----: | ------: | -------------------: |
| CL1 — Overview          |    4.5 |    4–5 |                12/12 |
| CL2 — Cooling System    |      4 |    4–5 |                11/12 |
| CL3 — Air Intake System |      4 | 4–4.25 |                12/12 |
| CL4 — Export            |      4 |    4–5 |                10/12 |

All four areas received generally positive clarity ratings. The export area had
the lowest Clear/Very clear count, although 10/12 participants still selected
one of those two categories.

## 5. Dashboard ambiguity probes

U1 and U2 were diagnostic probes and were **not scored**.

### U1 — Meaning of the 0–1 Risk Trend values

| Response                                             | n |
| ---------------------------------------------------- | -: |
| Mechanical-breakdown probability                     | 6 |
| Internal index supporting Low/Medium/High categories | 6 |
| Proportion of completed trips                        | 0 |
| Could not tell                                       | 0 |

Half of the participants interpreted the risk index as the probability of
mechanical breakdown. This indicates a material ambiguity in how the 0–1 scale
communicates risk, even though the associated page received positive clarity
ratings.

### U2 — Meaning of “High risk is expected around trip 20”

| Response                                                       |  n |
| -------------------------------------------------------------- | -: |
| Mechanical failure on approximately trip 20                    |  1 |
| Risk score crosses the High threshold at approximately trip 20 | 10 |
| Twenty trips have already been recorded                        |  0 |
| Could not tell                                                 |  1 |

Most participants interpreted the trip estimate as a projected threshold
crossing. One participant interpreted it as a mechanical-failure prediction,
and one could not determine its meaning.

## 6. Report comprehension

The median report comprehension score was **4/4** (IQR 4–4; observed range
3–4).

| Item                                       | Correct n/N | Correct % | Wilson 95% CI |
| ------------------------------------------ | ----------: | --------: | ------------: |
| RC1 — Locating individual sensor evidence |       12/12 |    100.0% | 75.8%–100.0% |
| RC2 — Model confidence                    |       11/12 |     91.7% |  64.6%–98.5% |
| RC3 — Immediate Air Intake advice         |       12/12 |    100.0% | 75.8%–100.0% |
| RC4 — Information to give the mechanic    |       12/12 |    100.0% | 75.8%–100.0% |

Report comprehension was high across all four items. Every participant viewed
the dashboard material before reading the reports, so these results may include
dashboard-to-report carryover and should not be interpreted as report-only
learning effects.

## 7. Report ratings

| Report and measure                         | Median |     IQR | Observed range |
| ------------------------------------------ | -----: | ------: | -------------: |
| Cooling System — ease of understanding    |      4 |    4–5 |           4–5 |
| Cooling System — reasonableness           |      4 | 4–4.25 |           4–5 |
| Air Intake System — ease of understanding |      4 |    4–5 |           4–5 |
| Air Intake System — reasonableness        |      5 |    4–5 |           3–5 |

Both reports received generally positive ratings. The two reports describe
different components, risk levels, and prediction wording, so their ratings are
reported separately and are not used to claim that one report performed better
than the other.

## 8. Optional comments

Six participants supplied a non-empty optional comment. Two comments were
positive or reported no requested change. Four comments raised concrete
presentation issues:

- the dashboard contained too much text and could be cumbersome to read;
- the report layout could be improved;
- the demo-data button could be more prominent; and
- important report content could be emphasised, for example with bold text.

These comments are presented descriptively. They do not constitute a formal
thematic analysis, and their frequency should not be interpreted as prevalence
in a wider population.

## 9. Interpretation

The results provide evidence that this sample generally identified the intended
dashboard and report messages. The strongest objective results concerned the
overall vehicle status, abnormal Cooling signals, stop-driving advice, and the
three report items RC1, RC3, and RC4. The principal communication concerns were
the visibility of the demo-data entry and the meaning of the 0–1 risk index.

These findings support targeted communication and presentation refinements.
They do not establish that participants can operate the application because the
study used controlled screenshots and report pages rather than interactive task
completion.

## 10. Limitations

- The sample was small (`N=12`), so Wilson intervals remain wide.
- Participants were predominantly aged 18–34 and generally lacked prior OBD-II
  experience.
- This was a communication and comprehension study, not an interaction-based
  usability test.
- Dashboard exposure always preceded report exposure.
- Q1–Q2 and Q3–Q10 came from different controlled interface sources.
- The Cooling and Air Intake reports cannot be compared directly.
- No inferential statistics, effect-size estimates, correlations, regressions,
  subgroup comparisons, or causal conclusions are supported.
