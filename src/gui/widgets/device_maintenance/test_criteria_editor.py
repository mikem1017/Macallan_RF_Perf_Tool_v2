"""
Test criteria editor widget.

This module provides a widget for editing test criteria for a specific
device, test type, and test stage. It supports form fields for single-value
criteria and a table for multi-row criteria (OOB requirements).
"""

from typing import Optional
from uuid import UUID
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout,
    QDoubleSpinBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, QEvent, QObject, QTimer, pyqtSignal

from ....core.models.device import Device
from ....core.models.test_criteria import TestCriteria
from ....core.services.device_service import DeviceService
from ....core.test_stages import TEST_STAGES, get_test_stage_display_name
from ...utils.error_handler import handle_exception


class OOBDoubleSpinBox(QDoubleSpinBox):
    """
    Custom QDoubleSpinBox for OOB fields that properly handles focus and text selection.
    
    When the spinbox receives focus (via Tab or click), it automatically:
    - Sets focus on the internal line edit
    - Selects all text for immediate replacement
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = None
        self._row = None
        self._col = None
    
    def focusInEvent(self, event):
        """Override to ensure line edit gets focus and text is selected."""
        super().focusInEvent(event)
        # Explicitly set focus on the line edit and select all text
        line_edit = self.lineEdit()
        if line_edit:
            # Set focus explicitly on line edit first
            line_edit.setFocus()
            # Use QTimer with longer delay to ensure focus is fully established
            QTimer.singleShot(50, lambda: self._select_all_text())
    
    # Removed keyPressEvent override - it was interfering with numeric input
    # When user types "0.1", selecting all text on first keypress causes "0" to be replaced with "1"
    # The focusInEvent selection is sufficient for initial text selection
    
    def _select_all_text(self):
        """Select all text in the line edit."""
        line_edit = self.lineEdit()
        if line_edit:
            line_edit.selectAll()
            line_edit.setCursorPosition(0)


class TestCriteriaEditor(QWidget):
    """
    Widget for editing test criteria.
    
    Provides tabs for each test stage, and within each tab, form fields
    for single-value criteria (Gain Range, VSWR Max) and a table for
    OOB requirements.
    """
    
    # Signal emitted when criteria are saved
    criteria_saved = pyqtSignal()
    
    def __init__(
        self,
        device: Device,
        test_type: str,
        device_service: DeviceService,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize test criteria editor.
        
        Args:
            device: Device to edit criteria for
            test_type: Test type (e.g., "S-Parameters")
            device_service: DeviceService instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device = device
        self.test_type = test_type
        self.device_service = device_service
        
        # Validate device data before proceeding
        if device is None:
            raise ValueError("Device cannot be None")
        
        # Validate device has required fields - Device model should ensure these exist
        # but add defensive checks anyway
        try:
            # Check all required attributes exist and are valid
            if not hasattr(device, 'id') or device.id is None:
                raise ValueError("Device missing id")
            if not hasattr(device, 'operational_freq_min') or device.operational_freq_min is None:
                raise ValueError("Device missing operational_freq_min")
            if not hasattr(device, 'operational_freq_max') or device.operational_freq_max is None:
                raise ValueError("Device missing operational_freq_max")
            if not hasattr(device, 'tests_performed'):
                raise ValueError("Device missing tests_performed attribute")
            
            # Validate tests_performed is a list
            if not isinstance(device.tests_performed, (list, tuple)):
                raise ValueError(f"Device tests_performed must be a list, got {type(device.tests_performed)}")
            
            # Validate ports are lists
            if not isinstance(device.input_ports, (list, tuple)):
                raise ValueError(f"Device input_ports must be a list, got {type(device.input_ports)}")
            if not isinstance(device.output_ports, (list, tuple)):
                raise ValueError(f"Device output_ports must be a list, got {type(device.output_ports)}")
        except Exception as e:
            # Log validation error
            handle_exception(self, e, "Validating device data")
            raise  # Re-raise to prevent initialization
        
        try:
            self._setup_ui()
        except Exception as e:
            import traceback
            error_msg = f"Error in _setup_ui:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            handle_exception(self, Exception(error_msg), "Setting up test criteria editor UI")
            raise  # Re-raise to let caller handle
        
        try:
            self._load_criteria()
        except Exception as e:
            import traceback
            error_msg = f"Error in _load_criteria:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            handle_exception(self, Exception(error_msg), "Loading test criteria")
            # Don't re-raise - UI is set up, just criteria loading failed
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tabs for each test stage
        self.stage_tabs = QTabWidget()
        
        for stage in TEST_STAGES:
            stage_widget = self._create_stage_widget(stage)
            self.stage_tabs.addTab(stage_widget, get_test_stage_display_name(stage))
        
        layout.addWidget(self.stage_tabs)
        
        # Save button
        save_button = QPushButton("Save All Criteria")
        save_button.clicked.connect(self._save_all_criteria)
        layout.addWidget(save_button)
    
    def _create_stage_widget(self, test_stage: str) -> QWidget:
        """Create widget for a specific test stage."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Form fields for single-value criteria
        form_group = QGroupBox("Criteria")
        form_layout = QFormLayout()
        
        # Gain Range (min/max)
        gain_group = QGroupBox("Gain Range (dB)")
        gain_layout = QHBoxLayout()
        self._gain_min = QDoubleSpinBox()
        self._gain_min.setRange(-100.0, 100.0)
        self._gain_min.setSuffix(" dB")
        self._gain_max = QDoubleSpinBox()
        self._gain_max.setRange(-100.0, 100.0)
        self._gain_max.setSuffix(" dB")
        gain_layout.addWidget(QLabel("Min:"))
        gain_layout.addWidget(self._gain_min)
        gain_layout.addWidget(QLabel("Max:"))
        gain_layout.addWidget(self._gain_max)
        gain_group.setLayout(gain_layout)
        form_layout.addRow(gain_group)
        
        # Store references keyed by stage
        if not hasattr(self, '_gain_mins'):
            self._gain_mins = {}
            self._gain_maxs = {}
            self._vswr_maxs = {}
        
        self._gain_mins[test_stage] = self._gain_min
        self._gain_maxs[test_stage] = self._gain_max
        
        # VSWR Max
        self._vswr_max = QDoubleSpinBox()
        self._vswr_max.setRange(1.0, 10.0)
        self._vswr_max.setSuffix("")
        self._vswr_max.setDecimals(2)
        form_layout.addRow("VSWR Max:", self._vswr_max)
        self._vswr_maxs[test_stage] = self._vswr_max
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # OOB Requirements Table
        oob_group = QGroupBox("Out-of-Band Requirements (Rejection >= dBc)")
        oob_layout = QVBoxLayout()
        
        oob_table = QTableWidget()
        oob_table.setColumnCount(3)
        oob_table.setHorizontalHeaderLabels(["Frequency Min (GHz)", "Frequency Max (GHz)", "Rejection >= (dBc)"])
        
        # Configure column sizing for even distribution
        header = oob_table.horizontalHeader()
        header.setStretchLastSection(False)  # Don't stretch last column
        # Use Interactive mode so columns can be resized and are evenly sized initially
        for col in range(3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set initial column widths proportionally after widget is ready
        # Use a longer delay to ensure table is visible and has proper size
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda table=oob_table: self._set_oob_column_widths(table))
        
        # Store table reference
        if not hasattr(self, '_oob_tables'):
            self._oob_tables = {}
        self._oob_tables[test_stage] = oob_table
        
        # Add/Remove buttons
        oob_buttons = QHBoxLayout()
        add_oob_button = QPushButton("Add OOB Requirement")
        add_oob_button.clicked.connect(lambda: self._add_oob_row(test_stage))
        remove_oob_button = QPushButton("Remove Selected")
        remove_oob_button.clicked.connect(lambda: self._remove_oob_row(test_stage))
        oob_buttons.addWidget(add_oob_button)
        oob_buttons.addWidget(remove_oob_button)
        oob_buttons.addStretch()
        
        oob_layout.addWidget(oob_table)
        oob_layout.addLayout(oob_buttons)
        oob_group.setLayout(oob_layout)
        layout.addWidget(oob_group)
        
        layout.addStretch()
        return widget
    
    def _add_oob_row(self, test_stage: str) -> None:
        """Add a new row to the OOB table."""
        table = self._oob_tables[test_stage]
        row = table.rowCount()
        table.insertRow(row)
        
        # Frequency Min - configure with empty default, select all on focus, tab/enter navigation
        freq_min = self._configure_oob_spinbox(0.0, 1000.0, 3, " GHz", table, row, 0)
        table.setCellWidget(row, 0, freq_min)
        
        # Frequency Max - configure with empty default, select all on focus, tab/enter navigation
        freq_max = self._configure_oob_spinbox(0.0, 1000.0, 3, " GHz", table, row, 1)
        table.setCellWidget(row, 1, freq_max)
        
        # Rejection - configure with empty default, select all on focus, tab/enter navigation
        rejection = self._configure_oob_spinbox(0.0, 200.0, 2, " dBc", table, row, 2)
        table.setCellWidget(row, 2, rejection)
        
        # Set tab order: freq_min -> freq_max -> rejection
        QWidget.setTabOrder(freq_min, freq_max)
        QWidget.setTabOrder(freq_max, rejection)
    
    def _configure_oob_spinbox(
        self,
        min_val: float,
        max_val: float,
        decimals: int,
        suffix: str,
        table: QTableWidget,
        row: int,
        col: int
    ) -> QDoubleSpinBox:
        """
        Configure an OOB spinbox with proper editing behavior.
        
        Sets up:
        - Empty/blank default value (special value text)
        - Select all text on focus
        - Tab and Enter key navigation
        
        Args:
            min_val: Minimum value (actual minimum, but we'll use a sentinel for blank)
            max_val: Maximum value
            decimals: Number of decimal places
            suffix: Unit suffix (e.g., " GHz")
            table: Table widget containing the spinbox
            row: Row number
            col: Column number
            
        Returns:
            Configured QDoubleSpinBox
        """
        spinbox = OOBDoubleSpinBox()
        # Store table reference for navigation
        spinbox._table = table
        spinbox._row = row
        spinbox._col = col
        
        # Use 0.0 as minimum - user can type to replace it immediately on focus
        spinbox.setRange(0.0, max_val)
        spinbox.setDecimals(decimals)
        spinbox.setSuffix(suffix)
        spinbox.setValue(0.0)  # Start at 0.0 - will be selected on focus for easy replacement
        
        # Ensure spinbox is enabled and editable
        spinbox.setEnabled(True)
        spinbox.setReadOnly(False)
        
        # Install event filter to handle Tab and Enter key navigation
        spinbox.installEventFilter(self._create_oob_spinbox_filter(table, row, col))
        
        return spinbox
    
    def _create_oob_spinbox_filter(self, table: QTableWidget, row: int, col: int):
        """
        Create an event filter for OOB spinbox to handle focus and Enter key.
        
        Args:
            table: Table widget
            row: Row number
            col: Column number
            
        Returns:
            Event filter object
        """
        class OOBSpinboxFilter(QObject):
            def __init__(self, table_ref, row_num, col_num):
                super().__init__()
                self.table = table_ref
                self.row = row_num
                self.col = col_num
            
            def eventFilter(self, obj, event):
                """Filter events for the spinbox."""
                # Note: FocusIn is now handled by OOBDoubleSpinBox.focusInEvent()
                # We only handle keyboard navigation here
                
                # Handle Tab, Shift+Tab, Enter, and Return keys
                if event.type() == QEvent.Type.KeyPress:
                    key = event.key()
                    is_tab = key == Qt.Key.Key_Tab
                    is_shift_tab = key == Qt.Key.Key_Backtab or (key == Qt.Key.Key_Tab and event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                    is_enter = key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter
                    
                    if is_tab or is_shift_tab or is_enter:
                        # Determine next field based on key
                        if is_shift_tab:
                            # Move to previous column, or previous row if at first column
                            next_col = (self.col - 1) % 3
                            next_row = self.row if next_col < 2 else self.row - 1
                        else:
                            # Move to next column, or next row if at last column
                            next_col = (self.col + 1) % 3
                            next_row = self.row if next_col > 0 else self.row + 1
                        
                        # Find next widget in table
                        if next_col >= 0 and next_row >= 0 and next_col < 3 and next_row < self.table.rowCount():
                            next_widget = self.table.cellWidget(next_row, next_col)
                            if next_widget:
                                # Set focus on the next widget
                                # The OOBDoubleSpinBox.focusInEvent() will handle text selection
                                next_widget.setFocus()
                                # Explicitly set focus on the line edit to ensure keyboard input works
                                if hasattr(next_widget, 'lineEdit'):
                                    line_edit = next_widget.lineEdit()
                                    if line_edit:
                                        line_edit.setFocus()
                                        # Select all text after a brief delay
                                        QTimer.singleShot(50, lambda: line_edit.selectAll() if line_edit else None)
                                return True  # Event handled
                        
                        # If no next widget, move focus to table
                        self.table.setFocus()
                        return True  # Event handled
                
                # Let other events pass through
                return False
        
        return OOBSpinboxFilter(table, row, col)
    
    def _remove_oob_row(self, test_stage: str) -> None:
        """Remove selected row from OOB table."""
        table = self._oob_tables[test_stage]
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
    
    def _load_criteria(self) -> None:
        """Load existing criteria for all test stages."""
        # Validate device has an ID
        if self.device.id is None:
            return  # Can't load criteria without device ID
        
        try:
            for stage in TEST_STAGES:
                try:
                    criteria = self.device_service.get_criteria_for_device(
                        self.device.id, self.test_type, stage
                    )
                except Exception as e:
                    # Log but continue with other stages
                    handle_exception(self, e, f"Loading criteria for {stage}")
                    continue
                
                # Validate dictionaries exist
                if not hasattr(self, '_gain_mins') or stage not in self._gain_mins:
                    continue
                if not hasattr(self, '_gain_maxs') or stage not in self._gain_maxs:
                    continue
                if not hasattr(self, '_vswr_maxs') or stage not in self._vswr_maxs:
                    continue
                if not hasattr(self, '_oob_tables') or stage not in self._oob_tables:
                    continue
                
                # Find Gain Range criteria
                gain_range = [c for c in criteria if c.requirement_name == "Gain Range"]
                if gain_range:
                    c = gain_range[0]
                    if self._gain_mins.get(stage):
                        self._gain_mins[stage].setValue(c.min_value or 0.0)
                    if self._gain_maxs.get(stage):
                        self._gain_maxs[stage].setValue(c.max_value or 0.0)
                
                # Find VSWR Max criteria
                vswr = [c for c in criteria if c.requirement_name == "VSWR Max"]
                if vswr:
                    c = vswr[0]
                    if self._vswr_maxs.get(stage):
                        self._vswr_maxs[stage].setValue(c.max_value or 1.0)
                
                # Find OOB criteria
                oob_criteria = [c for c in criteria if "OOB" in c.requirement_name]
                table = self._oob_tables.get(stage)
                if table:
                    table.setRowCount(0)
                    for oob in oob_criteria:
                        try:
                            self._add_oob_row(stage)
                            row = table.rowCount() - 1
                            freq_min_widget = table.cellWidget(row, 0)
                            freq_max_widget = table.cellWidget(row, 1)
                            rejection_widget = table.cellWidget(row, 2)
                            if freq_min_widget and oob.frequency_min is not None:
                                freq_min_widget.setValue(oob.frequency_min)
                            if freq_max_widget and oob.frequency_max is not None:
                                freq_max_widget.setValue(oob.frequency_max)
                            if rejection_widget and oob.min_value is not None:
                                rejection_widget.setValue(oob.min_value)
                        except Exception as e:
                            # Log but continue with other OOB criteria
                            handle_exception(self, e, f"Loading OOB criteria for {stage}")
                            continue
        except Exception as e:
            handle_exception(self, e, "Loading test criteria")
    
    def _save_all_criteria(self) -> None:
        """Save all criteria for all test stages."""
        try:
            for stage in TEST_STAGES:
                # Save Gain Range
                gain_min = self._gain_mins[stage].value()
                gain_max = self._gain_maxs[stage].value()
                if gain_min < gain_max:
                    # Find or create Gain Range criteria
                    criteria = self.device_service.get_criteria_for_device(
                        self.device.id, self.test_type, stage
                    )
                    gain_range = [c for c in criteria if c.requirement_name == "Gain Range"]
                    
                    if gain_range:
                        # Update existing
                        c = gain_range[0]
                        c.min_value = gain_min
                        c.max_value = gain_max
                        self.device_service.update_criteria(c)
                    else:
                        # Create new
                        c = TestCriteria(
                            device_id=self.device.id,
                            test_type=self.test_type,
                            test_stage=stage,
                            requirement_name="Gain Range",
                            criteria_type="range",
                            min_value=gain_min,
                            max_value=gain_max,
                            unit="dB"
                        )
                        self.device_service.add_criteria(c)
                
                # Save VSWR Max
                vswr_max = self._vswr_maxs[stage].value()
                criteria = self.device_service.get_criteria_for_device(
                    self.device.id, self.test_type, stage
                )
                vswr = [c for c in criteria if c.requirement_name == "VSWR Max"]
                
                if vswr:
                    c = vswr[0]
                    c.max_value = vswr_max
                    self.device_service.update_criteria(c)
                else:
                    c = TestCriteria(
                        device_id=self.device.id,
                        test_type=self.test_type,
                        test_stage=stage,
                        requirement_name="VSWR Max",
                        criteria_type="max",
                        max_value=vswr_max,
                        unit=""
                    )
                    self.device_service.add_criteria(c)
                
                # Save OOB requirements
                table = self._oob_tables[stage]
                existing_oob = [
                    c for c in self.device_service.get_criteria_for_device(
                        self.device.id, self.test_type, stage
                    ) if "OOB" in c.requirement_name
                ]
                
                # Delete all existing OOB
                for c in existing_oob:
                    self.device_service.delete_criteria(c.id)
                
                # Add new OOB requirements
                # Skip rows where all values are 0.0 (empty/unfilled rows)
                for row in range(table.rowCount()):
                    freq_min_widget = table.cellWidget(row, 0)
                    freq_max_widget = table.cellWidget(row, 1)
                    rejection_widget = table.cellWidget(row, 2)
                    
                    if freq_min_widget and freq_max_widget and rejection_widget:
                        freq_min = freq_min_widget.value()
                        freq_max = freq_max_widget.value()
                        rejection = rejection_widget.value()
                        
                        # Skip rows where values are 0.0 (empty/unfilled)
                        # Only save rows with valid values (> 0)
                        # Note: 0.0 is treated as empty since user can't have 0 GHz frequency
                        if (freq_min > 0 and freq_max > 0 and rejection > 0 and 
                            freq_min < freq_max):
                            c = TestCriteria(
                                device_id=self.device.id,
                                test_type=self.test_type,
                                test_stage=stage,
                                requirement_name=f"OOB {row + 1}",
                                criteria_type="greater_than_equal",
                                min_value=rejection,
                                frequency_min=freq_min,
                                frequency_max=freq_max,
                                unit="dBc"
                            )
                            self.device_service.add_criteria(c)
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Success", "Criteria saved successfully.")
            
            # Emit signal to notify parent that criteria were saved
            self.criteria_saved.emit()
        except Exception as e:
            handle_exception(self, e, "Saving criteria")
    
    def _set_oob_column_widths(self, table: QTableWidget) -> None:
        """Set column widths proportionally for even distribution."""
        # Try multiple times if table not ready yet
        if not table.isVisible():
            # Retry after a delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._set_oob_column_widths(table))
            return
        
        # Get available width
        available_width = table.viewport().width()
        if available_width <= 0:
            # Retry if width not available yet
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._set_oob_column_widths(table))
            return
        
        # Calculate proportional widths (each column gets equal share)
        # Reserve some space for scrollbar
        column_width = max(150, int((available_width - 20) / 3))  # Minimum 150px per column
        
        # Set widths for all columns
        header = table.horizontalHeader()
        for col in range(3):
            header.resizeSection(col, column_width)

