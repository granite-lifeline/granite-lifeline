"""What-If analysis page for dashboard-side scenario comparison."""

from __future__ import annotations

import html
import importlib
from dataclasses import dataclass
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Driving style — radio options & slider presets
# ---------------------------------------------------------------------------

STYLE_MULTIPLIERS = {
    "Easy": 0.90,
    "Normal": 1.00,
    "Hard": 1.12,
}

STYLE_DESCRIPTIONS = {
    "Easy":   "Light acceleration, low engine load.",
    "Normal": "Matches your current dashboard reading.",
    "Hard":   "Heavy acceleration, high RPM, sustained load.",
}

# Pending-key presets (never write directly to live widget keys mid-run).
STYLE_SLIDER_PRESETS: dict[str, dict] = {
    "Easy":   {"wi_coolant_p": -2, "wi_rpm_p": 0.90, "wi_load_p": 0.88, "wi_intake_p": 0},
    "Normal": {"wi_coolant_p": 0,  "wi_rpm_p": 1.00, "wi_load_p": 1.00, "wi_intake_p": 0},
    "Hard":   {"wi_coolant_p": 4,  "wi_rpm_p": 1.20, "wi_load_p": 1.25, "wi_intake_p": 3},
}

_PENDING_TO_WIDGET: dict[str, str] = {
    "wi_coolant_p": "wi_coolant",
    "wi_rpm_p":     "wi_rpm",
    "wi_load_p":    "wi_load",
    "wi_intake_p":  "wi_intake",
}


# ---------------------------------------------------------------------------
# Scenario cards
# Slider values are calibrated from KIT OBD-II dataset operating-condition
# statistics (operating_condition_signal_summary.csv):
#   Normal baseline medians (post_warmup, steady_driving):
#     coolant_temp ≈ 90 °C, rpm ≈ 1675, maf ≈ 20.8 g/s, intake_temp ≈ 18.5 °C
#   RPM multiplier  = scenario_rpm_median / 1675
#   Load multiplier = scenario_maf_median / 20.8  (capped at 1.50 for slider range)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioCard:
    key: str
    label: str
    description: str       # One plain-English sentence shown on the card
    icon: str              # Lucide icon name
    driving_style: str     # "Easy" | "Normal" | "Hard"
    coolant_offset: int    # °C relative to normal
    rpm_multiplier: float  # relative to steady-driving median 1675 RPM
    load_multiplier: float # relative to steady-driving median MAF 20.8 g/s
    intake_offset: int     # °C relative to normal


# Ordered Hard → Easy (per user preference).
SCENARIO_CARDS: list[ScenarioCard] = [
    ScenarioCard(
        key="hard_acceleration",
        label="Hard Acceleration",
        description="Fast driving with frequent heavy acceleration.",
        icon="zap",
        driving_style="Hard",
        # high_load: rpm median 2065 → 2065/1675 = 1.23; maf median 46.4 → 46.4/20.8 = 2.23 → cap 1.50
        coolant_offset=4,
        rpm_multiplier=1.23,
        load_multiplier=1.50,
        intake_offset=2,
    ),
    ScenarioCard(
        key="hills_towing",
        label="Hills or Heavy Load",
        description="Climbing a slope, towing, or carrying extra weight.",
        icon="gauge",
        driving_style="Hard",
        # high_load sustained: same operating state, slightly lower RPM than hard accel
        coolant_offset=6,
        rpm_multiplier=1.23,
        load_multiplier=1.40,
        intake_offset=3,
    ),
    ScenarioCard(
        key="hot_day_highway",
        label="Hot Day Highway",
        description="Long motorway cruise on a hot day.",
        icon="thermometer",
        driving_style="Normal",
        # steady_driving: rpm ≈ baseline; intake_temp P95 ≈ 36 °C → offset +18 °C capped at +10
        coolant_offset=5,
        rpm_multiplier=1.05,
        load_multiplier=0.95,
        intake_offset=10,
    ),
    ScenarioCard(
        key="city_traffic",
        label="Stuck in Traffic",
        description="Stop-and-go city driving with the engine idling a lot.",
        icon="activity",
        driving_style="Normal",
        # idle: rpm median 832 → 832/1675 = 0.50; maf median 8.4 → 8.4/20.8 = 0.40 → use 0.80 for mixed
        # high coolant offset because no airflow cooling while stationary
        coolant_offset=10,
        rpm_multiplier=0.75,
        load_multiplier=0.80,
        intake_offset=5,
    ),
    ScenarioCard(
        key="easy_commute",
        label="Easy Commute",
        description="Short, relaxed drive in cool weather.",
        icon="wind",
        driving_style="Easy",
        # below steady_driving baseline
        coolant_offset=-3,
        rpm_multiplier=0.54,
        load_multiplier=0.85,
        intake_offset=-5,
    ),
]

