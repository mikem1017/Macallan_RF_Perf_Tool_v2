"""Unit tests for Measurement model."""

import pytest
from datetime import date
from uuid import uuid4

from src.core.models.measurement import Measurement


class TestMeasurementModel:
    """Test Measurement model validation and behavior."""
    
    @pytest.fixture
    def device_id(self):
        """Provide a device ID for testing."""
        return uuid4()
    
    def test_create_valid_measurement(self, device_id):
        """Test creating a valid measurement."""
        # Note: touchstone_data would normally be a scikit-rf Network object
        # For testing, we'll use a mock object
        class MockNetwork:
            pass
        
        mock_network = MockNetwork()
        measurement = Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=mock_network
        )
        
        assert measurement.serial_number == "SN0001"
        assert measurement.temperature == "AMB"
        assert measurement.path_type == "PRI"
        assert measurement.metadata == {}
    
    def test_temperature_validation(self, device_id):
        """Test temperature validation."""
        valid_temps = ["AMB", "HOT", "COLD"]
        
        class MockNetwork:
            pass
        
        for temp in valid_temps:
            measurement = Measurement(
                device_id=device_id,
                serial_number="SN0001",
                test_type="S-Parameters",
                test_stage="SIT",
                temperature=temp,
                path_type="PRI",
                file_path="/path/to/file.s4p",
                measurement_date=date(2025, 9, 30),
                touchstone_data=MockNetwork()
            )
            assert measurement.temperature == temp
        
        with pytest.raises(ValueError, match="temperature must be one of"):
            Measurement(
                device_id=device_id,
                serial_number="SN0001",
                test_type="S-Parameters",
                test_stage="SIT",
                temperature="INVALID",
                path_type="PRI",
                file_path="/path/to/file.s4p",
                measurement_date=date(2025, 9, 30),
                touchstone_data=MockNetwork()
            )
    
    def test_path_type_validation(self, device_id):
        """Test path type validation."""
        class MockNetwork:
            pass
        
        valid_paths = ["PRI", "RED", "PRI_HG", "PRI_LG", "RED_HG", "RED_LG"]
        
        for path in valid_paths:
            measurement = Measurement(
                device_id=device_id,
                serial_number="SN0001",
                test_type="S-Parameters",
                test_stage="SIT",
                temperature="AMB",
                path_type=path,
                file_path="/path/to/file.s4p",
                measurement_date=date(2025, 9, 30),
                touchstone_data=MockNetwork()
            )
            assert measurement.path_type == path
        
        with pytest.raises(ValueError, match="path_type must be one of"):
            Measurement(
                device_id=device_id,
                serial_number="SN0001",
                test_type="S-Parameters",
                test_stage="SIT",
                temperature="AMB",
                path_type="INVALID",
                file_path="/path/to/file.s4p",
                measurement_date=date(2025, 9, 30),
                touchstone_data=MockNetwork()
            )
    
    def test_metadata_persistence(self, device_id):
        """Test that metadata can be set and persists."""
        class MockNetwork:
            pass
        
        metadata = {
            "part_number": "L109908",
            "run_number": "Run1"
        }
        
        measurement = Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=MockNetwork(),
            metadata=metadata
        )
        
        assert measurement.metadata == metadata
