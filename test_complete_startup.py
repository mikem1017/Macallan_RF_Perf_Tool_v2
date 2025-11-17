"""
Complete startup test that simulates the actual application launch.
This test should catch any initialization errors that occur during startup.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_complete_app_startup():
    """Test complete application startup sequence exactly as main() does."""
    print("Testing Complete Application Startup...")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.main import main
        
        # This should work exactly like running the app
        # We'll use sys.exit to catch the exit code
        print("  Creating QApplication...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("  Calling main()...")
        # We can't actually run main() because it enters event loop
        # Instead, let's test the initialization steps manually
        from src.gui.utils.service_factory import create_services
        from src.gui.main_window import MainWindow
        
        print("  Creating services...")
        device_service, measurement_service, compliance_service, conn = create_services()
        
        print("  Verifying services...")
        assert device_service is not None
        assert device_service.criteria_repo is not None
        assert hasattr(device_service.criteria_repo, 'get_by_device_and_test')
        
        print("  Creating MainWindow...")
        window = MainWindow(
            device_service=device_service,
            measurement_service=measurement_service,
            compliance_service=compliance_service
        )
        
        print("  Showing window...")
        window.show()
        
        print("  Processing events...")
        app.processEvents()
        
        print("  ✓ Complete startup successful")
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_device_maintenance_dialog_startup():
    """Test DeviceMaintenanceDialog startup which triggers DeviceListWidget refresh."""
    print("\nTesting DeviceMaintenanceDialog Startup...")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.utils.service_factory import create_services
        from src.gui.widgets.device_maintenance.device_maintenance_dialog import DeviceMaintenanceDialog
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("  Creating services...")
        device_service, measurement_service, compliance_service, conn = create_services()
        
        print("  Verifying device_service.criteria_repo...")
        if device_service.criteria_repo is None:
            raise ValueError("device_service.criteria_repo is None before creating dialog")
        
        print("  Creating DeviceMaintenanceDialog...")
        dialog = DeviceMaintenanceDialog(device_service=device_service)
        
        print("  Showing dialog...")
        dialog.show()
        
        print("  Processing events...")
        app.processEvents()
        
        print("  ✓ DeviceMaintenanceDialog startup successful")
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_device_selection_with_real_data():
    """Test selecting a device with real database data."""
    print("\nTesting Device Selection with Real Data...")
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.utils.service_factory import create_services
        from src.gui.widgets.device_maintenance.device_maintenance_dialog import DeviceMaintenanceDialog
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("  Creating services...")
        device_service, measurement_service, compliance_service, conn = create_services()
        
        print("  Getting all devices...")
        devices = device_service.get_all_devices()
        if not devices:
            print("  ⚠ No devices in database, skipping device selection test")
            conn.close()
            return True
        
        print(f"  Found {len(devices)} devices")
        
        print("  Creating DeviceMaintenanceDialog...")
        dialog = DeviceMaintenanceDialog(device_service=device_service)
        dialog.show()
        app.processEvents()
        
        # Select first device
        if devices:
            device = devices[0]
            print(f"  Selecting device: {device.part_number}")
            dialog._on_device_selected(device)
            app.processEvents()
            print("  ✓ Device selection successful")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all startup tests."""
    print("=" * 60)
    print("Complete Startup Test Suite")
    print("=" * 60)
    
    results = []
    results.append(("Complete App Startup", test_complete_app_startup()))
    results.append(("DeviceMaintenanceDialog Startup", test_device_maintenance_dialog_startup()))
    results.append(("Device Selection with Real Data", test_device_selection_with_real_data()))
    
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














