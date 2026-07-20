"""Overview page — vehicle health summary with CSV upload entry point."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from anomaly_display import COMPONENT_DISPLAY_NAMES
from csv_validator import validate_csv_columns, validate_csv_min_rows
from data_store import get_data_source, get_mock_data, get_overview_components
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
    show_footer,
    warning_banner_html,
)
# Note: show_mock_data_warning is defined in this file, not ui_components


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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


def _show_status_banner(mock_data: dict, tokens: dict) -> None:
    """Status banner with inline risk legend chips."""
    has_high = any(c.get("risk_level") == "High" for c in mock_data.values())

    if has_high:
        banner_bg = hex_to_rgba(tokens["risk_high"], 0.10)
        banner_border = hex_to_rgba(tokens["risk_high"], 0.30)
        icon_svg = lucide_icon("alert-triangle", size=18, color=tokens["danger_text"])
        status_text = "Attention needed — one or more components require urgent action"
        text_color = tokens["danger_text"]
    else:
        banner_bg = hex_to_rgba(tokens["risk_low"], 0.10)
        banner_border = hex_to_rgba(tokens["risk_low"], 0.30)
        icon_svg = lucide_icon("check-square", size=18, color=tokens["risk_low"])
        status_text = "All systems within normal range"
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
        f'<div style="background:{banner_bg};border:1px solid {banner_border};'
        'border-radius:14px;padding:14px 20px;margin:16px auto;max-width:860px;'
        'display:flex;align-items:center;justify-content:space-between;'
        f'gap:16px;flex-wrap:wrap;box-shadow:0 2px 8px {tokens["shadow"]};">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'{icon_svg}'
        f'<span style="font-weight:600;font-size:14px;color:{text_color};">'
        f'{status_text}</span></div>'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'{legend_chips}</div></div>',
        unsafe_allow_html=True,
    )


def _show_csv_uploader(tokens: dict) -> None:
    """CSV upload section with inline validation feedback."""
    # Section header
    st.markdown(
        f'<div style="margin:40px 0 14px 0;display:flex;align-items:center;'
        f'gap:10px;">'
        f'{lucide_icon("file-text", size=18, color=tokens["text_secondary"])}'
        f'<span style="font-size:13px;font-weight:700;letter-spacing:0.4px;'
        f'text-transform:uppercase;color:{tokens["text_secondary"]};">'
        'Analyze Your Own Drive Data</span></div>',
        unsafe_allow_html=True,
    )

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
            [data-testid="stFileUploaderDropzone"] {{
            border: 1.5px dashed {tokens["border"]} !important;
            border-radius: 10px !important;
            background: {tokens["surface_alt"]} !important;
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
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="csv_upload_section"):
        left_col, right_col = st.columns([3, 1], gap="large")
        with left_col:
            st.markdown(
                f'<p style="color:{tokens["text"]};font-size:14px;'
                f'font-weight:600;margin:0 0 4px 0;">Upload OBD-II CSV file</p>'
                f'<p style="color:{tokens["text_secondary"]};font-size:13px;'
                f'line-height:1.5;margin:0 0 12px 0;">'
                "Upload a raw OBD-II CSV file from your vehicle. "
                "Required columns include Time, Engine RPM, Vehicle Speed, "
                "Coolant Temperature, and other standard OBD-II signals. "
                "Minimum 700 rows (≈15 min at 1\u202fHz)."
                "</p>",
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Upload OBD-II CSV file",
                type=["csv"],
                key="csv_file_uploader",
                label_visibility="collapsed",
            )
        with right_col:
            st.markdown(
                '<div style="height:52px;"></div>', unsafe_allow_html=True
            )
            submit_clicked = st.button(
                "Run Analysis",
                key="csv_submit_btn",
                use_container_width=True,
            )

    # ── Validation feedback ──
    if submit_clicked:
        if uploaded_file is None:
            st.warning("Please select a CSV file before clicking Run Analysis.")
            return

        st.session_state["uploaded_csv"] = uploaded_file
        try:
            df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
        except Exception:
            df = pd.DataFrame()

        cols_ok, missing_cols = validate_csv_columns(df)
        rows_ok = validate_csv_min_rows(df)

        if not cols_ok:
            items_html = "".join(
                f'<li style="margin-bottom:4px;">{c}</li>'
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
        elif not rows_ok:
            body = (
                f'<p style="color:{tokens["danger_text"]};'
                f'font-size:14px;margin:8px 0 0 0;line-height:1.5;">'
                "Your file contains fewer than 700 rows. "
                "Please upload at least 15 minutes of driving data "
                "recorded at 1\u202fHz."
                "</p>"
            )
            st.markdown(
                danger_card_html("Insufficient Data", body, tokens),
                unsafe_allow_html=True,
            )
        else:
            st.session_state["validated_df"] = df
            st.success(
                f"File validated successfully. "
                f"{len(df)} rows loaded. Running analysis\u2026"
            )


def show_mock_data_warning(tokens: dict) -> None:
    """GL-132: Amber banner when any component is using mock data."""
    from anomaly_display import COMPONENT_DISPLAY_NAMES as _CDN
    data_source = get_data_source()
    mock_keys = [k for k, v in data_source.items() if v == "mock"]
    if not mock_keys:
        return
    names = ", ".join(_CDN.get(k, k) for k in mock_keys)
    st.markdown(
        warning_banner_html(
            f"Real pipeline output is not yet available for: "
            f"<em>{names}</em>. "
            "These cards show placeholder values from the test dataset.",
            tokens,
            label="Mock data active",
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def show_overview_page() -> None:
    """Display the Overview Page with component health summary."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]
    mock_data = get_mock_data()

    # ── Title row ──
    spacer_col, title_col, theme_col = st.columns([1, 10, 1])
    with title_col:
        with st.container(key="page_title_block"):
            st.title("Vehicle Health Status")
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
                st.caption(f"Last checked: {fmt}")
            else:
                st.caption("Last checked: N/A")
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
    with theme_col:
        _show_theme_toggle(dark_mode, tokens)

    # ── Empty state ──
    if not mock_data:
        info_icon = lucide_icon("info", size=20, color=tokens["text_secondary"])
        st.markdown(
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:14px;padding:24px 16px;margin:16px 0;'
            f'color:{tokens["text_secondary"]};'
            'display:flex;align-items:center;justify-content:center;gap:14px;">'
            f'{info_icon}'
            f'<span style="font-weight:600;color:{tokens["text_secondary"]};">'
            'No components to display</span></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Mock-data warning ──
    show_mock_data_warning(tokens)

    # ── Status banner with inline legend ──
    _show_status_banner(mock_data, tokens)

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

    # Scoped CSS for the detail button inside each card
    st.markdown(
        f"""
        <style>
        [class*="st-key-card_btn_"] button {{
            width: 100% !important;
            background: transparent !important;
            color: {tokens["text_secondary"]} !important;
            border: none !important;
            border-top: 1px solid {tokens["border"]} !important;
            border-radius: 0 0 16px 16px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            padding: 12px 0 !important;
            margin: 0 !important;
            transition: color 0.15s ease, background 0.15s ease !important;
        }}
        [class*="st-key-card_btn_"] button:hover {{
            background: {hex_to_rgba(tokens["accent"], 0.06)} !important;
            color: {tokens["accent"]} !important;
        }}
        [class*="st-key-card_btn_"] button:active {{
            transform: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    for idx, (component_key, component_data, _) in enumerate(sorted_components):
        col_idx = idx % len(cols) if num >= 3 else idx
        with cols[col_idx]:
            risk_level = component_data.get("risk_level", "Unknown")
            badge_bg = {
                "High": tokens["risk_high"],
                "Medium": tokens["risk_medium"],
                "Low": tokens["risk_low"],
            }.get(risk_level, tokens["text_secondary"])

            risk_pct = int(component_data.get("risk_score", 0) * 100)
            component_icon = lucide_icon(
                COMPONENT_ICONS.get(component_key, "activity"),
                size=20,
                color=badge_bg,
            )
            ring_size = 124
            ring_svg = progress_ring(
                risk_pct,
                color=badge_bg,
                track_color=tokens["border"],
                anim_key=component_key,
                size=ring_size,
                stroke=10,
            )
            # Card: top color stripe indicates risk level; no left bar
            card_html = (
                f'<div style="'
                f'background:{tokens["glass_surface"]};'
                'backdrop-filter:blur(24px) saturate(160%);'
                '-webkit-backdrop-filter:blur(24px) saturate(160%);'
                f'border:1px solid {tokens["glass_border"]};'
                f'border-top:3px solid {badge_bg};'
                'border-radius:16px;'
                f'box-shadow:0 2px 12px {tokens["shadow"]};'
                'padding:22px 16px 0 16px;min-height:260px;'
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
                'flex-direction:column;align-items:center;justify-content:center;">'
                f'<span style="font-family:{FONT_MONO};font-size:30px;'
                f'font-weight:700;color:{tokens["text"]};line-height:1;">'
                f'{risk_pct}%</span>'
                f'<span style="font-size:11px;color:{tokens["text_secondary"]};'
                'margin-top:6px;font-weight:600;letter-spacing:0.5px;'
                'text-transform:uppercase;">Risk Score</span>'
                '</div></div>'
                '<div style="width:100%;"></div>'
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

    # ── CSV uploader (below cards) ──
    _show_csv_uploader(tokens)

    show_footer(dark_mode)
