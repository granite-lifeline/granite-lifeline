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
    "Easy": 0.90,
    "Normal": 1.00,
    "Hard": 1.12,
}

# Short one-line description shown below the radio.
STYLE_DESCRIPTIONS = {
    "Easy":   "Light acceleration, low engine load.",
    "Normal": "Matches your current dashboard reading.",
    "Hard":   "Heavy acceleration, high RPM, sustained load.",
}

# Slider default values per driving style.
# Keys use a _pending_ prefix so we never touch live widget keys.
STYLE_SLIDER_PRESETS: dict[str, dict] = {
    "Easy":   {"wi_coolant_p": -2, "wi_rpm_p": 0.90, "wi_load_p": 0.88, "wi_intake_p": 0},
    "Normal": {"wi_coolant_p": 0,  "wi_rpm_p": 1.00, "wi_load_p": 1.00, "wi_intake_p": 0},
    "Hard":   {"wi_coolant_p": 4,  "wi_rpm_p": 1.20, "wi_load_p": 1.25, "wi_intake_p": 3},
}

# Mapping from _pending_ key → live widget key.
_PENDING_TO_WIDGET: dict[str, str] = {
    "wi_coolant_p": "wi_coolant",
    "wi_rpm_p":     "wi_rpm",
    "wi_load_p":    "wi_load",
    "wi_intake_p":  "wi_intake",
}

# One-line plain-English description per component.
COMPONENT_EXPLANATIONS = {
    "cooling_degradation":                  "Driven by heat, RPM, and heavy load.",
    "air_intake_maf_anomaly":               "Driven by RPM, load, and air temperature.",
    "accelerator_pedal_sensor":             "Driven by throttle changes and load.",
    "intake_air_temperature_sensor_fault":  "Driven by intake and ambient air temperature.",
    "map_load_signal_plausibility_fault":   "Driven by RPM and throttle load.",
}

# Uncertainty half-width added to projected scores for the range display.
# Represents the inherent imprecision of the heuristic formula.
_UNCERTAINTY_MARGIN = 0.07

