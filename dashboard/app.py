"""
Granite Lifeline Dashboard - Overview Page

Displays vehicle health status with component risk levels and navigation
to detailed diagnostic reports.
"""

import base64
import math
import streamlit as st
import plotly.graph_objects as go

MOCK_DATA = {
    "cooling_system_stress": {
        "display_name": "Cooling System",
        "risk_level": "High",
        "risk_score": 0.82,
        "trend": [0.45, 0.52, 0.61, 0.70, 0.82],
        "key_signals": [
            {
                "feature": "coolant_temp",
                "display_name": "Coolant Temperature",
                "value": 102,
                "unit": "°C",
                "reference_range": [90, 95],
                "status": "ABNORMAL"
            }
        ]
    },
    "air_intake_maf_anomaly": {
        "display_name": "Air Intake System",
        "risk_level": "Medium",
        "risk_score": 0.55,
        "trend": [0.30, 0.35, 0.40, 0.48, 0.55],
        "key_signals": [
            {
                "feature": "maf",
                "display_name": "Mass Airflow",
                "value": 13.0,
                "unit": "g/s",
                "reference_range": [8, 11],
                "status": "ABNORMAL"
            },
            {
                "feature": "map",
                "display_name": "Intake Pressure",
                "value": 45,
                "unit": "kPa",
                "reference_range": [40, 48],
                "status": "NORMAL"
            }
        ]
    },
    "accelerator_pedal_sensor": {
        "display_name": "Accelerator Pedal",
        "risk_level": "Low",
        "risk_score": 0.22,
        "trend": [0.18, 0.20, 0.21, 0.22, 0.22],
        "key_signals": [
            {
                "feature": "accel_pedal_d",
                "display_name": "Pedal Sensor D",
                "value": 35.0,
                "unit": "%",
                "reference_range": [0, 100],
                "status": "NORMAL"
            },
            {
                "feature": "accel_pedal_e",
                "display_name": "Pedal Sensor E",
                "value": 37.5,
                "unit": "%",
                "reference_range": [0, 100],
                "status": "NORMAL"
            }
        ]
    }
}

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


def show_icon_heading(title: str, icon_svg: str):
    """Display an H2 heading with an inline icon."""
    heading_html = f"""
    <h2 style="
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 14px;
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
        }}
        h1 {{
            font-size: 32px !important;
            margin-bottom: 8px !important;
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
    </style>
    """

    st.markdown(theme_css, unsafe_allow_html=True)


