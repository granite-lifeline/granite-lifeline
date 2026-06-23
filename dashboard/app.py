"""
Granite Lifeline Dashboard - Overview Page

Displays vehicle health status with component risk levels and navigation
to detailed diagnostic reports.
"""

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
                box-shadow: 0 5px 0 0 #2d7a70 !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1)
                            !important;
            }}
            .stButton > button:hover {{
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 0 0 #2d7a70 !important;
            }}
            .stButton > button:active {{
                transform: translateY(2px) !important;
                box-shadow: 0 1px 0 0 #2d7a70 !important;
            }}
            .stButton > button:focus-visible {{
                outline: 2px solid #ffcc00 !important;
                outline-offset: 2px !important;
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
                box-shadow: 0 5px 0 0 #2d7a70 !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1)
                            !important;
            }}
            .stButton > button:hover {{
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 0 0 #2d7a70 !important;
            }}
            .stButton > button:active {{
                transform: translateY(2px) !important;
                box-shadow: 0 1px 0 0 #2d7a70 !important;
            }}
            .stButton > button:focus-visible {{
                outline: 2px solid #ffcc00 !important;
                outline-offset: 2px !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                gap: 1.5rem !important;
            }}
            
            /* Animal Crossing Loading Spinner */
            @keyframes ac-spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .ac-spinner {{
                border: 4px solid rgba(25, 200, 185, 0.2);
                border-top: 4px solid #19c8b9;
                border-radius: 50%;
                width: 48px;
                height: 48px;
                animation: ac-spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
                margin: 40px auto;
            }}
            
            .ac-spinner-container {{
                text-align: center;
                padding: 60px 20px;
            }}
            
            .ac-spinner-text {{
                color: #19c8b9;
                font-size: 14px;
                font-weight: 600;
                margin-top: 16px;
                letter-spacing: 0.5px;
            }}
        </style>
        """

    st.markdown(theme_css, unsafe_allow_html=True)


def show_footer(dark_mode: bool):
    """Display team footer at bottom of page."""
    footer_color = "#c4a882" if dark_mode else "#9f927d"

    footer_html = f"""
    <div style="
        text-align: center;
        color: {footer_color};
        font-size: 12px;
        margin-top: 48px;
        padding: 16px 0;
    ">
        Granite Lifeline · University of Bristol MSc Computer Science ·
        IBM-sponsored project · Team: Charlotte Yu, Jintong He, Lei Pei,
        Qiuting Fu, Lucca Zhou, Ray Wang
    </div>
    """

    st.markdown(footer_html, unsafe_allow_html=True)


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

            # Adjust card background to warmer, less harsh color
            if dark_mode:
                card_bg_adjusted = card_bg
                pattern_color = "rgba(248, 240, 220, 0.06)"
            else:
                card_bg_adjusted = "#faf8f0"  # Warmer cream instead of pure white
                pattern_color = "rgba(121, 79, 39, 0.08)"
            
            card_html = f"""
            <div style="
                background-color: {card_bg_adjusted};
                background-image: radial-gradient(
                    circle,
                    {pattern_color} 1.5px,
                    transparent 1.5px
                );
                background-size: 20px 20px;
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

    st.markdown("---")
    show_footer(st.session_state.get("dark_mode", False))


