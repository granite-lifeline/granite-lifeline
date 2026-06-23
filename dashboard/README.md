# Dashboard

**Owner:** Report Team  
**Status:** Active Development  
**Last Updated:** 2026-06-23

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
- **Theme Support**: Light/dark mode toggle with Animal Crossing-inspired design
- **Responsive Design**: Optimized for desktop viewing (mobile optimization planned)

---

## Current Implementation Status

### [COMPLETED]

| Feature | Ticket | Description |
|---------|--------|-------------|
| Overview Page | GL-40 | Component cards with risk levels and scores |
| Component Detail Page | GL-41 | Metrics display with back navigation |
| Risk Score Trend Chart | GL-42 | Interactive Plotly line chart with theme support |
| Theme Toggle | GL-40 | Light/dark mode with Animal Crossing aesthetics |
| Team Footer | - | Team attribution footer |

### [PLANNED]

| Feature | Priority | Description |
|---------|----------|-------------|
| Diagnostic Report Display | P0 | Show anomaly_description, possible_cause, recommended_action |
| Key Signals Table | P0 | Display key_signals with ABNORMAL/NORMAL indicators |
| Report Layer Integration | P0 | Consume ReportLayerOutput instead of MOCK_DATA |
| Mobile Optimization | P1 | Responsive design for mobile devices |
| PDF Export | P2 | Download reports and charts |
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
    ↓
Renders:
    - Overview Page (component cards)
    - Detail Page (metrics + trend chart + reports)
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Streamlit | 1.x | Web app framework |
| Visualization | Plotly | 5.x | Interactive charts |
| Styling | Custom CSS | - | Theme implementation |
| Fonts | Google Fonts | - | Nunito, Noto Sans SC |

---

## Directory Structure

```
dashboard/
├── app.py              # Main Streamlit application
├── tests/              # Unit tests (planned)
│   └── .gitkeep
└── README.md           # This file
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
- **Navigation**: "View Details" button on each card
- **Team Footer**: Team attribution at bottom

**Design Principles:**
- Non-technical language (no jargon like "cooling_system_stress")
- Color-coded risk levels (red/orange/green)
- Large, readable fonts (Nunito family)
- Minimal cognitive load

### Detail Page

**Purpose:** Deep-dive into individual component health with historical context.

**Features:**
- **Back Navigation**: Return to overview
- **Component Header**: Name + risk level badge inline
- **Key Metrics**: 
  - Risk Score (percentage)
  - Last Updated timestamp
- **Trend Chart**: Interactive Plotly line chart showing:
  - Last 5 risk score readings (or fewer if less data available)
  - Time labels (T-4, T-3, T-2, T-1, Now)
  - Area fill for visual emphasis
  - Hover tooltips with exact values
  - Theme-aware colors
- **Data Validation**: Shows warning if less than 2 data points
- **Team Footer**: Team attribution at bottom

**Planned Additions:**
- Diagnostic report text (anomaly description, cause, actions)
- Key signals table with reference ranges
- Export functionality

---

## Technical Details

### Theme System

The dashboard implements a dual-theme system inspired by Animal Crossing aesthetics:

**Light Mode (Default)**
- Background: Warm beige (`rgb(247, 243, 223)`)
- Text: Brown (`#725d42`)
- Accent: Teal (`#19c8b9`)
- Cards: White with subtle shadows
- Chart: Beige background with brown grid

**Dark Mode**
- Background: Dark brown (`#3d3020`)
- Text: Light beige (`#e8d5b0`)
- Accent: Teal (`#19c8b9`)
- Cards: Darker brown with stronger shadows
- Chart: Dark brown background with lighter grid

Theme state is stored in `st.session_state["dark_mode"]` and persists across page navigation.

### Data Structure

The dashboard currently uses `MOCK_DATA` for development. Production integration will consume `ReportLayerOutput` from the Report Layer.

**Current Mock Data Schema:**
```python
MOCK_DATA = {
    "component_key": {
        "display_name": str,        # User-friendly name
        "risk_level": str,          # "High" | "Medium" | "Low"
        "risk_score": float,        # 0.0 - 1.0
        "trend": List[float],       # Historical risk scores (last 5)
        "key_signals": List[dict]   # Signal details
    }
}
```

**Supported Components:**
- `cooling_system_stress` → "Cooling System"
- `air_intake_maf_anomaly` → "Air Intake System"
- `accelerator_pedal_sensor` → "Accelerator Pedal"

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

### Current Status: Mock Data

The dashboard currently uses hardcoded `MOCK_DATA` for development and UI testing.

### Planned Integration

The dashboard will consume `ReportLayerOutput` from the Report Layer:

```python
from report_layer import generate_report
from shared.interface_models import ReportLayerOutput

# Get report for a component
report: ReportLayerOutput = generate_report(model_output)

# Display in dashboard
display_component_detail(report)
```

**Required Fields from ReportLayerOutput:**
- `timestamp`, `risk_score`, `risk_level`, `component`
- `prediction_confidence`, `key_signals`
- `anomaly_description`, `possible_cause`, `recommended_action`
- `risk_history` (for trend chart)

See `docs/INTERFACE.md` Section 3 for complete field definitions.

---

## Known Issues & Limitations

### Current Limitations

1. **Mock Data Only**: Not yet integrated with Report Layer
2. **No Diagnostic Reports**: anomaly_description, possible_cause, recommended_action not displayed
3. **No Key Signals Table**: key_signals not shown in detail page
4. **Fixed Components**: Only 3 component types supported
5. **No Export**: Cannot download reports or charts
6. **Desktop-First**: Mobile experience needs optimization
7. **No Persistence**: Risk history not stored between sessions

### Planned Improvements

- Report Layer integration (consume ReportLayerOutput)
- Display diagnostic report sections
- Key signals table with ABNORMAL/NORMAL indicators
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
- Verify `component_data["trend"]` has at least 2 data points
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
- Verify component key exists in MOCK_DATA
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
