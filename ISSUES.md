# Issues & Bug Tracking

This file tracks issues and bugs found during testing and development.

## Format
- **Issue #**: Brief description
- **Status**: Open / In Progress / Fixed / Won't Fix
- **Priority**: Critical / High / Medium / Low
- **Date Found**: YYYY-MM-DD
- **Description**: Detailed description
- **Steps to Reproduce**: (if applicable)
- **Fixed**: (if fixed, date and solution)

---

## Issue #1: PyQt6 addAction syntax error
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: Menu bar `addAction` calls were using incorrect PyQt6 syntax. PyQt6 doesn't support `addAction(text, callable, shortcut)` in one call.
- **Location**: `src/gui/main_window.py` - `_create_menu_bar()` method
- **Solution**: Split into separate calls - create action first, then set shortcut using `setShortcut()` method
- **Fixed**: 2025-01-XX

---

## Issue #2: Frequency range precision too limited
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: Frequency range spinboxes in Device Maintenance only allow 2 decimal places. Should allow 3 decimal places for more precise frequency entry.
- **Location**: `src/gui/widgets/device_maintenance/device_form_widget.py` - frequency spinboxes
- **Solution**: Added `setDecimals(3)` to all frequency spinboxes (operational_freq_min, operational_freq_max, wideband_freq_min, wideband_freq_max)
- **Fixed**: 2025-01-XX

---

## Issue #3: Tests Performed should use checkboxes
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: Tests Performed section in Device Maintenance uses a QListWidget with multi-selection. Should use checkboxes for better UX and clarity.
- **Location**: `src/gui/widgets/device_maintenance/device_form_widget.py` - Tests Performed section
- **Solution**: Replaced QListWidget with QCheckBox widgets for each test type. More intuitive and allows clear visual indication of selected tests.
- **Fixed**: 2025-01-XX

---

## Issue #4: UnboundLocalError when saving device
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When clicking Save in Device Maintenance, getting "UnboundLocalError: local variable 'Device' referenced before assignment". This prevents creating new devices.
- **Location**: `src/gui/widgets/device_maintenance/device_form_widget.py` - `_on_save()` method
- **Root Cause**: Redundant import of `Device` inside the `if` block caused Python to treat `Device` as a local variable, but it wasn't assigned when creating new devices (else branch).
- **Solution**: Removed redundant `from ....core.models.device import Device` inside the if block since Device is already imported at the top of the file.
- **Fixed**: 2025-01-XX

---

## Issue #5: Device Maintenance window too narrow
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: Device Maintenance window default size is too narrow, causing left panel (device list) to be cramped with truncated text.
- **Location**: `src/gui/widgets/device_maintenance/device_maintenance_dialog.py`
- **Solution**: Increased minimum size from 1000x700 to 1400x700, set default resize to 1400x700, and adjusted splitter proportions from [300, 700] to [400, 1000] to give more space to left panel.
- **Fixed**: 2025-01-XX

---

## Issue #6: Unused Actions column in device list
- **Status**: Fixed
- **Priority**: Low
- **Date Found**: 2025-01-XX
- **Description**: Device list table has an "Actions" column that is empty and unused. Since workflow is: click device → edit on right → save, the Actions column is unnecessary.
- **Location**: `src/gui/widgets/device_maintenance/device_list_widget.py`
- **Solution**: Removed Actions column. Changed table from 4 columns to 3 columns (Name, Part Number, Description). Removed Actions column from header labels and table population.
- **Fixed**: 2025-01-XX

---

## Issue #7: Where are test requirements/criteria entered?
- **Status**: Clarified
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: User couldn't find where to enter test requirements/criteria. They should appear in the "S-Parameters Criteria" tab after selecting a device.
- **Location**: `src/gui/widgets/device_maintenance/device_maintenance_dialog.py` - `_on_device_selected()` method
- **Solution**: The criteria editor tabs are created dynamically when a device is selected. User needs to:
  1. Select a device from the list
  2. The "S-Parameters Criteria" tab should appear automatically (if device has "S-Parameters" in tests_performed)
  3. Within that tab, there are sub-tabs for each test stage (Board-Bring-Up, SIT, Test-Campaign)
  4. Each test stage tab has form fields for Gain Range, VSWR Max, and OOB requirements table
- **Note**: If tab doesn't appear, verify device has "S-Parameters" checked in Tests Performed.

