# Failure Prediction UI Test Result

Task: GL-282 Test UI States and Themes

## Scope

This test result covers the Failure Prediction card and Data Quality Notes
area on the component detail page.

## Checked States

| State | Test data | Expected result |
|---|---|---|
| Has value | `cooling_system_stress` in `ui_required_data.json` | Shows `72% probability of failure within the next 15 trips`. |
| Null value | `air_intake_maf_anomaly` in `ui_required_data.json` | Shows pending placeholder text. |
| Notes non-empty | `cooling_system_stress` in `ui_required_data.json` | Shows Data Quality Notes with muted small text. |
| Notes empty | `air_intake_maf_anomaly` in `ui_required_data.json` | Notes area renders nothing. |
| Icon uniqueness | `dashboard/app.py` | Failure Prediction uses alert-triangle, while Risk Score Trend uses trending-up. |
| Light/dark theme tokens | `dashboard/app.py` | Both themes include glass card, text, accent, and shadow tokens. |

## Automated Verification

```bash
python3 -m pytest tests/test_failure_prediction_ui_states.py -q
```

Expected result:

```text
4 passed
```

## Notes

The tests focus on data-driven UI states and theme token coverage. Manual visual
checking is still useful for final presentation screenshots, but the automated
tests prevent the main state and theme assumptions from being accidentally
removed.
