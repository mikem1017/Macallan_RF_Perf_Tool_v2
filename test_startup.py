"""
Test script to verify application startup.
Tests the complete startup sequence to catch initialization errors.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_service_factory():
    """Test service factory creates services correctly."""
    print("Test 1: Service Factory")
    try:
        from src.gui.utils.service_factory import create_services
        device_service, measurement_service, compliance_service, conn = create_services()
        
        # Verify services are created
        assert device_service is not None, "DeviceService is None"
        assert measurement_service is not None, "MeasurementService is None"
        assert compliance_service is not None, "ComplianceService is None"
        
        # Verify criteria_repo is set
        assert device_service.criteria_repo is not None, "DeviceService.criteria_repo is None"
        assert hasattr(device_service.criteria_repo, 'get_by_device_and_test'), \
            "criteria_repo missing get_by_device_and_test method"
        
        print("  ✓ Service factory creates services correctly")
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_main_window_creation():
    """Test MainWindow can be created."""
    print("\nTest 2: MainWindow Creation")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.utils.service_factory import create_services
        from src.gui.main_window import MainWindow
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create services
        device_service, measurement_service, compliance_service, conn = create_services()
        
        # Verify criteria_repo before creating MainWindow
        if device_service.criteria_repo is None:
            raise ValueError("DeviceService.criteria_repo is None before MainWindow creation")
        
        # Create MainWindow
        window = MainWindow(
            device_service=device_service,
            measurement_service=measurement_service,
            compliance_service=compliance_service
        )
        
        assert window is not None, "MainWindow is None"
        print("  ✓ MainWindow created successfully")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_device_maintenance_dialog_creation():
    """Test DeviceMaintenanceDialog can be created."""
    print("\nTest 3: DeviceMaintenanceDialog Creation")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.utils.service_factory import create_services
        from src.gui.widgets.device_maintenance.device_maintenance_dialog import DeviceMaintenanceDialog
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create services
        device_service, measurement_service, compliance_service, conn = create_services()
        
        # Verify criteria_repo before creating dialog
        if device_service.criteria_repo is None:
            raise ValueError("DeviceService.criteria_repo is None before dialog creation")
        
        # Create dialog
        dialog = DeviceMaintenanceDialog(device_service=device_service)
        
        assert dialog is not None, "DeviceMaintenanceDialog is None"
        print("  ✓ DeviceMaintenanceDialog created successfully")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_full_startup():
    """Test complete application startup sequence."""
    print("\nTest 4: Full Startup Sequence")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.utils.service_factory import create_services
        from src.gui.main_window import MainWindow
        
        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create services
        device_service, measurement_service, compliance_service, conn = create_services()
        
        # Verify all services have required attributes
        if device_service.criteria_repo is None:
            raise ValueError("DeviceService.criteria_repo is None")
        
        # Create MainWindow
        window = MainWindow(
            device_service=device_service,
            measurement_service=measurement_service,
            compliance_service=compliance_service
        )
        
        # Try to show window (this triggers some initialization)
        window.show()
        
        # Process events to trigger any lazy initialization
        app.processEvents()
        
        print("  ✓ Full startup sequence completed")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all startup tests."""
    print("=" * 60)
    print("Application Startup Test Suite")
    print("=" * 60)
    
    results = []
    results.append(("Service Factory", test_service_factory()))
    results.append(("MainWindow Creation", test_main_window_creation()))
    results.append(("DeviceMaintenanceDialog Creation", test_device_maintenance_dialog_creation()))
    results.append(("Full Startup", test_full_startup()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())














