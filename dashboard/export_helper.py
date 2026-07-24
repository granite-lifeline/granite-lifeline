"""Helpers for preparing dashboard report export data."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

try:
    from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES
    from dashboard.failure_prediction import (
        format_failure_prediction_text,
        get_data_quality_notes,
        is_missing_value,
    )
except ImportError:  # Streamlit runs pages from inside dashboard/
    from anomaly_display import COMPONENT_DISPLAY_NAMES
    from failure_prediction import (
        format_failure_prediction_text,
        get_data_quality_notes,
        is_missing_value,
    )


NOT_AVAILABLE = "Not available"

EXPORT_SECTION_LABELS = {
    "summary": "Summary",
    "failure_prediction": "Failure Prediction",
    "key_signals": "Key Signals",
    "diagnostic_report": "Diagnostic Report",
    "data_quality_notes": "Data Quality Notes",
}

DEFAULT_EXPORT_SECTIONS = (
    "summary",
    "key_signals",
    "diagnostic_report",
)

ALL_EXPORT_SECTIONS = tuple(EXPORT_SECTION_LABELS.keys())

CSV_COLUMNS = (
    "feature",
    "value",
    "unit",
    "reference_range",
    "status",
)

SIGNAL_DISPLAY_NAMES = {
    "coolant_temp": "Coolant Temperature",
    "ect_rate_180s": "Coolant Temperature Rise Rate",
    "ect_start": "Coolant Temperature at Engine Start",
    "aat_start": "Ambient Temperature at Engine Start",
    "maf_integral_180s": "MAF Integral",
    "intake_temp": "Intake Air Temperature",
    "intake_temp_stability": "Intake Temperature Stability",
    "intake_ambient_delta": "Intake-Ambient Temperature Difference",
    "speed_density_maf_residual": "Speed-Density MAF Residual",
    "pedal_mapping_residual": "Pedal Mapping Residual",
    "pedal_slope": "Pedal Demand Rate",
    "accel_pedal_channel_delta": "Pedal Channel Difference",
    "map_range_60s": "MAP Range",
    "maf": "Mass Airflow",
    "map": "Intake Pressure",
    "accel_pedal_d": "Pedal Sensor D",
    "accel_pedal_e": "Pedal Sensor E",
}


def get_export_section_options() -> List[Dict[str, str]]:
    """Return section choices for the future export filter popup."""
    options = []
    for section_key in ALL_EXPORT_SECTIONS:
        options.append({
            "key": section_key,
            "label": EXPORT_SECTION_LABELS[section_key],
        })
    return options


def clean_export_sections(
    selected_sections: Optional[Iterable[str]] = None,
) -> List[str]:
    """Keep known section keys in dashboard display order."""
    wanted = (
        list(selected_sections)
        if selected_sections is not None else list(DEFAULT_EXPORT_SECTIONS)
    )
    clean_sections = []
    for section_key in ALL_EXPORT_SECTIONS:
        if section_key in wanted:
            clean_sections.append(section_key)
    return clean_sections


def clean_csv_columns(
    selected_columns: Optional[Iterable[str]] = None,
) -> List[str]:
    """Keep known CSV column keys in the required export order."""
    wanted = (
        list(selected_columns)
        if selected_columns is not None else list(CSV_COLUMNS)
    )
    clean_columns = []
    for column_key in CSV_COLUMNS:
        if column_key in wanted:
            clean_columns.append(column_key)
    return clean_columns or list(CSV_COLUMNS)


def format_plain_value(value: Any) -> str:
    """Format a value for export text."""
    if is_missing_value(value):
        return NOT_AVAILABLE
    return str(value)


def format_percent(value: Any) -> str:
    """Format a 0-1 score as a whole-number percentage."""
    if is_missing_value(value):
        return NOT_AVAILABLE
    try:
        return f"{int(round(float(value) * 100))}%"
    except (TypeError, ValueError):
        return NOT_AVAILABLE


def format_timestamp(value: Any) -> str:
    """Format an ISO timestamp for the exported report."""
    if is_missing_value(value):
        return NOT_AVAILABLE
    text = str(value)
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def format_reference_range(reference_range: Any) -> str:
    """Format a two-value reference range for CSV and PDF exports."""
    if (
        not isinstance(reference_range, list)
        or len(reference_range) != 2
    ):
        return NOT_AVAILABLE
    return f"{reference_range[0]}-{reference_range[1]}"


def get_signal_status(signal: Dict[str, Any]) -> str:
    """Return ABNORMAL, NORMAL, or Unknown for one key signal."""
    value = signal.get("value")
    reference_range = signal.get("reference_range")
    if (
        is_missing_value(value)
        or not isinstance(reference_range, list)
        or len(reference_range) != 2
    ):
        return "Unknown"

    try:
        signal_value = float(value)
        lo = float(reference_range[0])
        hi = float(reference_range[1])
    except (TypeError, ValueError):
        return "Unknown"

    if signal_value < lo or signal_value > hi:
        return "ABNORMAL"
    return "NORMAL"


def build_key_signal_rows(
    component_data: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build export-ready rows for the key signals table."""
    rows = []
    for signal in component_data.get("key_signals") or []:
        feature = format_plain_value(signal.get("feature"))
        rows.append({
            "feature": feature,
            "display_name": SIGNAL_DISPLAY_NAMES.get(feature, feature),
            "value": format_plain_value(signal.get("value")),
            "unit": format_plain_value(signal.get("unit")),
            "reference_range": format_reference_range(
                signal.get("reference_range")
            ),
            "status": get_signal_status(signal),
        })
    return rows


