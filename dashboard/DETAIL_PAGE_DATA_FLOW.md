# Detail Page Data Flow

Task: GL-277 Inspect Existing Detail Page Data Flow

## Summary

The detail page already receives dashboard-ready report data from
`dashboard/data_loader.py`. The loader reads a JSON list from
`dashboard/tests/ui_required_data.json`, converts it to a dictionary keyed by
`component`, and `dashboard/app.py` uses that dictionary for both the overview
cards and detail page.

The fields needed by the next Failure Prediction UI tasks are already present
in the test data:

- `estimated_failure_probability`
- `estimated_cycles_to_failure`
- `notes`

The failure prediction fields and data quality notes are loaded and rendered
by the detail page. Empty notes lists render nothing.

## Current Flow

```text
dashboard/tests/ui_required_data.json
    -> dashboard.data_loader.load_report_data()
    -> dashboard.data_loader.convert_to_component_dict()
    -> dashboard.data_loader.load_dashboard_data()
    -> dashboard.app.REPORT_DATA
    -> dashboard.app.MOCK_DATA
    -> show_overview_page()
    -> selected_component in st.session_state
    -> show_detail_page()
    -> render_component_detail(component_data, dark_mode, tokens)
```

## Entry Points

| File | Role |
|---|---|
| `dashboard/tests/ui_required_data.json` | Example Report Layer output used by the dashboard. |
| `dashboard/data_loader.py` | Loads JSON and groups reports by `component`. |
| `dashboard/app.py` | Loads `REPORT_DATA`, stores selected component in Streamlit session state, and renders the detail page. |
| `tests/test_data_loader.py` | Checks the loader and interface fields. |

## Detail Page Field Usage

| Field | Current use in detail page |
|---|---|
| `component` | Selects the detail page data and maps display name/icon. |
| `risk_level` | Styles the top risk card and warning state. |
| `risk_score` | Shows the main risk percentage and progress gauge. |
| `prediction_confidence` | Shows the confidence badge beside Diagnostic Report. |
| `risk_history` | Builds the risk trend chart. |
| `key_signals` | Builds the Key Signals section. |
| `anomaly_description` | Shows the "What's Happening" report section. |
| `possible_cause` | Shows the "Why This Matters" report section. |
| `recommended_action` | Shows the "What You Should Do" action list. |
| `estimated_failure_probability` | Shows the Failure Prediction card when paired with cycles. |
| `estimated_cycles_to_failure` | Shows the Failure Prediction card when paired with probability. |
| `notes` | Shows Data Quality Notes below the Failure Prediction card when non-empty. |

## Existing Fallbacks

- If the test data file cannot be loaded, `app.py` shows a Streamlit error and
  uses an empty dictionary.
- Empty `REPORT_DATA` is respected by the overview page instead of forcing the
  old fallback mock data.
- Missing detail sections are checked inside `render_component_detail()`.
- Missing or short `risk_history` shows an alert message instead of drawing a
  broken chart.
- Missing `key_signals` shows a missing-data state.
- Missing report text falls back to "Pending Granite LLM report generation..."
- Missing, null, or blank failure prediction fields show the pending
  placeholder instead of an empty card.

## Notes For Next Tasks

GL-278 renders the Failure Prediction card directly under Diagnostic Report
using:

- `estimated_failure_probability`
- `estimated_cycles_to_failure`

Recommended display rules:

- Has value: show something like `72% probability of failure within the next 15 trips`.
- Null value: show muted placeholder text:
  `Failure probability estimate pending — awaiting more drive cycles`.
- If only one of `estimated_failure_probability` or
  `estimated_cycles_to_failure` is missing, use the same placeholder.

GL-280 renders the Notes area directly under the Failure Prediction card
using:

- `notes`

Recommended display rules:

- Non-empty list: show "Data Quality Notes" with an info icon and muted text.
- Empty list: render nothing.