def show_detail_page():
    """Display Component Detail Page with risk metrics and trend chart."""
    component_key = st.session_state.get("selected_component")

    if not component_key or component_key not in MOCK_DATA:
        st.error("Component not found.")
        if st.button("← Back to Overview"):
            st.session_state["page"] = "overview"
            st.rerun()
        return

    component_data = MOCK_DATA[component_key]

    if st.button("← Back to Overview"):
        st.session_state["page"] = "overview"
        st.rerun()

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
    <div style="display: flex; align-items: center; margin-bottom: 24px;">
        <h1 style="margin: 0; display: inline;">
            {component_data["display_name"]}
        </h1>
        {badge_html}
    </div>
    """

    st.markdown(title_html, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        risk_pct = int(component_data["risk_score"] * 100)
        st.metric("Risk Score", f"{risk_pct}%")
    with col2:
        st.metric("Last Updated", "2026-06-23 10:00")

    st.markdown("---")

    trend = component_data["trend"]

    if len(trend) < 2:
        st.warning("Not enough data yet to show a trend.")
    else:
        st.subheader("Risk Score Trend")
        
        # Show loading spinner with Animal Crossing style
        with st.spinner(""):
            spinner_html = """
            <div class="ac-spinner-container">
                <div class="ac-spinner"></div>
                <div class="ac-spinner-text">Loading trend data...</div>
            </div>
            """
            spinner_placeholder = st.empty()
            spinner_placeholder.markdown(spinner_html, unsafe_allow_html=True)
            
            import time
            time.sleep(0.5)  # Brief loading animation
            spinner_placeholder.empty()

        time_labels = ["T-4", "T-3", "T-2", "T-1", "Now"]
        time_labels = time_labels[-len(trend):]

        dark_mode = st.session_state.get("dark_mode", False)

        # Optimized Animal Crossing color palette
        if dark_mode:
            line_color = "#7fb685"  # Softer green for dark mode
            bg_color = "#3d3020"
            paper_bg = "#2d2416"
            text_color = "#e8d5b0"
            grid_color = "#5c4a2a"
        else:
            line_color = "#19c8b9"  # Mint green for light mode
            bg_color = "rgb(247,243,223)"
            paper_bg = "#f8f8f0"
            text_color = "#725d42"
            grid_color = "#c4b89e"

        fill_color = "rgba(127, 182, 133, 0.15)" if dark_mode else "rgba(25, 200, 185, 0.2)"

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=time_labels,
            y=trend,
            mode="lines+markers",
            line=dict(color=line_color, width=3, shape="spline"),
            marker=dict(
                size=10,
                color=line_color,
                line=dict(color="white" if not dark_mode else "#2d2416", width=2)
            ),
            fill="tozeroy",
            fillcolor=fill_color,
            name="Risk Score",
            hovertemplate="<b>%{x}</b><br>Risk Score: %{y:.0%}<extra></extra>"
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
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Risk score over the last 5 recorded readings. "
            "Higher values indicate greater risk."
        )

    st.markdown("---")

    st.subheader("Key Signals")

    key_signals = component_data["key_signals"]

    if not key_signals:
        st.info("No signal data available for this component.")
    else:
        dark_mode = st.session_state.get("dark_mode", False)
        row_bg = (
            "rgba(247,243,223,0.6)" if not dark_mode
            else "rgba(61,52,40,0.3)"
        )

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
            row_html = f"""
            <div style="
                background: {row_bg};
                border-radius: 8px;
                padding: 8px;
                margin-bottom: 4px;
            ">
            </div>
            """
            st.markdown(row_html, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"**{signal['display_name']}**")

            with col2:
                st.text(f"{signal['value']} {signal['unit']}")

            with col3:
                ref_lower = signal["reference_range"][0]
                ref_upper = signal["reference_range"][1]
                st.text(
                    f"Normal: {ref_lower}–{ref_upper} {signal['unit']}"
                )

            with col4:
                if status == "ABNORMAL":
                    badge_bg = "#e05a5a"
                else:
                    badge_bg = "#6fba2c"

                badge_html = f"""
                <div style="
                    background-color: {badge_bg};
                    color: white;
                    padding: 3px 10px;
                    border-radius: 12px;
                    text-align: center;
                    font-size: 11px;
                    font-weight: 600;
                ">
                    {status}
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Diagnostic Report")

    dark_mode = st.session_state.get("dark_mode", False)

    if dark_mode:
        card_bg = "#3d3020"
        card_border = "#5c4a2a"
        title_color = "#f8f0dc"
        body_color = "#c4a882"
    else:
        card_bg = "rgb(247,243,223)"
        card_border = "#c4b89e"
        title_color = "#794f27"
        body_color = "#9f927d"

    cards = [
        {
            "icon": "🔍",
            "title": "What's Happening",
            "body": "Pending Granite LLM report generation..."
        },
        {
            "icon": "🔎",
            "title": "Why This Matters",
            "body": "Pending Granite LLM report generation..."
        },
        {
            "icon": "🔧",
            "title": "What You Should Do",
            "body": "Pending Granite LLM report generation..."
        }
    ]

    for card in cards:
        card_html = f"""
        <div style="
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        ">
            <h3 style="
                color: {title_color};
                margin: 0 0 8px 0;
                font-size: 16px;
                font-weight: 600;
            ">
                {card['icon']} {card['title']}
            </h3>
            <p style="
                color: {body_color};
                margin: 0;
                font-size: 14px;
                font-style: italic;
            ">
                {card['body']}
            </p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    show_footer(st.session_state.get("dark_mode", False))


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
