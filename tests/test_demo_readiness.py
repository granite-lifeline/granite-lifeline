"""GL-384 demo readiness checks for Dashboard / Report Layer."""

from pathlib import Path

from dashboard.anomaly_display import COMPONENT_DISPLAY_NAMES
from dashboard.data_loader import load_report_data
from dashboard.export_helper import (
    CSV_COLUMNS,
    DEFAULT_EXPORT_SECTIONS,
    build_export_data,
)
from shared.anomaly_mapping import GROUND_KNOWLEDGE_ANOMALY_TYPES


DEMO_DATA_PATH = Path("dashboard/tests/ui_required_data.json")
DEMO_CHECK_PATH = Path("dashboard/tests/demo_readiness_check.md")
DASHBOARD_README_PATH = Path("dashboard/README.md")


def _demo_reports() -> list[dict]:
    return load_report_data(str(DEMO_DATA_PATH))


def test_demo_data_covers_five_current_components():
    """Demo data should match the current INTERFACE.md component set."""
    reports = _demo_reports()
    components = {report["component"] for report in reports}

    assert len(reports) == 5
    assert components == set(GROUND_KNOWLEDGE_ANOMALY_TYPES)
    assert "electronic_throttle_tracking_fault" not in components
    assert "idle_speed_control_or_surge_degradation" not in components


def test_demo_components_have_owner_facing_content():
    """Each demo card/detail page has enough text for a real walkthrough."""
    reports = _demo_reports()

    for report in reports:
        component = report["component"]
        assert COMPONENT_DISPLAY_NAMES[component] != component
        assert report["risk_level"] in {"Low", "Medium", "High"}
        assert 0 <= report["risk_score"] <= 1
        assert report["key_signals"]
        assert report["risk_history"]
        assert report["anomaly_description"]
        assert report["possible_cause"]
        assert report["recommended_action"]


def test_demo_data_includes_failure_prediction_example():
    """At least one demo detail page should show the new prediction UI."""
    reports = _demo_reports()

    assert any(
        report.get("estimated_failure_probability") is not None
        and report.get("estimated_cycles_to_failure") is not None
        and report.get("notes")
        for report in reports
    )


def test_demo_export_defaults_are_ready_for_one_click_download():
    """Default export should include the core report and CSV fields."""
    export_data = build_export_data(_demo_reports()[0])

    assert export_data["sections"] == list(DEFAULT_EXPORT_SECTIONS)
    assert list(CSV_COLUMNS) == [
        "feature",
        "value",
        "unit",
        "reference_range",
        "status",
    ]
    assert export_data["summary"]["component_name"] == "Cooling System"
    assert export_data["key_signals"]
    assert export_data["diagnostic_report"]["recommended_action"]


def test_demo_readiness_checklist_documents_run_route_and_limits():
    """The GL-384 checklist should be usable before a live demo."""
    src = DEMO_CHECK_PATH.read_text(encoding="utf-8")

    for required_text in [
        "streamlit run dashboard/app.py --server.port 8502",
        "tests/test_demo_readiness.py",
        "Explore with demo data",
        "What-If",
        "PDF / CSV",
        "CSV upload",
        "percentage progress ring",
        "Analyzing data...",
        "five current anomaly types",
        "local Ollama",
        "placeholder scores",
    ]:
        assert required_text in src


def test_demo_readiness_checklist_covers_csv_loading_recovery():
    """GL-388: live CSV loading demo should cover success and recovery."""
    src = DEMO_CHECK_PATH.read_text(encoding="utf-8")

    for required_text in [
        "CSV Loading State Demo Checklist",
        "`Run Analysis` clicked",
        "`Analysing...`",
        "no duplicate file-row `Upload` button",
        "Pipeline succeeds",
        "Pipeline fails or times out",
        "Browser refresh during loading",
        "stale loading state is cleared",
        "CSV loading regression tests",
    ]:
        assert required_text in src


def test_dashboard_readme_uses_current_demo_readiness_language():
    """README should not send the team into the demo with stale wording."""
    src = DASHBOARD_README_PATH.read_text(encoding="utf-8")

    assert "Five-Type Component Display Mapping" in src
    assert "CSV Analysis Loading State" in src
    assert "GL-415/416" in src
    assert "Demo Readiness Check" in src
    assert "percentage progress ring" in src
    assert "tests/test_demo_readiness.py" in src
    assert "INTERFACE.md v0.7" not in src
    assert "Six-Type" not in src
    assert "6 current anomaly types" not in src
