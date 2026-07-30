# Dashboard

**Owner:** Report Team  
**Status:** Active Development  
**Last Updated:** 2026-07-30

---

## Overview

The Dashboard is the user-facing component of Granite Lifeline, providing vehicle owners with an intuitive web interface to monitor vehicle health, understand risk levels, and track component status over time.

```
Data Layer → Model Layer → Report Layer → Dashboard
```

### Key Features

- **Health Overview**: At-a-glance view of all monitored components with risk-based prioritization
- **Component Details**: Drill-down pages with metrics and interactive trend charts
- **CSV Upload & Live Analysis**: Upload a real KIT OBD-II CSV and run it through the full Data Layer → Model Layer → Report Layer pipeline for a live diagnostic report (requires local Ollama + Python ML dependencies — see Setup in the project root README)
- **What-If Analysis**: Interactive scenario page projecting how driving style / sensor offsets would shift each component's risk score
- **Signal Tooltips**: Plain-language glossary tooltips for technical signal names, sourced from the Report Layer's `SIGNAL_DISPLAY_NAMES`
- **Risk Score Trends**: Plotly-powered visualizations showing risk progression over time
- **Theme Support**: Light/dark mode toggle with an IBM Carbon-inspired "Pro" design
- **PDF / CSV Export**: Downloads filtered component reports and key signal data from the overview page
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
| Failure Prediction Data Support | GL-198 | Loads estimated_failure_probability, estimated_cycles_to_failure, and notes from the current ReportLayerOutput contract |
| Failure Prediction UI Display | GL-278/GL-280 | Shows failure probability card and Data Quality Notes on the detail page |
| Five-Type Component Display Mapping | GL-273/GL-384 | Maps all 5 current anomaly types to owner-friendly display names; legacy cooling_system_stress alias retained |
| PDF / CSV Export | GL-343 to GL-348 | Overview-page export panel with component filters, PDF section filters, CSV column filters, ZIP downloads, local PDF template, and tests |
| Module Split | GL-255 | `app.py` (2581 lines) split into `theme.py`, `ui_components.py`, `data_store.py`, and `pages/{overview,detail,what_if}.py` |
| CSV Upload Pipeline | GL-256 to GL-262 | Upload validation (KIT column/row checks), user-friendly error cards, and end-to-end wiring to Data Layer + Model Layer + Report Layer |
| Live Model Layer Integration | GL-365 | `csv_pipeline.py` invokes the Model Layer's `kit_residual_detector.py --batch` as a subprocess per INTERFACE.md §2.5's documented CLI/error contract; verified with a real, unmocked run producing a live report |
| What-If Analysis Page | — | Scenario cards, driving-style sliders, per-component risk projection, uncertainty range |
| Signal Tooltips | — | `glossary.py`; plain-language tooltips for technical signal names |
| Demo Readiness Check | GL-384 | Final dashboard/report demo checklist, expected outputs, known limitations, and regression command set |

### [PLANNED]

| Feature | Priority | Description |
|---------|----------|-------------|
| Mobile Optimization | P1 | Responsive design for mobile devices |
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
| PDF Export | ReportLab | 4.x | Local PDF generation |
| Styling | Custom CSS | - | Theme implementation |
| Fonts | Google Fonts | - | IBM Plex Sans, IBM Plex Mono, Noto Sans SC |

---

## Directory Structure

```
dashboard/
├── app.py                  # Entry point / router (theme, page dispatch)
├── theme.py                # THEME_TOKENS, icons, shared style helpers
├── ui_components.py        # Reusable HTML/markdown component builders
├── data_store.py           # get_mock_data()/get_data_source(); real vs. mock arbitration
├── data_loader.py          # JSON → component-keyed dict loader; load_model_output_for_dashboard()
├── csv_pipeline.py         # run_uploaded_csv_batch(): Data Layer -> Model Layer (subprocess) -> Report Layer
├── csv_validator.py        # Uploaded-CSV column/row validation (GL-257)
├── anomaly_display.py      # Component/signal display name mappings
├── glossary.py             # Signal tooltip text (plain-language, sourced from Report Layer)
├── export_helper.py        # PDF / CSV export data and file helpers
├── EXPORT_REPORT_PLAN.md   # GL-343 export entry and field checklist
├── pages/
│   ├── overview.py         # Health overview + CSV upload entry point
│   ├── detail.py           # Component detail page
│   └── what_if.py          # What-if scenario analysis page
├── assets/                 # Static assets
├── DATA_INTEGRATION.md     # Data contract and field documentation
├── tests/
│   └── ui_required_data.json   # Sample ReportLayerOutput-shaped data (mock fallback)
└── README.md               # This file
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Virtual environment activated (see root README.md)
- Dashboard dependencies installed from `requirements.txt`
- For local live CSV analysis only: extra Report/Data dependencies installed
  from `requirements-local.txt`
- For live CSV analysis only: Model Layer dependencies installed from
  `model_layer/ttm-related/requirements.txt`
- For live CSV analysis only: a local [Ollama](https://ollama.com) instance with `granite4.1:8b` pulled

### Installation

**Dashboard only (mock/demo data):**

```bash
uv run streamlit run dashboard/app.py
```

**Full local pipeline (real CSV upload → live analysis):** run `./setup.sh`
(macOS/Linux) or `.\setup.ps1` (Windows) from the project root — installs
Python dependencies, installs Ollama if missing, pulls the Granite LLM, and
starts the dashboard in one step. See the project root README's Setup
section for details.

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
- **Export Report Panel**: Multi-select dropdown controls for report
  components, PDF sections, and CSV columns, followed by PDF / CSV download
  buttons. Multiple selected components are downloaded as ZIP files.
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
(`THEME_TOKENS` in `theme.py`) rather than duplicated CSS per mode:

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

**Live Data Schema (current `docs/INTERFACE.md` contract):**
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

### Export Report Implementation

**Technology:** Streamlit `st.download_button`, Python `csv`, `zipfile`,
and ReportLab.

**Features:**
- Overview-page export panel below the component cards
- Report component multi-select list
- Collapsible PDF section and CSV column filters
- Single-component downloads as `.pdf` or `.csv`
- Multi-component downloads as `.zip`
- Download filenames include selected component names, selected export detail
  names, the download date, and the file type
- PDF report template includes a branded header, risk summary, summary cards,
  key signals table, diagnostic report panels, and footer page numbering
- No external service dependency; all export files are generated locally

**Local Validation:**
```bash
python -m pytest tests/test_export_helper.py tests/test_failure_prediction_ui_states.py
streamlit run dashboard/app.py --server.port 8502 --server.runOnSave true
```

Manual checks:
- Open `http://localhost:8502`
- Scroll below the overview component cards
- Expand and collapse Report components, PDF sections, and CSV columns
- Download one component as PDF and CSV
- Select multiple components and confirm PDF / CSV ZIP downloads
- Confirm the PDF risk block does not overlap in Preview or the browser PDF
  viewer

