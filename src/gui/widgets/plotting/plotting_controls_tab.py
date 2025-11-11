"""
Plotting Controls tab for main window.

This module provides the Plotting Controls tab where users can create
and manage plot windows.
"""

from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QGroupBox, QLabel, QListWidget
)
from PyQt6.QtCore import Qt

from .plot_window import PlotWindow
from ....core.services.device_service import DeviceService
from ....core.services.measurement_service import MeasurementService
from ....core.services.compliance_service import ComplianceService
from ...utils.error_handler import StatusBarMessage


class PlottingControlsTab(QWidget):
    """
    Plotting Controls tab widget.
    
    Provides interface for creating plot windows and managing them.
    """
    
    def __init__(
        self,
        device_service: DeviceService,
        measurement_service: MeasurementService,
        compliance_service: ComplianceService,
        database_path: Path,
        status_bar,
        test_setup_tab=None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize plotting controls tab.
        
        Args:
            device_service: DeviceService instance
            measurement_service: MeasurementService instance
            compliance_service: ComplianceService instance
            database_path: Path to database file (for worker threads)
            status_bar: QStatusBar for status messages
            test_setup_tab: Optional reference to TestSetupTab for accessing session measurements
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device_service = device_service
        self.measurement_service = measurement_service
        self.compliance_service = compliance_service
        self.database_path = database_path
        self.status_bar = status_bar
        self.test_setup_tab = test_setup_tab
        
        self.plot_windows = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Plot creation
        create_group = QGroupBox("Create Plot")
        create_layout = QVBoxLayout()
        
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(QLabel("Plot Type:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems([
            "Operational Gain",
            "Operational VSWR",
            "Operational Return Loss",
            "Wideband Gain",
            "Wideband VSWR",
            "Wideband Return Loss"
        ])
        plot_type_layout.addWidget(self.plot_type_combo)
        plot_type_layout.addStretch()
        create_layout.addLayout(plot_type_layout)
        
        self.create_button = QPushButton("Create Plot Window")
        self.create_button.clicked.connect(self._create_plot_window)
        create_layout.addWidget(self.create_button)
        
        # Update button state based on data availability
        self._update_create_button_state()
        
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Data")
        refresh_button.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_button)
        
        layout.addStretch()
    
    def _can_create_plot(self) -> bool:
        """Check if plot can be created (device selected and measurements loaded)."""
        if self.test_setup_tab is None:
            return False
        if self.test_setup_tab.current_device is None:
            return False
        if len(self.test_setup_tab.session_measurements) == 0:
            return False
        return True
    
    def _update_create_button_state(self) -> None:
        """Update the state of the Create Plot Window button."""
        can_create = self._can_create_plot()
        self.create_button.setEnabled(can_create)
        if not can_create:
            self.create_button.setToolTip("Please select a device and load measurement files in the Test Setup tab first.")
        else:
            self.create_button.setToolTip("")
    
    def _create_plot_window(self) -> None:
        """Create a new plot window."""
        if not self._can_create_plot():
            StatusBarMessage.show_warning(
                self.status_bar,
                "Please load measurement files in Test Setup tab first."
            )
            return
        
        plot_type = self.plot_type_combo.currentText()
        
        plot_window = PlotWindow(
            plot_type=plot_type,
            device_service=self.device_service,
            measurement_service=self.measurement_service,
            compliance_service=self.compliance_service,
            database_path=self.database_path,
            status_bar=self.status_bar,
            test_setup_tab=self.test_setup_tab,
            parent=self
        )
        
        self.plot_windows.append(plot_window)
        plot_window.show()
    
    def _refresh_data(self) -> None:
        """Refresh data from loaded measurements."""
        StatusBarMessage.show_info(self.status_bar, "Data refreshed.")
        # TODO: Implement actual refresh logic
    
    def on_device_changed(self) -> None:
        """Handle device change from Test Setup tab."""
        # Update all plot windows
        for plot_window in self.plot_windows:
            if plot_window.isVisible():
                plot_window.refresh_data()



