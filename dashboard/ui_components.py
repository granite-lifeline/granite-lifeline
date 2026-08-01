"""Reusable UI component helpers for the Granite Lifeline dashboard.

Every function returns either an HTML string (for st.markdown) or calls
st.markdown directly.  No business logic lives here — only presentation.
"""

from __future__ import annotations

import streamlit as st

try:
    from theme import (
        FONT_MONO,
        THEME_TOKENS,
        hex_to_rgba,
        lucide_icon,
    )
except ImportError:  # package import during tests
    from dashboard.theme import (
        FONT_MONO,
        THEME_TOKENS,
        hex_to_rgba,
        lucide_icon,
    )


# ---------------------------------------------------------------------------
# HTML string builders  (return str, caller decides when to render)
# ---------------------------------------------------------------------------

def glass_card_html(
    body: str,
    tokens: dict,
    *,
    padding: str = "20px",
    radius: str = "16px",
    extra_style: str = "",
) -> str:
    """Return a glass-morphism card wrapping *body* HTML."""
    return (
        f'<div style="'
        f'background:{tokens["glass_surface"]};'
        f'backdrop-filter:blur(24px) saturate(160%);'
        f'-webkit-backdrop-filter:blur(24px) saturate(160%);'
        f'border:1px solid {tokens["glass_border"]};'
        f'border-radius:{radius};'
        f'padding:{padding};'
        f'box-shadow:0 8px 28px {tokens["shadow"]},'
        f'inset 0 1px 0 rgba(255,255,255,0.10);'
        f'{extra_style}">'
        f'{body}'
        f'</div>'
    )


def danger_card_html(
    title: str,
    body: str,
    tokens: dict,
) -> str:
    """Return a red danger/error card HTML string."""
    return (
        f'<div style="'
        f'background:{tokens["danger_bg"]};'
        f'border:1px solid {tokens["danger_border"]};'
        f'border-radius:12px;'
        f'padding:16px 20px;'
        f'margin-top:12px;'
        f'box-shadow:0 4px 16px {tokens["shadow"]};'
        f'">'
        f'<strong style="color:{tokens["danger_text"]};font-size:15px;">'
        f'{title}</strong>'
        f'{body}'
        f'</div>'
    )


def info_banner_html(
    message: str,
    tokens: dict,
    *,
    icon_name: str = "info",
) -> str:
    """Return a neutral info banner HTML string."""
    icon = lucide_icon(icon_name, size=20, color=tokens["text_secondary"])
    return (
        f'<div style="'
        f'background:{hex_to_rgba(tokens["text_secondary"], 0.08)};'
        f'border:1px solid {hex_to_rgba(tokens["text_secondary"], 0.20)};'
        f'border-radius:12px;'
        f'padding:16px 20px;'
        f'display:flex;align-items:flex-start;gap:12px;">'
        f'<span style="flex-shrink:0;">{icon}</span>'
        f'<span style="color:{tokens["text"]};'
        f'font-size:14px;line-height:1.5;">{message}</span>'
        f'</div>'
    )


def warning_banner_html(
    message: str,
    tokens: dict,
    *,
    label: str = "Warning",
) -> str:
    """Return an amber warning banner HTML string."""
    icon = lucide_icon(
        "alert-triangle", size=18, color=tokens["risk_medium"]
    )
    return (
        f'<div style="'
        f'background:{hex_to_rgba(tokens["risk_medium"], 0.10)};'
        f'border:1px solid {hex_to_rgba(tokens["risk_medium"], 0.35)};'
        f'backdrop-filter:blur(16px);'
        f'-webkit-backdrop-filter:blur(16px);'
        f'border-radius:12px;'
        f'padding:12px 16px;'
        f'margin:12px auto 4px auto;'
        f'max-width:860px;'
        f'display:flex;align-items:flex-start;gap:12px;'
        f'box-shadow:0 4px 16px {tokens["shadow"]};'
        f'">'
        f'<span style="flex-shrink:0;margin-top:1px;">{icon}</span>'
        f'<span style="color:{tokens["text"]};'
        f'font-size:14px;line-height:1.5;">'
        f'<strong style="color:{tokens["risk_medium"]};">'
        f'{label}</strong> \u2014 {message}'
        f'</span>'
        f'</div>'
    )


def page_title_html(
    title: str,
    tokens: dict,
    *,
    subtitle: str | None = None,
    margin: str = "16px 0 24px",
) -> str:
    """Return the shared centered page title block."""
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f'<p class="gl-page-subtitle">{subtitle}</p>'
        )
    return (
        f'<div style="margin:{margin};text-align:center;">'
        f'<h1 class="gl-page-title">{title}</h1>'
        f'{subtitle_html}</div>'
    )


def section_heading_html(
    title: str,
    icon_svg: str,
    *,
    side_width: int = 24,
) -> str:
    """Return a centered section heading with balanced icon spacing."""
    return (
        '<div class="gl-section-heading">'
        f'<div style="display:flex;width:{side_width}px;">{icon_svg}</div>'
        f'<h2>{title}</h2>'
        f'<div style="width:{side_width}px;"></div>'
        '</div>'
    )


def empty_state_html(
    title: str,
    message: str,
    tokens: dict,
    *,
    icon_name: str = "info",
    max_width: str = "640px",
    margin: str = "12px auto",
) -> str:
    """Return the shared neutral empty/incomplete-data state."""
    icon = lucide_icon(icon_name, size=20, color=tokens["text_secondary"])
    return (
        f'<div class="gl-empty-state" style="max-width:{max_width};'
        f'margin:{margin};">'
        f'<div style="display:flex;align-items:center;flex-shrink:0;">'
        f'{icon}</div>'
        '<div style="flex:1;min-width:0;">'
        f'<div class="gl-empty-state-title">{title}</div>'
        f'<div class="gl-empty-state-message">{message}</div>'
        '</div></div>'
    )


