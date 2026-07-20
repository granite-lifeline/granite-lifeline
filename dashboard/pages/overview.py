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
    show_mock_data_warning,
    warning_banner_html,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _show_theme_toggle(dark_mode: bool, tokens: dict) -> None:
    """Render the dark/light-mode icon button."""
    st.markdown(
        '<div style="height:8px;"></div>', unsafe_allow_html=True
    )
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
                box-shadow: 0 1px 2px {tokens["shadow"]} !important;
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


def _show_csv_uploader(tokens: dict) -> None:
    """GL-256/258: CSV upload section with inline validation feedback.

    Uses a native Streamlit container styled as a glass card via CSS
    keyed to ``st-key-csv_upload_section``.  The file_uploader label is
    hidden with ``label_visibility="collapsed"`` so it never appears in
    the DOM and cannot cause text overlap.
    """
    # Scoped CSS — targets only the upload section container and its
    # children, never leaking to other expanders or widgets on the page.
    st.markdown(
        f"""
        <style>
        /* ── Upload section card ── */
        .st-key-csv_upload_section {{
            background: {tokens["glass_surface"]} !important;
            backdrop-filter: blur(20px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(150%) !important;
            border: 1px solid {tokens["glass_border"]} !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px {tokens["shadow"]} !important;
            padding: 20px 24px 16px 24px !important;
            margin: 16px 0 !important;
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
            width: 100% !important;
            background-color: {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            padding: 10px 0 !important;
            margin-top: 8px !important;
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
        # Section header
        upload_icon = lucide_icon("file-text", size=18, color=tokens["accent"])
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'margin-bottom:8px;">'
            f'{upload_icon}'
            f'<span style="font-size:15px;font-weight:600;'
            f'color:{tokens["text"]};">Upload your OBD-II data</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Helper text
        st.markdown(
            f'<p style="color:{tokens["text_secondary"]};font-size:13px;'
            f'line-height:1.5;margin:0 0 14px 0;">'
            "Upload a raw OBD-II CSV file recorded from your vehicle. "
            "The file must contain columns including: Time, "
            "Engine RPM\u00a0[RPM], Vehicle Speed Sensor\u00a0[km/h], "
            "Engine Coolant Temperature\u00a0[\u00b0C], and other "
            "standard OBD-II signals."
            "</p>",
            unsafe_allow_html=True,
        )
        # File picker — label hidden so it never renders in the DOM
        uploaded_file = st.file_uploader(
            "Upload OBD-II CSV file",
            type=["csv"],
            key="csv_file_uploader",
            label_visibility="collapsed",
        )
        # Submit button
        submit_clicked = st.button(
            "Run Analysis",
            key="csv_submit_btn",
            use_container_width=True,
        )

    # ── Validation feedback (rendered outside the card container) ──
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
            'backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);'
            'border-radius:12px;padding:24px 16px;margin:16px 0;'
            f'color:{tokens["text_secondary"]};'
            'display:flex;align-items:center;justify-content:center;'
            'gap:14px;'
            f'box-shadow:0 8px 28px {tokens["shadow"]},'
            'inset 0 1px 0 rgba(255,255,255,0.10);">'
            f'{info_icon}'
            f'<span style="font-weight:600;color:{tokens["text_secondary"]};">'
            'No components to display</span></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Mock-data warning ──
    show_mock_data_warning(tokens)

    # ── Status banner ──
    has_high = any(
        c.get("risk_level") == "High" for c in mock_data.values()
    )
    if has_high:
        alert_icon = lucide_icon(
            "alert-triangle", size=20, color=tokens["danger_text"]
        )
        st.markdown(
            f'<div style="background:{hex_to_rgba(tokens["risk_high"],0.12)};'
            f'border:1px solid {hex_to_rgba(tokens["risk_high"],0.35)};'
            'backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);'
            'border-radius:12px;padding:12px 16px;margin:16px auto;'
            'max-width:700px;'
            f'color:{tokens["danger_text"]};'
            'display:flex;align-items:center;justify-content:center;'
            'gap:14px;'
            f'box-shadow:0 8px 28px {tokens["shadow"]},'
            'inset 0 1px 0 rgba(255,255,255,0.10);">'
            f'{alert_icon}'
            f'<span style="font-weight:600;color:{tokens["danger_text"]};">'
            'Attention needed \u2014 one or more components require '
            'urgent action</span></div>',
            unsafe_allow_html=True,
        )
    else:
        ok_icon = lucide_icon(
            "check-square", size=20, color=tokens["risk_low"]
        )
        st.markdown(
            f'<div style="background:{hex_to_rgba(tokens["risk_low"],0.12)};'
            f'border:1px solid {hex_to_rgba(tokens["risk_low"],0.35)};'
            'backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);'
            'border-radius:12px;padding:12px 16px;margin:16px auto;'
            'max-width:700px;'
            f'color:{tokens["risk_low"]};'
            'display:flex;align-items:center;justify-content:center;'
            'gap:14px;'
            f'box-shadow:0 8px 28px {tokens["shadow"]},'
            'inset 0 1px 0 rgba(255,255,255,0.10);">'
            f'{ok_icon}'
            f'<span style="font-weight:600;color:{tokens["risk_low"]};">'
            'All systems within normal range</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Risk legend ──
    st.markdown(
        f'<div style="display:flex;justify-content:center;gap:24px;'
        f'margin:16px 0;font-size:14px;color:{tokens["text_secondary"]};">'
        + "".join(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="width:12px;height:12px;border-radius:50%;'
            f'background:{color};"></div><span>{label}</span></div>'
            for label, color in [
                ("High Risk", tokens["risk_high"]),
                ("Medium Risk", tokens["risk_medium"]),
                ("Low Risk", tokens["risk_low"]),
                ("Unknown", tokens["text_secondary"]),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── CSV uploader (GL-256 / GL-258) ──
    _show_csv_uploader(tokens)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Component cards ──
    sorted_components = get_overview_components()
    num = len(sorted_components)
    if num < 3:
        pad = 3 - num
        all_cols = st.columns([1] * pad + [2] * num + [1] * pad, gap="large")
        cols = all_cols[pad: pad + num]
    else:
        cols = st.columns(3, gap="large")

    for idx, (component_key, component_data, _) in enumerate(
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

            risk_pct = int(component_data.get("risk_score", 0) * 100)
            component_icon = lucide_icon(
                COMPONENT_ICONS.get(component_key, "activity"),
                size=22,
                color=badge_bg,
            )
            ring_size = 132
            ring_svg = progress_ring(
                risk_pct,
                color=badge_bg,
                track_color=tokens["border"],
                anim_key=component_key,
                size=ring_size,
                stroke=10,
            )
            card_html = (
                f'<div style="position:relative;'
                f'background:{tokens["glass_surface"]};'
                'backdrop-filter:blur(24px) saturate(160%);'
                '-webkit-backdrop-filter:blur(24px) saturate(160%);'
                f'border:1px solid {tokens["glass_border"]};'
                'border-radius:18px;'
                f'box-shadow:0 8px 28px {tokens["shadow"]},'
                'inset 0 1px 0 rgba(255,255,255,0.10);'
                'padding:24px 16px;margin-bottom:16px;min-height:280px;'
                'display:flex;flex-direction:column;align-items:center;'
                'justify-content:center;gap:24px;overflow:hidden;">'
                f'<div style="position:absolute;left:0;top:0;bottom:0;'
                f'width:4px;background:{badge_bg};"></div>'
                '<div style="display:flex;align-items:center;gap:12px;">'
                f'<div style="display:flex;">{component_icon}</div>'
                f'<h3 style="margin:0;color:{tokens["text"]};'
                f'font-size:22px;font-weight:700;">'
                f'{COMPONENT_DISPLAY_NAMES.get(component_key, component_key)}'
                '</h3></div>'
                f'<div style="position:relative;'
                f'width:{ring_size}px;height:{ring_size}px;">'
                f'{ring_svg}'
                '<div style="position:absolute;inset:0;display:flex;'
                'flex-direction:column;align-items:center;'
                'justify-content:center;">'
                f'<span style="font-family:{FONT_MONO};font-size:32px;'
                f'font-weight:700;color:{tokens["text"]};line-height:1;">'
                f'{risk_pct}%</span>'
                f'<span style="font-size:12px;color:{tokens["text_secondary"]};'
                'margin-top:8px;font-weight:600;letter-spacing:0.5px;'
                'text-transform:uppercase;">Risk Score</span>'
                '</div></div></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(
                "View Details  \u2192",
                key=f"btn_{component_key}",
                use_container_width=True,
            ):
                st.session_state["selected_component"] = component_key
                st.session_state["page"] = "detail"
                st.rerun()

    show_footer(dark_mode)
