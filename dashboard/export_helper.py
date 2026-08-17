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
    "risk_history": "Risk Trend",
    "key_signals": "Key Signals",
    "diagnostic_report": "Diagnostic Report",
}

DEFAULT_EXPORT_SECTIONS = (
    "summary",
    "failure_prediction",
    "risk_history",
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
# Matches dashboard/theme.py light-mode tokens exactly (accent,
# risk_high/medium/low) so the exported PDF and the live Dashboard never
# show two different colors for the same risk level.
PDF_BLUE = "#0f62fe"
PDF_DARK = "#1f2937"
PDF_MUTED = "#6b7280"
PDF_BORDER = "#d6d9df"
PDF_PANEL = "#f8fafc"
PDF_DANGER = "#da1e28"
PDF_WARNING = "#ff832b"
PDF_SUCCESS = "#24a148"

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
    """Build the top summary section for export.

    risk_score is an internal classification value, not a owner-facing
    probability (risk_score of 1.0 means "at or past the High-risk
    threshold", not "100% certain"). The live Dashboard never renders it
    as literal percentage text — only risk_level (High/Medium/Low) and,
    separately, the model's prediction_confidence are shown as
    percentages. The export must match that, not show its own number.
    """
    component = component_data.get("component")
    return {
        "component": format_plain_value(component),
        "component_name": COMPONENT_DISPLAY_NAMES.get(
            component, format_plain_value(component)
        ),
        "risk_level": format_plain_value(component_data.get("risk_level")),
        "confidence": format_percent(
            component_data.get("prediction_confidence")
        ),
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
        from reportlab.graphics.charts.linecharts import HorizontalLineChart
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.widgets.markers import makeMarker
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
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
        "Drawing": Drawing,
        "HorizontalLineChart": HorizontalLineChart,
        "makeMarker": makeMarker,
        "KeepTogether": KeepTogether,
        "PageBreak": PageBreak,
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
        name="ReportHeaderRiskLabel",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=tools["TA_CENTER"],
    ))
    styles.add(ParagraphStyle(
        name="ReportHeaderRiskBadge",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.white,
        alignment=tools["TA_CENTER"],
    ))
    styles.add(ParagraphStyle(
        name="ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor(PDF_DARK),
        spaceBefore=0,
        spaceAfter=0,
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
    risk_level = summary["risk_level"]
    badge_text = risk_level.upper() if risk_level != NOT_AVAILABLE else "N/A"

    # Risk badge is its own small rounded pill nested inside the header
    # bar, not a second full-height rectangle butted against the first —
    # avoids the hard two-color seam and the cramped "RISK / SCORE 86%"
    # line wrap of the previous layout.
    badge = Table(
        [[Paragraph("RISK LEVEL", styles["ReportHeaderRiskLabel"])],
         [Paragraph(pdf_text(badge_text), styles["ReportHeaderRiskBadge"])]],
        colWidths=[34 * mm],
        hAlign="CENTER",
    )
    badge.setStyle(TableStyle([
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        (
            "BACKGROUND", (0, 0), (-1, -1),
            _pdf_color(tools, _risk_color(summary)),
        ),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (0, 0), 8),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ("TOPPADDING", (0, 1), (0, 1), 1),
        ("BOTTOMPADDING", (0, 1), (0, 1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    header = Table(
        [[[title, subtitle], badge]],
        colWidths=[134 * mm, 34 * mm],
        hAlign="CENTER",
    )
    header.setStyle(TableStyle([
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_BLUE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 16),
        ("RIGHTPADDING", (1, 0), (1, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    elements.append(header)
    elements.append(tools["Spacer"](1, 7 * mm))


def _add_pdf_section(
    elements: List[Any],
    tools: Dict[str, Any],
    styles,
    title: str,
) -> List[Any]:
    """Build a section heading with a colored accent rule.

    Returns the heading flowables so the caller can bundle them into the
    same KeepTogether group as the section's content — a header must
    never be stranded alone at the bottom of a page.
    """
    Table = tools["Table"]
    mm = tools["mm"]
    heading = tools["Paragraph"](pdf_text(title), styles["ReportSection"])
    rule = Table([[""]], colWidths=[16 * mm], rowHeights=[2.4])
    rule.setStyle(tools["TableStyle"]([
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_BLUE)),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        tools["Spacer"](1, 5 * mm),
        heading,
        tools["Spacer"](1, 3),
        rule,
        tools["Spacer"](1, 3 * mm),
    ]


def _add_summary_pdf(
    tools: Dict[str, Any],
    styles,
    summary: Dict[str, str],
) -> Any:
    Paragraph = tools["Paragraph"]
    Table = tools["Table"]
    TableStyle = tools["TableStyle"]
    mm = tools["mm"]
    metric_items = [
        ("COMPONENT", summary["component_name"]),
        ("RISK LEVEL", summary["risk_level"]),
        ("MODEL CONFIDENCE", summary["confidence"]),
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
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_PANEL)),
        ("LINEABOVE", (0, 0), (-1, 0), 2.5, _pdf_color(tools, PDF_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _pdf_color(tools, PDF_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return table


def _format_trend_label(timestamp: Any) -> str:
    """Format one risk_history timestamp as a short axis label."""
    text = str(timestamp or "")
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).strftime("%m-%d")
    except ValueError:
        return ""


def _build_risk_trend_drawing(
    tools: Dict[str, Any],
    risk_history: List[Dict[str, Any]],
) -> Any:
    """Build a vector line-chart Drawing of risk_score over time.

    Mirrors the live Dashboard's trend chart (dashboard/pages/detail.py
    _render_trend): a 0-1 "risk index" line, not a percentage, and not
    described as a failure probability. Uses reportlab's own charting
    (no matplotlib/kaleido dependency) so the PDF has no new
    dependency and stays visually consistent with the rest of the
    report.
    """
    Drawing = tools["Drawing"]
    HorizontalLineChart = tools["HorizontalLineChart"]
    mm = tools["mm"]

    width = 176 * mm
    height = 52 * mm
    values = [float(entry.get("risk_score", 0)) for entry in risk_history]
    labels = [_format_trend_label(e.get("timestamp")) for e in risk_history]

    # Thin labels so they don't collide when there are many windows —
    # keep at most ~7 evenly spaced, blank the rest.
    keep_every = max(1, len(labels) // 7)
    thinned_labels = [
        label if idx % keep_every == 0 else ""
        for idx, label in enumerate(labels)
    ]

    drawing = Drawing(width, height)
    chart = HorizontalLineChart()
    chart.x = 8 * mm
    chart.y = 12 * mm
    chart.width = width - 16 * mm
    chart.height = height - 20 * mm
    chart.data = [values]
    chart.categoryAxis.categoryNames = thinned_labels
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.fillColor = _pdf_color(tools, PDF_MUTED)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 1
    chart.valueAxis.valueStep = 0.25
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = _pdf_color(tools, PDF_MUTED)
    chart.lines[0].strokeColor = _pdf_color(tools, PDF_BLUE)
    chart.lines[0].strokeWidth = 1.6
    chart.lines[0].symbol = tools["makeMarker"]("Circle")
    chart.lines[0].symbol.size = 3.2
    chart.lines[0].symbol.fillColor = _pdf_color(tools, PDF_BLUE)
    chart.lines[0].symbol.strokeColor = _pdf_color(tools, PDF_BLUE)
    drawing.add(chart)
    return drawing


def _add_risk_trend_panel(tools: Dict[str, Any], styles, rows) -> List[Any]:
    Table = tools["Table"]
    TableStyle = tools["TableStyle"]
    mm = tools["mm"]

    if len(rows) < 2:
        return _add_text_panel(
            tools,
            styles,
            "Risk Trend",
            "Not enough data yet to show a risk score trend.",
        )

    drawing = _build_risk_trend_drawing(tools, rows)
    caption = tools["Paragraph"](
        "Internal risk index over the recorded model windows. It "
        "supports the Low, Medium and High categories; it is not a "
        "probability of mechanical failure.",
        styles["ReportMuted"],
    )
    table = Table(
        [[drawing], [caption]],
        colWidths=[176 * mm],
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_PANEL)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, _pdf_color(tools, PDF_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (0, 0), 8),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 2),
        ("BOTTOMPADDING", (0, 1), (0, 1), 8),
    ]))
    return [table, tools["Spacer"](1, 2 * mm)]


def _status_style_name(status: str) -> str:
    if status == "ABNORMAL":
        return "StatusBad"
    if status == "NORMAL":
        return "StatusGood"
    return "StatusUnknown"


def _add_signal_pdf_table(
    tools: Dict[str, Any],
    styles,
    rows,
) -> Any:
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
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
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
    return table


def _add_text_panel(
    tools: Dict[str, Any],
    styles,
    title: str,
    body: Any,
    body_is_html: bool = False,
    body_style_name: str = "ReportBody",
) -> List[Any]:
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
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("BACKGROUND", (0, 0), (-1, -1), _pdf_color(tools, PDF_PANEL)),
        ("LINEBEFORE", (0, 0), (0, 0), 2.5, _pdf_color(tools, PDF_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.5, _pdf_color(tools, PDF_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [table, tools["Spacer"](1, 2 * mm)]


def _add_list_panel(
    tools: Dict[str, Any],
    styles,
    title: str,
    items: Iterable[Any],
    body_style_name: str = "ReportBody",
) -> List[Any]:
    clean_items = list(items) or [NOT_AVAILABLE]
    body = "<br/>".join(
        f"- {pdf_text(item)}" for item in clean_items
    )
    return _add_text_panel(
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
    # The rule needs clear air above the text baseline — 8pt Helvetica's
    # cap height reaches ~y+5.8, so a rule at y+5 visually cut through
    # the tops of the footer text. Give it real separation.
    line_y = y + 12
    canvas.line(
        doc.leftMargin, line_y, doc.pagesize[0] - doc.rightMargin, line_y
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
        # Footer rule sits at ~22mm from the page bottom (see
        # _draw_pdf_footer) — this needs to clear it with real margin,
        # not just avoid literal overlap.
        bottomMargin=26 * tools["mm"],
    )
    styles = _get_pdf_styles(tools)
    summary = build_summary(component_data)
    elements: List[Any] = []
    _add_report_header(elements, tools, styles, summary)

    export_data = build_export_data(component_data, selected_sections)
    KeepTogether = tools["KeepTogether"]
    SECTION_GAP = 8 * tools["mm"]

    def add_section(
        title: str,
        first_panel: Any,
        *rest_panels: Any,
        keep_whole: bool = False,
    ):
        """Glue the section heading to its content so a heading can
        never be stranded alone at the bottom of a page.

        By default only the heading + first panel are guaranteed
        together — later panels may still flow onto the next page if
        the section is unusually long. keep_whole=True instead keeps
        the entire section (heading + every panel) as one block, for
        sections such as Diagnostic Report that read best as a single
        page and are realistically short enough to fit one.
        """
        heading = _add_pdf_section(elements, tools, styles, title)
        if keep_whole:
            elements.append(
                KeepTogether([*heading, first_panel, *rest_panels])
            )
        else:
            elements.append(KeepTogether([*heading, first_panel]))
            for panel in rest_panels:
                elements.append(panel)
        elements.append(tools["Spacer"](1, SECTION_GAP))

    if "summary" in export_data:
        add_section("Summary", _add_summary_pdf(
            tools, styles, export_data["summary"]
        ))

    if "failure_prediction" in export_data:
        panel = _add_text_panel(
            tools,
            styles,
            "Prediction",
            export_data["failure_prediction"]["text"],
        )
        add_section("Failure Prediction", panel[0], *panel[1:])

    if "risk_history" in export_data:
        panel = _add_risk_trend_panel(
            tools, styles, export_data["risk_history"]
        )
        add_section("Risk Trend", panel[0], *panel[1:])

    if "key_signals" in export_data:
        add_section("Key Signals", _add_signal_pdf_table(
            tools, styles, export_data["key_signals"]
        ))

    if "diagnostic_report" in export_data:
        report = export_data["diagnostic_report"]
        # The narrative report reads as its own page, separate from the
        # data/metrics sections above — not a hard technical requirement,
        # a deliberate readability choice. _add_report_header() always
        # appends exactly 2 elements (header table + spacer); only break
        # if some other section was actually rendered before this one,
        # so a diagnostic_report-only export doesn't start with a blank
        # page.
        if len(elements) > 2:
            elements.append(tools["PageBreak"]())
        whats_happening = _add_text_panel(
            tools,
            styles,
            "What's Happening",
            report["anomaly_description"],
            body_style_name="ReportDiagnosticBody",
        )
        why_this_matters = _add_text_panel(
            tools,
            styles,
            "Why This Matters",
            report["possible_cause"],
            body_style_name="ReportDiagnosticBody",
        )
        what_to_do = _add_list_panel(
            tools,
            styles,
            "What You Should Do",
            report["recommended_action"],
            body_style_name="ReportDiagnosticBody",
        )
        add_section(
            "Diagnostic Report",
            whats_happening[0],
            *whats_happening[1:],
            *why_this_matters,
            *what_to_do,
            keep_whole=True,
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

    if "risk_history" in sections:
        history = component_data.get("risk_history")
        export_data["risk_history"] = (
            history if isinstance(history, list) else []
        )

    if "key_signals" in sections:
        export_data["key_signals"] = build_key_signal_rows(component_data)

    if "diagnostic_report" in sections:
        export_data["diagnostic_report"] = build_diagnostic_report(
            component_data
        )

    return export_data
