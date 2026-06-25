"""
Granite Lifeline Dashboard - Overview Page

Displays vehicle health status with component risk levels and navigation
to detailed diagnostic reports.
"""

import base64
import math
import time
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
from data_loader import load_dashboard_data

COMPONENT_DISPLAY_NAMES = {
    "cooling_system_stress": "Cooling System",
    "air_intake_maf_anomaly": "Air Intake System",
    "accelerator_pedal_sensor": "Accelerator Pedal"
}

SIGNAL_DISPLAY_NAMES = {
    "coolant_temp": "Coolant Temperature",
    "coolant_slope": "Coolant Slope",
    "maf": "Mass Airflow",
    "map": "Intake Pressure",
    "accel_pedal_d": "Pedal Sensor D",
    "accel_pedal_e": "Pedal Sensor E"
}

# Load report data from Report Layer
try:
    REPORT_DATA = load_dashboard_data("dashboard/tests/ui_required_data.json")
except Exception as e:
    st.error(f"Failed to load report data: {e}")
    REPORT_DATA = {}

# Fallback MOCK_DATA for development (kept for reference)
MOCK_DATA_FALLBACK = {
    "cooling_system_stress": {
        "timestamp": "2026-06-16T12:00:00Z",
        "risk_score": 0.86,
        "risk_level": "High",
        "component": "cooling_system_stress",
        "prediction_confidence": 0.88,
        "key_signals": [
            {
                "feature": "coolant_temp",
                "value": 104.0,
                "unit": "°C",
                "reference_range": [90.0, 95.0]
            },
            {
                "feature": "coolant_slope",
                "value": 3.4,
                "unit": "°C/min",
                "reference_range": [0.0, 2.0]
            }
        ],
        "risk_history": [
            {"timestamp": "2026-06-15T08:00:00Z", "risk_score": 0.45},
            {"timestamp": "2026-06-15T12:00:00Z", "risk_score": 0.52},
            {"timestamp": "2026-06-15T16:00:00Z", "risk_score": 0.61},
            {"timestamp": "2026-06-16T08:00:00Z", "risk_score": 0.70},
            {"timestamp": "2026-06-16T12:00:00Z", "risk_score": 0.86}
        ],
        "anomaly_description": "The coolant temperature is above its reference range and is rising faster than expected. High risk means the vehicle may need prompt attention.",
        "possible_cause": "This could be related to cooling system stress, such as low coolant, radiator problems, or water pump degradation.",
        "recommended_action": [
            "Avoid heavy driving if it is safe to do so.",
            "Check the coolant level when the engine is cool.",
            "Ask a mechanic to inspect the cooling system as soon as possible."
        ]
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
            {"timestamp": "2026-06-15T07:00:00Z", "risk_score": 0.30},
            {"timestamp": "2026-06-15T11:00:00Z", "risk_score": 0.35},
            {"timestamp": "2026-06-15T15:00:00Z", "risk_score": 0.40},
            {"timestamp": "2026-06-16T07:00:00Z", "risk_score": 0.48},
            {"timestamp": "2026-06-16T11:00:00Z", "risk_score": 0.61}
        ],
        "anomaly_description": "The airflow reading is higher than its reference range, while the intake pressure reading is still inside its reference range. Medium risk means the vehicle should be checked soon, but it is not an immediate emergency.",
        "possible_cause": "This may indicate an airflow sensor issue, a dirty air filter, or an air intake leak. The result is not a confirmed fault.",
        "recommended_action": [
            "Ask a mechanic to inspect the air intake system soon.",
            "Check whether the air filter needs cleaning or replacement.",
            "Keep watching for rough idling, poor acceleration, or warning lights."
        ]
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
            {"timestamp": "2026-06-15T06:00:00Z", "risk_score": 0.18},
            {"timestamp": "2026-06-15T10:00:00Z", "risk_score": 0.20},
            {"timestamp": "2026-06-15T14:00:00Z", "risk_score": 0.21},
            {"timestamp": "2026-06-16T06:00:00Z", "risk_score": 0.22},
            {"timestamp": "2026-06-16T10:00:00Z", "risk_score": 0.22}
        ],
        "anomaly_description": "The accelerator pedal sensor reading does not show a strong abnormal pattern right now. Low risk means the issue does not look urgent.",
        "possible_cause": "This could be related to normal sensor movement or a short sensor delay. The current data does not strongly suggest a confirmed fault.",
        "recommended_action": [
            "Continue monitoring the dashboard.",
            "If the warning appears repeatedly, ask a mechanic to check the pedal sensor."
        ]
    }
}

# Use REPORT_DATA as primary data source, fallback to MOCK_DATA_FALLBACK if loading fails
MOCK_DATA = REPORT_DATA if REPORT_DATA else MOCK_DATA_FALLBACK

