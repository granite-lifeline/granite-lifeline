# Google Forms Build Sheet — Granite Lifeline Communication Study

**Version 3.0 — 2026-08-11**  
**Screenshot build:** `granite-lifeline` `develop` @ `74e58d0`

This is the authoritative source for constructing two matched online
questionnaires: `rag_first` and `baseline_first`. Copy wording and option
order exactly. Do not shorten labels or adapt questions while building either
Form.

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
initial descriptive view of response counts and distributions. Do not enable
the respondent-facing `View results summary` setting: it can make response
summaries, including free-text answers, available to people who can respond.

The linked Google Sheet or CSV export remains the analysis authority. Forms
charts include all submissions and do not apply the protocol exclusions,
derive Q1--Q8 correctness flags, calculate the 0--8 comprehension score,
produce Wilson confidence intervals, or calculate medians and interquartile
ranges. Apply those steps in `results_log_template.md` before reporting
findings.

## 2. Form title and description

**Title**

> Granite Lifeline Dashboard Communication Study

**Description**

> We are evaluating how clearly a vehicle-health dashboard and its example
> reports communicate their results. You will see screenshots and answer
> questions about what they appear to say. You will not install or operate
> software, open a PDF, or use a real vehicle.
>
> The study takes no more than 15 minutes. We are reviewing the communication,
> not testing you. Some wording may genuinely be unclear, and identifying that
> is useful to the project.
>
> Project contact: pn25381@bristol.ac.uk

## 3. Section 1 — Information and consent

**Section title:** `Before you take part`

**Section description**

> This study is part of the University of Bristol MSc project Granite
> Lifeline. It investigates whether adults can understand information shown in
> screenshots of a vehicle-health dashboard and example reports.
>
> Participation is voluntary. The form asks for broad age, driving,
> mechanical-knowledge and software-confidence categories, followed by your
> interpretation of dashboard and report screenshots. It does not ask for your
> name, email address, student number, or information about a real vehicle.
>
> Responses are anonymous and will be stored in university-managed storage for
> the project team and supervisor to analyse for teaching and research. You
> may stop at any time before submitting. Because no identity is attached to a
> submitted response, the team cannot identify and remove it afterwards.
>
> The screenshots contain illustrative vehicle readings only. They do not
> describe you or any real vehicle. Please do not include names or other
> identifying information in the optional comment.
>
> Questions can be sent to: pn25381@bristol.ac.uk

### C1 — Eligibility and consent

- **Type:** Multiple choice
- **Required:** Yes
- **Branching:** first option → Section 2; second option → Exit section
- **Prompt:** `Please select the statement that applies to you.`
- **Options, in this order:**
  1. `I am 18 or over, I have read the information above, and I freely consent to take part.`
  2. `I am under 18 or I do not consent to take part.`
- **Scored:** No

### Exit section

**Title:** `You will not enter the study`

**Text**

> Thank you for considering the study. No study answers have been requested.
> Please close this form without submitting a response.

Set this section to submit/end rather than continue to the questionnaire. Do
not count an exit response in the study dataset.

## 4. Section 2 — Background

**Section title:** `A little about your experience`

**Section description**

> These broad categories help us describe the group that answered the form.
> They will not be used to grade or identify anyone.

### B1 — Age band

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which age band are you in?`
- **Options:** `18–24`; `25–34`; `35–44`; `45+`; `Prefer not to say`

### B2 — Driving licence

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Do you hold, or have you previously held, a driving licence?`
- **Options:** `Yes`; `No`; `Prefer not to say`

### B3 — Mechanical knowledge

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How would you describe your knowledge of how cars work mechanically?`
- **Options, in order:** `None`; `A little`; `Moderate`; `Good`;
  `I work or have worked on vehicles`; `Prefer not to say`

### B4 — Software confidence

- **Type:** Linear scale, 1 to 5
- **Required:** Yes
- **Prompt:** `How confident are you generally with software and web applications?`
- **Left label:** `1 — Not at all confident`
- **Right label:** `5 — Very confident`

### B5 — OBD-II experience

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Have you used a vehicle diagnostic app or OBD-II reader before?`
- **Options:** `Yes`; `No`; `Not sure`; `Prefer not to say`

## 5. Rating scales

Create each clarity item as a required multiple-choice question. Do not use a
grid because each item belongs directly below its own screenshot group.

**Options, fixed for CL1–CL6:**

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

Insert image `assets/01-demo-entry.png`.

**Image caption:** `Screenshot 1 — The dashboard starting page.`

**Image alt text:** `Granite Lifeline starting page with CSV upload controls, How to Run Locally, and Explore with demo data.`

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

### CL1 — Starting-page clarity

- **Prompt:** `How clear is this screen about how to view sample results without uploading files?`
- **Options:** shared clarity scale

## 7. Section 4 — Upload and local setup guidance

**Section title:** `Understanding the upload guidance`

Insert these images in order:

1. `assets/02-three-file-message.png`
   - Caption: `Screenshot 2A — The message shown after three trip files are selected.`
   - Alt text: `Upload page showing an Upload At Least 5 CSV Files message after three files were selected.`
