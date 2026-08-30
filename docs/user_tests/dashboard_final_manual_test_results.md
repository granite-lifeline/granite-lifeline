# Dashboard Final Manual Test Results

## Scope

This record summarises the final manual re-test of the Granite Lifeline
Dashboard. Xinle (Charlotte) Yu carried out the checks after the Dashboard
revisions. The checks used the local application and the controlled JSON
fixtures under `dashboard/tests/`.

## Result

All 28 manual cases passed in the final re-test.

| Test IDs | Area checked | Final result |
| --- | --- | --- |
| TC-001--TC-003 | Overview rendering, risk-card content and risk ordering | Pass |
| TC-004 | Display when all components have Medium risk | Pass |
| TC-005 | Ordering of mixed High-, Medium- and Low-risk components | Pass |
| TC-006--TC-007 | Navigation from the Overview to component details | Pass |
| TC-008 | Component name, risk badge and risk gauge on the Detail page | Pass |
| TC-009--TC-010 | Risk Trend rendering and interaction | Pass |
| TC-011--TC-013 | Key Signals table, ordering and status presentation | Pass |
| TC-014--TC-015 | Diagnostic-report sections and content | Pass |
| TC-016 | Empty component-list state | Pass |
| TC-017 | Single-component state | Pass |
| TC-018 | Missing optional fields | Pass |
| TC-019 | Missing risk history | Pass |
| TC-020 | Missing key signals | Pass |
| TC-021--TC-024 | Light and dark themes, theme toggle and persistence | Pass |
| TC-025 | Responsive layout at mobile, tablet and desktop widths | Pass |
| TC-026--TC-028 | Local-run guidance and return to the upload flow | Pass |

## Re-test notes

The earlier execution record marked TC-008 as partial because the Detail page
did not show the risk-level badge. TC-025 was also partial because the Key
Signals table overflowed and the confidence badge had spacing problems at
mobile width. Both cases passed after the interface fixes.

The earlier plan did not contain final outcomes for TC-004, TC-005 and
TC-016--TC-020. These cases were re-run with
`ui_all_medium_risk.json`, `ui_mixed_risk_levels.json`,
`ui_empty_data.json`, `ui_single_component.json`,
`ui_missing_fields_data.json`, `ui_no_trend_data.json` and
`ui_no_key_signals.json`; all seven passed.

This manual result covers the stated interface cases. It does not constitute a
complete browser and device matrix, a formal accessibility audit, or a
performance and concurrency evaluation.
