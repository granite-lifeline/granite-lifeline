# Granite Lifeline Dashboard Communication Study Protocol

**Version 2.0 — 2026-08-09**  
**Build represented:** `granite-lifeline` `develop` @ `74e58d0`  
**Companion documents:** `questionnaires.md`, `screenshot_capture_plan.md`,
`form_admin_checklist.md`, and `results_log_template.md`

This protocol supersedes the interactive usability-study protocol version
1.2. Participants do not operate the dashboard. They view a fixed sequence of
screenshots in an anonymous Google Form and answer questions about what the
screens communicate.

## 1. Purpose and research questions

The dashboard is intended to explain vehicle-component risk to people who are
not automotive engineers. This study tests whether adults can understand the
delivered interface from its visible wording and visual hierarchy.

| RQ | Question | Evidence |
| --- | --- | --- |
| **RQ1** | Can viewers correctly identify the vehicle-health status, priority component, risk trend, recommended action, upload requirement, and export scope? | Eight scored multiple-choice items |
| **RQ2** | Which dashboard areas appear clear or unclear to viewers? | Six five-point clarity ratings, two unscored ambiguity probes, and one optional comment |

This is a **communication and comprehension study**, not an interaction-based
usability test. It cannot establish whether participants can operate the
dashboard, complete tasks, find controls independently, or tolerate the
workload of using the application.

## 2. Method

The study is a self-guided, screenshot-based online questionnaire. Every
participant sees the same images in the same order and answers immediately
below each image group. No participant installs software, runs a local
pipeline, uploads a file, follows commands, or uses the hosted dashboard.

The earlier protocol's task success, time-on-task, error count, assists, SEQ,
SUS, and NASA-TLX measures are removed. Those measures require performed tasks
or actual system use, which passive screenshot viewing does not provide.

The form targets an **8–10 minute** completion time. It is not configured as a
Google Forms quiz, and it never shows correctness feedback to participants.
The answer key in `questionnaires.md` is for offline analysis only.

## 3. Participants

- **Target:** 10–14 valid completed responses.
- **Inclusion:** adults aged 18 or over who can give informed consent.
- **Audience:** mixed adults; a driving licence or vehicle ownership is not
  required.
- **Exclusion:** anyone who worked on Granite Lifeline or previously saw the
  dashboard. The pilot participant is also excluded from the final sample.
- **Recruitment:** convenience sampling through a neutral invitation that
  states the study concerns dashboard communication.

Licence history, mechanical knowledge, software confidence, and prior OBD-II
experience describe the sample only. The sample is too small for driver versus
non-driver comparisons or inferential subgroup claims.

## 4. Build and stimulus control

All screenshots are captured from the sibling main repository's clean
`develop` checkout at commit `74e58d0`. The current demo fixture is
`dashboard/tests/ui_required_data.json`.

The fixed evidence anchors are:

| Item | Current value | Evidence |
| --- | --- | --- |
| Components shown | Five | `dashboard/tests/ui_required_data.json` |
| Highest priority | Cooling System | fixture ordering plus `dashboard/data_store.py` risk sorting |
| Cooling risk | High, 86% | fixture `risk_level` and `risk_score` |
| Cooling trend | 45% → 52% → 61% → 70% → 86% | fixture `risk_history` |
| Failure label | 72% within 15 trips | fixture estimate and `dashboard/failure_prediction.py` |
| Recommended response | Check coolant only when cool and arrange prompt cooling-system inspection | fixture `recommended_action` |
| History upload rule | One file for a single analysis, or at least five chronological files for history; two to four are rejected | `dashboard/pages/overview.py` |
| Default export | All five components; PDF and CSV ZIP downloads | `dashboard/pages/overview.py` |

The six stimulus sections are:

1. **Demo entry:** landing page and `Explore with demo data`.
2. **Upload and local setup:** three-file validation message and the current
   four-step `How to Run Locally` guide.
3. **Overview:** data-source notice, urgent-attention banner, risk legend, and
   all five component cards.
4. **Cooling risk:** failure label, 86% gauge, and rising trend.
5. **Cooling explanation:** key signals, diagnosis, cause, and actions.
6. **Export:** untouched default export summary and ZIP buttons.

Screenshots are light-theme desktop captures, cropped for legibility rather
than full-browser reproductions. Captions are neutral and do not reveal an
answer. Images must remain readable in Google Forms desktop and mobile
previews.

## 5. Form flow

| Stage | Content | Required |
| --- | --- | --- |
| 1. Information and consent | Purpose, anonymous data use, 18+ and consent gate | Yes |
| 2. Background | Five coarse contextual questions | Yes, with `Prefer not to say` where appropriate |
| 3. Six screenshot sections | Eight scored questions, six clarity ratings, and two ambiguity probes | Yes |
| 4. Final comment | Anything confusing or hard to interpret | No |
| 5. Debrief | Illustrative-data and failure-label explanation | Displayed after submission |

