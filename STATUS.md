# Project Status - Macallan RF Performance Tool v2

**Last Updated**: 2025-01-XX  
**Current Phase**: Phase 5 (GUI Implementation) - In Progress  
**Primary Blocker**: Issue #14 - Program crashes when selecting device L109908

---

## Executive Summary

This is a full-featured RF performance analysis tool built with Python 3.13.7+ and PyQt6. The tool allows users to:
1. **Device Maintenance**: CRUD operations for device configurations and test criteria
2. **Test Setup**: Load RF measurement files (Touchstone S2P-S10P) and evaluate compliance
3. **Plotting**: Interactive plotting with filtering and export capabilities

The application follows clean architecture principles with strict separation between data layer, business logic, and UI. Testability is the highest priority.

---

## Project Architecture

### Technology Stack
- **Language**: Python 3.13.7+ (3.14 preferred)
- **GUI Framework**: PyQt6
- **RF Data Processing**: scikit-rf (Network objects)
- **Database**: SQLite3
- **Testing**: pytest + pytest-qt
- **Plotting**: matplotlib
- **Data Validation**: Pydantic v2

### Directory Structure
```
Macallan_RF_Perf_Tool_v2/
├── src/
│   ├── core/                    # Core business logic (UI-independent)
│   │   ├── models/              # Pydantic models (Device, TestCriteria, Measurement, TestResult)
│   │   ├── repositories/        # Repository pattern implementations (SQLite)
│   │   ├── services/            # Business logic services
│   │   ├── rf_data/             # RF data processing (filename parser, touchstone loader, S-param calculator)
│   │   ├── test_types/          # Pluggable test type implementations
│   │   ├── exceptions.py        # Custom exception classes
│   │   └── test_stages.py       # Configurable test stages
│   ├── gui/                     # UI layer (thin, delegates to services)
│   │   ├── widgets/
│   │   │   ├── device_maintenance/  # Device CRUD dialog and widgets
│   │   │   ├── test_setup/          # Test setup tab and compliance table
│   │   │   └── plotting/            # Plotting controls and plot windows
│   │   ├── utils/               # Service factory, error handler
│   │   ├── main_window.py      # Main application window
│   │   └── main.py             # Application entry point
│   └── database/
│       └── schema.py           # SQLite schema definition
├── tests/
│   ├── unit/                   # Unit tests (no GUI)
│   ├── integration/            # Integration tests
│   └── gui/                    # GUI tests (pytest-qt)
├── ISSUES.md                   # Bug tracking
├── GUI_TEST_SEQUENCE.md       # Systematic GUI test sequence
├── STATUS.md                   # This file
├── requirements.txt            # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                    # Python package setup
├── main.bat                    # Windows launcher script
└── README.md                   # Project overview
```

### Key Design Patterns
- **Repository Pattern**: Abstract interfaces (`IRepository`) for data access
- **Dependency Injection**: Services receive repositories via constructor
- **Strategy Pattern**: Pluggable test types via `AbstractTestType`
- **Singleton Pattern**: `TestTypeRegistry` for managing test types
- **Clean Architecture**: Strict separation of concerns

---

## Completed Work

### Phase 1: Core Models & Database Schema ✅
- **Status**: Complete
- **Files**:
  - `src/core/models/device.py` - Device model with validation (part number format, frequency ranges, port configs)
  - `src/core/models/test_criteria.py` - TestCriteria model with support for multiple criteria types
  - `src/core/models/measurement.py` - Measurement model with Network serialization
  - `src/core/models/test_result.py` - TestResult model for pass/fail evaluation
  - `src/database/schema.py` - SQLite schema with 4 main tables
- **Features**:
  - Pydantic v2 models with extensive validation
  - UUID-based primary keys
  - JSON serialization for complex fields (lists, Network objects)
  - Support for configurable test stages
  - Port configuration for devices (input/output ports)

### Phase 2: RF Data Processing ✅
- **Status**: Complete
- **Files**:
  - `src/core/rf_data/filename_parser.py` - Hybrid regex/keyword parsing for metadata extraction
  - `src/core/rf_data/touchstone_loader.py` - Touchstone file loading (S2P-S10P)
  - `src/core/rf_data/s_parameter_calculator.py` - S-parameter calculations (gain, VSWR, OOB rejection)
- **Features**:
  - Extracts serial number (SNXXXX or EMXXXX), part number, path type (PRI/RED), temperature, date, run number
  - Handles multiple Touchstone formats (S2P to S10P)
  - Calculates gain range (min/max), VSWR, OOB rejection (worst-case across frequency range)
  - Frequency filtering with boundary points included

