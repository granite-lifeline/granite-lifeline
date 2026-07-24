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

## Export Data Helper

GL-344 adds `dashboard/export_helper.py`.

The helper prepares filtered export data before the CSV or PDF file is built.
This supports the planned popup flow:

1. User clicks `Export PDF` or `Export CSV`.
2. Dashboard opens a small filter popup.
3. User chooses sections to export.
4. The selected section keys are passed to `build_export_data()`.

Current supported section keys:

- `summary`
- `failure_prediction`
- `key_signals`
- `diagnostic_report`
- `data_quality_notes`

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

GL-345 adds CSV generation helpers in `dashboard/export_helper.py`:

- `build_key_signals_csv()` returns CSV text.
- `build_key_signals_csv_bytes()` returns UTF-8 bytes for
  `st.download_button`.
- `build_csv_file_name()` returns a stable download filename.

The helper uses only the Python standard library, so it has no external
service or system-level dependency.

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
