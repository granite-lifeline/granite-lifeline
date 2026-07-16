# UI Required Data

This document lists the data that should be uploaded for the dashboard UI.

The fields come from `docs/INTERFACE.md`. Do not add extra interface fields for
the UI upload payload.

## Required Payload Shape

The dashboard should receive a list of report objects. Each object represents
one monitored component.

```json
[
  {
    "timestamp": "2026-06-16T12:00:00Z",
    "risk_score": 0.86,
    "risk_level": "High",
    "component": "cooling_system_stress",
    "prediction_confidence": 0.88,
    "key_signals": [
      {
        "feature": "coolant_temp",
        "value": 104.0,
        "unit": "C",
        "reference_range": [90.0, 95.0]
      },
      {
        "feature": "coolant_slope",
        "value": 3.4,
        "unit": "C/min",
        "reference_range": [0.0, 2.0]
      }
    ],
    "risk_history": [
      {
        "timestamp": "2026-06-15T12:00:00Z",
        "risk_score": 0.64
      },
      {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86
      }
    ],
    "anomaly_description": "The coolant temperature is above its reference range and is rising faster than expected. High risk means the vehicle may need prompt attention.",
    "possible_cause": "This could be related to cooling system stress, such as low coolant, radiator problems, or water pump degradation.",
    "recommended_action": [
      "Avoid heavy driving if it is safe to do so.",
      "Check the coolant level when the engine is cool.",
      "Ask a mechanic to inspect the cooling system as soon as possible."
    ],
    "estimated_cycles_to_failure": 15,
    "estimated_failure_probability": 0.72,
    "notes": [
      "Coolant readings include repaired sensor gaps from the latest drive cycle.",
      "Failure estimate may become more stable after more drive cycles."
    ]
  },
  {
    "timestamp": "2026-06-16T11:00:00Z",
    "risk_score": 0.61,
    "risk_level": "Medium",
    "component": "air_intake_maf_anomaly",
    "prediction_confidence": 0.76,
    "key_signals": [
      {
        "feature": "maf",
        "value": 28.5,
        "unit": "g/s",
        "reference_range": [10.0, 22.0]
      },
      {
        "feature": "map",
        "value": 82.0,
        "unit": "kPa",
        "reference_range": [60.0, 90.0]
      }
    ],
    "risk_history": [
      {
        "timestamp": "2026-06-15T11:00:00Z",
        "risk_score": 0.48
      },
      {
        "timestamp": "2026-06-16T11:00:00Z",
        "risk_score": 0.61
      }
    ],
    "anomaly_description": "The airflow reading is higher than its reference range, while the intake pressure reading is still inside its reference range. Medium risk means the vehicle should be checked soon, but it is not an immediate emergency.",
    "possible_cause": "This may indicate an airflow sensor issue, a dirty air filter, or an air intake leak. The result is not a confirmed fault.",
    "recommended_action": [
      "Ask a mechanic to inspect the air intake system soon.",
      "Check whether the air filter needs cleaning or replacement.",
      "Keep watching for rough idling, poor acceleration, or warning lights."
    ],
    "estimated_cycles_to_failure": null,
    "estimated_failure_probability": null,
    "notes": []
  },
  {
    "timestamp": "2026-06-16T10:00:00Z",
    "risk_score": 0.22,
    "risk_level": "Low",
    "component": "accelerator_pedal_sensor",
    "prediction_confidence": 0.62,
    "key_signals": [
      {
        "feature": "accel_pedal_d",
        "value": 35.0,
        "unit": "%",
        "reference_range": [0.0, 100.0]
      },
      {
        "feature": "accel_pedal_e",
        "value": 37.5,
        "unit": "%",
        "reference_range": [0.0, 100.0]
      }
    ],
    "risk_history": [
      {
        "timestamp": "2026-06-15T10:00:00Z",
        "risk_score": 0.20
      },
      {
        "timestamp": "2026-06-16T10:00:00Z",
        "risk_score": 0.22
      }
    ],
    "anomaly_description": "The accelerator pedal sensor reading does not show a strong abnormal pattern right now. Low risk means the issue does not look urgent.",
    "possible_cause": "This could be related to normal sensor movement or a short sensor delay. The current data does not strongly suggest a confirmed fault.",
    "recommended_action": [
      "Continue monitoring the dashboard.",
      "If the warning appears repeatedly, ask a mechanic to check the pedal sensor."
    ],
    "estimated_cycles_to_failure": null,
    "estimated_failure_probability": null,
    "notes": []
  }
]
```

## Field Notes

| Field | UI usage |
|---|---|
| `timestamp` | Shows when the report was last checked. |
| `risk_score` | Shows the risk percentage. |
| `risk_level` | Shows urgency as Low, Medium, or High. |
| `component` | Tells the UI which vehicle component the report belongs to. |
| `prediction_confidence` | Shows model confidence as supporting information. |
| `key_signals` | Shows the signals contributing to risk. |
| `risk_history` | Draws the risk trend chart over time. |
| `anomaly_description` | Explains what is happening. |
| `possible_cause` | Explains the likely cause. |
| `recommended_action` | Shows suggested actions as a list. |
| `estimated_cycles_to_failure` | Shows the number of trips used in the failure prediction card. |
| `estimated_failure_probability` | Shows the failure probability in the failure prediction card. |
| `notes` | Shows Data Quality Notes when the list is not empty. |

## Important Notes

- Do not upload `display_name`; the UI can map it from `component`.
- Do not upload `trend`; the UI can calculate trend values from
  `risk_history`.
- Do not upload fields that are not listed in `docs/INTERFACE.md`.
