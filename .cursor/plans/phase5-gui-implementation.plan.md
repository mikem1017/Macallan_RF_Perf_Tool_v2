# Phase 5: GUI Implementation

## Overview

Build the PyQt6 GUI layer that provides a user-friendly interface for all three main functions. The GUI uses a main window with tabs for Test Setup and Plotting Controls. Device Maintenance is accessed via a menu item that opens a modal dialog. Plot windows are separate, allowing multiple plots to be open simultaneously.

## Application Structure

- **Main Window**: Single window with tabs
  - Tab 1: Test Setup
  - Tab 2: Plotting Controls/Setup
  - Menu Bar: File, Edit, Tools (Device Maintenance), View, Help
- **Device Maintenance**: Modal dialog opened from Tools menu
- **Plot Windows**: Separate windows opened from Plotting Controls tab
  - Multiple plot windows can be open simultaneously
  - Each plot window can display different data (operational gain, operational VSWR, wideband gain, wideband VSWR, etc.)

## Device Maintenance Dialog

- **Device List**: Table view with columns (Name, Part Number, Description, Actions)
  - Left side: Table of devices with Edit/Delete buttons
  - Right side: Form for creating/editing device
- **Test Criteria Editor**: 
  - Tabs for each test type (currently only S-Parameters)
  - Within each test type tab, tabs for each test stage (Board-Bring-Up, SIT, Test-Campaign)
  - Single-value criteria (Gain Range, VSWR Max) → Form fields
  - Multi-row criteria (OOB requirements) → Table view with add/remove rows
  - OOB table columns: Frequency Min, Frequency Max, Rejection >= (dBc)

## Test Setup Tab

- **Device Selection**: Dropdown to select device
- **Test Stage Selection**: Dropdown to select test stage (Board-Bring-Up, SIT, Test-Campaign)
- **Test Type Tabs**: Tabs for each test type the device undergoes (currently S-Parameters)
- **File Loaders**: Separate buttons for Hot, Cold, and Ambient temperatures
  - Each button opens single file dialog accepting multiple files (2 or 4 files)
  - Standard mode: 2 files (PRI, RED)
  - Multi-gain mode: 4 files (PRI_HG, PRI_LG, RED_HG, RED_LG)
- **Compliance Table**: Hierarchical tree view with 6 columns
  - Columns: Requirement, Limit, PRI (value), PRI Status, RED (value), RED Status
  - Hierarchy: Temperature → Criterion Type → S-parameter
  - Collapsible/expandable sections
  - Aggregate pass/fail status at each level
  - Automatically re-evaluates when test stage changes

## Plotting Controls Tab

- **Plot Creation**: Buttons/dropdown to create new plot windows
  - Plot types: Operational Gain, Operational VSWR, Wideband Gain, Wideband VSWR
- **Plot Management**: List of open plot windows
- **Manual Refresh**: Button to refresh data from loaded measurements

## Plot Windows

- **Filtering Controls**: Checkboxes for multi-select filtering
  - HG/LG (high-gain/low-gain) - if multi-gain mode
  - Amb/Hot/Cold (temperature)
  - Pri/Red (path type)
  - Individual S-parameters (S21, S31, S41, etc.)
- **Matplotlib Plot**: Interactive plot with data
- **Axis Controls**: Min/max for X and Y axes
- **Title Controls**: Editable plot title (dynamic based on device, serial number, etc.)
- **Export**: Save plot, copy to clipboard buttons

## Error Handling

- **Critical Errors**: Modal error dialogs (blocking)
  - File load failures
  - Database errors
  - Validation failures that block operation
- **Warnings**: Non-modal status bar/message area
  - Part number mismatch
  - Serial number mismatch
  - Stale results notifications

## Database Initialization

- Automatically create database if it doesn't exist
- Database location: Same directory as .exe or .bat file
- Uses `src/database/schema.py` to create schema

## Application Entry Point

- **Development**: `main.py` file that launches the GUI
- **Production**: `.bat` file (calls `main.py`)
- **Ultimate Goal**: `.exe` file (using PyInstaller or similar)

## Implementation Tasks

### 1. Main Application Window
- Create `MainWindow` class with QTabWidget
- Implement Test Setup tab
- Implement Plotting Controls tab
- Add menu bar with Device Maintenance option
- Handle database initialization on startup

### 2. Device Maintenance Dialog
- Create `DeviceMaintenanceDialog` class (modal)
- Device list table with CRUD operations
- Device form for creating/editing
- Test criteria editor with tabs
- Integration with DeviceService

### 3. Test Setup Tab
- Device and test stage dropdowns
- Test type tabs (dynamic based on device.tests_performed)
- File loader buttons (Hot, Cold, Ambient)
- File dialog for multiple file selection
- Integration with MeasurementService and ComplianceService
- Compliance table with hierarchical tree view

### 4. Plotting Controls Tab
- Plot creation interface
- Plot window management
- Manual refresh button

### 5. Plot Windows
- Create `PlotWindow` class (separate QMainWindow)
- Filtering controls (checkboxes)
- Matplotlib integration with matplotlib.backends.backend_qt5agg
- Axis controls (spinboxes or sliders)
- Title editing
- Export functionality (save, copy to clipboard)

### 6. Service Integration
- Create service instances with dependency injection
- Initialize repositories with database connection
- Wire GUI events to service methods
- Handle errors and display appropriate messages

### 7. Testing
- pytest-qt tests for GUI components
- Mock services for GUI testing
- Test user interactions and workflows

## Files to Create

### Main Application
- `src/gui/main_window.py` - Main application window
- `src/gui/main.py` - Application entry point
- `main.bat` - Batch file for Windows

### Device Maintenance
- `src/gui/widgets/device_maintenance/device_maintenance_dialog.py`
- `src/gui/widgets/device_maintenance/device_list_widget.py`
- `src/gui/widgets/device_maintenance/device_form_widget.py`
- `src/gui/widgets/device_maintenance/test_criteria_editor.py`

### Test Setup
- `src/gui/widgets/test_setup/test_setup_tab.py`
- `src/gui/widgets/test_setup/compliance_table_widget.py`
- `src/gui/widgets/test_setup/file_loader_widget.py`

### Plotting
- `src/gui/widgets/plotting/plotting_controls_tab.py`
- `src/gui/widgets/plotting/plot_window.py`
- `src/gui/widgets/plotting/plot_controls_widget.py`

### Utilities
- `src/gui/utils/error_handler.py` - Error dialog and status bar utilities
- `src/gui/utils/service_factory.py` - Factory for creating service instances

## Testing Strategy

- Use pytest-qt for GUI testing
- Mock all services to test UI logic in isolation
- Test user workflows: device creation → file loading → compliance → plotting
- Test error handling and edge cases