# ---------------------------------------------------------------------------
# Direct Streamlit renderers
# ---------------------------------------------------------------------------

def show_divider(dark_mode: bool, margin: str = "36px auto") -> None:
    """Render a hairline divider clipped to content width."""
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]
    st.markdown(
        f'<div style="width:100%;max-width:1100px;'
        f'margin:{margin};'
        f'border-top:1px solid {tokens["border"]};"></div>',
        unsafe_allow_html=True,
    )


def show_icon_heading(
    title: str,
    icon_svg: str,
    *,
    center: bool = False,
    confidence: float | None = None,
    tokens: dict | None = None,
) -> None:
    """Render an H2 heading with an inline icon and optional confidence."""
    if tokens is None:
        dark = st.session_state.get("dark_mode", False)
        tokens = THEME_TOKENS["dark" if dark else "light"]

    justify = "center" if center else "flex-start"

    confidence_badge_html = ""
    if confidence is not None:
        pct = int(confidence * 100)
        if confidence >= 0.8:
            badge_color = tokens["accent"]
        elif confidence >= 0.6:
            badge_color = tokens["risk_medium"]
        else:
            badge_color = tokens["text_secondary"]
        badge_icon = lucide_icon("shield", size=13, color=badge_color)
        confidence_badge_html = (
            f'<div class="gl-confidence-badge" style="position:absolute;'
            f'right:0;top:50%;transform:translateY(-50%);display:flex;'
            f'align-items:center;gap:7px;'
            f'background:{hex_to_rgba(badge_color, 0.14)};'
            f'border:1px solid {hex_to_rgba(badge_color, 0.45)};'
            f'backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);'
            f'color:{badge_color};padding:5px 14px;border-radius:100px;'
            f'font-size:12px;font-weight:700;'
            f'font-family:{FONT_MONO};white-space:nowrap;">'
            f'{badge_icon}<span>Confidence: {pct}%</span></div>'
        )

    wrapper_position = "relative" if confidence_badge_html else "static"
    wrapper_class = "gl-heading-wrap" if confidence_badge_html else ""
    heading_html = (
        f'<div class="{wrapper_class}" style="position:{wrapper_position};'
        f'display:flex;align-items:center;justify-content:{justify};'
        f'margin-bottom:16px;">'
        f'<h2 style="margin:0;display:flex;align-items:center;gap:20px;">'
        f'{icon_svg}{title}</h2>'
        f'{confidence_badge_html}</div>'
    )
    st.markdown(heading_html, unsafe_allow_html=True)


def show_footer(dark_mode: bool) -> None:
    """Render the team footer."""
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
        f'<div style="margin-bottom:8px;font-size:13px;">'
        f'<a class="footer-link" href="{m["url"]}" target="_blank" '
        f'rel="noopener noreferrer">{m["name"]}</a>'
        f'<span style="color:{tokens["text_secondary"]};font-size:12px;">'
        f' · {m["role"]}</span></div>'
        for m in team_members
    )
    footer_html = f"""
    <div style="margin-top:48px;padding-top:28px;">
        <div style="border-top:1px solid {tokens["border"]};
            padding-top:28px;display:grid;
            grid-template-columns:1.4fr 1fr 1.4fr;gap:32px;">
            <div>
                <div class="footer-heading">Granite Lifeline</div>
                <div style="margin-bottom:6px;">
                    <a class="footer-link"
                       href="https://github.com/granite-lifeline"
                       target="_blank" rel="noopener noreferrer"
                       style="font-size:15px;">Granite Lifeline</a>
                </div>
                <div style="color:{tokens["text_secondary"]};font-size:13px;">
                    Vehicle health monitoring · IBM-sponsored project
                </div>
            </div>
            <div>
                <div class="footer-heading">Links</div>
                <div style="margin-bottom:8px;font-size:13px;">
                    <a class="footer-link"
                       href="https://github.com/granite-lifeline/granite-lifeline"
                       target="_blank" rel="noopener noreferrer">
                       Repository</a>
                </div>
                <div style="font-size:13px;">
                    <a class="footer-link"
                       href="https://granite-lifeline.github.io/granite-lifeline-blog/"
                       target="_blank" rel="noopener noreferrer">Blog</a>
                </div>
            </div>
            <div>
                <div class="footer-heading">Team</div>
                <div style="color:{tokens["text_secondary"]};font-size:12px;
                    margin-bottom:10px;">
                    University of Bristol MSc Computer Science
                </div>
                <div style="color:{tokens["text"]};">{team_html}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)


def show_pipeline_error_card(
    error_type: str,
    tokens: dict,
) -> None:
    """GL-261: Render an amber warning card for a known pipeline error."""
    _MESSAGES: dict[str, str] = {
        "empty_file": (
            "The uploaded file appears to be empty. "
            "Please upload a valid OBD-II CSV file."
        ),
        "pipeline_timeout": (
            "The analysis pipeline timed out. This may happen with very "
            "large files. Please try uploading a shorter drive session "
            "(15\u201330 minutes recommended)."
        ),
        "model_unavailable": (
            "The anomaly detection model is currently unavailable. "
            "Analysis will resume when the model service is restored."
        ),
        "report_unavailable": (
            "The diagnostic report could not be generated. "
            "Raw analysis results are shown below."
        ),
    }
    message = _MESSAGES.get(error_type, f"Unknown error: {error_type}")
    st.markdown(
        warning_banner_html(
            message, tokens, label="Pipeline warning"
        ),
        unsafe_allow_html=True,
    )
