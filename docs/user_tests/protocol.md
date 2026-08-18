# Granite Lifeline Dashboard and Report Communication Study Protocol

**Version 4.0 — 2026-08-18**
**Stimulus sources:** entry-flow screens from build `74e58d0`; dashboard-state
screens and both reports from the Report-layer handoff. Both are recorded in §4.

**Companion documents:** `questionnaires.md` and `results_log_template.md`

This protocol supersedes version 3.0. Participants do not operate the dashboard
or open a PDF. They view a fixed sequence of dashboard screenshots and complete
report pages in an anonymous Google Form and answer questions about what those
screens and pages communicate.

## 0. What Version 4.0 changed

Version 3.0 is withdrawn in full. Version 4.0 adds new content and rebuilds
every dashboard item against the current build.

**Added.** A report-understanding stage. After the dashboard sections, each
participant reads two complete diagnostic reports — the Cooling System report
and the Air Intake System report, three pages each — and answers four scored
comprehension items, RC1–RC4, plus an ease-of-understanding and a
reasonableness rating per report. `report_comprehension_total` ranges 0–4.

**Withdrawn.** The Version 3.0 comparison of two reports for one case, one
generated with retrieved grounding and one without, is not being run. With it go
the two counterbalanced Forms, the `rag_first` / `baseline_first` condition
mapping and its decoding columns, the neutral `Report A` / `Report B` labels,
the RP1/RP2 blind preference items, and the paired analysis. Build **one** Form.
Do not reinstate that comparison without a new decision record.

**Rebuilt.** The dashboard now shows two components rather than five, risk as a
`High` / `Medium` level with no percentage, a 0–1 internal risk index in place
of the old rising percentage trend, and new failure-prediction wording; the
`72% within 15 trips` label and the demo-data notice no longer exist. Every
dashboard item was rewritten against the current screenshots. Scored dashboard
items run Q1–Q10 and `comprehension_total` ranges **0–10**.

**Sampling.** The study now recruits licence holders only. C1 gates age, licence
history and consent together, so the questionnaire asks no separate licence
question and licence status is a constant, not a variable; see §3.

**Trimmed to hold 15 minutes.** Four clarity items, one per rated screen, each
sitting directly below the single image it rates; two unscored probes; and one
combined optional comment. Nothing scored was cut. The entry-flow sections carry
no clarity item, on the grounds recorded in §6.2 and §9.

## 1. Purpose and research questions

The dashboard and the diagnostic report are intended to explain
vehicle-component risk to people who are not automotive engineers. This study
tests whether adults can understand the delivered wording and visual hierarchy
from prompted viewing.

| RQ | Question | Evidence |
| --- | --- | --- |
| **RQ1** | Can viewers correctly identify key dashboard messages? | Ten scored multiple-choice items |
| **RQ2** | Which dashboard areas appear clear or unclear? | Four clarity ratings, two unscored diagnostic probes, and one optional comment |
| **RQ3** | Can viewers correctly identify key messages in the delivered diagnostic report, and how do they rate it? | Four scored report items, plus two ease-of-understanding and two reasonableness ratings and one optional comment |

This is a **communication and comprehension study**, not an interaction-based
usability test. It cannot establish whether participants can operate the
dashboard, open or navigate a PDF, complete tasks, find controls independently,
or tolerate the workload of using the application.

## 2. Method

The study is a self-guided, screenshot-based online questionnaire. Every
participant sees the same images in the same order. No participant installs
software, runs a local pipeline, uploads a file, follows commands, uses the
hosted dashboard, opens a PDF, or changes report settings.

Two sections show the entry flow: the starting page, the message returned when
too few trip files are selected, and the local-setup guide. Participants read
those screens; they never carry out any step shown on them. Comprehension of
setup *instructions* is therefore all that is measured, never setup success.