### Demo Readiness

GL-384 keeps the final demonstration focused on owner-facing workflows rather
than implementation details. The current demo path is documented in
`dashboard/tests/demo_readiness_check.md` and covers:

- Hosted/demo-data launch path
- Overview page risk prioritization and component navigation
- Detail page failure prediction, notes, trend, key signals, and report text
- What-If scenario flow
- PDF / CSV export flow
- Empty/error states for CSV upload and missing data
- Known limitations to disclose during the viva/demo

Recommended pre-demo command:

```bash
python -m pytest \
  tests/test_dashboard.py \
  tests/test_export_helper.py \
  tests/test_csv_upload_pipeline.py \
  tests/test_failure_prediction_ui_states.py \
  tests/test_dashboard_ui_consistency.py \
  tests/test_dashboard_what_if.py \
  tests/test_demo_readiness.py
```

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
- Tested with available component types
- Tested trend chart with various data lengths
- Tested overview PDF / CSV export with one component
- Tested overview PDF / CSV ZIP export with multiple components
- Tested export filters for Report components, PDF sections, and CSV columns
- Verified responsive layout
- Checked browser console for errors
- Ran `python -m pytest tests/test_export_helper.py tests/test_failure_prediction_ui_states.py`
- Ran `flake8 dashboard/app.py` (exit code 0)
- Verified no breaking changes to data contracts

---

## Integration with Report Layer

### Static / Demo Mode

With no CSV uploaded, the dashboard loads a fixed sample `ReportLayerOutput`-shaped
JSON via `load_dashboard_data()` in `data_loader.py`. The file path defaults to
`dashboard/tests/ui_required_data.json` and can be overridden with the
`DASHBOARD_TEST_DATA` environment variable. This is what the public hosted
demo (`granite-lifeline.streamlit.app`) runs, since it has no budget for
hosted LLM/model inference (see `docs/viva/report_challenge.md` Limitations).
Streamlit Cloud should deploy the lightweight `requirements.txt` environment
and use Python 3.11 from the app's Advanced settings; local-only
`requirements-local.txt` and Model Layer dependencies are intentionally kept
out of the hosted dependency install.

### Live Mode (real CSV upload)

`pages/overview.py`'s upload button calls `csv_pipeline.run_uploaded_csv_batch()`,
which runs the uploaded file through Data Layer (`run_data_pipeline_for_upload`),
then the Model Layer (`kit_residual_detector.py --batch`, invoked as a
subprocess per INTERFACE.md §2.5), then `report_generator.generate_report()`,
and stores the result in `st.session_state["dashboard_data"]` — `data_store.py`
prefers this over the static file whenever it's present. This requires local
Ollama + Model Layer's Python dependencies (see Getting Started above); it
has been verified end-to-end with a real KIT CSV producing a real report.

**Consumed Fields from ReportLayerOutput (current `docs/INTERFACE.md` contract):**
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

1. **Only 3 of 5 anomaly types have real Model Layer detection logic** (`cooling_degradation`, `air_intake_maf_anomaly`, `accelerator_pedal_sensor`); the other 2 are permanent 0.0-score placeholders in `kit_residual_detector.py`, so a live upload can never surface them as the top result even if that fault is actually present.
2. **`estimated_cycles_to_failure` / `estimated_failure_probability` are always null** in live mode — the Model Layer's trend estimator (Story 8) is not yet implemented.
3. **Desktop-First**: Mobile experience needs optimization.
4. **No cross-session persistence**: in live mode, `risk_history` is synthesized per request from the Model Layer's batch envelope (every analysed window in the uploaded file), not stored across separate uploads or sessions — this is a deliberate simplification, not an oversight, and is sufficient for "trend within this one upload."
5. **No hosted/zero-install mode**: live analysis requires local Ollama + Model Layer Python dependencies; there is no paid hosted inference (see Integration with Report Layer above).

### Planned Improvements

- Mobile-responsive improvements
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

### Downloaded PDF still shows an old layout

**Issue:** The PDF download does not reflect recent template changes.

**Solution:**
- Stop and restart Streamlit so `dashboard/export_helper.py` is reloaded
- Refresh the browser page before downloading again
- Open the newest file in the Downloads folder, because repeated downloads
  may keep similar filenames

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
