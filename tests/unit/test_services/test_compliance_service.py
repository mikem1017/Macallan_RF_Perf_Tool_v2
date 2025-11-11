"""Unit tests for ComplianceService."""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import date

from src.core.services.compliance_service import ComplianceService
from src.core.models.device import Device
from src.core.models.measurement import Measurement
from src.core.models.test_criteria import TestCriteria
from src.core.models.test_result import TestResult
from src.core.test_types.registry import TestTypeRegistry
from src.core.exceptions import DeviceNotFoundError


class TestComplianceService:
    """Test ComplianceService business logic."""
    
    @pytest.fixture
    def measurement_repo(self):
        """Mock measurement repository."""
        return Mock()
    
    @pytest.fixture
    def criteria_repo(self):
        """Mock criteria repository."""
        return Mock()
    
    @pytest.fixture
    def device_repo(self):
        """Mock device repository."""
        return Mock()
    
    @pytest.fixture
    def result_repo(self):
        """Mock result repository."""
        return Mock()
    
    @pytest.fixture
    def test_type_registry(self):
        """Mock test type registry."""
        return Mock()
    
    @pytest.fixture
    def service(self, measurement_repo, criteria_repo, device_repo, result_repo, test_type_registry):
        """Provide ComplianceService with mocked dependencies."""
        return ComplianceService(
            measurement_repository=measurement_repo,
            criteria_repository=criteria_repo,
            device_repository=device_repo,
            result_repository=result_repo,
            test_type_registry=test_type_registry
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
    
    @pytest.fixture
    def sample_measurement(self, sample_device):
        """Provide a sample measurement."""
        mock_network = MagicMock()
        mock_network.nports = 4
        
        return Measurement(
            device_id=sample_device.id,
            serial_number="SN0001",
            test_type="S-Parameters",
            test_stage="SIT",
            temperature="AMB",
            path_type="PRI",
            file_path="/path/to/file.s4p",
            measurement_date=date(2025, 9, 30),
            touchstone_data=mock_network,
            metadata={}
        )
    
    @pytest.fixture
    def sample_criteria(self, sample_device):
        """Provide sample test criteria."""
        return [
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
    
    def test_evaluate_compliance(self, service, device_repo, criteria_repo, test_type_registry,
                                 sample_device, sample_measurement, sample_criteria):
        """Test evaluating compliance for a measurement."""
        device_repo.get_by_id.return_value = sample_device
        criteria_repo.get_by_device_and_test.return_value = sample_criteria
        
        # Mock test type
        mock_test_type = Mock()
        mock_test_type.evaluate_compliance.return_value = [
            TestResult(
                measurement_id=sample_measurement.id,
                test_criteria_id=sample_criteria[0].id,
                measured_value=29.5,
                passed=True,
                s_parameter="S21"
            )
        ]
        test_type_registry.get.return_value = mock_test_type
        
        results = service.evaluate_compliance(sample_measurement, sample_device, "SIT")
        
        assert len(results) == 1
        assert results[0].passed is True
        mock_test_type.evaluate_compliance.assert_called_once()
    
    def test_evaluate_compliance_no_criteria(self, service, device_repo, criteria_repo,
                                            sample_device, sample_measurement):
        """Test evaluating when no criteria defined."""
        device_repo.get_by_id.return_value = sample_device
        criteria_repo.get_by_device_and_test.return_value = []  # No criteria
        
        results = service.evaluate_compliance(sample_measurement, sample_device, "SIT")
        
        assert len(results) == 0
    
    def test_evaluate_compliance_no_test_type(self, service, device_repo, criteria_repo, test_type_registry,
                                              sample_device, sample_measurement, sample_criteria):
        """Test evaluating when test type not registered."""
        device_repo.get_by_id.return_value = sample_device
        criteria_repo.get_by_device_and_test.return_value = sample_criteria
        test_type_registry.get.return_value = None  # Test type not found
        
        results = service.evaluate_compliance(sample_measurement, sample_device, "SIT")
        
        assert len(results) == 0
    
    def test_evaluate_all_measurements(self, service, device_repo, measurement_repo, criteria_repo,
                                       test_type_registry, sample_device, sample_measurement, sample_criteria):
        """Test evaluating all measurements."""
        device_repo.get_by_id.return_value = sample_device
        # Changed: get_by_device() returns all measurements for device, then filtered by test_type
        measurement_repo.get_by_device.return_value = [sample_measurement]
        criteria_repo.get_by_device_and_test.return_value = sample_criteria
        
        # Mock test type
        mock_test_type = Mock()
        mock_test_type.evaluate_compliance.return_value = [
            TestResult(
                measurement_id=sample_measurement.id,
                test_criteria_id=sample_criteria[0].id,
                measured_value=29.5,
                passed=True,
                s_parameter="S21"
            )
        ]
        test_type_registry.get.return_value = mock_test_type
        
        results = service.evaluate_all_measurements(
            sample_device.id, "S-Parameters", "SIT"
        )
        
        assert len(results) == 1
        assert sample_measurement.id in results
    
    def test_save_test_results(self, service, result_repo):
        """Test saving test results."""
        results = [
            TestResult(
                measurement_id=uuid4(),
                test_criteria_id=uuid4(),
                measured_value=29.5,
                passed=True,
                s_parameter="S21"
            )
        ]
        result_repo.create.return_value = results[0]
        
        saved = service.save_test_results(results)
        
        assert len(saved) == 1
        result_repo.create.assert_called_once()
    
    def test_get_overall_pass_status_all_pass(self, service, result_repo):
        """Test overall pass status when all results pass."""
        measurement_id = uuid4()
        results = [
            TestResult(
                measurement_id=measurement_id,
                test_criteria_id=uuid4(),
                measured_value=29.5,
                passed=True,
                s_parameter="S21"
            ),
            TestResult(
                measurement_id=measurement_id,
                test_criteria_id=uuid4(),
                measured_value=1.8,
                passed=True,
                s_parameter="S11"
            )
        ]
        result_repo.get_by_measurement_id.return_value = results
        
        status = service.get_overall_pass_status(measurement_id)
        
        assert status is True
    
    def test_get_overall_pass_status_one_fails(self, service, result_repo):
        """Test overall pass status when one result fails."""
        measurement_id = uuid4()
        results = [
            TestResult(
                measurement_id=measurement_id,
                test_criteria_id=uuid4(),
                measured_value=29.5,
                passed=True,
                s_parameter="S21"
            ),
            TestResult(
                measurement_id=measurement_id,
                test_criteria_id=uuid4(),
                measured_value=3.0,
                passed=False,  # Fails
                s_parameter="S11"
            )
        ]
        result_repo.get_by_measurement_id.return_value = results
        
        status = service.get_overall_pass_status(measurement_id)
        
        assert status is False
    
    def test_mark_results_stale_for_criteria(self, service, result_repo):
        """Test marking results as stale."""
        criteria_id = uuid4()
        result_repo.mark_as_stale_by_criteria.return_value = 5
        
        count = service.mark_results_stale_for_criteria(criteria_id)
        
        assert count == 5
        result_repo.mark_as_stale_by_criteria.assert_called_once_with(criteria_id)

