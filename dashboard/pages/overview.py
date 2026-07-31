"""Overview page — vehicle health summary with CSV upload entry point."""

from __future__ import annotations

import io
import html
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st
from pandas.errors import EmptyDataError

from anomaly_display import COMPONENT_DISPLAY_NAMES
from csv_validator import validate_csv_columns, validate_csv_min_rows
from csv_pipeline import (
    ModelBatchRunnerUnavailable,
    UploadedCsvPipelineError,
    run_uploaded_csv_batch,
)
from data_store import get_data_source, get_mock_data, get_overview_components
from export_helper import (
    CSV_COLUMNS,
    DEFAULT_EXPORT_SECTIONS,
    EXPORT_SECTION_LABELS,
    build_diagnostic_pdf_bytes,
    build_key_signals_csv_bytes,
    clean_csv_columns,
    clean_export_sections,
    clean_file_name_part,
)
from theme import (
    COMPONENT_ICONS,
    FONT_MONO,
    THEME_TOKENS,
    hex_to_rgba,
    lucide_icon,
    progress_ring,
    svg_data_uri,
)
from ui_components import (
    danger_card_html,
    empty_state_html,
    page_title_html,
    section_heading_html,
    show_footer,
    warning_banner_html,
)
# Note: show_mock_data_warning is defined in this file, not ui_components


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

CSV_ANALYSIS_RUNNING_KEY = "csv_analysis_running"


def _set_csv_analysis_running(is_running: bool) -> None:
    st.session_state[CSV_ANALYSIS_RUNNING_KEY] = is_running


def _recover_csv_analysis_running_state() -> bool:
    """Clear stale loading state left by an interrupted previous run."""
    if st.session_state.get(CSV_ANALYSIS_RUNNING_KEY, False):
        _set_csv_analysis_running(False)
    return False


