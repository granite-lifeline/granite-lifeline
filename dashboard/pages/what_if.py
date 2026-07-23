"""What-If analysis page for dashboard-side scenario comparison."""

from __future__ import annotations

import html
from dataclasses import dataclass

import streamlit as st

try:
    from anomaly_display import COMPONENT_DISPLAY_NAMES
    from data_store import get_overview_components
    from theme import (
        COMPONENT_ICONS,
        FONT_MONO,
        THEME_TOKENS,
        hex_to_rgba,
        lucide_icon,
    )
except ImportError:  # package import during tests
    from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES
    from dashboard.data_store import get_overview_components
    from dashboard.theme import (
        COMPONENT_ICONS,
        FONT_MONO,
        THEME_TOKENS,
        hex_to_rgba,
        lucide_icon,
    )


STYLE_MULTIPLIERS = {
    "Conservative": 0.90,
    "Normal": 1.00,
    "Aggressive": 1.12,
}


@dataclass(frozen=True)
class ScenarioInputs:
    """Dashboard-side what-if controls."""

    driving_style: str
    coolant_temp_offset: float
    rpm_multiplier: float
    load_stress_multiplier: float
    intake_temp_offset: float


def _risk_level(score: float) -> str:
    if score >= 0.70:
        return "High"
    if score >= 0.30:
        return "Medium"
    return "Low"


def _component_sensitivity(component_key: str, inputs: ScenarioInputs) -> float:
    """Return a transparent heuristic risk delta for one component."""
    style_delta = STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
    rpm_delta = inputs.rpm_multiplier - 1.0
    load_delta = inputs.load_stress_multiplier - 1.0

    weights = {
        "cooling_degradation": (
            0.35 * style_delta
            + 0.010 * inputs.coolant_temp_offset
            + 0.18 * max(rpm_delta, 0)
            + 0.10 * max(load_delta, 0)
            + 0.003 * max(inputs.intake_temp_offset, 0)
        ),
        "air_intake_maf_anomaly": (
            0.28 * style_delta
            + 0.20 * max(rpm_delta, 0)
            + 0.24 * max(load_delta, 0)
            + 0.002 * abs(inputs.intake_temp_offset)
        ),
        "accelerator_pedal_sensor": (
            0.20 * style_delta
            + 0.30 * max(load_delta, 0)
            + 0.08 * max(rpm_delta, 0)
        ),
        "intake_air_temperature_sensor_fault": (
            0.12 * style_delta
            + 0.012 * inputs.intake_temp_offset
            + 0.004 * inputs.coolant_temp_offset
        ),
        "map_load_signal_plausibility_fault": (
            0.24 * style_delta
            + 0.22 * max(rpm_delta, 0)
            + 0.26 * max(load_delta, 0)
        ),
    }.get(component_key, 0.10 * style_delta)

    return weights


def project_component_risk(
    component_key: str,
    baseline_score: float,
    inputs: ScenarioInputs,
) -> float:
    """Project a scenario risk score from the current dashboard baseline."""
    baseline = max(0.0, min(1.0, float(baseline_score or 0.0)))
    projected = baseline + _component_sensitivity(component_key, inputs)
    if inputs.driving_style == "Conservative":
        projected -= 0.04 * (baseline - projected)
    return max(0.0, min(1.0, projected))


def _risk_color(level: str, tokens: dict) -> str:
    return {
        "High": tokens["risk_high"],
        "Medium": tokens["risk_medium"],
        "Low": tokens["risk_low"],
    }.get(level, tokens["text_secondary"])


