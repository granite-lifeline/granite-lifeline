# Google Forms Build Sheet — Granite Lifeline Communication Study

**Version 4.0 — 2026-08-18**
**Stimulus sources:** entry-flow screens from build `74e58d0`; dashboard-state
screens and both reports from the Report-layer handoff. Both are recorded in
`protocol.md` §4, which also carries the image manifest.

This is the authoritative source for constructing the single online
questionnaire. Copy wording and option order exactly. Do not shorten labels or
adapt questions while building the Form.

## 1. Form settings

| Google Forms setting | Required value |
| --- | --- |
| Make this a quiz | Off |
| Collect email addresses | Do not collect |
| Send responders a copy | Off |
| Allow response editing | Off |
| Limit to one response | Off; this otherwise requires sign-in |
| View results summary (respondent-facing) | Off; owner-only `Responses > Summary` remains available |
| Shuffle question order | Off |
| Shuffle option order | Off for every question |
| Progress bar | On |
| Disable autosave for respondents | On, if the setting is available |
| Accepting responses | Off until every launch check passes |

Use the Google account and Drive location approved for university-managed
project data. Do not add tracking links, file-upload questions, or fields for
names, emails, student numbers, or social accounts.

### Using Google Forms summary charts

The project team may use the owner-only `Responses > Summary` charts for an
initial descriptive view of response counts and distributions. Do not enable the
respondent-facing `View results summary` setting: it can make response
summaries, including free-text answers, available to people who can respond.

The linked Google Sheet or CSV export remains the analysis authority. Forms
charts include all submissions and do not apply the protocol exclusions, derive
correctness flags, calculate the composite scores, produce Wilson confidence
intervals, or calculate medians and interquartile ranges. Apply those steps in
`results_log_template.md` before reporting findings.

## 2. Form title and description

**Title**

> Granite Lifeline Dashboard and Report Communication Study

**Description**

> We are evaluating how clearly a vehicle-health dashboard and its diagnostic
> reports communicate their results. You will see screenshots and report pages
> and answer questions about what they appear to say. Some screenshots show
> setup instructions, but you will not install or operate software, run any
> command, upload a file, open a PDF, or use a real vehicle.
>
> The study takes no more than 15 minutes. We are reviewing the communication,
> not testing you. Some wording may genuinely be unclear, and identifying that
> is useful to the project.
>
> Project contact: pn25381@bristol.ac.uk

## 3. Section 1 — Information and consent

**Section title:** `Before you take part`

**Section description**

> This study is part of the University of Bristol MSc project Granite Lifeline.
> It investigates whether drivers can understand information shown in
> screenshots of a vehicle-health dashboard and in the diagnostic reports it
> produces.
>
> We are inviting people aged 18 or over who hold, or have previously held, a
> driving licence. You do not need to own a vehicle or know anything about how
> cars work mechanically.
>
> Participation is voluntary. The form asks for broad age, mechanical-knowledge
> and software-confidence categories, followed by your interpretation of
> dashboard screenshots and report pages. It does not ask for your name, email
> address, student number, or information about a real vehicle.
>
> Responses are anonymous and will be stored in university-managed storage for
> the project team and supervisor to analyse for teaching and research. You may
> stop at any time before submitting. Because no identity is attached to a
> submitted response, the team cannot identify and remove it afterwards.
>
> The screenshots and report pages contain illustrative vehicle readings only.
> They do not describe you or any real vehicle. Please do not include names or
> other identifying information in the optional comments.
>
> Questions can be sent to: pn25381@bristol.ac.uk

### C1 — Eligibility and consent

- **Type:** Multiple choice
- **Required:** Yes
- **Branching:** first option → Section 2; second option → Exit section
- **Prompt:** `Please select the statement that applies to you.`
- **Options, in this order:**
  1. `I am 18 or over, I hold or have previously held a driving licence, I have read the information above, and I freely consent to take part.`
  2. `I am under 18, I have never held a driving licence, or I do not consent to take part.`
- **Scored:** No

C1 is the only eligibility gate. The licence requirement is stated in the
section description above and confirmed here, so the questionnaire asks no
separate licence question; see `protocol.md` §3.

