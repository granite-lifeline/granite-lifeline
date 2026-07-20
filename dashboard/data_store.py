"""Data loading, caching, and component list helpers.

All data-access logic lives here.  The rest of the dashboard imports
``get_mock_data()`` and ``get_data_source()`` rather than touching
globals directly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from data_loader import load_dashboard_data
from anomaly_display import (
    GROUND_KNOWLEDGE_ANOMALY_TYPES,
    LEGACY_COMPONENT_ALIASES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_PRIORITY: dict[str, int] = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
    "Unknown": 3,
}

_DEFAULT_TEST_FILE = "dashboard/tests/ui_required_data.json"


# ---------------------------------------------------------------------------
# Cached loader  (Ollama / report_generator called at most once per process)
# ---------------------------------------------------------------------------

@st.cache_resource
def _load_cached(file_path: str) -> dict:
    """Load dashboard data exactly once; return {} on any failure."""
    try:
        return load_dashboard_data(file_path)
    except Exception:
        return {}


def _build_data_views() -> tuple[dict, dict]:
    """Return (component_data, data_source) stripping the sentinel key."""
    file_path = os.getenv("DASHBOARD_TEST_DATA", _DEFAULT_TEST_FILE)
    raw = _load_cached(file_path)
    if not isinstance(raw, dict):
        return {}, {}
    ds = dict(raw.get("_data_source", {}))
    data = {k: v for k, v in raw.items() if k != "_data_source"}
    return data, ds


# Module-level views — evaluated once when the module is first imported.
_REPORT_DATA, _DATA_SOURCE = _build_data_views()


# ---------------------------------------------------------------------------
# Fallback mock data  (inline → JSON round-trip kept in memory)
# ---------------------------------------------------------------------------

_MOCK_FALLBACK_JSON = json.dumps({
    "cooling_degradation": {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 104.0,
                "unit": "\u00b0C",
                "reference_range": [90.0, 95.0],
            },
            {
                "feature": "ect_rate_180s",
                "value": 3.4,
                "unit": "\u00b0C/min",
                "reference_range": [0.0, 0.5],
            },
        ],
        "risk_history": [
            {"timestamp": "2026-06-15T08:00:00Z", "risk_score": 0.45},
            {"timestamp": "2026-06-15T12:00:00Z", "risk_score": 0.52},
            {"timestamp": "2026-06-15T16:00:00Z", "risk_score": 0.61},
            {"timestamp": "2026-06-16T08:00:00Z", "risk_score": 0.70},
            {"timestamp": "2026-06-16T12:00:00Z", "risk_score": 0.86},
        ],
        "anomaly_description": (
            "The coolant temperature is above its reference range and is "
            "rising faster than expected. High risk means the vehicle may "
            "need prompt attention."
        ),
        "possible_cause": (
            "This could be related to cooling system degradation, such as low "
            "coolant, radiator problems, or water pump degradation."
        ),
        "recommended_action": [
            "Avoid heavy driving if it is safe to do so.",
            "Check the coolant level when the engine is cool.",
            "Ask a mechanic to inspect the cooling system as soon as "
            "possible.",
        ],
    },
    "air_intake_maf_anomaly": {
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
                "reference_range": [10.0, 22.0],
            },
            {
                "feature": "map",
                "value": 82.0,
                "unit": "kPa",
                "reference_range": [60.0, 90.0],
            },
        ],
        "risk_history": [
            {"timestamp": "2026-06-15T07:00:00Z", "risk_score": 0.30},
            {"timestamp": "2026-06-15T11:00:00Z", "risk_score": 0.35},
            {"timestamp": "2026-06-15T15:00:00Z", "risk_score": 0.40},
            {"timestamp": "2026-06-16T07:00:00Z", "risk_score": 0.48},
            {"timestamp": "2026-06-16T11:00:00Z", "risk_score": 0.61},
        ],
        "anomaly_description": (
            "The airflow reading is higher than its reference range, while "
            "the intake pressure reading is still inside its reference "
            "range. Medium risk means the vehicle should be checked soon."
        ),
        "possible_cause": (
            "This may indicate an airflow sensor issue, a dirty air "
            "filter, or an air intake leak."
        ),
        "recommended_action": [
            "Ask a mechanic to inspect the air intake system soon.",
            "Check whether the air filter needs cleaning or replacement.",
            "Keep watching for rough idling, poor acceleration, or "
            "warning lights.",
        ],
    },
    "accelerator_pedal_sensor": {
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
                "reference_range": [0.0, 100.0],
            },
            {
                "feature": "accel_pedal_e",
                "value": 37.5,
                "unit": "%",
                "reference_range": [0.0, 100.0],
            },
        ],
        "risk_history": [
            {"timestamp": "2026-06-15T06:00:00Z", "risk_score": 0.18},
            {"timestamp": "2026-06-15T10:00:00Z", "risk_score": 0.20},
            {"timestamp": "2026-06-15T14:00:00Z", "risk_score": 0.21},
            {"timestamp": "2026-06-16T06:00:00Z", "risk_score": 0.22},
            {"timestamp": "2026-06-16T10:00:00Z", "risk_score": 0.22},
        ],
        "anomaly_description": (
            "The accelerator pedal sensor reading does not show a strong "
            "abnormal pattern right now. Low risk means the issue does "
            "not look urgent."
        ),
        "possible_cause": (
            "This could be related to normal sensor movement or a short "
            "sensor delay."
        ),
        "recommended_action": [
            "Continue monitoring the dashboard.",
            "If the warning appears repeatedly, ask a mechanic to check "
            "the pedal sensor.",
        ],
    },
})

_MOCK_DATA_FALLBACK: dict = json.loads(_MOCK_FALLBACK_JSON)


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------

def get_mock_data() -> dict:
    """Return the active component data (real or mock)."""
    return _REPORT_DATA if _REPORT_DATA else _MOCK_DATA_FALLBACK


def get_data_source() -> dict:
    """Return the component → 'real'|'mock' source map."""
    data = get_mock_data()
    if not _DATA_SOURCE and data:
        return {k: "mock" for k in data}
    return _DATA_SOURCE


# ---------------------------------------------------------------------------
# Component list helpers
# ---------------------------------------------------------------------------

def make_overview_placeholder(component_key: str) -> dict:
    """Return a zeroed-out placeholder dict for a missing component."""
    return {
        "timestamp": "",
        "risk_score": 0.0,
        "risk_level": None,
        "component": component_key,
        "prediction_confidence": 0.0,
        "key_signals": [],
        "risk_history": None,
        "anomaly_description": "",
        "possible_cause": "",
        "recommended_action": [],
        "estimated_cycles_to_failure": None,
        "estimated_failure_probability": None,
        "notes": [],
    }


def get_overview_components() -> list[tuple[str, dict, bool]]:
    """Return sorted (key, data, is_placeholder) tuples for the overview."""
    mock_data = get_mock_data()
    real_components: dict[str, dict] = {}

    for raw_key, component_data in mock_data.items():
        component = component_data.get("component", raw_key)
        canonical_key = LEGACY_COMPONENT_ALIASES.get(component, component)
        if canonical_key in real_components and raw_key != canonical_key:
            continue
        entry = dict(component_data)
        entry["component"] = canonical_key
        real_components[canonical_key] = entry

    result: list[tuple[str, dict, bool]] = []
    for key in GROUND_KNOWLEDGE_ANOMALY_TYPES:
        if key in real_components:
            result.append((key, real_components[key], False))
        else:
            result.append((key, make_overview_placeholder(key), True))

    return sorted(
        result,
        key=lambda x: (
            RISK_PRIORITY.get(x[1].get("risk_level", "Unknown"), 3),
            -x[1].get("risk_score", 0),
        ),
    )
