"""Tests for dashboard export data helpers."""

import io
import sys
import zipfile
from pathlib import Path

import pytest

from dashboard.export_helper import (
    CSV_COLUMNS,
    DEFAULT_EXPORT_SECTIONS,
    NOT_AVAILABLE,
    PDF_TITLE,
    _get_pdf_styles,
    _get_reportlab_tools,
    build_csv_file_name,
    build_diagnostic_pdf_bytes,
    build_export_data,
    build_key_signal_rows,
    build_key_signals_csv,
    build_key_signals_csv_bytes,
    build_pdf_file_name,
    clean_csv_columns,
    clean_export_sections,
    format_percent,
    format_reference_range,
    get_export_section_options,
    get_signal_status,
)


def _sample_component():
    return {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_degradation",
        "prediction_confidence": 0.88,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 104.0,
                "unit": "C",
                "reference_range": [90.0, 95.0],
            },
            {
                "feature": "map",
                "value": 82.0,
                "unit": "kPa",
                "reference_range": [60.0, 90.0],
            },
        ],
        "anomaly_description": "Coolant temperature is high.",
        "possible_cause": "This may indicate cooling stress.",
        "recommended_action": [
            "Avoid heavy driving if it is safe.",
            "Ask a mechanic to inspect the cooling system.",
        ],
        "estimated_cycles_to_failure": 15,
        "estimated_failure_probability": 0.72,
        "notes": ["Failure estimate may change after more drive cycles."],
    }


def test_export_section_options_for_future_popup():
    """Test export helper exposes choices for the filter popup."""
    options = get_export_section_options()

    keys = [option["key"] for option in options]

    assert "summary" in keys
    assert "key_signals" in keys
    assert "diagnostic_report" in keys
    assert "data_quality_notes" not in keys


def test_export_section_options_omit_internal_data_notes():
    """Owner exports must not expose internal Model Layer notes."""
    keys = [option["key"] for option in get_export_section_options()]

    assert "data_quality_notes" not in keys
    assert keys.index("failure_prediction") < keys.index("key_signals")


def test_clean_export_sections_uses_default_order():
    """Test selected export sections stay in dashboard order."""
    sections = clean_export_sections([
        "diagnostic_report",
        "unknown",
        "summary",
    ])

    assert sections == ["summary", "diagnostic_report"]


def test_clean_export_sections_defaults_to_required_export_content():
    """Test default export sections match Task 6 required content."""
    assert clean_export_sections() == list(DEFAULT_EXPORT_SECTIONS)


def test_clean_csv_columns_uses_required_export_order():
    """Test CSV columns stay in the required Task 6 order."""
    columns = clean_csv_columns([
        "status",
        "bad_column",
        "feature",
    ])

    assert columns == ["feature", "status"]


def test_clean_csv_columns_defaults_to_all_columns():
    """Test CSV helper defaults to all required columns."""
    assert clean_csv_columns() == list(CSV_COLUMNS)
    assert clean_csv_columns(["bad_column"]) == list(CSV_COLUMNS)


def test_format_percent_handles_scores_and_missing_values():
    """Test risk score percentage formatting for export."""
    assert format_percent(0.864) == "86%"
    assert format_percent(None) == NOT_AVAILABLE
    assert format_percent("bad") == NOT_AVAILABLE


def test_format_reference_range_for_csv_and_pdf():
    """Test reference range format used by CSV and PDF exports."""
    assert format_reference_range([90.0, 95.0]) == "90.0-95.0"
    assert format_reference_range([]) == NOT_AVAILABLE
    assert format_reference_range("90-95") == NOT_AVAILABLE


def test_get_signal_status_abnormal_normal_unknown():
    """Test status calculation from value and reference_range."""
    assert get_signal_status({
        "value": 104.0,
        "reference_range": [90.0, 95.0],
    }) == "ABNORMAL"
    assert get_signal_status({
        "value": 82.0,
        "reference_range": [60.0, 90.0],
    }) == "NORMAL"
    assert get_signal_status({
        "value": None,
        "reference_range": [60.0, 90.0],
    }) == "Unknown"


def test_build_key_signal_rows_adds_display_name_and_status():
    """Test key signal rows are ready for export tables."""
    rows = build_key_signal_rows(_sample_component())

    assert rows[0]["feature"] == "coolant_temp"
    assert rows[0]["display_name"] == "Coolant Temperature"
    assert rows[0]["reference_range"] == "90.0-95.0"
    assert rows[0]["status"] == "ABNORMAL"
    assert rows[1]["status"] == "NORMAL"


def test_build_key_signal_rows_handles_empty_data():
    """Test empty key signals still return an empty row list."""
    assert build_key_signal_rows({"key_signals": []}) == []
    assert build_key_signal_rows({}) == []


def test_build_key_signals_csv_contains_header_and_rows():
    """Test CSV export contains the required key signal data."""
    csv_text = build_key_signals_csv(_sample_component())

    assert csv_text.splitlines()[0] == (
        "feature,value,unit,reference_range,status"
    )
    assert "coolant_temp,104.0,C,90.0-95.0,ABNORMAL" in csv_text
    assert "map,82.0,kPa,60.0-90.0,NORMAL" in csv_text


