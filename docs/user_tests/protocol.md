# Granite Lifeline Dashboard and Report Communication Study Protocol

**Version 3.0 — 2026-08-11**  
**Dashboard screenshot build:** `granite-lifeline` `develop` @ `74e58d0`  
**Report-pair status:** no report pair is approved or captured in this version

**Companion documents:** `questionnaires.md`, `screenshot_capture_plan.md`,
`form_admin_checklist.md`, `results_log_template.md`, and
`pdf-refine.md`

This protocol supersedes version 2.0. Participants do not operate the
dashboard or open a PDF. They view a fixed sequence of dashboard and report
screenshots in an anonymous Google Form and answer questions about what the
screens communicate.

## 1. Purpose and research questions

The dashboard and report are intended to explain vehicle-component risk to
people who are not automotive engineers. This study tests whether adults can
understand the delivered wording and visual hierarchy from prompted viewing.

| RQ | Question | Evidence |
| --- | --- | --- |
| **RQ1** | Can viewers correctly identify key dashboard messages? | Eight scored multiple-choice items |
| **RQ2** | Which dashboard areas appear clear or unclear? | Six clarity ratings, two ambiguity probes, and one optional comment |
| **RQ3** | For the same case and layout, do viewers rate a retrieved-grounding report and a no-retrieval report differently for ease of understanding and reasonableness? | Counterbalanced paired ratings and blind preferences |

This is a **communication and comprehension study**, not an interaction-based
usability test. It cannot establish whether participants can operate the
dashboard, open or navigate a PDF, complete tasks, find controls independently,
or tolerate the workload of using the application.

## 2. Method

The study is a self-guided, screenshot-based online questionnaire. Every
participant sees the same dashboard images in the same order. No participant
installs software, runs a local pipeline, uploads a file, follows commands,
uses the hosted dashboard, opens a PDF, or changes report settings.

After the dashboard sections, each participant views two complete report
stimulus sets. Each set contains every page of one locked PDF, represented as
legible PNG screenshots in original page order. The reports must use the same
model input, number of pages, headings, visual layout, and source evidence.
They may differ only in report text generated with or without retrieved
grounding.

Google Forms cannot randomly assign a report order. Build two otherwise
identical Forms and recruit two separate groups:

| Form version | Valid target | First report | Second report |
| --- | ---: | --- | --- |
| `rag_first` | 6 | Report A: retrieved grounding | Report B: no retrieval |
| `baseline_first` | 6 | Report A: no retrieval | Report B: retrieved grounding |

Participants see only `Report A` and `Report B`; they are not told which
generation condition produced either report until after submission. The form
version is an administration field, not a participant question.

The study targets **12 valid completed responses** and a pilot-confirmed
completion time of **no more than 15 minutes**. It is not a Google Forms quiz
and never shows correctness feedback to participants. The answer key in
`questionnaires.md` is for offline dashboard analysis only.

## 3. Participants

- **Target:** 12 valid completed responses: 6 from each Form version.
- **Inclusion:** adults aged 18 or over who can give informed consent.
- **Audience:** mixed adults; a driving licence or vehicle ownership is not
  required.
- **Exclusion:** anyone who worked on Granite Lifeline, previously saw the
  dashboard or either study report, or took part in either pilot. Form-test
  responses are also excluded.
- **Recruitment:** convenience sampling through a neutral invitation that
  states the study concerns dashboard and report communication.

Licence history, mechanical knowledge, software confidence, and prior OBD-II
experience describe the sample only. The sample supports no demographic or
inferential subgroup claims.

## 4. Stimulus control and report-pair acceptance

The seven dashboard images are captured from the sibling main repository's
clean `develop` checkout at commit `74e58d0`. The current dashboard fixture is
`dashboard/tests/ui_required_data.json`.

| Dashboard anchor | Current value |
| --- | --- |
| Components shown | Five |
| Highest priority | Cooling System |
| Cooling risk | High, 86% |
| Cooling trend | 45% → 52% → 61% → 70% → 86% |
| Failure label | 72% within 15 trips |
| Default export | All five components; PDF and CSV ZIP downloads |

The six dashboard stimulus sections are demo entry, upload and local setup,
overview, Cooling risk, Cooling explanation, and export. Screenshots are
light-theme desktop captures, cropped for legibility rather than full-browser
reproductions.

Before report screenshots are captured or either revised Form is launched, the
Report group must supply the following controlled handoff for both conditions:

1. The two final PDFs, each generated from the same named model-input fixture.
2. The source branch and full commit, generation date, and generation
   configuration for each PDF.
3. The condition mapping: retrieved grounding or no retrieval.
4. The source report-output JSONs and evidence that risk, estimate, key
   signals, and recommended actions use the same underlying case.
5. Confirmation that page count, page order, headings, visual layout, and
   non-generated content are identical.

Record the handoff and SHA-256 hash of every report PDF and page PNG in
`assets/README.md`. If the report case differs from the dashboard demo case,
record that fact and report dashboard and report findings separately. Never
claim that the dashboard and report conditions represent the same vehicle
without verified fixture evidence.

## 5. Form flow

