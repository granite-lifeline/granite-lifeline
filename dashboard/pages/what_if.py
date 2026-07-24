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
    "Easy":   {"wi_coolant_p": -2, "wi_rpm_p": 0.90, "wi_load_p": 0.88, "wi_intake_p": 0, "wi_style_p": "Easy"},
    "Normal": {"wi_coolant_p": 0,  "wi_rpm_p": 1.00, "wi_load_p": 1.00, "wi_intake_p": 0, "wi_style_p": "Normal"},
    "Hard":   {"wi_coolant_p": 4,  "wi_rpm_p": 1.20, "wi_load_p": 1.25, "wi_intake_p": 3, "wi_style_p": "Hard"},
}

_PENDING_TO_WIDGET: dict[str, str] = {
    "wi_coolant_p": "wi_coolant",
    "wi_rpm_p":     "wi_rpm",
    "wi_load_p":    "wi_load",
    "wi_intake_p":  "wi_intake",
    "wi_style_p":   "wi_style",
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
        # high_load: rpm median 2065 → 2065/1675 = 1.23; maf median 46.4 → cap 1.50
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
        # intake_temp P95 ≈ 36 °C → offset capped at +10
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
        # idle rpm median 832 → 0.75× mixed; high coolant because no airflow cooling
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
        coolant_offset=-3,
        rpm_multiplier=0.54,
        load_multiplier=0.85,
        intake_offset=-5,
    ),
]

# Per-scenario, per-component plain-English reason why risk changes.
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

# ±7 % range shown under each What-if number (heuristic imprecision).
_UNCERTAINTY_MARGIN = 0.07
# Intensity score above which an extreme-scenario warning is shown.
_EXTREME_THRESHOLD  = 0.55


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
# If a pkl is absent the heuristic formula is used (graceful fallback).
# ---------------------------------------------------------------------------

_SURROGATE_CACHE: dict[str, object] = {}
_ARTIFACT_DIR = Path(__file__).parent.parent / "model_artifacts"


def _surrogate_predict(component_key: str, inputs: ScenarioInputs) -> float | None:
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
        return float(model.predict([[
            inputs.coolant_temp_offset,
            inputs.rpm_multiplier,
            inputs.load_stress_multiplier,
            inputs.intake_temp_offset,
        ]])[0])
    except Exception:
        return None


def _heuristic_sensitivity(component_key: str, inputs: ScenarioInputs) -> float:
    """
    Hand-calibrated heuristic risk delta.
    Coefficients grounded in KIT OBD-II operating-condition statistics
    (data_layer/operating_condition_statistics/operating_condition_signal_summary.csv)
    and Bosch Automotive Handbook physical relationships.
    """
    style_delta = STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
    rpm_delta   = inputs.rpm_multiplier - 1.0
    load_delta  = inputs.load_stress_multiplier - 1.0
    return {
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
            + 0.24 * max(load_delta, 0)
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
            + 0.22 * max(load_delta, 0)
        ),
    }.get(component_key, 0.10 * style_delta)


def _component_sensitivity(component_key: str, inputs: ScenarioInputs) -> float:
    surrogate = _surrogate_predict(component_key, inputs)
    return surrogate if surrogate is not None else _heuristic_sensitivity(component_key, inputs)


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
    baseline  = max(0.0, min(1.0, float(baseline_score or 0.0)))
    projected = baseline + _component_sensitivity(component_key, inputs)
    if inputs.driving_style == "Easy":
        projected = min(projected, baseline)
    return max(0.0, min(1.0, projected))


def _scenario_intensity(inputs: ScenarioInputs) -> float:
    return (
        STYLE_MULTIPLIERS[inputs.driving_style] - 1.0
        + max(inputs.rpm_multiplier - 1.0, 0)
        + max(inputs.load_stress_multiplier - 1.0, 0)
        + max(inputs.coolant_temp_offset, 0) / 20.0
        + max(inputs.intake_temp_offset, 0) / 20.0
    )


# ---------------------------------------------------------------------------
# CSS  — all visual styling lives here; no HTML wrappers around widgets
# ---------------------------------------------------------------------------