# When the combined "intensity" of all slider adjustments exceeds this
# threshold, we show an extreme-scenario warning.
_EXTREME_THRESHOLD = 0.55


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

    delta = {
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

    return delta


def project_component_risk(
    component_key: str,
    baseline_score: float,
    inputs: ScenarioInputs,
) -> float:
    """Project a scenario risk score from the current dashboard baseline."""
    baseline = max(0.0, min(1.0, float(baseline_score or 0.0)))
    projected = baseline + _component_sensitivity(component_key, inputs)
    # Easy mode: never let projected exceed baseline (sliders could otherwise
    # push it up even when style_delta is negative).
    if inputs.driving_style == "Easy":
        projected = min(projected, baseline)
    return max(0.0, min(1.0, projected))


def _scenario_intensity(inputs: ScenarioInputs) -> float:
    """Return a rough 0–1 measure of how extreme the scenario is."""
    style_push = STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
    rpm_push   = max(inputs.rpm_multiplier - 1.0, 0)
    load_push  = max(inputs.load_stress_multiplier - 1.0, 0)
    temp_push  = max(inputs.coolant_temp_offset, 0) / 20.0
    intake_push = max(inputs.intake_temp_offset, 0) / 20.0
    return style_push + rpm_push + load_push + temp_push + intake_push


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
        .what-if-control-help {{
            color:{tokens["text_secondary"]};
            font-size:12px;
            line-height:1.45;
            margin:-6px 0 12px 0;
        }}
        .what-if-row {{
            align-items:center;
            border-top:1px solid {tokens["border"]};
            display:grid;
            gap:16px;
            grid-template-columns:minmax(200px,1.4fr) 130px 90px 110px;
            padding:14px 0;
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
        .what-if-name-block {{
            min-width:0;
        }}
        .what-if-component-help {{
            color:{tokens["text_secondary"]};
            font-size:11px;
            font-weight:500;
            line-height:1.4;
            margin-top:3px;
        }}
        .what-if-score {{
            color:{tokens["text"]};
            font-family:{FONT_MONO};
            font-size:18px;
            font-weight:800;
            text-align:right;
        }}
        .what-if-range {{
            color:{tokens["text_secondary"]};
            font-family:{FONT_MONO};
            font-size:11px;
            text-align:right;
            margin-top:2px;
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
            height:6px;
            overflow:hidden;
            width:100%;
        }}
        .what-if-meter > span {{
            border-radius:999px;
            display:block;
            height:6px;
        }}
        .what-if-action {{
            background:{hex_to_rgba(tokens["accent"], 0.07)};
            border-radius:8px;
            color:{tokens["text"]};
            font-size:12px;
            line-height:1.5;
            margin-top:6px;
            padding:8px 10px;
        }}
        .what-if-extreme-warn {{
            background:{hex_to_rgba(tokens["risk_medium"], 0.10)};
            border:1px solid {hex_to_rgba(tokens["risk_medium"], 0.35)};
            border-radius:10px;
            color:{tokens["risk_medium"]};
            font-size:12px;
            font-weight:600;
            line-height:1.45;
            margin-top:10px;
            padding:10px 12px;
        }}
        .st-key-what_if_back_btn button {{
            background:transparent !important;
            border:1px solid {tokens["border"]} !important;
            border-radius:10px !important;
            color:{tokens["text"]} !important;
            font-size:13px !important;
            font-weight:700 !important;
        }}
        .st-key-what_if_back_btn button * {{
            color:inherit !important;
        }}
        .st-key-what_if_back_btn button:hover {{
            border-color:{tokens["accent"]} !important;
            color:{tokens["accent"]} !important;
        }}
        .st-key-what_if_back_btn button:hover * {{
            color:{tokens["accent"]} !important;
        }}
        .st-key-what_if_reset_btn button {{
            background:transparent !important;
            border:1px solid {tokens["border"]} !important;
            border-radius:10px !important;
            color:{tokens["text_secondary"]} !important;
            font-size:12px !important;
        }}
        .st-key-what_if_reset_btn button:hover {{
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
            .what-if-range {{
                text-align:left;
            }}
        }}
        @media (max-width: 540px) {{
            .what-if-row {{
                grid-template-columns:1fr;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_cell(
    label: str,
    value: str,
    subtext: str = "",
    color: str | None = None,
) -> str:
    score_style = f"color:{color};" if color else ""
    sub_html = (
        f'<div class="what-if-range">{html.escape(subtext)}</div>'
        if subtext else ""
    )
    return (
        '<div>'
        f'<div class="what-if-label">{html.escape(label)}</div>'
        f'<div class="what-if-score" style="{score_style}">{html.escape(value)}</div>'
        f'{sub_html}'
        '</div>'
    )


def _render_component_row(
    component_key: str,
    baseline: float,
    projected: float,
    component_data: dict,
    tokens: dict,
) -> str:
    baseline_pct = int(round(baseline * 100))
    projected_pct = int(round(projected * 100))
    delta_pct = projected_pct - baseline_pct
    level = _risk_level(projected)
    level_color = _risk_color(level, tokens)
    delta_prefix = "+" if delta_pct > 0 else ""
    delta_color = (
        tokens["risk_high"] if delta_pct > 0
        else tokens["risk_low"] if delta_pct < 0
        else tokens["text_secondary"]
    )

    # Range: projected ± uncertainty, clamped to [0, 100]
    lo = max(0, int(round((projected - _UNCERTAINTY_MARGIN) * 100)))
    hi = min(100, int(round((projected + _UNCERTAINTY_MARGIN) * 100)))
    range_str = f"{lo}–{hi}%"

    icon = lucide_icon(
        COMPONENT_ICONS.get(component_key, "activity"),
        size=18,
        color=level_color,
    )

    # Recommended action (first item only) for High/Medium components
    action_html = ""
    if level in ("High", "Medium"):
        actions = component_data.get("recommended_action") or []
        if actions:
            action_html = (
                f'<div class="what-if-action">'
                f'💡 {html.escape(str(actions[0]))}'
                '</div>'
            )

    return (
        '<div class="what-if-row">'
        '<div class="what-if-name">'
        f'{icon}<div class="what-if-name-block">'
        f'<div>{html.escape(COMPONENT_DISPLAY_NAMES.get(component_key, component_key))}</div>'
        '<div class="what-if-component-help">'
        f'{html.escape(COMPONENT_EXPLANATIONS.get(component_key, "Risk based on current reading."))}'
        '</div>'
        f'{action_html}'
        '</div></div>'
        f'{_metric_cell("Now", f"{baseline_pct}%")}'
        f'{_metric_cell("What-if", f"{projected_pct}%", subtext=f"range {range_str}", color=delta_color)}'
        '<div>'
        f'<span class="what-if-pill" style="background:{level_color};">'
        f'{html.escape(level)}</span>'
        '<div class="what-if-meter" style="margin-top:8px;">'
        f'<span style="background:{level_color};width:{projected_pct}%;"></span>'
        '</div></div></div>'
    )


def _render_summary_card(
    rows: list[tuple[str, float, float]],
    inputs: ScenarioInputs,
    tokens: dict,
) -> None:
    if not rows:
        return

    avg_baseline = sum(r[1] for r in rows) / len(rows)
    avg_projected = sum(r[2] for r in rows) / len(rows)
    avg_baseline_pct = int(round(avg_baseline * 100))
    avg_projected_pct = int(round(avg_projected * 100))
    delta = avg_projected_pct - avg_baseline_pct

    if delta > 0:
        verdict = f"Overall risk goes up from {avg_baseline_pct}% → {avg_projected_pct}%."
        verdict_color = tokens["risk_high"]
    elif delta < 0:
        verdict = f"Overall risk drops from {avg_baseline_pct}% → {avg_projected_pct}%."
        verdict_color = tokens["risk_low"]
    else:
        verdict = f"Overall risk stays at {avg_baseline_pct}%."
        verdict_color = tokens["text_secondary"]

    # Extreme scenario warning
    intensity = _scenario_intensity(inputs)
    extreme_html = ""
    if intensity >= _EXTREME_THRESHOLD:
        extreme_html = (
            '<div class="what-if-extreme-warn">'
            "⚠️ This is a very extreme scenario. Real-world risk changes are "
            "likely smaller than shown — the numbers are estimates, not predictions."
            "</div>"
        )

    st.markdown(
        '<div class="what-if-card" style="margin-bottom:18px;">'
        f'<div style="color:{tokens["text_secondary"]};font-size:11px;'
        'font-weight:700;letter-spacing:0.4px;text-transform:uppercase;'
        'margin-bottom:8px;">Summary</div>'
        f'<div style="color:{verdict_color};font-size:22px;font-weight:800;'
        f'line-height:1.2;">{html.escape(verdict)}</div>'
        f'<div style="color:{tokens["text_secondary"]};font-size:12px;'
        'margin-top:6px;">'
        'Each "What-if" number shows a range — the actual outcome could land '
        'anywhere inside it. Estimate only, not a new diagnostic scan.'
        '</div>'
        f'{extreme_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def _flush_pending_presets() -> None:
    """Copy any pending preset values into live widget keys before widgets render.

    Streamlit raises StreamlitAPIException if you write to a widget's
    session_state key *after* the widget has been instantiated in the same
    run.  The fix: store the desired values under *pending* keys in one run,
    then read them here at the top of the *next* run — before the widgets are
    created — and promote them to the live keys.
    """
    for pending_key, widget_key in _PENDING_TO_WIDGET.items():
        if pending_key in st.session_state:
            st.session_state[widget_key] = st.session_state.pop(pending_key)


def _apply_preset(style: str) -> None:
    """Store preset values as pending keys and rerun."""
    for pending_key, value in STYLE_SLIDER_PRESETS[style].items():
        st.session_state[pending_key] = value
    st.rerun()


def show_what_if_page() -> None:
    """Render the What-If Analysis page."""
    # Must run before any widget is instantiated.
    _flush_pending_presets()

    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]
    _render_page_styles(tokens)

    st.markdown('<div class="what-if-shell">', unsafe_allow_html=True)

    # ── Top navigation bar ──────────────────────────────────────────────────
    nav_left, _spacer = st.columns([3, 7])
    with nav_left:
        if st.button(
            "← Back to Dashboard",
            key="what_if_back_btn",
            help="Return to the dashboard overview",
        ):
            st.session_state["page"] = "overview"
            st.rerun()

    # ── Page heading ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin:12px 0 20px 0;text-align:center;">'
        f'<h1 style="color:{tokens["text"]};font-size:28px;'
        'font-weight:800;line-height:1.2;margin:0;">'
        'What if I drive differently?</h1>'
        f'<p style="color:{tokens["text_secondary"]};font-size:13px;'
        'margin:6px auto 0 auto;max-width:520px;">'
        'Adjust the scenario below to see how your vehicle risks might change.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    control_col, result_col = st.columns([1, 1.7], gap="large")

    # ── Controls ────────────────────────────────────────────────────────────
    with control_col:
        st.markdown('<div class="what-if-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{tokens["text"]};font-size:15px;'
            'font-weight:800;margin-bottom:12px;">Driving scenario</div>',
            unsafe_allow_html=True,
        )

        driving_style = st.radio(
            "Driving style",
            list(STYLE_MULTIPLIERS),
            index=list(STYLE_MULTIPLIERS).index(
                st.session_state.get("wi_style", "Normal")
            ),
            horizontal=True,
            label_visibility="hidden",
        )
        st.session_state["wi_style"] = driving_style
        st.markdown(
            f'<div class="what-if-control-help">'
            f'{html.escape(STYLE_DESCRIPTIONS[driving_style])}</div>',
            unsafe_allow_html=True,
        )

        coolant_offset = st.slider(
            "Engine temperature (°C change)",
            min_value=-10,
            max_value=20,
            value=st.session_state.get("wi_coolant", 0),
            step=1,
            key="wi_coolant",
            help="How much hotter or cooler the engine runs vs. now.",
        )
        rpm_multiplier = st.slider(
            "Engine speed",
            min_value=0.8,
            max_value=1.4,
            value=st.session_state.get("wi_rpm", 1.0),
            step=0.05,
            format="%.2fx",
            key="wi_rpm",
            help="1.20× = 20% more time at high RPM than now.",
        )
        load_multiplier = st.slider(
            "Acceleration & load",
            min_value=0.8,
            max_value=1.5,
            value=st.session_state.get("wi_load", 1.0),
            step=0.05,
            format="%.2fx",
            key="wi_load",
            help="Higher = harder acceleration, towing, or hill climbing.",
        )
        intake_offset = st.slider(
            "Outside air temperature (°C change)",
            min_value=-10,
            max_value=20,
            value=st.session_state.get("wi_intake", 0),
            step=1,
            key="wi_intake",
            help="Positive = hotter ambient air (hot weather, stop-and-go traffic).",
        )

        preset_col, reset_col = st.columns(2)
        with preset_col:
            if st.button(
                f"Apply {driving_style} preset",
                key="what_if_preset_btn",
                use_container_width=True,
                help="Set all sliders to typical values for this driving style.",
            ):
                _apply_preset(driving_style)
        with reset_col:
            if st.button(
                "↺ Reset",
                key="what_if_reset_btn",
                use_container_width=True,
                help="Reset all sliders to Normal defaults.",
            ):
                for k in ("wi_coolant", "wi_rpm", "wi_load", "wi_intake",
                          "wi_style",
                          "wi_coolant_p", "wi_rpm_p", "wi_load_p", "wi_intake_p"):
                    st.session_state.pop(k, None)
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Compute projections ─────────────────────────────────────────────────
    inputs = ScenarioInputs(
        driving_style=driving_style,
        coolant_temp_offset=float(coolant_offset),
        rpm_multiplier=float(rpm_multiplier),
        load_stress_multiplier=float(load_multiplier),
        intake_temp_offset=float(intake_offset),
    )

    # Collect real component rows, keeping component_data for recommended_action.
    rows: list[tuple[str, float, float, dict]] = []
    for component_key, component_data, is_placeholder in get_overview_components():
        if is_placeholder:
            continue
        baseline = float(component_data.get("risk_score", 0.0) or 0.0)
        projected = project_component_risk(component_key, baseline, inputs)
        rows.append((component_key, baseline, projected, component_data))

    # ── Results ─────────────────────────────────────────────────────────────
    with result_col:
        if not rows:
            st.info(
                "No component data available yet. "
                "Upload a CSV on the main dashboard to get started."
            )
        else:
            _render_summary_card(
                [(key, base, proj) for key, base, proj, _ in rows],
                inputs,
                tokens,
            )
            body = "".join(
                _render_component_row(key, base, proj, cdata, tokens)
                for key, base, proj, cdata in rows
            )
            st.markdown(
                '<div class="what-if-card">'
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'color:{tokens["text"]};font-size:15px;font-weight:800;'
                'margin-bottom:6px;">'
                f'{lucide_icon("sliders", size=16, color=tokens["accent"])}'
                'Component breakdown</div>'
                f'<div style="color:{tokens["text_secondary"]};font-size:12px;'
                'margin-bottom:10px;">'
                '"Now" = current reading · "What-if" = estimated · '
                '"Range" = realistic spread'
                '</div>'
                f'{body}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)
    try:
        from ui_components import show_footer
    except ImportError:
        from dashboard.ui_components import show_footer

    show_footer(dark_mode)