### Phase 3: Business Logic & Test Types ✅
- **Status**: Complete
- **Files**:
  - `src/core/repositories/*.py` - SQLite implementations of repositories
  - `src/core/services/device_service.py` - Device and criteria CRUD operations
  - `src/core/services/measurement_service.py` - File loading and measurement storage
  - `src/core/services/compliance_service.py` - Compliance evaluation orchestration
  - `src/core/test_types/base.py` - Abstract base class for test types
  - `src/core/test_types/s_parameters.py` - S-Parameter test type implementation
  - `src/core/test_types/registry.py` - Test type registry (singleton)
- **Features**:
  - Full CRUD for devices and test criteria
  - Automatic compliance evaluation on file load
  - Test result storage with stale marking when criteria change
  - Dynamic S-parameter determination based on device port configuration
  - OOB rejection calculation using worst-case (minimum) rejection across frequency range

### Phase 4: Service Layer Enhancements ✅
- **Status**: Complete
- **Changes**:
  - File loading validation (part number matching, serial number consistency, temperature consistency)
  - Multiple file support (2 or 4 files per temperature based on Multi-Gain-Mode)
  - Compliance evaluation triggers (automatic on load + manual trigger)
  - Results storage per temperature with stale marking
  - Device deletion with related data confirmation
  - Transaction management for database operations
  - Error handling with Result objects (recommendation chosen by implementation)

### Phase 5: GUI Implementation 🟡
- **Status**: In Progress (80% complete)
- **Files**:
  - `src/gui/main.py` - Application entry point with global exception handler
  - `src/gui/main_window.py` - Main window with tabs and menu bar
  - `src/gui/widgets/device_maintenance/device_maintenance_dialog.py` - Device CRUD dialog
  - `src/gui/widgets/device_maintenance/device_list_widget.py` - Device list table
  - `src/gui/widgets/device_maintenance/device_form_widget.py` - Device form
  - `src/gui/widgets/device_maintenance/test_criteria_editor.py` - Test criteria editor with test stage tabs
  - `src/gui/widgets/test_setup/test_setup_tab.py` - Test setup tab with file loaders
  - `src/gui/widgets/test_setup/compliance_table_widget.py` - Hierarchical compliance table
  - `src/gui/widgets/plotting/plotting_controls_tab.py` - Plotting controls tab
  - `src/gui/widgets/plotting/plot_window.py` - Individual plot windows
  - `src/gui/utils/service_factory.py` - Service dependency injection
  - `src/gui/utils/error_handler.py` - Centralized error handling
- **Features Implemented**:
  - ✅ Main window with tabs (Test Setup, Plotting)
  - ✅ Device Maintenance dialog (menu item Ctrl+D)
  - ✅ Device list table (3 columns: Name, Part Number, Description)
  - ✅ Device form with all fields (frequency 3 decimals, checkboxes for tests)
  - ✅ Test criteria editor with test stage tabs
  - ✅ OOB requirements table (with spinbox improvements)
  - ✅ Test Setup tab with device/test stage selection
  - ✅ File loaders (Hot, Cold, Ambient) accepting multiple files
  - ✅ Compliance table with hierarchical tree view (6 columns)
  - ✅ Copy compliance table to clipboard (tab-separated)
  - ✅ Global exception handler (catches all unhandled exceptions)
  - ✅ Error handling with modal dialogs (critical) and status bar (warnings)
- **Features Pending**:
  - ⚠️ Plotting windows (basic structure exists, needs completion)
  - ⚠️ Plot filtering controls (checkboxes for HG/LG, Amb/Hot/Cold, Pri/Red, S-parameters)
  - ⚠️ Plot export (save/copy to clipboard)

---

## Known Issues

### Critical Issues

