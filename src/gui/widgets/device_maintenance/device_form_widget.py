"""
Device form widget for creating and editing devices.

This module provides a form widget for entering/editing device information,
including name, part number, frequency ranges, port configuration, and test settings.
"""

from typing import Optional
from uuid import UUID
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDoubleSpinBox, QCheckBox, QListWidget, QPushButton, QLabel, QSpinBox,
    QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ....core.models.device import Device
from ....core.exceptions import ValidationError
from ...utils.error_handler import handle_exception


class DeviceFormWidget(QWidget):
    """
    Form widget for creating and editing devices.
    
    Provides input fields for all device properties and emits signals
    when devices are saved or cancelled.
    """
    
    # Signals
    device_saved = pyqtSignal(Device)  # Emitted when device is saved
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize device form widget.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.current_device_id: Optional[UUID] = None
        self._setup_ui()
        self.clear_form()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        # Part Number
        self.part_number_edit = QLineEdit()
        form_layout.addRow("Part Number (Lnnnnnn):", self.part_number_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)
        
        # Operational Frequency Range
        freq_group = QGroupBox("Operational Frequency Range (GHz)")
        freq_layout = QHBoxLayout()
        self.operational_freq_min = QDoubleSpinBox()
        self.operational_freq_min.setRange(0.0, 1000.0)
        self.operational_freq_min.setDecimals(3)  # Allow 3 decimal places
        self.operational_freq_min.setSuffix(" GHz")
        self.operational_freq_max = QDoubleSpinBox()
        self.operational_freq_max.setRange(0.0, 1000.0)
        self.operational_freq_max.setDecimals(3)  # Allow 3 decimal places
        self.operational_freq_max.setSuffix(" GHz")
        freq_layout.addWidget(QLabel("Min:"))
        freq_layout.addWidget(self.operational_freq_min)
        freq_layout.addWidget(QLabel("Max:"))
        freq_layout.addWidget(self.operational_freq_max)
        freq_group.setLayout(freq_layout)
        form_layout.addRow(freq_group)
        
        # Wideband Frequency Range
        wb_group = QGroupBox("Wideband Frequency Range (GHz)")
        wb_layout = QHBoxLayout()
        self.wideband_freq_min = QDoubleSpinBox()
        self.wideband_freq_min.setRange(0.0, 1000.0)
        self.wideband_freq_min.setDecimals(3)  # Allow 3 decimal places
        self.wideband_freq_min.setSuffix(" GHz")
        self.wideband_freq_max = QDoubleSpinBox()
        self.wideband_freq_max.setRange(0.0, 1000.0)
        self.wideband_freq_max.setDecimals(3)  # Allow 3 decimal places
        self.wideband_freq_max.setSuffix(" GHz")
        wb_layout.addWidget(QLabel("Min:"))
        wb_layout.addWidget(self.wideband_freq_min)
        wb_layout.addWidget(QLabel("Max:"))
        wb_layout.addWidget(self.wideband_freq_max)
        wb_group.setLayout(wb_layout)
        form_layout.addRow(wb_group)
        
        # Multi-Gain Mode
        self.multi_gain_checkbox = QCheckBox("Multi-Gain Mode")
        form_layout.addRow(self.multi_gain_checkbox)
        
        # Input Ports
        input_group = QGroupBox("Input Ports")
        input_layout = QVBoxLayout()
        self.input_ports_edit = QLineEdit()
        self.input_ports_edit.setPlaceholderText("e.g., 1, 2 or 1 2")
        self.input_ports_edit.setToolTip("Enter comma or space-separated port numbers")
        input_layout.addWidget(self.input_ports_edit)
        input_group.setLayout(input_layout)
        form_layout.addRow(input_group)
        
        # Output Ports
        output_group = QGroupBox("Output Ports")
        output_layout = QVBoxLayout()
        self.output_ports_edit = QLineEdit()
        self.output_ports_edit.setPlaceholderText("e.g., 3, 4 or 3 4")
        self.output_ports_edit.setToolTip("Enter comma or space-separated port numbers")
        output_layout.addWidget(self.output_ports_edit)
        output_group.setLayout(output_layout)
        form_layout.addRow(output_group)
        
        # Tests Performed
        tests_group = QGroupBox("Tests Performed")
        tests_layout = QVBoxLayout()
        # Use checkboxes instead of list widget for better UX
        self.test_checkboxes = {}
        # Available test types (currently only S-Parameters, but extensible)
        available_tests = ["S-Parameters"]
        for test_type in available_tests:
            checkbox = QCheckBox(test_type)
            self.test_checkboxes[test_type] = checkbox
            tests_layout.addWidget(checkbox)
        tests_layout.addStretch()
        tests_group.setLayout(tests_layout)
        form_layout.addRow(tests_group)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.current_device_id = None
        self.name_edit.clear()
        self.part_number_edit.clear()
        self.description_edit.clear()
        self.operational_freq_min.setValue(0.0)
        self.operational_freq_max.setValue(1.0)
        self.wideband_freq_min.setValue(0.0)
        self.wideband_freq_max.setValue(1.0)
        self.multi_gain_checkbox.setChecked(False)
        self.input_ports_edit.clear()
        self.output_ports_edit.clear()
        
        # Clear test selections
        for checkbox in self.test_checkboxes.values():
            checkbox.setChecked(False)
    
    def load_device(self, device: Device) -> None:
        """
        Load device data into the form.
        
        Args:
            device: Device to load
        """
        self.current_device_id = device.id
        
        # Basic fields with None checks
        self.name_edit.setText(device.name or "")
        self.part_number_edit.setText(device.part_number or "")
        self.description_edit.setPlainText(device.description or "")
        
        # Frequency fields with None/default checks
        if device.operational_freq_min is not None:
            self.operational_freq_min.setValue(device.operational_freq_min)
        else:
            self.operational_freq_min.setValue(1.0)
        
        if device.operational_freq_max is not None:
            self.operational_freq_max.setValue(device.operational_freq_max)
        else:
            self.operational_freq_max.setValue(2.0)
        
        if device.wideband_freq_min is not None:
            self.wideband_freq_min.setValue(device.wideband_freq_min)
        else:
            self.wideband_freq_min.setValue(0.5)
        
        if device.wideband_freq_max is not None:
            self.wideband_freq_max.setValue(device.wideband_freq_max)
        else:
            self.wideband_freq_max.setValue(1.0)
        
        # Multi-gain mode
        self.multi_gain_checkbox.setChecked(device.multi_gain_mode if device.multi_gain_mode is not None else False)
        
        # Ports - handle None or empty lists
        if device.input_ports:
            self.input_ports_edit.setText(", ".join(map(str, device.input_ports)))
        else:
            self.input_ports_edit.setText("")
        
        if device.output_ports:
            self.output_ports_edit.setText(", ".join(map(str, device.output_ports)))
        else:
            self.output_ports_edit.setText("")
        
        # Tests performed - handle None or empty
        if device.tests_performed:
            for test_type, checkbox in self.test_checkboxes.items():
                checkbox.setChecked(test_type in device.tests_performed)
        else:
            # Clear all checkboxes if no tests performed
            for checkbox in self.test_checkboxes.values():
                checkbox.setChecked(False)
    
    def _parse_ports(self, text: str) -> list[int]:
        """
        Parse port numbers from text input.
        
        Supports comma-separated or space-separated values.
        
        Args:
            text: Input text
            
        Returns:
            List of port numbers
        """
        if not text.strip():
            return []
        
        # Try comma-separated first
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 1:
            # Try space-separated
            parts = [p.strip() for p in text.split()]
        
        ports = []
        for part in parts:
            try:
                port = int(part)
                if port > 0:
                    ports.append(port)
            except ValueError:
                continue
        
        return ports
    
    def _on_save(self) -> None:
        """Handle save button click."""
        try:
            # Gather form data
            name = self.name_edit.text().strip()
            if not name:
                raise ValidationError("Device name is required")
            
            part_number = self.part_number_edit.text().strip()
            if not part_number:
                raise ValidationError("Part number is required")
            
            description = self.description_edit.toPlainText().strip()
            
            op_freq_min = self.operational_freq_min.value()
            op_freq_max = self.operational_freq_max.value()
            if op_freq_min >= op_freq_max:
                raise ValidationError("Operational frequency min must be less than max")
            
            wb_freq_min = self.wideband_freq_min.value()
            wb_freq_max = self.wideband_freq_max.value()
            if wb_freq_min >= wb_freq_max:
                raise ValidationError("Wideband frequency min must be less than max")
            
            input_ports = self._parse_ports(self.input_ports_edit.text())
            if not input_ports:
                raise ValidationError("At least one input port is required")
            
            output_ports = self._parse_ports(self.output_ports_edit.text())
            if not output_ports:
                raise ValidationError("At least one output port is required")
            
            # Get selected tests from checkboxes
            selected_tests = [
                test_type
                for test_type, checkbox in self.test_checkboxes.items()
                if checkbox.isChecked()
            ]
            
            if not selected_tests:
                raise ValidationError("At least one test type must be selected")
            
            # Create or update device
            device_data = {
                "name": name,
                "part_number": part_number,
                "description": description,
                "operational_freq_min": op_freq_min,
                "operational_freq_max": op_freq_max,
                "wideband_freq_min": wb_freq_min,
                "wideband_freq_max": wb_freq_max,
                "multi_gain_mode": self.multi_gain_checkbox.isChecked(),
                "tests_performed": selected_tests,
                "input_ports": input_ports,
                "output_ports": output_ports
            }
            
            if self.current_device_id:
                # Update existing device
                device = Device(id=self.current_device_id, **device_data)
            else:
                # Create new device
                device = Device(**device_data)
            
            # Emit signal (parent will handle saving)
            self.device_saved.emit(device)
            
        except ValidationError as e:
            handle_exception(self, e, "Validating device")
        except Exception as e:
            handle_exception(self, e, "Saving device")

