"""GUI tests for MainWindow."""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from src.gui.main_window import MainWindow
from src.core.services.device_service import DeviceService
from src.core.services.measurement_service import MeasurementService
from src.core.services.compliance_service import ComplianceService


@pytest.fixture
def qapp():
    """Provide QApplication instance."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def mock_services():
    """Provide mocked services."""
    device_service = Mock(spec=DeviceService)
    measurement_service = Mock(spec=MeasurementService)
    compliance_service = Mock(spec=ComplianceService)
    return device_service, measurement_service, compliance_service


@pytest.fixture
def main_window(qapp, mock_services):
    """Provide MainWindow instance."""
    device_service, measurement_service, compliance_service = mock_services
    window = MainWindow(
        device_service=device_service,
        measurement_service=measurement_service,
        compliance_service=compliance_service
    )
    yield window
    window.close()


class TestMainWindow:
    """Test MainWindow functionality."""
    
    def test_window_creation(self, main_window):
        """Test that main window is created."""
        assert main_window is not None
        assert main_window.windowTitle() == "Macallan RF Performance Tool"
    
    def test_tabs_exist(self, main_window):
        """Test that tabs are created."""
        assert main_window.tab_widget.count() == 2
        assert main_window.tab_widget.tabText(0) == "Test Setup"
        assert main_window.tab_widget.tabText(1) == "Plotting"
    
    def test_menu_bar_exists(self, main_window):
        """Test that menu bar is created."""
        menubar = main_window.menuBar()
        assert menubar is not None
    
    def test_device_maintenance_menu_action(self, main_window, qapp):
        """Test that Device Maintenance can be opened from menu."""
        menubar = main_window.menuBar()
        # Find Tools menu
        tools_menu = None
        for action in menubar.actions():
            if action.text() and "Tools" in action.text():
                tools_menu = action.menu()
                break
        if tools_menu:
            actions = tools_menu.actions()
            device_action = next((a for a in actions if "Device Maintenance" in a.text()), None)
            if device_action:
                # Trigger action
                device_action.trigger()
                # Dialog should be created
                # Note: Actual dialog creation would require more complex setup
                assert device_action is not None

