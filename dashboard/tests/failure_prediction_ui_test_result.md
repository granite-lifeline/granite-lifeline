# Failure Prediction UI Test Result

Task: GL-288 Test UI States and Themes

## Scope

This test result covers the updated Failure Prediction summary banner, its
Data Quality Notes content card, and the light/dark theme assumptions used on
the component detail page.

## Checked States

| State | Test data | Expected result |
|---|---|---|
| Has value | `cooling_degradation` in `ui_required_data.json` | Shows `72%` and `15 trips` as highlighted values in the summary banner. |
| Null value | `air_intake_maf_anomaly` in `ui_required_data.json` | Shows the pending placeholder in a compact info notice style. |
| Notes non-empty | `cooling_degradation` in `ui_required_data.json` | Shows Data Quality Notes as a glass content card with accent icon, title divider, and normal text. |
| Notes empty | `air_intake_maf_anomaly` in `ui_required_data.json` | Notes area renders nothing. |
| Banner placement | `dashboard/app.py` | Incomplete Data appears before Failure Prediction; Failure Prediction appears before Risk Score. |
| Icon uniqueness | `dashboard/app.py` | Failure Prediction uses alert-triangle, while Risk Score Trend uses trending-up. |
| Light/dark theme tokens | `dashboard/app.py` | Both themes include glass card, text, accent, and shadow tokens. |

## Automated Verification

```bash
python3 -m pytest tests/test_failure_prediction_ui_states.py -q
```

Expected result:

```text
8 passed
```

## Notes

The tests focus on data-driven UI states and theme token coverage. Manual visual
checking is still useful for final presentation screenshots, but the automated
tests prevent the main state and theme assumptions from being accidentally
removed.