2. `assets/03-local-run-guide.png`
   - Caption: `Screenshot 2B — The four-step local setup guide.`
   - Alt text: `How to Run Locally page with Prepare project, Install tools, Start Granite, and Open dashboard steps.`

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

### U1 — Least-clear local step

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Without carrying out the commands, which setup step would need the most explanation for you?`
- **Options, in order:** `Prepare project`; `Install tools`; `Start Granite`;
  `Open dashboard`; `None — all four steps are clear`
- **Scored:** No

### CL2 — Upload/setup clarity

- **Prompt:** `Overall, how clear are the upload message and local setup guide?`
- **Options:** shared clarity scale

## 8. Section 5 — Vehicle-health overview

**Section title:** `Understanding the vehicle overview`

Insert image `assets/04-vehicle-overview.png`.

**Image caption:** `Screenshot 3 — The vehicle-health overview and component cards.`

**Image alt text:** `Overview with a demo-data notice, urgent-attention banner, risk legend, and five component cards led by Cooling System at 86 percent.`

### Q3 — Overall status

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What is the main message about this vehicle's overall condition?`
- **Options, in order:**
  1. `No component needs attention`
  2. `Attention is needed because at least one component is High risk`
  3. `Every component has failed`
  4. `The dashboard has no component data`
- **Analyst key:** option 2
- **Score column:** `q3_correct`

### Q4 — Priority component

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which option correctly identifies the component that needs attention first?`
- **Options, in order:**
  1. `Cooling System — High — 86%`
  2. `Air Intake — Medium — 61%`
  3. `Manifold Pressure — Medium — 54%`
  4. `Accelerator Pedal — Low — 22%`
- **Analyst key:** option 1
- **Score column:** `q4_correct`

### Q5 — Data-source notice

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `What does the orange Data source notice indicate?`
- **Options, in order:**
  1. `The sample vehicle is currently on fire`
  2. `The shown component results use illustrative demo values`
  3. `All five components have missing data`
  4. `The participant uploaded an invalid file`
- **Analyst key:** option 2
- **Score column:** `q5_correct`

### CL3 — Overview clarity

- **Prompt:** `How clear is this screen about the vehicle's overall condition and which component has the highest priority?`
- **Options:** shared clarity scale

## 9. Section 6 — Cooling risk and trend

**Section title:** `Understanding the Cooling System risk`

Insert image `assets/05-cooling-risk.png`.

**Image caption:** `Screenshot 4 — Cooling System failure label, risk score, and recent trend.`

**Image alt text:** `Cooling System detail showing 72 percent within 15 trips, an 86 percent risk gauge, and an upward risk trend.`

### Q6 — Trend direction

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How has the Cooling System risk changed across the readings shown?`
- **Options, in order:** `It has been rising`; `It has been falling`;
  `It has stayed constant`; `The screen does not show a trend`
- **Analyst key:** option 1
- **Score column:** `q6_correct`

### U2 — Failure-label interpretation

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Based only on this screenshot, what do you think “72% probability of failure within the next 15 trips” means?`
- **Options, in order:**
  1. `A 72% chance that the Cooling System will mechanically fail within 15 trips`
  2. `A 72% chance that the projected risk will cross the dashboard's High-risk threshold within 15 trips`
  3. `The model is 72% confident that the current risk score is 86%`
  4. `I cannot tell what kind of “failure” the percentage refers to`
- **Scored:** No; report the distribution exactly

### CL4 — Risk-detail clarity

- **Prompt:** `How clear are the current risk score, trend, and failure estimate on this screen?`
- **Options:** shared clarity scale

## 10. Section 7 — Cooling explanation and action

**Section title:** `Understanding the explanation`

Insert image `assets/06-cooling-explanation.png`.

**Image caption:** `Screenshot 5 — Cooling System signals, explanation, and recommended actions.`

**Image alt text:** `Cooling System detail showing abnormal coolant readings, cooling-system stress causes, and three recommended actions.`

### Q7 — Recommended response

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which option best matches the actions recommended on this screen?`
- **Options, in order:**
  1. `Continue heavy driving and add coolant while the engine is hot`
  2. `Avoid heavy driving if safe, check coolant when the engine is cool, and arrange a prompt cooling-system inspection`
  3. `Replace the accelerator pedal immediately`
  4. `No action is needed because the risk is Low`
- **Analyst key:** option 2
- **Score column:** `q7_correct`

### CL5 — Explanation clarity

- **Prompt:** `How clear are the explanation, possible cause, and recommended actions?`
- **Options:** shared clarity scale

## 11. Section 8 — Exporting the report

**Section title:** `Understanding the export summary`

Insert image `assets/07-export-defaults.png`.

**Image caption:** `Screenshot 6 — The untouched default export panel.`

**Image alt text:** `Export panel ready to download five components with PDF ZIP and CSV ZIP buttons.`

### Q8 — Default PDF scope

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Without changing any export options, what would “Download PDF ZIP” provide?`
- **Options, in order:**
  1. `One PDF for the Cooling System only`
  2. `A ZIP containing PDF reports for all five components`
  3. `A CSV containing only the risk scores`
  4. `The dashboard application installer`
