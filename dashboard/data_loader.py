"""
Data loader for dashboard.

Loads Report Layer output data for dashboard display.
Supports real ModelLayerOutput JSON files (GL-131) with graceful
fallback to mock test data when real data is unavailable (GL-132).
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GL-131: Mapping of anomaly_type → real ModelLayerOutput JSON file path.
# Set to None for anomaly types that do not yet have a real output file.
# ---------------------------------------------------------------------------
REAL_DATA_PATHS: Dict[str, Optional[str]] = {
    "cooling_degradation": (
        "model_layer/ttm-related/outputs/kit_residual_sample.json"
    ),
    "air_intake_maf_anomaly": None,
    "accelerator_pedal_sensor": None,
}

# Canonical mock-data fallback file (ReportLayerOutput format)
_MOCK_DATA_FILE = "dashboard/tests/ui_required_data.json"

# The 3 confirmed anomaly types for GL-129
CONFIRMED_ANOMALY_TYPES = list(REAL_DATA_PATHS.keys())


def load_report_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load Report Layer output data from JSON file.

    Args:
        file_path: Path to JSON file containing report data

    Returns:
        List of report objects, each representing one monitored component

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Report data file not found: {file_path}"
        )

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate data is a list
    if not isinstance(data, list):
        raise ValueError(
            "Report data must be a list of component reports"
        )

    return data


def convert_to_component_dict(
    report_list: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Convert report list to component-keyed dictionary for dashboard use.

    Args:
        report_list: List of report objects from Report Layer

    Returns:
        Dictionary keyed by component name, values are report objects
    """
    component_dict = {}

    for report in report_list:
        component = report.get("component")
        if component:
            component_dict[component] = report

    return component_dict


def load_real_data(anomaly_type: str) -> Optional[Dict[str, Any]]:
    """
    GL-131: Attempt to load real ModelLayerOutput for an anomaly type,
    then call report_generator.generate_report() to produce
    ReportLayerOutput for the dashboard.

    Returns the ReportLayerOutput dict on success, or None when:
    - No real file is mapped for this anomaly_type
    - The file is missing or contains invalid JSON
    - The JSON fails ModelLayerOutput schema validation
    - report_generator is not yet available (ImportError)
    - report_generator.generate_report() raises any exception

    Args:
        anomaly_type: One of the CONFIRMED_ANOMALY_TYPES

    Returns:
        ReportLayerOutput dict ready for dashboard, or None
    """
    file_path = REAL_DATA_PATHS.get(anomaly_type)
    if file_path is None:
        logger.info(
            "[GL-131] No real data path configured for '%s' — "
            "will use mock data.",
            anomaly_type,
        )
        return None

    path = Path(file_path)
    if not path.exists():
        logger.warning(
            "[GL-131] Real data file not found for '%s': %s — "
            "will use mock data.",
            anomaly_type,
            file_path,
        )
        return None

    # Read and parse the JSON file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "[GL-131] Failed to read real data file '%s': %s — "
            "will use mock data.",
            file_path,
            exc,
        )
        return None

    # Validate against ModelLayerOutput schema
    try:
        import sys as _sys
        _sys.path.insert(0, ".")
        from shared.interface_models import ModelLayerOutput
        ModelLayerOutput(**raw)
    except ImportError:
        logger.warning(
            "[GL-131] shared.interface_models not available — "
            "skipping schema validation for '%s'.",
            anomaly_type,
        )
    except Exception as exc:
        logger.warning(
            "[GL-131] Real data file '%s' failed schema validation: %s — "
            "will use mock data.",
            file_path,
            exc,
        )
        return None

    # Attempt to generate a ReportLayerOutput via report_generator
    try:
        from report_layer.pipeline.report_generator import generate_report
        report = generate_report(raw)
        logger.info(
            "[GL-131] Loaded real data for '%s' from %s.",
            anomaly_type,
            file_path,
        )
        return report
    except ImportError:
        logger.warning(
            "[GL-131] report_layer.pipeline.report_generator is not yet "
            "available — will use mock data for '%s'.",
            anomaly_type,
        )
        return None
    except Exception as exc:
        logger.warning(
            "[GL-131] report_generator.generate_report() failed for '%s': "
            "%s — will use mock data.",
            anomaly_type,
            exc,
        )
        return None