def _render_page_styles(tokens: dict) -> None:
    st.markdown(
        f"""
        <style>
        .what-if-shell {{
            max-width:1180px;
            margin:0 auto;
        }}
        .what-if-card {{
            background:{tokens["glass_surface"]};
            border:1px solid {tokens["glass_border"]};
            border-radius:16px;
            box-shadow:0 2px 12px {tokens["shadow"]};
            padding:20px;
        }}
        .what-if-row {{
            align-items:center;
            border-top:1px solid {tokens["border"]};
            display:grid;
            gap:16px;
            grid-template-columns:minmax(220px,1.35fr) 110px 110px 90px 120px;
            padding:16px 0;
        }}
        .what-if-row:first-child {{
            border-top:none;
            padding-top:0;
        }}
        .what-if-name {{
            align-items:center;
            color:{tokens["text"]};
            display:flex;
            font-size:14px;
            font-weight:700;
            gap:10px;
            min-width:0;
        }}
        .what-if-score {{
            color:{tokens["text"]};
            font-family:{FONT_MONO};
            font-size:18px;
            font-weight:800;
            text-align:right;
        }}
        .what-if-label {{
            color:{tokens["text_secondary"]};
            font-size:11px;
            font-weight:700;
            letter-spacing:0.3px;
            text-transform:uppercase;
        }}
        .what-if-pill {{
            border-radius:999px;
            color:#fff;
            display:inline-flex;
            font-size:12px;
            font-weight:800;
            justify-content:center;
            line-height:1;
            padding:7px 10px;
            white-space:nowrap;
        }}
        .what-if-meter {{
            background:{tokens["surface_alt"]};
            border-radius:999px;
            height:8px;
            overflow:hidden;
            width:100%;
        }}
        .what-if-meter > span {{
            border-radius:999px;
            display:block;
            height:8px;
        }}
        .st-key-what_if_back_btn button,
        .st-key-what_if_dashboard_btn button {{
            background:transparent !important;
            border:1px solid {tokens["border"]} !important;
            border-radius:10px !important;
            color:{tokens["text"]} !important;
            font-size:13px !important;
            font-weight:700 !important;
        }}
        .st-key-what_if_back_btn button:hover,
        .st-key-what_if_dashboard_btn button:hover {{
            border-color:{tokens["accent"]} !important;
            color:{tokens["accent"]} !important;
        }}
        @media (max-width: 760px) {{
            .what-if-row {{
                grid-template-columns:1fr 1fr;
            }}
            .what-if-name {{
                grid-column:1 / -1;
            }}
            .what-if-score {{
                text-align:left;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_cell(label: str, value: str) -> str:
    return (
        '<div>'
        f'<div class="what-if-label">{html.escape(label)}</div>'
        f'<div class="what-if-score">{html.escape(value)}</div>'
        '</div>'
    )


def _render_component_row(
    component_key: str,
    baseline: float,
    projected: float,
    tokens: dict,
) -> str:
    baseline_pct = int(round(baseline * 100))
    projected_pct = int(round(projected * 100))
    delta_pct = projected_pct - baseline_pct
    level = _risk_level(projected)
    level_color = _risk_color(level, tokens)
    delta_prefix = "+" if delta_pct > 0 else ""
    icon = lucide_icon(
        COMPONENT_ICONS.get(component_key, "activity"),
        size=18,
        color=level_color,
    )
    return (
        '<div class="what-if-row">'
        '<div class="what-if-name">'
        f'{icon}<span>{html.escape(COMPONENT_DISPLAY_NAMES.get(component_key, component_key))}</span>'
        '</div>'
        f'{_metric_cell("Baseline", f"{baseline_pct}%")}'
        f'{_metric_cell("Scenario", f"{projected_pct}%")}'
        f'{_metric_cell("Delta", f"{delta_prefix}{delta_pct}%")}'
        '<div>'
        f'<span class="what-if-pill" style="background:{level_color};">'
        f'{html.escape(level)}</span>'
        '<div class="what-if-meter" style="margin-top:10px;">'
        f'<span style="background:{level_color};width:{projected_pct}%;"></span>'
        '</div></div></div>'
    )


def _render_summary_card(
    rows: list[tuple[str, float, float]],
    inputs: ScenarioInputs,
    tokens: dict,
) -> None:
    if not rows:
        st.markdown(
            '<div class="what-if-card">No component data is available.</div>',
            unsafe_allow_html=True,
        )
        return

    avg_baseline = sum(row[1] for row in rows) / len(rows)
    avg_projected = sum(row[2] for row in rows) / len(rows)
    delta = int(round((avg_projected - avg_baseline) * 100))
    direction = "higher" if delta > 0 else "lower" if delta < 0 else "unchanged"
    summary = (
        f'{inputs.driving_style} scenario is {abs(delta)} percentage points '
        f'{direction} than the current dashboard baseline on average.'
    )
    st.markdown(
        '<div class="what-if-card" style="margin-bottom:18px;">'
        f'<div style="color:{tokens["text_secondary"]};font-size:12px;'
        'font-weight:700;letter-spacing:0.3px;text-transform:uppercase;">'
        'Scenario projection</div>'
        f'<div style="color:{tokens["text"]};font-size:22px;font-weight:800;'
        'line-height:1.25;margin-top:8px;">'
        f'{html.escape(summary)}</div>'
        f'<div style="color:{tokens["text_secondary"]};font-size:13px;'
        'line-height:1.45;margin-top:10px;">'
        'Dashboard-side sensitivity estimate. Full simulation can replace '
        'this estimator when Model Layer scenario inference is available.'
        '</div></div>',
        unsafe_allow_html=True,
    )


def show_what_if_page() -> None:
    """Render the GL-263 What-If Analysis MVP."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]
    _render_page_styles(tokens)

    st.markdown('<div class="what-if-shell">', unsafe_allow_html=True)
    top_left, top_right = st.columns([8, 2])
    with top_left:
        if st.button(
            "\u2190 Back to Dashboard",
            key="what_if_back_btn",
            help="Return to the dashboard overview",
        ):
            st.session_state["page"] = "overview"
            st.rerun()
    with top_right:
        if st.button(
            "Dashboard",
            key="what_if_dashboard_btn",
            use_container_width=True,
        ):
            st.session_state["page"] = "overview"
            st.rerun()

    st.markdown(
        f'<div style="margin:18px 0 24px 0;text-align:center;">'
        f'<h1 style="color:{tokens["text"]};font-size:34px;'
        'font-weight:800;line-height:1.15;margin:0;">'
        'What-If Analysis</h1>'
        f'<p style="color:{tokens["text_secondary"]};font-size:14px;'
        'line-height:1.55;margin:10px auto 0 auto;max-width:640px;">'
        'Compare the current component risk profile against a simulated '
        'driving scenario using the data already loaded in the dashboard.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    control_col, result_col = st.columns([1, 1.7], gap="large")
    with control_col:
        st.markdown('<div class="what-if-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{tokens["text"]};font-size:17px;'
            'font-weight:800;margin-bottom:14px;">Scenario controls</div>',
            unsafe_allow_html=True,
        )
        driving_style = st.radio(
            "Driving style",
            list(STYLE_MULTIPLIERS),
            index=1,
            horizontal=True,
        )
        coolant_offset = st.slider(
            "Coolant temperature offset (C)",
            min_value=-10,
            max_value=20,
            value=0,
            step=1,
        )
        rpm_multiplier = st.slider(
            "RPM multiplier",
            min_value=0.8,
            max_value=1.4,
            value=1.0,
            step=0.05,
            format="%.2fx",
        )
        load_multiplier = st.slider(
            "Load / throttle stress",
            min_value=0.8,
            max_value=1.5,
            value=1.0,
            step=0.05,
            format="%.2fx",
        )
        intake_offset = st.slider(
            "Ambient / intake temperature offset (C)",
            min_value=-10,
            max_value=20,
            value=0,
            step=1,
        )
        st.markdown(
            f'<div style="color:{tokens["text_secondary"]};font-size:12px;'
            'line-height:1.45;margin-top:14px;">'
            'Controls affect all five supported anomaly types with different '
            'component sensitivities. This does not rerun Model Layer.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    inputs = ScenarioInputs(
        driving_style=driving_style,
        coolant_temp_offset=float(coolant_offset),
        rpm_multiplier=float(rpm_multiplier),
        load_stress_multiplier=float(load_multiplier),
        intake_temp_offset=float(intake_offset),
    )
    rows: list[tuple[str, float, float]] = []
    for component_key, component_data, is_placeholder in get_overview_components():
        if is_placeholder:
            continue
        baseline = float(component_data.get("risk_score", 0.0) or 0.0)
        projected = project_component_risk(component_key, baseline, inputs)
        rows.append((component_key, baseline, projected))

    with result_col:
        _render_summary_card(rows, inputs, tokens)
        body = "".join(
            _render_component_row(key, base, projected, tokens)
            for key, base, projected in rows
        )
        st.markdown(
            '<div class="what-if-card">'
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'color:{tokens["text"]};font-size:17px;font-weight:800;'
            'margin-bottom:8px;">'
            f'{lucide_icon("sliders", size=18, color=tokens["accent"])}'
            'Baseline vs Scenario</div>'
            f'{body}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    try:
        from ui_components import show_footer
    except ImportError:
        from dashboard.ui_components import show_footer

    show_footer(dark_mode)