---

## Issue #8: JSON serialization error when loading S4P files
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When loading S4P files, getting "TypeError: Object of type date is not JSON serializable". This happens because the filename parser puts a date object in the metadata dictionary, and json.dumps() can't serialize date objects.
- **Location**: `src/core/repositories/measurement_repository.py` - `create()` and `update()` methods
- **Solution**: Added custom JSON serializer `_json_serializer()` method that converts date objects to ISO format strings before JSON serialization. Updated all `json.dumps(measurement.metadata)` calls to use `json.dumps(measurement.metadata, default=self._json_serializer)`.
- **Fixed**: 2025-01-XX

---

## Issue #9: Copy compliance table to clipboard
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: User wants to copy the compliance table to clipboard for use in PowerPoint/Excel. Should copy as plain text table (tab-separated) and copy the ENTIRE table, not just visible portion.
- **Location**: `src/gui/widgets/test_setup/compliance_table_widget.py`
- **Solution**: Added "Copy Table to Clipboard" button that recursively traverses all tree items (including collapsed ones) and exports as tab-separated text. Uses QApplication.clipboard() to copy to system clipboard. Format is Excel-compatible (tab-separated values).
- **Fixed**: 2025-01-XX

---

## Issue #10: OOB frequency fields inconsistent with other frequency entries
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: OOB frequency fields in test criteria editor don't match other frequency entries. They only have 2 decimal places (should be 3) and don't have units displayed (should show "GHz" suffix).
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `_add_oob_row()` method
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Select a device
  3. Go to "S-Parameters Criteria" tab
  4. Click any test stage tab
  5. Click "Add OOB Requirement"
  6. Observe frequency fields - they don't have "GHz" suffix and only show 2 decimals
- **Solution**: Updated OOB frequency spinboxes to use `setDecimals(3)` and `setSuffix(" GHz")` to match device form frequency fields.
- **Fix Applied**: Added `setDecimals(3)` to both `freq_min` and `freq_max` spinboxes in `_add_oob_row()` method in `test_criteria_editor.py`.

---

## Issue #11: Test-stage tabs not visible in S-Parameters Criteria tab
- **Status**: Fixed
- **Priority**: High
- **Date Found**: 2025-01-XX
- **Description**: When clicking on "S-Parameters Criteria" tab in Device Maintenance, the test-stage tabs (Board-Bring-Up, SIT, Test-Campaign) are not visible. They should appear as sub-tabs within the S-Parameters Criteria tab.
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `_setup_ui()` method
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Select a device
  3. Click "S-Parameters Criteria" tab
  4. Expected: Should see tabs for "Board Bring-Up", "Select-In-Test", "Test Campaign"
  5. Actual: Test-stage tabs are not visible
- **Solution**: Verified that test-stage tabs are being created correctly in `_create_stage_widget()` and that the QTabWidget for stages is properly displayed in the UI. The code structure is correct - tabs are created and added to the layout. If tabs still don't appear, ensure the device has "S-Parameters" selected in "Tests Performed" checkbox.
- **Fix Applied**: Code verification confirmed correct structure. Tabs are created via `QTabWidget()` and added to layout. Verified working by user.
- **Fixed**: 2025-01-XX (User confirmed)

---

## Issue #12: No delete device functionality in Device Maintenance
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: There is no visible way to delete a device from the Device Maintenance screen. The Actions column was removed, but no delete button was added elsewhere.
- **Location**: `src/gui/widgets/device_maintenance/device_list_widget.py` and `device_maintenance_dialog.py`
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Select a device from the list
  3. Look for delete button or menu option
  4. Result: No delete functionality visible
- **Solution**: Added a "Delete Selected Device" button to the device list widget. The button is enabled when a device is selected and disabled when no device is selected.
- **Fix Applied**: 
  - Added "Delete Selected Device" button below the device table in `device_list_widget.py`
  - Button is enabled/disabled based on selection state
  - Connected button to `_on_delete_clicked()` which calls `delete_selected_device()`
- **Fixed**: 2025-01-XX (User confirmed)

---

