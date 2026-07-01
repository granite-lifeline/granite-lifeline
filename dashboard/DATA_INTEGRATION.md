# Dashboard Data Integration

## Overview

The dashboard now loads real Report Layer data instead of hardcoded mock data.

## Data Flow

```
Report Layer Output (JSON)
    ↓
data_loader.py (load_dashboard_data)
    ↓
REPORT_DATA (component-keyed dictionary)
    ↓
Dashboard UI (app.py)
```

## Files

### `data_loader.py`
Data loading module with three main functions:

- `load_report_data(file_path)`: Load JSON file and return list of reports
- `convert_to_component_dict(report_list)`: Convert list to component-keyed dict
- `load_dashboard_data(file_path)`: Combined function for dashboard use

### `tests/ui_required_data.json`
Complete Report Layer output example with all INTERFACE.md v0.2 fields:

- 3 components: cooling_system_stress, air_intake_maf_anomaly, accelerator_pedal_sensor
- All required fields: timestamp, risk_score, risk_level, component, prediction_confidence, key_signals, risk_history, anomaly_description, possible_cause, recommended_action

### `tests/ui_required_data.md`
Documentation of required data structure and field usage.

## Usage

### In Dashboard (app.py)

```python
from data_loader import load_dashboard_data

# Load report data
REPORT_DATA = load_dashboard_data("dashboard/tests/ui_required_data.json")

# Use as component dictionary
cooling_data = REPORT_DATA["cooling_system_stress"]
print(cooling_data["risk_level"])  # "High"
```

### Standalone Testing

```python
from dashboard.data_loader import load_dashboard_data

# Load data
data = load_dashboard_data("dashboard/tests/ui_required_data.json")

# Access components
print(f"Loaded {len(data)} components")
print("Components:", list(data.keys()))
```

## Data Structure

Each component report must include:

| Field | Type | Description |
|-------|------|-------------|
| timestamp | string | ISO 8601 timestamp |
| risk_score | float | 0.0-1.0 risk score |
| risk_level | string | "Low", "Medium", or "High" |
| component | string | Component identifier |
| prediction_confidence | float | 0.0-1.0 confidence |
| key_signals | array | Signal details with feature, value, unit, reference_range |
| risk_history | array | Historical risk scores with timestamp and risk_score |
| anomaly_description | string | Granite LLM generated description |
| possible_cause | string | Granite LLM generated cause |
| recommended_action | array | Granite LLM generated action items |

See `docs/INTERFACE.md` Section 3 for complete field definitions.

## Fallback Behavior

If data loading fails, the dashboard falls back to `MOCK_DATA_FALLBACK`:

```python
try:
    REPORT_DATA = load_dashboard_data("dashboard/tests/ui_required_data.json")
except Exception as e:
    st.error(f"Failed to load report data: {e}")
    REPORT_DATA = {}

# Use REPORT_DATA if available, otherwise fallback
MOCK_DATA = REPORT_DATA if REPORT_DATA else MOCK_DATA_FALLBACK
```

## Testing

### Manual Test
```bash
cd /Users/charlotteyu/Desktop/IBM/granite-lifeline
python -c "from dashboard.data_loader import load_dashboard_data; \
           data = load_dashboard_data('dashboard/tests/ui_required_data.json'); \
           print(f'Loaded {len(data)} components')"
```

Expected output:
```
Loaded 3 components
```

### Unit Tests
```bash
python -m pytest tests/test_data_loader.py -v
```

Tests cover:
- Successful data loading
- File not found error handling
- Component dictionary conversion
- Missing component field handling
- INTERFACE.md compliance validation

## Integration with Report Layer

When Report Layer implements the report generation pipeline:

1. Report Layer generates JSON output with all required fields
2. Save output to a known location (e.g., `data/processed/latest_report.json`)
3. Update dashboard to load from that location:
   ```python
   REPORT_DATA = load_dashboard_data("data/processed/latest_report.json")
   ```

## Related Files

- `docs/INTERFACE.md` - Data contract specification
- `shared/interface_models.py` - Pydantic models for type safety
- `dashboard/tests/ui_required_data.md` - Field usage documentation
- `tests/test_data_loader.py` - Unit tests