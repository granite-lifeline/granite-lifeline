"""
Project-level pytest configuration.

Provides a session-scoped autouse fixture that patches
report_layer.pipeline.report_generator.generate_report with a fast stub
for all test modules except test_gl133_dashboard_real_data.py.

This keeps the existing test suite fast (no Ollama calls) while
GL-133 tests are free to exercise the real pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

# Ensure project root is on sys.path so all imports resolve correctly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Modules allowed to call the real Ollama pipeline
# ---------------------------------------------------------------------------
_REAL_PIPELINE_MODULES = {"test_gl133_dashboard_real_data"}


def _stub_generate_report(model_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fast stub for report_generator.generate_report used in unit tests.

    Returns a minimal ReportLayerOutput-compatible dict built from the
    ModelLayerOutput pass-through fields.  Never calls Ollama.
    """
    return {
        "timestamp": model_output.get("timestamp", ""),
        "risk_score": model_output.get("risk_score", 0.0),
        "risk_level": model_output.get("risk_level"),
        "component": model_output.get("component", ""),
        "prediction_confidence": model_output.get(
            "prediction_confidence", 0.0
        ),
        "key_signals": model_output.get("key_signals", []),
        "estimated_cycles_to_failure": model_output.get(
            "estimated_cycles_to_failure"
        ),
        "estimated_failure_probability": model_output.get(
            "estimated_failure_probability"
        ),
        "notes": model_output.get("notes", []),
        "risk_history": None,
        "anomaly_description": "[stub] anomaly description",
        "possible_cause": "[stub] possible cause",
        "recommended_action": ["[stub] check the vehicle"],
        "report_generation_success": True,
    }


@pytest.fixture(autouse=True)
def _patch_report_generator(request):
    """
    Auto-patch generate_report for every test except GL-133 real-data tests.

    GL-133 tests (test_gl133_dashboard_real_data.py) are explicitly
    excluded so they exercise the real Ollama pipeline.
    """
    module_name = Path(request.fspath).stem
    if module_name in _REAL_PIPELINE_MODULES:
        # Let GL-133 tests use the real pipeline — no patch.
        yield
        return

    # For all other tests, replace generate_report with the fast stub so
    # load_dashboard_data() resolves instantly without network calls.
    with patch(
        "report_layer.pipeline.report_generator.generate_report",
        side_effect=_stub_generate_report,
    ):
        yield
