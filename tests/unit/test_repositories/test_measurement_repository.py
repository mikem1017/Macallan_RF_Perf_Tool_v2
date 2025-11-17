"""Unit tests for MeasurementRepository."""

import pytest
from uuid import uuid4
from datetime import date
from pathlib import Path

from src.core.repositories.measurement_repository import MeasurementRepository
from src.core.models.measurement import Measurement
from src.core.rf_data.touchstone_loader import TouchstoneLoader
from src.core.exceptions import FileLoadError


class TestMeasurementRepository:
    """Test MeasurementRepository CRUD operations."""
    
    @pytest.fixture
    def db_connection(self):
        """Provide in-memory database connection."""
        from src.database.schema import get_in_memory_connection
        conn = get_in_memory_connection()
        yield conn
        conn.close()
    
    @pytest.fixture
    def repository(self, db_connection):
        """Provide MeasurementRepository instance."""
        return MeasurementRepository(db_connection)
    
    @pytest.fixture
    def device_id(self):
        """Provide a device ID for testing."""
        return uuid4()
    
    @pytest.fixture
    def sample_network(self):
        """Load a sample Network object for testing."""
        try:
            loader = TouchstoneLoader()
            filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
            return loader.load_file(filepath)
        except FileLoadError:
            pytest.skip("scikit-rf not available or test file not found")
    
    @pytest.fixture
    def sample_measurement(self, device_id, sample_network):
        """Provide a sample Measurement for testing."""
        return Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=sample_network,
            metadata={"part_number": "L109908", "run_number": "Run1"}
        )
    
    def test_create_measurement(self, repository, sample_measurement):
        """Test creating a measurement."""
        created = repository.create(sample_measurement)
        
        assert created.id == sample_measurement.id
        assert created.serial_number == "SN0001"
        assert created.temperature == "AMB"
    
    def test_get_by_id_exists(self, repository, sample_measurement):
        """Test getting measurement by ID when it exists."""
        repository.create(sample_measurement)
        
        retrieved = repository.get_by_id(sample_measurement.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_measurement.id
        assert retrieved.serial_number == sample_measurement.serial_number
        # Network object should be deserialized
        assert retrieved.touchstone_data is not None
        assert hasattr(retrieved.touchstone_data, 'nports')
    
    def test_get_by_id_not_exists(self, repository):
        """Test getting measurement by ID when it doesn't exist."""
        result = repository.get_by_id(uuid4())
        assert result is None
    
    def test_get_by_device_and_test_stage(self, repository, device_id, sample_network):
        """Test getting measurements by device/test_type/test_stage."""
        # Create multiple measurements
        m1 = Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file1.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=sample_network,
            metadata={}
        )
        m2 = Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="HOT",
            path_type="RED",
            file_path="/path/to/file2.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=sample_network,
            metadata={}
        )
        
        repository.create(m1)
        repository.create(m2)
        
        # Get measurements for this device/test_type/test_stage
        results = repository.get_by_device_and_test_stage(
            device_id, "S-Parameters", "SIT"
        )
        
        assert len(results) == 2
        assert {r.temperature for r in results} == {"AMB", "HOT"}
    
    def test_get_by_serial_number(self, repository, device_id, sample_network):
        """Test getting measurements by serial number."""
        m1 = Measurement(
            device_id=device_id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file1.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=sample_network,
            metadata={}
        )
        
        repository.create(m1)
        
        results = repository.get_by_serial_number("SN0001")
        
        assert len(results) == 1
        assert results[0].serial_number == "SN0001"
    
    def test_network_serialization(self, repository, sample_measurement):
        """Test that Network objects are properly serialized/deserialized."""
        # Create measurement with Network object
        created = repository.create(sample_measurement)
        
        # Retrieve it
        retrieved = repository.get_by_id(created.id)
        
        # Network should be deserialized and functional
        assert retrieved is not None
        assert hasattr(retrieved.touchstone_data, 'nports')
        assert retrieved.touchstone_data.nports == 4  # S4P file
        assert len(retrieved.touchstone_data.f) > 0  # Has frequency data