# Per-scenario, per-component plain-English reason why risk changes.
# Format: SCENARIO_COMPONENT_REASONS[scenario_key][component_key]
SCENARIO_COMPONENT_REASONS: dict[str, dict[str, str]] = {
    "hard_acceleration": {
        "cooling_degradation":
            "Hard acceleration keeps the engine running hot for longer.",
        "air_intake_maf_anomaly":
            "Heavy throttle stresses the airflow sensor more.",
        "accelerator_pedal_sensor":
            "Rapid pedal movements put more strain on the pedal sensor.",
        "intake_air_temperature_sensor_fault":
            "Engine heat can warm the intake air slightly.",
        "map_load_signal_plausibility_fault":
            "High load makes the pressure sensor work harder to stay accurate.",
    },
    "hills_towing": {
        "cooling_degradation":
            "Sustained climbing or towing generates a lot of engine heat.",
        "air_intake_maf_anomaly":
            "The engine needs more air under heavy load — the sensor reads harder.",
        "accelerator_pedal_sensor":
            "Sustained heavy pedal pressure stresses the sensor over time.",
        "intake_air_temperature_sensor_fault":
            "Engine bay heat soaks into the intake air during hard work.",
        "map_load_signal_plausibility_fault":
            "High and sustained load makes pressure readings more likely to drift.",
    },
    "hot_day_highway": {
        "cooling_degradation":
            "Hot outside air gives the cooling system less room to shed heat.",
        "air_intake_maf_anomaly":
            "Hot dense air affects how accurately the sensor reads airflow.",
        "accelerator_pedal_sensor":
            "Steady cruise keeps pedal stress low — small change expected.",
        "intake_air_temperature_sensor_fault":
            "This is the most affected part — the sensor reads much hotter air.",
        "map_load_signal_plausibility_fault":
            "Steady highway load is predictable, so risk change is small.",
    },
    "city_traffic": {
        "cooling_degradation":
            "Idling in traffic means no airflow over the radiator — heat builds up.",
        "air_intake_maf_anomaly":
            "Frequent stop-start causes irregular airflow that is harder to read.",
        "accelerator_pedal_sensor":
            "Lots of small pedal movements in traffic add up over time.",
        "intake_air_temperature_sensor_fault":
            "Hot road-level air and engine heat raise intake temperature significantly.",
        "map_load_signal_plausibility_fault":
            "Frequent engine load changes make the pressure sensor work inconsistently.",
    },
    "easy_commute": {
        "cooling_degradation":
            "Cool weather and light driving keep the engine well within safe limits.",
        "air_intake_maf_anomaly":
            "Low load means steady, easy airflow — the sensor is under little stress.",
        "accelerator_pedal_sensor":
            "Gentle pedal use puts almost no strain on the sensor.",
        "intake_air_temperature_sensor_fault":
            "Cool air entering the engine keeps this sensor reading stable.",
        "map_load_signal_plausibility_fault":
            "Low and steady engine load means the pressure signal stays predictable.",
    },
}


# ---------------------------------------------------------------------------
# Component explanations (generic, shown when no scenario is active)
# ---------------------------------------------------------------------------

COMPONENT_EXPLANATIONS = {
    "cooling_degradation":
        "Driven by engine heat, how hard the engine works, and outside temperature.",
    "air_intake_maf_anomaly":
        "Driven by how much air the engine pulls in and how hard it works.",
    "accelerator_pedal_sensor":
        "Driven by how often and how hard the pedal is pressed.",
    "intake_air_temperature_sensor_fault":
        "Driven by intake air temperature and ambient conditions.",
    "map_load_signal_plausibility_fault":
        "Driven by engine load and how much the load varies.",
}


# ---------------------------------------------------------------------------
# Uncertainty & extreme-scenario thresholds
# ---------------------------------------------------------------------------

