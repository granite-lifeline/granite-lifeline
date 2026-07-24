"""Detail page — component drill-down with gauge, trend, signals, report."""

from __future__ import annotations

import html as _html
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from anomaly_display import COMPONENT_DISPLAY_NAMES
from data_store import get_overview_components
from failure_prediction import (
    format_failure_prediction_text,
    get_data_quality_notes,
)
from glossary import get_signal_display_name, get_signal_tooltip
from theme import (
    COMPONENT_ICONS,
    FONT_MONO,
    THEME_TOKENS,
    hex_to_rgba,
    lucide_icon,
    svg_data_uri,
)
from ui_components import (
    show_divider,
    show_footer,
    show_icon_heading,
)


# ---------------------------------------------------------------------------
# Sub-renderers
# ---------------------------------------------------------------------------

def _risk_badge_color(risk_level: str, tokens: dict) -> str:
    return {
        "High": tokens["risk_high"],
        "Medium": tokens["risk_medium"],
        "Low": tokens["risk_low"],
    }.get(risk_level, tokens["text_secondary"])


def _render_failure_prediction(
    component_data: dict,
    tokens: dict,
) -> None:
    """Failure prediction banner + data-quality notes."""
    prediction_text, has_value = format_failure_prediction_text(
        component_data
    )
    notes = get_data_quality_notes(component_data)
    text_color = tokens["text"] if has_value else tokens["text_secondary"]
    border_color = (
        hex_to_rgba(tokens["accent"], 0.35)
        if has_value else tokens["glass_border"]
    )
    info_icon = lucide_icon("info", size=18, color=tokens["accent"])

    note_items = "".join(
        '<div style="display:flex;gap:8px;margin-top:8px;">'
        f'<span style="color:{tokens["accent"]};'
        'font-size:13px;line-height:1.45;">•</span>'
        f'<span style="color:{tokens["text"]};'
        f'font-size:13px;line-height:1.45;">{_html.escape(n)}</span>'
        '</div>'
        for n in notes
    )
    notes_panel = ""
    if notes:
        notes_panel = (
            f'<div style="flex:1;min-width:260px;'
            f'background:{tokens["glass_surface"]};'
            f'border:1px solid {tokens["glass_border"]};'
            'border-radius:16px;padding:14px 16px 13px 16px;'
            f'box-shadow:0 8px 24px {tokens["shadow"]},'
            'inset 0 1px 0 rgba(255,255,255,0.10);">'
            '<div style="display:flex;align-items:center;'
            'justify-content:center;gap:8px;'
            f'color:{tokens["text"]};font-size:14px;font-weight:700;'
            f'padding-bottom:8px;border-bottom:2px solid {tokens["border"]};">'
            f'{info_icon}Data Quality Notes</div>'
            f'<div style="margin-top:4px;">{note_items}</div></div>'
        )

    if has_value:
        prob = component_data.get("estimated_failure_probability")
        cycles = component_data.get("estimated_cycles_to_failure")
        pct = int(round(float(prob) * 100))
        cnt = int(cycles)
        prediction_html = (
            '<div style="display:flex;align-items:baseline;'
            'justify-content:center;gap:8px;flex-wrap:wrap;text-align:center;">'
            f'<span style="color:{tokens["accent"]};'
            f'font-family:{FONT_MONO};font-size:16px;font-weight:800;">'
            f'{pct}%</span>'
            f'<span style="color:{tokens["text"]};font-size:15px;'
            'line-height:1.45;">probability of failure within the next</span>'
            f'<span style="color:{tokens["text"]};'
            'font-size:16px;font-weight:800;line-height:1.45;">'
            f'{cnt} trips</span></div>'
        )
    else:
        pending = lucide_icon("info", size=20, color=tokens["text_secondary"])
        prediction_html = (
            '<div style="display:flex;justify-content:center;width:100%;">'
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:12px;padding:16px 20px;'
            'display:flex;align-items:center;gap:12px;max-width:600px;">'
            f'<div style="display:flex;align-items:center;flex-shrink:0;">'
            f'{pending}</div>'
            f'<div style="color:{text_color};font-size:14px;line-height:1.5;">'
            f'{_html.escape(prediction_text)}</div>'
            '</div></div>'
        )

    card_html = (
        f'<div style="background:{tokens["glass_surface"]};'
        'backdrop-filter:blur(24px) saturate(160%);'
        '-webkit-backdrop-filter:blur(24px) saturate(160%);'
        f'border:1px solid {border_color};border-radius:16px;'
        'padding:18px 20px;margin:0 auto 28px auto;'
        f'box-shadow:0 2px 12px {tokens["shadow"]};max-width:1120px;">'
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:18px;flex-wrap:wrap;">'
        '<div style="flex:1.25;min-width:260px;display:flex;'
        'align-items:center;justify-content:center;">'
        f'<div style="min-width:0;width:100%;">{prediction_html}</div>'
        '</div>'
        f'{notes_panel}</div></div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_gauge(
    component_data: dict,
    tokens: dict,
    badge_bg: str,
    trend: list[float],
) -> None:
    """Risk score gauge chart."""
    risk_level = component_data.get("risk_level")
    if risk_level not in {"High", "Medium", "Low"}:
        info = lucide_icon("info", size=20, color=tokens["text_secondary"])
        st.markdown(
            f'<div style="display:flex;justify-content:center;width:100%;">'
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:12px;padding:18px 20px;margin:28px 0;'
            'max-width:420px;display:flex;align-items:center;gap:12px;">'
            f'<div style="display:flex;align-items:center;flex-shrink:0;">'
            f'{info}</div>'
            f'<div style="color:{tokens["text"]};font-size:14px;'
            'line-height:1.5;">No risk score is available for this '
            'component yet.</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    risk_pct = int(component_data["risk_score"] * 100)
    delta_config = None
    if len(trend) >= 2:
        delta_config = dict(
            reference=trend[-2] * 100,
            increasing=dict(color=tokens["risk_high"]),
            decreasing=dict(color=tokens["risk_low"]),
        )
    fig = go.Figure(go.Indicator(
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
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=tokens["text_secondary"]),
        margin=dict(l=40, r=40, t=30, b=10),
        height=282,
    )
    st.plotly_chart(fig, use_container_width=True, key="detail_risk_gauge")

    ts = component_data.get("timestamp", "")
    if ts:
        try:
            fmt = datetime.fromisoformat(
                ts.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M")
        except Exception:
            fmt = ts
    else:
        fmt = "N/A"
    st.markdown(
        f'<p style="text-align:center;color:{tokens["text_secondary"]};'
        f'font-size:12px;margin:-8px 0 0 0;">Last updated: {fmt}</p>',
        unsafe_allow_html=True,
    )


def _render_trend(
    component_data: dict,
    tokens: dict,
    dark_mode: bool,
    trend: list[float],
) -> None:
    """Risk trend line chart."""
    if len(trend) < 2:
        info = lucide_icon("info", size=20, color=tokens["text_secondary"])
        st.markdown(
            f'<div style="display:flex;justify-content:center;width:100%;">'
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:12px;padding:16px 20px;margin:12px 0;'
            'max-width:600px;display:flex;align-items:center;gap:12px;">'
            f'<div style="display:flex;align-items:center;flex-shrink:0;">'
            f'{info}</div>'
            f'<div style="color:{tokens["text"]};font-size:14px;'
            'line-height:1.5;">Not enough data yet to show a trend.</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    history = component_data.get("risk_history") or []
    time_labels = []
    for idx, entry in enumerate(history[-len(trend):]):
        raw_ts = entry.get("timestamp", "")
        try:
            label = datetime.fromisoformat(
                raw_ts.replace("Z", "+00:00")
            ).strftime("%m-%d %H:%M")
        except Exception:
            label = raw_ts or f"T-{len(trend) - idx - 1}"
        time_labels.append(label)
    fill_color = (
        "rgba(41,151,255,0.15)" if dark_mode else "rgba(0,113,227,0.12)"
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_labels,
        y=trend,
        mode="lines+markers",
        line=dict(color=tokens["accent"], width=3, shape="spline"),
        marker=dict(
            size=8,
            color=tokens["accent"],
            line=dict(color=tokens["surface"], width=2),
        ),
        fill="tozeroy",
        fillcolor=fill_color,
        name="Risk Score",
        hovertemplate="<b>%{x}</b><br>Risk Score: %{y:.0%}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=tokens["text_secondary"]),
        xaxis=dict(gridcolor=tokens["border"], showgrid=True),
        yaxis=dict(
            gridcolor=tokens["border"],
            showgrid=True,
            range=[0, 1],
            tickformat=".0%",
        ),
        margin=dict(l=40, r=20, t=20, b=40),
        height=260,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="detail_trend_chart")
    st.caption(
        "Risk score over the latest recorded model windows. "
        "Higher values indicate greater risk."
    )


def _render_signals(
    component_data: dict,
    tokens: dict,
) -> None:
    """Key signals table."""
    key_signals = component_data.get("key_signals") or []
    if not key_signals:
        info = lucide_icon("info", size=20, color=tokens["text_secondary"])
        st.markdown(
            f'<div style="display:flex;justify-content:center;width:100%;">'
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:12px;padding:16px 20px;margin:12px 0;'
            'max-width:600px;display:flex;align-items:center;gap:12px;">'
            f'<div style="display:flex;align-items:center;flex-shrink:0;">'
            f'{info}</div>'
            f'<div style="color:{tokens["text"]};font-size:14px;'
            'line-height:1.5;">No signal data available for this component.'
            '</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    header_html = (
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:8px 12px;font-size:11px;font-weight:700;'
        f'letter-spacing:0.4px;text-transform:uppercase;'
        f'color:{tokens["text_secondary"]};">'
        '<div style="flex:2.5;min-width:100px;">Signal</div>'
        '<div style="flex:1.5;min-width:70px;">Reading</div>'
        '<div style="flex:2;min-width:90px;">Normal Range</div>'
        '<div style="flex:0.8;min-width:50px;">Unit</div>'
        '<div style="flex:1.2;min-width:76px;max-width:90px;'
        'text-align:center;">Status</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    signals_with_status = []
    for sig in key_signals:
        lo, hi = sig["reference_range"]
        abnormal = sig["value"] < lo or sig["value"] > hi
        signals_with_status.append((sig, "ABNORMAL" if abnormal else "NORMAL"))
    signals_with_status.sort(key=lambda x: x[1] == "NORMAL")

    row_bg = hex_to_rgba(tokens["text"], 0.045)
    for sig, status in signals_with_status:
        lo, hi = sig["reference_range"]
        badge_color = (
            tokens["risk_high"] if status == "ABNORMAL"
            else tokens["risk_low"]
        )
        name = get_signal_display_name(sig["feature"])
        tooltip = get_signal_tooltip(sig["feature"])
        safe_name = _html.escape(str(name))
        safe_tooltip = _html.escape(str(tooltip), quote=True)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'background:{row_bg};border-radius:8px;'
            f'padding:10px 12px;margin-bottom:6px;">'
            f'<div style="flex:2.5;min-width:100px;font-weight:600;'
            f'color:{tokens["text"]};font-size:13px;line-height:1.3;'
            f'word-wrap:break-word;" title="{safe_tooltip}">'
            f'{safe_name}</div>'
            f'<div style="flex:1.5;min-width:70px;'
            f'font-family:{FONT_MONO};color:{tokens["text"]};'
            f'font-size:13px;font-weight:600;">{sig["value"]}</div>'
            f'<div style="flex:2;min-width:90px;'
            f'font-family:{FONT_MONO};color:{tokens["text_secondary"]};'
            f'font-size:12px;">{lo}\u2013{hi}</div>'
            f'<div style="flex:0.8;min-width:50px;'
            f'font-family:{FONT_MONO};color:{tokens["text_secondary"]};'
            f'font-size:12px;">{sig["unit"]}</div>'
            f'<div style="flex:1.2;min-width:76px;max-width:90px;'
            f'text-align:center;background-color:{badge_color};'
            'color:white;padding:4px 6px;border-radius:12px;'
            f'font-size:10px;font-weight:600;">{status}</div>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_report(
    component_data: dict,
    tokens: dict,
) -> None:
    """Diagnostic report section (What's Happening / Why / Action)."""
    pending = "Pending Granite LLM report generation..."
    anomaly_desc = component_data.get("anomaly_description") or pending
    possible_cause = component_data.get("possible_cause") or pending
    recommended_action = component_data.get("recommended_action") or pending

    if isinstance(recommended_action, list):
        items = "".join(
            f'<div style="display:flex;gap:8px;align-items:flex-start;'
            f'margin-bottom:10px;">'
            f'<span style="color:{tokens["accent"]};font-weight:700;'
            f'flex-shrink:0;">\u2022</span>'
            f'<span style="color:{tokens["text"]};">{a}</span></div>'
            for a in recommended_action
        )
        action_html = (
            f'<div style="text-align:center;">'
            f'<div style="display:inline-block;text-align:left;">'
            f'{items}</div></div>'
        )
    else:
        action_html = (
            f"<div style='display:flex;justify-content:center;'>"
            f"<p style='margin:0;max-width:90%;color:{tokens['text']};"
            f"text-align:left;'>{recommended_action}</p></div>"
        )

    info_cards = [
        {
            "icon": lucide_icon("info", size=18, color=tokens["accent"]),
            "title": "What's Happening",
            "body": anomaly_desc,
        },
        {
            "icon": lucide_icon(
                "help-circle", size=18, color=tokens["accent"]
            ),
            "title": "Why This Matters",
            "body": possible_cause,
        },
    ]

    report_cols = st.columns([5, 7], gap="medium")
    with report_cols[0]:
        for card in info_cards:
            st.markdown(
                f'<div style="background:{tokens["glass_surface"]};'
                'backdrop-filter:blur(24px) saturate(160%);'
                '-webkit-backdrop-filter:blur(24px) saturate(160%);'
                f'border:1px solid {tokens["glass_border"]};'
                'border-radius:16px;padding:16px 18px;margin:0 0 14px 0;'
                f'box-shadow:0 2px 12px {tokens["shadow"]};">'
                f'<h3 style="color:{tokens["text"]};margin:0 0 12px 0;'
                'font-size:15px;font-weight:700;display:flex;'
                'align-items:center;justify-content:center;gap:9px;'
                f'padding-bottom:9px;border-bottom:1px solid {tokens["border"]};">'
                f'{card["icon"]}{card["title"]}</h3>'
                '<div style="display:flex;justify-content:center;">'
                f'<p style="margin:0;max-width:90%;font-size:14px;'
                f'line-height:1.6;color:{tokens["text"]};text-align:left;">'
                f'{card["body"]}</p></div></div>',
                unsafe_allow_html=True,
            )

    with report_cols[1]:
        action_icon = lucide_icon(
            "check-square", size=22, color=tokens["accent"]
        )
        st.markdown(
            f'<div style="'
            f'background:{hex_to_rgba(tokens["accent"], 0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["accent"], 0.28)};'
            f'border-top:3px solid {tokens["accent"]};'
            'border-radius:16px;padding:22px 24px;'
            f'box-shadow:0 2px 12px {tokens["shadow"]};">'
            f'<h3 style="color:{tokens["text"]};margin:0 0 16px 0;'
            'font-size:18px;font-weight:700;display:flex;'
            'align-items:center;justify-content:center;gap:10px;'
            f'padding-bottom:12px;'
            f'border-bottom:1px solid {hex_to_rgba(tokens["accent"], 0.25)};">'
            f'{action_icon}What You Should Do</h3>'
            f'<div style="font-size:14.5px;line-height:1.7;text-align:center;">'
            f'{action_html}</div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def render_component_detail(
    component_data: dict,
    dark_mode: bool,
    tokens: dict,
) -> None:
    """Render the full detail view for one component."""
    risk_level = component_data.get("risk_level", "Unknown")
    badge_bg = _risk_badge_color(risk_level, tokens)
    component_id = component_data["component"]
    display_name = COMPONENT_DISPLAY_NAMES.get(component_id, component_id)

    st.markdown(
        f'<div style="display:flex;align-items:center;'
        f'justify-content:center;margin-bottom:24px;">'
        f'<h1 style="margin:0;display:inline;">{display_name}</h1></div>',
        unsafe_allow_html=True,
    )

    # Incomplete-data info panel
    missing_fields, missing_sections = [], []
    if risk_level == "Unknown":
        for field in ("risk_level", "anomaly_description",
                      "possible_cause", "recommended_action"):
            if not component_data.get(field):
                missing_fields.append(field)
    risk_history = component_data.get("risk_history") or []
    key_signals = component_data.get("key_signals") or []
    if not risk_history or len(risk_history) < 2:
        missing_sections.append("Risk Trend data")
    if not key_signals:
        missing_sections.append("Key Signals data")

    if missing_fields or missing_sections:
        parts = []
        if missing_fields:
            parts.append(f"missing critical fields ({', '.join(missing_fields)})")
        if missing_sections:
            parts.append(f"missing {', '.join(missing_sections)}")
        msg = "This component has " + " and ".join(parts) + "."
        info_icon = lucide_icon("info", size=20, color=tokens["text_secondary"])
        st.markdown(
            f'<div style="background:{hex_to_rgba(tokens["text_secondary"],0.08)};'
            f'border:1px solid {hex_to_rgba(tokens["text_secondary"],0.20)};'
            'border-radius:12px;padding:16px 20px;'
            'margin:0 auto 24px auto;max-width:700px;'
            'display:flex;align-items:flex-start;gap:12px;">'
            f'{info_icon}'
            '<div style="flex:1;">'
            f'<div style="font-weight:600;color:{tokens["text"]};'
            'margin-bottom:4px;">Incomplete Data</div>'
            f'<div style="color:{tokens["text_secondary"]};'
            f'font-size:14px;line-height:1.5;">{msg} Some visualizations '
            'and information may not be available.</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # Failure prediction heading + card
    pred_has_value = format_failure_prediction_text(component_data)[1]
    fi_color = tokens["accent"] if pred_has_value else tokens["text_secondary"]
    failure_icon = lucide_icon("alert-triangle", size=24, color=fi_color)
    st.markdown(
        '<div style="display:flex;align-items:center;'
        'justify-content:center;margin-bottom:16px;">'
        '<div style="display:grid;grid-template-columns:24px auto 24px;'
        'align-items:center;column-gap:20px;">'
        f'<div style="display:flex;">{failure_icon}</div>'
        '<h2 style="margin:0;">Failure Prediction</h2>'
        '<div style="width:24px;"></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    _render_failure_prediction(component_data, tokens)

    # Hero row: gauge + trend
    trend = [e["risk_score"] for e in (component_data.get("risk_history") or [])]

    st.markdown(
        f"""
        <style>
            .st-key-gauge_card,
            .st-key-trend_card,
            .st-key-signals_card {{
                background: {tokens["glass_surface"]} !important;
                backdrop-filter: blur(24px) saturate(160%) !important;
                -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
                border: 1px solid {tokens["glass_border"]} !important;
                border-radius: 16px !important;
                box-shadow: 0 2px 12px {tokens["shadow"]} !important;
                padding: 20px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    hero_cols = st.columns([4, 8], gap="large")
    with hero_cols[0]:
        show_icon_heading(
            "Risk Score",
            lucide_icon("zap", size=24, color=tokens["accent"]),
            center=True,
            tokens=tokens,
        )
        with st.container(key="gauge_card"):
            _render_gauge(component_data, tokens, badge_bg, trend)

    with hero_cols[1]:
        show_icon_heading(
            "Risk Score Trend",
            lucide_icon("trending-up", size=24, color=tokens["accent"]),
            center=True,
            tokens=tokens,
        )
        with st.container(key="trend_card"):
            _render_trend(component_data, tokens, dark_mode, trend)

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    # Key signals
    show_icon_heading(
        "Key Signals",
        lucide_icon("activity", size=24, color=tokens["accent"]),
        center=True,
        tokens=tokens,
    )
    with st.container(key="signals_card"):
        _render_signals(component_data, tokens)

    show_divider(dark_mode)

    # Diagnostic report
    conf = component_data.get("prediction_confidence")
    show_icon_heading(
        "Diagnostic Report",
        lucide_icon("file-text", size=22, color=tokens["accent"]),
        center=True,
        confidence=conf,
        tokens=tokens,
    )
    _render_report(component_data, tokens)


def show_detail_page() -> None:
    """Display the Component Detail Page with tab-based switching."""
    component_key = st.session_state.get("selected_component")
    overview_components = get_overview_components()
    component_lookup = {
        k: d for k, d, _ in overview_components
    }

    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    if not component_key or component_key not in component_lookup:
        st.error("Component not found.")
        if st.button("\u2190 Back to Overview"):
            st.session_state["page"] = "overview"
            st.rerun()
        return

    if st.button("\u2190 Back to Overview"):
        st.session_state["page"] = "overview"
        st.rerun()

    risk_color_map = {
        "High": tokens["risk_high"],
        "Medium": tokens["risk_medium"],
        "Low": tokens["risk_low"],
        "Unknown": tokens["text_secondary"],
    }

    tab_row_key = overview_components[0][0]
    tab_row_selector = (
        'div[data-testid="stHorizontalBlock"]'
        f":has(.st-key-tab_btn_{tab_row_key})"
    )
    tab_cols = st.columns(len(overview_components), gap="small")
    tab_css_rules: list[str] = []
    tab_css_rules.append(f"""
        {tab_row_selector} {{
            gap: 0.35rem !important;
            flex-wrap: nowrap !important;
            align-items: stretch !important;
        }}
        {tab_row_selector} > div[data-testid="stColumn"] {{
            min-width: 0 !important;
            flex: 1 1 0 !important;
        }}
        {tab_row_selector} .stButton {{ height: 100% !important; }}
        {tab_row_selector} button {{
            min-height: 52px !important;
            font-size: 12px !important;
            line-height: 1.2 !important;
            text-align: center !important;
            white-space: normal !important;
            padding-top: 6px !important;
            padding-bottom: 6px !important;
        }}
        {tab_row_selector} button p {{
            font-size: 12px !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }}
    """)

    for col, (tab_key, tab_data, _) in zip(tab_cols, overview_components):
        with col:
            is_active = tab_key == component_key
            icon_color = risk_color_map.get(
                tab_data.get("risk_level", "Unknown"),
                tokens["text_secondary"],
            )
            icon_svg = lucide_icon(
                COMPONENT_ICONS.get(tab_key, "activity"),
                size=16,
                color=icon_color,
            )
            icon_src = svg_data_uri(icon_svg)
            label = (
                COMPONENT_DISPLAY_NAMES.get(tab_key, tab_key) or tab_key
            )
            if st.button(
                label,
                key=f"tab_btn_{tab_key}",
                use_container_width=True,
            ):
                st.session_state["selected_component"] = tab_key
                st.rerun()

            icon_css = (
                f"background-color:transparent !important;"
                f"background-image:url('{icon_src}') !important;"
                "background-repeat:no-repeat !important;"
                "background-position:10px center !important;"
                "background-size:16px 16px !important;"
                "padding:8px 8px 8px 34px !important;"
            )
            if is_active:
                tab_css_rules.append(f"""
                    .st-key-tab_btn_{tab_key} button {{
                        {icon_css}
                        color: {tokens["accent"]} !important;
                        border: none !important;
                        border-bottom: 2.5px solid {tokens["accent"]} !important;
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
                        border-bottom: 2.5px solid {tokens["border"]} !important;
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
    render_component_detail(
        component_lookup[component_key], dark_mode, tokens
    )
    show_footer(dark_mode)