### Exit section

**Title:** `You will not enter the study`

**Text**

> Thank you for considering the study. No study answers have been requested.
> Please close this form without submitting a response.

Set this section to submit/end rather than continue to the questionnaire. Do not
count an exit response in the study dataset.

## 4. Section 2 — Background

**Section title:** `A little about your experience`

**Section description**

> These broad categories help us describe the group that answered the form.
> They will not be used to grade or identify anyone.

Four background items, B1–B4. **Superseded:** an earlier draft asked a fifth
item, `Do you hold, or have you previously held, a driving licence?`. The study
now recruits licence holders only, so C1 gates the licence requirement and the
background question is removed rather than asked of a sample that can only
answer it one way. B1 keeps its number; mechanical knowledge, software
confidence and OBD-II experience move up to B2, B3 and B4.

### B1 — Age band

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which age band are you in?`
- **Options:** `18–24`; `25–34`; `35–44`; `45+`; `Prefer not to say`

### B2 — Mechanical knowledge

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How would you describe your knowledge of how cars work mechanically?`
- **Options, in order:** `None`; `A little`; `Moderate`; `Good`;
  `I work or have worked on vehicles`; `Prefer not to say`

### B3 — Software confidence

- **Type:** Linear scale, 1 to 5
- **Required:** Yes
- **Prompt:** `How confident are you generally with software and web applications?`
- **Left label:** `1 — Not at all confident`
- **Right label:** `5 — Very confident`

### B4 — OBD-II experience

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Have you used a vehicle diagnostic app or OBD-II reader before?`
- **Options:** `Yes`; `No`; `Not sure`; `Prefer not to say`

## 5. Rating scales

Create each rating item as a required multiple-choice question. Do not use a
grid, because each item belongs directly below its own image group.

**Clarity options, fixed for CL1–CL4:**

1. `1 — Very unclear`
2. `2 — Unclear`
3. `3 — Neither clear nor unclear`
4. `4 — Clear`
5. `5 — Very clear`

**Report ease-of-understanding options, fixed for RCL1–RCL2:**

1. `1 — Very difficult to understand`
2. `2 — Difficult to understand`
3. `3 — Neither difficult nor easy to understand`
4. `4 — Easy to understand`
5. `5 — Very easy to understand`

**Report reasonableness options, fixed for RRN1–RRN2:**

1. `1 — Very unreasonable`
2. `2 — Unreasonable`
3. `3 — Neither unreasonable nor reasonable`
4. `4 — Reasonable`
5. `5 — Very reasonable`

## 6. Section 3 — Starting the dashboard

**Section title:** `Starting with sample results`

Insert image `assets/s1-demo-entry.png`.

**Image caption:** `Screenshot 1 — The dashboard starting page.`

**Image alt text:** `Granite Lifeline starting page with an OBD-II CSV upload control, a Run Analysis button, a How to Run Locally link, and an Explore with demo data link.`

### Q1 — Demo entry

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `If you wanted to view sample results without selecting any files, which visible option would you choose?`
- **Options, in order:**
  1. `Run Analysis`
  2. `How to Run Locally`
  3. `Explore with demo data`
  4. `The light/dark theme control`
- **Analyst key:** option 3
- **Score column:** `q1_correct`

## 7. Section 4 — Upload and local setup guidance

**Section title:** `Understanding the upload guidance`

Insert these images in order:

1. `assets/s2-three-file-message.png`
   - Caption: `Screenshot 2A — The message shown after three trip files are selected.`
   - Alt text: `Upload page listing three selected trip CSV files above a red Upload At Least 5 CSV Files message.`
2. `assets/s3-local-run-guide.png`
   - Caption: `Screenshot 2B — The four-step local setup guide.`
   - Alt text: `How to Run Locally page with Prepare project, Install tools, Start Granite and Open dashboard steps, each with a copyable command block.`

### Q2 — History-upload requirement

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `According to the message, what should someone do if they want failure prediction from a trip history?`
- **Options, in order:**
  1. `Upload exactly three files again`
  2. `Upload at least five chronological CSV files`
  3. `Convert the three files to PDF`
  4. `Open the demo data instead`
- **Analyst key:** option 2
- **Score column:** `q2_correct`

The entry-flow sections carry no clarity item; see §17, constraint 4.

## 8. Section 5 — Vehicle-health overview

**Section title:** `Understanding the vehicle overview`

Insert image `assets/s4-vehicle-overview.png`.

**Image caption:** `Screenshot 3 — The vehicle-health overview and component cards.`

**Image alt text:** `Vehicle Health Status page with an attention-needed banner, a risk-level legend, and two component cards.`

### Q3 — Overall status

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What is the main message about this vehicle's overall condition?`
- **Options, in order:**
  1. `No component needs attention`
  2. `Attention is needed because at least one component requires urgent action`
  3. `Every component has already failed`
  4. `The dashboard has no component data`
