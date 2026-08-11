# Google Form Administration and Pilot Checklist

**Version 3.0 — 2026-08-11**  
**Pinned screenshot build:** `granite-lifeline` `develop` @ `74e58d0`

This replaces the former facilitator script. The current study is self-guided:
no facilitator observes participants and no participant opens the dashboard or
a PDF. Build two matched Forms: `rag_first` and `baseline_first`.

## A. Before building the form

- [x] Read `protocol.md` and `questionnaires.md` in full.
- [x] Confirm every participant-facing contact field uses
      `pn25381@bristol.ac.uk`.
- [x] Obtain supervisor approval and complete the applicable Bristol student
      permission process.
- [x] Confirm the university-managed Google account and response-storage
      location.
- [x] Confirm all seven PNGs pass `screenshot_capture_plan.md` §5.
- [ ] Receive the controlled report-pair handoff required by `protocol.md`
      §4: both PDFs, condition mapping, source branch/commit, fixture,
      output JSONs, and generation configuration.
- [ ] Verify that the two reports use the same case, pages, headings, layout,
      and non-generated content; record any dashboard/report fixture mismatch.
- [ ] Convert every report page to the controlled PNG sets specified in
      `screenshot_capture_plan.md` §4A and record all hashes in
      `assets/README.md`.

## B. Verify the represented dashboard build

From `../granite-lifeline`:

```sh
git status --short --branch
git rev-parse HEAD
.venv/bin/python -m pytest -q \
  tests/test_dashboard.py \
  tests/test_export_helper.py \
  tests/test_failure_prediction_ui_states.py \
  tests/test_dashboard_ui_consistency.py \
  tests/test_demo_readiness.py
```

Expected build SHA:

```text
74e58d075a10a50a9c1f01d57e5d52adfed6e346
```

The test command must exit zero. A documented optional PDF extraction skip is
acceptable; a failed test is not.

If `develop` has changed, follow `protocol.md` §10. Do not update only the
displayed SHA while retaining unverified screenshots.

## C. Build the Google Form

- [ ] Preserve the verified version-2 dashboard Form as an archival reference.
- [ ] Clone it into `rag_first` and `baseline_first`, then copy the revised
      title, description, sections, images, questions, and option order
      exactly from `questionnaires.md`.
- [ ] Confirm the Forms differ only in which controlled report pages appear
      under neutral `Report A` and `Report B` labels.
- [ ] Keep the Form-version-to-condition mapping in the administration log;
      do not show it to participants.
- [ ] Keep quiz mode and automatic correctness feedback off.
- [ ] Keep email collection, sign-in, one-response restriction, response
      editing, and respondent-facing `View results summary` off. Owner-only
      `Responses > Summary` charts may remain available to the project team.
- [ ] Keep question and option shuffling off.
- [ ] Turn the progress bar on.
- [ ] Mark C1, B1–B5, Q1–Q8, U1–U2, CL1–CL6, RCL1–RCL2, RRN1–RRN2, and
      RP1–RP2 required.
- [ ] Leave O1 and RO1 optional.
- [ ] Route non-consent directly to the exit section.
- [ ] Use the exact confirmation/debrief message.
- [ ] Keep `Accepting responses` off.

## D. Form quality check

Preview without submitting and verify:

- [ ] Section order is fixed and screenshots appear before their questions.
- [ ] In each Form, all Report A pages precede RCL1/RRN1 and all Report B pages
      precede RCL2/RRN2.
- [ ] Report A/B labels, captions, alt text, and page counts are neutral and
      do not reveal condition, filename, retrieval, or generation method.
- [ ] Every screenshot caption is neutral.
- [ ] Every screenshot is legible on desktop.
- [ ] Every screenshot and option list is legible on a phone-sized preview.
- [ ] No question asks a participant to click, upload, download, install, run,
      or execute anything.
- [ ] No field collects identifying information.
- [ ] No answer key or score is visible.
- [ ] Estimated completion time is no more than 15 minutes.

## E. Branch and export tests

### Non-consent path

- [ ] Select the non-consent C1 option.
- [ ] Confirm the study sections do not appear.
- [ ] Confirm the exit text does not imply that study data was collected.

### Complete path — run for both Form versions

- [ ] Submit one form-test response containing known Q1–Q8 answers and both
      report ratings/preferences.
- [ ] Confirm all required questions block an incomplete submission.
- [ ] Confirm O1 can remain blank.
- [ ] Confirm the debrief appears only after submission.
- [ ] Export responses to Google Sheets/CSV.
- [ ] Confirm each expected raw column exists exactly once.
- [ ] Apply `results_log_template.md` scoring and confirm the known dashboard
      response totals 8/8; confirm its report labels decode correctly from the
      Form version.
- [ ] Mark each response `form_test` and exclude it from the final dataset.

## F. Pilot

Use one adult per Form version who is not on the project and will not enter the
final sample.

- [ ] Provide the assigned Form link and no extra dashboard or report
      explanation.
- [ ] Record only start/end time and the participant's voluntary feedback;
      do not record the participant or their screen.
- [ ] Confirm completion is within 15 minutes.
- [ ] Ask whether any screenshot text was too small.
- [ ] Ask whether any question had two plausible answers.
- [ ] Ask whether the report-page sequence made both reports readable without
      zooming or opening a PDF.
- [ ] Inspect the exported pilot row and score calculation.
- [ ] Mark the response `pilot` and exclude it.

If wording, options, screenshots, page order, or report-condition mapping
change after the pilot, repeat both branch tests for both Forms. If a
substantive dashboard or report state changes, recapture all affected images
and update the controlled-source metadata.

## G. Launch

- [ ] Freeze both Form versions and all screenshot files.
- [ ] Record the Form version, launch date, dashboard build SHA, report source
      commit, fixture, PDF hashes, and screenshot hashes in the study log.
- [ ] Turn `Accepting responses` on.
- [ ] Send the neutral recruitment message below.

**Recruitment message**

> We are inviting adults aged 18 or over to take part in a short University of
> Bristol study about how clearly a vehicle-health dashboard and example
> reports communicate results. The anonymous Google Form takes no more than
> 15 minutes and shows only screenshots; you will not install, run, or open
> any software or PDF. Please respond once. Participation is voluntary, and
> full information appears before consent at the start of the form.

## H. Close and preserve

- [ ] Stop each Form after six valid completions, for 12 valid completions in
      total, or at the documented recruitment deadline, whichever comes first.
- [ ] Export and preserve an untouched raw response file.
- [ ] Create a separate working analysis copy.
- [ ] Assign P01, P02, … only in the working copy.
- [ ] Apply exclusions before fixing N.
- [ ] Restrict both files to the project team and supervisor.
- [ ] Follow `results_log_template.md` and the protocol reporting boundary.
