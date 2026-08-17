"""Helpers for preparing dashboard report export data."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from xml.sax.saxutils import escape

try:
    from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES
    from dashboard.failure_prediction import (
        format_failure_prediction_text,
        is_missing_value,
    )
except ImportError:  # Streamlit runs pages from inside dashboard/
    from anomaly_display import COMPONENT_DISPLAY_NAMES
    from failure_prediction import (
        format_failure_prediction_text,
        is_missing_value,
    )


NOT_AVAILABLE = "Not available"

EXPORT_SECTION_LABELS = {
    "summary": "Summary",
    "failure_prediction": "Failure Prediction",
    "key_signals": "Key Signals",
    "diagnostic_report": "Diagnostic Report",
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

PDF_TITLE = "Granite Lifeline Diagnostic Report"
PDF_BLUE = "#2563eb"
PDF_DARK = "#1f2937"
PDF_MUTED = "#6b7280"
PDF_BORDER = "#d6d9df"
PDF_PANEL = "#f8fafc"
PDF_DANGER = "#dc2626"
PDF_WARNING = "#f97316"
PDF_SUCCESS = "#16a34a"

SIGNAL_DISPLAY_NAMES = {
    "coolant_temp": "Coolant Temperature",
    "ect_rate_180s": "Coolant Temperature Rise Rate",
    "ect_start": "Coolant Temperature at Engine Start",
    "aat_start": "Ambient Temperature at Engine Start",
    "maf_integral_180s": "MAF Integral",
    "intake_temp": "Intake Air Temperature",
    "intake_air_temp": "Intake Air Temperature",
    "intake_temp_stability": "Intake Temperature Stability",
    "intake_ambient_delta": "Intake-Ambient Temperature Difference",
    "ambient_air_temp": "Ambient Air Temperature",
    "speed_density_maf_residual": "Speed-Density MAF Residual",
    "pedal_mapping_residual": "Pedal Mapping Residual",
    "pedal_slope": "Pedal Demand Rate",
    "accel_pedal_channel_delta": "Pedal Channel Difference",
    "map_range_60s": "MAP Range",
    "maf": "Mass Airflow",
    "map": "Intake Pressure",
    "throttle_position": "Throttle Position",
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


def build_pdf_file_name(component_data: Dict[str, Any]) -> str:
    """Build a simple PDF filename for the current component report."""
    component = clean_file_name_part(component_data.get("component"))
    timestamp = clean_file_name_part(component_data.get("timestamp"))
    if timestamp == "not_available":
        return f"{component}_diagnostic_report.pdf"
    return f"{component}_{timestamp}_diagnostic_report.pdf"


def pdf_text(value: Any) -> str:
    """Make plain text safe for ReportLab Paragraph."""
    return escape(format_plain_value(value))


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


def _get_reportlab_tools():
    """Load reportlab only when PDF export is used."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PDF export needs the Python package 'reportlab'. "
            "Install project dependencies with "
            "pip install -r requirements.txt."
        ) from exc

    return {
        "colors": colors,
        "A4": A4,
        "ParagraphStyle": ParagraphStyle,
        "TA_CENTER": TA_CENTER,
        "TA_LEFT": TA_LEFT,
        "getSampleStyleSheet": getSampleStyleSheet,
        "mm": mm,
        "Paragraph": Paragraph,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
    }