#### Issue #14: Program crashes when selecting device L109908 in Device Maintenance
- **Status**: Open (Multiple attempts to fix)
- **Priority**: Critical
- **Description**: Clicking device L109908 causes program crash. This is a persistent issue despite multiple layers of defensive programming.
- **Location**: Multiple locations:
  - `src/gui/widgets/device_maintenance/device_maintenance_dialog.py` - `_on_device_selected()`
  - `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `__init__` and `_load_criteria()`
  - `src/core/repositories/device_repository.py` - `_row_to_device()`
- **Fixes Applied**:
  1. **DeviceRepository**: Robust handling of `NULL` and malformed JSON for `tests_performed`, `input_ports`, `output_ports`, and `None` for frequency fields
  2. **DeviceMaintenanceDialog**: Extensive error handling in `_on_device_selected()`, validation of `tests_performed` type, creation of `safe_device` with defaults, detailed error dialogs
  3. **DeviceListWidget**: `try-except` around selection change, `None` checks
  4. **DeviceFormWidget**: Comprehensive `None` checks and defaults in `load_device()`
  5. **TestCriteriaEditor**: Robust validation in `__init__`, defensive checks for dictionary/attribute existence in `_load_criteria()`
  6. **main.py**: Global exception handler (`sys.excepthook`) to catch all unhandled exceptions and display in `QMessageBox`
  7. **DeviceService**: Explicit `ValueError` checks for `None` repositories and method existence
  8. **ServiceFactory**: Explicit `ValueError` checks after service creation
- **Next Steps**:
  - **CRITICAL**: Get exact error message/traceback from user (should appear in QMessageBox due to global exception handler)
  - If no message appears, the crash may be happening before QApplication is initialized
  - May need to inspect database directly to see what data is stored for device L109908
  - Consider creating a test script that loads device L109908 in isolation to debug

### Medium Priority Issues

#### Issue #10: OOB frequency fields inconsistent with other frequency entries
- **Status**: Pending Verification
- **Priority**: Medium
- **Description**: OOB frequency fields had 2 decimals (should be 3) and no units. Default values made editing difficult.
- **Fix Applied**: 
  - Added `setDecimals(3)` and `setSuffix(" GHz")` to OOB frequency spinboxes
  - Implemented `_configure_oob_spinbox()` and `_create_oob_spinbox_filter()` for better UX:
    - Empty/blank default values using `setSpecialValueText("")`
    - Select all text on focus
    - Proper tab/Enter key navigation
- **Status**: Fix applied, awaiting user verification

#### Issue #13: Compliance table not populating after loading files
- **Status**: Pending Verification
- **Priority**: Critical (was fixed)
- **Description**: Compliance table only showed "AMB" but no criterion results. Columns were unevenly spaced and text was unreadable.
- **Fix Applied**:
  1. Fixed filtering logic in `compliance_service.py` - now correctly filters by `criterion.test_stage` instead of `measurement.test_stage`
  2. Removed `setStretchLastSection(True)`, set all columns to `QHeaderView.ResizeMode.Interactive`
  3. Implemented `_set_proportional_column_widths()` for even distribution
  4. Changed text color to black (`QColor(0, 0, 0)`) on light green/red backgrounds
- **Status**: Fix applied, awaiting user verification

#### Issue #15: Gain range should display min AND max gain in operational band
- **Status**: Pending Verification
- **Priority**: Medium
- **Description**: Compliance table showed only single value (e.g., "28.87") instead of range (e.g., "28.5 to 29.2 dB").
- **Fix Applied**:
  - Modified `_format_value()` in `compliance_table_widget.py` to detect Gain Range criteria
  - Deserializes `Network` from `Measurement` object
  - Recalculates min/max gain using `SParameterCalculator`
  - Formats output as "X.XX to Y.YY dB"
- **Status**: Fix applied, awaiting user verification

### Fixed Issues (Closed)
- ✅ Issue #1: PyQt6 `addAction` syntax error
- ✅ Issue #2: Frequency range precision too limited
- ✅ Issue #3: Tests Performed should use checkboxes
- ✅ Issue #4: UnboundLocalError when saving device
- ✅ Issue #5: Device Maintenance window too narrow
- ✅ Issue #6: Unused Actions column in device list
- ✅ Issue #7: Where are test requirements/criteria entered? (Clarified)
- ✅ Issue #8: JSON serialization error when loading S4P files
- ✅ Issue #9: Copy compliance table to clipboard
- ✅ Issue #11: Test-stage tabs not visible
- ✅ Issue #12: No delete device functionality

---

## Testing Status

### Unit Tests
- **Status**: Comprehensive coverage for core models, repositories, services
- **Location**: `tests/unit/`
- **Coverage**: Models, repositories, RF data processing, test types, services

### Integration Tests
- **Status**: Basic integration tests exist
- **Location**: `tests/integration/`
- **Coverage**: Service integration, database operations

### GUI Tests
- **Status**: Limited (pytest-qt setup exists)
- **Location**: `tests/gui/`
- **Coverage**: Basic widget tests
- **Note**: GUI testing is challenging due to PyQt6 complexity. Manual testing has been primary method.

### Manual Testing
- **Status**: Ongoing via `GUI_TEST_SEQUENCE.md`
- **Coverage**: End-to-end workflows, edge cases, error handling
- **Test Script**: `GUI_TEST_SEQUENCE.md` provides systematic test sequence

---

## Database Schema

### Tables
1. **devices**
   - `id` (TEXT PRIMARY KEY) - UUID
   - `name` (TEXT)
   - `description` (TEXT)
   - `part_number` (TEXT)
   - `operational_freq_min` (REAL)
   - `operational_freq_max` (REAL)
   - `wideband_freq_min` (REAL)
   - `wideband_freq_max` (REAL)
   - `multi_gain_mode` (INTEGER) - Boolean
   - `tests_performed` (TEXT) - JSON array
   - `input_ports` (TEXT) - JSON array
   - `output_ports` (TEXT) - JSON array

2. **test_criteria**
   - `id` (TEXT PRIMARY KEY) - UUID
   - `device_id` (TEXT) - Foreign key to devices
   - `test_type` (TEXT)
   - `test_stage` (TEXT)
   - `requirement_name` (TEXT)
   - `min_value` (REAL)
   - `max_value` (REAL)
   - `unit` (TEXT)
   - `criteria_data` (TEXT) - JSON for complex criteria (OOB requirements)

3. **measurements**
   - `id` (TEXT PRIMARY KEY) - UUID
   - `device_id` (TEXT) - Foreign key to devices
   - `serial_number` (TEXT)
   - `temperature` (TEXT)
   - `path_type` (TEXT) - PRI/RED
   - `gain_mode` (TEXT) - HG/LG (optional)
   - `touchstone_data` (TEXT) - JSON-serialized Network object
   - `metadata` (TEXT) - JSON object (date, run_number, etc.)
   - `created_at` (TEXT) - ISO timestamp

4. **test_results**
   - `id` (TEXT PRIMARY KEY) - UUID
   - `measurement_id` (TEXT) - Foreign key to measurements
   - `test_criteria_id` (TEXT) - Foreign key to test_criteria
   - `measured_value` (REAL)
   - `passed` (INTEGER) - Boolean
   - `s_parameter` (TEXT) - e.g., "S21", "S31"
   - `stale` (INTEGER) - Boolean (marks results as outdated when criteria change)

### Database Location
- **Development**: Same directory as `main.bat` / `.sh` script
- **Production**: Same directory as `.exe` file
- **Default Name**: `rf_performance.db`
- **Initialization**: Automatic on first run via `create_schema()`

---

## Key Technical Decisions

### 1. OOB Rejection Architecture
- **Decision**: OOB criteria use frequency ranges (`frequency_min`, `frequency_max`) instead of single frequency
- **Rationale**: Allows specification of rejection across a frequency band
- **Implementation**: Calculates worst-case (minimum) rejection across the range and compares using `>=` operator
- **Location**: `src/core/test_types/s_parameters.py` - `_evaluate_oob_criterion()`

### 2. Gain Range Display
- **Decision**: Store `max_gain` in `TestResult.measured_value` for database compatibility, but GUI recalculates min/max from raw data for display
- **Rationale**: Allows "X.XX to Y.YY dB" format without storing redundant data
- **Implementation**: `compliance_table_widget.py` - `_format_value()` detects Gain Range criteria and recalculates

### 3. Port Configuration
- **Decision**: Devices define `input_ports` and `output_ports` lists
- **Rationale**: Makes S-parameter determination dynamic (gain = S<output><input>, VSWR = S<port><port>)
- **Implementation**: `SParametersTestType` calculates relevant S-parameters based on port configuration

### 4. Test Stage Filtering
- **Decision**: Filter results by `criterion.test_stage`, not `measurement.test_stage`
- **Rationale**: Results are linked to criteria via `test_criteria_id`. Criteria have `test_stage`, measurements don't.
- **Implementation**: `compliance_service.py` - `get_compliance_results()` filters by checking each result's associated criterion

### 5. Error Handling Strategy
- **Decision**: Combination approach - critical errors use modal dialogs, warnings use status bar
- **Rationale**: Non-blocking warnings for validation issues, blocking dialogs for critical failures
- **Implementation**: `error_handler.py` provides `handle_exception()` and `handle_warning()` functions

### 6. Global Exception Handler
- **Decision**: Install `sys.excepthook` in `main.py` to catch all unhandled exceptions
- **Rationale**: Prevents silent crashes, provides detailed error information to user
- **Implementation**: `exception_hook()` function displays `QMessageBox` with full traceback

---

## Next Steps

### Immediate (Critical)
1. **Resolve Issue #14**:
   - Get exact error message/traceback from user (should appear in QMessageBox)
   - If no message, investigate crash before QApplication initialization
   - Inspect database directly for device L109908 data
   - Create isolated test script to load device L109908

### Short Term
2. **Verify Pending Issues**:
   - Issue #10: OOB frequency fields (user verification)
   - Issue #13: Compliance table population (user verification)
   - Issue #15: Gain range display (user verification)

3. **Complete Plotting Features**:
   - Finish plot window implementation
   - Add filtering controls (HG/LG, Amb/Hot/Cold, Pri/Red, S-parameters)
   - Implement plot export (save/copy to clipboard)
   - Dynamic plot titles based on device/serial number

### Medium Term
4. **Testing**:
   - Expand GUI test coverage with pytest-qt
   - Create automated test scripts for common workflows
   - Add performance tests for large datasets

5. **Documentation**:
   - API documentation (docstrings are extensive, but could add Sphinx)
   - User manual for Device Maintenance, Test Setup, Plotting
   - Developer guide for adding new test types

### Long Term
6. **Additional Test Types**:
   - Implement additional test types beyond S-Parameters
   - Ensure modularity and testability maintained

7. **Enhancements**:
   - Export/import device configurations
   - Batch processing of multiple serial numbers
   - Historical tracking of test results over time

---

## Development Workflow

### Running the Application
```bash
# Windows (development)
main.bat

