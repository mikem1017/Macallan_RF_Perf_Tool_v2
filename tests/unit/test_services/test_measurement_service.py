"""Unit tests for MeasurementService."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
from datetime import date

from src.core.services.measurement_service import MeasurementService
from src.core.models.device import Device
from src.core.models.measurement import Measurement
from src.core.exceptions import FileLoadError, ValidationError, DeviceNotFoundError


class TestMeasurementService:
    """Test MeasurementService business logic."""
    
    @pytest.fixture
    def measurement_repo(self):
        """Mock measurement repository."""
        return Mock()
    
    @pytest.fixture
    def device_repo(self):
        """Mock device repository."""
        return Mock()
    
    @pytest.fixture
    def touchstone_loader(self):
        """Mock touchstone loader."""
        return Mock()
    
    @pytest.fixture
    def filename_parser(self):
        """Mock filename parser."""
        return Mock()
    
    @pytest.fixture
    def service(self, measurement_repo, device_repo, touchstone_loader, filename_parser):
        """Provide MeasurementService with mocked dependencies."""
        return MeasurementService(
            measurement_repository=measurement_repo,
            device_repository=device_repo,
            touchstone_loader=touchstone_loader,
            filename_parser=filename_parser
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
            multi_gain_mode=False,
            input_ports=[1],
            output_ports=[2]
        )
    
    @pytest.fixture
    def mock_network(self):
        """Mock Network object."""
        network = MagicMock()
        network.nports = 4
        network.f = [1e9, 2e9, 3e9]  # Mock frequency array
        return network
    
    def test_load_measurement_file(self, service, device_repo, touchstone_loader, filename_parser, sample_device, mock_network):
        """Test loading a single measurement file."""
        filepath = Path("test_file.s4p")
        
        # Mock device exists
        device_repo.get_by_id.return_value = sample_device
        
        # Mock file loading
        metadata = {
            "serial_number": "SN0001",
            "part_number": "L123456",
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "PRI",
            "file_path": str(filepath),
            "test_type": "S-Parameters"
        }
        touchstone_loader.load_with_metadata.return_value = (mock_network, metadata)
        
        measurement, warning = service.load_measurement_file(filepath, sample_device, "SIT")
        
        assert measurement.device_id == sample_device.id
        assert measurement.serial_number == "SN0001"
        assert measurement.test_stage == "SIT"
        assert warning is None  # Part number matches
    
    def test_load_measurement_file_part_number_mismatch(self, service, device_repo, touchstone_loader, filename_parser, sample_device, mock_network):
        """Test loading file with part number mismatch."""
        filepath = Path("test_file.s4p")
        
        device_repo.get_by_id.return_value = sample_device
        
        # Part number in filename doesn't match device
        metadata = {
            "serial_number": "SN0001",
            "part_number": "L999999",  # Different from device's L123456
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "PRI",
            "file_path": str(filepath),
            "test_type": "S-Parameters"
        }
        touchstone_loader.load_with_metadata.return_value = (mock_network, metadata)
        
        measurement, warning = service.load_measurement_file(filepath, sample_device, "SIT")
        
        assert measurement is not None
        assert warning is not None
        assert "L999999" in warning
        assert "L123456" in warning
    
    def test_load_measurement_file_device_not_found(self, service, device_repo, sample_device):
        """Test loading file when device doesn't exist."""
        device_repo.get_by_id.return_value = None
        
        with pytest.raises(DeviceNotFoundError):
            service.load_measurement_file(Path("test.s4p"), sample_device, "SIT")
    
    def test_load_multiple_files_standard_mode(self, service, device_repo, touchstone_loader, sample_device, mock_network):
        """Test loading 2 files for standard mode."""
        filepaths = [Path("pri.s4p"), Path("red.s4p")]
        
        device_repo.get_by_id.return_value = sample_device
        
        # Mock metadata for both files
        metadata1 = {
            "serial_number": "SN0001",
            "part_number": "L123456",
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "PRI",
            "file_path": str(filepaths[0]),
            "test_type": "S-Parameters"
        }
        metadata2 = {
            "serial_number": "SN0001",
            "part_number": "L123456",
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "RED",
            "file_path": str(filepaths[1]),
            "test_type": "S-Parameters"
        }
        
        touchstone_loader.load_with_metadata.side_effect = [
            (mock_network, metadata1),
            (mock_network, metadata2)
        ]
        
        measurements, warnings = service.load_multiple_files(
            filepaths, sample_device, "SIT", "AMB"
        )
        
        assert len(measurements) == 2
        assert {m.path_type for m in measurements} == {"PRI", "RED"}
        assert len(warnings) == 0
    
    def test_load_multiple_files_multi_gain_mode(self, service, device_repo, touchstone_loader, sample_device, mock_network):
        """Test loading 4 files for multi-gain mode."""
        # Enable multi-gain mode
        sample_device.multi_gain_mode = True
        
        filepaths = [
            Path("pri_hg.s4p"), Path("pri_lg.s4p"),
            Path("red_hg.s4p"), Path("red_lg.s4p")
        ]
        
        device_repo.get_by_id.return_value = sample_device
        
        # Mock metadata for all 4 files
        metadata_list = [
            {"serial_number": "SN0001", "part_number": "L123456", "date": date(2025, 9, 30),
             "temperature": "AMB", "path_type": "PRI_HG", "file_path": str(filepaths[0]), "test_type": "S-Parameters"},
            {"serial_number": "SN0001", "part_number": "L123456", "date": date(2025, 9, 30),
             "temperature": "AMB", "path_type": "PRI_LG", "file_path": str(filepaths[1]), "test_type": "S-Parameters"},
            {"serial_number": "SN0001", "part_number": "L123456", "date": date(2025, 9, 30),
             "temperature": "AMB", "path_type": "RED_HG", "file_path": str(filepaths[2]), "test_type": "S-Parameters"},
            {"serial_number": "SN0001", "part_number": "L123456", "date": date(2025, 9, 30),
             "temperature": "AMB", "path_type": "RED_LG", "file_path": str(filepaths[3]), "test_type": "S-Parameters"},
        ]
        
        touchstone_loader.load_with_metadata.side_effect = [
            (mock_network, md) for md in metadata_list
        ]
        
        measurements, warnings = service.load_multiple_files(
            filepaths, sample_device, "SIT", "AMB"
        )
        
        assert len(measurements) == 4
        assert len(warnings) == 0
    
    def test_load_multiple_files_wrong_count(self, service, sample_device):
        """Test loading wrong number of files."""
        filepaths = [Path("file1.s4p"), Path("file2.s4p"), Path("file3.s4p")]  # 3 files - invalid
        
        with pytest.raises(ValidationError, match="Expected 2 or 4 files"):
            service.load_multiple_files(filepaths, sample_device, "SIT", "AMB")
    
    def test_load_multiple_files_mismatched_serial(self, service, device_repo, touchstone_loader, sample_device, mock_network):
        """Test loading files with mismatched serial numbers."""
        filepaths = [Path("pri.s4p"), Path("red.s4p")]
        
        device_repo.get_by_id.return_value = sample_device
        
        # Different serial numbers
        metadata1 = {
            "serial_number": "SN0001",
            "part_number": "L123456",
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "PRI",
            "file_path": str(filepaths[0]),
            "test_type": "S-Parameters"
        }
        metadata2 = {
            "serial_number": "SN0002",  # Different serial
            "part_number": "L123456",
            "date": date(2025, 9, 30),
            "temperature": "AMB",
            "path_type": "RED",
            "file_path": str(filepaths[1]),
            "test_type": "S-Parameters"
        }
        
        touchstone_loader.load_with_metadata.side_effect = [
            (mock_network, metadata1),
            (mock_network, metadata2)
        ]
        
        measurements, warnings = service.load_multiple_files(
            filepaths, sample_device, "SIT", "AMB"
        )
        
        assert len(measurements) == 2  # Still loaded
        assert len(warnings) > 0  # Has warning about mismatch
        assert any("serial number" in w.lower() for w in warnings)
    
    def test_save_measurement(self, service, measurement_repo):
        """Test saving a measurement."""
        measurement = Mock(spec=Measurement)
        measurement.id = uuid4()
        measurement_repo.create.return_value = measurement
        
        result = service.save_measurement(measurement)
        
        measurement_repo.create.assert_called_once_with(measurement)
        assert result == measurement
    
    def test_get_measurements_for_device(self, service, measurement_repo, sample_device):
        """Test getting measurements for device."""
        measurements = [Mock(), Mock()]
        measurement_repo.get_by_device_and_test_stage.return_value = measurements
        
        result = service.get_measurements_for_device(
            sample_device.id, "S-Parameters", "SIT"
        )
        
        measurement_repo.get_by_device_and_test_stage.assert_called_once_with(
            sample_device.id, "S-Parameters", "SIT"
        )
        assert len(result) == 2











