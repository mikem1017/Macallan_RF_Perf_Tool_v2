# Macallan RF Performance Tool v2

The Macallan RF Performance Tool is a PyQt6 desktop application for loading RF measurements (Touchstone S-parameter files), evaluating them against device-specific requirements, and visualizing operational performance. The code base is structured for maintainability and automated testing with a clean architecture that separates data access, business logic, and presentation.

---

## Table of Contents

1. [Key Capabilities](#key-capabilities)  
2. [Architecture Overview](#architecture-overview)  
3. [Core Domains](#core-domains)  
   - [Devices and Criteria](#devices-and-criteria)  
   - [Measurements and Test Results](#measurements-and-test-results)  
   - [Compliance Evaluation](#compliance-evaluation)  
   - [Plotting Pipeline](#plotting-pipeline)  
4. [Workflow Walkthrough](#workflow-walkthrough)  
   - [Device Maintenance](#device-maintenance)  
   - [Loading Measurements](#loading-measurements)  
   - [Reviewing Compliance](#reviewing-compliance)  
   - [Visualizing Data](#visualizing-data)  
5. [Directory Layout](#directory-layout)  
6. [Installation & Environment](#installation--environment)  
7. [Running the Application](#running-the-application)  
8. [Testing](#testing)  
9. [Database Schema](#database-schema)  
10. [Configuration & Settings](#configuration--settings)  
11. [Logging & Troubleshooting](#logging--troubleshooting)  
12. [Phase Status & Next Steps](#phase-status--next-steps)

---

## Key Capabilities

- **Device maintenance** with CRUD operations, multi-stage criteria, gain range, gain flatness, VSWR, and OOB rejection rules.  
- **Measurement ingestion** supporting Touchstone S2P through S10P files, multi-gain mode, and temperature-specific runs.  
- **Automated compliance** evaluation across test stages using a dedicated service layer and pluggable test types.  
- **Interactive plotting** windows with filtering, consistent tick spacing (10 intervals on each axis), hash-mark acceptance regions, and export options.  
- **Session awareness** so only the data loaded in the current UI session is displayed, preventing historical bleed-over.  
- **Extensive validation** via Pydantic models and repository-level safety checks.

---

## Architecture Overview

The project adheres to clean architecture principles:

- **Core models** (`src/core/models`) represent devices, measurements, test criteria, and test results using Pydantic for validation.  
- **Repositories** (`src/core/repositories`) encapsulate SQLite persistence concerns with serialization for scikit-rf Network objects.  
- **Services** (`src/core/services`) contain business logic, orchestrating repositories, RF calculations, and test-type evaluations.  
- **Test types** (`src/core/test_types`) implement evaluation strategies (currently S-Parameters) and can be extended without touching the UI.  
- **RF utilities** (`src/core/rf_data`) provide filename parsing, Touchstone loading, and S-parameter calculations (gain, flatness, VSWR, OOB rejection).  
- **GUI layer** (`src/gui`) is thin, delegating all heavy lifting to services and exposing the application through PyQt6 widgets.

Communication path example:

```
PlotWindow -> PlottingService -> MeasurementRepository -> s_parameter_calculator
                                     |
                                     -> DeviceService -> TestCriteriaRepository
```

Each layer has high test coverage (unit tests for models, repositories, services, and test types; pytest-qt for GUI).

---

## Core Domains

### Devices and Criteria

- Devices define operational and wideband frequency ranges, port configuration, and tests performed.  
- Criteria are stored per device, test type, and test stage. Supported evaluation modes include range, min, max, and OOB ranges.  
- Gain flatness (max value of max-min over operational band) and gain range (min/max limits) are both supported.  
- Criteria editing UI persists data through `DeviceService`, which marks stale test results for recalculation when criteria change.

### Measurements and Test Results

- Touchstone files are loaded via `MeasurementService`. All metadata (serial number, temperature, path type, run number) is parsed automatically.  
- Measurements are serialized (Network objects pickled to BLOB) in SQLite.  
- Compliance results are stored via `ComplianceService` and linked to measurements and criteria. Results carry `s_parameter`, measured value, and pass/fail status.

### Compliance Evaluation

- `ComplianceService` pulls relevant criteria for the current test stage and calls the registered test type (S-Parameters).  
- `SParametersTestType` calculates gain range, gain flatness (max-min), VSWR, return loss, and OOB rejection.  
- Evaluations cover all combinations of temperatures, paths, and S-parameters provided by the device configuration.  
- Gain range display in the compliance table recalculates min-to-max values so users always see both bounds.

### Plotting Pipeline

- Plot windows run in the GUI thread but computation happens in a background `PlottingWorker`.  
- `PlottingService` filters measurements, pulls S-parameters, and returns aggregated traces (frequency arrays, values, labels).  
- Acceptance regions draw hash marks and maintain consistent thickness regardless of axis scaling.  
- Axis tick marks are enforced at 10 evenly spaced segments with three-decimal frequency labels.  
- A hover cursor gives per-point detail (frequency, gain/VSWR/return loss).

---

## Workflow Walkthrough

### Device Maintenance

1. Open the Device Maintenance dialog (`Tools -> Device Maintenance`).  
2. Add or edit a device, specifying:
   - Frequency ranges (operational and wideband)  
   - Port configuration (input and output ports)  
   - Multi-gain mode if applicable  
   - Tests performed (currently S-Parameters)
3. Define criteria per test stage:
   - Gain Range min/max  
   - Gain Flatness max  
   - VSWR max  
   - Optional OOB rejection ranges (frequency min/max with dBc requirement)
4. Saving updates the database and marks related test results as stale.

### Loading Measurements

1. In the Test Setup tab, select a device and the desired test stage.  
2. Load Touchstone files per temperature (Ambient, Hot, Cold).  
   - Standard mode expects PRI/RED pairs.  
   - Multi-gain mode expects PRI_HG, PRI_LG, RED_HG, RED_LG.  
3. Files are validated (serial number consistency, optional part number warnings) and stored session-wide.  
4. The file display lists metadata for the current session and temperature only.

### Reviewing Compliance

1. The compliance table organizes results as Temperature → Criterion → S-Parameter.  
2. Columns show requirement, limit text, PRI value/status, RED value/status.  
3. Changing the test stage triggers background re-evaluation using the same loaded measurements with new criteria.  
4. Copy-to-clipboard exports either table text or the entire table as an image for reporting.

### Visualizing Data

1. From the Plotting Controls tab, open plot windows (operational gain/VSWR, wideband, etc.).  
2. Filter by temperature, path, and S-parameter checkboxes.  
3. Adjust axis limits; tick marks remain at 10 intervals with fixed 3-decimal labels.  
4. Acceptance lines show min/max gain, flatness, or VSWR thresholds with directional hash marks.  
5. Save or copy plots for documentation.

---

## Directory Layout

```
Macallan_RF_Perf_Tool_v2/
├── README.md                     # This documentation
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Development/test dependencies
├── src/
│   ├── core/
│   │   ├── models/               # Pydantic domain models
│   │   ├── repositories/         # SQLite repository implementations
│   │   ├── services/             # Business logic services
│   │   ├── rf_data/              # Filename parser, touchstone loader, S-parameter calculator
│   │   ├── test_types/           # Test type framework (S-Parameters implementation)
│   │   ├── exceptions.py
│   │   └── test_stages.py
│   ├── gui/
│   │   ├── main.py               # Application entry point
│   │   ├── main_window.py        # Main window with tabs/menu
│   │   ├── utils/                # Service factory, error handler
│   │   └── widgets/
│   │       ├── device_maintenance/
│   │       ├── test_setup/
│   │       └── plotting/
│   └── database/
│       └── schema.py             # SQLite schema initialization
└── tests/
    ├── unit/
    ├── integration/
    └── gui/
```

The repo also includes documentation helpers (`STATUS.md`, `PHASE_5_STATUS.md`, `.cursor/plans/`), demo scripts, and automation artifacts.

---

## Installation & Environment

1. Use Python 3.13.7 or later (3.14 preferred).  
2. Install runtime dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. For development and testing (pytest, pytest-qt), also install:

   ```bash
   pip install -r requirements-dev.txt
   ```

The application depends on `scikit-rf` for Touchstone parsing and S-parameter calculations. On macOS you may need `brew install libomp` for scikit-rf if missing.

---

## Running the Application

### macOS / Linux

```bash
python3 -m src.gui.main
```

### Windows (development)

Double-click `main.bat` or run:

```cmd
python -m src.gui.main
```

On first launch, the tool creates `rf_performance.db` in the project root (or the executable directory in production builds). Schema creation happens automatically.

---

## Testing

- **Unit tests** cover models, repositories, services, RF calculations, and test types:

  ```bash
  python3 -m pytest tests/unit
  ```

- **Integration tests** ensure module interaction and database flows:

  ```bash
  python3 -m pytest tests/integration
  ```

- **GUI tests** (pytest-qt) can be run with:

  ```bash
  python3 -m pytest tests/gui
  ```

- **Coverage example**:

  ```bash
  python3 -m pytest --cov=src --cov-report=html
  ```

Demo helper scripts such as `demo_phase2.py` show sample calculations using the core calculator functionality.

---

## Database Schema

SQLite tables (see `src/database/schema.py`):

1. `devices`: device metadata, frequency ranges, JSON fields for ports and tests performed.  
2. `test_criteria`: criteria per device/test stage (range, max, OOB frequency ranges).  
3. `measurements`: serialized Network data and parsed metadata.  
4. `test_results`: measured values linked to criteria, pass/fail flags, stale indicators.

All tables use UUID primary keys. Cascading deletes ensure referential integrity.

---

## Configuration & Settings

- The default database path is in the executable directory (or project root during development).  
- Service creation lives in `src/gui/utils/service_factory.py`. Update this file if you move the database or swap repository implementations.  
- Test stages are configurable via `src/core/test_stages.py` (currently Board-Bring-Up, SIT, Test-Campaign).  
- Additional test types can be registered in `src/core/test_types/registry.py`.

---

## Logging & Troubleshooting

- A global exception hook (`src/gui/main.py`) catches uncaught errors and shows detailed tracebacks to the user.  
- GUI widgets use `handle_exception`/`handle_warning` from `src/gui/utils/error_handler.py` for consistent messaging.  
- Compliance evaluation runs in background threads; errors propagate back to the UI with descriptive dialogs and table refresh safeguards.  
- Common issues:
  - **Missing scikit-rf**: install via `pip install scikit-rf`.  
  - **Touchstone parsing failures**: verify file extension and integrity; loader logs warnings for malformed metadata.  
  - **Plot ticks disappear**: resolved by enforcing fixed intervals; if ticks still vanish, ensure axis limits are valid (min < max).

---

## Phase Status & Next Steps

- **Phase 1-4** (models, RF utilities, services) are complete with automated tests.  
- **Phase 5/6** (GUI implementation, plotting) are largely complete, including compliance table polish and consistent plotting visuals.  
- **Phase 7** is open for definition; likely targets production hardening, expanded automated GUI tests, packaging, and additional test types.

For a historical summary and outstanding tasks see `STATUS.md` and `PHASE_5_STATUS.md`.

---

*Macallan RF Performance Tool v2 – internal engineering utility. All rights reserved.*










