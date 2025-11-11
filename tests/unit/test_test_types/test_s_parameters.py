"""Unit tests for S-Parameters test type."""

import pytest
from pathlib import Path
from uuid import uuid4

from src.core.test_types.s_parameters import SParametersTestType
from src.core.test_types.registry import TestTypeRegistry
from src.core.models.measurement import Measurement
from src.core.models.test_criteria import TestCriteria
from src.core.rf_data.touchstone_loader import TouchstoneLoader
from datetime import date


class TestSParametersTestType:
    """Test S-Parameters test type implementation."""
    
    @pytest.fixture
    def test_type(self):
        """Provide S-Parameters test type instance."""
        return SParametersTestType()
    
    @pytest.fixture
    def sample_measurement(self):
        """Provide a sample measurement with real data."""
        loader = TouchstoneLoader()
        network, metadata = loader.load_with_metadata(
            Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        )
        
        # Serialize network for storage
        serialized = loader.serialize_network(network)
        
        return Measurement(
            device_id=uuid4(),
            serial_number=metadata["serial_number"],
            test_type="S-Parameters",
            test_stage="SIT",
            temperature=metadata["temperature"],
            path_type=metadata["path_type"],
            file_path=str(Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")),
            measurement_date=metadata["date"],
            touchstone_data=serialized
        )
    
    @pytest.fixture
    def sample_device(self):
        """Provide a sample device with port configuration."""
        from src.core.models.device import Device
        return Device(
            name="Test Device",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1, 2],
            output_ports=[3, 4]
        )
    
    @pytest.fixture
    def sample_criteria(self):
        """Provide sample test criteria with generic names."""
        device_id = uuid4()
        
        criteria = [
            # Gain range criteria (generic)
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="Gain Range",
                criteria_type="range",
                min_value=27.5,
                max_value=31.3,
                unit="dB"
            ),
            # Gain flatness criteria (generic)
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="Gain Flatness",
                criteria_type="max",
                max_value=2.3,
                unit="dB"
            ),
            # VSWR criteria (generic)
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="VSWR Max",
                criteria_type="max",
                max_value=2.0,
                unit=""
            ),
            # OOB criteria
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="OOB 1",
                criteria_type="greater_than_equal",
                min_value=25.0,
                unit="dBc",
                frequency_min=3.0,   # OOB range minimum (3 GHz)
                frequency_max=5.0   # OOB range maximum (5 GHz)
            )
        ]
        
        return criteria
    
    def test_test_type_properties(self, test_type):
        """Test test type name and description."""
        assert test_type.name == "S-Parameters"
        assert "S-Parameter" in test_type.description
    
    def test_calculate_metrics(self, test_type, sample_measurement):
        """Test metric calculation."""
        metrics = test_type.calculate_metrics(
            sample_measurement,
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Should calculate metrics for all S-parameters in 4-port file
        # Check some common ones
        assert "S21 Gain Range" in metrics or "S31 Gain Range" in metrics
        assert "S11 VSWR" in metrics  # VSWR for port 1
        
        # Check gain range structure
        for key in metrics.keys():
            if "Gain Range" in key:
                gain_range = metrics[key]
                assert "min" in gain_range
                assert "max" in gain_range
                assert isinstance(gain_range["min"], float)
                assert isinstance(gain_range["max"], float)
                break
    
    def test_evaluate_compliance_gain_range(self, test_type, sample_measurement, sample_device, sample_criteria):
        """Test compliance evaluation for gain range."""
        # Update measurement device_id to match criteria
        sample_measurement.device_id = sample_criteria[0].device_id
        sample_device.id = sample_criteria[0].device_id
        
        results = test_type.evaluate_compliance(
            sample_measurement,
            sample_device,
            [sample_criteria[0]],  # Just gain range criteria
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Should have one result per gain S-parameter (S31, S32, S41, S42 = 4 results)
        assert len(results) == 4
        for result in results:
            assert result.test_criteria_id == sample_criteria[0].id
            assert result.s_parameter is not None
            assert result.s_parameter.startswith("S")
            assert result.measured_value is not None
            assert isinstance(result.passed, bool)
    
    def test_evaluate_compliance_flatness(self, test_type, sample_measurement, sample_device, sample_criteria):
        """Test compliance evaluation for flatness."""
        sample_measurement.device_id = sample_criteria[1].device_id
        sample_device.id = sample_criteria[1].device_id
        
        results = test_type.evaluate_compliance(
            sample_measurement,
            sample_device,
            [sample_criteria[1]],  # Just flatness criteria
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Should have one result per gain S-parameter
        assert len(results) == 4
        for result in results:
            assert result.test_criteria_id == sample_criteria[1].id
            assert result.s_parameter is not None
            assert result.measured_value is not None
    
    def test_evaluate_compliance_vswr(self, test_type, sample_measurement, sample_device, sample_criteria):
        """Test compliance evaluation for VSWR."""
        sample_measurement.device_id = sample_criteria[2].device_id
        sample_device.id = sample_criteria[2].device_id
        
        results = test_type.evaluate_compliance(
            sample_measurement,
            sample_device,
            [sample_criteria[2]],  # Just VSWR criteria
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Should have one result per port (S11, S22, S33, S44 = 4 results)
        assert len(results) == 4
        for result in results:
            assert result.test_criteria_id == sample_criteria[2].id
            assert result.s_parameter is not None
            assert result.s_parameter in ["S11", "S22", "S33", "S44"]
            assert result.measured_value is not None
    
    def test_evaluate_compliance_oob(self, test_type, sample_measurement, sample_device, sample_criteria):
        """Test compliance evaluation for OOB."""
        sample_measurement.device_id = sample_criteria[3].device_id
        sample_device.id = sample_criteria[3].device_id
        
        results = test_type.evaluate_compliance(
            sample_measurement,
            sample_device,
            [sample_criteria[3]],  # Just OOB criteria
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Should have one result per gain S-parameter
        assert len(results) == 4
        for result in results:
            assert result.test_criteria_id == sample_criteria[3].id
            assert result.s_parameter is not None
            assert result.measured_value is not None
    
    def test_evaluate_compliance_multiple(self, test_type, sample_measurement, sample_device, sample_criteria):
        """Test compliance evaluation with multiple criteria."""
        sample_measurement.device_id = sample_criteria[0].device_id
        sample_device.id = sample_criteria[0].device_id
        
        results = test_type.evaluate_compliance(
            sample_measurement,
            sample_device,
            sample_criteria,
            operational_freq_min=0.5,
            operational_freq_max=2.0
        )
        
        # Gain Range: 4 results (4 gain S-params)
        # Flatness: 4 results (4 gain S-params)
        # VSWR Max: 4 results (4 ports)
        # OOB 1: 4 results (4 gain S-params)
        # Total: 16 results
        assert len(results) == 16
        for result in results:
            assert result.measured_value is not None
            assert isinstance(result.passed, bool)
            assert result.s_parameter is not None
