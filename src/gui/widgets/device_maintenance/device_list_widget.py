"""
Device list widget for Device Maintenance.

This module provides a table widget that displays all devices and allows
selecting, editing, and deleting them.
"""

from typing import Optional
from uuid import UUID
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ....core.models.device import Device
from ....core.services.device_service import DeviceService
from ....core.exceptions import DatabaseError
from ...utils.error_handler import handle_exception, show_error


class DeviceListWidget(QWidget):
    """
    Widget displaying a table of devices with edit/delete buttons.
    
    Emits signals when devices are selected, edited, or deleted.
    """
    
    # Signals
    device_selected = pyqtSignal(Device)  # Emitted when device is selected
    device_deleted = pyqtSignal(UUID)  # Emitted when device is deleted
    device_new_requested = pyqtSignal()  # Emitted when New Device button is clicked
    
    def __init__(
        self,
        device_service: DeviceService,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize device list widget.
        
        Args:
            device_service: DeviceService instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device_service = device_service
        self.devices: list[Device] = []
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # Removed Actions column
        self.table.setHorizontalHeaderLabels(["Name", "Part Number", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Connect selection signal
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.table)
        
        # Add New Device and Delete buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        new_device_button = QPushButton("New Device")
        new_device_button.clicked.connect(self._on_new_device_clicked)
        delete_button = QPushButton("Delete Selected Device")
        delete_button.clicked.connect(self._on_delete_clicked)
        delete_button.setEnabled(False)  # Disabled until device is selected
        button_layout.addWidget(new_device_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)
        
        # Store button references for enabling/disabling
        self.new_device_button = new_device_button
        self.delete_button = delete_button
    
    def refresh(self) -> None:
        """Refresh the device list from the database."""
        try:
            self.devices = self.device_service.get_all_devices()
            self._populate_table()
        except Exception as e:
            handle_exception(self, e, "Loading devices")
    
    def _populate_table(self) -> None:
        """Populate the table with device data."""
        self.table.setRowCount(len(self.devices))
        
        for row, device in enumerate(self.devices):
            # Name
            name_item = QTableWidgetItem(device.name)
            name_item.setData(Qt.ItemDataRole.UserRole, device.id)  # Store ID
            self.table.setItem(row, 0, name_item)
            
            # Part Number
            self.table.setItem(row, 1, QTableWidgetItem(device.part_number))
            
            # Description (truncated if long)
            desc = device.description[:50] + "..." if len(device.description) > 50 else device.description
            self.table.setItem(row, 2, QTableWidgetItem(desc))
    
    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        try:
            selected_rows = self.table.selectedIndexes()
            if selected_rows:
                row = selected_rows[0].row()
                if row < len(self.devices):
                    device = self.devices[row]
                    # Validate device before emitting
                    if device is None:
                        return
                    try:
                        self.device_selected.emit(device)
                    except Exception as e:
                        handle_exception(self, e, "Emitting device selection signal")
                        return
                    # Enable delete button when device is selected
                    if hasattr(self, 'delete_button'):
                        self.delete_button.setEnabled(True)
            else:
                # Disable delete button when no selection
                if hasattr(self, 'delete_button'):
                    self.delete_button.setEnabled(False)
        except Exception as e:
            handle_exception(self, e, "Handling device selection change")
    
    def get_selected_device(self) -> Optional[Device]:
        """Get the currently selected device."""
        selected_rows = self.table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.devices):
                return self.devices[row]
        return None
    
    def delete_selected_device(self) -> bool:
        """
        Delete the selected device after confirmation.
        
        Returns:
            True if device was deleted, False otherwise
        """
        device = self.get_selected_device()
        if device is None:
            return False
        
        # Get deletion info
        try:
            info = self.device_service.get_deletion_info(device.id)
            
            # Confirm deletion
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Delete Device")
            msg.setText(f"Are you sure you want to delete device '{device.name}'?")
            
            if info["has_related_data"]:
                details = (
                    f"This will also delete:\n"
                    f"- {info['criteria_count']} test criteria\n"
                    f"- {info['measurement_count']} measurements\n"
                    f"\nThis action cannot be undone."
                )
                msg.setDetailedText(details)
            
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                # Delete device
                self.device_service.delete_device(device.id)
                self.device_deleted.emit(device.id)
                self.refresh()
                return True
        except Exception as e:
            handle_exception(self, e, "Deleting device")
        
        return False
    
    def _on_new_device_clicked(self) -> None:
        """Handle New Device button click."""
        self.device_new_requested.emit()
    
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        self.delete_selected_device()

