"""
Granite Lifeline Dashboard

Entry point: sets up Streamlit config, session state, and routes between
the Overview and Detail pages.  All logic lives in submodules.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so that `shared`, `data_layer`, etc.
# are importable when Streamlit launches from any working directory.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st  # noqa: E402 (must come after sys.path patch)

from theme import apply_theme  # noqa: E402
from pages.overview import show_overview_page  # noqa: E402
from pages.detail import show_detail_page  # noqa: E402
from pages.local_run import show_local_run_page  # noqa: E402
from pages.what_if import show_what_if_page  # noqa: E402


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="Granite Lifeline",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    if "page" not in st.session_state:
        st.session_state["page"] = "overview"
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    apply_theme(st.session_state.get("dark_mode", False))

    if st.session_state["page"] == "detail":
        show_detail_page()
    elif st.session_state["page"] == "local_run":
        show_local_run_page()
    elif st.session_state["page"] == "what_if":
        show_what_if_page()
    else:
        show_overview_page()


if __name__ == "__main__":
    main()