A participant who does not confirm eligibility and consent is branched to an
exit section and provides no study answers.

## 6. Measures and scoring

### 6.1 Objective comprehension

The eight scored items are worth one point each, with no partial credit:

1. Select `Explore with demo data` to view example results.
2. Respond to the three-file error by uploading at least five chronological
   CSV files.
3. Recognise that the car needs attention because at least one component is
   High risk.
4. Identify `Cooling System — High — 86%` as the priority.
5. Interpret the data-source notice as indicating illustrative demo values.
6. Identify the Cooling risk trend as rising.
7. Select the coolant-check and prompt-mechanic response.
8. Recognise that the untouched PDF export is a ZIP covering all five
   components.

The total comprehension score ranges from **0 to 8**.

### 6.2 Clarity

Each stimulus section receives one rating on this fixed ordinal scale:

1. Very unclear
2. Unclear
3. Neither clear nor unclear
4. Clear
5. Very clear

### 6.3 Diagnostic, unscored items

The following items diagnose wording problems and do not contribute to the
0–8 score:

- what `72% probability of failure within the next 15 trips` appears to mean;
- which of the four local-run steps remains least clear.

The live interface contract defines the failure estimate as the probability
that the projected risk crosses the High-risk threshold within a fixed
horizon, not a calibrated probability of mechanical failure. Because the
dashboard label does not explain this distinction, a mechanical-failure
interpretation is a finding about the interface wording, not a participant
error.

## 7. Analysis plan

Analysis is descriptive throughout:

1. Report correct `n/N` and a Wilson 95% confidence interval for each scored
   item.
2. Report the median, interquartile range, and observed range of the 0–8 total
   score.
3. Report the median and interquartile range for each clarity item. Also show
   the count selecting `Clear` or `Very clear` so the small-sample denominator
   remains visible.
4. Report response counts for both unscored ambiguity probes.
5. Summarise the optional comments descriptively. Do not claim a formal
   thematic analysis from one short prompt.
6. Describe background responses as counts only. Do not run significance
   tests, compare demographic groups, or generalise percentages to the wider
   population.

The pilot response, non-consenting exits, obvious test submissions, and any
response submitted after a documented form fault are excluded before `N` is
fixed. Anonymous duplicate responses cannot be reliably detected; the
recruitment message therefore asks each person to respond once.

## 8. Ethics and data handling

- Obtain supervisor sign-off on the experiment and the relevant Bristol
  student permission form before recruitment.
- Participants must be 18 or over and give informed consent before any study
  questions appear.
- Google Forms email collection and sign-in are disabled. Do not collect
  names, email addresses, student numbers, social handles, or free-text
  identifying details.
- Store the form and exported responses in university-managed storage with
  access limited to the project team and supervisor.
- Because the form is anonymous at submission, a submitted response cannot be
  identified and withdrawn later. State this before consent; participants may
  exit before submitting.
- The optional comment warns participants not to include names or identifying
  information.
- No participant is photographed, recorded, screen-shared, or observed.
- The debrief states that every vehicle reading is illustrative and describes
  no real vehicle.

The participant-facing project contact is `pn25381@bristol.ac.uk`.

## 9. Limitations and reporting boundary

- Screenshots reveal what is visible after navigation; they do not test
  discoverability, control operation, scrolling, responsiveness, downloads,
  file validation, or system performance.
- The questionnaire measures comprehension under prompted viewing and is
  likely easier than unaided use.
- The small convenience sample supports descriptive findings only.
- A single fixed demo vehicle cannot establish comprehension across other
  risk combinations or missing-data states.
- The local-run guide is shown to mixed adults even though command-line setup
  is intended for technically confident users; report that result separately
  from owner-facing dashboard comprehension.
- The failure wording is known to overstate the live contract. Its response
  distribution diagnoses this issue but does not validate the estimator.

Permitted report wording includes `participants correctly interpreted` or
`participants rated the screenshot as clear`. Do not write `participants
successfully used`, `the dashboard was usable`, `tasks were completed`, or
`workload was low` from this study.

## 10. Change control and launch gate

Do not mix screenshots from different builds. Immediately before launch:

1. Confirm the main repo is still on `develop` and record its full SHA.
2. If the SHA differs from `74e58d0`, diff every stimulus-relevant file and
   either retain the pinned capture set or recapture and re-key the whole form.
3. Run the dashboard regression command in `form_admin_checklist.md`.
4. Preview every form section on desktop and mobile.
5. Submit one non-consent path and one complete test response.
6. Export the response sheet and verify all columns and the 0–8 score.
7. Confirm `pn25381@bristol.ac.uk` appears in every participant-facing contact
   field and obtain supervisor sign-off.