def test_build_key_signals_csv_handles_empty_signals():
    """Test CSV export still has a header when there are no rows."""
    csv_text = build_key_signals_csv({"key_signals": []})

    assert csv_text == "feature,value,unit,reference_range,status\n"


def test_build_key_signals_csv_filters_columns():
    """Test popup column choices can filter the CSV export."""
    csv_text = build_key_signals_csv(
        _sample_component(),
        selected_columns=["feature", "status"],
    )

    assert csv_text.splitlines() == [
        "feature,status",
        "coolant_temp,ABNORMAL",
        "map,NORMAL",
    ]


def test_build_key_signals_csv_bytes_returns_utf8_bytes():
    """Test Streamlit download_button can receive CSV bytes."""
    csv_bytes = build_key_signals_csv_bytes(_sample_component())

    assert isinstance(csv_bytes, bytes)
    assert csv_bytes.decode("utf-8").startswith("feature,value")


def test_export_zip_contains_each_selected_component_csv():
    """GL-383: multi-component export ZIP keeps every component file."""
    dashboard_dir = str(Path("dashboard").resolve())
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)

    from dashboard.pages.overview import _build_zip_bytes

    files = []
    for idx in range(5):
        component = {
            **_sample_component(),
            "component": f"component_{idx}",
        }
        files.append((
            f"component_{idx}_key_signals.csv",
            build_key_signals_csv_bytes(component),
        ))

    zip_bytes = _build_zip_bytes(files)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        names = sorted(zip_file.namelist())
        assert names == [f"component_{i}_key_signals.csv" for i in range(5)]
        for name in names:
            csv_text = zip_file.read(name).decode("utf-8")
            assert csv_text.startswith("feature,value,unit")
            assert "coolant_temp" in csv_text


def test_build_csv_file_name_uses_component_and_timestamp():
    """Test CSV filename is simple and stable for download."""
    file_name = build_csv_file_name(_sample_component())

    assert file_name == (
        "cooling_degradation_2026_06_16t12_00_00z_key_signals.csv"
    )


def test_build_pdf_file_name_uses_component_and_timestamp():
    """Test PDF filename is simple and stable for download."""
    file_name = build_pdf_file_name(_sample_component())

    assert file_name == (
        "cooling_degradation_2026_06_16t12_00_00z_diagnostic_report.pdf"
    )


def test_build_diagnostic_pdf_bytes_returns_pdf_file():
    """Test PDF export creates a real PDF byte payload."""
    pdf_bytes = build_diagnostic_pdf_bytes(_sample_component())

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_build_diagnostic_pdf_bytes_contains_key_report_text():
    """GL-383: PDF export keeps the important user-facing report text."""
    pypdf = pytest.importorskip("pypdf")
    pdf_bytes = build_diagnostic_pdf_bytes(_sample_component())

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert PDF_TITLE in text
    assert "Cooling System" in text
    assert "86%" in text
    assert "High" in text
    assert "Coolant Temperature" in text
    assert "Coolant temperature is high." in text


def test_build_diagnostic_pdf_bytes_accepts_section_filter():
    """Test PDF export can use popup section choices."""
    pdf_bytes = build_diagnostic_pdf_bytes(
        _sample_component(),
        selected_sections=["summary", "key_signals"],
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_diagnostic_report_pdf_body_style_is_more_readable():
    """GL-439: diagnostic report body text is larger with wider spacing."""
    tools = _get_reportlab_tools()
    styles = _get_pdf_styles(tools)

    assert styles["ReportDiagnosticBody"].fontSize > (
        styles["ReportBody"].fontSize
    )
    assert styles["ReportDiagnosticBody"].leading > (
        styles["ReportBody"].leading
    )


def test_pdf_title_is_user_facing():
    """Test PDF title is ready for the exported report."""
    assert PDF_TITLE == "Granite Lifeline Diagnostic Report"


def test_build_export_data_default_sections():
    """Test default helper output has summary, signals, and report."""
    export_data = build_export_data(_sample_component())

    assert export_data["sections"] == [
        "summary",
        "key_signals",
        "diagnostic_report",
    ]
    assert export_data["summary"]["component_name"] == "Cooling System"
    assert export_data["summary"]["risk_score"] == "86%"
    assert len(export_data["key_signals"]) == 2
    assert (
        export_data["diagnostic_report"]["anomaly_description"]
        == "Coolant temperature is high."
    )


def test_build_export_data_filters_optional_sections():
    """Test popup section choices can filter the export payload."""
    export_data = build_export_data(
        _sample_component(),
        selected_sections=["failure_prediction", "data_quality_notes"],
    )

    assert export_data["sections"] == ["failure_prediction"]
    assert export_data["failure_prediction"]["has_value"] is True
    assert "72%" not in export_data["failure_prediction"]["text"]
    assert "data_quality_notes" not in export_data
    assert "summary" not in export_data
