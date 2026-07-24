# Dashboard

**Owner:** Report Team  
**Status:** Active Development  
**Last Updated:** 2026-07-13

---

## Overview

The Dashboard is the user-facing component of Granite Lifeline, providing vehicle owners with an intuitive web interface to monitor vehicle health, understand risk levels, and track component status over time.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Key Features

- **Health Overview**: At-a-glance view of all monitored components with risk-based prioritization
- **Component Details**: Drill-down pages with metrics and interactive trend charts
- **Risk Score Trends**: Plotly-powered visualizations showing risk progression over time
- **Theme Support**: Light/dark mode toggle with an IBM Carbon-inspired "Pro" design
- **Interface v0.7 Data Loading**: Loads ReportLayerOutput-shaped JSON, including failure prediction fields and Model Layer notes
- **Responsive Design**: Optimized for desktop viewing (mobile optimization planned)

---

## Current Implementation Status

### [COMPLETED]

| Feature | Ticket | Description |
|---------|--------|-------------|
| Overview Page | GL-40 | Component cards with risk levels and scores |
| Component Detail Page | GL-41 | Metrics display with back navigation |
| Risk Score Trend Chart | GL-42 | Interactive Plotly line chart with theme support |
| Theme Toggle | GL-40 | Light/dark mode with Pro (IBM Carbon-inspired) aesthetics |
| Team Footer | - | Team attribution footer |
| Diagnostic Report Display | GL-41 | anomaly_description, possible_cause, recommended_action cards |
| Key Signals Table | GL-41 | ABNORMAL/NORMAL signal rows with reference range |
| Report Layer Integration | GL-41 | Loads ReportLayerOutput via data_loader.py; MOCK_DATA_FALLBACK retained |
| Failure Prediction Data Support | GL-198 | Loads estimated_failure_probability, estimated_cycles_to_failure, notes from INTERFACE.md v0.7 test data |
| Failure Prediction UI Display | GL-278/GL-280 | Shows failure probability card and Data Quality Notes on the detail page |
| Six-Type Component Display Mapping | GL-273 | Maps all 6 current anomaly types to owner-friendly display names; legacy cooling_system_stress alias retained |

### [PLANNED]

| Feature | Priority | Description |
|---------|----------|-------------|
| Mobile Optimization | P1 | Responsive design for mobile devices |
| PDF / CSV Export | P2 | Download detail-page diagnostic report and key signals |
| 3D Component Visualization | P3 | Interactive 3D car model with component highlighting |

---

## Architecture

### Data Flow

```
ReportLayerOutput (from Report Layer)
    ↓
Dashboard consumes:
    - timestamp, risk_score, risk_level
    - component, prediction_confidence
    - key_signals
    - anomaly_description, possible_cause, recommended_action
    - risk_history (for trend chart)
    - estimated_failure_probability, estimated_cycles_to_failure
    - notes
    ↓
Renders:
    - Overview Page (component cards)
    - Detail Page (metrics + trend chart + signals + report)
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Streamlit | 1.x | Web app framework |
| Visualization | Plotly | 5.x | Interactive charts |
| Styling | Custom CSS | - | Theme implementation |
| Fonts | Google Fonts | - | IBM Plex Sans, IBM Plex Mono, Noto Sans SC |

---

## Directory Structure

```
dashboard/
├── app.py                  # Main Streamlit application
├── anomaly_display.py      # Component/signal display name mappings
├── data_loader.py          # JSON → component-keyed dict loader
├── export_helper.py        # GL-344 filtered export data helper
├── EXPORT_REPORT_PLAN.md   # GL-343 export entry and field checklist
├── assets/                 # Static assets
├── DATA_INTEGRATION.md     # Data contract and field documentation
├── tests/
│   └── ui_required_data.json   # INTERFACE.md v0.7-shaped sample data
└── README.md               # This file
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Virtual environment activated (see root README.md)
- Dependencies installed from `requirements.txt`

### Installation

From the project root directory:

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### Running the Dashboard

```bash
# From project root
streamlit run dashboard/app.py

# Or from dashboard directory
cd dashboard
streamlit run app.py
```

The dashboard will open automatically in your default browser at `http://localhost:8501`.

### Development Mode

For development with auto-reload:

```bash
streamlit run dashboard/app.py --server.runOnSave true
```

---

## User Interface

### Overview Page

**Purpose:** Provide at-a-glance vehicle health status across all monitored components.

**Features:**
- **Health Summary Banner**: Alert if any component requires urgent attention
- **Component Cards**: 3-column grid showing:
  - Component name (e.g., "Cooling System")
  - Risk level badge (High/Medium/Low with color coding)
  - Current risk score percentage