- **Analyst key:** option 2
- **Score column:** `q3_correct`

### Q4 — Priority component

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which option correctly identifies the component at the higher risk level?`
- **Options, in order:**
  1. `Cooling System, at High risk level`
  2. `Air Intake System, at High risk level`
  3. `Both components are at Medium risk level`
  4. `Neither card shows a risk level`
- **Analyst key:** option 1
- **Score column:** `q4_correct`

### CL1 — Overview clarity

- **Prompt:** `How clear is this screen about the vehicle's overall condition and which component has the highest priority?`
- **Options:** clarity scale

## 9. Section 6 — Cooling System detail

**Section title:** `Understanding the Cooling System page`

Insert image `assets/s5-cooling-detail.png`.

**Image caption:** `Screenshot 4 — The full Cooling System detail page.`

**Image alt text:** `Cooling System page with a Failure Prediction panel, a High risk-level gauge, a Risk Trend chart, a Key Signals table with two abnormal coolant rows, and What's Happening, Why This Matters and What You Should Do cards.`

### Q5 — Failure prediction

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What does the Failure Prediction panel say about the Cooling System?`
- **Options, in order:**
  1. `It has already reached the High-risk threshold, and a professional inspection should be arranged soon`
  2. `It will definitely break down within the next 10 trips`
  3. `It is expected to reach High risk in about 20 trips`
  4. `It is operating normally and needs no attention`
- **Analyst key:** option 1
- **Score column:** `q5_correct`

### Q6 — Abnormal signals

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `According to the Key Signals table, which readings are marked ABNORMAL?`
- **Options, in order:**
  1. `Vehicle Speed and Engine RPM`
  2. `Coolant Temperature and Coolant Temperature Rise Rate`
  3. `Every reading in the table`
  4. `None of the readings`
- **Analyst key:** option 2
- **Score column:** `q6_correct`

### Q7 — Stop-driving trigger

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `According to this page, when should someone stop driving and seek help?`
- **Options, in order:**
  1. `As soon as the page shows High risk, without exception`
  2. `Only after the next scheduled service`
  3. `If a red temperature warning light appears, steam comes from under the hood, power is suddenly lost, or the engine feels unusually hot`
  4. `The page does not say when to stop driving`
- **Analyst key:** option 3
- **Score column:** `q7_correct`

### U1 — Risk-index interpretation

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Based only on this screenshot, what do you think the 0 to 1 values on the Risk Trend chart mean?`
- **Options, in order:**
  1. `The probability that the cooling system will mechanically break down`
  2. `An internal risk index that supports the Low, Medium and High categories`
  3. `The proportion of trips that have been completed so far`
  4. `I cannot tell what the 0 to 1 values refer to`
- **Scored:** No; report the distribution exactly

### CL2 — Cooling System page clarity

- **Prompt:** `How clear are the risk level, trend, signal readings, and recommended actions on this page?`
- **Options:** clarity scale

## 10. Section 7 — Air Intake System detail

**Section title:** `Understanding the Air Intake System page`

Insert image `assets/s6-air-intake-detail.png`.

**Image caption:** `Screenshot 5 — The full Air Intake System detail page.`

