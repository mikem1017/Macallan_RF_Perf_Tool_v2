"""
Device Maintenance dialog.

This module provides the main dialog for device CRUD operations and
test criteria management.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .device_list_widget import DeviceListWidget
from .device_form_widget import DeviceFormWidget
from .test_criteria_editor import TestCriteriaEditor
from ....core.models.device import Device
from ....core.services.device_service import DeviceService
from ...utils.error_handler import handle_exception


class DeviceMaintenanceDialog(QDialog):
    """
    Dialog for device maintenance.
    
    Provides device list, device form, and test criteria editor
    in a tabbed interface.
    """
    
    # Signal emitted when a device is updated (for refreshing other parts of GUI)
    device_updated = pyqtSignal()
    
    # Signal emitted when test criteria are saved (for refreshing compliance table)
    criteria_updated = pyqtSignal()
    
    def __init__(
        self,
        device_service: DeviceService,
        parent: Optional[QDialog] = None
    ):
        """
        Initialize device maintenance dialog.
        
        Args:
            device_service: DeviceService instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device_service = device_service
        self.current_device: Optional[Device] = None
        
        self.setWindowTitle("Device Maintenance")
        self.setMinimumSize(1400, 700)  # Wider window for better layout
        self.resize(1400, 700)  # Set default size
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create splitter for device list and form
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Device list
        self.device_list = DeviceListWidget(self.device_service)
        self.device_list.device_selected.connect(self._on_device_selected)
        self.device_list.device_deleted.connect(self._on_device_deleted)
        self.device_list.device_new_requested.connect(self._on_new_device_requested)
        splitter.addWidget(self.device_list)
        
        # Right side: Form and criteria editor in tabs
        self.right_tabs = QTabWidget()
        
        # Device form tab
        self.device_form = DeviceFormWidget()
        self.device_form.device_saved.connect(self._on_device_saved)
        self.right_tabs.addTab(self.device_form, "Device Info")
        
        # Store criteria editor reference (will be created when device selected)
        self.criteria_editor: Optional[TestCriteriaEditor] = None
        self.criteria_tab_index = -1
        
        splitter.addWidget(self.right_tabs)
        
        # Set splitter proportions (wider left panel for better visibility)
        splitter.setSizes([400, 1000])
        
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def _on_device_selected(self, device: Device) -> None:
        """Handle device selection."""
        try:
            # Validate device first
            if device is None:
                handle_exception(
                    self,
                    ValueError("Device is None"),
                    "Selecting device"
                )
                return
            
            # Clear form first to reset any previous state
            self.device_form.clear_form()
            
            # Reload device from database to ensure we have fresh data
            fresh_device = self.device_service.get_device(device.id)
            if not fresh_device:
                handle_exception(
                    self,
                    ValueError(f"Device {device.id} not found in database"),
                    "Loading device"
                )
                return
            
            self.current_device = fresh_device
            
            # Load device into form with error handling
            try:
                self.device_form.load_device(fresh_device)
            except Exception as e:
                import traceback
                error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                handle_exception(
                    self,
                    Exception(error_details),
                    "Loading device data into form"
                )
                return
            
            # Update criteria editor if device has test types
            # Remove old criteria tabs
            tabs_to_remove = []
            for i in range(self.right_tabs.count()):
                if i > 0:  # Keep device info tab (index 0)
                    tabs_to_remove.append(i)
            for i in reversed(tabs_to_remove):
                self.right_tabs.removeTab(i)
            
            # Add criteria tabs for each test type
            # Validate tests_performed is not None and is iterable
            if device.tests_performed is None:
                return  # No tests configured, skip criteria tabs
            
            if not isinstance(device.tests_performed, (list, tuple, set)):
                # Handle case where tests_performed might be a string or other type
                handle_exception(
                    self,
                    ValueError(f"Invalid tests_performed type: {type(device.tests_performed)}"),
                    "Loading test criteria"
                )
                return
            
            for test_type in device.tests_performed:
                # Skip None or empty test types
                if not test_type or not isinstance(test_type, str):
                    continue
                
                try:
                    # Create a new Device object with validated data instead of deepcopy
                    # This avoids any issues with deepcopy and Pydantic models
                    from ....core.models.device import Device
                    
                    # Build device data safely
                    device_data = {
                        "id": device.id,
                        "name": device.name or "",
                        "description": device.description or "",
                        "part_number": device.part_number or "",
                        "operational_freq_min": device.operational_freq_min if device.operational_freq_min is not None else 1.0,
                        "operational_freq_max": device.operational_freq_max if device.operational_freq_max is not None else 2.0,
                        "wideband_freq_min": device.wideband_freq_min if device.wideband_freq_min is not None else 0.5,
                        "wideband_freq_max": device.wideband_freq_max if device.wideband_freq_max is not None else 1.0,
                        "multi_gain_mode": device.multi_gain_mode if device.multi_gain_mode is not None else False,
                        "tests_performed": device.tests_performed if device.tests_performed is not None else [],
                        "input_ports": device.input_ports if device.input_ports is not None else [],
                        "output_ports": device.output_ports if device.output_ports is not None else []
                    }
                    
                    # Create new Device object with validated data
                    safe_device = Device(**device_data)
                    
                    criteria_editor = TestCriteriaEditor(
                        device=safe_device,
                        test_type=test_type,
                        device_service=self.device_service
                    )
                    # Connect criteria saved signal to emit dialog's criteria_updated signal
                    criteria_editor.criteria_saved.connect(self.criteria_updated.emit)
                    self.right_tabs.addTab(
                        criteria_editor, f"{test_type} Criteria"
                    )
                except Exception as e:
                    # More detailed error logging with traceback
                    import traceback
                    error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                    # Show error dialog immediately
                    from PyQt6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("Error Creating Criteria Editor")
                    msg.setText(f"Failed to create criteria editor for {test_type}")
                    msg.setDetailedText(error_details)
                    msg.exec()
                    # Continue with other test types even if one fails
        except Exception as e:
            handle_exception(self, e, "Selecting device")
    
    def _on_device_saved(self, device: Device) -> None:
        """Handle device save."""
        try:
            saved_device = None
            if self.current_device and device.id == self.current_device.id:
                # Update existing device
                saved_device = self.device_service.update_device(device)
                self.current_device = saved_device
            else:
                # Create new device - get the created device from database
                saved_device = self.device_service.create_device(device)
                self.current_device = saved_device
            
            # Refresh device list
            self.device_list.refresh()
            
            # Select the saved device using the device from database (has correct ID)
            if saved_device:
                # Reload device from database to ensure we have fresh data
                fresh_device = self.device_service.get_device(saved_device.id)
                if fresh_device:
                    self._on_device_selected(fresh_device)
            
            # Emit signal for other parts of GUI
            self.device_updated.emit()
            
            QMessageBox.information(self, "Success", "Device saved successfully.")
        except Exception as e:
            handle_exception(self, e, "Saving device")
            # Clear form state on error to prevent corruption
            self.device_form.clear_form()
            self.current_device = None
    
    def _on_new_device_requested(self) -> None:
        """Handle New Device button click."""
        # Clear form and reset state
        self.current_device = None
        self.device_form.clear_form()
        # Clear any criteria tabs
        tabs_to_remove = []
        for i in range(self.right_tabs.count()):
            if i > 0:  # Keep device info tab (index 0)
                tabs_to_remove.append(i)
        for i in reversed(tabs_to_remove):
            self.right_tabs.removeTab(i)
        # Switch to Device Info tab
        self.right_tabs.setCurrentIndex(0)
    
    def _on_device_deleted(self, device_id) -> None:
        """Handle device deletion."""
        self.current_device = None
        self.device_form.clear_form()
        self.device_updated.emit()