The dashboard-state sections then cover the vehicle overview, both component
detail pages, and the export panel. After them, each participant reads two
complete reports: the Cooling System report and the Air Intake System report,
three pages each, presented as legible PNG page images in original page order.
The reports describe two different components of the same vehicle case. There
is no comparison between report generation conditions; see §0.

Build **one** Google Form. The study targets **12 valid completed responses**
and a pilot-confirmed completion time of **no more than 15 minutes**. It is not
a Google Forms quiz and never shows correctness feedback to participants. The
answer key in `questionnaires.md` is for offline analysis only.

## 3. Participants

- **Target:** 12 valid completed responses.
- **Inclusion:** adults aged 18 or over who hold, or have previously held, a
  driving licence and can give informed consent.
- **Audience:** licence holders of mixed background; vehicle ownership and
  mechanical knowledge are not required.
- **Exclusion:** anyone who has never held a driving licence, anyone who worked
  on Granite Lifeline, anyone who previously saw the dashboard or either study
  report, and anyone who took part in the pilot. Form-test responses are also
  excluded.
- **Recruitment:** convenience sampling through a neutral invitation that
  states the study concerns dashboard and report communication and that it is
  open to licence holders aged 18 or over.

The licence requirement is enforced by the C1 eligibility gate, which routes
anyone who has never held a licence to the exit section. Because every valid
respondent is a licence holder, the questionnaire asks no separate licence
question and no analysis may split the sample by licence status.

Mechanical knowledge, software confidence, and prior OBD-II experience describe
the sample only. The sample supports no demographic or inferential subgroup
claims.

## 4. Stimulus control and anchor values

Thirteen participant-facing images come from two sources:

- **`s1`–`s3`, the entry flow:** starting page, too-few-files message, and
  local-setup guide, reinstated from build `74e58d0`. The Report-layer handoff
  contains no capture of these screens, so no current replacement exists. They
  show no risk level, percentage, component count, risk trend, or data-source
  notice, so they cannot contradict any anchor value below. Confirm before
  launch that the entry flow still looks this way, and re-capture all three if
  it does not.
- **`s4`–`s7` and the six report pages:** derived from the six PDFs supplied by
  the Report layer as a single handoff and used as supplied. This group does not
  regenerate, edit, or re-derive the dashboard state or the report text, and the
  Report layer uploads the underlying sources to the main team repository
  separately.

The six dashboard stimulus sections are starting page, upload and local setup,
overview, Cooling System detail, Air Intake System detail, and export. Images
are light-theme desktop captures, cropped for legibility rather than
full-browser reproductions.

The seven dashboard images are held in `assets/`. Verify each against this
manifest before the Form is published:

| File | Form section | Source | Pixels | SHA-256 |
| --- | --- | --- | --- | --- |
| `s1-demo-entry.png` | Starting with sample results | `74e58d0` | 1440 × 863 | `8b7be25f227166c4d2a8555292e827d84eb3ed780f0355b7c106a0a493eed8ea` |
| `s2-three-file-message.png` | Understanding the upload guidance | `74e58d0` | 1440 × 1000 | `2016613586e3f2073f8b222fe3fcebd29180818027ff83c674f0a2f2a772314e` |
| `s3-local-run-guide.png` | Understanding the upload guidance | `74e58d0` | 1440 × 1602 | `4f48c9d20a71730d7861ea5b421f46a4d1111582417d0ec890032f0d38bfd921` |
| `s4-vehicle-overview.png` | Vehicle-health overview | handoff | 2968 × 1400 | `1f35a545f073e66a7c3658361f3b26a54121532a942858babfcc2a223ca42956` |
| `s5-cooling-detail.png` | Cooling System detail | handoff | 2968 × 4540 | `6a9cf76f6e5cf69c1000938524bf1b4ac4be5a8109483261b68e38a84dd34933` |
| `s6-air-intake-detail.png` | Air Intake System detail | handoff | 2968 × 4420 | `92b90bf9d302b43dac0271947cc12dbe1c63455a30c740114a7f5fb215f5f22b` |
| `s7-export-defaults.png` | Exporting the report | handoff | 2968 × 830 | `5802acac63584a463b0193d770c196457a48a74eaf5bd8f2878f4bf9e6bb5bd0` |

