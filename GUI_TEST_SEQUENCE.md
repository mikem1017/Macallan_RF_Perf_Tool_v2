# GUI Test Sequence

This document provides a systematic test sequence for validating all GUI functionality in the Macallan RF Performance Tool.

## Test Environment Setup

1. Launch application: `python3 -m src.gui.main`
2. Verify main window opens with two tabs: "Test Setup" and "Plotting"
3. Verify menu bar is present: File, Edit, Tools, View, Help

---

## Test Sequence 1: Device Maintenance

### 1.1 Open Device Maintenance Dialog
- **Action**: Click Tools → Device Maintenance (or press Ctrl+D)
- **Expected**: Device Maintenance dialog opens
- **Verify**: 
  - Window is wider (1400px default)
  - Left panel shows device list table
  - Right panel shows "Device Info" tab
  - Table has 3 columns: Name, Part Number, Description (no Actions column)

### 1.2 Create New Device
- **Action**: Fill in device form:
  - Name: "Test Device 1"
  - Part Number: "L123456"
  - Description: "Test description"
  - Operational Frequency: Min=0.5 GHz, Max=2.0 GHz (test 3 decimal places)
  - Wideband Frequency: Min=0.1 GHz, Max=5.0 GHz
  - Multi-Gain Mode: Unchecked
  - Input Ports: "1"
  - Output Ports: "2, 3, 4"
  - Tests Performed: Check "S-Parameters"
- **Action**: Click "Save"
- **Expected**: 
  - Device saved successfully message
  - Device appears in left panel table
  - Form clears for next entry

### 1.3 Edit Existing Device
- **Action**: Click on device in left panel table
- **Expected**: 
  - Device data loads into form on right
  - "S-Parameters Criteria" tab appears automatically
- **Action**: Change description, click "Save"
- **Expected**: Changes saved, table updates

### 1.4 Test Criteria - Gain Range
- **Action**: Click "S-Parameters Criteria" tab
- **Expected**: Three sub-tabs: "Board Bring-Up", "Select-In-Test", "Test Campaign"
- **Action**: Click "Select-In-Test" tab
- **Action**: Set Gain Range: Min=27.5 dB, Max=31.3 dB
- **Action**: Click "Save All Criteria" button
- **Expected**: Success message, criteria saved

### 1.5 Test Criteria - VSWR Max
- **Action**: In same "Select-In-Test" tab
- **Action**: Set VSWR Max: 2.0
- **Action**: Click "Save All Criteria"
- **Expected**: Criteria saved

### 1.6 Test Criteria - OOB Requirements
- **Action**: In "Select-In-Test" tab
- **Action**: Click "Add OOB Requirement" button
- **Expected**: New row appears in OOB table
- **Action**: Fill in:
  - Frequency Min: 0.1 GHz
  - Frequency Max: 0.5 GHz
  - Rejection >=: 60.0 dBc
- **Action**: Click "Add OOB Requirement" again, add second requirement
- **Action**: Click "Save All Criteria"
- **Expected**: Both OOB requirements saved

### 1.7 Test Criteria - Multiple Test Stages
- **Action**: Click "Board-Bring-Up" tab
- **Action**: Set different values (Gain Range: 25.0-32.0 dB, VSWR Max: 2.5)
- **Action**: Click "Save All Criteria"
- **Expected**: Different criteria saved for different test stage

### 1.8 Window Size Verification
- **Action**: Check window dimensions
- **Expected**: Window is at least 1400px wide (not cramped)

### 1.9 Delete Device
- **Action**: Select device in table
- **Action**: (If delete button exists, use it; otherwise verify deletion workflow)
- **Expected**: Confirmation dialog if device has related data

---

## Test Sequence 2: Test Setup Tab

### 2.1 Device Selection
- **Action**: Go to Test Setup tab in main window
- **Action**: Select device from "Device" dropdown
- **Expected**: 
  - Device selected
  - Test type tabs appear (S-Parameters tab)

### 2.2 Test Stage Selection
- **Action**: Select "SIT" from "Test Stage" dropdown
- **Expected**: Test stage changes

### 2.3 Load Ambient Files
- **Action**: Click "Load Ambient Files" button
- **Action**: Select 2 S4P files (PRI and RED) from file dialog
- **Expected**: 
  - Files load successfully
  - Status message confirms loading
  - No JSON serialization errors
  - Compliance table updates

### 2.4 Load Multiple Temperatures
- **Action**: Click "Load Hot Files" button
- **Action**: Select 2 S4P files
- **Expected**: Hot files loaded
- **Action**: Click "Load Cold Files" button
- **Action**: Select 2 S4P files
- **Expected**: Cold files loaded

### 2.5 Compliance Table Display
- **Action**: Verify compliance table shows:
  - Hierarchical structure: Temperature → Criterion → S-parameter
  - All 6 columns visible
  - Pass/fail status color-coded (green/red)
  - Expandable/collapsible sections
- **Expected**: Table displays all compliance results