| Stage | Content | Required |
| --- | --- | --- |
| 1. Information and consent | Purpose, anonymous data use, 18+ gate | Yes |
| 2. Background | Five coarse contextual questions | Yes |
| 3. Dashboard screenshots | Q1–Q8, CL1–CL6, U1–U2 | Yes |
| 4. Report A | Complete report pages, two ratings | Yes |
| 5. Report B | Complete report pages, two ratings | Yes |
| 6. Blind report comparison | Two preference questions and optional reason | Preferences yes; reason no |
| 7. Final dashboard comment | Optional | No |
| 8. Debrief | Dashboard limitations and report-condition disclosure | After submission |

A participant who does not confirm eligibility and consent is routed to an
exit section and provides no study answers.

## 6. Measures and scoring

### 6.1 Dashboard objective comprehension

The existing eight scored dashboard items remain worth one point each, with no
partial credit. They cover demo entry, upload history, overall status,
priority component, data-source notice, risk trend, recommended response, and
default export scope. `comprehension_total` remains the sum of Q1–Q8 and
ranges from **0 to 8**.

### 6.2 Dashboard clarity and diagnostic items

The six dashboard clarity items retain their fixed five-point ordinal scale.
The two existing diagnostic items remain unscored. The failure-label item
diagnoses wording rather than validating the estimator.

### 6.3 Report paired ratings

Immediately after each report, participants answer two required five-point
items:

1. how easy the report was to understand;
2. how reasonable its explanation and recommended actions appeared.

After both reports, participants select which was easier to understand and
which appeared more reasonable, with an equal option for each. The optional
comparison comment may explain a preference but must not contain identifying
information.

These are perceived communication measures. No report-comprehension score is
calculated because reading the first report may affect recall while reading the
second report.

## 7. Analysis plan

Analysis is descriptive throughout:

1. Report dashboard item correctness as `n/N` with Wilson 95% confidence
   intervals, and report the median, interquartile range, and observed range
   of the unchanged 0–8 dashboard total.
2. Report dashboard clarity per item with median, interquartile range, and
   the `Clear`/`Very clear` count.
3. Decode each report label using the Form version, then report the paired
   RAG-minus-baseline difference for ease of understanding and reasonableness.
4. Report median and observed range of each paired difference, plus counts of
   participants favouring, disfavoring, or equally rating retrieved grounding.
5. Report blind easier-to-understand and more-reasonable preferences as `n/N`.
6. Display report findings separately for the two six-person order groups to
   reveal, but not test, possible order effects.
7. Summarise optional comments descriptively. Do not present a formal thematic
   analysis, statistical significance test, effect-size estimate, correlation,
   regression, or causal conclusion.

Exclude pilot, non-consenting, form-test, documented form-fault, and other
protocol-deviation responses before fixing `N`. Do not exclude an answer
because it is incorrect or critical of either report.

## 8. Ethics and data handling

- Obtain supervisor sign-off and the applicable Bristol student permission
  before recruitment or a substantive Form amendment.
- Forms must not collect names, email addresses, student numbers, social
  handles, or free-text identifying details.
- Store forms and raw exports in university-managed storage limited to the
  project team and supervisor.
- A submitted anonymous response cannot be identified and removed later; state
  this before consent.
- No participant is photographed, recorded, screen-shared, or observed.
- The debrief explains that readings are illustrative and discloses the report
  retrieval comparison only after all ratings are submitted.

The participant-facing project contact is `pn25381@bristol.ac.uk`.

## 9. Limitations and reporting boundary

- Screenshot viewing does not test PDF controls, zooming, navigation,
  downloads, dashboard interaction, responsiveness, or performance.
- Prompted viewing is easier than unaided system use.
- A 12-person convenience sample supports descriptive paired findings only.
- Counterbalancing reduces, but does not remove, carryover and order effects.
- The report comparison concerns the supplied single case and locked layout;
  it does not establish superiority for other anomalies, vehicles, prompts, or
  report designs.
- A preference for retrieved grounding is not evidence of mechanical accuracy,
  predictive validity, or safety.

Permitted wording includes `participants rated the report as easier to
understand` and `participants preferred the report on reasonableness`. Do not
write `participants successfully used`, `the report was usable`, `retrieved
grounding improved comprehension`, or `the reports were mechanically accurate`
from this study.

## 10. Change control and launch gate

Do not mix dashboard screenshots, report pages, or report conditions from
different controlled sources. Immediately before launch:

1. Verify the dashboard source SHA and every existing dashboard image hash.
2. Complete the report-pair acceptance checks in section 4 and preserve the
   handoff materials.
3. Clone the verified dashboard Form into `rag_first` and `baseline_first`;
   modify only report-page order and the invisible administration mapping.
4. Preview every section on desktop and mobile, including every report page.
5. Submit non-consent and complete form-test paths for both Forms.
6. Export both response sheets and verify dashboard scoring, report columns,
   condition decoding, and no identifying data.
7. Pilot each order version, confirm completion within 15 minutes, then repeat
   the launch checks after any content, screenshot, option, or order change.
8. Obtain supervisor approval for the revised study materials before turning
   on responses.