The six report page images, `assets/reports/cooling/page-01.png` through
`page-03.png` and `assets/reports/air-intake/page-01.png` through `page-03.png`,
are not in this directory yet. The Report layer uploads them with the underlying
report sources. Each is an A4 page rendered at 1696 × 2400. Do not build the
Form until all six are present, complete, and in original page order.

| Dashboard anchor | Current value |
| --- | --- |
| Demo entry | `Explore with demo data`, below an `or` divider under the upload card |
| Too-few-files message | `Upload At Least 5 CSV Files`; failure prediction needs at least five chronological trips |
| Local-setup guide | Four steps: `Prepare project`, `Install tools`, `Start Granite`, `Open dashboard` |
| Components shown | Two: Cooling System and Air Intake System |
| Overall banner | `Attention needed — one or more components require urgent action` |
| Cooling System | `High` risk level; no percentage on the card or gauge |
| Air Intake System | `Medium` risk level; no percentage on the card or gauge |
| Cooling failure prediction | Already reached the High-risk threshold; arrange a professional inspection soon |
| Air Intake failure prediction | About 4.7% chance of crossing into High risk within the next 10 trips; High risk expected around trip 20 |
| Risk trend | 0–1 internal risk index over the recorded model windows, captioned as not a probability of mechanical failure |
| Cooling abnormal signals | Coolant Temperature 84.0 °C against 90–95; Coolant Temperature Rise Rate 5.5069 °C/min against 0–2 |
| Air Intake abnormal signal | Speed-Density MAF Residual 32.4138 g/s against −20–20 |
| Default export | 2 component(s), 5 PDF section(s), 5 CSV column(s); PDF and CSV ZIP downloads |

The report pages carry the same case: the same risk levels, the same
prediction wording, and the same key-signal readings and reference ranges.

The first three anchors are read from `s1`–`s3` and the rest from `s4`–`s7`. No
item may combine the two groups, because they come from different builds.

Two further constraints on the images themselves. Every participant-facing image
must be cropped to **exclude the page footer**, which names six real project
members. And the Air Intake model confidence differs between the two stimulus
types, 92% on the dashboard against 93% in the report; no question may depend on
that value, and neither figure may be reported as the component's confidence.
The Cooling System agrees at 65% in both, which is why RC2 uses that figure.
Every other anchor above agrees across the two stimulus types.

## 5. Form flow

| Stage | Content | Required |
| --- | --- | --- |
| 1. Information and consent | Purpose, anonymous data use, 18+ and licence gate | Yes |
| 2. Background | Four coarse contextual questions | Yes |
| 3. Entry-flow screenshots | Q1–Q2 | Yes |
| 4. Dashboard-state screenshots | Q3–Q10, CL1–CL4, U1–U2 | Yes |
| 5. Cooling System report | Three pages, RC1–RC2, RCL1, RRN1 | Yes |
| 6. Air Intake System report | Three pages, RC3–RC4, RCL2, RRN2 | Yes |
| 7. Final comment | O1, one combined box | No |
| 8. Debrief | Limitations and label clarification | After submission |

A participant who does not confirm age, licence history, and consent at C1 is
routed to an exit section and provides no study answers.

## 6. Measures and scoring

### 6.1 Dashboard objective comprehension

Ten scored dashboard items are worth one point each, with no partial credit.
They cover demo entry, the trip-history upload requirement, overall status,
priority component, the Cooling failure prediction, Cooling abnormal signals,
the Cooling stop-driving trigger, the Air Intake failure prediction, the Air
Intake abnormal signal, and default export scope. `comprehension_total` is the
sum of Q1–Q10 and ranges from **0 to 10**.