RISK_PRIORITY = {"High": 0, "Medium": 1, "Low": 2}

THEME_TOKENS = {
    "light": {
        "bg": "#f5f5f7",
        "surface": "#ffffff",
        "surface_alt": "#f5f5f7",
        "border": "#d2d2d7",
        "text": "#1d1d1f",
        "text_secondary": "#6e6e73",
        "accent": "#0f62fe",
        "accent_contrast": "#ffffff",
        "shadow": "rgba(0, 0, 0, 0.08)",
        "risk_high": "#da1e28",
        "risk_medium": "#ff832b",
        "risk_low": "#24a148",
        "danger_bg": "#fff1f1",
        "danger_border": "#ffd7d9",
        "danger_text": "#a2191f",
    },
    "dark": {
        "bg": "#1c1c1e",
        "surface": "#2c2c2e",
        "surface_alt": "#252527",
        "border": "#3a3a3c",
        "text": "#f5f5f7",
        "text_secondary": "#98989d",
        "accent": "#4589ff",
        "accent_contrast": "#ffffff",
        "shadow": "rgba(0, 0, 0, 0.4)",
        "risk_high": "#fa4d56",
        "risk_medium": "#ff832b",
        "risk_low": "#42be65",
        "danger_bg": "#2c1618",
        "danger_border": "#5e2125",
        "danger_text": "#ff8389",
    },
}

FONT_SANS = (
    "'IBM Plex Sans', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)
FONT_MONO = "'IBM Plex Mono', 'SF Mono', Consolas, monospace"

# Hand-coded Lucide-style icon glyphs (placeholder set, swappable via
# the same lucide_icon() call sites once a final icon set is sourced).
ICONS = {
    "sun": (
        '<circle cx="12" cy="12" r="5"></circle>'
        '<line x1="12" y1="1" x2="12" y2="3"></line>'
        '<line x1="12" y1="21" x2="12" y2="23"></line>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>'
        '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>'
        '<line x1="1" y1="12" x2="3" y2="12"></line>'
        '<line x1="21" y1="12" x2="23" y2="12"></line>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>'
        '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>'
    ),
    "moon": (
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z">'
        '</path>'
    ),
    "trending-up": (
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>'
        '<polyline points="17 6 23 6 23 12"></polyline>'
    ),
    "activity": (
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>'
    ),
    "file-text": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 '
        '2-2V8z"></path>'
        '<polyline points="14 2 14 8 20 8"></polyline>'
        '<line x1="16" y1="13" x2="8" y2="13"></line>'
        '<line x1="16" y1="17" x2="8" y2="17"></line>'
        '<polyline points="10 9 9 9 8 9"></polyline>'
    ),
    "alert-triangle": (
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 '
        '0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>'
        '<line x1="12" y1="9" x2="12" y2="13"></line>'
        '<line x1="12" y1="17" x2="12.01" y2="17"></line>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"></circle>'
        '<line x1="12" y1="16" x2="12" y2="12"></line>'
        '<line x1="12" y1="8" x2="12.01" y2="8"></line>'
    ),
    "help-circle": (
        '<circle cx="12" cy="12" r="10"></circle>'
        '<path d="M9.09 9a3 3 0 1 1 5.83 1c0 2-3 3-3 3"></path>'
        '<line x1="12" y1="17" x2="12.01" y2="17"></line>'
    ),
    "check-square": (
        '<polyline points="9 11 12 14 22 4"></polyline>'
        '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 '
        '2-2h11"></path>'
    ),
    "droplet": (
        '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>'
    ),
    "wind": (
        '<path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 '
        '14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"></path>'
    ),
    "zap": (
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2">'
        '</polygon>'
    ),
}

# Per-component icon, keyed by MOCK_DATA component key (falls back to a
# generic icon for components not in this map).
COMPONENT_ICONS = {
    "cooling_system_stress": "droplet",
    "air_intake_maf_anomaly": "wind",
    "accelerator_pedal_sensor": "zap",
}