def build_key_signals_csv(
    component_data: Dict[str, Any],
    selected_columns: Optional[Iterable[str]] = None,
) -> str:
    """Build CSV text for the key signals table."""
    columns = clean_csv_columns(selected_columns)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction="ignore",
        lineterminator="\n",
    )

    writer.writeheader()
    for row in build_key_signal_rows(component_data):
        writer.writerow(row)

    return output.getvalue()


def build_key_signals_csv_bytes(
    component_data: Dict[str, Any],
    selected_columns: Optional[Iterable[str]] = None,
) -> bytes:
    """Build UTF-8 CSV bytes for Streamlit download_button."""
    return build_key_signals_csv(
        component_data,
        selected_columns,
    ).encode("utf-8")


def clean_file_name_part(value: Any) -> str:
    """Make one small filename part from report data."""
    text = format_plain_value(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "report"


def build_csv_file_name(component_data: Dict[str, Any]) -> str:
    """Build a simple CSV filename for the current component report."""
    component = clean_file_name_part(component_data.get("component"))
    timestamp = clean_file_name_part(component_data.get("timestamp"))
    if timestamp == "not_available":
        return f"{component}_key_signals.csv"
    return f"{component}_{timestamp}_key_signals.csv"


def build_summary(component_data: Dict[str, Any]) -> Dict[str, str]:
    """Build the top summary section for export."""
    component = component_data.get("component")
    return {
        "component": format_plain_value(component),
        "component_name": COMPONENT_DISPLAY_NAMES.get(
            component, format_plain_value(component)
        ),
        "risk_score": format_percent(component_data.get("risk_score")),
        "risk_level": format_plain_value(component_data.get("risk_level")),
        "timestamp": format_timestamp(component_data.get("timestamp")),
    }


def build_diagnostic_report(component_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build the three-section diagnostic report for export."""
    actions = component_data.get("recommended_action")
    if isinstance(actions, list):
        clean_actions = [
            str(action).strip() for action in actions if str(action).strip()
        ]
    elif is_missing_value(actions):
        clean_actions = []
    else:
        clean_actions = [str(actions)]

    return {
        "anomaly_description": format_plain_value(
            component_data.get("anomaly_description")
        ),
        "possible_cause": format_plain_value(
            component_data.get("possible_cause")
        ),
        "recommended_action": clean_actions,
    }


def build_export_data(
    component_data: Dict[str, Any],
    selected_sections: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Build filtered export data for PDF / CSV export.

    The future popup can pass selected section keys from
    `get_export_section_options()`. Unknown section names are ignored.
    """
    sections = clean_export_sections(selected_sections)
    export_data: Dict[str, Any] = {"sections": sections}

    if "summary" in sections:
        export_data["summary"] = build_summary(component_data)

    if "failure_prediction" in sections:
        text, has_value = format_failure_prediction_text(component_data)
        export_data["failure_prediction"] = {
            "text": text,
            "has_value": has_value,
        }

    if "key_signals" in sections:
        export_data["key_signals"] = build_key_signal_rows(component_data)

    if "diagnostic_report" in sections:
        export_data["diagnostic_report"] = build_diagnostic_report(
            component_data
        )

    if "data_quality_notes" in sections:
        export_data["data_quality_notes"] = get_data_quality_notes(
            component_data
        )

    return export_data
