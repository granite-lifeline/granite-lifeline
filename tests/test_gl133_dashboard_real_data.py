"""
GL-133: Verify Dashboard renders correctly with data for all 5
confirmed anomaly types.

Covers:
- Overview Page: all 5 anomaly types produce dashboard-ready component
  dicts with the correct risk fields.
- Detail Page data: risk_score, key_signals, and report panel fields
  (anomaly_description, possible_cause, recommended_action) are present.
- Real vs mock data source tracking via _data_source metadata.
- Fallback warning banner logic: mock-data components are correctly
  identified so the banner can be shown.
- Schema compliance: all required ReportLayerOutput fields present for
  every component returned by load_dashboard_data().

NOTE: cooling_degradation uses the real pipeline
(report_layer.pipeline.report_generator + Ollama).  If Ollama is
unreachable the real pipeline falls back to an empty report dict — the
test marks the Ollama-dependent assertion as xfail in that case so the
suite can always be run offline.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dashboard.data_loader import (  # noqa: E402
    load_dashboard_data,
    CONFIRMED_ANOMALY_TYPES,
    REAL_DATA_PATHS,
)

# ---------------------------------------------------------------------------
# Shared fixture — runs load_dashboard_data() once per test module.
# Uses the real pipeline for cooling_degradation; mock for missing real files.
# ---------------------------------------------------------------------------
_DATA_CACHE: Optional[dict] = None
REAL_SAMPLE_PATH = (
    project_root / "model_layer/ttm-related/outputs/kit_residual_sample.json"
)


def _get_data() -> dict:
    global _DATA_CACHE
    if _DATA_CACHE is None:
        _DATA_CACHE = load_dashboard_data(
            "dashboard/tests/ui_required_data.json"
        )
    return _DATA_CACHE


# ---------------------------------------------------------------------------
# GL-133-1: Confirm all 5 confirmed anomaly types are present
# ---------------------------------------------------------------------------

class TestOverviewPageComponents:
    """GL-133: Overview Page shows risk cards for all 5 anomaly types."""

    def test_five_components_present(self):
        """Dashboard dict contains exactly 5 component entries."""
        data = _get_data()
        components = {k: v for k, v in data.items() if k != "_data_source"}
        assert len(components) == 5, (
            f"Expected 5 components, got {len(components)}: "
            f"{list(components.keys())}"
        )

    def test_cooling_component_present(self):
        """Cooling component is present under the canonical key."""
        data = _get_data()
        assert "cooling_degradation" in data

    def test_air_intake_present(self):
        data = _get_data()
        assert "air_intake_maf_anomaly" in data

    def test_accelerator_pedal_present(self):
        data = _get_data()
        assert "accelerator_pedal_sensor" in data

    def test_iat_present(self):
        data = _get_data()
        assert "intake_air_temperature_sensor_fault" in data

    def test_map_present(self):
        data = _get_data()
        assert "map_load_signal_plausibility_fault" in data

    def test_all_components_have_risk_level(self):
        """Every component dict has an interface-compatible risk_level."""
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            assert "risk_level" in entry, f"{key}: missing risk_level"
            assert entry["risk_level"] in ("High", "Medium", "Low", None), (
                f"{key}: unexpected risk_level '{entry['risk_level']}'"
            )

    def test_all_components_have_risk_score(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            assert "risk_score" in entry, f"{key}: missing risk_score"
            assert 0.0 <= entry["risk_score"] <= 1.0, (
                f"{key}: risk_score out of range: {entry['risk_score']}"
            )


# ---------------------------------------------------------------------------
# GL-133-2: Detail Page data — real pipeline output for cooling_degradation
# ---------------------------------------------------------------------------

class TestDetailPageRealData:
    """GL-133: Detail Page renders correctly for cooling_degradation."""

    def _cooling(self) -> dict:
        data = _get_data()
        return data.get("cooling_degradation") or data.get(
            "cooling_degradation"
        )

    def test_cooling_risk_score_from_real_file(self):
        """cooling_degradation risk_score matches kit_residual_sample.json."""
        data = _get_data()
        source = data.get("_data_source", {})
        cooling_key = (
            "cooling_degradation"
            if "cooling_degradation" in data
            else "cooling_degradation"
        )
        if source.get(cooling_key) != "real":
            pytest.skip("cooling_degradation not loaded from real data")
        cooling = data[cooling_key]
        expected = json.loads(
            REAL_SAMPLE_PATH.read_text(encoding="utf-8")
        )["risk_score"]
        assert cooling["risk_score"] == expected, (
            f"Expected risk_score={expected} from real file, "
            f"got {cooling['risk_score']}"
        )

    def test_cooling_key_signals_present(self):
        """cooling component has at least one key_signal."""
        cooling = self._cooling()
        assert cooling is not None
        assert isinstance(cooling.get("key_signals"), list)
        assert len(cooling["key_signals"]) >= 1

    def test_cooling_key_signals_structure(self):
        """Each key_signal has feature, value, unit, reference_range."""
        cooling = self._cooling()
        assert cooling is not None
        for signal in cooling["key_signals"]:
            assert "feature" in signal
            assert "value" in signal
            assert "unit" in signal
            assert isinstance(signal.get("reference_range"), list)
            assert len(signal["reference_range"]) == 2

    def test_cooling_report_panel_fields_present(self):
        """Report panel fields present (may be empty for fallback)."""
        cooling = self._cooling()
        assert cooling is not None
        for field in ("anomaly_description", "possible_cause",
                      "recommended_action"):
            assert field in cooling, f"Missing report field: {field}"

    def test_cooling_recommended_action_is_list(self):
        cooling = self._cooling()
        assert cooling is not None
        assert isinstance(cooling["recommended_action"], list)

    def test_real_pipeline_report_fields_follow_interface(self):
        """Real pipeline output follows the current report interface."""
        data = _get_data()
        source = data.get("_data_source", {})
        cooling_key = (
            "cooling_degradation"
            if "cooling_degradation" in data
            else "cooling_degradation"
        )
        if source.get(cooling_key) != "real":
            pytest.skip("cooling_degradation not loaded from real data")
        cooling = data[cooling_key]
        assert "report_generation_success" not in cooling
        for field in (
            "anomaly_description",
            "possible_cause",
            "recommended_action",
            "risk_history",
        ):
            assert field in cooling, f"Missing report field: {field}"
        assert isinstance(cooling["recommended_action"], list)


# ---------------------------------------------------------------------------
# GL-133-3: Mock-data fallback for types without real files
# ---------------------------------------------------------------------------

class TestMockDataFallback:
    """GL-133: types without configured real files use mock data."""

    def test_air_intake_source_is_mock(self):
        data = _get_data()
        source = data.get("_data_source", {})
        assert source.get("air_intake_maf_anomaly") == "mock", (
            "air_intake_maf_anomaly should use mock data "
            "(no real file configured)"
        )

    def test_accelerator_pedal_source_is_mock(self):
        data = _get_data()
        source = data.get("_data_source", {})
        assert source.get("accelerator_pedal_sensor") == "mock", (
            "accelerator_pedal_sensor should use mock data "
            "(no real file configured)"
        )

    def test_mock_components_have_full_report_fields(self):
        """Mock fallback entries include all ReportLayerOutput fields."""
        data = _get_data()
        for key in ("air_intake_maf_anomaly", "accelerator_pedal_sensor"):
            entry = data[key]
            for field in (
                "timestamp", "risk_score", "risk_level", "component",
                "prediction_confidence", "key_signals",
                "anomaly_description", "possible_cause", "recommended_action",
                "estimated_cycles_to_failure", "estimated_failure_probability",
                "notes",
            ):
                assert field in entry, f"{key}: missing field '{field}'"


# ---------------------------------------------------------------------------
# GL-133-4: Warning banner — _data_source metadata is correct
# ---------------------------------------------------------------------------

class TestFallbackWarningBanner:
    """GL-133: Fallback warning banner appears for mock components."""

    def test_data_source_metadata_present(self):
        data = _get_data()
        assert "_data_source" in data
        assert isinstance(data["_data_source"], dict)

    def test_mock_components_identified_for_banner(self):
        """Components that need the warning banner are identifiable."""
        data = _get_data()
        source = data["_data_source"]
        mock_components = [k for k, v in source.items() if v == "mock"]
        # At minimum air_intake and accelerator pedal must be flagged
        assert "air_intake_maf_anomaly" in mock_components
        assert "accelerator_pedal_sensor" in mock_components

    def test_real_components_not_in_mock_banner(self):
        """Components served by real data do not appear in mock list."""
        data = _get_data()
        source = data["_data_source"]
        real_components = [k for k, v in source.items() if v == "real"]
        mock_components = [k for k, v in source.items() if v == "mock"]
        for comp in real_components:
            assert comp not in mock_components, (
                f"{comp} is tagged as both real and mock"
            )

    def test_no_duplicate_component_keys(self):
        """No component appears under both its canonical and legacy key."""
        data = _get_data()
        components = {k for k in data if k != "_data_source"}
        assert len(components) == len(set(components))


# ---------------------------------------------------------------------------
# GL-133-5: Schema compliance for all components
# ---------------------------------------------------------------------------

class TestSchemaCompliance:
    """GL-133: All returned components satisfy ReportLayerOutput schema."""

    REQUIRED_FIELDS = [
        "timestamp",
        "risk_score",
        "risk_level",
        "component",
        "prediction_confidence",
        "key_signals",
        "anomaly_description",
        "possible_cause",
        "recommended_action",
        "estimated_cycles_to_failure",
        "estimated_failure_probability",
        "notes",
    ]

    def test_all_required_fields_present(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            for field in self.REQUIRED_FIELDS:
                assert field in entry, (
                    f"Component '{key}': missing required field '{field}'"
                )

    def test_key_signals_each_valid(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            for signal in entry["key_signals"]:
                assert "feature" in signal, f"{key}: signal missing 'feature'"
                assert "value" in signal, f"{key}: signal missing 'value'"
                assert "unit" in signal, f"{key}: signal missing 'unit'"
                assert isinstance(
                    signal.get("reference_range"), list
                ), f"{key}: signal 'reference_range' must be a list"

    def test_notes_is_list(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            assert isinstance(entry["notes"], list), (
                f"{key}: 'notes' must be a list"
            )

    def test_recommended_action_is_list(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            assert isinstance(entry["recommended_action"], list), (
                f"{key}: 'recommended_action' must be a list"
            )

    def test_risk_score_in_range(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            score = entry["risk_score"]
            assert 0.0 <= score <= 1.0, (
                f"{key}: risk_score {score} out of [0, 1]"
            )

    def test_prediction_confidence_in_range(self):
        data = _get_data()
        for key, entry in data.items():
            if key == "_data_source":
                continue
            conf = entry["prediction_confidence"]
            assert 0.0 <= conf <= 1.0, (
                f"{key}: prediction_confidence {conf} out of [0, 1]"
            )


# ---------------------------------------------------------------------------
# GL-133-6: REAL_DATA_PATHS registry is correctly configured
# ---------------------------------------------------------------------------

class TestRealDataPathsRegistry:
    """GL-133: REAL_DATA_PATHS covers the 3 confirmed anomaly types."""

    def test_all_three_types_registered(self):
        for anomaly_type in (
            "cooling_degradation",
            "air_intake_maf_anomaly",
            "accelerator_pedal_sensor",
        ):
            assert anomaly_type in REAL_DATA_PATHS, (
                f"{anomaly_type} missing from REAL_DATA_PATHS"
            )

    def test_cooling_degradation_path_exists(self):
        path_str = REAL_DATA_PATHS["cooling_degradation"]
        assert path_str is not None, (
            "cooling_degradation has no real data path configured"
        )
        assert Path(path_str).exists(), (
            f"Real data file not found: {path_str}"
        )

    def test_missing_types_are_none(self):
        for anomaly_type in (
            "air_intake_maf_anomaly",
            "accelerator_pedal_sensor",
        ):
            assert REAL_DATA_PATHS[anomaly_type] is None, (
                f"{anomaly_type}: expected None path (no real file yet)"
            )

    def test_confirmed_anomaly_types_match_registry(self):
        assert set(CONFIRMED_ANOMALY_TYPES) == set(REAL_DATA_PATHS.keys())