def lucide_icon(
    name: str,
    size: int = 20,
    color: str = "currentColor",
    stroke_width: float = 2,
) -> str:
    """Render a Lucide-style icon as an inline SVG string."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS[name]}</svg>'
    )


def svg_data_uri(svg_markup: str) -> str:
    """Encode inline SVG markup as a base64 data URI."""
    encoded = base64.b64encode(svg_markup.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def progress_ring(
    pct: int,
    color: str,
    track_color: str,
    anim_key: str,
    size: int = 64,
    stroke: int = 7,
) -> str:
    """Render an animated circular progress ring as inline SVG."""
    radius = (size - stroke) / 2
    center = size / 2
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - pct / 100)
    anim_name = f"ring-fill-{anim_key}"
    return (
        f'<svg width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" '
        f'style="transform: rotate(-90deg); flex-shrink: 0;">'
        f'<circle cx="{center}" cy="{center}" r="{radius}" fill="none" '
        f'stroke="{track_color}" stroke-width="{stroke}"></circle>'
        f'<circle cx="{center}" cy="{center}" r="{radius}" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{circumference:.2f}" '
        f'style="animation: {anim_name} 1s ease-out forwards;">'
        f'</circle>'
        f'<style>@keyframes {anim_name} '
        f'{{ to {{ stroke-dashoffset: {offset:.2f}; }} }}</style>'
        f'</svg>'
    )


def get_theme() -> dict:
    """Return the active Pro theme's token dict for the current mode."""
    mode = "dark" if st.session_state.get("dark_mode", False) else "light"
    return THEME_TOKENS[mode]


def show_divider(dark_mode: bool, margin: str = "36px auto"):
    """Display a hairline divider clipped to content width."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]
    divider_html = f"""
    <div style="
        width: 100%;
        max-width: 1100px;
        margin: {margin};
        border-top: 1px solid {tokens["border"]};
    "></div>
    """
    st.markdown(divider_html, unsafe_allow_html=True)


def show_icon_heading(title: str, icon_svg: str, center: bool = False):
    """Display an H2 heading with an inline icon."""
    justify = "center" if center else "flex-start"
    heading_html = f"""
    <h2 style="
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: {justify};
        gap: 20px;
    ">
        {icon_svg}{title}
    </h2>
    """
    st.markdown(heading_html, unsafe_allow_html=True)


def apply_theme(dark_mode: bool):
    """Apply the Pro theme's CSS for the given light/dark mode."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    font_link = (
        '<link href="https://fonts.googleapis.com/css2?'
        'family=IBM+Plex+Sans:wght@400;500;600;700'
        '&family=IBM+Plex+Mono:wght@500;600;700'
        '&family=Noto+Sans+SC:wght@400;500;700'
        '&display=swap" rel="stylesheet">'
    )
    font_family = FONT_SANS

    theme_css = f"""
    {font_link}
    <style>
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background-color: {tokens["bg"]} !important;
        }}
        .main {{
            background-color: {tokens["bg"]} !important;
        }}
        .main .block-container {{
            background-color: {tokens["bg"]} !important;
            font-family: {font_family} !important;
            padding-top: 2.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 1100px !important;
        }}
        h1, h2, h3 {{
            color: {tokens["text"]} !important;
            font-weight: 700 !important;
            font-family: {font_family} !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}
        h1 > span:first-child,
        h2 > span:first-child,
        h3 > span:first-child {{
            display: inline-flex !important;
            align-items: center !important;
            gap: 12px !important;
        }}
        h1 {{
            font-size: 32px !important;
            margin-bottom: 8px !important;
        }}
        h2 {{
            font-size: 20px !important;
        }}
        h3 {{
            font-size: 18px !important;
        }}
        p, label, span, .stMarkdown, .stMarkdown p {{
            color: {tokens["text"]} !important;
            font-family: {font_family} !important;
        }}
        .stCaption {{
            color: {tokens["text_secondary"]} !important;
            font-size: 13px !important;
        }}
        .stButton > button {{
            background: transparent !important;
            color: {tokens["accent"]} !important;
            border: 1.5px solid {tokens["accent"]} !important;
            border-radius: 10px !important;
            padding: 9px 20px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            font-family: {font_family} !important;
            box-shadow: none !important;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        .stButton > button:hover {{
            background: {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
        }}
        .stButton > button * {{
            color: inherit !important;
        }}
        .stButton > button:active {{
            transform: scale(0.97) !important;
        }}
        .stButton > button:focus-visible {{
            outline: 2px solid {tokens["accent"]} !important;
            outline-offset: 2px !important;
        }}
        [data-testid="stMetricValue"] {{
            font-family: {FONT_MONO} !important;
            color: {tokens["text"]} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {tokens["text_secondary"]} !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 1.5rem !important;
        }}

        @keyframes loading-spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        .loading-spinner {{
            border: 4px solid {tokens["border"]};
            border-top: 4px solid {tokens["accent"]};
            border-radius: 50%;
            width: 48px;
            height: 48px;
            animation: loading-spin 1s cubic-bezier(0.4, 0, 0.2, 1)
                       infinite;
            margin: 40px auto;
        }}

        .loading-spinner-container {{
            text-align: center;
            padding: 60px 20px;
        }}

        .loading-spinner-text {{
            color: {tokens["accent"]};
            font-size: 14px;
            font-weight: 600;
            margin-top: 16px;
            letter-spacing: 0.5px;
        }}

        .footer-link {{
            color: {tokens["accent"]} !important;
            text-decoration: none !important;
            font-weight: 600 !important;
        }}
        .footer-link:hover {{
            text-decoration: underline !important;
        }}
        .footer-heading {{
            color: {tokens["text_secondary"]} !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            margin-bottom: 12px !important;
        }}
    </style>
    """

    st.markdown(theme_css, unsafe_allow_html=True)