# ±7% range shown under each What-if number (heuristic imprecision).
_UNCERTAINTY_MARGIN = 0.07

# Intensity score above which an extreme-scenario warning is shown.
_EXTREME_THRESHOLD = 0.55


# ---------------------------------------------------------------------------
# ScenarioInputs dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioInputs:
    """Dashboard-side what-if controls."""
    driving_style: str
    coolant_temp_offset: float
    rpm_multiplier: float
    load_stress_multiplier: float
    intake_temp_offset: float


# ---------------------------------------------------------------------------
# Surrogate model interface
# Trained models live at dashboard/model_artifacts/surrogate_{component}.pkl
# If a pkl file is absent the heuristic formula is used instead (graceful fallback).
# Training pipeline: once the main model (TTM + kit_residual_detector) can produce
# stable risk_score outputs for segmented KIT driving data, fit one Ridge regressor
# per component on (coolant_offset, rpm_ratio, load_ratio, intake_offset) → risk_delta
# and serialise with joblib.dump().
# ---------------------------------------------------------------------------

_SURROGATE_CACHE: dict[str, object] = {}
_ARTIFACT_DIR = Path(__file__).parent.parent / "model_artifacts"


def _surrogate_predict(component_key: str, inputs: ScenarioInputs) -> float | None:
    """Return surrogate-predicted risk delta, or None if model unavailable."""
    try:
        joblib = importlib.import_module("joblib")
    except ImportError:
        return None

    pkl_path = _ARTIFACT_DIR / f"surrogate_{component_key}.pkl"
    if not pkl_path.exists():
        return None

    if component_key not in _SURROGATE_CACHE:
        try:
            _SURROGATE_CACHE[component_key] = joblib.load(pkl_path)
        except Exception:
            return None

    model = _SURROGATE_CACHE.get(component_key)
    if model is None:
        return None

    try:
        X = [[
            inputs.coolant_temp_offset,
            inputs.rpm_multiplier,
            inputs.load_stress_multiplier,
            inputs.intake_temp_offset,
        ]]
        return float(model.predict(X)[0])
    except Exception:
        return None


def _heuristic_sensitivity(component_key: str, inputs: ScenarioInputs) -> float:
    """
    Hand-calibrated heuristic risk delta.

    Coefficients are grounded in KIT OBD-II dataset operating-condition statistics
    (data_layer/operating_condition_statistics/operating_condition_signal_summary.csv)
    and Bosch Automotive Handbook physical relationships.  They represent the best
    available estimate until a surrogate model is trained on real risk_score labels.
    """
    style_delta = STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
    rpm_delta   = inputs.rpm_multiplier - 1.0
    load_delta  = inputs.load_stress_multiplier - 1.0

    return {
        # Cooling: heat, RPM and load all raise engine temperature.
        # coolant coefficient 0.010 per °C ≈ SAE J1979 & Seat Leon Zone B/C boundary.
        "cooling_degradation": (
            0.35 * style_delta
            + 0.010 * inputs.coolant_temp_offset
            + 0.18 * max(rpm_delta, 0)
            + 0.10 * max(load_delta, 0)
            + 0.003 * max(inputs.intake_temp_offset, 0)
        ),
        # MAF sensor: RPM and load drive air-mass demand; intake temp affects density.
        "air_intake_maf_anomaly": (
            0.28 * style_delta
            + 0.20 * max(rpm_delta, 0)
            + 0.24 * max(load_delta, 0)
            + 0.002 * abs(inputs.intake_temp_offset)
        ),
        # Pedal sensor: load (throttle demand) is the primary stressor.
        "accelerator_pedal_sensor": (
            0.20 * style_delta
            + 0.24 * max(load_delta, 0)
            + 0.08 * max(rpm_delta, 0)
        ),
        # IAT sensor: intake and ambient temperature are the direct physical drivers.
        "intake_air_temperature_sensor_fault": (
            0.12 * style_delta
            + 0.012 * inputs.intake_temp_offset
            + 0.004 * inputs.coolant_temp_offset
        ),
        # MAP sensor: load and RPM variation cause plausibility failures.
        "map_load_signal_plausibility_fault": (
            0.24 * style_delta
            + 0.22 * max(rpm_delta, 0)
            + 0.22 * max(load_delta, 0)
        ),
    }.get(component_key, 0.10 * style_delta)