- **Risk-Based Sorting**: High-risk components appear first
- **Theme Toggle**: Sun/moon icon in top-right corner
- **Risk Visualization**: Animated progress ring per card
- **Navigation**: "View Details" button on each card
- **Footer**: Multi-section footer with repository/blog links and
  team attribution

**Design Principles:**
- Non-technical language (no raw anomaly IDs in owner-facing labels)
- Color-coded risk levels (red/orange/green)
- Large, readable fonts (IBM Plex Sans family)
- Minimal cognitive load

### Detail Page

**Purpose:** Deep-dive into individual component health with historical context.

**Features:**
- **Back Navigation**: Return to overview
- **Component Tabs**: Switch between all monitored components without
  leaving the detail view (risk-colored emoji + name per tab)
- **Component Header**: Name + risk level badge, centered
- **Risk Gauge**: Plotly gauge showing current risk score with a
  delta arrow vs. the previous reading
- **Trend Chart**: Interactive Plotly line chart showing:
  - Last 5 risk score readings (or fewer if less data available)
  - Time labels (T-4, T-3, T-2, T-1, Now)
  - Area fill for visual emphasis
  - Hover tooltips with exact values
  - Theme-aware colors
- **Data Validation**: Shows warning if less than 2 data points
- **Key Signals Table**: Header row (Signal/Reading/Normal
  Range/Status) above per-signal rows with ABNORMAL/NORMAL badges
- **Diagnostic Report**: Three-column card grid (what's happening,
  why it matters, what to do)
- **Footer**: Multi-section footer with repository/blog links and
  team attribution

---

## Technical Details

### Theme System

The dashboard implements a single "Pro" theme (minimalist, IBM Carbon Design
System-inspired) with light/dark mode variants, defined as a token dict
(`THEME_TOKENS` in `app.py`) rather than duplicated CSS per mode:

**Light Mode (Default)**

- Background: `#f5f5f7`
- Surface (cards): `#ffffff`
- Text: `#1d1d1f` / secondary `#6e6e73`
- Accent: `#0f62fe`
- Risk colors: High `#da1e28`, Medium `#ff832b`, Low `#24a148`

**Dark Mode**

- Background: `#1c1c1e`
- Surface (cards): `#2c2c2e`
- Text: `#f5f5f7` / secondary `#98989d`
- Accent: `#4589ff`
- Risk colors: High `#fa4d56`, Medium `#ff832b`, Low `#42be65`

Fonts: IBM Plex Sans (headings/body) and IBM Plex Mono (numeric values —
risk scores, metrics, signal readings), loaded via Google Fonts, reinforcing
the IBM-sponsored project's brand identity.

Each overview card carries a `border-left` stripe and a small per-component
icon (`COMPONENT_ICONS`) colored by risk level, so risk is perceptible before
reading any text. Decorative icons (heading icons, theme toggle, alert
banner) are inline Lucide-style SVGs rendered via `lucide_icon()`, colored
from the active theme token so they recolor automatically between
light/dark — a placeholder icon set pending a final sourced icon set.

Theme state is stored in `st.session_state["dark_mode"]` and persists across page navigation.

### Data Structure

The dashboard loads `ReportLayerOutput` JSON via `data_loader.py`. A
`MOCK_DATA_FALLBACK` dict is retained in `app.py` for offline development.

**Live Data Schema (INTERFACE.md v0.7):**
```python
{
    "timestamp": str,                       # ISO 8601
    "risk_score": float,                    # 0.0–1.0
    "risk_level": str,                      # "Low" | "Medium" | "High"
    "component": str,                       # Component identifier
    "prediction_confidence": float,         # 0.0–1.0
    "key_signals": List[dict],              # feature, value, unit, reference_range
    "risk_history": List[dict],             # timestamp + risk_score entries
    "anomaly_description": str,             # Granite LLM generated
    "possible_cause": str,                  # Granite LLM generated
    "recommended_action": List[str],        # Granite LLM generated
    "estimated_failure_probability": float | None,  # Model Layer, may be null
    "estimated_cycles_to_failure": int | None,      # Model Layer, may be null
    "notes": List[str],                     # Model Layer validation messages
}
```

**Supported Components:**
- `cooling_degradation` → "Cooling System"
- `air_intake_maf_anomaly` → "Air Intake System"
- `accelerator_pedal_sensor` → "Accelerator Pedal"
- `intake_air_temperature_sensor_fault` → "Intake Air Temperature"
- `map_load_signal_plausibility_fault` → "MAP Load Signal"

`cooling_system_stress` is retained as a legacy alias for older dashboard
test data and is displayed as "Cooling System".

### Page Routing

Simple session-state-based routing:
- `st.session_state["page"]`: `"overview"` | `"detail"`
- `st.session_state["selected_component"]`: Component key for detail view
- `st.session_state["dark_mode"]`: Theme toggle state (boolean)

