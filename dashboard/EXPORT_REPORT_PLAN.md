# Export Report Plan - GL-343

This note confirms the Detail Page entry point and the data fields for
Task 6 PDF / CSV export.

## Export Entry

The export buttons should be added on the component Detail Page.

Recommended code location:

- File: `dashboard/pages/detail.py`
- Function: `render_component_detail()`
- Position: after the component title and before the Failure Prediction
  section

This position keeps the export action easy to find and gives the export code
direct access to `component_data`, `display_name`, `dark_mode`, and `tokens`.

Recommended UI:

- `Export PDF`
- `Export CSV`

Both buttons should use `st.download_button` so the feature works in local
Streamlit without an external service.

## PDF Export Fields

The PDF should contain the complete component diagnostic report.

| PDF section | Source field | Notes |
|---|---|---|
| Component name | `component` | Convert to display name with `COMPONENT_DISPLAY_NAMES`. |
| Risk score | `risk_score` | Format as a percentage. |
| Risk level | `risk_level` | Use `Unknown` if missing. |
| Timestamp | `timestamp` | Format ISO timestamp when possible. |
| Key signals table | `key_signals` | Include feature, value, unit, reference range, and status. |
| What's Happening | `anomaly_description` | Use existing report text. |
| Why This Matters | `possible_cause` | Use existing report text. |
| What You Should Do | `recommended_action` | Render list items as separate lines. |

Optional fields that may be included later:

- `prediction_confidence`
- `estimated_failure_probability`
- `estimated_cycles_to_failure`
- `notes`

These optional fields are already available in the dashboard data, but they are
not required by Task 6 export content.

## CSV Export Fields

The CSV should contain only the key signals table.

| CSV column | Source field | Notes |
|---|---|---|
| `feature` | `key_signals[].feature` | Keep the interface feature name. |
| `value` | `key_signals[].value` | Keep numeric value when present. |
| `unit` | `key_signals[].unit` | Empty string if missing. |
| `reference_range` | `key_signals[].reference_range` | Format as `lower-upper`. |
| `status` | calculated | `ABNORMAL` if value is outside reference range, otherwise `NORMAL`. |

## Fallback Rules

- If `key_signals` is empty, CSV export should still download a file with the
  header row.
- If a report text field is missing, PDF export should show `Not available`.
- If `risk_level` is missing, use `Unknown`.
- If `timestamp` is missing, use `Not available`.
- Export generation should not stop the Detail Page from loading.

## Confirmed Current Data Source

The Detail Page receives one component report as `component_data`.

The fields are loaded through:

1. `dashboard/data_loader.py`
2. `dashboard/data_store.py`
3. `dashboard/pages/detail.py`

The current dashboard test data already contains the required Task 6 fields.