`comprehension_total` mixes two builds: Q1 and Q2 read the entry-flow captures
and Q3–Q10 read the current dashboard state. Report the composite only alongside
the per-item results, so a reader can see which items came from which source.

### 6.2 Dashboard clarity and diagnostic items

Four clarity items use a fixed five-point ordinal scale. Each sits directly
below the single image it rates, so no participant answers a rating question
from memory:

| Item | Rates | Image |
| --- | --- | --- |
| CL1 | The vehicle overview | `s4` |
| CL2 | The Cooling System page | `s5` |
| CL3 | The Air Intake System page | `s6` |
| CL4 | The export panel | `s7` |

The entry-flow sections carry no clarity item. They show an older build, so a
clarity rating of them could be neither pooled with the dashboard-state results
nor acted on with confidence — the same reason the setup probe was removed.
Entry-flow comprehension is still measured, by Q1 and Q2.

CL2 and CL3 use identical wording because the two component pages share a
layout. Report them separately and never average them into one component-page
score.

Two diagnostic items are unscored: U1 probes what the 0–1 risk-trend index
appears to mean and U2 probes what `High risk is expected around trip 20`
appears to mean. Both diagnose wording rather than validating the estimator.

One optional free-text comment, O1, covers the screenshots and the report pages
together and asks the respondent to name the screen they mean.

### 6.3 Report comprehension and ratings

Four scored report items, RC1–RC4, are worth one point each, with no partial
credit. RC1 and RC2 concern the Cooling System report; RC3 and RC4 concern the
Air Intake System report. `report_comprehension_total` is their sum and ranges
from **0 to 4**. The items are labelled `RC` so they are never confused with the
research questions RQ1–RQ3 above.

They are scored because the two reports describe **different** components, so
reading one does not supply the answers for the other. The items are chosen so
that none repeats a dashboard item.

Immediately after each report, participants also answer two required five-point
items: how easy that report was to understand, and how reasonable its
explanation and recommended actions appeared. One optional comment follows both
reports and must not contain identifying information.

## 7. Analysis plan

Analysis is descriptive throughout:

1. Report dashboard item correctness as `n/N` with Wilson 95% confidence
   intervals, and report the median, interquartile range, and observed range of
   the 0–10 dashboard total.
2. Report dashboard clarity per item with median, interquartile range, and the
   `Clear`/`Very clear` count.
3. Report report-item correctness as `n/N` with Wilson 95% confidence
   intervals, and report the median, interquartile range, and observed range of
   the 0–4 report total.
4. Report each report's ease-of-understanding and reasonableness ratings with
   median, interquartile range, and observed range, per report and never pooled
   into a single report score.
5. Report the U1 and U2 distributions as unscored counts.
6. Summarise optional comments descriptively. Do not present a formal thematic
   analysis, statistical significance test, effect-size estimate, correlation,
   regression, or causal conclusion.

Do not compare the Cooling and Air Intake reports against each other. They
differ in component, risk level, and prediction wording, so any difference in
ratings is uninterpretable.

Exclude pilot, non-consenting, form-test, documented form-fault, and other
protocol-deviation responses before fixing `N`. Do not exclude an answer
because it is incorrect or critical of the dashboard or a report.

## 8. Ethics and data handling

- Obtain supervisor sign-off and the applicable Bristol student permission
  before recruitment or a substantive Form amendment.
- Forms must not collect names, email addresses, student numbers, social
  handles, or free-text identifying details.
- Store the form and raw exports in university-managed storage limited to the
  project team and supervisor.
- A submitted anonymous response cannot be identified and removed later; state
  this before consent.
- No participant is photographed, recorded, screen-shared, or observed.
- Crop the page footer from every participant-facing image so project members
  are not named to participants.
- The debrief explains that readings are illustrative and clarifies the
  risk-index and failure-prediction wording after all answers are submitted.