- **Analyst key:** option 2
- **Score column:** `q8_correct`

### CL6 — Export clarity

- **Prompt:** `How clear is what will be included in the default export?`
- **Options:** shared clarity scale

## 12. Section 9 — Report A

**Section title:** `Reading Report A`

**Section description**

> The following screenshots show every page of one example vehicle-health
> report. Read them in the order shown, then answer the two questions below.

Insert every PNG from the mapped source directory below in ascending
page-number order:

| Form version | `Report A` source pages |
| --- | --- |
| `rag_first` | `assets/reports/rag/` |
| `baseline_first` | `assets/reports/baseline/` |

For each inserted page, use the neutral caption
`Report A — page <number> of <total>.` Do not mention retrieval, RAG,
grounding, baseline, or a PDF filename in participant-facing text. Supply page
alt text that describes its visible heading and sections without revealing a
condition.

### RCL1 — Report A ease of understanding

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How easy was Report A to understand?`
- **Options:** report ease-of-understanding options

### RRN1 — Report A reasonableness

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How reasonable did Report A's explanation and recommended actions appear?`
- **Options:** report reasonableness options

## 13. Section 10 — Report B

**Section title:** `Reading Report B`

**Section description**

> The following screenshots show every page of a second example
> vehicle-health report about the same case. Read them in the order shown,
> then answer the two questions below.

Insert every PNG from the mapped source directory below in ascending
page-number order:

| Form version | `Report B` source pages |
| --- | --- |
| `rag_first` | `assets/reports/baseline/` |
| `baseline_first` | `assets/reports/rag/` |

Use the neutral caption `Report B — page <number> of <total>.` Apply the same
alt-text rule as Report A. The total must equal the Report A total.

### RCL2 — Report B ease of understanding

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How easy was Report B to understand?`
- **Options:** report ease-of-understanding options

### RRN2 — Report B reasonableness

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `How reasonable did Report B's explanation and recommended actions appear?`
- **Options:** report reasonableness options

## 14. Section 11 — Comparing the reports

**Section title:** `Comparing the two reports`

**Section description**

> Thinking about the two reports you have just read, please compare how they
> communicated the same vehicle-health case.

### RP1 — Easier report

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which report was easier to understand?`
- **Options, in order:** `Report A`; `Report B`; `They were equally easy to understand`
- **Scored:** No

### RP2 — More-reasonable report

- **Type:** Multiple choice
- **Required:** Yes
- **Prompt:** `Which report had the more reasonable explanation and recommended actions?`
- **Options, in order:** `Report A`; `Report B`; `They appeared equally reasonable`
- **Scored:** No

### RO1 — Report-comparison comment

- **Type:** Paragraph
- **Required:** No
- **Prompt:** `What, if anything, made one report easier to understand or more reasonable than the other?`
- **Description:** `Please do not include your name or other identifying information.`

## 15. Section 12 — Final dashboard comment

**Section title:** `Final comment`

### O1 — Anything unclear

- **Type:** Paragraph
- **Required:** No
- **Prompt:** `Was there anything in the dashboard screenshots that you found confusing or hard to interpret?`
- **Description:** `Please do not include your name or other identifying information.`

## 16. Confirmation message and debrief

Set the form confirmation message to:

> Thank you for taking part. Your anonymous response has been submitted.
>
> All vehicle readings in the screenshots were illustrative demo data and did
> not describe a real vehicle. One label also needs clarification: the “72%
> probability of failure” is intended to describe the model's projected chance
> of crossing the dashboard's High-risk threshold within 15 trips. It is not a
> calibrated 72% chance of a mechanical breakdown.
>
> The two reports described the same example case and were shown in different
> orders. One was generated with retrieved, source-grounded knowledge and the
> other without retrieval. This distinction was withheld until now so it did
> not influence your ratings.
>
> If you have questions about the study, contact: pn25381@bristol.ac.uk

## 17. Analyst answer key and Form-version mapping

| Item | Correct response | Correct flag |
| --- | --- | --- |
| Q1 | Explore with demo data | `q1_correct` |
| Q2 | Upload at least five chronological CSV files | `q2_correct` |
| Q3 | Attention is needed because at least one component is High risk | `q3_correct` |
| Q4 | Cooling System — High — 86% | `q4_correct` |
| Q5 | The shown component results use illustrative demo values | `q5_correct` |
| Q6 | It has been rising | `q6_correct` |
| Q7 | Avoid heavy driving if safe, check coolant when cool, and arrange prompt inspection | `q7_correct` |
| Q8 | A ZIP containing PDF reports for all five components | `q8_correct` |

`comprehension_total` is the sum of `q1_correct` through `q8_correct`, with
each flag encoded as `1` for correct and `0` for any other response.

The report items are never scored for correctness. After exporting responses,
use the Form version to decode labels for analysis:

| Form version | Report A | Report B |
| --- | --- | --- |
| `rag_first` | RAG | no RAG |
| `baseline_first` | no RAG | RAG |

Do not add the condition mapping, report filenames, source commits, or report
PDF hashes to either participant-facing Form.