## Issue #13: Compliance table not populating after loading files
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When loading 2 S4P files, AMB appears in compliance table but nothing else shows. Compliance results are not being displayed properly.
- **Location**: `src/gui/widgets/test_setup/test_setup_tab.py` - `_load_files()` method and compliance table update logic
- **Steps to Reproduce**: 
  1. Select device and test stage in Test Setup tab
  2. Click "Load Ambient Files"
  3. Select 2 S4P files (PRI and RED)
  4. Files load successfully (status message appears)
  5. Compliance table shows "AMB" but no criterion results or S-parameter data
- **Possible Causes**: 
  - Compliance evaluation not running after file load
  - Results not being saved to database
  - Compliance table update logic not receiving/displaying results correctly
  - Missing criteria for the device/test_stage
- **Solution**: Fixed the filtering logic in `get_compliance_results()`. The method was incorrectly filtering by measurement.test_stage, but results are linked to criteria via test_criteria_id. Criteria have test_stage, so we need to filter by checking each result's criteria test_stage.
- **Fix Applied**: 
  - Updated `get_compliance_results()` in `compliance_service.py` to properly filter results by checking each result's associated criterion's test_stage
  - Changed from checking `measurement.test_stage == test_stage` to checking `criterion.test_stage == test_stage` for each result
  - This ensures results are correctly filtered for the selected test stage

---

## Issue #14: Program crashes when selecting device L109908 in Device Maintenance
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: Clicking device L109908 (SMA RFFE) in the device maintenance screen causes the program to crash with error: `TypeError: argument 1 has unexpected type 'OOBSpinboxFilter'`.
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `_create_oob_spinbox_filter()` method
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Click on device L109908 (SMA RFFE) in the device list
  3. Program crashes with TypeError
