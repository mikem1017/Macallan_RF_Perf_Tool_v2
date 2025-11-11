"""Unit tests for DeviceService."""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from src.core.services.device_service import DeviceService
from src.core.models.device import Device
from src.core.models.test_criteria import TestCriteria
from src.core.exceptions import DeviceNotFoundError


class TestDeviceService:
    """Test DeviceService business logic."""
    
    @pytest.fixture
    def device_repo(self):
        """Mock device repository."""
        return Mock()
    
    @pytest.fixture
    def criteria_repo(self):
        """Mock criteria repository."""
        return Mock()
    
    @pytest.fixture
    def measurement_repo(self):
        """Mock measurement repository."""
        return Mock()
    
    @pytest.fixture
    def result_repo(self):
        """Mock result repository."""
        return Mock()
    
    @pytest.fixture
    def service(self, device_repo, criteria_repo, measurement_repo, result_repo):
        """Provide DeviceService with mocked dependencies."""
        return DeviceService(
            device_repository=device_repo,
            criteria_repository=criteria_repo,
            measurement_repository=measurement_repo,
            result_repository=result_repo
        )
    
    @pytest.fixture
    def sample_device(self):
        """Provide a sample device."""
        return Device(
            name="Test Device",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1],
            output_ports=[2]
        )
    
    def test_create_device(self, service, device_repo, sample_device):
        """Test creating a device."""
        device_repo.create.return_value = sample_device
        
        result = service.create_device(sample_device)
        
        device_repo.create.assert_called_once_with(sample_device)
        assert result == sample_device
    
    def test_get_device(self, service, device_repo, sample_device):
        """Test getting a device."""
        device_repo.get_by_id.return_value = sample_device
        
        result = service.get_device(sample_device.id)
        
        device_repo.get_by_id.assert_called_once_with(sample_device.id)
        assert result == sample_device
    
    def test_get_all_devices(self, service, device_repo, sample_device):
        """Test getting all devices."""
        device_repo.get_all.return_value = [sample_device]
        
        result = service.get_all_devices()
        
        device_repo.get_all.assert_called_once()
        assert len(result) == 1
    
    def test_update_device(self, service, device_repo, sample_device):
        """Test updating a device."""
        device_repo.update.return_value = sample_device
        
        result = service.update_device(sample_device)
        
        device_repo.update.assert_called_once_with(sample_device)
        assert result == sample_device
    
    def test_get_deletion_info(self, service, device_repo, criteria_repo, measurement_repo, sample_device):
        """Test getting deletion information."""
        device_repo.get_by_id.return_value = sample_device
        criteria_repo.get_all.return_value = [
            TestCriteria(
                device_id=sample_device.id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="Gain Range",
                criteria_type="range",
                min_value=27.5,
                max_value=31.3,
                unit="dB"
            )
        ]
        measurement_repo.get_by_device.return_value = [Mock()]  # Mock measurement
        
        info = service.get_deletion_info(sample_device.id)
        
        assert info["device"] == sample_device
        assert info["criteria_count"] == 1
        assert info["measurement_count"] == 1
        assert info["has_related_data"] is True
    
    def test_get_deletion_info_no_device(self, service, device_repo):
        """Test getting deletion info when device doesn't exist."""
        device_repo.get_by_id.return_value = None
        
        with pytest.raises(DeviceNotFoundError):
            service.get_deletion_info(uuid4())
    
    def test_get_criteria_for_device(self, service, criteria_repo, sample_device):
        """Test getting criteria for device."""
        criteria_list = [
            TestCriteria(
                device_id=sample_device.id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="Gain Range",
                criteria_type="range",
                min_value=27.5,
                max_value=31.3,
                unit="dB"
            )
        ]
        criteria_repo.get_by_device_and_test.return_value = criteria_list
        
        result = service.get_criteria_for_device(
            sample_device.id, "S-Parameters", "SIT"
        )
        
        criteria_repo.get_by_device_and_test.assert_called_once_with(
            sample_device.id, "S-Parameters", "SIT"
        )
        assert len(result) == 1
    
    def test_add_criteria(self, service, criteria_repo):
        """Test adding criteria."""
        criteria = TestCriteria(
            device_id=uuid4(),
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="Gain Range",
            criteria_type="range",
            min_value=27.5,
            max_value=31.3,
            unit="dB"
        )
        criteria_repo.create.return_value = criteria
        
        result = service.add_criteria(criteria)
        
        criteria_repo.create.assert_called_once_with(criteria)
        assert result == criteria
    
    def test_update_criteria_marks_results_stale(self, service, criteria_repo, result_repo):
        """Test that updating criteria marks results as stale."""
        criteria = TestCriteria(
            device_id=uuid4(),
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="Gain Range",
            criteria_type="range",
            min_value=27.5,
            max_value=31.3,
            unit="dB"
        )
        criteria_repo.update.return_value = criteria
        result_repo.mark_as_stale_by_criteria.return_value = 5
        
        result = service.update_criteria(criteria)
        
        criteria_repo.update.assert_called_once_with(criteria)
        result_repo.mark_as_stale_by_criteria.assert_called_once_with(criteria.id)
        assert result == criteria
    
    def test_delete_criteria(self, service, criteria_repo):
        """Test deleting criteria."""
        criteria_id = uuid4()
        
        service.delete_criteria(criteria_id)
        
        criteria_repo.delete.assert_called_once_with(criteria_id)











