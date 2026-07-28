"""Streamlit Cloud entry point for Granite Lifeline.

The dashboard implementation lives in ``dashboard/app.py``.  Streamlit
Community Cloud commonly expects a root-level ``streamlit_app.py``, so
this thin wrapper keeps the hosted demo and local entry point aligned.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

for path in (PROJECT_ROOT, DASHBOARD_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dashboard.app import main  # noqa: E402


if __name__ == "__main__":
    main()
