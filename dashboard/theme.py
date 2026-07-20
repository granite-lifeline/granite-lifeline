"""Theme tokens, icons, and CSS injection for the Granite Lifeline dashboard.

Single source of truth for all visual design decisions: colour tokens,
typography constants, icon glyphs, and the global CSS injector.
"""

from __future__ import annotations

import base64
import math

import streamlit as st


# ---------------------------------------------------------------------------
# Colour tokens
# ---------------------------------------------------------------------------

THEME_TOKENS: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#f5f5f7",
        "surface": "#ffffff",
        "surface_alt": "#f5f5f7",
        "border": "#d2d2d7",
        "text": "#1d1d1f",
        "text_secondary": "#6e6e73",
        "accent": "#0f62fe",
        "accent_contrast": "#ffffff",
        "shadow": "rgba(0, 0, 0, 0.06)",
        "risk_high": "#da1e28",
        "risk_medium": "#ff832b",
        "risk_low": "#24a148",
        "danger_bg": "#fff1f1",
        "danger_border": "#ffd7d9",
        "danger_text": "#a2191f",
        "glass_surface": "rgba(255, 255, 255, 0.72)",
        "glass_border": "rgba(0, 0, 0, 0.07)",
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
        "shadow": "rgba(0, 0, 0, 0.32)",
        "risk_high": "#fa4d56",
        "risk_medium": "#ff832b",
        "risk_low": "#42be65",
        "danger_bg": "#2c1618",
        "danger_border": "#5e2125",
        "danger_text": "#ff8389",
        "glass_surface": "rgba(44, 44, 46, 0.60)",
        "glass_border": "rgba(255, 255, 255, 0.10)",
    },
}

FONT_SANS = (
    "'IBM Plex Sans', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)
FONT_MONO = "'IBM Plex Mono', 'SF Mono', Consolas, monospace"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a ``#rrggbb`` hex colour to an ``rgba()`` CSS string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def get_tokens() -> dict[str, str]:
    """Return the active theme token dict for the current session mode."""
    mode = "dark" if st.session_state.get("dark_mode", False) else "light"
    return THEME_TOKENS[mode]


# ---------------------------------------------------------------------------
# Icon registry
# ---------------------------------------------------------------------------

# Hand-coded Lucide-style SVG path data, keyed by icon name.
ICONS: dict[str, str] = {
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
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>'
    ),
    "trending-up": (
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>'
        '<polyline points="17 6 23 6 23 12"></polyline>'
    ),
    "activity": (
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>'
    ),
    "thermometer": (
        '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 '
        '5 0z"></path>'
        '<line x1="12" y1="7" x2="12" y2="14"></line>'
    ),
    "gauge": (
        '<path d="M12 14l4-4"></path>'
        '<path d="M3.34 19a10 10 0 1 1 17.32 0"></path>'
    ),
    "sliders": (
        '<line x1="4" y1="21" x2="4" y2="14"></line>'
        '<line x1="4" y1="10" x2="4" y2="3"></line>'
        '<line x1="12" y1="21" x2="12" y2="12"></line>'
        '<line x1="12" y1="8" x2="12" y2="3"></line>'
        '<line x1="20" y1="21" x2="20" y2="16"></line>'
        '<line x1="20" y1="12" x2="20" y2="3"></line>'
        '<line x1="2" y1="14" x2="6" y2="14"></line>'
        '<line x1="10" y1="8" x2="14" y2="8"></line>'
        '<line x1="18" y1="16" x2="22" y2="16"></line>'
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
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>'
    ),
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.35 8.97a1 1 0 0 1-.6.03C8.5 20.5 '
        '4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 '
        '1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"></path>'
    ),
}

