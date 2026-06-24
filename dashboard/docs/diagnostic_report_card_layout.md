# Diagnostic Report Card Layout

Ticket: GL-62

User story:
As a vehicle owner, I want the diagnostic explanation and the urgency level
to appear together in a single, uncluttered view, so that I can quickly grasp
both what is happening and how urgent it is without navigating between
sections.

## Goal

Create one clear report card for Dashboard. The card should show the current
diagnostic explanation, urgency level, confidence, possible cause, and actions
in the same view.

This layout uses the fields from `ReportLayerOutput`:

- `component`
- `risk_level`
- `prediction_confidence`
- `anomaly_description`
- `possible_cause`
- `recommended_action`

## Desktop Wireframe

```text
+--------------------------------------------------------------+
| Diagnostic Report                              [High risk]    |
| Cooling System                                  88% confidence|
+--------------------------------------------------------------+
| What's happening                                             |
| The coolant temperature is above its reference range and is   |
| rising faster than expected. High risk means the vehicle may  |
| need prompt attention.                                       |
|                                                              |
| Possible cause                                               |
| This could be related to cooling system stress, such as low   |
| coolant, radiator problems, or water pump degradation.        |
|                                                              |
| Recommended actions                                          |
| 1. Avoid heavy driving if it is safe to do so.                |
| 2. Check the coolant level when the engine is cool.           |
| 3. Ask a mechanic to inspect the cooling system soon.         |
+--------------------------------------------------------------+
```

## Layout Rules

### Header area

The top of the card should show:

- title: `Diagnostic Report`
- component name from `component`
- risk badge from `risk_level`
- confidence text from `prediction_confidence`

Example:

```text
Diagnostic Report
Cooling System
High risk
Prediction confidence: 88%
```

### Main content area

The body of the card should have three sections:

```text
What's happening
anomaly_description

Possible cause
possible_cause

Recommended actions
recommended_action as a clear list
```

Do not show raw JSON in the dashboard.

### Recommended actions

`recommended_action` is an array of strings, so it should be displayed as a
list. It should not be shown as one long paragraph.

Good:

```text
- Avoid heavy driving if it is safe to do so.
- Check the coolant level when the engine is cool.
- Ask a mechanic to inspect the cooling system soon.
```

Bad:

```text
["Avoid heavy driving", "Check coolant level"]
```

## Risk Level Visual Style

The risk badge should make urgency easy to understand.

| risk_level | Badge text | Visual emphasis |
|---|---|---|
| Low | Low risk | calm green style |
| Medium | Medium risk | warning orange style |
| High | High risk | strong red style |
| missing | Risk unavailable | neutral grey style |

When `risk_level` is `High`, the whole report card should also be visually
stronger than Medium or Low. For example:

- red badge
- stronger border color
- slightly stronger header background

## Fallback Display

If a field is missing or empty, the card should show placeholder text instead
of breaking.

| Field | Placeholder |
|---|---|
| `risk_level` | Risk level unavailable |
| `prediction_confidence` | Prediction confidence unavailable |
| `anomaly_description` | Anomaly description is not available yet. |
| `possible_cause` | Possible cause is not available yet. |
| `recommended_action` | Recommended actions are not available yet. |

## Streamlit Implementation Plan

This layout can be implemented later as one helper function:

```python
def show_diagnostic_report_card(report):
    risk_level = get_text(report, "risk_level", "Risk level unavailable")
    confidence = get_confidence_text(report)

    st.markdown("### Diagnostic Report")
    show_risk_badge(risk_level)
    st.caption(confidence)

    st.subheader("What's happening")
    st.write(get_text(
        report,
        "anomaly_description",
        "Anomaly description is not available yet.",
    ))

    st.subheader("Possible cause")
    st.write(get_text(
        report,
        "possible_cause",
        "Possible cause is not available yet.",
    ))

    st.subheader("Recommended actions")
    actions = report.get("recommended_action", [])
    if not actions:
        actions = ["Recommended actions are not available yet."]
    for action in actions:
        st.write("- " + action)
```

## Acceptance Criteria Mapping

- All diagnostic text and urgency are shown in one card.
- `risk_level` is visible in the card header.
- High risk has stronger visual emphasis than Medium or Low.
- `recommended_action` is displayed as a list.
- `prediction_confidence` is shown as a supporting indicator.
- Missing fields use placeholder text.