def _component_sensitivity(component_key: str, inputs: ScenarioInputs) -> float:
    """Return risk delta: surrogate if available, heuristic otherwise."""
    surrogate = _surrogate_predict(component_key, inputs)
    if surrogate is not None:
        return surrogate
    return _heuristic_sensitivity(component_key, inputs)


# ---------------------------------------------------------------------------
# Risk helpers
# ---------------------------------------------------------------------------

def _risk_level(score: float) -> str:
    if score >= 0.70:
        return "High"
    if score >= 0.30:
        return "Medium"
    return "Low"


def _risk_color(level: str, tokens: dict) -> str:
    return {
        "High":   tokens["risk_high"],
        "Medium": tokens["risk_medium"],
        "Low":    tokens["risk_low"],
    }.get(level, tokens["text_secondary"])


def project_component_risk(
    component_key: str,
    baseline_score: float,
    inputs: ScenarioInputs,
) -> float:
    """Project scenario risk from the current dashboard baseline."""
    baseline  = max(0.0, min(1.0, float(baseline_score or 0.0)))
    projected = baseline + _component_sensitivity(component_key, inputs)
    if inputs.driving_style == "Easy":
        projected = min(projected, baseline)
    return max(0.0, min(1.0, projected))


def _scenario_intensity(inputs: ScenarioInputs) -> float:
    style_push  = STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
    rpm_push    = max(inputs.rpm_multiplier - 1.0, 0)
    load_push   = max(inputs.load_stress_multiplier - 1.0, 0)
    temp_push   = max(inputs.coolant_temp_offset, 0) / 20.0
    intake_push = max(inputs.intake_temp_offset, 0) / 20.0
    return style_push + rpm_push + load_push + temp_push + intake_push


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

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
        /* ── Scenario cards ── */
        .wi-scenarios {{
            display:grid;
            gap:10px;
            grid-template-columns:repeat(5, 1fr);
            margin-bottom:20px;
        }}
        .wi-scenario-card {{
            background:{tokens["glass_surface"]};
            border:2px solid {tokens["glass_border"]};
            border-radius:14px;
            cursor:pointer;
            padding:14px 10px 12px 10px;
            text-align:center;
            transition:border-color 0.15s, background 0.15s;
        }}
        .wi-scenario-card.active {{
            border-color:{tokens["accent"]};
            background:{hex_to_rgba(tokens["accent"], 0.07)};
        }}
        .wi-scenario-icon {{
            display:flex;
            justify-content:center;
            margin-bottom:6px;
        }}
        .wi-scenario-label {{
            color:{tokens["text"]};
            font-size:12px;
            font-weight:700;
            line-height:1.3;
        }}
        .wi-scenario-desc {{
            color:{tokens["text_secondary"]};
            font-size:11px;
            line-height:1.4;
            margin-top:4px;
        }}
        /* ── Component filter pills ── */
        .wi-filter-bar {{
            display:flex;
            flex-wrap:wrap;
            gap:6px;
            margin-bottom:14px;
        }}
        .wi-filter-pill {{
            border-radius:999px;
            border:1.5px solid {tokens["border"]};
            color:{tokens["text_secondary"]};
            cursor:pointer;
            font-size:12px;
            font-weight:600;
            padding:4px 12px;
            white-space:nowrap;
            background:transparent;
        }}
        .wi-filter-pill.active {{
            border-color:{tokens["accent"]};
            color:{tokens["accent"]};
            background:{hex_to_rgba(tokens["accent"], 0.07)};
        }}
        /* ── Controls ── */
        .what-if-control-help {{
            color:{tokens["text_secondary"]};
            font-size:12px;
            line-height:1.45;
            margin:-6px 0 12px 0;
        }}
        /* ── Result rows ── */
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
        .what-if-row.highlighted {{
            background:{hex_to_rgba(tokens["accent"], 0.05)};
            border-radius:10px;
            margin:0 -8px;
            padding:14px 8px;
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
        .what-if-name-block {{ min-width:0; }}
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
        /* ── Buttons ── */
        .st-key-what_if_back_btn button {{
            background:transparent !important;
            border:1px solid {tokens["border"]} !important;
            border-radius:10px !important;
            color:{tokens["text"]} !important;
            font-size:13px !important;
            font-weight:700 !important;
        }}
        .st-key-what_if_back_btn button * {{ color:inherit !important; }}
        .st-key-what_if_back_btn button:hover {{
            border-color:{tokens["accent"]} !important;
            color:{tokens["accent"]} !important;
        }}
        .st-key-what_if_back_btn button:hover * {{ color:{tokens["accent"]} !important; }}
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
        @media (max-width: 900px) {{
            .wi-scenarios {{ grid-template-columns:repeat(3,1fr); }}
        }}
        @media (max-width: 760px) {{
            .wi-scenarios {{ grid-template-columns:repeat(2,1fr); }}
            .what-if-row {{ grid-template-columns:1fr 1fr; }}
            .what-if-name {{ grid-column:1 / -1; }}
            .what-if-score {{ text-align:left; }}
            .what-if-range {{ text-align:left; }}
        }}
        @media (max-width: 540px) {{
            .wi-scenarios {{ grid-template-columns:1fr 1fr; }}
            .what-if-row {{ grid-template-columns:1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

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
    scenario_key: str | None = None,
    highlighted: bool = False,
) -> str:
    baseline_pct  = int(round(baseline * 100))
    projected_pct = int(round(projected * 100))
    delta_pct     = projected_pct - baseline_pct
    level         = _risk_level(projected)
    level_color   = _risk_color(level, tokens)
    delta_color   = (
        tokens["risk_high"]    if delta_pct > 0
        else tokens["risk_low"] if delta_pct < 0
        else tokens["text_secondary"]
    )
    lo       = max(0,   int(round((projected - _UNCERTAINTY_MARGIN) * 100)))
    hi       = min(100, int(round((projected + _UNCERTAINTY_MARGIN) * 100)))
    range_str = f"{lo}–{hi}%"

    icon = lucide_icon(
        COMPONENT_ICONS.get(component_key, "activity"),
        size=18,
        color=level_color,
    )

    # Component sub-label: scenario-specific reason if a scenario is active,
    # otherwise the generic explanation.
    if scenario_key and scenario_key in SCENARIO_COMPONENT_REASONS:
        sub_label = SCENARIO_COMPONENT_REASONS[scenario_key].get(
            component_key,
            COMPONENT_EXPLANATIONS.get(component_key, "Risk based on current reading."),
        )
    else:
        sub_label = COMPONENT_EXPLANATIONS.get(component_key, "Risk based on current reading.")

    # Recommended action for High/Medium components.
    action_html = ""
    if level in ("High", "Medium"):
        actions = component_data.get("recommended_action") or []
        if actions:
            action_html = (
                f'<div class="what-if-action">'
                f'💡 {html.escape(str(actions[0]))}'
                '</div>'
            )

    row_class = "what-if-row highlighted" if highlighted else "what-if-row"

    return (
        f'<div class="{row_class}">'
        '<div class="what-if-name">'
        f'{icon}<div class="what-if-name-block">'
        f'<div>{html.escape(COMPONENT_DISPLAY_NAMES.get(component_key, component_key))}</div>'
        f'<div class="what-if-component-help">{html.escape(sub_label)}</div>'
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

    avg_baseline     = sum(r[1] for r in rows) / len(rows)
    avg_projected    = sum(r[2] for r in rows) / len(rows)
    avg_baseline_pct = int(round(avg_baseline * 100))
    avg_proj_pct     = int(round(avg_projected * 100))
    delta            = avg_proj_pct - avg_baseline_pct

    if delta > 0:
        verdict       = f"Overall risk goes up from {avg_baseline_pct}% → {avg_proj_pct}%."
        verdict_color = tokens["risk_high"]
    elif delta < 0:
        verdict       = f"Overall risk drops from {avg_baseline_pct}% → {avg_proj_pct}%."
        verdict_color = tokens["risk_low"]
    else:
        verdict       = f"Overall risk stays at {avg_baseline_pct}%."
        verdict_color = tokens["text_secondary"]

    intensity    = _scenario_intensity(inputs)
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
        f'<div style="color:{tokens["text_secondary"]};font-size:12px;margin-top:6px;">'
        'Each "What-if" number shows a range — the actual outcome could land '
        'anywhere inside it. Estimate only, not a new diagnostic scan.'
        '</div>'
        f'{extreme_html}'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Scenario card HTML (pure HTML — no Streamlit widgets, no interactivity needed;
# the actual selection is driven by Streamlit buttons rendered below)
# ---------------------------------------------------------------------------

def _render_scenario_cards(
    active_key: str | None,
    tokens: dict,
) -> None:
    """Render scenario card grid (visual only — selection via st.buttons below)."""
    cards_html = '<div class="wi-scenarios">'
    for sc in SCENARIO_CARDS:
        active_cls = " active" if sc.key == active_key else ""
        icon_svg   = lucide_icon(
            sc.icon,
            size=22,
            color=tokens["accent"] if sc.key == active_key else tokens["text_secondary"],
        )
        cards_html += (
            f'<div class="wi-scenario-card{active_cls}">'
            f'<div class="wi-scenario-icon">{icon_svg}</div>'
            f'<div class="wi-scenario-label">{html.escape(sc.label)}</div>'
            f'<div class="wi-scenario-desc">{html.escape(sc.description)}</div>'
            '</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pending-preset helpers
# ---------------------------------------------------------------------------

def _flush_pending_presets() -> None:
    """Promote pending preset keys to live widget keys before widgets render."""
    for pending_key, widget_key in _PENDING_TO_WIDGET.items():
        if pending_key in st.session_state:
            st.session_state[widget_key] = st.session_state.pop(pending_key)


def _apply_scenario(sc: ScenarioCard) -> None:
    """Store a scenario card's values as pending keys and rerun."""
    st.session_state["wi_scenario"] = sc.key
    st.session_state["wi_style"]    = sc.driving_style
    st.session_state["wi_coolant_p"] = sc.coolant_offset
    st.session_state["wi_rpm_p"]     = sc.rpm_multiplier
    st.session_state["wi_load_p"]    = sc.load_multiplier
    st.session_state["wi_intake_p"]  = sc.intake_offset
    st.rerun()


def _apply_style_preset(style: str) -> None:
    """Store style preset values as pending keys and rerun."""
    st.session_state["wi_scenario"] = None
    for pending_key, value in STYLE_SLIDER_PRESETS[style].items():
        st.session_state[pending_key] = value
    st.rerun()


def _reset_all() -> None:
    for k in (
        "wi_coolant", "wi_rpm", "wi_load", "wi_intake",
        "wi_style", "wi_scenario", "wi_filter",
        "wi_coolant_p", "wi_rpm_p", "wi_load_p", "wi_intake_p",
    ):
        st.session_state.pop(k, None)
    st.rerun()


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def show_what_if_page() -> None:
    """Render the What-If Analysis page."""
    # Must run before any widget is instantiated.
    _flush_pending_presets()

    dark_mode = st.session_state.get("dark_mode", False)
    tokens    = THEME_TOKENS["dark" if dark_mode else "light"]
    _render_page_styles(tokens)

    # Active scenario / filter state.
    active_scenario: str | None = st.session_state.get("wi_scenario")
    active_filter:   str | None = st.session_state.get("wi_filter")

    st.markdown('<div class="what-if-shell">', unsafe_allow_html=True)

    # ── Nav ────────────────────────────────────────────────────────────────
    nav_left, _spacer = st.columns([3, 7])
    with nav_left:
        if st.button(
            "← Back to Dashboard",
            key="what_if_back_btn",
            help="Return to the dashboard overview",
        ):
            st.session_state["page"] = "overview"
            st.rerun()

    # ── Heading ─────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin:12px 0 20px 0;text-align:center;">'
        f'<h1 style="color:{tokens["text"]};font-size:28px;'
        'font-weight:800;line-height:1.2;margin:0;">'
        'What if I drive differently?</h1>'
        f'<p style="color:{tokens["text_secondary"]};font-size:13px;'
        'margin:6px auto 0 auto;max-width:520px;">'
        'Pick a scenario or adjust the sliders to see how your vehicle risks might change.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    # ── Scenario cards (visual) ─────────────────────────────────────────────
    _render_scenario_cards(active_scenario, tokens)

    # Scenario selection buttons (invisible — same grid order as cards above).
    # Using st.columns to align buttons under each visual card.
    btn_cols = st.columns(len(SCENARIO_CARDS), gap="small")
    for i, sc in enumerate(SCENARIO_CARDS):
        with btn_cols[i]:
            label = "✓ Selected" if sc.key == active_scenario else "Select"
            if st.button(label, key=f"wi_sc_{sc.key}", use_container_width=True):
                _apply_scenario(sc)

    st.markdown(
        f'<div style="height:4px;border-bottom:1px solid {tokens["border"]};'
        'margin:16px 0 20px 0;"></div>',
        unsafe_allow_html=True,
    )

    control_col, result_col = st.columns([1, 1.7], gap="large")

    # ── Controls ────────────────────────────────────────────────────────────
    with control_col:
        st.markdown('<div class="what-if-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{tokens["text"]};font-size:15px;'
            'font-weight:800;margin-bottom:12px;">Fine-tune</div>',
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
            min_value=-10, max_value=20,
            value=st.session_state.get("wi_coolant", 0),
            step=1,
            key="wi_coolant",
            help="How much hotter or cooler the engine runs vs. now.",
        )
        rpm_multiplier = st.slider(
            "Engine speed",
            min_value=0.8, max_value=1.4,
            value=st.session_state.get("wi_rpm", 1.0),
            step=0.05,
            format="%.2fx",
            key="wi_rpm",
            help="How much faster or slower the engine runs on average. "
                 "1.20× means 20% faster than your current reading.",
        )
        load_multiplier = st.slider(
            "Acceleration & load",
            min_value=0.8, max_value=1.5,
            value=st.session_state.get("wi_load", 1.0),
            step=0.05,
            format="%.2fx",
            key="wi_load",
            help="How hard the engine works. Higher = more hill climbing, "
                 "towing, or heavy acceleration.",
        )
        intake_offset = st.slider(
            "Outside air temperature (°C change)",
            min_value=-10, max_value=20,
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
                help="Set sliders to typical values for this driving style.",
            ):
                _apply_style_preset(driving_style)
        with reset_col:
            if st.button(
                "↺ Reset",
                key="what_if_reset_btn",
                use_container_width=True,
                help="Reset everything to Normal defaults.",
            ):
                _reset_all()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Compute projections ─────────────────────────────────────────────────
    inputs = ScenarioInputs(
        driving_style=driving_style,
        coolant_temp_offset=float(coolant_offset),
        rpm_multiplier=float(rpm_multiplier),
        load_stress_multiplier=float(load_multiplier),
        intake_temp_offset=float(intake_offset),
    )

    rows: list[tuple[str, float, float, dict]] = []
    for component_key, component_data, is_placeholder in get_overview_components():
        if is_placeholder:
            continue
        baseline  = float(component_data.get("risk_score", 0.0) or 0.0)
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

            # Component filter bar — "All" + one pill per component.
            all_component_keys = [key for key, *_ in rows]
            filter_options     = ["All"] + [
                COMPONENT_DISPLAY_NAMES.get(k, k) for k in all_component_keys
            ]
            pills_html = '<div class="wi-filter-bar">'
            for opt in filter_options:
                is_active = (
                    (opt == "All" and active_filter is None)
                    or (opt != "All" and active_filter == opt)
                )
                active_cls = " active" if is_active else ""
                pills_html += (
                    f'<span class="wi-filter-pill{active_cls}">'
                    f'{html.escape(opt)}</span>'
                )
            pills_html += '</div>'
            st.markdown(pills_html, unsafe_allow_html=True)

            # Filter pill selection buttons (hidden under each pill via columns).
            pill_cols = st.columns(len(filter_options))
            for i, opt in enumerate(filter_options):
                with pill_cols[i]:
                    if st.button(
                        opt,
                        key=f"wi_filter_{i}",
                        use_container_width=True,
                    ):
                        if opt == "All":
                            st.session_state.pop("wi_filter", None)
                        else:
                            st.session_state["wi_filter"] = opt
                        st.rerun()

            # Build visible rows (respect filter; highlighted if it matches the
            # component that the user navigated from in Overview).
            focus_component: str | None = st.session_state.get("wi_focus_component")
            visible_rows = [
                (key, base, proj, cdata)
                for key, base, proj, cdata in rows
                if active_filter is None
                or COMPONENT_DISPLAY_NAMES.get(key, key) == active_filter
            ]

            body = "".join(
                _render_component_row(
                    key, base, proj, cdata, tokens,
                    scenario_key=active_scenario,
                    highlighted=(key == focus_component),
                )
                for key, base, proj, cdata in visible_rows
            )

            if not body:
                st.info("No components match the current filter.")
            else:
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
