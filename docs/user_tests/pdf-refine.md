# Report-Comparison Refinement Record

**Status:** approved design implemented in the Version 3.0 study documents  
**Date:** 2026-08-11

The earlier proposal for a standalone report-comprehension section is
superseded. The study now compares two reports for the same controlled case:
one generated with retrieved grounding and one generated without retrieval.

## Approved design

- Retain the existing dashboard screenshot study and its unchanged Q1–Q8
  `comprehension_total` range of 0–8.
- Build two matched Google Forms: six valid participants read retrieved
  grounding first, and six read the no-retrieval report first.
- Show every page from each locked PDF as controlled PNG screenshots. The
  reports must have identical case, page count, headings, layout, and
  non-generated content.
- Use neutral `Report A` and `Report B` labels during the questionnaire.
  Disclose the generation conditions only in the post-submission debrief.
- Rate each report for ease of understanding and reasonableness, then collect
  blind preferences for the easier and more reasonable report.
- Do not create report objective-comprehension items or a
  `report_comprehension_total`: the first report can affect recall for the
  second report.
- Limit the pilot-confirmed Form completion time to 15 minutes.

## Required report handoff

The Report group must provide both final PDFs, their branch and full commit,
the common model-input fixture, generation date and configuration, source
output JSONs, and the condition mapping. The user-test team verifies the pair
against `protocol.md` §4 before creating assets or launching either Form.

If the report fixture differs from the dashboard's Cooling demo fixture, record
the mismatch and report dashboard and report findings separately. Do not
present unverified report values as dashboard values.

## Implementation authority

`protocol.md` defines the study method and reporting boundary.
`questionnaires.md` contains the exact Google Forms wording and Form-version
mapping. `screenshot_capture_plan.md` defines PDF conversion and stimulus
acceptance. `results_log_template.md` defines condition decoding and descriptive
paired analysis. `form_admin_checklist.md` defines build, form-test, pilot, and
launch checks.
