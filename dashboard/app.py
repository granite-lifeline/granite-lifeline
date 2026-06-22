"""
Granite Lifeline Dashboard - Overview Page

Displays vehicle health status with component risk levels and navigation
to detailed diagnostic reports.
"""

import streamlit as st

# Mock data for three components
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

# Risk level priority for sorting
RISK_PRIORITY = {"High": 0, "Medium": 1, "Low": 2}


def apply_theme(dark_mode: bool):
    """Apply Animal Crossing themed CSS based on dark_mode setting."""
    if dark_mode:
        # Animal Crossing Dark Theme
        theme_css = """
        <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            /* Hide sidebar and header */
            section[data-testid="stSidebar"] {
                display: none !important;
            }
            header[data-testid="stHeader"] {
                display: none !important;
            }
            
            /* Main app background */
            [data-testid="stAppViewContainer"] {
                background-color: #2d2416 !important;
            }
            
            /* Content block background */
            .main .block-container {
                background-color: #3d3020 !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Headings */
            h1, h2, h3 {
                color: #f8f0dc !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Body text */
            p, div, span, label {
                color: #e8d5b0 !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Secondary text */
            .stCaption {
                color: #c4a882 !important;
            }
            
            /* Buttons */
            .stButton > button {
                background-color: #19c8b9 !important;
                color: white !important;
                border-radius: 50px !important;
                border: none !important;
                box-shadow: 0 5px 0 #bdaea0 !important;
                font-family: 'Nunito', sans-serif !important;
                font-weight: 600 !important;
            }
            
            .stButton > button:active {
                transform: translateY(3px) !important;
                box-shadow: 0 2px 0 #bdaea0 !important;
            }
            
            /* Card/container borders */
            .element-container {
                border-color: #5c4a2a !important;
            }
        </style>
        """
    else:
        # Animal Crossing Light Theme
        theme_css = """
        <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            /* Hide sidebar and header */
            section[data-testid="stSidebar"] {
                display: none !important;
            }
            header[data-testid="stHeader"] {
                display: none !important;
            }
            
            /* Main app background */
            [data-testid="stAppViewContainer"] {
                background-color: #f8f8f0 !important;
            }
            
            /* Content block background */
            .main .block-container {
                background-color: rgb(247, 243, 223) !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Headings */
            h1, h2, h3 {
                color: #794f27 !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Body text */
            p, div, span, label {
                color: #725d42 !important;
                font-family: 'Nunito', sans-serif !important;
            }
            
            /* Buttons */
            .stButton > button {
                background-color: #19c8b9 !important;
                color: white !important;
                border-radius: 50px !important;
                border: none !important;
                box-shadow: 0 5px 0 #bdaea0 !important;
                font-family: 'Nunito', sans-serif !important;
                font-weight: 600 !important;
            }
            
            .stButton > button:active {
                transform: translateY(3px) !important;
                box-shadow: 0 2px 0 #bdaea0 !important;
            }
        </style>
        """
    
    st.markdown(theme_css, unsafe_allow_html=True)


def show_overview_page():
    """Display the Overview Page with component health summary."""
    st.title("Your Vehicle Health Status")
    st.caption("Last checked: 2026-06-23 10:00")

    # Check if any component has High risk
    has_high_risk = any(
        comp["risk_level"] == "High" for comp in MOCK_DATA.values()
    )

    # Display summary banner
    if has_high_risk:
        st.error(
            "⚠️ Attention needed — one or more components require "
            "urgent action"
        )
    else:
        st.success("✓ All systems within normal range")

    st.markdown("---")

    # Sort components by risk level (High → Medium → Low)
    sorted_components = sorted(
        MOCK_DATA.items(),
        key=lambda x: RISK_PRIORITY[x[1]["risk_level"]]
    )

    # Display component cards in 3 columns
    cols = st.columns(3)

    for idx, (component_key, component_data) in enumerate(
        sorted_components
    ):
        with cols[idx]:
            # Component card
            st.subheader(component_data["display_name"])

            # Risk level badge with color
            risk_level = component_data["risk_level"]
            if risk_level == "High":
                st.markdown(
                    '<span style="background-color: #ff4b4b; color: white; '
                    'padding: 4px 12px; border-radius: 4px; font-weight: '
                    'bold;">🔴 High Risk</span>',
                    unsafe_allow_html=True
                )
            elif risk_level == "Medium":
                st.markdown(
                    '<span style="background-color: #ffa500; color: white; '
                    'padding: 4px 12px; border-radius: 4px; font-weight: '
                    'bold;">🟠 Medium Risk</span>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<span style="background-color: #00cc00; color: white; '
                    'padding: 4px 12px; border-radius: 4px; font-weight: '
                    'bold;">🟢 Low Risk</span>',
                    unsafe_allow_html=True
                )

            # Risk score as percentage
            risk_pct = int(component_data["risk_score"] * 100)
            st.metric("Risk Score", f"{risk_pct}%")

            # View Details button
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
        layout="wide"
    )

    # Initialize session state
    if "page" not in st.session_state:
        st.session_state["page"] = "overview"

    # Day/night toggle at the top
    col1, col2 = st.columns([6, 1])
    with col1:
        pass  # Empty column
    with col2:
        dark_mode = st.toggle("🌙", key="dark_mode", value=False)

    # Apply theme based on toggle state
    apply_theme(dark_mode)

    # Route to appropriate page
    if st.session_state["page"] == "detail":
        show_detail_page()
    else:
        show_overview_page()


if __name__ == "__main__":
    main()