def show_footer(dark_mode: bool):
    """Display team footer at bottom of page."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    footer_html = f"""
    <div style="margin-top: 48px; padding-top: 20px;">
        <div style="
            border-top: 1px solid {tokens["border"]};
            padding-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 24px;
            flex-wrap: wrap;
        ">
            <div>
                <div style="
                    color: {tokens["text"]};
                    font-weight: 700;
                    font-size: 15px;
                    margin-bottom: 4px;
                ">
                    Granite Lifeline
                </div>
                <div style="
                    color: {tokens["text_secondary"]};
                    font-size: 13px;
                ">
                    Vehicle health monitoring · IBM-sponsored project
                </div>
            </div>
            <div style="display: flex; gap: 24px; font-size: 13px;">
                <a class="footer-link"
                   href="https://github.com/granite-lifeline/granite-lifeline"
                   target="_blank" rel="noopener noreferrer">
                    Repository
                </a>
                <a class="footer-link"
                   href="https://granite-lifeline.github.io/granite-lifeline-blog/"
                   target="_blank" rel="noopener noreferrer">
                    Blog
                </a>
            </div>
        </div>
        <div style="
            border-top: 1px solid {tokens["border"]};
            margin-top: 16px;
            padding-top: 16px;
            padding-bottom: 8px;
            color: {tokens["text_secondary"]};
            font-size: 12px;
        ">
            University of Bristol MSc Computer Science · Team: Charlotte
            Yu, Jintong He, Lei Pei, Qiuting Fu, Lucca Zhou, Ray Wang
        </div>
    </div>
    """

    st.markdown(footer_html, unsafe_allow_html=True)


def show_overview_page():
    """Display the Overview Page with component health summary."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    title_col, theme_col = st.columns([11, 1])
    with title_col:
        with st.container(key="page_title_block"):
            st.title("Vehicle Health Status")
            st.caption("Last checked: 2026-06-23 10:00")
        st.markdown(
            """
            <style>
                .st-key-page_title_block,
                .st-key-page_title_block h1,
                .st-key-page_title_block .stCaption {
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
            gap: 10px;
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
                risk_label = "High Risk"
            elif risk_level == "Medium":
                badge_bg = tokens["risk_medium"]
                risk_label = "Medium Risk"
            else:
                badge_bg = tokens["risk_low"]
                risk_label = "Low Risk"

            risk_pct = int(component_data["risk_score"] * 100)
            component_icon = lucide_icon(
                COMPONENT_ICONS.get(component_key, "activity"),
                size=18,
                color=badge_bg,
            )
            ring_svg = progress_ring(
                risk_pct,
                color=badge_bg,
                track_color=tokens["border"],
                anim_key=component_key,
                size=64,
                stroke=7,
            )

            card_html = f"""
            <div style="
                background-color: {tokens["surface"]};
                border: 1px solid {tokens["border"]};
                border-left: 4px solid {badge_bg};
                border-radius: 14px;
                box-shadow: 0 1px 3px {tokens["shadow"]};
                padding: 24px;
                margin-bottom: 16px;
                min-height: 180px;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 16px;
                ">
                    {component_icon}
                    <h3 style="
                        margin: 0;
                        color: {tokens["text"]};
                        font-size: 18px;
                        font-weight: 700;
                    ">
                        {component_data["display_name"]}
                    </h3>
                </div>
                <div style="
                    background-color: {badge_bg};
                    color: white;
                    padding: 6px 14px;
                    border-radius: 20px;
                    display: inline-block;
                    font-weight: 600;
                    font-size: 12px;
                    margin-bottom: 20px;
                ">
                    {risk_label}
                </div>
                <div style="
                    margin-top: 16px;
                    display: flex;
                    align-items: center;
                    gap: 16px;
                ">
                    {ring_svg}
                    <div>
                        <p style="
                            font-family: {FONT_MONO};
                            font-size: 36px;
                            font-weight: 700;
                            margin: 0;
                            color: {tokens["text"]};
                            line-height: 1;
                        ">
                            {risk_pct}%
                        </p>
                        <p style="
                            font-size: 12px;
                            color: {tokens["text_secondary"]};
                            margin: 4px 0 0 0;
                            font-weight: 500;
                        ">
                            Risk Score
                        </p>
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
        risk_label = "High Risk"
    elif risk_level == "Medium":
        badge_bg = tokens["risk_medium"]
        risk_label = "Medium Risk"
    else:
        badge_bg = tokens["risk_low"]
        risk_label = "Low Risk"

    badge_html = f"""
    <div style="
        background-color: {badge_bg};
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        display: inline-block;
        font-weight: 600;
        font-size: 12px;
        margin-left: 16px;
    ">
        {risk_label}
    </div>
    """

    title_html = f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 24px;
    ">
        <h1 style="margin: 0; display: inline;">
            {component_data["display_name"]}
        </h1>
        {badge_html}
    </div>
    """

    st.markdown(title_html, unsafe_allow_html=True)

    trend = component_data["trend"]
    risk_pct = int(component_data["risk_score"] * 100)

    gauge_col, trend_col = st.columns([4, 8], gap="large")

    with gauge_col:
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
            margin=dict(l=40, r=40, t=30, b=10),
            height=220,
        )
        st.plotly_chart(
            gauge_fig,
            use_container_width=True,
            key="detail_risk_gauge",
        )
        st.markdown(
            f"""
            <p style="
                text-align: center;
                color: {tokens["text_secondary"]};
                font-size: 12px;
                margin-top: -8px;
            ">
                Last updated: 2026-06-23 10:00
            </p>
            """,
            unsafe_allow_html=True,
        )

    with trend_col:
        if len(trend) < 2:
            st.warning("Not enough data yet to show a trend.")
        else:
            heading_icon = lucide_icon(
                "trending-up", size=22, color=tokens["accent"]
            )
            show_icon_heading("Risk Score Trend", heading_icon)

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

                import time
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
                    "<b>%{x}</b><br>Risk Score: %{y:.0%}<extra></extra>"
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
                height=220,
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

    show_divider(dark_mode)

    heading_icon = lucide_icon("activity", size=22, color=tokens["accent"])
    show_icon_heading("Key Signals", heading_icon)

    key_signals = component_data["key_signals"]

    if not key_signals:
        st.info("No signal data available for this component.")
    else:
        row_bg = tokens["surface_alt"]

        header_html = f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 0 16px 8px 16px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: {tokens["text_secondary"]};
        ">
            <div style="flex: 2; min-width: 0;">Signal</div>
            <div style="flex: 1; min-width: 0;">Reading</div>
            <div style="flex: 1; min-width: 0;">Normal Range</div>
            <div style="
                flex-shrink: 0;
                min-width: 84px;
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

            row_html = f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 16px;
                background: {row_bg};
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 6px;
            ">
                <div style="
                    flex: 2;
                    min-width: 0;
                    font-weight: 600;
                    color: {tokens["text"]};
                ">
                    {signal["display_name"]}
                </div>
                <div style="
                    flex: 1;
                    min-width: 0;
                    font-family: {FONT_MONO};
                    color: {tokens["text"]};
                ">
                    {signal["value"]} {signal["unit"]}
                </div>
                <div style="
                    flex: 1;
                    min-width: 0;
                    color: {tokens["text_secondary"]};
                    font-size: 13px;
                ">
                    Normal: {ref_lower}–{ref_upper} {signal["unit"]}
                </div>
                <div style="
                    flex-shrink: 0;
                    min-width: 84px;
                    text-align: center;
                    background-color: {signal_badge_bg};
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
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

    cards = [
        {
            "icon": lucide_icon(
                "info", size=18, color=tokens["text_secondary"]
            ),
            "title": "What's Happening",
            "body": "Pending Granite LLM report generation..."
        },
        {
            "icon": lucide_icon(
                "help-circle", size=18, color=tokens["text_secondary"]
            ),
            "title": "Why This Matters",
            "body": "Pending Granite LLM report generation..."
        },
        {
            "icon": lucide_icon(
                "check-square", size=18, color=tokens["text_secondary"]
            ),
            "title": "What You Should Do",
            "body": "Pending Granite LLM report generation..."
        }
    ]

    report_cols = st.columns(3, gap="medium")
    for col, card in zip(report_cols, cards):
        with col:
            card_html = f"""
            <div style="
                background: {tokens["surface"]};
                border: 1px solid {tokens["border"]};
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                min-height: 160px;
            ">
                <h3 style="
                    color: {tokens["text"]};
                    margin: 0 0 8px 0;
                    font-size: 16px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    {card["icon"]}{card["title"]}
                </h3>
                <p style="
                    color: {tokens["text_secondary"]};
                    margin: 0;
                    font-size: 14px;
                    font-style: italic;
                ">
                    {card["body"]}
                </p>
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
    risk_emoji = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}

    tab_cols = st.columns(len(sorted_components), gap="small")
    tab_css_rules = []

    for col, (tab_key, tab_data) in zip(tab_cols, sorted_components):
        with col:
            is_active = tab_key == component_key
            label = (
                f"{risk_emoji[tab_data['risk_level']]} "
                f"{tab_data['display_name']}"
            )
            if st.button(
                label,
                key=f"tab_btn_{tab_key}",
                use_container_width=True,
            ):
                st.session_state["selected_component"] = tab_key
                st.rerun()

            if is_active:
                tab_css_rules.append(f"""
                    .st-key-tab_btn_{tab_key} button {{
                        background: transparent !important;
                        color: {tokens["accent"]} !important;
                        border: none !important;
                        border-bottom: 2.5px solid {tokens["accent"]}
                            !important;
                        border-radius: 0 !important;
                        font-weight: 700 !important;
                    }}
                    .st-key-tab_btn_{tab_key} button:hover {{
                        background: transparent !important;
                        color: {tokens["accent"]} !important;
                    }}
                """)
            else:
                tab_css_rules.append(f"""
                    .st-key-tab_btn_{tab_key} button {{
                        background: transparent !important;
                        color: {tokens["text_secondary"]} !important;
                        border: none !important;
                        border-bottom: 2.5px solid {tokens["border"]}
                            !important;
                        border-radius: 0 !important;
                        font-weight: 500 !important;
                    }}
                    .st-key-tab_btn_{tab_key} button:hover {{
                        color: {tokens["text"]} !important;
                        background: transparent !important;
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