**Image alt text:** `Air Intake System page with a Failure Prediction panel, a Medium risk-level gauge, a Risk Trend chart, a Key Signals table with one abnormal airflow row, and What's Happening, Why This Matters and What You Should Do cards.`

### Q8 — Failure prediction

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What does the Failure Prediction panel say about the Air Intake System?`
- **Options, in order:**
  1. `It has already reached the High-risk threshold`
  2. `There is about a 4.7% chance of crossing into High risk within the next 10 trips`
  3. `There is about a 4.7% chance that the sensor has already failed`
  4. `No prediction can be made for this component`
- **Analyst key:** option 2
- **Score column:** `q8_correct`

### Q9 — Abnormal signal

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `According to the Key Signals table, which reading is marked ABNORMAL?`
- **Options, in order:**
  1. `Mass Airflow`
  2. `Manifold Air Pressure`
  3. `Speed-Density MAF Residual`
  4. `Engine RPM`
- **Analyst key:** option 3
- **Score column:** `q9_correct`

### U2 — Trip-estimate interpretation

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Based only on this screenshot, what do you think “High risk is expected around trip 20” means?`
- **Options, in order:**
  1. `The air intake system will mechanically fail on about the twentieth trip`
  2. `The risk score is projected to cross the dashboard's High-risk threshold at about the twentieth trip`
  3. `The dashboard has recorded twenty trips so far`
  4. `I cannot tell what “trip 20” refers to`
- **Scored:** No; report the distribution exactly

### CL3 — Air Intake System page clarity

- **Prompt:** `How clear are the risk level, trend, signal readings, and recommended actions on this page?`
- **Options:** clarity scale
- **Note:** CL2 and CL3 use identical wording because the two component pages
  use the same layout. Report them separately; do not average them into a single
  component-page score.

## 11. Section 8 — Exporting the report

**Section title:** `Understanding the export summary`

Insert image `assets/s7-export-defaults.png`.

**Image caption:** `Screenshot 6 — The untouched default export panel.`

**Image alt text:** `Export Report panel ready to download 2 components, 5 PDF sections and 5 CSV columns, with a Diagnostic report card reading 2 reports ZIP file, a Key signals table card reading 2 tables ZIP file, and Download PDF ZIP and Download CSV ZIP buttons.`

### Q10 — Default PDF scope

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Without changing any export options, what would “Download PDF ZIP” provide?`
- **Options, in order:**
  1. `One PDF for the Cooling System only`
  2. `A ZIP containing a diagnostic report for each of the two components`
  3. `A CSV containing only the risk levels`
  4. `The dashboard application installer`
- **Analyst key:** option 2
- **Score column:** `q10_correct`

### CL4 — Export clarity

- **Prompt:** `How clear is what will be included in the default export?`
- **Options:** clarity scale

## 12. Section 9 — The Cooling System report

**Section title:** `Reading the Cooling System report`

**Section description**

> The dashboard can also produce a printable diagnostic report. The following
> three pages are the complete Cooling System report. Please read them in the
> order shown, then answer the questions below.

Insert these images in order:

1. `assets/reports/cooling/page-01.png`
   - Caption: `Cooling System report — page 1 of 3.`
   - Alt text: `Report page with a Granite Lifeline Diagnostic Report header, a HIGH risk-level badge, a Summary block, a Failure Prediction block, and a Risk Trend chart.`
2. `assets/reports/cooling/page-02.png`
   - Caption: `Cooling System report — page 2 of 3.`
   - Alt text: `Report page showing a Key Signals table with Feature, Value, Unit, Reference Range and Status columns and two abnormal coolant rows.`
3. `assets/reports/cooling/page-03.png`
   - Caption: `Cooling System report — page 3 of 3.`
   - Alt text: `Report page with What's Happening, Why This Matters and What You Should Do sections.`

### RC1 — Locating the evidence

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `If you wanted to see the individual sensor readings behind this assessment and the range each one should sit in, which section of the report would you look at?`
- **Options, in order:**
  1. `Summary`
  2. `Failure Prediction`
  3. `Key Signals`
  4. `What You Should Do`
- **Analyst key:** option 3
- **Score column:** `rc1_correct`

