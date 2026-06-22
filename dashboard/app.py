"""
Granite Lifeline Dashboard - Overview Page

Displays vehicle health status with component risk levels and navigation
to detailed diagnostic reports.
"""

import streamlit as st

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


def apply_theme(dark_mode: bool):
    """Apply Animal Crossing themed CSS based on dark_mode setting."""
    font_link = (
        '<link href="https://fonts.googleapis.com/css2?family=Nunito:'
        'wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;'
        '700&display=swap" rel="stylesheet">'
    )

    if dark_mode:
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
                background-color: #2d2416 !important;
            }}
            .main {{
                background-color: #3d3020 !important;
            }}
            .main .block-container {{
                background-color: #3d3020 !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
                max-width: 1100px !important;
            }}
            h1, h2, h3 {{
                color: #f8f0dc !important;
                font-weight: 700 !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
            }}
            h1 {{
                font-size: 32px !important;
                margin-bottom: 8px !important;
            }}
            p, label, span, .stMarkdown, .stMarkdown p {{
                color: #e8d5b0 !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
            }}
            .stCaption {{
                color: #c4a882 !important;
                font-size: 13px !important;
            }}
            .stButton > button {{
                background: linear-gradient(135deg, #4db8a8 0%,
                            #3a9d8f 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 10px 20px !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
                transition: all 0.2s ease !important;
            }}
            .stButton > button:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
            }}
            .stButton > button:active {{
                transform: translateY(0px) !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                gap: 1.5rem !important;
            }}
        </style>
        """
    else:
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
                background-color: #f8f8f0 !important;
            }}
            .main {{
                background-color: rgb(247, 243, 223) !important;
            }}
            .main .block-container {{
                background-color: rgb(247, 243, 223) !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
                max-width: 1100px !important;
            }}
            h1, h2, h3 {{
                color: #794f27 !important;
                font-weight: 700 !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
            }}
            h1 {{
                font-size: 32px !important;
                margin-bottom: 8px !important;
            }}
            p, label, span, .stMarkdown, .stMarkdown p {{
                color: #725d42 !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
            }}
            .stCaption {{
                color: #9f927d !important;
                font-size: 13px !important;
            }}
            .stButton > button {{
                background: linear-gradient(135deg, #4db8a8 0%,
                            #3a9d8f 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 10px 20px !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                font-family: Nunito, 'Noto Sans SC', -apple-system,
                             sans-serif !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
                transition: all 0.2s ease !important;
            }}
            .stButton > button:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
            }}
            .stButton > button:active {{
                transform: translateY(0px) !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                gap: 1.5rem !important;
            }}
        </style>
        """

    st.markdown(theme_css, unsafe_allow_html=True)


def show_overview_page():
    """Display the Overview Page with component health summary."""
    dark_mode = st.session_state.get("dark_mode", False)

    col_title, col_theme = st.columns([5, 1])
    with col_title:
        st.title("Vehicle Health Status")
        st.caption("Last checked: 2026-06-23 10:00")
    with col_theme:
        if dark_mode:
            if st.button("☀", key="theme_btn", use_container_width=True):
                st.session_state["dark_mode"] = False
                st.rerun()
        else:
            if st.button("◐", key="theme_btn", use_container_width=True):
                st.session_state["dark_mode"] = True
                st.rerun()

    has_high_risk = any(
        comp["risk_level"] == "High" for comp in MOCK_DATA.values()
    )

    if has_high_risk:
        st.error(
            "⚠️ Attention needed — one or more components require "
            "urgent action"
        )
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
            if dark_mode:
                card_bg = "#4a3d2a"
                card_border = "#6b5a3f"
                card_shadow = "rgba(0,0,0,0.3)"
                text_color = "#f8f0dc"
                secondary_color = "#c4a882"
            else:
                card_bg = "#ffffff"
                card_border = "#d4c4a8"
                card_shadow = "rgba(121,79,39,0.08)"
                text_color = "#794f27"
                secondary_color = "#9f927d"

            risk_level = component_data["risk_level"]
            if risk_level == "High":
                badge_bg = "#d97757"
                risk_label = "High Risk"
            elif risk_level == "Medium":
                badge_bg = "#e8b86d"
                risk_label = "Medium Risk"
            else:
                badge_bg = "#7fb685"
                risk_label = "Low Risk"

            risk_pct = int(component_data["risk_score"] * 100)

            card_html = f"""
            <div style="
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 16px;
                box-shadow: 0 2px 12px {card_shadow};
                padding: 24px;
                margin-bottom: 16px;
                min-height: 180px;
            ">
                <h3 style="
                    margin: 0 0 16px 0;
                    color: {text_color};
                    font-size: 18px;
                    font-weight: 700;
                ">
                    {component_data["display_name"]}
                </h3>
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
                <div style="margin-top: 16px;">
                    <p style="
                        font-size: 36px;
                        font-weight: 800;
                        margin: 0;
                        color: {text_color};
                        line-height: 1;
                    ">
                        {risk_pct}%
                    </p>
                    <p style="
                        font-size: 12px;
                        color: {secondary_color};
                        margin: 4px 0 0 0;
                        font-weight: 500;
                    ">
                        Risk Score
                    </p>
                </div>
            </div>
            """

            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(
                "View Details",
                key=f"btn_{component_key}",
                use_container_width=True
            ):
                st.session_state["selected_component"] = component_key
                st.session_state["page"] = "detail"
                st.rerun()


def show_detail_page():
    """Placeholder for Detail Page (to be implemented)."""
    st.title("Component Details")
    st.info("Detail page coming soon")

    if st.button("← Back to Overview"):
        st.session_state["page"] = "overview"
        st.rerun()


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

# Made with Bob