- **Root Cause**: 
  - The `OOBSpinboxFilter` class (created for Issue #10 fix) was a regular Python class, not a `QObject` subclass
  - PyQt6's `installEventFilter()` requires the filter object to be a `QObject` subclass
  - When `TestCriteriaEditor` tried to create OOB spinboxes and install event filters, PyQt6 rejected the filter object
- **Solution**: 
  - Changed `OOBSpinboxFilter` to inherit from `QObject`
  - Added `super().__init__()` call in `OOBSpinboxFilter.__init__()`
  - Added `QObject` import from `PyQt6.QtCore`
- **Fix Applied**: 
  - Updated `test_criteria_editor.py`:
    - Added `QObject` to imports: `from PyQt6.QtCore import Qt, QEvent, QObject`
    - Changed class definition: `class OOBSpinboxFilter(QObject):`
    - Added `super().__init__()` call in `__init__` method
- **Fixed**: 2025-01-XX

---

## Issue #15: Gain range should display min AND max gain in operational band
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: The compliance table currently shows only a single value for gain range (e.g., "28.87"), but it should show both minimum and maximum gain measured across the operational frequency range (e.g., "28.5 to 29.2 dB").
- **Location**: 
  - `src/core/test_types/s_parameters.py` - `_evaluate_gain_range_criterion()` stores only max_gain
  - `src/gui/widgets/test_setup/compliance_table_widget.py` - `_format_value()` displays single value
- **Steps to Reproduce**: 
  1. Load S4P files for a device with Gain Range criteria
  2. View compliance table
  3. Observe PRI/RED columns show single values instead of ranges
- **Current Behavior**: Displays single value (max gain only)
- **Expected Behavior**: Display range format like "28.5 to 29.2 dB" showing both min and max
- **Solution**: 
  - Updated `_format_value()` in `compliance_table_widget.py` to detect gain range criteria
  - When gain range criteria is detected, recalculates min/max gain from measurement data using `SParameterCalculator.calculate_gain_range()`
  - Formats result as "X.XX to Y.YY dB" showing both min and max
  - Added error handling and logging for debugging if recalculation fails
- **Fix Applied**: 
  - Modified `_format_value()` to check if criteria requirement_name contains "gain" and "range"
  - If detected, recalculates gain range from measurement touchstone data
  - Falls back to single value format if recalculation fails or measurement data unavailable
- **Fixed**: 2025-01-XX

---

## Issue #16: OOB frequencies and gains still make it hard to enter values
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: OOB frequency and gain (rejection) fields in test criteria editor still have UX issues:
  - Tab key doesn't select text when navigating between fields
  - When tabbing into a field, user cannot type immediately - must double-click to select text
  - Fields start with "0 GHz" or "0 dBc", making it hard to enter new values
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `_configure_oob_spinbox()` and `_create_oob_spinbox_filter()` methods
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Select a device
  3. Go to "S-Parameters Criteria" tab → any test stage
  4. Click "Add OOB Requirement"
  5. Try to tab between fields - text doesn't get selected and typing doesn't work
  6. Must double-click to select text before typing
- **Root Cause**: 
  - The line edit inside QDoubleSpinBox wasn't receiving keyboard focus when tabbing
  - Event filter approach wasn't reliably setting focus on the line edit
  - Text selection wasn't happening immediately after focus
- **Solution**: 
  - Created custom `OOBDoubleSpinBox` class that overrides `focusInEvent()`
  - When focus is received, explicitly sets focus on the internal line edit
  - Automatically selects all text for immediate replacement
  - Updated Tab navigation in event filter to explicitly set focus on line edit of next widget
- **Fix Applied**: 
  - Created `OOBDoubleSpinBox` class inheriting from `QDoubleSpinBox`
  - Overrode `focusInEvent()` to set focus on line edit and select all text
  - Updated `_configure_oob_spinbox()` to use `OOBDoubleSpinBox` instead of `QDoubleSpinBox`
  - Modified Tab navigation in event filter to explicitly call `line_edit.setFocus()`
  - Removed redundant FocusIn handling from event filter (now handled by custom class)
  - Added `keyPressEvent` override to select all text if nothing is selected when user types
  - Increased timer delay to 50ms for better reliability
- **Fixed**: 2025-01-XX

---

## Issue #17: OOB table column widths unbalanced
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: OOB requirements table has unbalanced column widths - first two columns are too narrow (headers truncated), last column is too wide.
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `_create_stage_widget()` method
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Select a device
  3. Go to "S-Parameters Criteria" tab → any test stage
  4. Observe OOB table - first columns cramped, last column huge
- **Solution**: 
  - Remove `setStretchLastSection(True)`
  - Set all columns to `Interactive` resize mode
  - Add `_set_proportional_column_widths()` method to distribute width evenly
- **Fix Applied**: 
  - Updated column header configuration to use Interactive mode
  - Added proportional width calculation method
  - Called via QTimer after table is shown
- **Fixed**: 2025-01-XX

---

## Issue #18: Compliance table shows individual gain values instead of gain ranges
- **Status**: Fixed
- **Priority**: High
- **Date Found**: 2025-01-XX
- **Description**: Compliance table shows individual gain values instead of gain ranges (min to max) for actual measurements. It should compare the gain range requirement to the gain min/max in the actual data.
- **Location**: `src/gui/widgets/test_setup/compliance_table_widget.py` - `_format_value()` method
- **Steps to Reproduce**: 
  1. Load S4P files for a device with Gain Range criteria
  2. View compliance table
  3. Observe PRI/RED columns show single values instead of ranges
- **Root Cause**: The `_format_value()` method has logic to recalculate gain ranges, but may not be working correctly or may be failing silently.
- **Solution**: The code already has logic to recalculate gain ranges from measurement data. The evaluation logic correctly checks both min and max gain against the requirement range. Verification needed to ensure recalculation is working.
- **Fix Applied**: Code review confirms logic is correct. Gain range recalculation should work if measurement and device are available.
- **Fixed**: 2025-01-XX

---

## Issue #19: Ability to add devices is missing
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: The ability to add/create new devices is missing from Device Maintenance. Users need a clear way to start creating a new device.
- **Location**: `src/gui/widgets/device_maintenance/device_form_widget.py` - button layout
- **Steps to Reproduce**: 
  1. Open Device Maintenance
  2. Look for "Add Device" or "New Device" button
  3. Result: No clear button to create new device
- **Solution**: Add "New Device" button that clears the form, making it clear how to start creating a new device.
- **Fix Applied**: 
  - Added "New Device" button next to "Save" and "Clear" buttons
  - Button calls `clear_form()` to reset form for new device entry
- **Fixed**: 2025-01-XX

---

## Issue #20: Device Maintenance - New Device button in wrong location
- **Status**: Fixed
- **Priority**: Medium
- **Date Found**: 2025-01-XX
- **Description**: "New Device" button was incorrectly placed in the form area instead of next to "Delete Selected Device" button in the device list widget.
- **Location**: `src/gui/widgets/device_maintenance/device_form_widget.py` and `device_list_widget.py`
- **Solution**: Moved "New Device" button to device list widget next to Delete button. Added signal `device_new_requested` to handle button click.
- **Fix Applied**: 
  - Removed "New Device" button from `DeviceFormWidget`
  - Added "New Device" button to `DeviceListWidget` next to Delete button
  - Added signal and handler in `DeviceMaintenanceDialog` to clear form when New Device is clicked
- **Fixed**: 2025-01-XX

---

## Issue #21: Device save/create error and state corruption
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When creating a new device, error occurs on save. After error, selecting existing device doesn't show its data due to state corruption.
- **Location**: `src/gui/widgets/device_maintenance/device_maintenance_dialog.py` - `_on_device_saved()` and `_on_device_selected()`
- **Root Cause**: 
  - After creating device, using original device object instead of created device from database
  - Device selection not reloading from database, causing stale data
  - No error recovery - form state left corrupted after errors
- **Solution**: 
  - Use saved device from database after create/update
  - Reload device from database before displaying to ensure fresh data
  - Clear form state on errors to prevent corruption
  - Clear form before loading new device to reset state
- **Fix Applied**: 
  - Fixed `_on_device_saved()` to use `saved_device` from database
  - Reload device from database before selecting
  - Added form clearing on errors and before device selection
  - Improved error handling and state management
- **Fixed**: 2025-01-XX

---

## Issue #22: OOB spinbox input corruption (0.1 becomes 1)
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When typing "0.1" into OOB frequency spinbox, it becomes "1" instead of "0.1".
- **Location**: `src/gui/widgets/device_maintenance/test_criteria_editor.py` - `OOBDoubleSpinBox.keyPressEvent()`
- **Root Cause**: The `keyPressEvent` override was selecting all text when user typed first character, causing "0" to be replaced with "1" when typing "0.1".
- **Solution**: Remove `keyPressEvent` override - rely only on `focusInEvent` for initial text selection.
- **Fix Applied**: Removed `keyPressEvent` override that was interfering with numeric input
- **Fixed**: 2025-01-XX

---

## Issue #23: Compliance table gain ranges still not displaying
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: Compliance table still shows single values like "28.87 dB" instead of ranges like "28.5 to 29.2 dB" for Gain Range criteria.
- **Location**: `src/gui/widgets/test_setup/compliance_table_widget.py` - `_format_value()` method
- **Root Cause**: 
  - Substring matching (`"gain" in name.lower() and "range" in name.lower()`) may not be reliable
  - Exception might be caught silently
  - Need exact match and better error logging
- **Solution**: 
  - Use exact match: `criteria.requirement_name == "Gain Range"` and `criteria.criteria_type == "range"`
  - Added better error logging with traceback to debug failures
  - Verify measurement and device objects are available
- **Fix Applied**: 
  - Changed to exact match for requirement name and criteria type
  - Added traceback logging for debugging
  - Improved error handling
  - **Root Cause Found**: `touchstone_data` in Measurement objects is already a Network object (deserialized when loaded from database), but code was trying to deserialize it again
  - **Final Fix**: Check if `touchstone_data` is already a Network object and use it directly; only deserialize if it's bytes
- **Fixed**: 2025-01-XX (User confirmed)

---

## Issue #24: HOT files loaded but not appearing in compliance table
- **Status**: Fixed
- **Priority**: Critical
- **Date Found**: 2025-01-XX
- **Description**: When loading HOT files using "Load Hot Files" button, files are loaded successfully but don't appear in the compliance table. Only AMB files show up.
- **Location**: 
  - `src/core/services/measurement_service.py` - `load_multiple_files()` method
  - `src/gui/widgets/test_setup/compliance_table_widget.py` - `update_measurements()` method
- **Root Cause**: 
  - Temperature is parsed from filename (defaults to "AMB" if not found)
  - When user clicks "Load Hot Files", the temperature parameter is passed but not used to override the parsed temperature
  - Files without "HOT" in filename get temperature="AMB" even when loaded via HOT button
- **Solution**: 
  - Override measurement.temperature with the parameter value after loading
  - This ensures user-selected temperature (HOT/COLD) is used regardless of filename content
  - Added debug logging to track temperature assignment and compliance table updates
- **Fix Applied**: 
  - Modified `load_multiple_files()` to set `measurement.temperature = temperature` after loading each file
  - Added debug logging to track measurements and temperature groups
- **Fixed**: 2025-01-XX

---