def _render_page_styles(tokens: dict) -> None:
    T = tokens  # short alias

    # Scenario cards are pure HTML (st.markdown); each column also gets a
    # transparent overlay button for click handling. CSS only needs to style
    # that overlay button — it must be invisible and fill its container.
    active_scenario = st.session_state.get("wi_scenario")
    sc_btn_rules = ""
    for sc in SCENARIO_CARDS:
        key_cls = f".st-key-wi_sc_{sc.key}"
        sc_btn_rules += f"""
        {key_cls} {{
            position: relative !important;
            margin-top: -8px !important;
        }}
        {key_cls} button {{
            background: transparent !important;
            border: none !important;
            bottom: 0 !important;
            cursor: pointer !important;
            left: 0 !important;
            opacity: 0 !important;
            position: absolute !important;
            right: 0 !important;
            top: 0 !important;
            width: 100% !important;
            height: 100% !important;
            z-index: 2 !important;
        }}
        """

    # Slider label styling — make them look cleaner
    slider_rules = """
        [data-testid="stSlider"] label p {
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        [data-testid="stSlider"] [data-testid="stTickBarMin"],
        [data-testid="stSlider"] [data-testid="stTickBarMax"] {
            font-size: 11px !important;
        }
    """

    st.markdown(
        f"""
        <style>
        /* ── Page shell ── */
        .wi-shell {{
            max-width: 1140px;
            margin: 0 auto;
        }}

        /* ── Section divider ── */
        .wi-divider {{
            border: none;
            border-top: 1px solid {T["border"]};
            margin: 24px 0;
        }}

        /* ── Section heading ── */
        .wi-section-head {{
            color: {T["text_secondary"]};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}

        /* ── Scenario picker: invisible overlay buttons on top of HTML cards ── */
        {sc_btn_rules}

        /* ── Scenario card (pure HTML, rendered via st.markdown) ── */
        .wi-sc-card {{
            background: {T["glass_surface"]};
            border: 2px solid {T["glass_border"]};
            border-radius: 14px;
            box-shadow: 0 1px 6px {T["shadow"]};
            cursor: pointer;
            display: flex;
            flex-direction: column;
            gap: 0;
            min-height: 120px;
            padding: 14px 12px 12px 12px;
            position: relative;
            transition: border-color 0.15s ease, background 0.15s ease;
            z-index: 1;
        }}
        .wi-sc-card:hover {{
            border-color: {T["accent"]};
            background: {hex_to_rgba(T["accent"], 0.05)};
        }}
        .wi-sc-card.wi-sc-active {{
            background: {hex_to_rgba(T["accent"], 0.07)};
            border-color: {T["accent"]};
        }}
        .wi-sc-icon {{
            display: block;
            margin-bottom: 8px;
        }}
        .wi-sc-label {{
            color: {T["text"]};
            display: block;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.3;
        }}
        .wi-sc-desc {{
            color: {T["text_secondary"]};
            display: block;
            font-size: 11px;
            line-height: 1.45;
            margin-top: 4px;
        }}
        .wi-sc-check {{
            color: {T["accent"]};
            display: block;
            font-size: 11px;
            font-weight: 700;
            margin-top: 6px;
        }}

        /* ── Summary banner ── */
        .wi-summary {{
            border-radius: 14px;
            margin-bottom: 20px;
            padding: 18px 20px;
        }}
        .wi-summary-label {{
            color: {T["text_secondary"]};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }}
        .wi-summary-verdict {{
            font-size: 22px;
            font-weight: 800;
            line-height: 1.2;
        }}
        .wi-summary-worst {{
            font-size: 13px;
            font-weight: 600;
            margin-top: 6px;
        }}
        .wi-summary-note {{
            color: {T["text_secondary"]};
            font-size: 12px;
            margin-top: 6px;
        }}
        .wi-extreme {{
            background: {hex_to_rgba(T["risk_medium"], 0.10)};
            border: 1px solid {hex_to_rgba(T["risk_medium"], 0.35)};
            border-radius: 8px;
            color: {T["risk_medium"]};
            font-size: 12px;
            font-weight: 600;
            line-height: 1.45;
            margin-top: 10px;
            padding: 9px 12px;
        }}

        /* ── Filter pills — rendered as a flex-wrap HTML row with real <button>s
               so they never overflow into clipped st.columns ── */
        .wi-filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 16px;
        }}
        .wi-filter-pill {{
            background: transparent;
            border: 1.5px solid {T["border"]};
            border-radius: 999px;
            color: {T["text_secondary"]};
            cursor: pointer;
            font-family: inherit;
            font-size: 12px;
            font-weight: 600;
            line-height: 1;
            padding: 5px 14px;
            transition: border-color 0.12s, color 0.12s;
            white-space: nowrap;
        }}
        .wi-filter-pill:hover {{
            border-color: {T["accent"]};
            color: {T["accent"]};
        }}
        .wi-filter-pill.wi-filter-active {{
            border-color: {T["accent"]};
            color: {T["accent"]};
        }}

        /* Hide the functional filter radio — pills provide the visual layer */
        .st-key-wi_filter_radio {{
            display: none !important;
        }}

        /* ── Component breakdown table ── */
        .wi-breakdown {{
            background: {T["glass_surface"]};
            border: 1px solid {T["glass_border"]};
            border-radius: 16px;
            box-shadow: 0 2px 12px {T["shadow"]};
            overflow: hidden;
        }}
        .wi-breakdown-head {{
            border-bottom: 1px solid {T["border"]};
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 16px 20px 14px 20px;
        }}
        .wi-breakdown-title {{
            color: {T["text"]};
            font-size: 15px;
            font-weight: 700;
        }}
        .wi-breakdown-legend {{
            color: {T["text_secondary"]};
            font-size: 11px;
            margin-left: auto;
        }}
        .wi-row {{
            border-bottom: 1px solid {T["border"]};
            display: grid;
            gap: 0;
            grid-template-columns: 1fr 88px 88px 100px;
            padding: 0;
        }}
        .wi-row:last-child {{
            border-bottom: none;
        }}
        .wi-row.wi-row-focus {{
            background: {hex_to_rgba(T["accent"], 0.04)};
        }}
        /* Name cell */
        .wi-cell-name {{
            align-items: flex-start;
            border-right: 1px solid {T["border"]};
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 16px 20px;
        }}
        .wi-cell-name-top {{
            align-items: center;
            display: flex;
            gap: 8px;
        }}
        .wi-cell-name-title {{
            color: {T["text"]};
            font-size: 14px;
            font-weight: 700;
        }}
        .wi-cell-name-why {{
            color: {T["text_secondary"]};
            font-size: 12px;
            line-height: 1.45;
        }}
        .wi-cell-action {{
            background: {hex_to_rgba(T["accent"], 0.06)};
            border-radius: 6px;
            color: {T["text"]};
            font-size: 11px;
            line-height: 1.45;
            margin-top: 4px;
            padding: 6px 8px;
        }}
        /* Metric cells */
        .wi-cell {{
            border-right: 1px solid {T["border"]};
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 16px 12px;
            text-align: right;
        }}
        .wi-cell:last-child {{
            border-right: none;
        }}
        .wi-cell-lbl {{
            color: {T["text_secondary"]};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.4px;
            margin-bottom: 4px;
            text-transform: uppercase;
        }}
        .wi-cell-val {{
            color: {T["text"]};
            font-family: {FONT_MONO};
            font-size: 17px;
            font-weight: 800;
            line-height: 1;
        }}
        .wi-cell-delta {{
            font-family: {FONT_MONO};
            font-size: 11px;
            font-weight: 700;
            margin-top: 3px;
        }}
        .wi-cell-range {{
            color: {T["text_secondary"]};
            font-family: {FONT_MONO};
            font-size: 10px;
            margin-top: 2px;
        }}
        /* Risk cell */
        .wi-cell-risk {{
            align-items: flex-end;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 16px 16px 16px 12px;
        }}
        .wi-pill {{
            border-radius: 999px;
            color: #fff;
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 10px;
        }}
        .wi-bar-track {{
            background: {T["surface_alt"]};
            border-radius: 999px;
            height: 5px;
            margin-top: 8px;
            overflow: hidden;
            width: 64px;
        }}
        .wi-bar-fill {{
            border-radius: 999px;
            height: 5px;
        }}

        /* ── Control panel — targeted via st.container key ── */
        .st-key-wi_controls_box {{
            background: {T["glass_surface"]};
            border: 1px solid {T["glass_border"]};
            border-radius: 16px;
            box-shadow: 0 2px 12px {T["shadow"]};
            padding: 20px;
        }}
        .wi-controls-title {{
            color: {T["text"]};
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 16px;
        }}
        .wi-style-desc {{
            color: {T["text_secondary"]};
            font-size: 12px;
            line-height: 1.4;
            margin-top: -8px;
            margin-bottom: 12px;
        }}
        .wi-slider-caption {{
            color: {T["text_secondary"]};
            font-size: 11px;
            margin-top: -10px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}

        /* Step indicator */
        .wi-steps {{
            display: flex;
            gap: 0;
            justify-content: center;
            margin: -12px auto 28px;
        }}
        .wi-step {{
            align-items: center;
            display: flex;
            gap: 6px;
            padding: 0 14px;
        }}
        .wi-step:not(:last-child)::after {{
            color: {T["border"]};
            content: "\203A";
            font-size: 18px;
            margin-left: 14px;
            line-height: 1;
        }}
        .wi-step-num {{
            background: {T["surface_alt"]};
            border: 1.5px solid {T["border"]};
            border-radius: 50%;
            color: {T["text_secondary"]};
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            height: 22px;
            width: 22px;
        }}
        .wi-step-lbl {{
            color: {T["text_secondary"]};
            font-size: 12px;
        }}

        /* Back button */
        .st-key-what_if_back_btn button {{
            background: transparent !important;
            border: 1px solid {T["border"]} !important;
            border-radius: 10px !important;
            color: {T["text"]} !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            padding: 6px 14px !important;
        }}
        .st-key-what_if_back_btn button:hover {{
            border-color: {T["accent"]} !important;
            color: {T["accent"]} !important;
        }}
        .st-key-what_if_back_btn button *,
        .st-key-what_if_back_btn button:hover * {{ color: inherit !important; }}

        /* Reset button */
        .st-key-what_if_reset_btn button {{
            background: transparent !important;
            border: 1px solid {T["border"]} !important;
            border-radius: 8px !important;
            color: {T["text_secondary"]} !important;
            font-size: 12px !important;
        }}
        .st-key-what_if_reset_btn button:hover {{
            border-color: {T["accent"]} !important;
            color: {T["accent"]} !important;
        }}
        .st-key-what_if_reset_btn button *,
        .st-key-what_if_reset_btn button:hover * {{ color: inherit !important; }}

        /* ── Responsive ── */
        @media (max-width: 760px) {{
            .wi-row {{ grid-template-columns: 1fr 80px 80px 80px; }}
            .wi-cell-name {{ padding: 14px; }}
            .wi-cell {{ padding: 14px 8px; }}
            .wi-cell-risk {{ padding: 14px 10px 14px 8px; }}
        }}
        @media (max-width: 540px) {{
            .wi-row {{ grid-template-columns: 1fr; }}
            .wi-cell-name {{ border-right: none; border-bottom: 1px solid {T["border"]}; }}
            .wi-cell {{ border-right: none; text-align: left; }}
            .wi-cell-risk {{ align-items: flex-start; }}
            .wi-bar-track {{ width: 100%; }}
        }}

        {slider_rules}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# HTML renderers
# ---------------------------------------------------------------------------

def _scenario_card_html(sc: ScenarioCard, active: bool, tokens: dict) -> str:
    """Build the full card HTML for a scenario. Rendered via st.markdown."""
    icon_color = tokens["accent"] if active else tokens["text_secondary"]
    icon_svg   = lucide_icon(sc.icon, size=20, color=icon_color)
    card_cls   = "wi-sc-card wi-sc-active" if active else "wi-sc-card"
    check      = (
        f'<span class="wi-sc-check">Selected</span>'
        if active else ""
    )
    return (
        f'<div class="{card_cls}">'
        f'<span class="wi-sc-icon">{icon_svg}</span>'
        f'<span class="wi-sc-label">{html.escape(sc.label)}</span>'
        f'<span class="wi-sc-desc">{html.escape(sc.description)}</span>'
        f'{check}'
        f'</div>'
    )


def _component_row_html(
    component_key: str,
    baseline: float,
    projected: float,
    component_data: dict,
    tokens: dict,
    scenario_key: str | None,
    focus: bool,
) -> str:
    T = tokens
    baseline_pct  = int(round(baseline * 100))
    projected_pct = int(round(projected * 100))
    delta_pct     = projected_pct - baseline_pct
    level         = _risk_level(projected)
    level_color   = _risk_color(level, tokens)

    # What-if value color: red for worse, green for better, muted for unchanged.
    val_color = (
        T["risk_high"]    if delta_pct > 0
        else T["risk_low"] if delta_pct < 0
        else T["text_secondary"]
    )

    # Delta arrow + formatted change
    if delta_pct > 0:
        arrow, arrow_color = "▲", T["risk_high"]
    elif delta_pct < 0:
        arrow, arrow_color = "▼", T["risk_low"]
    else:
        arrow, arrow_color = "—", T["text_secondary"]
    delta_html = (
        f'<div class="wi-cell-delta" style="color:{arrow_color};">'
        f'{arrow} {abs(delta_pct)}%</div>'
        if delta_pct != 0 else
        f'<div class="wi-cell-delta" style="color:{arrow_color};">—</div>'
    )

    # Uncertainty range
    lo = max(0,   int(round((projected - _UNCERTAINTY_MARGIN) * 100)))
    hi = min(100, int(round((projected + _UNCERTAINTY_MARGIN) * 100)))

    icon_svg  = lucide_icon(COMPONENT_ICONS.get(component_key, "activity"), size=16, color=level_color)
    disp_name = html.escape(COMPONENT_DISPLAY_NAMES.get(component_key, component_key))

    # Sub-label: scenario-specific reason or generic explanation.
    if scenario_key and scenario_key in SCENARIO_COMPONENT_REASONS:
        sub_label = SCENARIO_COMPONENT_REASONS[scenario_key].get(
            component_key,
            COMPONENT_EXPLANATIONS.get(component_key, ""),
        )
    else:
        sub_label = COMPONENT_EXPLANATIONS.get(component_key, "")

    # Action tip for High / Medium — no emoji.
    action_html = ""
    if level in ("High", "Medium"):
        actions = component_data.get("recommended_action") or []
        if actions:
            action_html = (
                f'<div class="wi-cell-action">{html.escape(str(actions[0]))}</div>'
            )

    row_cls = "wi-row wi-row-focus" if focus else "wi-row"

    return (
        f'<div class="{row_cls}">'

        # Name + reason
        '<div class="wi-cell-name">'
        f'<div class="wi-cell-name-top">{icon_svg}'
        f'<span class="wi-cell-name-title">{disp_name}</span></div>'
        f'<div class="wi-cell-name-why">{html.escape(sub_label)}</div>'
        f'{action_html}'
        '</div>'

        # Now
        '<div class="wi-cell">'
        '<div class="wi-cell-lbl">Now</div>'
        f'<div class="wi-cell-val">{baseline_pct}%</div>'
        '</div>'

        # What-if: projected value + delta arrow + uncertainty range
        f'<div class="wi-cell">'
        '<div class="wi-cell-lbl">What-if</div>'
        f'<div class="wi-cell-val" style="color:{val_color};">{projected_pct}%</div>'
        f'{delta_html}'
        f'<div class="wi-cell-range" title="Estimate +/- 7% model uncertainty">est. {lo}–{hi}%</div>'
        '</div>'

        # Risk level + bar
        '<div class="wi-cell-risk">'
        f'<span class="wi-pill" style="background:{level_color};">{html.escape(level)}</span>'
        f'<div class="wi-bar-track"><div class="wi-bar-fill" style="width:{projected_pct}%;background:{level_color};"></div></div>'
        '</div>'

        '</div>'
    )


def _slider_caption(label: str, value: float, is_offset: bool = False) -> str:
    """Return a plain-English description of the current slider value."""
    if is_offset:
        v = int(round(value))
        if v == 0:
            return f"{label}: same as now"
        direction = "warmer" if v > 0 else "cooler"
        return f"{label}: {abs(v)}\u00b0C {direction} than now"
    else:
        if 0.97 <= value <= 1.03:
            return f"{label}: normal"
        pct = int(round((value - 1.0) * 100))
        direction = "above" if pct > 0 else "below"
        return f"{label}: {abs(pct)}% {direction} normal"


def _render_summary(
    rows: list[tuple[str, float, float]],
    inputs: ScenarioInputs,
    tokens: dict,
) -> None:
    if not rows:
        return
    T = tokens

    avg_baseline = sum(r[1] for r in rows) / len(rows)
    avg_proj     = sum(r[2] for r in rows) / len(rows)
    b_pct        = int(round(avg_baseline * 100))
    p_pct        = int(round(avg_proj * 100))
    delta        = p_pct - b_pct

    # Identify the component with the largest positive delta.
    worst_row  = max(rows, key=lambda r: r[2] - r[1])
    worst_key  = worst_row[0]
    worst_proj = int(round(worst_row[2] * 100))
    worst_name = html.escape(COMPONENT_DISPLAY_NAMES.get(worst_key, worst_key))
    worst_delta = int(round((worst_row[2] - worst_row[1]) * 100))

    if delta > 0:
        verdict, vcolor, bg = (
            f"Overall risk goes up from {b_pct}% to {p_pct}%.",
            T["risk_high"],
            hex_to_rgba(T["risk_high"], 0.06),
        )
    elif delta < 0:
        verdict, vcolor, bg = (
            f"Overall risk drops from {b_pct}% to {p_pct}%.",
            T["risk_low"],
            hex_to_rgba(T["risk_low"], 0.06),
        )
    else:
        verdict, vcolor, bg = (
            f"Overall risk stays at {b_pct}%.",
            T["text_secondary"],
            T["glass_surface"],
        )

    # Worst-component callout (only shown when it actually worsens).
    worst_html = ""
    if worst_delta > 0:
        wc = T["risk_high"] if worst_proj >= 70 else T["risk_medium"] if worst_proj >= 30 else T["text_secondary"]
        worst_html = (
            f'<div class="wi-summary-worst" style="color:{wc};">'
            f'Biggest impact: {worst_name} rises to {worst_proj}%'
            f'</div>'
        )

    extreme = ""
    if _scenario_intensity(inputs) >= _EXTREME_THRESHOLD:
        extreme = (
            '<div class="wi-extreme">'
            "Extreme scenario — real changes are likely smaller than shown."
            "</div>"
        )

    st.markdown(
        f'<div class="wi-summary" style="background:{bg};border:1px solid {hex_to_rgba(vcolor, 0.2)};">'
        f'<div class="wi-summary-label">Result</div>'
        f'<div class="wi-summary-verdict" style="color:{vcolor};">{html.escape(verdict)}</div>'
        f'{worst_html}'
        f'<div class="wi-summary-note">Estimate only — not a diagnostic scan.</div>'
        f'{extreme}'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _flush_pending_presets() -> None:
    """Promote pending preset keys to live widget keys before widgets render."""
    for pending_key, widget_key in _PENDING_TO_WIDGET.items():
        if pending_key in st.session_state:
            st.session_state[widget_key] = st.session_state.pop(pending_key)


def _apply_scenario(sc: ScenarioCard) -> None:
    st.session_state.update({
        "wi_scenario":  sc.key,
        "wi_style_p":   sc.driving_style,   # pending — flushed before next widget render
        "wi_coolant_p": sc.coolant_offset,
        "wi_rpm_p":     sc.rpm_multiplier,
        "wi_load_p":    sc.load_multiplier,
        "wi_intake_p":  sc.intake_offset,
    })
    st.rerun()


def _reset_all() -> None:
    for k in (
        "wi_coolant", "wi_rpm", "wi_load", "wi_intake",
        "wi_style", "wi_scenario", "wi_filter", "wi_focus_component",
        "wi_coolant_p", "wi_rpm_p", "wi_load_p", "wi_intake_p", "wi_style_p",
    ):
        st.session_state.pop(k, None)
    st.rerun()


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def show_what_if_page() -> None:
    """Render the What-If Analysis page."""
    _flush_pending_presets()  # must run before any widget

    dark_mode       = st.session_state.get("dark_mode", False)
    tokens          = THEME_TOKENS["dark" if dark_mode else "light"]
    active_scenario = st.session_state.get("wi_scenario")
    active_filter   = st.session_state.get("wi_filter")
    focus_component = st.session_state.get("wi_focus_component")

    _render_page_styles(tokens)

    st.markdown('<div class="wi-shell">', unsafe_allow_html=True)

    # ── Nav bar ─────────────────────────────────────────────────────────────
    nav_l, _gap = st.columns([3, 7])
    with nav_l:
        if st.button("← Back to Dashboard", key="what_if_back_btn"):
            st.session_state["page"] = "overview"
            st.rerun()

    # ── Page title ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;margin:16px 0 20px;">'
        f'<h1 style="color:{tokens["text"]};font-size:26px;font-weight:800;'
        f'line-height:1.2;margin:0;">What if I drive differently?</h1>'
        f'<p style="color:{tokens["text_secondary"]};font-size:13px;'
        f'margin:6px auto 0;max-width:480px;line-height:1.5;">'
        f'Pick a scenario to instantly see the impact, or fine-tune with the sliders.</p>'
        f'</div>'
        # Step indicator
        f'<div class="wi-steps">'
        f'<div class="wi-step"><span class="wi-step-num">1</span>'
        f'<span class="wi-step-lbl">Pick a scenario</span></div>'
        f'<div class="wi-step"><span class="wi-step-num">2</span>'
        f'<span class="wi-step-lbl">Fine-tune sliders</span></div>'
        f'<div class="wi-step"><span class="wi-step-num">3</span>'
        f'<span class="wi-step-lbl">See the impact</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Scenario picker ──────────────────────────────────────────────────────
    # Each column: HTML card (visible) + transparent st.button overlay (clickable).
    # The button container is position:relative; the button is position:absolute
    # covering the entire card so clicking anywhere on the card fires it.
    st.markdown('<div class="wi-section-head">Choose a scenario</div>', unsafe_allow_html=True)
    sc_cols = st.columns(len(SCENARIO_CARDS), gap="small")
    for i, sc in enumerate(SCENARIO_CARDS):
        with sc_cols[i]:
            is_active = sc.key == active_scenario
            # Render the visible card HTML
            st.markdown(_scenario_card_html(sc, is_active, tokens), unsafe_allow_html=True)
            # Transparent overlay button — absolutely positioned over the card via CSS
            if st.button(
                sc.label,           # plain text label (invisible due to opacity:0)
                key=f"wi_sc_{sc.key}",
                use_container_width=True,
            ):
                _apply_scenario(sc)

    st.markdown('<hr class="wi-divider">', unsafe_allow_html=True)

    # ── Two-column layout: controls left, results right ──────────────────────
    ctrl_col, result_col = st.columns([1, 1.75], gap="large")

    # ── Controls — use st.container so CSS can target the real DOM wrapper ──
    with ctrl_col:
        with st.container(key="wi_controls_box"):
            st.markdown(
                '<div class="wi-controls-title">Fine-tune</div>',
                unsafe_allow_html=True,
            )

            prev_style = st.session_state.get("wi_style", "Normal")
            driving_style = st.radio(
                "Driving style",
                list(STYLE_MULTIPLIERS),
                index=list(STYLE_MULTIPLIERS).index(prev_style),
                horizontal=True,
                key="wi_style",
                label_visibility="hidden",
            )

            # Auto-apply slider presets when the radio selection changes.
            if driving_style != prev_style:
                presets = STYLE_SLIDER_PRESETS[driving_style]
                # Write only the slider pending keys (not wi_style_p — already set).
                for pk in ("wi_coolant_p", "wi_rpm_p", "wi_load_p", "wi_intake_p"):
                    st.session_state[pk] = presets[pk]
                st.session_state.pop("wi_scenario", None)
                st.rerun()

            st.markdown(
                f'<div class="wi-style-desc">{html.escape(STYLE_DESCRIPTIONS[driving_style])}</div>',
                unsafe_allow_html=True,
            )

            coolant_offset = st.slider(
                "Engine temperature (°C change)",
                min_value=-10, max_value=20, step=1,
                value=st.session_state.get("wi_coolant", 0),
                key="wi_coolant",
                help="How much hotter or cooler the engine runs vs. now.",
            )
            st.markdown(
                f'<div class="wi-slider-caption">'
                f'{html.escape(_slider_caption("Engine temp", coolant_offset, is_offset=True))}'
                f'</div>',
                unsafe_allow_html=True,
            )

            rpm_multiplier = st.slider(
                "Engine speed",
                min_value=0.8, max_value=1.4, step=0.05,
                value=st.session_state.get("wi_rpm", 1.0),
                format="%.2fx",
                key="wi_rpm",
                help="How much faster or slower the engine runs. "
                     "1.20x means 20% more revs than your current reading.",
            )
            st.markdown(
                f'<div class="wi-slider-caption">'
                f'{html.escape(_slider_caption("Engine speed", rpm_multiplier))}'
                f'</div>',
                unsafe_allow_html=True,
            )

            load_multiplier = st.slider(
                "Acceleration & load",
                min_value=0.8, max_value=1.5, step=0.05,
                value=st.session_state.get("wi_load", 1.0),
                format="%.2fx",
                key="wi_load",
                help="How hard the engine works. Higher = towing, hill climbing, heavy acceleration.",
            )
            st.markdown(
                f'<div class="wi-slider-caption">'
                f'{html.escape(_slider_caption("Load", load_multiplier))}'
                f'</div>',
                unsafe_allow_html=True,
            )

            intake_offset = st.slider(
                "Outside air temperature (°C change)",
                min_value=-10, max_value=20, step=1,
                value=st.session_state.get("wi_intake", 0),
                key="wi_intake",
                help="Positive = hotter outside air (hot day, stop-and-go traffic).",
            )
            st.markdown(
                f'<div class="wi-slider-caption">'
                f'{html.escape(_slider_caption("Outside air", intake_offset, is_offset=True))}'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button(
                "Reset",
                key="what_if_reset_btn",
                use_container_width=True,
                help="Reset everything to Normal defaults.",
            ):
                _reset_all()

    # ── Compute projections ───────────────────────────────────────────────────
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

    # ── Results ───────────────────────────────────────────────────────────────
    with result_col:
        if not rows:
            st.info(
                "No component data yet. "
                "Upload a CSV on the main dashboard to get started."
            )
        else:
            # Summary banner
            _render_summary(
                [(k, b, p) for k, b, p, _ in rows],
                inputs,
                tokens,
            )

            # Filter pills — pure HTML buttons in a flex-wrap row.
            # A hidden st.radio tracks the selection; JS-free via form submit fallback
            # is unavailable in Streamlit, so we use a compact st.radio with pill CSS.
            all_keys      = [k for k, *_ in rows]
            filter_labels = ["All"] + [COMPONENT_DISPLAY_NAMES.get(k, k) for k in all_keys]

            pills_html = '<div class="wi-filter-row">'
            for lbl in filter_labels:
                is_active_pill = (lbl == "All" and active_filter is None) or (
                    lbl != "All" and active_filter == lbl
                )
                pill_cls = "wi-filter-pill wi-filter-active" if is_active_pill else "wi-filter-pill"
                pills_html += f'<span class="{pill_cls}">{html.escape(lbl)}</span>'
            pills_html += "</div>"
            st.markdown(pills_html, unsafe_allow_html=True)

            # Invisible st.radio drives the actual selection (Streamlit needs a widget).
            selected_pill = st.radio(
                "Filter by component",
                filter_labels,
                index=filter_labels.index(active_filter) if active_filter in filter_labels else 0,
                horizontal=True,
                key="wi_filter_radio",
                label_visibility="collapsed",
            )
            # Sync session state and rerun only when selection changes.
            new_filter = None if selected_pill == "All" else selected_pill
            if new_filter != active_filter:
                if new_filter is None:
                    st.session_state.pop("wi_filter", None)
                else:
                    st.session_state["wi_filter"] = new_filter
                st.rerun()

            # Build visible rows
            visible = [
                (k, b, p, d) for k, b, p, d in rows
                if active_filter is None
                or COMPONENT_DISPLAY_NAMES.get(k, k) == active_filter
            ]

            if not visible:
                st.info("No components match the current filter.")
            else:
                rows_html = "".join(
                    _component_row_html(
                        k, b, p, d, tokens,
                        scenario_key=active_scenario,
                        focus=(k == focus_component),
                    )
                    for k, b, p, d in visible
                )
                st.markdown(
                    '<div class="wi-breakdown">'
                    '<div class="wi-breakdown-head">'
                    f'{lucide_icon("sliders", size=15, color=tokens["accent"])}'
                    '<span class="wi-breakdown-title">Component breakdown</span>'
                    '<span class="wi-breakdown-legend">Now · What-if · Risk level</span>'
                    '</div>'
                    f'{rows_html}'
                    '</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('</div>', unsafe_allow_html=True)

    try:
        from ui_components import show_footer
    except ImportError:
        from dashboard.ui_components import show_footer
    show_footer(dark_mode)
