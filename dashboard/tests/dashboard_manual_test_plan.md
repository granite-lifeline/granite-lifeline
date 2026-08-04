# Dashboard Manual Test Plan

**Project:** Granite Lifeline - MSc Project at University of Bristol  
**Sponsor:** IBM  
**Component:** Dashboard (Streamlit)  
**Task:** GL-98 (Sub-task of GL-97: Dashboard Testing)  
**Version:** 1.0  
**Date:** 2026-06-28

## Overview

This document provides a structured manual test plan for the Granite Lifeline Dashboard. The Dashboard is built with Streamlit and consists of two main pages:

1. **Overview Page**: Displays engine component risk cards with sorting by risk level
2. **Detail Page**: Shows detailed component information including trend charts, key signals, and diagnostic reports

## Test Environment

- **Application**: Streamlit Dashboard (`dashboard/app.py`)
- **Data Source**: Mock JSON data in ModelLayerOutput format
- **Browsers**: Chrome, Firefox, Safari (latest versions)
- **Themes**: Light and Dark mode

## Test Data Schema

```json
{
  "anomaly_type": "string",
  "risk_score": "float (0.0-100.0)",
  "risk_level": "string (Low/Medium/High)",
  "key_signals": [
    {
      "signal_name": "string",
      "value": "float",
      "unit": "string",
      "reference_range": "string",
      "status": "string (ABNORMAL/NORMAL)"
    }
  ],
  "diagnostic_report": {
    "anomalous_behaviour": "string",
    "probable_cause": "string",
    "recommended_action": "string"
  },
  "trend_data": [
    {
      "time_index": "int",
      "risk_score": "float"
    }
  ]
}
```

## Test Cases

| Test ID | Test Area | Test Description | Preconditions | Test Steps | Expected Result | Pass/Fail |
|---------|-----------|------------------|---------------|------------|-----------------|-----------|
| TC-001 | Overview Page | Verify Overview Page renders correctly | Dashboard is running | 1. Launch dashboard<br>2. Observe Overview Page | Overview Page displays with header, theme toggle, and component cards | Pass |
| TC-002 | Overview Page | Verify risk card content | Dashboard shows multiple components | 1. Navigate to Overview Page<br>2. Examine each risk card | Each card displays: component name, risk level badge, risk score percentage, and "View Details" button | Pass |
| TC-003 | Risk Sorting | Verify High risk components appear first | Mock data contains High, Medium, and Low risk components | 1. Navigate to Overview Page<br>2. Observe card order | Cards are sorted: High risk first, then Medium, then Low | Pass |
| TC-004 | Risk Sorting | Verify sorting with all same risk level | Load ui_all_medium_risk.json | 1. Load ui_all_medium_risk.json<br>2. Navigate to Overview Page | All 3 Medium risk cards display correctly without errors |  |
| TC-005 | Risk Sorting | Verify sorting with mixed risk levels | Load ui_mixed_risk_levels.json | 1. Load ui_mixed_risk_levels.json<br>2. Navigate to Overview Page<br>3. Count cards in each section | High risk cards (2) appear first, Medium (3) in middle, Low (1) last |  |
| TC-006 | Navigation | Verify navigation to Detail Page | Overview Page is displayed | 1. Click "View Details" on any component card | Detail Page opens showing selected component details | Pass |
| TC-007 | Navigation | Verify navigation for each risk level | Components of all risk levels exist | 1. Click "View Details" on High risk card<br>2. Return and click Medium risk card<br>3. Return and click Low risk card | Detail Page opens correctly for each risk level | Pass |
| TC-008 | Detail Page | Verify Detail Page header | Detail Page is open | 1. Navigate to Detail Page<br>2. Observe header section | Header displays component name, risk level badge, and risk score gauge | Partial (Missing risk level badge) |
| TC-009 | Trend Chart | Verify trend chart renders | Component has trend_data | 1. Navigate to Detail Page<br>2. Locate trend chart section | Plotly interactive chart displays with time on x-axis and risk score on y-axis | Pass |
| TC-010 | Trend Chart | Verify trend chart interactivity | Trend chart is displayed | 1. Hover over data points<br>2. Try zoom/pan controls | Tooltip shows time and risk score; zoom and pan work correctly | Pass |
| TC-011 | Key Signals | Verify Key Signals section renders | Component has key_signals data | 1. Navigate to Detail Page<br>2. Locate Key Signals section | Section displays table with columns: Signal Name, Value, Unit, Reference Range, Status | Pass |
| TC-012 | Key Signals | Verify ABNORMAL signals appear first | Component has both ABNORMAL and NORMAL signals | 1. Navigate to Detail Page<br>2. Observe Key Signals order | ABNORMAL signals are listed before NORMAL signals | Pass |
| TC-013 | Key Signals | Verify signal status badges | Component has mixed signal statuses | 1. Navigate to Detail Page<br>2. Examine status badges | ABNORMAL badges are red/warning color; NORMAL badges are green/success color | Pass |
| TC-014 | Diagnostic Report | Verify Diagnostic Report section | Detail Page is open | 1. Navigate to Detail Page<br>2. Locate Diagnostic Report section | Section displays three subsections: "What's Happening", "Why This Matters", "What You Should Do" | Pass |
| TC-015 | Diagnostic Report | Verify report content display | Component has diagnostic_report data | 1. Navigate to Detail Page<br>2. Read each report subsection | "What's Happening" shows anomalous_behaviour; "Why This Matters" shows probable_cause; "What You Should Do" shows recommended_action | Pass |
| TC-016 | Edge Case | Verify empty component list handling | Load ui_empty_data.json | 1. Load ui_empty_data.json<br>2. Navigate to Overview Page | Page displays message "No components to display" or similar |  |
| TC-017 | Edge Case | Verify single component display | Load ui_single_component.json | 1. Load ui_single_component.json<br>2. Navigate to Overview Page | Single card displays correctly without layout issues |  |
| TC-018 | Edge Case | Verify missing optional fields | Load ui_missing_fields_data.json | 1. Load ui_missing_fields_data.json<br>2. Navigate to Detail Page for each component | Page displays placeholder text for missing fields without errors |  |
| TC-019 | Edge Case | Verify missing trend_data | Load ui_no_trend_data.json | 1. Load ui_no_trend_data.json<br>2. Navigate to Detail Page | Trend chart section shows "No trend data available" or is hidden |  |
| TC-020 | Edge Case | Verify missing key_signals | Load ui_no_key_signals.json | 1. Load ui_no_key_signals.json<br>2. Navigate to Detail Page | Key Signals section shows "No signals available" or is hidden |  |
| TC-021 | Theme | Verify light theme rendering | Dashboard is in light mode | 1. Ensure light theme is active<br>2. Navigate through all pages | All elements use light theme colors: white background, dark text | Pass |
| TC-022 | Theme | Verify dark theme rendering | Dashboard is in dark mode | 1. Toggle to dark theme<br>2. Navigate through all pages | All elements use dark theme colors: dark background, light text | Pass |
| TC-023 | Theme | Verify theme toggle functionality | Dashboard is running | 1. Click theme toggle button<br>2. Observe color changes<br>3. Toggle again | Theme switches between light and dark; all elements update correctly | Pass |
| TC-024 | Theme | Verify theme persistence | Theme has been changed | 1. Change theme<br>2. Navigate to Detail Page<br>3. Return to Overview | Theme remains consistent across page navigation | Pass |
| TC-025 | Responsive | Verify layout on different screen sizes | Dashboard is running | 1. Resize browser window to mobile size<br>2. Resize to tablet size<br>3. Resize to desktop size | Layout adapts appropriately; no horizontal scrolling; cards stack on mobile | Partial (Mobile: Key Signals table overflow, Confidence badge spacing issue) |
| TC-026 | Local Run Help | Verify local run button appears on the upload interface | Dashboard is running on Overview or Landing page | 1. Open the upload page<br>2. Locate the CSV upload card<br>3. Check the top-right How to Run Locally button | Upload card stays centered and the How to Run Locally button is visible in the top-right area | Pass |
| TC-027 | Local Run Help | Verify full local setup guide page and copy commands | How to Run Locally button is visible | 1. Click How to Run Locally<br>2. Confirm the full guide page opens<br>3. Check the four setup steps<br>4. Review the command blocks<br>5. Click Back to Upload | The page looks similar to the What-If page, setup steps and command blocks are readable, and Back to Upload returns to the upload interface | Pass |
| TC-028 | Local Run Help | Verify local setup guide does not affect upload behaviour | Returned from How to Run Locally page | 1. Click Back to Upload<br>2. Select a CSV file<br>3. Click Run Analysis | Upload controls still work normally; Run Analysis still changes to Analysing while the app is processing | Pass |