### RC2 — Model confidence

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What model confidence does the report's Summary give for this assessment?`
- **Options, in order:** `65%`; `84%`; `90%`; `The Summary does not give a confidence value`
- **Analyst key:** option 1
- **Score column:** `rc2_correct`

### RCL1 — Cooling report ease of understanding

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How easy was the Cooling System report to understand?`
- **Options:** report ease-of-understanding options

### RRN1 — Cooling report reasonableness

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How reasonable did the Cooling System report's explanation and recommended actions appear?`
- **Options:** report reasonableness options

## 13. Section 10 — The Air Intake System report

**Section title:** `Reading the Air Intake System report`

**Section description**

> The following three pages are the complete Air Intake System report for the
> same vehicle. Please read them in the order shown, then answer the questions
> below.

Insert these images in order:

1. `assets/reports/air-intake/page-01.png`
   - Caption: `Air Intake System report — page 1 of 3.`
   - Alt text: `Report page with a Granite Lifeline Diagnostic Report header, a MEDIUM risk-level badge, a Summary block, a Failure Prediction block, and a Risk Trend chart.`
2. `assets/reports/air-intake/page-02.png`
   - Caption: `Air Intake System report — page 2 of 3.`
   - Alt text: `Report page showing a Key Signals table with Feature, Value, Unit, Reference Range and Status columns and one abnormal airflow row.`
3. `assets/reports/air-intake/page-03.png`
   - Caption: `Air Intake System report — page 3 of 3.`
   - Alt text: `Report page with What's Happening, Why This Matters and What You Should Do sections.`

### RC3 — Immediate advice

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `According to this report, what should the driver do now?`
- **Options, in order:**
  1. `Stop driving immediately and have the vehicle recovered`
  2. `Watch for unusual idle behaviour, hesitation when accelerating, or a noticeable drop in power`
  3. `Replace the air filter without consulting a mechanic`
  4. `Nothing at all until the next annual service`
- **Analyst key:** option 2
- **Score column:** `rc3_correct`

### RC4 — Information for the mechanic

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What does the report suggest telling the mechanic?`
- **Options, in order:**
  1. `To replace the engine control unit`
  2. `To check the thermostat and the coolant pump`
  3. `To check the air filter for contamination, inspect the airflow sensor's wiring and connectors, and verify its calibration across RPM ranges`
  4. `The report gives nothing to tell the mechanic`
- **Analyst key:** option 3
- **Score column:** `rc4_correct`

### RCL2 — Air Intake report ease of understanding

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How easy was the Air Intake System report to understand?`
- **Options:** report ease-of-understanding options

### RRN2 — Air Intake report reasonableness

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How reasonable did the Air Intake System report's explanation and recommended actions appear?`
- **Options:** report reasonableness options

## 14. Section 11 — Final comments

**Section title:** `Final comments`

### O1 — Open comment

- **Type:** Paragraph
- **Required:** No
- **Prompt:** `Was there anything in the screenshots or the report pages that you found confusing, or that you would want explained differently?`
- **Description:** `Please say which screen or report page you mean. Please do not include your name or other identifying information.`

One combined box replaces the separate dashboard and report comments. Ask
respondents to name the screen so comments remain attributable to a medium
during analysis.

## 15. Confirmation message and debrief

Set the form confirmation message to:

> Thank you for taking part. Your anonymous response has been submitted.
>
> All vehicle readings in the screenshots and report pages were illustrative and
> did not describe a real vehicle.
>
> Two labels also need clarification. The 0 to 1 Risk Trend values are an
> internal risk index used to place a component in the Low, Medium or High
> category; they are not a probability that a part will break. And a phrase such
> as “about a 4.7% chance of crossing into High risk within the next 10 trips”
> describes the model's projected chance of crossing its own High-risk
> threshold. Neither figure is a calibrated chance of a mechanical breakdown.
>
> If you have questions about the study, contact: pn25381@bristol.ac.uk

## 16. Analyst answer key

