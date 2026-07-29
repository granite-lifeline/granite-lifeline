"""
Project-level pytest configuration.

Provides an autouse fixture that patches
report_layer.pipeline.report_generator.generate_report with a fast
stub for every test module except test_gl133_dashboard_real_data.py.

This keeps the existing test suite fast (no Ollama calls) while
GL-133 tests are free to exercise the real pipeline.

The fixture is safe to use even when report_generator cannot be
imported (e.g. CI without the `requests` package) because it uses
create=True and catches ImportError/AttributeError during setup.
"""

from __future__ import annotations

import importlib
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

_PATCH_TARGET = (
    "report_layer.pipeline.report_generator.generate_report"
)


def _stub_generate_report(
    model_output: Dict[str, Any],
    risk_history: Any = None,
) -> Dict[str, Any]:
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
        "risk_history": risk_history,
        "anomaly_description": "[stub] anomaly description",
        "possible_cause": "[stub] possible cause",
        "recommended_action": ["[stub] check the vehicle"],
    }


def _try_import_report_generator() -> bool:
    """
    Attempt to import report_generator.  Return True on success.

    Importing may fail in CI where optional dependencies (e.g.
    `requests`) are not installed.  In that case the module is simply
    not available and we skip the patch.
    """
    try:
        importlib.import_module(
            "report_layer.pipeline.report_generator"
        )
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _patch_report_generator(request):
    """
    Auto-patch generate_report for every test except GL-133 tests.

    - For GL-133 (test_gl133_dashboard_real_data.py): no patch, the
      real pipeline is used.
    - For all other tests: replace generate_report with a fast stub
      so load_dashboard_data() resolves instantly without network
      calls.
    - If report_generator cannot be imported (e.g. missing `requests`
      in CI), the fixture yields without patching — the data_loader's
      own ImportError handling will fall back to mock data.
    """
    module_name = Path(request.fspath).stem

    # Let GL-133 tests use the real pipeline.
    if module_name in _REAL_PIPELINE_MODULES:
        yield
        return

    # Try to import the module; if unavailable (CI), skip patching —
    # data_loader.load_real_data() will catch the ImportError itself
    # and fall back to mock data transparently.
    if not _try_import_report_generator():
        yield
        return

    with patch(
        _PATCH_TARGET,
        side_effect=_stub_generate_report,
    ):
        yield
