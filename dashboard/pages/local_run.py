"""Local setup guide page for running the app on this computer."""

from __future__ import annotations

import html

import streamlit as st

from theme import FONT_MONO, THEME_TOKENS, hex_to_rgba, lucide_icon
from ui_components import page_title_html, show_footer


def _render_page_styles(tokens: dict[str, str]) -> None:
    """Inject local-run guide styles."""
    st.markdown(
        f"""
        <style>
        .local-run-shell {{
            margin: 0 auto;
            max-width: 1180px;
            padding: 0 8px 24px;
        }}
        .local-run-steps {{
            align-items: center;
            display: flex;
            gap: 0;
            justify-content: center;
            margin: 4px auto 28px;
        }}
        .local-run-step-chip {{
            align-items: center;
            display: flex;
            gap: 7px;
            padding: 0 12px;
        }}
        .local-run-step-chip:not(:last-child)::after {{
            color: {tokens["text_secondary"]};
            content: "\\2192";
            font-size: 16px;
            font-weight: 700;
            line-height: 1;
            margin-left: 12px;
            opacity: 0.75;
        }}
        .local-run-step-num {{
            align-items: center;
            background: {tokens["surface_alt"]};
            border: 1.5px solid {tokens["border"]};
            border-radius: 50%;
            color: {tokens["text_secondary"]};
            display: inline-flex;
            font-family: {FONT_MONO};
            font-size: 12px;
            font-weight: 700;
            height: 24px;
            justify-content: center;
            line-height: 1;
            width: 24px;
        }}
        .local-run-step-lbl {{
            color: {tokens["text_secondary"]};
            font-size: 12px;
        }}
        .local-run-section-row {{
            align-items: center;
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .local-run-section-head {{
            color: {tokens["text"]};
            font-size: 15px;
            font-weight: 700;
        }}
        .local-run-section-meta {{
            color: {tokens["text_secondary"]};
            font-size: 12px;
        }}
        .local-run-card {{
            background: {tokens["glass_surface"]};
            border: 1px solid {tokens["glass_border"]};
            border-radius: 16px;
            box-shadow: 0 2px 12px {tokens["shadow"]};
            box-sizing: border-box;
            padding: 20px;
        }}
        .st-key-local_run_commands_card {{
            background: {tokens["glass_surface"]};
            border: 1px solid {tokens["glass_border"]};
            border-radius: 16px;
            box-shadow: 0 2px 12px {tokens["shadow"]};
            box-sizing: border-box;
            padding: 20px;
        }}
        .local-run-step-card {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            border-radius: 12px;
            box-sizing: border-box;
            margin: 14px 0 10px;
            padding: 16px;
        }}
        .local-run-step-card-head {{
            align-items: center;
            display: flex;
            gap: 9px;
            margin-bottom: 8px;
        }}
        .local-run-step-card-title {{
            color: {tokens["text"]};
            font-size: 14px;
            font-weight: 700;
            line-height: 1.3;
        }}
        .local-run-step-card-copy {{
            color: {tokens["text_secondary"]};
            font-size: 12px;
            line-height: 1.45;
        }}
        .local-run-note-card {{
            background: {tokens["accent_subtle"]};
            border: 1px solid {hex_to_rgba(tokens["accent"], 0.22)};
            border-radius: 12px;
            color: {tokens["text"]};
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 14px;
            padding: 16px;
        }}
        .local-run-note-title {{
            align-items: center;
            color: {tokens["text"]};
            display: flex;
            font-size: 14px;
            font-weight: 700;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .local-run-dot-list {{
            color: {tokens["text_secondary"]};
            font-size: 13px;
            line-height: 1.6;
            margin: 0;
            padding-left: 18px;
        }}
        .st-key-local_run_back_btn button {{
            background: {tokens["accent_subtle"]} !important;
            border: 1.5px solid {tokens["accent"]} !important;
            border-radius: 14px !important;
            color: {tokens["accent"]} !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            min-height: 52px !important;
            padding: 0 28px !important;
            width: 100% !important;
        }}
        .st-key-local_run_back_btn button:hover {{
            background: {tokens["accent_hover"]} !important;
            border-color: {tokens["accent_hover"]} !important;
            color: {tokens["accent_contrast"]} !important;
        }}
        .st-key-local_run_back_btn button *,
        .st-key-local_run_back_btn button:hover * {{
            color: inherit !important;
        }}
        @media (max-width: 760px) {{
            .local-run-steps {{
                justify-content: flex-start;
                overflow-x: auto;
                padding-bottom: 4px;
            }}
            .local-run-step-chip {{
                min-width: max-content;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _step_card(number: int, title: str, copy: str) -> str:
    return (
        '<div class="local-run-step-card">'
        '<div class="local-run-step-card-head">'
        f'<span class="local-run-step-num">{number}</span>'
        f'<div class="local-run-step-card-title">{html.escape(title)}</div>'
        '</div>'
        f'<div class="local-run-step-card-copy">{html.escape(copy)}</div>'
        '</div>'
    )


def _render_command_blocks() -> None:
    st.markdown(
        _step_card(
            1,
            "Prepare project",
            "Get the project files and open the folder before running it.",
        ),
        unsafe_allow_html=True,
    )
    st.code(
        "git clone https://github.com/granite-lifeline/granite-lifeline.git",
        language="bash",
    )
    st.code("cd granite-lifeline", language="bash")

    st.markdown(
        _step_card(
            2,
            "Install tools",
            "Set up everything the app needs on your computer.",
        ),
        unsafe_allow_html=True,
    )
    st.code("./setup.sh", language="bash")
    st.caption(r"Windows PowerShell: .\setup.ps1")

    st.markdown(
        _step_card(
            3,
            "Start Granite",
            "Start the local helper used to create the report text.",
        ),
        unsafe_allow_html=True,
    )
    st.code("ollama serve", language="bash")
    st.code("ollama pull granite4.1:8b", language="bash")

    st.markdown(
        _step_card(
            4,
            "Open dashboard",
            "Prepare the guide content and open the app in your browser.",
        ),
        unsafe_allow_html=True,
    )
    st.code(
        "uv run python -m report_layer.rag.knowledge_indexer\n"
        "uv run python -m report_layer.rag.symptom_knowledge_indexer",
        language="bash",
    )
    st.code("uv run streamlit run dashboard/app.py", language="bash")


def show_local_run_page() -> None:
    """Render the full How to Run Locally guide page."""
    dark_mode = st.session_state.get("dark_mode", False)
    tokens = THEME_TOKENS["dark" if dark_mode else "light"]

    _render_page_styles(tokens)

    st.markdown('<div class="local-run-shell">', unsafe_allow_html=True)

    nav_l, _gap = st.columns([3, 7])
    with nav_l:
        if st.button("← Back to Upload", key="local_run_back_btn"):
            st.session_state["page"] = "overview"
            st.rerun()

    st.markdown(
        page_title_html(
            "How to Run Locally",
            tokens,
            subtitle=(
                "Follow these steps to run the app on your computer and try "
                "the upload feature during a live demo."
            ),
            margin="16px 0 20px",
        )
        + '<div class="local-run-steps">'
        '<div class="local-run-step-chip"><span class="local-run-step-num">1'
        '</span><span class="local-run-step-lbl">Prepare project</span></div>'
        '<div class="local-run-step-chip"><span class="local-run-step-num">2'
        '</span><span class="local-run-step-lbl">Install tools</span></div>'
        '<div class="local-run-step-chip"><span class="local-run-step-num">3'
        '</span><span class="local-run-step-lbl">Start Granite</span></div>'
        '<div class="local-run-step-chip"><span class="local-run-step-num">4'
        '</span><span class="local-run-step-lbl">Open dashboard</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _, command_col, _ = st.columns([1, 2.6, 1], gap="large")
    with command_col:
        with st.container(key="local_run_commands_card"):
            st.markdown(
                '<div class="local-run-section-row">'
                '<div class="local-run-section-head">Copy commands</div>'
                '<div class="local-run-section-meta">Setup overview included'
                '</div>'
                '</div>'
                '<div class="local-run-note-card">'
                '<div class="local-run-note-title">'
                + lucide_icon("file-text", size=15, color=tokens["accent"])
                + '<span>Before running</span></div>'
                '<ul class="local-run-dot-list">'
                '<li>Make sure the required app tools are installed</li>'
                '<li>Keep the local report helper running</li>'
                '<li>Prepare the guide content before opening the app</li>'
                '</ul></div>',
                unsafe_allow_html=True,
            )
            _render_command_blocks()

    st.markdown('</div>', unsafe_allow_html=True)
    show_footer(dark_mode)
