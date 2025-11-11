"""
Main application window.

This module provides the MainWindow class, which is the primary application
window containing tabs for Test Setup and Plotting Controls, plus a menu bar.
"""

from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QStatusBar, QWidget
)
from PyQt6.QtCore import Qt

from .widgets.test_setup.test_setup_tab import TestSetupTab
from .widgets.plotting.plotting_controls_tab import PlottingControlsTab
from .widgets.device_maintenance.device_maintenance_dialog import DeviceMaintenanceDialog
from .utils.error_handler import StatusBarMessage
from ..core.services.device_service import DeviceService
from ..core.services.measurement_service import MeasurementService
from ..core.services.compliance_service import ComplianceService


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Provides tabs for Test Setup and Plotting Controls, plus a menu bar
    for accessing Device Maintenance and other functions.
    """
    
    def __init__(
        self,
        device_service: DeviceService,
        measurement_service: MeasurementService,
        compliance_service: ComplianceService,
        database_path: Path,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize main window.
        
        Args:
            device_service: DeviceService instance
            measurement_service: MeasurementService instance
            compliance_service: ComplianceService instance
            database_path: Path to database file (for worker threads)
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device_service = device_service
        self.measurement_service = measurement_service
        self.compliance_service = compliance_service
        self.database_path = database_path
        
        # Track device maintenance dialog
        self.device_maintenance_dialog: Optional[DeviceMaintenanceDialog] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Macallan RF Performance Tool")
        self.setMinimumSize(1200, 800)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create tabs
        self.test_setup_tab = TestSetupTab(
            device_service=self.device_service,
            measurement_service=self.measurement_service,
            compliance_service=self.compliance_service,
            database_path=self.database_path,
            status_bar=self.status_bar
        )
        self.tab_widget.addTab(self.test_setup_tab, "Test Setup")
        
        self.plotting_tab = PlottingControlsTab(
            device_service=self.device_service,
            measurement_service=self.measurement_service,
            compliance_service=self.compliance_service,
            database_path=self.database_path,
            status_bar=self.status_bar,
            test_setup_tab=self.test_setup_tab
        )
        self.tab_widget.addTab(self.plotting_tab, "Plotting")
        
        # Connect signals
        self.test_setup_tab.device_changed.connect(self._on_device_changed)
        self.test_setup_tab.measurements_loaded.connect(self.plotting_tab._update_create_button_state)
    
    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = file_menu.addAction("E&xit", self.close)
        exit_action.setShortcut("Ctrl+Q")
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        # Future: Add undo/redo, preferences, etc.
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        device_action = tools_menu.addAction(
            "&Device Maintenance...",
            self._open_device_maintenance
        )
        device_action.setShortcut("Ctrl+D")
        
        # View menu
        view_menu = menubar.addMenu("&View")
        # Future: Add view options
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About...", self._show_about)
    
    def _open_device_maintenance(self) -> None:
        """Open the Device Maintenance dialog."""
        if self.device_maintenance_dialog is None or not self.device_maintenance_dialog.isVisible():
            self.device_maintenance_dialog = DeviceMaintenanceDialog(
                device_service=self.device_service,
                parent=self
            )
            # Connect signal to refresh test setup when device is updated
            self.device_maintenance_dialog.device_updated.connect(
                self._on_device_updated
            )
            # Connect signal to refresh compliance table when criteria are updated
            self.device_maintenance_dialog.criteria_updated.connect(
                self._on_criteria_updated
            )
            self.device_maintenance_dialog.show()
        else:
            # Bring to front if already open
            self.device_maintenance_dialog.raise_()
            self.device_maintenance_dialog.activateWindow()
    
    def _on_device_updated(self) -> None:
        """Handle device update signal from Device Maintenance."""
        # Refresh device list in test setup tab
        self.test_setup_tab.refresh_device_list()
    
    def _on_criteria_updated(self) -> None:
        """Handle criteria update signal from Device Maintenance."""
        # Refresh compliance table immediately when criteria are saved
        self.test_setup_tab.refresh_compliance_table()
    
    def _on_device_changed(self) -> None:
        """Handle device change signal from Test Setup tab."""
        # Update plotting tab when device changes
        self.plotting_tab.on_device_changed()
    
    def _show_about(self) -> None:
        """Show About dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About Macallan RF Performance Tool",
            "Macallan RF Performance Tool v2.0\n\n"
            "A full-featured RF performance analysis tool for plotting "
            "S-parameters and comparing measurements against specifications.\n\n"
            "© 2025 Macallan Engineering"
        )