| Item | Correct response | Correct flag |
| --- | --- | --- |
| Q1 | Explore with demo data | `q1_correct` |
| Q2 | Upload at least five chronological CSV files | `q2_correct` |
| Q3 | Attention is needed because at least one component requires urgent action | `q3_correct` |
| Q4 | Cooling System, at High risk level | `q4_correct` |
| Q5 | It has already reached the High-risk threshold, and a professional inspection should be arranged soon | `q5_correct` |
| Q6 | Coolant Temperature and Coolant Temperature Rise Rate | `q6_correct` |
| Q7 | If a red temperature warning light appears, steam comes from under the hood, power is suddenly lost, or the engine feels unusually hot | `q7_correct` |
| Q8 | There is about a 4.7% chance of crossing into High risk within the next 10 trips | `q8_correct` |
| Q9 | Speed-Density MAF Residual | `q9_correct` |
| Q10 | A ZIP containing a diagnostic report for each of the two components | `q10_correct` |
| RC1 | Key Signals | `rc1_correct` |
| RC2 | 65% | `rc2_correct` |
| RC3 | Watch for unusual idle behaviour, hesitation when accelerating, or a noticeable drop in power | `rc3_correct` |
| RC4 | To check the air filter for contamination, inspect the airflow sensor's wiring and connectors, and verify its calibration across RPM ranges | `rc4_correct` |

`comprehension_total` is the sum of `q1_correct` through `q10_correct` and
ranges from 0 to 10. `report_comprehension_total` is the sum of `rc1_correct`
through `rc4_correct` and ranges from 0 to 4. Encode each flag as `1` for
correct and `0` for any other response. Never score U1, U2, clarity, rating,
background, or open-comment responses.

## 17. Question-writing constraints

Four constraints bind any future amendment:

1. **No question may depend on the Air Intake model confidence.** The dashboard
   shows 92% and the report shows 93% for the same component; see
   `protocol.md` §4. RC2 deliberately uses the Cooling System confidence,
   which is 65% in both.
2. **No report item may repeat a dashboard item.** Every participant sees the
   dashboard first, and both media describe the same vehicle case, so a repeated
   item would measure recall rather than report comprehension. RC1–RC4 are
   chosen accordingly, and `protocol.md` §9 still records dashboard-to-report
   carryover as a limitation.
3. **No question may compare the entry-flow screens with the dashboard-state
   screens.** Q1, Q2, U1, CL1 and CL2 read `s1`–`s3`, which come from an earlier
   build than `s4`–`s7`; see `protocol.md` §4. Each item must be answerable
   from its own screenshot alone.
4. **Every clarity item rates the single image directly above it, and only
   current-build screens carry one.** A rating question must never require
   scrolling back to a screenshot in an earlier section: a participant answering
   from memory produces noise, not a clarity measure. The four rated screens are
   the overview, the Cooling System page, the Air Intake System page, and the
   export panel. The entry-flow sections carry no clarity item, on the same
   grounds that removed the setup probe — they show an older build, so their
   ratings could be neither pooled with the dashboard-state results nor acted on
   with confidence. Their comprehension is still measured, by Q1 and Q2.

**Superseded.** Three earlier Version 4.0 drafts are now replaced. The first
dropped Sections 3 and 4 and numbered the dashboard items Q1–Q8. The second
reinstated those sections but carried six clarity items, CL1–CL6, and three
probes, U1–U3, in a 20-minute Form. The third held 15 minutes by merging clarity
items across sections, which produced two ratings that spanned more than one
image. The present pack keeps the reinstated sections and the scored items
Q1–Q10, `comprehension_total` 0–10, with four clarity items, CL1–CL4, two
probes, U1–U2, and one optional comment. The mapping is:

| Superseded item | Present item |
| --- | --- |
| Q1–Q8 of the first draft | Q3–Q10 |
| CL starting page, CL upload and setup | removed |
| CL overview | CL1 |
| CL cooling | CL2 |
| CL air intake | CL3 |
| CL export | CL4 |
| The merged entry-flow and component-page clarity items of the third draft | split back; see constraint 4 |
| U1 least-clear setup step | removed |
| U2 risk index, U3 trip estimate | U1, U2 |
| RO1 report comment, O1 dashboard comment | O1, one combined box |