def load_dashboard_data(
    file_path: str = "dashboard/tests/ui_required_data.json",
) -> Dict[str, Any]:
    """
    GL-131/GL-132: Load and prepare report data for dashboard display.

    For each confirmed anomaly type, first attempts to load real
    ModelLayerOutput data and run it through report_generator.  Falls
    back to the mock ReportLayerOutput from *file_path* for any type
    where real data is unavailable.

    Args:
        file_path: Path to the mock ReportLayerOutput JSON file used
                   as fallback.  Defaults to the dashboard test data.

    Returns:
        Dictionary keyed by component name, ready for dashboard use.
        The special key ``"_data_source"`` maps each component name to
        either ``"real"`` or ``"mock"`` so callers can show a warning
        banner when fallback is active.

    Example:
        >>> data = load_dashboard_data()
        >>> cooling_data = data["cooling_degradation"]
        >>> print(data["_data_source"]["cooling_degradation"])
        'real'  # or 'mock'
    """
    # Load the full mock dataset as the baseline fallback
    mock_list = load_report_data(file_path)
    mock_by_component = convert_to_component_dict(mock_list)

    result: Dict[str, Any] = {}
    data_source: Dict[str, str] = {}

    for anomaly_type in CONFIRMED_ANOMALY_TYPES:
        real_report = load_real_data(anomaly_type)

        if real_report is not None:
            component_key = real_report.get("component", anomaly_type)
            result[component_key] = real_report
            data_source[component_key] = "real"
            logger.info(
                "[GL-131] Using real data for component '%s'.",
                component_key,
            )
        else:
            # Find the matching mock entry.
            # Try exact key first, then resolve legacy aliases so that
            # e.g. "cooling_degradation" picks up the mock entry stored
            # under the old key "cooling_system_stress".
            try:
                from shared.anomaly_mapping import LEGACY_COMPONENT_ALIASES
                _alias_reverse = {
                    v: k for k, v in LEGACY_COMPONENT_ALIASES.items()
                }
            except ImportError:
                _alias_reverse = {}

            mock_entry = mock_by_component.get(anomaly_type)
            if mock_entry is None:
                # Check if there is a legacy key for this anomaly_type
                legacy_key = _alias_reverse.get(anomaly_type)
                if legacy_key:
                    mock_entry = mock_by_component.get(legacy_key)
            if mock_entry is None:
                # Last resort: linear scan by component field value
                for entry in mock_list:
                    if entry.get("component") == anomaly_type:
                        mock_entry = entry
                        break

            if mock_entry is not None:
                component_key = mock_entry.get("component", anomaly_type)
                result[component_key] = mock_entry
                data_source[component_key] = "mock"
                logger.info(
                    "[GL-132] Using mock data for component '%s' "
                    "(real data not available).",
                    component_key,
                )
            else:
                logger.warning(
                    "[GL-132] No mock data found for anomaly type '%s' — "
                    "component will be absent from dashboard.",
                    anomaly_type,
                )

    # Preserve extra components from the mock file that are not already
    # covered — but skip legacy alias keys whose canonical counterpart was
    # already loaded as real data (e.g. don't add "cooling_system_stress"
    # when "cooling_degradation" was already placed by real data).
    try:
        from shared.anomaly_mapping import LEGACY_COMPONENT_ALIASES
    except ImportError:
        LEGACY_COMPONENT_ALIASES = {}

    for component_key, entry in mock_by_component.items():
        if component_key in result:
            continue
        # If this key is a legacy alias whose canonical form is already
        # present, skip it to avoid duplicate entries.
        canonical = LEGACY_COMPONENT_ALIASES.get(component_key)
        if canonical and canonical in result:
            continue
        result[component_key] = entry
        data_source[component_key] = "mock"

    result["_data_source"] = data_source
    return result