# Per-component icon name, keyed by component/anomaly key.
COMPONENT_ICONS: dict[str, str] = {
    "cooling_degradation": "droplet",
    "cooling_system_stress": "droplet",
    "intake_air_temperature_sensor_fault": "thermometer",
    "air_intake_maf_anomaly": "wind",
    "map_load_signal_plausibility_fault": "gauge",
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
    encoded = base64.b64encode(
        svg_markup.encode("utf-8")
    ).decode("utf-8")
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


# ---------------------------------------------------------------------------
# Global CSS injector
# ---------------------------------------------------------------------------

def apply_theme(dark_mode: bool) -> None:
    """Inject global CSS for the given light/dark mode."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    font_link = (
        '<link href="https://fonts.googleapis.com/css2?'
        'family=IBM+Plex+Sans:wght@400;500;600;700'
        '&family=IBM+Plex+Mono:wght@500;600;700'
        '&family=Noto+Sans+SC:wght@400;500;700'
        '&display=swap" rel="stylesheet">'
    )

    blob_alpha = (
        (0.28, 0.22, 0.16, 0.20)
        if dark_mode else (0.10, 0.08, 0.07, 0.08)
    )
    blob_css = (
        f"radial-gradient(circle at 12% 8%, "
        f"{hex_to_rgba(tokens['accent'], blob_alpha[0])}, "
        f"transparent 40%), "
        f"radial-gradient(circle at 88% 12%, "
        f"{hex_to_rgba(tokens['risk_high'], blob_alpha[1])}, "
        f"transparent 38%), "
        f"radial-gradient(circle at 50% 55%, "
        f"{hex_to_rgba(tokens['risk_medium'], blob_alpha[2])}, "
        f"transparent 45%), "
        f"radial-gradient(circle at 85% 90%, "
        f"{hex_to_rgba(tokens['risk_low'], blob_alpha[3])}, "
        f"transparent 42%)"
    )

    theme_css = f"""
    {font_link}
    <style>
        section[data-testid="stSidebar"] {{ display: none !important; }}
        header[data-testid="stHeader"]   {{ display: none !important; }}
        [data-testid="stAppViewContainer"] {{
            background-color: {tokens["bg"]} !important;
            background-image: {blob_css} !important;
            background-attachment: fixed !important;
        }}
        .main {{ background-color: transparent !important; }}
        .main .block-container {{
            background-color: transparent !important;
            font-family: {FONT_SANS} !important;
            padding-top: 2.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 1100px !important;
        }}
        h1, h2, h3 {{
            color: {tokens["text"]} !important;
            font-weight: 700 !important;
            font-family: {FONT_SANS} !important;
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
        h1 [data-testid="stHeaderActionElements"],
        h2 [data-testid="stHeaderActionElements"],
        h3 [data-testid="stHeaderActionElements"] {{
            display: none !important;
        }}
        @media (max-width: 680px) {{
            .gl-heading-wrap {{ flex-direction: column !important; }}
            .gl-confidence-badge {{
                position: static !important;
                transform: none !important;
            }}
        }}
        h1 {{ font-size: 32px !important; margin-bottom: 8px !important; }}
        h2 {{ font-size: 20px !important; }}
        h3 {{ font-size: 18px !important; }}
        p, label, span, .stMarkdown, .stMarkdown p {{
            color: {tokens["text"]} !important;
            font-family: {FONT_SANS} !important;
        }}
        .stCaption {{
            color: {tokens["text_secondary"]} !important;
            font-size: 13px !important;
        }}
        .stButton > button {{
            background: {hex_to_rgba(tokens["accent"], 0.08)} !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            color: {tokens["accent"]} !important;
            border: 1.5px solid {tokens["accent"]} !important;
            border-radius: 10px !important;
            padding: 9px 20px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            font-family: {FONT_SANS} !important;
            box-shadow: none !important;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        .stButton > button:hover {{
            background: {tokens["accent"]} !important;
            color: {tokens["accent_contrast"]} !important;
        }}
        .stButton > button * {{ color: inherit !important; }}
        .stButton > button:active {{ transform: scale(0.97) !important; }}
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
        div[data-testid="stHorizontalBlock"] {{ gap: 1.5rem !important; }}
        @keyframes loading-spin {{
            0%   {{ transform: rotate(0deg);   }}
            100% {{ transform: rotate(360deg); }}
        }}
        .loading-spinner {{
            border: 4px solid {tokens["border"]};
            border-top: 4px solid {tokens["accent"]};
            border-radius: 50%;
            width: 48px; height: 48px;
            animation: loading-spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
            margin: 40px auto;
        }}
        .loading-spinner-container {{
            text-align: center; padding: 60px 20px;
        }}
        .loading-spinner-text {{
            color: {tokens["accent"]}; font-size: 14px;
            font-weight: 600; margin-top: 16px; letter-spacing: 0.5px;
        }}
        .footer-link {{
            color: {tokens["accent"]} !important;
            text-decoration: none !important;
            font-weight: 600 !important;
        }}
        .footer-link:hover {{ text-decoration: underline !important; }}
        .footer-heading {{
            color: {tokens["text_secondary"]} !important;
            font-size: 11px !important; font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            margin-bottom: 12px !important;
        }}
    </style>
    """
    st.markdown(theme_css, unsafe_allow_html=True)