def show_footer(dark_mode: bool):
    """Display team footer at bottom of page."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    team_members = [
        {
            "name": "Charlotte Yu",
            "role": "System Integration & Report Layer",
            "url": "https://github.com/charlotteyu-47",
        },
        {
            "name": "Jintong He",
            "role": "Report Layer",
            "url": "https://github.com/1613578121-arch",
        },
        {
            "name": "Lei Pei",
            "role": "Data Layer",
            "url": "https://github.com/ploading1017",
        },
        {
            "name": "Qiuting Fu",
            "role": "Data Layer",
            "url": "https://github.com/Ray1410",
        },
        {
            "name": "Lucca Zhou",
            "role": "Model Layer",
            "url": "https://github.com/hikorido",
        },
        {
            "name": "Ray Wang",
            "role": "Model Layer",
            "url": "https://github.com/learnerrayyy",
        },
    ]
    team_html = "".join(
        f'<div style="margin-bottom: 8px; font-size: 13px;">'
        f'<a class="footer-link" href="{member["url"]}" target="_blank" '
        f'rel="noopener noreferrer">{member["name"]}</a>'
        f'<span style="color: {tokens["text_secondary"]}; '
        f'font-size: 12px;"> · {member["role"]}</span>'
        f'</div>'
        for member in team_members
    )

    footer_html = f"""
    <div style="margin-top: 48px; padding-top: 28px;">
        <div style="
            border-top: 1px solid {tokens["border"]};
            padding-top: 28px;
            display: grid;
            grid-template-columns: 1.4fr 1fr 1.4fr;
            gap: 32px;
        ">
            <div>
                <div class="footer-heading">Granite Lifeline</div>
                <div style="margin-bottom: 6px;">
                    <a class="footer-link"
                       href="https://github.com/granite-lifeline"
                       target="_blank" rel="noopener noreferrer"
                       style="font-size: 15px;">
                        Granite Lifeline
                    </a>
                </div>
                <div style="
                    color: {tokens["text_secondary"]};
                    font-size: 13px;
                ">
                    Vehicle health monitoring · IBM-sponsored project
                </div>
            </div>
            <div>
                <div class="footer-heading">Links</div>
                <div style="margin-bottom: 8px; font-size: 13px;">
                    <a class="footer-link"
                       href="https://github.com/granite-lifeline/granite-lifeline"
                       target="_blank" rel="noopener noreferrer">
                        Repository
                    </a>
                </div>
                <div style="font-size: 13px;">
                    <a class="footer-link"
                       href="https://granite-lifeline.github.io/granite-lifeline-blog/"
                       target="_blank" rel="noopener noreferrer">
                        Blog
                    </a>
                </div>
            </div>
            <div>
                <div class="footer-heading">Team</div>
                <div style="
                    color: {tokens["text_secondary"]};
                    font-size: 12px;
                    margin-bottom: 10px;
                ">
                    University of Bristol MSc Computer Science
                </div>
                <div style="color: {tokens["text"]};">
                    {team_html}
                </div>
            </div>
        </div>
    </div>
    """

    st.markdown(footer_html, unsafe_allow_html=True)


def show_overview_page():
    """Display the Overview Page with component health summary."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    spacer_col, title_col, theme_col = st.columns([1, 10, 1])
    with title_col:
        with st.container(key="page_title_block"):
            st.title("Vehicle Health Status")
            latest_timestamp = max(
                (comp.get("timestamp", "") for comp in MOCK_DATA.values()),
                default=""
            )
            if latest_timestamp:
                dt = datetime.fromisoformat(
                    latest_timestamp.replace('Z', '+00:00')
                )
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                st.caption(f"Last checked: {formatted_time}")
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
            unsafe_allow_html=True
        )
    with theme_col:
        st.markdown(
            '<div style="height: 8px;"></div>',
            unsafe_allow_html=True
        )
        if dark_mode:
            theme_icon_svg = lucide_icon("sun", size=20, color=tokens["text"])
            if st.button(
                "Light",
                key="theme_btn",
                help="Switch to light mode"
            ):
                st.session_state["dark_mode"] = False
                st.rerun()
        else:
            theme_icon_svg = lucide_icon(
                "moon", size=20, color=tokens["text"]
            )
            if st.button(
                "Dark",
                key="theme_btn",
                help="Switch to dark mode"
            ):
                st.session_state["dark_mode"] = True
                st.rerun()

        theme_icon_src = svg_data_uri(theme_icon_svg)

        st.markdown(
            f"""
            <style>
                div[data-testid="stColumn"]:has(.st-key-theme_btn)
                    div[data-testid="stVerticalBlock"] {{
                    align-items: flex-end !important;
                }}
                .st-key-theme_btn button {{
                    background-color: {tokens["surface"]} !important;
                    background-image: url("{theme_icon_src}") !important;
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
                .st-key-theme_btn button * {{
                    color: transparent !important;
                    font-size: 0 !important;
                    line-height: 0 !important;
                }}
                .st-key-theme_btn button p {{
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
            unsafe_allow_html=True
        )

    has_high_risk = any(
        comp["risk_level"] == "High" for comp in MOCK_DATA.values()
    )

    if has_high_risk:
        alert_icon = lucide_icon(
            "alert-triangle", size=20, color=tokens["danger_text"]
        )
        alert_html = f"""
        <div style="
            background-color: {tokens["danger_bg"]};
            border: 1px solid {tokens["danger_border"]};
            border-radius: 10px;
            padding: 12px 16px;
            margin: 16px 0;
            color: {tokens["danger_text"]};
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
        ">
            {alert_icon}
            <span style="font-weight: 600; color: {tokens["danger_text"]};">
                Attention needed — one or more components require
                urgent action
            </span>
        </div>
        """
        st.markdown(alert_html, unsafe_allow_html=True)
    else:
        st.success("✓ All systems within normal range")

    st.markdown("<br>", unsafe_allow_html=True)

    sorted_components = sorted(
        MOCK_DATA.items(),
        key=lambda x: RISK_PRIORITY[x[1]["risk_level"]]
    )

    cols = st.columns(3, gap="large")

    for idx, (component_key, component_data) in enumerate(
        sorted_components
    ):
        with cols[idx]:
            risk_level = component_data["risk_level"]
            if risk_level == "High":
                badge_bg = tokens["risk_high"]
            elif risk_level == "Medium":
                badge_bg = tokens["risk_medium"]
            else:
                badge_bg = tokens["risk_low"]

            risk_pct = int(component_data["risk_score"] * 100)
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

            card_html = f"""
            <div style="
                background-color: {tokens["surface"]};
                border-top: 1px solid {tokens["border"]};
                border-right: 1px solid {tokens["border"]};
                border-bottom: 1px solid {tokens["border"]};
                border-left: 4px solid {badge_bg};
                border-radius: 14px;
                box-shadow: 0 1px 3px {tokens["shadow"]};
                padding: 24px 16px;
                margin-bottom: 16px;
                min-height: 280px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 24px;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 12px;
                ">
                    {component_icon}
                    <h3 style="
                        margin: 0;
                        color: {tokens["text"]};
                        font-size: 22px;
                        font-weight: 700;
                    ">
                        {COMPONENT_DISPLAY_NAMES.get(component_key, component_key)}
                    </h3>
                </div>
                <div style="
                    position: relative;
                    width: {ring_size}px;
                    height: {ring_size}px;
                ">
                    {ring_svg}
                    <div style="
                        position: absolute;
                        inset: 0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                    ">
                        <span style="
                            font-family: {FONT_MONO};
                            font-size: 32px;
                            font-weight: 700;
                            color: {tokens["text"]};
                            line-height: 1;
                        ">
                            {risk_pct}%
                        </span>
                        <span style="
                            font-size: 12px;
                            color: {tokens["text_secondary"]};
                            margin-top: 8px;
                            font-weight: 600;
                            letter-spacing: 0.5px;
                            text-transform: uppercase;
                        ">
                            Risk Score
                        </span>
                    </div>
                </div>
            </div>
            """

            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(
                "View Details  →",
                key=f"btn_{component_key}",
                use_container_width=True
            ):
                st.session_state["selected_component"] = component_key
                st.session_state["page"] = "detail"
                st.rerun()

    show_footer(dark_mode)


def render_component_detail(
    component_data: dict,
    dark_mode: bool,
    tokens: dict,
):
    """Render metrics, trend, signals, and report for one component."""
    risk_level = component_data["risk_level"]
    if risk_level == "High":
        badge_bg = tokens["risk_high"]
    elif risk_level == "Medium":
        badge_bg = tokens["risk_medium"]
    else:
        badge_bg = tokens["risk_low"]

    # Get display name from mapping
    component_id = component_data["component"]
    display_name = COMPONENT_DISPLAY_NAMES.get(component_id, component_id)

    title_html = f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 24px;
    ">
        <h1 style="margin: 0; display: inline;">
            {display_name}
        </h1>
    </div>
    """

    st.markdown(title_html, unsafe_allow_html=True)

    # Extract trend from risk_history
    risk_history = component_data.get("risk_history", [])
    trend = [entry["risk_score"] for entry in risk_history]
    risk_pct = int(component_data["risk_score"] * 100)

    card_css = f"""
    <style>
        .st-key-gauge_card,
        .st-key-trend_card,
        .st-key-signals_card {{
            background-color: {tokens["surface"]} !important;
            border: 1px solid {tokens["border"]} !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 3px {tokens["shadow"]} !important;
            padding: 20px !important;
        }}
        .st-key-gauge_card {{
            max-width: 380px !important;
            margin: 0 auto 8px auto !important;
        }}
    </style>
    """
    st.markdown(card_css, unsafe_allow_html=True)

    gauge_heading_icon = lucide_icon("zap", size=24, color=tokens["accent"])
    show_icon_heading("Risk Score", gauge_heading_icon, center=True)

    with st.container(key="gauge_card"):
        delta_config = None
        if len(trend) >= 2:
            delta_config = dict(
                reference=trend[-2] * 100,
                increasing=dict(color=tokens["risk_high"]),
                decreasing=dict(color=tokens["risk_low"]),
            )

        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number+delta" if delta_config else "gauge+number",
            value=risk_pct,
            number=dict(
                suffix="%",
                font=dict(family=FONT_MONO, size=40, color=tokens["text"]),
            ),
            delta=delta_config,
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickcolor=tokens["text_secondary"],
                    tickfont=dict(color=tokens["text_secondary"], size=10),
                ),
                bar=dict(color=badge_bg, thickness=0.3),
                bgcolor=tokens["surface_alt"],
                borderwidth=0,
            ),
        ))
        gauge_fig.update_layout(
            paper_bgcolor=tokens["surface"],
            font=dict(color=tokens["text_secondary"]),
            margin=dict(l=40, r=40, t=20, b=10),
            height=200,
        )
        st.plotly_chart(
            gauge_fig,
            use_container_width=True,
            key="detail_risk_gauge",
        )
        
        # Format timestamp
        timestamp_str = component_data.get("timestamp", "")
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_time = timestamp_str
        else:
            formatted_time = "N/A"
        
        st.markdown(
            f"""
            <p style="
                text-align: center;
                color: {tokens["text_secondary"]};
                font-size: 12px;
                margin: -8px 0 0 0;
            ">
                Last updated: {formatted_time}
            </p>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height: 28px;'></div>", unsafe_allow_html=True
    )

    trend_col, signals_col = st.columns([6, 6], gap="large")

    with trend_col:
        heading_icon = lucide_icon(
            "trending-up", size=24, color=tokens["accent"]
        )
        show_icon_heading("Risk Score Trend", heading_icon)

        with st.container(key="trend_card"):
            if len(trend) < 2:
                st.warning("Not enough data yet to show a trend.")
            else:
                with st.spinner(""):
                    spinner_html = """
                    <div class="loading-spinner-container">
                        <div class="loading-spinner"></div>
                        <div class="loading-spinner-text">
                            Loading trend data...
                        </div>
                    </div>
                    """
                    spinner_placeholder = st.empty()
                    spinner_placeholder.markdown(
                        spinner_html,
                        unsafe_allow_html=True
                    )

                    time.sleep(0.5)
                    spinner_placeholder.empty()

                time_labels = ["T-4", "T-3", "T-2", "T-1", "Now"]
                time_labels = time_labels[-len(trend):]

                line_color = tokens["accent"]
                bg_color = tokens["surface"]
                paper_bg = tokens["surface"]
                text_color = tokens["text_secondary"]
                grid_color = tokens["border"]
                fill_color = (
                    "rgba(41, 151, 255, 0.15)" if dark_mode
                    else "rgba(0, 113, 227, 0.12)"
                )

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=time_labels,
                    y=trend,
                    mode="lines+markers",
                    line=dict(color=line_color, width=3, shape="spline"),
                    marker=dict(
                        size=8,
                        color=line_color,
                        line=dict(color=tokens["surface"], width=2)
                    ),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    name="Risk Score",
                    hovertemplate=(
                        "<b>%{x}</b><br>Risk Score: %{y:.0%}<extra>"
                        "</extra>"
                    )
                ))

                fig.update_layout(
                    plot_bgcolor=bg_color,
                    paper_bgcolor=paper_bg,
                    font=dict(color=text_color),
                    xaxis=dict(
                        gridcolor=grid_color,
                        showgrid=True
                    ),
                    yaxis=dict(
                        gridcolor=grid_color,
                        showgrid=True,
                        range=[0, 1],
                        tickformat=".0%"
                    ),
                    margin=dict(l=40, r=20, t=20, b=40),
                    height=260,
                    showlegend=False
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="detail_trend_chart",
                )

                st.caption(
                    "Risk score over the last 5 recorded readings. "
                    "Higher values indicate greater risk."
                )

    with signals_col:
        heading_icon = lucide_icon(
            "activity", size=24, color=tokens["accent"]
        )
        show_icon_heading("Key Signals", heading_icon)

        with st.container(key="signals_card"):
            key_signals = component_data["key_signals"]

            if not key_signals:
                st.info("No signal data available for this component.")
            else:
                row_bg = tokens["surface_alt"]

                header_html = f"""
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 12px;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 0.4px;
                    text-transform: uppercase;
                    color: {tokens["text_secondary"]};
                ">
                    <div style="flex: 2.5; min-width: 100px;">Signal</div>
                    <div style="flex: 1.5; min-width: 70px;">Reading</div>
                    <div style="flex: 2; min-width: 90px;">Normal Range</div>
                    <div style="flex: 0.8; min-width: 50px;">Unit</div>
                    <div style="
                        flex: 1.2;
                        min-width: 76px;
                        max-width: 90px;
                        text-align: center;
                    ">
                        Status
                    </div>
                </div>
                """
                st.markdown(header_html, unsafe_allow_html=True)

                signals_with_status = []
                for signal in key_signals:
                    ref_lower = signal["reference_range"][0]
                    ref_upper = signal["reference_range"][1]
                    is_abnormal = (
                        signal["value"] < ref_lower or
                        signal["value"] > ref_upper
                    )
                    status = "ABNORMAL" if is_abnormal else "NORMAL"
                    signals_with_status.append((signal, status))

                signals_with_status.sort(key=lambda x: x[1] == "NORMAL")

                for signal, status in signals_with_status:
                    ref_lower = signal["reference_range"][0]
                    ref_upper = signal["reference_range"][1]
                    signal_badge_bg = (
                        tokens["risk_high"] if status == "ABNORMAL"
                        else tokens["risk_low"]
                    )
                    
                    # Get display name from mapping
                    signal_id = signal["feature"]
                    signal_display_name = SIGNAL_DISPLAY_NAMES.get(signal_id, signal_id)

                    row_html = f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        background: {row_bg};
                        border-radius: 8px;
                        padding: 10px 12px;
                        margin-bottom: 6px;
                    ">
                        <div style="
                            flex: 2.5;
                            min-width: 100px;
                            font-weight: 600;
                            color: {tokens["text"]};
                            font-size: 13px;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        ">
                            {signal_display_name}
                        </div>
                        <div style="
                            flex: 1.5;
                            min-width: 70px;
                            font-family: {FONT_MONO};
                            color: {tokens["text"]};
                            font-size: 13px;
                            font-weight: 600;
                        ">
                            {signal["value"]}
                        </div>
                        <div style="
                            flex: 2;
                            min-width: 90px;
                            font-family: {FONT_MONO};
                            color: {tokens["text_secondary"]};
                            font-size: 12px;
                        ">
                            {ref_lower}–{ref_upper}
                        </div>
                        <div style="
                            flex: 0.8;
                            min-width: 50px;
                            font-family: {FONT_MONO};
                            color: {tokens["text_secondary"]};
                            font-size: 12px;
                        ">
                            {signal["unit"]}
                        </div>
                        <div style="
                            flex: 1.2;
                            min-width: 76px;
                            max-width: 90px;
                            text-align: center;
                            background-color: {signal_badge_bg};
                            color: white;
                            padding: 4px 6px;
                            border-radius: 12px;
                            font-size: 10px;
                            font-weight: 600;
                        ">
                            {status}
                        </div>
                    </div>
                    """
                    st.markdown(row_html, unsafe_allow_html=True)

    show_divider(dark_mode)

    heading_icon = lucide_icon("file-text", size=22, color=tokens["accent"])
    show_icon_heading("Diagnostic Report", heading_icon)

    # Get Granite LLM generated content
    anomaly_desc = component_data.get("anomaly_description", "Pending Granite LLM report generation...")
    possible_cause = component_data.get("possible_cause", "Pending Granite LLM report generation...")
    recommended_action = component_data.get("recommended_action", "Pending Granite LLM report generation...")
    
    # Format recommended_action as bullet list if it's a list
    if isinstance(recommended_action, list):
        action_items = ""
        for action in recommended_action:
            action_items += f"""
            <div style="
                display: flex;
                gap: 8px;
                margin-bottom: 8px;
                align-items: flex-start;
            ">
                <span style="
                    color: {tokens["accent"]};
                    font-weight: 700;
                    flex-shrink: 0;
                ">•</span>
                <span style="color: {tokens["text"]};">{action}</span>
            </div>
            """
        action_html = f"<div>{action_items}</div>"
    else:
        action_html = f"<p style='margin: 0; color: {tokens["text"]};'>{recommended_action}</p>"
    
    cards = [
        {
            "icon": lucide_icon(
                "info", size=20, color=tokens["accent"]
            ),
            "title": "What's Happening",
            "body": anomaly_desc,
            "is_html": False
        },
        {
            "icon": lucide_icon(
                "help-circle", size=20, color=tokens["accent"]
            ),
            "title": "Why This Matters",
            "body": possible_cause,
            "is_html": False
        },
        {
            "icon": lucide_icon(
                "check-square", size=20, color=tokens["accent"]
            ),
            "title": "What You Should Do",
            "body": action_html,
            "is_html": True
        }
    ]

    report_cols = st.columns(3, gap="medium")
    for col, card in zip(report_cols, cards):
        with col:
            body_content = card["body"] if card["is_html"] else f"<p style='margin: 0; color: {tokens["text"]}; line-height: 1.6;'>{card['body']}</p>"
            card_html = f"""
            <div style="
                background: {tokens["surface"]};
                border: 1px solid {tokens["border"]};
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 12px;
                min-height: 200px;
                display: flex;
                flex-direction: column;
            ">
                <h3 style="
                    color: {tokens["text"]};
                    margin: 0 0 14px 0;
                    font-size: 16px;
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid {tokens["border"]};
                ">
                    {card["icon"]}{card["title"]}
                </h3>
                <div style="
                    font-size: 14px;
                    line-height: 1.6;
                    flex: 1;
                ">
                    {body_content}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)


def show_detail_page():
    """Display Component Detail Page with tab-based component switch."""
    component_key = st.session_state.get("selected_component")

    if not component_key or component_key not in MOCK_DATA:
        st.error("Component not found.")
        if st.button("← Back to Overview"):
            st.session_state["page"] = "overview"
            st.rerun()
        return

    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    if st.button("← Back to Overview"):
        st.session_state["page"] = "overview"
        st.rerun()

    sorted_components = sorted(
        MOCK_DATA.items(),
        key=lambda x: RISK_PRIORITY[x[1]["risk_level"]]
    )
    risk_color_map = {
        "High": tokens["risk_high"],
        "Medium": tokens["risk_medium"],
        "Low": tokens["risk_low"],
    }

    tab_cols = st.columns(len(sorted_components), gap="small")
    tab_css_rules = []

    for col, (tab_key, tab_data) in zip(tab_cols, sorted_components):
        with col:
            is_active = tab_key == component_key
            icon_color = risk_color_map[tab_data["risk_level"]]
            icon_svg = lucide_icon(
                COMPONENT_ICONS.get(tab_key, "activity"),
                size=16,
                color=icon_color,
            )
            icon_src = svg_data_uri(icon_svg)
            label = COMPONENT_DISPLAY_NAMES.get(tab_key, tab_key)
            if st.button(
                label,
                key=f"tab_btn_{tab_key}",
                use_container_width=True,
            ):
                st.session_state["selected_component"] = tab_key
                st.rerun()

            icon_css = f"""
                background-color: transparent !important;
                background-image: url("{icon_src}") !important;
                background-repeat: no-repeat !important;
                background-position: 18px center !important;
                background-size: 16px 16px !important;
                padding-left: 52px !important;
            """
            if is_active:
                tab_css_rules.append(f"""
                    .st-key-tab_btn_{tab_key} button {{
                        {icon_css}
                        color: {tokens["accent"]} !important;
                        border: none !important;
                        border-bottom: 2.5px solid {tokens["accent"]}
                            !important;
                        border-radius: 0 !important;
                        font-weight: 700 !important;
                    }}
                    .st-key-tab_btn_{tab_key} button:hover {{
                        {icon_css}
                        color: {tokens["accent"]} !important;
                    }}
                """)
            else:
                tab_css_rules.append(f"""
                    .st-key-tab_btn_{tab_key} button {{
                        {icon_css}
                        color: {tokens["text_secondary"]} !important;
                        border: none !important;
                        border-bottom: 2.5px solid {tokens["border"]}
                            !important;
                        border-radius: 0 !important;
                        font-weight: 500 !important;
                    }}
                    .st-key-tab_btn_{tab_key} button:hover {{
                        {icon_css}
                        color: {tokens["text"]} !important;
                    }}
                """)

    st.markdown(
        f"<style>{''.join(tab_css_rules)}</style>",
        unsafe_allow_html=True,
    )

    show_divider(dark_mode, margin="8px auto 32px auto")

    render_component_detail(MOCK_DATA[component_key], dark_mode, tokens)

    show_footer(dark_mode)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Granite Lifeline",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    if "page" not in st.session_state:
        st.session_state["page"] = "overview"
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    apply_theme(st.session_state.get("dark_mode", False))

    if st.session_state["page"] == "detail":
        show_detail_page()
    else:
        show_overview_page()


if __name__ == "__main__":
    main()