def _get_pdf_styles(tools: Dict[str, Any]):
    """Create the small style set used by the exported report template."""
    colors = tools["colors"]
    styles = tools["getSampleStyleSheet"]()
    ParagraphStyle = tools["ParagraphStyle"]

    styles.add(ParagraphStyle(
        name="ReportHeaderTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.white,
        alignment=tools["TA_LEFT"],
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ReportHeaderSub",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=tools["TA_LEFT"],
    ))
    styles.add(ParagraphStyle(
        name="ReportHeaderRiskBox",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.white,
        alignment=tools["TA_CENTER"],
    ))
    styles.add(ParagraphStyle(
        name="ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor(PDF_DARK),
        spaceBefore=3,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="ReportPanelTitle",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor(PDF_BLUE),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor(PDF_DARK),
    ))
    styles.add(ParagraphStyle(
        name="ReportDiagnosticBody",
        parent=styles["ReportBody"],
        fontSize=10.5,
        leading=16.5,
    ))
    styles.add(ParagraphStyle(
        name="ReportMuted",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor(PDF_MUTED),
    ))
    styles.add(ParagraphStyle(
        name="ReportMetric",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor(PDF_DARK),
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(PDF_DARK),
    ))
    styles.add(ParagraphStyle(
        name="TableCellMuted",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor(PDF_MUTED),
    ))
    styles.add(ParagraphStyle(
        name="StatusBad",
        parent=styles["TableCell"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(PDF_DANGER),
    ))
    styles.add(ParagraphStyle(
        name="StatusGood",
        parent=styles["TableCell"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(PDF_SUCCESS),
    ))
    styles.add(ParagraphStyle(
        name="StatusUnknown",
        parent=styles["TableCell"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(PDF_MUTED),
    ))
    return styles


def _pdf_color(tools: Dict[str, Any], hex_value: str):
    return tools["colors"].HexColor(hex_value)


def _risk_color(summary: Dict[str, str]) -> str:
    level = summary.get("risk_level", "").lower()
    if level == "high":
        return PDF_DANGER
    if level == "medium":
        return PDF_WARNING
    if level == "low":
        return PDF_SUCCESS
    return PDF_MUTED


def _add_report_header(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    summary: Dict[str, str],
):
    Paragraph = tools["Paragraph"]
    Table = tools["Table"]
    TableStyle = tools["TableStyle"]
    mm = tools["mm"]

    title = Paragraph(PDF_TITLE, styles["ReportHeaderTitle"])
    subtitle = Paragraph(
        f"Component: {pdf_text(summary['component_name'])}<br/>"
        f"Generated: {pdf_text(summary['timestamp'])}",
        styles["ReportHeaderSub"],
    )
    risk_score = summary["risk_score"]
    if risk_score == NOT_AVAILABLE:
        risk_score = "N/A"
    risk = Paragraph(
        f"RISK SCORE&nbsp;&nbsp;"
        f"<font size='16'>{pdf_text(risk_score)}</font>"
        f"<br/>Risk level: {pdf_text(summary['risk_level'])}",
        styles["ReportHeaderRiskBox"],
    )
    header = Table(
        [[[title, subtitle], risk]],
        colWidths=[126 * mm, 42 * mm],
        hAlign="CENTER",
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), _pdf_color(tools, PDF_BLUE)),
        (
            "BACKGROUND", (1, 0), (1, 0),
            _pdf_color(tools, _risk_color(summary)),
        ),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BLUE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 13),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
    ]))
    elements.append(header)
    elements.append(tools["Spacer"](1, 7 * mm))


def _add_pdf_section(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    title: str,
):
    elements.append(tools["Spacer"](1, 4 * tools["mm"]))
    elements.append(
        tools["Paragraph"](pdf_text(title), styles["ReportSection"])
    )


def _add_summary_pdf(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    summary: Dict[str, str],
):
    Paragraph = tools["Paragraph"]
    Table = tools["Table"]
    TableStyle = tools["TableStyle"]
    mm = tools["mm"]
    metric_items = [
        ("COMPONENT", summary["component_name"]),
        ("RISK SCORE", summary["risk_score"]),
        ("RISK LEVEL", summary["risk_level"]),
        ("TIMESTAMP", summary["timestamp"]),
    ]
    cells = []
    for label, value in metric_items:
        cells.append(Paragraph(
            f"<font color='{PDF_MUTED}' size='7'>{label}</font><br/>"
            f"<font color='{PDF_DARK}' size='12'>"
            f"<b>{pdf_text(value)}</b></font>",
            styles["ReportMetric"],
        ))
    table = Table([cells], colWidths=[42 * mm] * 4, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_PANEL)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _pdf_color(tools, PDF_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)


def _status_style_name(status: str) -> str:
    if status == "ABNORMAL":
        return "StatusBad"
    if status == "NORMAL":
        return "StatusGood"
    return "StatusUnknown"


