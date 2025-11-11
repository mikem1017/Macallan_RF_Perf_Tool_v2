"""Unit tests for DeviceRepository."""

import pytest

from src.core.models.device import Device
from src.core.exceptions import DeviceNotFoundError, DatabaseError
from src.core.repositories.device_repository import DeviceRepository


class TestDeviceRepository:
    """Test DeviceRepository CRUD operations."""
    
    def test_create_device(self, device_repository, sample_device):
        """Test creating a device."""
        created = device_repository.create(sample_device)
        
        assert created.id == sample_device.id
        assert created.name == sample_device.name
        assert created.part_number == sample_device.part_number
    
    def test_get_by_id_exists(self, device_repository, sample_device):
        """Test getting a device by ID when it exists."""
        device_repository.create(sample_device)
        retrieved = device_repository.get_by_id(sample_device.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_device.id
        assert retrieved.name == sample_device.name
    
    def test_get_by_id_not_exists(self, device_repository):
        """Test getting a device by ID when it doesn't exist."""
        from uuid import uuid4
        retrieved = device_repository.get_by_id(uuid4())
        
        assert retrieved is None
    
    def test_get_all_empty(self, device_repository):
        """Test getting all devices when none exist."""
        devices = device_repository.get_all()
        
        assert devices == []
    
    def test_get_all_multiple(self, device_repository, sample_device):
        """Test getting all devices when multiple exist."""
        device1 = sample_device
        device2 = Device(
            name="Another Device",
            part_number="L789012",
            operational_freq_min=1.0,
            operational_freq_max=3.0,
            wideband_freq_min=0.5,
            wideband_freq_max=6.0,
            input_ports=[1],
            output_ports=[2]
        )
        
        device_repository.create(device1)
        device_repository.create(device2)
        
        devices = device_repository.get_all()
        
        assert len(devices) == 2
        names = {d.name for d in devices}
        assert "Test Device" in names
        assert "Another Device" in names
    
    def test_update_device(self, device_repository, sample_device):
        """Test updating a device."""
        device_repository.create(sample_device)
        
        sample_device.name = "Updated Device"
        sample_device.description = "Updated description"
        
        updated = device_repository.update(sample_device)
        
        assert updated.name == "Updated Device"
        assert updated.description == "Updated description"
        
        # Verify it was actually updated
        retrieved = device_repository.get_by_id(sample_device.id)
        assert retrieved.name == "Updated Device"
    
    def test_update_device_not_exists(self, device_repository, sample_device):
        """Test updating a non-existent device raises error."""
        with pytest.raises(DeviceNotFoundError):
            device_repository.update(sample_device)
    
    def test_delete_device(self, device_repository, sample_device):
        """Test deleting a device."""
        device_repository.create(sample_device)
        device_repository.delete(sample_device.id)
        
        retrieved = device_repository.get_by_id(sample_device.id)
        assert retrieved is None
    
    def test_delete_device_not_exists(self, device_repository):
        """Test deleting a non-existent device raises error."""
        from uuid import uuid4
        with pytest.raises(DeviceNotFoundError):
            device_repository.delete(uuid4())
    
    def test_multi_gain_mode_persistence(self, device_repository, sample_device_multi_gain):
        """Test that multi-gain mode is correctly persisted."""
        device_repository.create(sample_device_multi_gain)
        retrieved = device_repository.get_by_id(sample_device_multi_gain.id)
        
        assert retrieved.multi_gain_mode is True
    
    def test_tests_performed_persistence(self, device_repository):
        """Test that tests_performed list is correctly persisted."""
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            tests_performed=["S-Parameters", "Power/Linearity"],
            input_ports=[1],
            output_ports=[2]
        )
        
        device_repository.create(device)
        retrieved = device_repository.get_by_id(device.id)
        
        assert retrieved.tests_performed == ["S-Parameters", "Power/Linearity"]