def _show_theme_toggle(dark_mode: bool, tokens: dict) -> None:
    """Render the dark/light-mode icon button."""
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if dark_mode:
        theme_icon_svg = lucide_icon("sun", size=20, color=tokens["text"])
        if st.button("Light", key="theme_btn", help="Switch to light mode"):
            st.session_state["dark_mode"] = False
            st.rerun()
    else:
        theme_icon_svg = lucide_icon("moon", size=20, color=tokens["text"])
        if st.button("Dark", key="theme_btn", help="Switch to dark mode"):
            st.session_state["dark_mode"] = True
            st.rerun()

    icon_src = svg_data_uri(theme_icon_svg)
    st.markdown(
        f"""
        <style>
            div[data-testid="stColumn"]:has(.st-key-theme_btn)
                div[data-testid="stVerticalBlock"] {{
                align-items: flex-end !important;
            }}
            .st-key-theme_btn button {{
                background-color: {tokens["surface"]} !important;
                background-image: url("{icon_src}") !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                background-size: 20px 20px !important;
                border: 1px solid {tokens["border"]} !important;
                border-radius: 10px !important;
                box-shadow: 0 1px 3px {tokens["shadow"]} !important;
                color: transparent !important;
                font-size: 0 !important;
                height: 40px !important;
                line-height: 0 !important;
                margin-left: auto !important;
                min-height: 40px !important;
                min-width: 40px !important;
                padding: 0 !important;
                transition: background-color 0.2s ease !important;
                width: 40px !important;
            }}
            .st-key-theme_btn button:hover {{
                background-color: {tokens["surface_alt"]} !important;
            }}
            .st-key-theme_btn button:active {{
                transform: scale(0.95) !important;
            }}
            .st-key-theme_btn button:focus-visible {{
                outline: 2px solid {tokens["accent"]} !important;
                outline-offset: 2px !important;
            }}
            .st-key-theme_btn button *,
            .st-key-theme_btn button p {{
                color: transparent !important;
                font-size: 0 !important;
                line-height: 0 !important;
                display: none !important;
            }}
            [data-baseweb="tooltip"] > div {{
                background-color: {tokens["surface"]} !important;
                border: 1px solid {tokens["border"]} !important;
                border-radius: 10px !important;
                box-shadow: 0 2px 8px {tokens["shadow"]} !important;
            }}
            [data-testid="stTooltipContent"],
            [data-testid="stTooltipContent"] p {{
                color: {tokens["text"]} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_status_banner(
    mock_data: dict,
    data_source: dict,
    tokens: dict,
) -> None:
    """Status banner with inline risk legend chips."""
    has_high = any(c.get("risk_level") == "High" for c in mock_data.values())
    has_incomplete = any(
        source == "missing" for source in data_source.values()
    )

    if has_high:
        banner_bg = hex_to_rgba(tokens["risk_high"], 0.10)
        banner_border = hex_to_rgba(tokens["risk_high"], 0.30)
        icon_svg = lucide_icon(
            "alert-triangle", size=18, color=tokens["danger_text"]
        )
        status_text = (
            "Attention needed — one or more components require "
            "urgent action"
        )
        text_color = tokens["danger_text"]
    elif has_incomplete:
        banner_bg = hex_to_rgba(tokens["text_secondary"], 0.08)
        banner_border = hex_to_rgba(tokens["text_secondary"], 0.22)
        icon_svg = lucide_icon(
            "info", size=18, color=tokens["text_secondary"]
        )
        status_text = (
            "Analysis incomplete — some components do not have data yet"
        )
        text_color = tokens["text_secondary"]
    else:
        banner_bg = hex_to_rgba(tokens["risk_low"], 0.10)
        banner_border = hex_to_rgba(tokens["risk_low"], 0.30)
        icon_svg = lucide_icon(
            "check-square", size=18, color=tokens["risk_low"]
        )
        status_text = "No high-risk components detected"
        text_color = tokens["risk_low"]

    legend_chips = "".join(
        f'<div style="display:flex;align-items:center;gap:5px;'
        f'background:{hex_to_rgba(color, 0.12)};'
        f'border:1px solid {hex_to_rgba(color, 0.30)};'
        f'border-radius:100px;padding:3px 10px;font-size:12px;'
        f'color:{tokens["text_secondary"]};white-space:nowrap;">'
        f'<div style="width:7px;height:7px;border-radius:50%;'
        f'background:{color};flex-shrink:0;"></div>'
        f'<span>{label}</span></div>'
        for label, color in [
            ("High", tokens["risk_high"]),
            ("Medium", tokens["risk_medium"]),
            ("Low", tokens["risk_low"]),
        ]
    )

    st.markdown(
        f'<div style="background:{banner_bg};'
        f'border:1px solid {banner_border};'
        'border-radius:14px;padding:14px 20px;margin:16px auto;'
        'max-width:860px;'
        'display:flex;align-items:center;justify-content:space-between;'
        f'gap:16px;flex-wrap:wrap;box-shadow:0 2px 8px {tokens["shadow"]};">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'{icon_svg}'
        f'<span style="font-weight:600;font-size:14px;color:{text_color};">'
        f'{status_text}</span></div>'
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'flex-wrap:wrap;">'
        f'{legend_chips}</div></div>',
        unsafe_allow_html=True,
    )


def _show_csv_upload_heading(tokens: dict) -> None:
    """Render centered upload heading with inline requirements toggle."""
    columns = [
        "Time",
        "Engine RPM [RPM]",
        "Vehicle Speed Sensor [km/h]",
        "Engine Coolant Temperature [°C]",
        "Intake Air Temperature [°C]",
        "Intake Manifold Absolute Pressure [kPa]",
        "Air Flow Rate from Mass Flow Sensor [g/s]",
        "Absolute Throttle Position [%]",
        "Ambient Air Temperature [°C]",
        "Accelerator Pedal Position D [%]",
        "Accelerator Pedal Position E [%]",
    ]
    column_items = "".join(
        f'<div class="csv-upload-help-column">{col}</div>'
        for col in columns
    )

    hint_icon = lucide_icon(
        "help-circle", size=16, color=tokens["text_secondary"]
    )
    hint_icon_src = svg_data_uri(hint_icon)

    st.markdown(
        f"""
        <style>
        .csv-upload-help {{
            display:block;
            margin:0 0 20px 0;
            width:100%;
        }}
        .csv-upload-help summary {{
            align-items:center;
            cursor:pointer;
            display:grid;
            gap:10px;
            grid-template-columns:28px auto 28px;
            justify-content:center;
            list-style:none;
            width:100%;
        }}
        .csv-upload-help summary::-webkit-details-marker {{
            display:none;
        }}
        .csv-heading-spacer {{
            height:28px;
            visibility:hidden;
            width:28px;
        }}
        .csv-upload-heading-title {{
            color:{tokens["text"]};
            font-size:15px;
            font-weight:700;
            line-height:28px;
            text-align:center;
            white-space:nowrap;
        }}
        .csv-help-icon {{
            background-color: {tokens["surface"]} !important;
            background-image: url("{hint_icon_src}") !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-size: 16px 16px !important;
            border: 1px solid {tokens["border"]} !important;
            border-radius: 50% !important;
            display:inline-flex;
            height: 28px !important;
            flex:0 0 28px;
            width: 28px !important;
            transition: background-color 0.15s ease,
                border-color 0.15s ease !important;
        }}
        .csv-upload-help summary:hover .csv-help-icon {{
            background-color: {hex_to_rgba(tokens["accent"], 0.08)} !important;
            border-color: {tokens["accent"]} !important;
        }}
        .csv-upload-help-panel {{
            background:{tokens["surface"]};
            border:1px solid {hex_to_rgba(tokens["accent"], 0.22)};
            border-radius:12px;
            box-sizing:border-box;
            box-shadow:0 8px 24px {tokens["shadow"]};
            max-width:min(460px, calc(100% - 24px));
            margin:14px auto 0 auto;
            padding:16px 18px;
            width:100%;
        }}
        .csv-upload-help-grid {{
            display:grid;
            gap:8px 20px;
            grid-template-columns:repeat(2, minmax(0, 1fr));
        }}
        .csv-upload-help-column {{
            color:{tokens["text"]};
            font-family:{FONT_MONO};
            font-size:12px;
            line-height:1.55;
            overflow-wrap:anywhere;
        }}
        @media (max-width: 640px) {{
            .csv-upload-help-panel {{
                max-width:100%;
                padding:14px;
            }}
            .csv-upload-help-grid {{
                grid-template-columns:1fr;
            }}
        }}
        </style>
        <details class="csv-upload-help">
            <summary aria-label="Show CSV requirements">
                <span class="csv-heading-spacer" aria-hidden="true"></span>
                <span class="csv-upload-heading-title">
                    Upload OBD-II CSV File</span>
                <span class="csv-help-icon" aria-hidden="true"></span>
            </summary>
                <div class="csv-upload-help-panel">
                    <div style="font-size:12px;font-weight:700;
                        letter-spacing:0.4px;
                        text-transform:uppercase;color:{tokens["accent"]};
                        margin-bottom:10px;">Required CSV format</div>
                    <div class="csv-upload-help-grid">{column_items}</div>
                    <div style="margin-top:10px;font-size:12px;
                        color:{tokens["text_secondary"]};
                        border-top:1px solid
                            {hex_to_rgba(tokens["accent"], 0.18)};
                        padding-top:8px;">
                        Minimum <strong style="color:{tokens["text"]}">
                            700 rows</strong>
                        (≈ 15 min recorded at 1&nbsp;Hz)
                    </div>
                </div>
        </details>
        """,
        unsafe_allow_html=True,
    )


def _error_paragraph(message: str, tokens: dict) -> str:
    return (
        f'<p style="color:{tokens["danger_text"]};font-size:14px;'
        f'margin:8px 0 0 0;line-height:1.5;">'
        f'{html.escape(message)}</p>'
    )


def _show_pipeline_error(title: str, message: str, tokens: dict) -> None:
    st.markdown(
        danger_card_html(title, _error_paragraph(message, tokens), tokens),
        unsafe_allow_html=True,
    )


def _show_csv_analysis_loading(tokens: dict) -> None:
    """Render a clear loading state for the CSV analysis pipeline."""
    st.markdown(
        f"""
        <style>
        .csv-analysis-loading {{
            align-items: center;
            background: {tokens["surface"]};
            border: 1px solid {hex_to_rgba(tokens["accent"], 0.28)};
            border-radius: 12px;
            box-shadow: 0 2px 10px {tokens["shadow"]};
            display: flex;
            gap: 14px;
            margin: 12px auto 0 auto;
            max-width: 620px;
            padding: 16px 18px;
        }}
        .csv-analysis-spinner {{
            animation: csv-spin 1s linear infinite;
            border: 3px solid {hex_to_rgba(tokens["accent"], 0.16)};
            border-radius: 999px;
            border-top-color: {tokens["accent"]};
            flex: 0 0 auto;
            height: 28px;
            width: 28px;
        }}
        .csv-analysis-title {{
            color: {tokens["text"]};
            font-size: 15px;
            font-weight: 800;
            margin-bottom: 4px;
        }}
        .csv-analysis-message {{
            color: {tokens["text_secondary"]};
            font-size: 13px;
            line-height: 1.45;
        }}
        @keyframes csv-spin {{
            to {{ transform: rotate(360deg); }}
        }}
        </style>
        <div class="csv-analysis-loading" role="status">
            <div class="csv-analysis-spinner" aria-hidden="true"></div>
            <div>
                <div class="csv-analysis-title">Analysing your CSV...</div>
                <div class="csv-analysis-message">
                    Running Data Layer, Model Layer, and Report Layer.
                    This may take a few minutes.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _handle_uploaded_csv_submit(uploaded_file, tokens: dict) -> None:
    """Validate an uploaded CSV and run the dashboard upload pipeline."""
    if uploaded_file is None:
        st.markdown(
            empty_state_html(
                "Choose a CSV file first",
                "Select an OBD-II CSV file, then run the analysis again.",
                tokens,
                icon_name="help-circle",
                max_width="560px",
                margin="12px auto 0 auto",
            ),
            unsafe_allow_html=True,
        )
        return

    csv_bytes = uploaded_file.getvalue()
    if not csv_bytes.strip():
        _show_pipeline_error(
            "Empty File",
            "The uploaded file appears to be empty. "
            "Please upload a valid OBD-II CSV file.",
            tokens,
        )
        return

    st.session_state["uploaded_csv"] = uploaded_file
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    except EmptyDataError:
        _show_pipeline_error(
            "Empty File",
            "The uploaded file does not contain any CSV rows.",
            tokens,
        )
        return
    except Exception as exc:
        _show_pipeline_error(
            "Unreadable CSV",
            f"The uploaded file could not be parsed as CSV. {exc}",
            tokens,
        )
        return

    if df.empty:
        _show_pipeline_error(
            "Empty File",
            "The uploaded file does not contain any data rows.",
            tokens,
        )
        return

    cols_ok, missing_cols = validate_csv_columns(df)
    rows_ok = validate_csv_min_rows(df)

    if not cols_ok:
        items_html = "".join(
            f'<li style="margin-bottom:4px;">{html.escape(c)}</li>'
            for c in missing_cols
        )
        body = (
            f'<ul style="color:{tokens["danger_text"]};'
            f'font-size:14px;margin:8px 0 0 0;'
            f'padding-left:20px;line-height:1.7;">'
            f'{items_html}</ul>'
        )
        st.markdown(
            danger_card_html("Missing Required Columns", body, tokens),
            unsafe_allow_html=True,
        )
        return

    if not rows_ok:
        _show_pipeline_error(
            "Insufficient Data",
            "Your file contains fewer than 700 rows. Please upload at "
            "least 15 minutes of driving data recorded at 1 Hz.",
            tokens,
        )
        return

    _set_csv_analysis_running(True)
    _show_csv_analysis_loading(tokens)

    should_rerun = False
    try:
        try:
            with st.spinner("Analysing CSV..."):
                result = run_uploaded_csv_batch(
                    csv_bytes, uploaded_file.name
                )
        except TimeoutError:
            _show_pipeline_error(
                "Analysis Timed Out",
                "The analysis pipeline timed out. Please try uploading a "
                "shorter drive session.",
                tokens,
            )
            return
        except ModelBatchRunnerUnavailable as exc:
            _show_pipeline_error(
                "Model Analysis Unavailable", str(exc), tokens
            )
            return
        except UploadedCsvPipelineError as exc:
            _show_pipeline_error("Analysis Unavailable", str(exc), tokens)
            return
        except Exception as exc:
            _show_pipeline_error(
                "Analysis Unavailable",
                f"The analysis pipeline could not complete. {exc}",
                tokens,
            )
            return

        # report_generator.generate_report() never raises — an LLM
        # timeout or connection failure surfaces as an empty
        # anomaly_description instead of an exception, so detect that
        # fallback here rather than in a never-triggered except clause.
        components = {k: v for k, v in result.items() if k != "_data_source"}
        if not components or all(
            not c.get("anomaly_description") for c in components.values()
        ):
            _show_pipeline_error(
                "Analysis Timed Out",
                "The diagnostic report could not be generated in time. "
                "Please try again or upload a shorter drive session.",
                tokens,
            )
            return

        st.session_state["dashboard_data"] = result
        st.session_state["validated_df"] = df
        st.session_state["dashboard_mode"] = "dashboard"
        should_rerun = True
    finally:
        _set_csv_analysis_running(False)

    if should_rerun:
        st.rerun()


def _show_csv_uploader(tokens: dict) -> None:
    """CSV upload section with inline validation feedback (re-upload
    in dashboard)."""
    _recover_csv_analysis_running_state()
    st.markdown(
        f"""
        <style>
        /* ── Upload section card ── */
        .st-key-csv_upload_section {{
            background: {tokens["glass_surface"]} !important;
            backdrop-filter: blur(20px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(150%) !important;
            border: 1px solid {tokens["glass_border"]} !important;
            border-radius: 16px !important;
            box-shadow: 0 2px 12px {tokens["shadow"]} !important;
            padding: 20px 24px !important;
        }}
        /* ── Drop-zone ── */
        .st-key-csv_upload_section
            [data-testid="stFileUploader"] {{
            display: block !important;
            width: 100% !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] {{
            align-items: center !important;
            background: transparent !important;
            border: none !important;
            display: flex !important;
            justify-content: center !important;
            min-height: 58px !important;
            padding: 0 !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzoneInstructions"] {{
            display: none !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploader"] label {{
            display: none !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploader"] small {{
            display: none !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploader"] section {{
            align-items: center !important;
            display: flex !important;
            justify-content: center !important;
            padding: 0 !important;
            width: 100% !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] button {{
            align-items: center !important;
            background: {tokens["surface_alt"]} !important;
            border: 1.5px solid {tokens["border"]} !important;
            border-radius: 12px !important;
            color: transparent !important;
            display: flex !important;
            font-size: 0 !important;
            font-weight: 700 !important;
            justify-content: center !important;
            margin: 0 auto !important;
            min-height: 44px !important;
            min-width: 132px !important;
            padding: 0 24px !important;
            position: relative !important;
            width: 132px !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] button * {{
            color: transparent !important;
            display: none !important;
            font-size: 0 !important;
            line-height: 0 !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] button::after {{
            align-items: center !important;
            color: {tokens["text"]} !important;
            content: "Upload";
            display: flex !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            inset: 0 !important;
            justify-content: center !important;
            line-height: 1 !important;
            position: absolute !important;
            text-align: center !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] button:hover {{
            border-color: {tokens["accent"]} !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDropzone"] button:hover::after {{
            color: {tokens["accent"]} !important;
        }}
        .st-key-csv_upload_section
            [data-testid="stFileUploaderDeleteBtn"] {{
            display: none !important;
        }}
        /* ── Run Analysis button ── */
        .st-key-csv_submit_btn button {{
            background-color: {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            transition: opacity 0.15s ease !important;
        }}
        .st-key-csv_submit_btn button:hover {{
            opacity: 0.88 !important;
        }}
        .st-key-csv_submit_btn button:disabled {{
            cursor: progress !important;
            opacity: 0.64 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="csv_upload_section"):
        _show_csv_upload_heading(tokens)
        uploaded_file = st.file_uploader(
            "CSV file",
            type=["csv"],
            key="csv_file_uploader",
            label_visibility="collapsed",
        )
        analysis_running = bool(
            st.session_state.get(CSV_ANALYSIS_RUNNING_KEY, False)
        )
        submit_clicked = st.button(
            "Analysing..." if analysis_running else "Run Analysis",
            key="csv_submit_btn",
            use_container_width=True,
            disabled=analysis_running,
        )

    # ── Validation feedback ──
    if submit_clicked:
        _handle_uploaded_csv_submit(uploaded_file, tokens)


def _component_label(component_key: str) -> str:
    return COMPONENT_DISPLAY_NAMES.get(component_key, component_key)


def _set_default_state(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value


def _build_zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_data in files:
            zip_file.writestr(file_name, file_data)
    return output.getvalue()


def _join_file_name_parts(names: list[str]) -> str:
    clean_names = [clean_file_name_part(name) for name in names]
    clean_names = [name for name in clean_names if name != "not_available"]
    return "_".join(clean_names) or "report"


def _make_export_file_name(
    component_names: list[str],
    detail_names: list[str],
    download_date: str,
    file_kind: str,
    extension: str,
) -> str:
    parts = [
        _join_file_name_parts(component_names),
        _join_file_name_parts(detail_names),
        download_date,
        clean_file_name_part(file_kind),
    ]
    return "_".join(parts) + f".{extension}"


def _export_download_card_html(
    title: str,
    meta: str,
    icon_name: str,
    tokens: dict,
) -> str:
    icon_html = lucide_icon(icon_name, size=18, color=tokens["accent"])
    return (
        '<div class="export-download-card">'
        '<div class="export-download-icon">'
        f'{icon_html}'
        '</div>'
        '<div>'
        f'<div class="export-download-title">{html.escape(title)}</div>'
        f'<div class="export-download-meta">{html.escape(meta)}</div>'
        '</div>'
        '</div>'
    )


def _show_dashboard_export_controls(
    overview_components: list,
    tokens: dict,
) -> None:
    """Render PDF and CSV export controls at the bottom of overview."""
    component_lookup = {
        key: data for key, data, _ in overview_components
    }
    component_keys = list(component_lookup.keys())
    if not component_keys:
        return

    section_keys = list(EXPORT_SECTION_LABELS.keys())
    column_keys = list(CSV_COLUMNS)
    _set_default_state("overview_export_options_open", False)
    _set_default_state("overview_component_dropdown_open", False)
    _set_default_state("overview_pdf_dropdown_open", False)
    _set_default_state("overview_csv_dropdown_open", False)
    for component_key in component_keys:
        _set_default_state(f"overview_component_choice_{component_key}", True)
    for section_key in section_keys:
        _set_default_state(
            f"overview_pdf_choice_{section_key}",
            section_key in DEFAULT_EXPORT_SECTIONS,
        )
    for column_key in column_keys:
        _set_default_state(f"overview_csv_choice_{column_key}", True)

    st.markdown(
        f"""
        <style>
        .st-key-dashboard_export_panel {{
            max-width: 860px;
            margin: 4px auto 20px auto;
            background: {tokens["glass_surface"]} !important;
            border: 1px solid {tokens["glass_border"]} !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 12px {tokens["shadow"]} !important;
            padding: 14px 16px 16px 16px !important;
        }}
        .st-key-dashboard_export_panel button {{
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}
        .st-key-dashboard_export_panel
            [class*="st-key-overview_component_choice_"] {{
            margin-bottom: 0 !important;
        }}
        .export-quick-summary {{
            align-items: center;
            background: {tokens["surface_alt"]};
            border: 1px solid {tokens["border"]};
            border-radius: 10px;
            color: {tokens["text_secondary"]};
            display: flex;
            flex-wrap: wrap;
            font-size: 12px;
            gap: 8px;
            justify-content: space-between;
            margin: 0 0 10px 0;
            padding: 10px 12px;
        }}
        .export-quick-summary strong {{
            color: {tokens["text"]};
            font-weight: 700;
        }}
        .export-quick-summary span {{
            white-space: nowrap;
        }}
        .export-download-card {{
            align-items: center;
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            border-radius: 12px;
            display: flex;
            gap: 10px;
            margin: 2px 0 8px 0;
            min-height: 58px;
            padding: 12px 14px;
        }}
        .export-download-icon {{
            align-items: center;
            background: {tokens["accent_subtle"]};
            border-radius: 10px;
            display: inline-flex;
            height: 34px;
            justify-content: center;
            width: 34px;
        }}
        .export-download-title {{
            color: {tokens["text"]};
            font-size: 13px;
            font-weight: 700;
            line-height: 1.25;
        }}
        .export-download-meta {{
            color: {tokens["text_secondary"]};
            font-size: 11px;
            line-height: 1.35;
            margin-top: 2px;
        }}
        .st-key-overview_download_pdf button {{
            background: {tokens["accent"]} !important;
            border: 1.5px solid {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
            min-height: 44px !important;
        }}
        .st-key-overview_download_pdf button:hover {{
            background: {tokens["accent_hover"]} !important;
            border-color: {tokens["accent_hover"]} !important;
            color: {tokens["accent_contrast"]} !important;
        }}
        .st-key-overview_download_pdf button *,
        .st-key-overview_download_pdf button:hover * {{
            color: {tokens["accent_contrast"]} !important;
        }}
        .st-key-overview_download_csv button {{
            background: {tokens["accent"]} !important;
            border: 1.5px solid {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
            min-height: 44px !important;
        }}
        .st-key-overview_download_csv button:hover {{
            background: {tokens["accent_hover"]} !important;
            border-color: {tokens["accent_hover"]} !important;
            color: {tokens["accent_contrast"]} !important;
        }}
        .st-key-overview_download_csv button *,
        .st-key-overview_download_csv button:hover * {{
            color: {tokens["accent_contrast"]} !important;
        }}
        .st-key-export_options_toggle button {{
            background: transparent !important;
            border: 1px dashed {tokens["border"]} !important;
            color: {tokens["text_secondary"]} !important;
            margin-top: 10px !important;
            min-height: 42px !important;
        }}
        .st-key-export_options_toggle button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.06)} !important;
            border-color: {tokens["accent"]} !important;
            color: {tokens["accent"]} !important;
        }}
        .st-key-export_options_panel {{
            background: {tokens["surface_alt"]} !important;
            border: 1px solid {tokens["border"]} !important;
            border-radius: 12px !important;
            margin-top: 10px !important;
            padding: 12px !important;
        }}
        .export-options-title {{
            color: {tokens["text"]};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}
        .st-key-dashboard_export_panel
            [class*="st-key-export_dropdown_"] button {{
            background: {tokens["surface"]} !important;
            border: 1.5px solid {tokens["border"]} !important;
            color: {tokens["text"]} !important;
            min-height: 48px !important;
            text-align: left !important;
        }}
        .st-key-dashboard_export_panel
            [class*="st-key-export_dropdown_"] button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.06)} !important;
            border-color: {tokens["accent"]} !important;
            color: {tokens["accent"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="dashboard_export_panel"):
        st.markdown(
            section_heading_html(
                "Export Report",
                lucide_icon("file-text", size=20, color=tokens["accent"]),
                side_width=20,
            ),
            unsafe_allow_html=True,
        )

        selected_component_keys = [
            component_key for component_key in component_keys
            if st.session_state.get(
                f"overview_component_choice_{component_key}"
            )
        ]
        if not selected_component_keys:
            selected_component_keys = list(component_keys)
        selected_components = [
            component_lookup[component_key]
            for component_key in selected_component_keys
        ]
        selected_sections = [
            section_key for section_key in section_keys
            if st.session_state.get(f"overview_pdf_choice_{section_key}")
        ]
        selected_columns = [
            column_key for column_key in column_keys
            if st.session_state.get(f"overview_csv_choice_{column_key}")
        ]

        selected_sections = clean_export_sections(selected_sections)
        selected_columns = clean_csv_columns(selected_columns)
        download_date = datetime.now().strftime("%Y_%m_%d")
        component_names = [
            _component_label(component_key)
            for component_key in selected_component_keys
        ]
        pdf_detail_names = [
            EXPORT_SECTION_LABELS.get(section_key, section_key)
            for section_key in selected_sections
        ]
        csv_detail_names = [
            column_key.replace("_", " ").title()
            for column_key in selected_columns
        ]
        summary_html = (
            '<div class="export-quick-summary">'
            '<strong>Ready to download</strong>'
            f'<span>{len(selected_component_keys)} component(s)</span>'
            f'<span>{len(selected_sections)} PDF section(s)</span>'
            f'<span>{len(selected_columns)} CSV column(s)</span>'
            '</div>'
        )
        st.markdown(summary_html, unsafe_allow_html=True)

        pdf_col, csv_col = st.columns(2, gap="small")
        with pdf_col:
            try:
                if len(selected_components) == 1:
                    pdf_data = build_diagnostic_pdf_bytes(
                        selected_components[0],
                        selected_sections=selected_sections,
                    )
                    pdf_file_name = _make_export_file_name(
                        component_names,
                        pdf_detail_names,
                        download_date,
                        "diagnostic_report",
                        "pdf",
                    )
                    pdf_mime = "application/pdf"
                    pdf_label = "Download PDF"
                    pdf_card_meta = (
                        f"{len(selected_sections)} section(s), PDF file"
                    )
                else:
                    pdf_files = [
                        (
                            _make_export_file_name(
                                [_component_label(
                                    component_data.get("component", "")
                                )],
                                pdf_detail_names,
                                download_date,
                                "diagnostic_report",
                                "pdf",
                            ),
                            build_diagnostic_pdf_bytes(
                                component_data,
                                selected_sections=selected_sections,
                            ),
                        )
                        for component_data in selected_components
                    ]
                    pdf_data = _build_zip_bytes(pdf_files)
                    pdf_file_name = _make_export_file_name(
                        component_names,
                        pdf_detail_names,
                        download_date,
                        "pdf_reports",
                        "zip",
                    )
                    pdf_mime = "application/zip"
                    pdf_label = "Download PDF ZIP"
                    pdf_card_meta = (
                        f"{len(selected_components)} reports, ZIP file"
                    )
                st.markdown(
                    _export_download_card_html(
                        "Diagnostic report",
                        pdf_card_meta,
                        "file-text",
                        tokens,
                    ),
                    unsafe_allow_html=True,
                )
                st.download_button(
                    pdf_label,
                    data=pdf_data,
                    file_name=pdf_file_name,
                    mime=pdf_mime,
                    key="overview_download_pdf",
                    use_container_width=True,
                )
            except RuntimeError as err:
                st.markdown(
                    danger_card_html(
                        "PDF export unavailable",
                        _error_paragraph(str(err), tokens),
                        tokens,
                    ),
                    unsafe_allow_html=True,
                )

        with csv_col:
            if len(selected_components) == 1:
                csv_data = build_key_signals_csv_bytes(
                    selected_components[0],
                    selected_columns=selected_columns,
                )
                csv_file_name = _make_export_file_name(
                    component_names,
                    csv_detail_names,
                    download_date,
                    "key_signals",
                    "csv",
                )
                csv_mime = "text/csv"
                csv_label = "Download CSV"
                csv_card_meta = (
                    f"{len(selected_columns)} column(s), CSV file"
                )
            else:
                csv_files = [
                    (
                        _make_export_file_name(
                            [_component_label(
                                component_data.get("component", "")
                            )],
                            csv_detail_names,
                            download_date,
                            "key_signals",
                            "csv",
                        ),
                        build_key_signals_csv_bytes(
                            component_data,
                            selected_columns=selected_columns,
                        ),
                    )
                    for component_data in selected_components
                ]
                csv_data = _build_zip_bytes(csv_files)
                csv_file_name = _make_export_file_name(
                    component_names,
                    csv_detail_names,
                    download_date,
                    "csv_reports",
                    "zip",
                )
                csv_mime = "application/zip"
                csv_label = "Download CSV ZIP"
                csv_card_meta = (
                    f"{len(selected_components)} tables, ZIP file"
                )
            st.markdown(
                _export_download_card_html(
                    "Key signals table",
                    csv_card_meta,
                    "activity",
                    tokens,
                ),
                unsafe_allow_html=True,
            )
            st.download_button(
                csv_label,
                data=csv_data,
                file_name=csv_file_name,
                mime=csv_mime,
                key="overview_download_csv",
                use_container_width=True,
            )

        options_label = (
            "Hide export options"
            if st.session_state["overview_export_options_open"]
            else "Customize export options"
        )
        if st.button(
            options_label,
            key="export_options_toggle",
            use_container_width=True,
        ):
            st.session_state["overview_export_options_open"] = (
                not st.session_state["overview_export_options_open"]
            )
            st.rerun()

        if st.session_state["overview_export_options_open"]:
            with st.container(key="export_options_panel"):
                st.markdown(
                    '<div class="export-options-title">Export options</div>',
                    unsafe_allow_html=True,
                )
                open_text = (
                    "^" if st.session_state["overview_component_dropdown_open"]
                    else "v"
                )
                component_label = (
                    f"Report components "
                    f"({len(selected_component_keys)}/{len(component_keys)}) "
                    f"{open_text}"
                )
                if st.button(
                    component_label,
                    key="export_dropdown_components",
                    use_container_width=True,
                ):
                    dropdown_key = "overview_component_dropdown_open"
                    st.session_state[dropdown_key] = (
                        not st.session_state[dropdown_key]
                    )
                    st.rerun()

                if st.session_state["overview_component_dropdown_open"]:
                    st.markdown("Report components")
                    component_cols = st.columns(3, gap="small")
                    for idx, component_key in enumerate(component_keys):
                        with component_cols[idx % 3]:
                            st.checkbox(
                                _component_label(component_key),
                                key=(
                                    f"overview_component_choice_"
                                    f"{component_key}"
                                ),
                            )

                filter_col_1, filter_col_2 = st.columns(2, gap="small")
                with filter_col_1:
                    open_text = (
                        "^" if st.session_state["overview_pdf_dropdown_open"]
                        else "v"
                    )
                    pdf_label = (
                        f"PDF sections "
                        f"({len(selected_sections)}/{len(section_keys)}) "
                        f"{open_text}"
                    )
                    if st.button(
                        pdf_label,
                        key="export_dropdown_pdf",
                        use_container_width=True,
                    ):
                        st.session_state["overview_pdf_dropdown_open"] = (
                            not st.session_state["overview_pdf_dropdown_open"]
                        )
                        st.rerun()

                    if st.session_state["overview_pdf_dropdown_open"]:
                        st.markdown("PDF sections")
                        for section_key in section_keys:
                            st.checkbox(
                                EXPORT_SECTION_LABELS.get(
                                    section_key, section_key
                                ),
                                key=f"overview_pdf_choice_{section_key}",
                            )

                with filter_col_2:
                    open_text = (
                        "^" if st.session_state["overview_csv_dropdown_open"]
                        else "v"
                    )
                    csv_label = (
                        f"CSV columns "
                        f"({len(selected_columns)}/{len(column_keys)}) "
                        f"{open_text}"
                    )
                    if st.button(
                        csv_label,
                        key="export_dropdown_csv",
                        use_container_width=True,
                    ):
                        st.session_state["overview_csv_dropdown_open"] = (
                            not st.session_state["overview_csv_dropdown_open"]
                        )
                        st.rerun()

                    if st.session_state["overview_csv_dropdown_open"]:
                        st.markdown("CSV columns")
                        for column_key in column_keys:
                            label = column_key.replace("_", " ").title()
                            st.checkbox(
                                label,
                                key=f"overview_csv_choice_{column_key}",
                            )


def show_mock_data_warning(tokens: dict) -> None:
    """GL-132: Amber banner when any component is using mock data."""
    from anomaly_display import COMPONENT_DISPLAY_NAMES as _CDN
    data_source = get_data_source()
    mock_keys = [k for k, v in data_source.items() if v == "mock"]
    missing_keys = [k for k, v in data_source.items() if v == "missing"]
    if not mock_keys and not missing_keys:
        return
    parts = []
    if mock_keys:
        names = ", ".join(_CDN.get(k, k) for k in mock_keys)
        parts.append(f"<em>{names}</em> use demo values")
    if missing_keys:
        names = ", ".join(_CDN.get(k, k) for k in missing_keys)
        parts.append(f"<em>{names}</em> have no data yet")
    st.markdown(
        warning_banner_html(
            "Real pipeline output is incomplete: "
            + "; ".join(parts)
            + ".",
            tokens,
            label="Data source notice",
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Landing page (state A — no data uploaded yet)
# ---------------------------------------------------------------------------

def _show_landing_page(dark_mode: bool, tokens: dict) -> None:
    """Centered upload card with a secondary demo-data link."""
    _recover_csv_analysis_running_state()

    # ── Minimal nav bar: brand left, theme toggle right ──
    nav_left, nav_right = st.columns([10, 1])
    with nav_left:
        st.markdown(
            f'<div style="padding:8px 0 24px 0;">'
            f'<span style="font-size:17px;font-weight:700;'
            f'color:{tokens["text"]};">Granite Lifeline</span></div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        _show_theme_toggle(dark_mode, tokens)

    # ── Vertical centering spacer ──
    st.markdown(
        '<div style="height:clamp(24px, 6vh, 60px);"></div>',
        unsafe_allow_html=True,
    )

    # ── Hero text ──
    st.markdown(
        page_title_html(
            "Vehicle Health Analysis",
            tokens,
            subtitle=(
                "Upload your OBD-II drive data to get a full health "
                "diagnostic report."
            ),
            margin="0 auto 32px auto",
        ),
        unsafe_allow_html=True,
    )

    # ── Upload card CSS ──
    st.markdown(
        f"""
        <style>
        .st-key-landing_upload_card {{
            background: {tokens["glass_surface"]} !important;
            backdrop-filter: blur(20px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(150%) !important;
            border: 1px solid {tokens["glass_border"]} !important;
            border-radius: 20px !important;
            box-shadow: 0 4px 24px {tokens["shadow"]} !important;
            padding: 32px 32px 24px 32px !important;
            max-width: 560px !important;
            margin: 0 auto !important;
        }}
        /* Larger drop-zone */
        .st-key-landing_upload_card [data-testid="stFileUploader"] {{
            display: block !important;
            width: 100% !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploaderDropzone"] {{
            align-items: center !important;
            background: transparent !important;
            border: none !important;
            display: flex !important;
            justify-content: center !important;
            min-height: 64px !important;
            padding: 0 !important;
        }}
        .st-key-landing_upload_card
            [data-testid="stFileUploaderDropzoneInstructions"] {{
            display: none !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploader"] label {{
            display: none !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploader"] small {{
            display: none !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploader"] section {{
            align-items: center !important;
            display: flex !important;
            justify-content: center !important;
            padding: 0 !important;
            width: 100% !important;
        }}
        .st-key-landing_upload_card
            [data-testid="stFileUploaderDropzone"] button {{
            align-items: center !important;
            background: {tokens["surface_alt"]} !important;
            border: 1.5px solid {tokens["border"]} !important;
            border-radius: 12px !important;
            color: transparent !important;
            display: flex !important;
            font-size: 0 !important;
            font-weight: 700 !important;
            justify-content: center !important;
            margin: 0 auto !important;
            min-height: 46px !important;
            min-width: 140px !important;
            padding: 0 26px !important;
            position: relative !important;
            width: 140px !important;
        }}
        .st-key-landing_upload_card
            [data-testid="stFileUploaderDropzone"] button * {{
            color: transparent !important;
            display: none !important;
            font-size: 0 !important;
            line-height: 0 !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploaderDropzone"]
                button::after {{
            align-items: center !important;
            color: {tokens["text"]} !important;
            content: "Upload";
            display: flex !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            inset: 0 !important;
            justify-content: center !important;
            line-height: 1 !important;
            position: absolute !important;
            text-align: center !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploaderDropzone"]
                button:hover {{
            border-color: {tokens["accent"]} !important;
        }}
        .st-key-landing_upload_card [data-testid="stFileUploaderDropzone"]
                button:hover::after {{
            color: {tokens["accent"]} !important;
        }}
        .st-key-landing_upload_card
            [data-testid="stFileUploaderDeleteBtn"] {{
            display: none !important;
        }}
        /* Run Analysis button — full-width accent */
        .st-key-landing_run_btn button {{
            width: 100% !important;
            background-color: {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            padding: 13px 0 !important;
            margin-top: 4px !important;
            transition: opacity 0.15s ease !important;
        }}
        .st-key-landing_run_btn button:hover {{ opacity: 0.88 !important; }}
        .st-key-landing_run_btn button:disabled {{
            cursor: progress !important;
            opacity: 0.64 !important;
        }}
        /* Demo data link-button */
        .st-key-landing_demo_btn button {{
            background: transparent !important;
            color: {tokens["text_secondary"]} !important;
            border: none !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            text-decoration: underline !important;
            padding: 4px 8px !important;
            box-shadow: none !important;
        }}
        .st-key-landing_demo_btn button:hover {{
            color: {tokens["text"]} !important;
            background: transparent !important;
            border: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Upload card — centered via columns ──
    _, card_col, _ = st.columns([1, 4, 1])
    with card_col:
        with st.container(key="landing_upload_card"):
            _show_csv_upload_heading(tokens)
            uploaded_file = st.file_uploader(
                "CSV file",
                type=["csv"],
                key="landing_csv_uploader",
                label_visibility="collapsed",
            )
            # Run Analysis button — full width inside the card col
            analysis_running = bool(
                st.session_state.get(CSV_ANALYSIS_RUNNING_KEY, False)
            )
            submit_clicked = st.button(
                "Analysing..." if analysis_running else "Run Analysis",
                key="landing_run_btn",
                use_container_width=True,
                disabled=analysis_running,
            )

    # ── Validation feedback ──
    if submit_clicked:
        _handle_uploaded_csv_submit(uploaded_file, tokens)

    # ── Secondary: demo data entry ──
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;'
        f'max-width:560px;margin:24px auto 0 auto;">'
        f'<div style="flex:1;height:1px;background:{tokens["border"]};"></div>'
        f'<span style="font-size:12px;color:{tokens["text_secondary"]};'
        f'white-space:nowrap;">or</span>'
        f'<div style="flex:1;height:1px;background:{tokens["border"]};"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
        .st-key-landing_demo_btn button {{
            background: transparent !important;
            color: {tokens["text_secondary"]} !important;
            border: 1px solid {tokens["border"]} !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 9px 0 !important;
            box-shadow: none !important;
            transition: border-color 0.15s ease, color 0.15s ease !important;
        }}
        .st-key-landing_demo_btn button:hover {{
            border-color: {tokens["text"]} !important;
            color: {tokens["text"]} !important;
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    _, demo_col, _ = st.columns([1, 2, 1])
    with demo_col:
        if st.button(
            "Explore with demo data",
            key="landing_demo_btn",
            use_container_width=True,
        ):
            st.session_state.pop("dashboard_data", None)
            st.session_state.pop("validated_df", None)
            st.session_state.pop("uploaded_csv", None)
            st.session_state["dashboard_mode"] = "dashboard"
            st.rerun()

    show_footer(dark_mode)


# ---------------------------------------------------------------------------
# Dashboard page (state B — data loaded, show component cards)
# ---------------------------------------------------------------------------

def _show_dashboard_page(dark_mode: bool, tokens: dict) -> None:
    """Full dashboard view with component cards and collapsible re-upload."""
    mock_data = get_mock_data()

    # ── Back button + title row ──
    st.markdown(
        f"""
        <style>
        .st-key-dashboard_back_btn button {{
            background: transparent !important;
            color: {tokens["text_secondary"]} !important;
            border: none !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 6px 4px !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
            transition: color 0.15s ease !important;
        }}
        .st-key-dashboard_back_btn button:hover {{
            color: {tokens["text"]} !important;
            background: transparent !important;
            border: none !important;
        }}
        div.st-key-dashboard_what_if_btn button,
        .st-key-dashboard_what_if_btn button {{
            background: transparent !important;
            border: 1.5px solid {tokens["border"]} !important;
            border-radius: 10px !important;
            color: {tokens["text"]} !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            min-height: 38px !important;
            transition: border-color 0.15s ease, color 0.15s ease,
                        background 0.15s ease !important;
        }}
        div.st-key-dashboard_what_if_btn button *,
        div.st-key-dashboard_what_if_btn button:hover *,
        .st-key-dashboard_what_if_btn button *,
        .st-key-dashboard_what_if_btn button:hover * {{
            color: inherit !important;
        }}
        div.st-key-dashboard_what_if_btn button:hover,
        .st-key-dashboard_what_if_btn button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.07)} !important;
            border-color: {tokens["accent"]} !important;
            color: {tokens["accent"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    spacer_col, title_col, action_col, theme_col = st.columns([1, 8, 2, 1])
    with spacer_col:
        st.markdown(
            '<div style="height:8px;"></div>', unsafe_allow_html=True
        )
        if st.button(
            "\u2190",
            key="dashboard_back_btn",
            help="Back to upload",
        ):
            st.session_state["dashboard_mode"] = "landing"
            st.rerun()
    with title_col:
        with st.container(key="page_title_block"):
            latest = max(
                (c.get("timestamp", "") for c in mock_data.values()),
                default="",
            )
            if latest:
                try:
                    fmt = datetime.fromisoformat(
                        latest.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    fmt = latest
            else:
                fmt = "N/A"
            st.markdown(
                page_title_html(
                    "Vehicle Health Status",
                    tokens,
                    subtitle=f"Last checked: {fmt}",
                    margin="0 auto 4px auto",
                ),
                unsafe_allow_html=True,
            )
        st.markdown(
            """
            <style>
                .st-key-page_title_block,
                .st-key-page_title_block h1,
                .st-key-page_title_block [data-testid="stCaptionContainer"] {
                    text-align: center !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
    with action_col:
        st.markdown(
            '<div style="height:12px;"></div>', unsafe_allow_html=True
        )
        if st.button(
            "What-If Analysis",
            key="dashboard_what_if_btn",
            use_container_width=True,
        ):
            st.session_state["page"] = "what_if"
            st.rerun()
    with theme_col:
        _show_theme_toggle(dark_mode, tokens)

    if not mock_data:
        st.markdown(
            empty_state_html(
                "No components to display",
                "Upload a valid OBD-II CSV file or explore with demo data.",
                tokens,
                max_width="700px",
                margin="16px auto",
            ),
            unsafe_allow_html=True,
        )
        return

    # ── Mock-data warning ──
    show_mock_data_warning(tokens)

    # ── Status banner with inline legend ──
    data_source = get_data_source()
    _show_status_banner(mock_data, data_source, tokens)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Component cards ──
    sorted_components = get_overview_components()
    num = len(sorted_components)
    if num < 3:
        pad = 3 - num
        all_cols = st.columns([1] * pad + [2] * num + [1] * pad, gap="large")
        cols = all_cols[pad: pad + num]
    else:
        cols = st.columns(3, gap="large")

    # Scoped CSS for the detail button and what-if link button.
    st.markdown(
        f"""
        <style>
        [class*="st-key-card_btn_"] button {{
            width: 100% !important;
            background: {tokens["surface_alt"]} !important;
            color: {tokens["text"]} !important;
            border: 1.5px solid {tokens["border"]} !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            padding: 10px 0 !important;
            margin: 0 !important;
            transition: background 0.15s ease, border-color 0.15s ease,
                        color 0.15s ease !important;
        }}
        [class*="st-key-card_btn_"] button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.08)} !important;
            border-color: {tokens["accent"]} !important;
            color: {tokens["accent"]} !important;
        }}
        [class*="st-key-card_btn_"] button:active {{
            transform: scale(0.98) !important;
        }}
        [class*="st-key-card_btn_"] button *,
        [class*="st-key-card_btn_"] button:hover * {{
            color: inherit !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    for idx, (component_key, component_data, is_placeholder) in enumerate(
        sorted_components
    ):
        col_idx = idx % len(cols) if num >= 3 else idx
        with cols[col_idx]:
            risk_level = component_data.get("risk_level", "Unknown")
            badge_bg = {
                "High": tokens["risk_high"],
                "Medium": tokens["risk_medium"],
                "Low": tokens["risk_low"],
            }.get(risk_level, tokens["text_secondary"])

            has_score = not is_placeholder and risk_level in {
                "High", "Medium", "Low"
            }
            risk_pct = int(component_data.get("risk_score", 0) * 100)
            component_icon = lucide_icon(
                COMPONENT_ICONS.get(component_key, "activity"),
                size=20,
                color=badge_bg,
            )
            ring_size = 124
            ring_svg = progress_ring(
                risk_pct if has_score else 0,
                color=badge_bg,
                track_color=tokens["border"],
                anim_key=component_key,
                size=ring_size,
                stroke=10,
            )
            score_text = f"{risk_pct}%" if has_score else "N/A"
            score_label = "Risk Score" if has_score else "No Data"
            card_html = (
                f'<div style="'
                f'background:{tokens["glass_surface"]};'
                'backdrop-filter:blur(24px) saturate(160%);'
                '-webkit-backdrop-filter:blur(24px) saturate(160%);'
                f'border:1px solid {tokens["glass_border"]};'
                f'border-top:3px solid {badge_bg};'
                'border-radius:16px;'
                f'box-shadow:0 2px 12px {tokens["shadow"]};'
                'padding:22px 16px 16px 16px;min-height:260px;'
                'display:flex;flex-direction:column;align-items:center;'
                'justify-content:center;gap:20px;">'
                '<div style="display:flex;align-items:center;gap:10px;">'
                f'{component_icon}'
                f'<span style="color:{tokens["text"]};'
                f'font-size:15px;font-weight:700;">'
                f'{COMPONENT_DISPLAY_NAMES.get(component_key, component_key)}'
                '</span></div>'
                f'<div style="position:relative;'
                f'width:{ring_size}px;height:{ring_size}px;">'
                f'{ring_svg}'
                '<div style="position:absolute;inset:0;display:flex;'
                'flex-direction:column;align-items:center;'
                'justify-content:center;">'
                f'<span style="font-family:{FONT_MONO};font-size:30px;'
                f'font-weight:700;color:{tokens["text"]};line-height:1;">'
                f'{score_text}</span>'
                f'<span style="font-size:11px;'
                f'color:{tokens["text_secondary"]};'
                'margin-top:6px;font-weight:600;letter-spacing:0.5px;'
                f'text-transform:uppercase;">{score_label}</span>'
                '</div></div>'
                '<div style="width:100%;flex:1;"></div>'
                '</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(
                "View Details  \u2192",
                key=f"card_btn_{component_key}",
                use_container_width=True,
            ):
                st.session_state["selected_component"] = component_key
                st.session_state["page"] = "detail"
                st.rerun()

    _show_dashboard_export_controls(sorted_components, tokens)

    # ── Re-upload section (collapsed) ──
    st.markdown(
        "<div style='height:16px;'></div>", unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <style>
        .st-key-dashboard_reupload_expander {{
            border: 1px solid {tokens["border"]} !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }}
        .st-key-dashboard_reupload_toggle button {{
            align-items: center !important;
            background: {tokens["surface"]} !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: {tokens["text"]} !important;
            display: inline-flex !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            gap: 10px !important;
            justify-content: flex-start !important;
            line-height: 1.2 !important;
            margin: 0 !important;
            min-height: 44px !important;
            padding: 0 18px !important;
            text-align: left !important;
            width: 100% !important;
        }}
        .st-key-dashboard_reupload_toggle button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.06)} !important;
            border: none !important;
            color: {tokens["text"]} !important;
        }}
        .st-key-dashboard_reupload_toggle button p {{
            align-items: center !important;
            display: inline-flex !important;
            gap: 10px !important;
        }}
        .st-key-dashboard_reupload_body {{
            border-top: 1px solid {tokens["border"]} !important;
            padding: 18px 16px 20px 16px !important;
        }}
        .st-key-dashboard_reupload_body .st-key-csv_upload_section {{
            margin: 0 auto !important;
            max-width: 100% !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if "dashboard_reupload_open" not in st.session_state:
        st.session_state["dashboard_reupload_open"] = False

    with st.container(key="dashboard_reupload_expander"):
        is_open = st.session_state["dashboard_reupload_open"]
        arrow = "\u25be" if is_open else "\u203a"
        if st.button(
            f"{arrow} Upload new data",
            key="dashboard_reupload_toggle",
            use_container_width=True,
        ):
            st.session_state["dashboard_reupload_open"] = not is_open
            st.rerun()

        if st.session_state["dashboard_reupload_open"]:
            with st.container(key="dashboard_reupload_body"):
                _show_csv_uploader(tokens)

    show_footer(dark_mode)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def show_overview_page() -> None:
    """Route between landing (state A) and dashboard (state B)."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    # State B is active when the user has explicitly uploaded data OR
    # clicked "explore with demo data".
    mode = st.session_state.get("dashboard_mode", "landing")

    if mode == "dashboard":
        _show_dashboard_page(dark_mode, tokens)
    else:
        _show_landing_page(dark_mode, tokens)