# macOS/Linux (development)
python3 -m src.gui.main

# Production (future)
rf_performance_tool.exe
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_device_repository.py
```

### Debugging
- **Global Exception Handler**: All unhandled exceptions are caught and displayed in `QMessageBox`
- **Logging**: Consider adding Python logging module for detailed debugging
- **Test Scripts**: Temporary scripts like `test_complete_startup.py` can be created for isolated testing

---

## File-Specific Notes

### Critical Files for Issue #14
1. **`src/core/repositories/device_repository.py`**:
   - `_row_to_device()` method handles `NULL` values and malformed JSON
   - Must be robust for devices with missing or corrupted data

2. **`src/gui/widgets/device_maintenance/device_maintenance_dialog.py`**:
   - `_on_device_selected()` method creates `safe_device` object with defaults
   - Extensive error handling with traceback logging

3. **`src/gui/widgets/device_maintenance/test_criteria_editor.py`**:
   - `__init__()` validates device attributes before UI setup
   - `_load_criteria()` has defensive checks for dictionary/attribute existence

4. **`src/gui/main.py`**:
   - `exception_hook()` should catch all unhandled exceptions
   - If crash occurs before QApplication initialization, this won't help

### Files with Extensive Comments (8/10 level)
- All core models (`src/core/models/*.py`)
- All repositories (`src/core/repositories/*.py`)
- All services (`src/core/services/*.py`)
- RF data processing (`src/core/rf_data/*.py`)
- Test types (`src/core/test_types/*.py`)
- Database schema (`src/database/schema.py`)
- Exceptions (`src/core/exceptions.py`)

---

## User Feedback Loop

### Issue Tracking Process
1. User reports issue in chat
2. Issue added to `ISSUES.md` with full details
3. Fix implemented and tested
4. User verifies fix
5. Issue marked as "Fixed" in `ISSUES.md`

### Current Issue Status
- **Open**: Issue #14 (Critical)
- **Pending Verification**: Issues #10, #13, #15
- **Fixed**: Issues #1-#12

---

## Contact Points for Resumption

When resuming work:
1. **Check `ISSUES.md`** for latest issue status
2. **Check `STATUS.md`** (this file) for current state
3. **Review `GUI_TEST_SEQUENCE.md`** for testing procedures
4. **Start with Issue #14** if still unresolved
5. **Verify pending issues** (#10, #13, #15) with user
6. **Complete plotting features** if Issue #14 is resolved

---

## Notes for Future Development

1. **Testability**: Maintain strict separation of concerns. All business logic should be testable without GUI.

2. **Modularity**: Test types are pluggable via `AbstractTestType`. Adding new test types should not require changes to core services.

3. **Error Handling**: Use the global exception handler and error handler utilities. Always provide user-friendly error messages.

4. **Database**: SQLite is used for simplicity. Consider migration to PostgreSQL if scalability becomes an issue.

5. **Performance**: Current implementation loads all Network objects into memory. For very large datasets, consider lazy loading or streaming.

6. **Code Quality**: Extensive comments (8/10 level) are required. All new code should match this standard.

---

## Conclusion

The project is approximately **80% complete**. Core functionality is implemented and working, but Issue #14 (device selection crash) is blocking full testing. Once resolved, the remaining work is primarily:
- Completing plotting features
- Verifying pending fixes
- Final testing and polish

The application architecture is solid, testable, and modular. The codebase is well-commented and follows clean architecture principles.