## Test Execution Notes

### Prerequisites
- Streamlit installed (`pip install streamlit`)
- Dashboard dependencies installed (`pip install -r requirements.txt`)
- Mock data files available in `dashboard/tests/` directory

### How to Run Dashboard
```bash
streamlit run dashboard/app.py
```

### Test Data Files
- `dashboard/tests/ui_required_data.json` - Complete test data with current anomaly types
- `dashboard/tests/ui_missing_fields_data.json` - Test data with missing optional fields
- `dashboard/tests/ui_all_medium_risk.json` - Components with Medium risk level
- `dashboard/tests/ui_mixed_risk_levels.json` - Mixed risk levels (2 High, 3 Medium, 1 Low)
- `dashboard/tests/ui_empty_data.json` - Empty component array
- `dashboard/tests/ui_single_component.json` - Single component data
- `dashboard/tests/ui_no_trend_data.json` - Components with empty risk_history array
- `dashboard/tests/ui_no_key_signals.json` - Components with empty key_signals array

## Pass/Fail Criteria

- **Pass**: Test case meets all expected results without errors or visual issues
- **Fail**: Test case produces errors, incorrect display, or does not meet expected results
- **Blocked**: Test cannot be executed due to environment or dependency issues
- **N/A**: Test case not applicable to current configuration

## Defect Reporting

When a test fails, report defects with:
1. Test ID
2. Steps to reproduce
3. Expected vs. actual result
4. Screenshots (if applicable)
5. Browser and OS information
6. Console errors (if any)

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Test Author | | | |
| Reviewer | | | |
| Approver | | | |

---

**Related Tasks:**
- GL-97: Dashboard Testing (Parent)
- GL-98: Create Manual Test Plan (Current)
