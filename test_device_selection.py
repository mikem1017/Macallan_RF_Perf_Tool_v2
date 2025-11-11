"""
Test script for device selection functionality.
Tests various device configurations to ensure no crashes occur.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.schema import create_schema, get_database_path
from src.core.repositories.device_repository import DeviceRepository
from src.core.models.device import Device
from src.core.services.device_service import DeviceService
from src.gui.widgets.device_maintenance.device_maintenance_dialog import DeviceMaintenanceDialog
import sqlite3
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from uuid import uuid4

def test_device_repository_edge_cases():
    """Test device repository with edge cases."""
    print("Testing Device Repository Edge Cases...")
    
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    repo = DeviceRepository(conn)
    
    # Test 1: Device with None frequencies
    print("  Test 1: Device with None frequencies...")
    try:
        device = Device(
            id=uuid4(),
            name="Test Device",
            part_number="L123456",
            operational_freq_min=1.0,
            operational_freq_max=2.0,
            wideband_freq_min=0.5,
            wideband_freq_max=3.0,
            input_ports=[1],
            output_ports=[2, 3],
            tests_performed=["S-Parameters"]
        )
        repo.create(device)
        
        # Try to retrieve it
        retrieved = repo.get_by_id(device.id)
        assert retrieved is not None, "Device not found"
        assert retrieved.operational_freq_min == 1.0, "Frequency not preserved"
        print("    ✓ Passed")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Device with empty lists
    print("  Test 2: Device with empty lists...")
    try:
        device = Device(
            id=uuid4(),
            name="Test Device 2",
            part_number="L234567",
            operational_freq_min=1.0,
            operational_freq_max=2.0,
            wideband_freq_min=0.5,
            wideband_freq_max=3.0,
            input_ports=[],
            output_ports=[],
            tests_performed=[]
        )
        repo.create(device)
        retrieved = repo.get_by_id(device.id)
        assert retrieved.tests_performed == [], "Empty list not preserved"
        print("    ✓ Passed")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        traceback.print_exc()
        return False
    
    conn.close()
    return True

def test_device_selection_with_real_data():
    """Test device selection with real database data."""
    print("\nTesting Device Selection with Real Data...")
    
    # Initialize QApplication if not exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Get real database
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        
        repo = DeviceRepository(conn)
        device_service = DeviceService(repo, None, None)  # Only need device repo for this test
        
        # Get all devices
        devices = device_service.get_all_devices()
        print(f"  Found {len(devices)} devices in database")
        
        # Find L109908
        l109908 = [d for d in devices if d.part_number == "L109908"]
        if not l109908:
            print("    ⚠ L109908 not found in database")
            return True
        
        device = l109908[0]
        print(f"  Testing device: {device.part_number}")
        print(f"    operational_freq_min: {device.operational_freq_min}")
        print(f"    operational_freq_max: {device.operational_freq_max}")
        print(f"    tests_performed: {device.tests_performed} (type: {type(device.tests_performed)})")
        print(f"    input_ports: {device.input_ports} (type: {type(device.input_ports)})")
        print(f"    output_ports: {device.output_ports} (type: {type(device.output_ports)})")
        
        # Test creating dialog and selecting device
        print("  Creating DeviceMaintenanceDialog...")
        dialog = DeviceMaintenanceDialog(device_service)
        
        print("  Calling _on_device_selected...")
        try:
            dialog._on_device_selected(device)
            print("    ✓ Passed - no crash")
            return True
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def test_device_selection_edge_cases():
    """Test device selection with various edge cases."""
    print("\nTesting Device Selection Edge Cases...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Create mock services
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        repo = DeviceRepository(conn)
        device_service = DeviceService(repo, None, None)
        
        # Test 1: Device with None tests_performed (should be handled)
        print("  Test 1: Device with None tests_performed...")
        try:
            device = Device(
                id=uuid4(),
                name="Test",
                part_number="L111111",
                operational_freq_min=1.0,
                operational_freq_max=2.0,
                wideband_freq_min=0.5,
                wideband_freq_max=3.0,
                input_ports=[1],
                output_ports=[2],
                tests_performed=[]
            )
            repo.create(device)
            
            dialog = DeviceMaintenanceDialog(device_service)
            dialog._on_device_selected(device)
            print("    ✓ Passed")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            traceback.print_exc()
            return False
        
        # Test 2: Device with valid tests_performed
        print("  Test 2: Device with S-Parameters test...")
        try:
            device = Device(
                id=uuid4(),
                name="Test 2",
                part_number="L222222",
                operational_freq_min=1.626,
                operational_freq_max=1.675,
                wideband_freq_min=0.1,
                wideband_freq_max=6.0,
                input_ports=[1],
                output_ports=[2, 3, 4],
                tests_performed=["S-Parameters"]
            )
            repo.create(device)
            
            dialog = DeviceMaintenanceDialog(device_service)
            dialog._on_device_selected(device)
            print("    ✓ Passed")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Device Selection Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Repository edge cases
    results.append(("Repository Edge Cases", test_device_repository_edge_cases()))
    
    # Test 2: Real data
    results.append(("Real Data Selection", test_device_selection_with_real_data()))
    
    # Test 3: Edge cases
    results.append(("Edge Cases", test_device_selection_edge_cases()))
    
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