### Trend Chart Implementation

**Technology:** Plotly `go.Scatter` with area fill

**Features:**
- Dynamic time labels based on data length
- Y-axis: 0-100% range with percentage formatting
- X-axis: Time labels (T-4 to Now)
- Line: 3px width, 8px markers, teal color (#19c8b9)
- Fill: 20% opacity area to zero
- Hover: Custom template showing time and risk percentage
- Theme-aware: Background, text, and grid colors adapt to theme

**Data Requirements:**
- Minimum 2 data points to render chart
- Shows warning if insufficient data
- Handles up to 5 data points (T-4 to Now)

---

## Development Guidelines

### Code Style

- **Flake8 compliant**: All code passes `flake8 dashboard/app.py`
- **PEP 8**: 79-character line limit, proper spacing
- **Type hints**: Use where appropriate for clarity
- **Docstrings**: Google-style for all functions

### Adding New Features

1. **Create Jira ticket** (GL-XX format)
2. **Update this README** with planned feature status
3. **Implement feature** following existing patterns
4. **Test thoroughly** in both light and dark modes
5. **Run flake8** to ensure code quality
6. **Update status** in this README upon completion

### Testing Checklist

Before committing dashboard changes:

- Tested in light mode
- Tested in dark mode
- Tested navigation (overview ↔ detail)
- Tested with all 3 component types
- Tested trend chart with various data lengths
- Verified responsive layout
- Checked browser console for errors
- Ran `flake8 dashboard/app.py` (exit code 0)
- Verified no breaking changes to data contracts

---

## Integration with Report Layer

### Current Status: Live Data via data_loader.py

The dashboard loads `ReportLayerOutput`-shaped JSON at startup via
`load_dashboard_data()` in `data_loader.py`. The data file path defaults to
`dashboard/tests/ui_required_data.json` and can be overridden with the
`DASHBOARD_TEST_DATA` environment variable.

### Planned Integration

When the Report Layer pipeline is complete, point the dashboard at its output:

```python
# Set env var before starting Streamlit
DASHBOARD_TEST_DATA=data/processed/latest_report.json streamlit run dashboard/app.py
```

**Consumed Fields from ReportLayerOutput (INTERFACE.md v0.7):**
- `timestamp`, `risk_score`, `risk_level`, `component`
- `prediction_confidence`, `key_signals`
- `anomaly_description`, `possible_cause`, `recommended_action`
- `risk_history` (trend chart)
- `estimated_failure_probability`, `estimated_cycles_to_failure`
- `notes`

See `docs/INTERFACE.md` Section 3 for complete field definitions.

---

## Known Issues & Limitations

### Current Limitations

1. **Partial Real Data**: test JSON currently contains full sample reports for the main 3 components; other anomaly types appear as UI placeholders unless data is provided.
2. **No Export**: Cannot download reports or charts.
3. **Desktop-First**: Mobile experience needs optimization.
4. **No Persistence**: Risk history is read from loaded JSON and is not stored between dashboard sessions.

### Planned Improvements

- Mobile-responsive improvements
- PDF export functionality
- Accessibility enhancements (WCAG 2.1 AA)
- 3D component visualization (exploratory)

---

## Troubleshooting

### Dashboard won't start

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Theme not switching

**Issue:** Theme toggle button doesn't change appearance

**Solution:**
- Clear browser cache
- Check browser console for JavaScript errors
- Verify `st.session_state["dark_mode"]` is being set
- Try hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

### Trend chart not displaying

**Issue:** Shows "Not enough data yet to show a trend."

**Solution:**
- Verify `component_data["risk_history"]` has at least 2 data points
- Check browser console for Plotly errors
- Ensure `plotly` is installed: `pip install plotly`

### Port already in use

**Error:** `Address already in use`

**Solution:**
```bash
# Kill existing Streamlit process
pkill -f streamlit

# Or use different port
streamlit run dashboard/app.py --server.port 8502
```

### Component not found error

**Issue:** "Component not found" error on detail page

**Solution:**
- Verify component key exists in loaded report data or in `anomaly_display.py`
- Check `st.session_state["selected_component"]` value
- Clear session state: Stop and restart Streamlit

---

## Team & Contact

**Report Team (Dashboard Owners):**
- Charlotte Yu
- Jintong He

**Project:** Granite Lifeline  
**Institution:** University of Bristol MSc Computer Science  
**Sponsor:** IBM

For questions or contributions, please refer to the main project README or create a Jira ticket.

---

## References

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [Project INTERFACE.md](../docs/INTERFACE.md) - Data contracts
- [Report Layer README](../report_layer/README.md) - Report Layer documentation
- [Project README.md](../README.md) - Overall architecture