The participant-facing project contact is `pn25381@bristol.ac.uk`.

## 9. Limitations and reporting boundary

- Screenshot and page-image viewing does not test PDF controls, zooming,
  navigation, downloads, dashboard interaction, responsiveness, or performance.
- Q1 and Q2 test whether the **wording** of the entry and setup screens is
  understood. No participant uploads a file or runs a command, so nothing here
  evidences that anyone can actually start the application, and no result may be
  described as installation or setup success.
- **The entry-flow captures `s1`–`s3` come from build `74e58d0`, an earlier
  build than the dashboard-state captures.** They are used because the
  Report-layer handoff contains no entry-flow screens. Findings from Q1 and Q2
  describe that earlier entry flow, and must not be pooled with, or compared
  against, the dashboard-state findings. No clarity rating covers those screens,
  so this study says nothing about how clear the entry flow appears.
- Prompted viewing is easier than unaided system use.
- A 12-person convenience sample supports descriptive findings only.
- **Every participant holds or has held a driving licence.** Findings describe
  how the dashboard and reports communicate to drivers. Nothing here evidences
  how a non-driver reads either medium, and no result may be split or compared
  by licence status.
- **Dashboard exposure precedes report exposure for every participant.** The
  two media describe the same vehicle case, so report comprehension scores may
  be inflated by carryover from the dashboard sections. Report the two totals
  separately and never present the report total as independent evidence that
  the report alone communicates successfully.
- The report findings concern the two supplied reports and their locked layout.
  They do not establish that the format works for other anomalies, vehicles,
  prompts, or report designs.
- Participants see two components at two risk levels. Nothing here evidences
  how the dashboard or report communicates a Low-risk or healthy result.
- The risk trend is a 0–1 internal index, and the failure prediction is a
  risk-pattern estimate. Neither is a calibrated probability of mechanical
  failure, and no participant response can validate the estimator.

Permitted wording includes `participants correctly identified`,
`participants rated the report as easy to understand`, and
`participants found the export scope unclear`. Do not write
`participants successfully used`, `the dashboard was usable`,
`the report was accurate`, or `the reports were mechanically accurate` from
this study.

## 10. Change control and launch gate

The only permitted mixing of sources is the entry flow: `s1`–`s3` from build
`74e58d0` alongside `s4`–`s7` and the report pages from the Report-layer
handoff, on the grounds stated in §4. The four remaining Version 3.0 images —
`04-vehicle-overview.png`, `05-cooling-risk.png`, `06-cooling-explanation.png`
and `07-export-defaults.png`, deleted from `assets/` in this revision — show a
five-component dashboard, an `86%` gauge, a `72% within 15 trips` label and a
`5 component(s)` export. None of that exists in the current build, so they
**must never appear in a Form** and their values must never be cited as current.
Immediately before launch:

1. Verify every image hash and dimension against the §4 manifest, and confirm
   all six report page images have arrived.
2. Confirm every image excludes the page footer.
3. Confirm the entry flow in the current build still matches `s1`–`s3`.
4. Preview every section on desktop and mobile, including every report page.
5. Submit non-consent and complete form-test paths.
6. Export the response sheet and verify dashboard scoring, report columns, and
   no identifying data. Anchor the column map recorded in
   `results_log_template.md` §0 against that export.
7. Pilot the Form, confirm completion within 15 minutes, then repeat the launch
   checks after any content, image, option, or order change.
8. Obtain supervisor approval for the study materials before turning on
   responses.

Responses carry no identity, so a test or pilot submission cannot be recognised
afterwards from its answers. Record the exact submission timestamp and the
applicable `results_log_template.md` §1 exclusion reason for every form-test and
pilot submission, and for the window of any content change made while the Form
was accepting responses. That log is the only thing that makes those rows
excludable; without it they are indistinguishable from valid responses. Keep it
as the `submission_log` of `results_log_template.md` §0, and never delete a row
from the response sheet to remove one.