def _add_signal_pdf_table(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    rows,
):
    Paragraph = tools["Paragraph"]
    table_rows = [[
        Paragraph("Feature", styles["TableHeader"]),
        Paragraph("Value", styles["TableHeader"]),
        Paragraph("Unit", styles["TableHeader"]),
        Paragraph("Reference Range", styles["TableHeader"]),
        Paragraph("Status", styles["TableHeader"]),
    ]]
    for row in rows:
        display_name = row.get("display_name") or row["feature"]
        if display_name != row["feature"]:
            feature = Paragraph(
                f"{pdf_text(display_name)}<br/>"
                f"<font color='{PDF_MUTED}' size='7'>"
                f"{pdf_text(row['feature'])}</font>",
                styles["TableCell"],
            )
        else:
            feature = Paragraph(pdf_text(row["feature"]), styles["TableCell"])
        table_rows.append([
            feature,
            Paragraph(pdf_text(row["value"]), styles["TableCell"]),
            Paragraph(pdf_text(row["unit"]), styles["TableCell"]),
            Paragraph(pdf_text(row["reference_range"]), styles["TableCell"]),
            Paragraph(
                pdf_text(row["status"]),
                styles[_status_style_name(row["status"])],
            ),
        ])

    if len(table_rows) == 1:
        table_rows.append([
            Paragraph("No key signals available", styles["TableCell"]),
            "",
            "",
            "",
            "",
        ])

    table = tools["Table"](
        table_rows,
        colWidths=[
            54 * tools["mm"],
            23 * tools["mm"],
            18 * tools["mm"],
            44 * tools["mm"],
            29 * tools["mm"],
        ],
        hAlign="CENTER",
        repeatRows=1,
    )
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _pdf_color(tools, PDF_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, _pdf_color(tools, PDF_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    for row_number in range(1, len(table_rows)):
        if row_number % 2 == 1:
            style.append((
                "BACKGROUND",
                (0, row_number),
                (-1, row_number),
                _pdf_color(tools, PDF_PANEL),
            ))
    table.setStyle(tools["TableStyle"](style))
    elements.append(table)


def _add_text_panel(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    title: str,
    body: Any,
    body_is_html: bool = False,
    body_style_name: str = "ReportBody",
):
    Paragraph = tools["Paragraph"]
    Table = tools["Table"]
    TableStyle = tools["TableStyle"]
    mm = tools["mm"]
    body_text = body if body_is_html else pdf_text(body)
    table = Table(
        [[
            Paragraph(pdf_text(title), styles["ReportPanelTitle"]),
            Paragraph(body_text, styles[body_style_name]),
        ]],
        colWidths=[42 * mm, 126 * mm],
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_PANEL)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    elements.append(table)
    elements.append(tools["Spacer"](1, 2 * mm))


def _add_list_panel(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    title: str,
    items: Iterable[Any],
    body_style_name: str = "ReportBody",
):
    clean_items = list(items) or [NOT_AVAILABLE]
    body = "<br/>".join(
        f"- {pdf_text(item)}" for item in clean_items
    )
    _add_text_panel(
        elements,
        tools,
        styles,
        title,
        body,
        body_is_html=True,
        body_style_name=body_style_name,
    )


def _draw_pdf_footer(canvas, doc, tools: Dict[str, Any]):
    mm = tools["mm"]
    canvas.saveState()
    canvas.setStrokeColor(_pdf_color(tools, PDF_BORDER))
    canvas.setFillColor(_pdf_color(tools, PDF_MUTED))
    canvas.setFont("Helvetica", 8)
    y = 10 * mm
    canvas.line(
        doc.leftMargin, y + 5, doc.pagesize[0] - doc.rightMargin, y + 5
    )
    canvas.drawString(doc.leftMargin, y, "Granite Lifeline")
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        y,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def _add_small_table(
    elements: List[Any],
    tools: Dict[str, Any],
    rows,
    has_header: bool = False,
):
    colors = tools["colors"]
    table = tools["Table"](rows, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6d9df")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f4f8")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]
    if has_header:
        style.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    else:
        style.append(("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"))

    table.setStyle(tools["TableStyle"](style))
    elements.append(table)


def build_diagnostic_pdf_bytes(
    component_data: Dict[str, Any],
    selected_sections: Optional[Iterable[str]] = None,
) -> bytes:
    """Build PDF bytes for the component diagnostic report."""
    tools = _get_reportlab_tools()
    buffer = io.BytesIO()
    doc = tools["SimpleDocTemplate"](
        buffer,
        pagesize=tools["A4"],
        rightMargin=16 * tools["mm"],
        leftMargin=16 * tools["mm"],
        topMargin=14 * tools["mm"],
        bottomMargin=14 * tools["mm"],
    )
    styles = _get_pdf_styles(tools)
    summary = build_summary(component_data)
    elements: List[Any] = []
    _add_report_header(elements, tools, styles, summary)

    export_data = build_export_data(component_data, selected_sections)

    if "summary" in export_data:
        _add_pdf_section(elements, tools, styles, "Summary")
        _add_summary_pdf(elements, tools, styles, export_data["summary"])

    if "failure_prediction" in export_data:
        _add_pdf_section(elements, tools, styles, "Failure Prediction")
        _add_text_panel(
            elements,
            tools,
            styles,
            "Prediction",
            export_data["failure_prediction"]["text"],
        )

    if "key_signals" in export_data:
        _add_pdf_section(elements, tools, styles, "Key Signals")
        _add_signal_pdf_table(
            elements,
            tools,
            styles,
            export_data["key_signals"],
        )

    if "diagnostic_report" in export_data:
        report = export_data["diagnostic_report"]
        _add_pdf_section(elements, tools, styles, "Diagnostic Report")
        _add_text_panel(
            elements,
            tools,
            styles,
            "What's Happening",
            report["anomaly_description"],
            body_style_name="ReportDiagnosticBody",
        )
        _add_text_panel(
            elements,
            tools,
            styles,
            "Why This Matters",
            report["possible_cause"],
            body_style_name="ReportDiagnosticBody",
        )
        _add_list_panel(
            elements,
            tools,
            styles,
            "What You Should Do",
            report["recommended_action"],
            body_style_name="ReportDiagnosticBody",
        )

    doc.build(
        elements,
        onFirstPage=lambda canvas, page_doc: _draw_pdf_footer(
            canvas,
            page_doc,
            tools,
        ),
        onLaterPages=lambda canvas, page_doc: _draw_pdf_footer(
            canvas,
            page_doc,
            tools,
        ),
    )
    return buffer.getvalue()


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

    return export_data