### 2.6 Change Test Stage
- **Action**: Change "Test Stage" dropdown to "Board-Bring-Up"
- **Expected**: 
  - Compliance table automatically updates
  - Shows results for Board-Bring-Up criteria (different values)

### 2.7 Copy Compliance Table
- **Action**: Click "Copy Table to Clipboard" button
- **Expected**: 
  - Status message: "Copied X rows to clipboard"
  - Table copied to clipboard
- **Action**: Paste into Excel or text editor
- **Expected**: 
  - Tab-separated format
  - All rows present (including collapsed ones)
  - Hierarchical indentation preserved

---

## Test Sequence 3: Plotting Controls Tab

### 3.1 Create Plot Window
- **Action**: Go to "Plotting" tab
- **Action**: Select "Operational Gain" from "Plot Type" dropdown
- **Action**: Click "Create Plot Window"
- **Expected**: New plot window opens

### 3.2 Plot Window Features
- **Action**: In plot window, verify:
  - Filtering controls (checkboxes) for Temperature, Path, S-parameters
  - Matplotlib plot area
  - Axis controls (X Min/Max, Y Min/Max)
  - Title edit field
  - "Save Plot" button
  - "Copy to Clipboard" button
- **Expected**: All controls present

### 3.3 Multiple Plot Windows
- **Action**: Create another plot window (Operational VSWR)
- **Expected**: Second window opens independently
- **Action**: Create third window (Wideband Gain)
- **Expected**: All three windows can be open simultaneously

### 3.4 Plot Filtering
- **Action**: In plot window, uncheck "Hot" temperature
- **Action**: Uncheck "Cold" temperature
- **Expected**: Plot updates (if data available)

---

## Test Sequence 4: Error Handling

### 4.1 Invalid Part Number
- **Action**: In Device Maintenance, try to enter part number "ABC123"
- **Expected**: Validation error (must be Lnnnnnn format)

### 4.2 Invalid Frequency Range
- **Action**: Set operational frequency min > max
- **Action**: Click Save
- **Expected**: Validation error

### 4.3 Missing Required Fields
- **Action**: Try to save device without name
- **Expected**: Validation error

### 4.4 File Load Errors
- **Action**: Try to load non-Touchstone file
- **Expected**: Error dialog with clear message

### 4.5 Wrong File Count
- **Action**: Try to load 3 files when device expects 2
- **Expected**: Validation error with helpful message

---

## Test Sequence 5: Workflow Integration

### 5.1 Complete Workflow
1. Create device in Device Maintenance
2. Set test criteria for SIT stage
3. Go to Test Setup tab
4. Select device and SIT stage
5. Load ambient files
6. Verify compliance table shows results
7. Copy compliance table to clipboard
8. Create plot window
9. Verify plot displays data

### 5.2 Multi-Temperature Workflow
1. Load files for all three temperatures (Amb, Hot, Cold)
2. Verify compliance table shows all temperatures
3. Verify hierarchical structure shows temperature → criterion → S-parameter
4. Verify aggregate pass/fail at each level

### 5.3 Test Stage Comparison
1. Set different criteria for SIT vs Board-Bring-Up
2. Load same measurement files
3. Switch between test stages
4. Verify compliance table updates with different results

---

## Test Sequence 6: Edge Cases

### 6.1 Empty Device List
- **Action**: Open Device Maintenance with no devices
- **Expected**: Empty table, form ready for new device

### 6.2 No Measurements
- **Action**: Select device with no loaded files
- **Expected**: Compliance table is empty or shows message

### 6.3 No Criteria Defined
- **Action**: Load files for device with no test criteria
- **Expected**: Compliance table empty or shows "No criteria defined"

### 6.4 Very Long Descriptions
- **Action**: Enter very long device description (200+ characters)
- **Expected**: Description field handles it, table truncates with "..."

---

## Test Checklist

- [ ] Device Maintenance opens correctly
- [ ] Create device works
- [ ] Edit device works
- [ ] Save device works
- [ ] Test criteria tabs appear
- [ ] Gain Range criteria saves
- [ ] VSWR Max criteria saves
- [ ] OOB requirements table works (add/remove)
- [ ] Multiple test stages work independently
- [ ] Device list table displays correctly (no Actions column)
- [ ] Window is wide enough (not cramped)
- [ ] Test Setup tab loads
- [ ] Device selection works
- [ ] Test stage selection works
- [ ] File loading works (Ambient)
- [ ] File loading works (Hot)
- [ ] File loading works (Cold)
- [ ] Compliance table displays correctly
- [ ] Compliance table updates when test stage changes
- [ ] Copy to clipboard works
- [ ] Pasted data is tab-separated
- [ ] All rows copied (not just visible)
- [ ] Plotting tab works
- [ ] Plot windows can be created
- [ ] Multiple plot windows work
- [ ] Error handling works
- [ ] Complete workflow works end-to-end

---

## Notes

- Test with real S4P files from `tests/data/` directory
- Verify all messages/notifications appear correctly
- Check that status bar messages appear for warnings
- Verify color coding in compliance table (green=pass, red=fail)
- Test keyboard shortcuts (Ctrl+Q, Ctrl+D)











