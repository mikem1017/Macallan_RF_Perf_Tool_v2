"""Unit tests for TestCriteria model."""

import pytest
from uuid import uuid4

from src.core.models.test_criteria import TestCriteria
from src.core.exceptions import TestCriteriaError


class TestTestCriteriaModel:
    """Test TestCriteria model validation and behavior."""
    
    @pytest.fixture
    def device_id(self):
        """Provide a device ID for testing."""
        return uuid4()
    
    def test_range_criteria_valid(self, device_id):
        """Test creating valid range criteria."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Gain",
            criteria_type="range",
            min_value=27.5,
            max_value=31.3,
            unit="dB"
        )
        
        assert criteria.min_value == 27.5
        assert criteria.max_value == 31.3
        assert criteria.criteria_type == "range"
    
    def test_range_criteria_missing_values(self, device_id):
        """Test range criteria requires both min and max."""
        with pytest.raises(TestCriteriaError, match="range.*requires both"):
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="S21 Gain",
                criteria_type="range",
                min_value=27.5,
                max_value=None,  # Missing
                unit="dB"
            )
    
    def test_range_criteria_invalid_order(self, device_id):
        """Test range criteria min must be less than max."""
        with pytest.raises(TestCriteriaError, match="min_value.*must be less"):
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="S21 Gain",
                criteria_type="range",
                min_value=31.3,
                max_value=27.5,  # Invalid: min >= max
                unit="dB"
            )
    
    def test_min_criteria_valid(self, device_id):
        """Test creating valid min criteria."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 OoB 1",
            criteria_type="min",
            min_value=25.0,
            unit="dBc"
        )
        
        assert criteria.min_value == 25.0
        assert criteria.max_value is None
    
    def test_min_criteria_missing_value(self, device_id):
        """Test min criteria requires min_value."""
        with pytest.raises(TestCriteriaError, match="min.*requires min_value"):
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="S21 OoB 1",
                criteria_type="min",
                min_value=None,  # Missing
                unit="dBc"
            )
    
    def test_max_criteria_valid(self, device_id):
        """Test creating valid max criteria."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Flatness",
            criteria_type="max",
            max_value=2.3,
            unit="dB"
        )
        
        assert criteria.max_value == 2.3
        assert criteria.min_value is None
    
    def test_less_than_equal_criteria(self, device_id):
        """Test less_than_equal criteria."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Flatness",
            criteria_type="less_than_equal",
            max_value=2.3,
            unit="dB"
        )
        
        assert criteria.max_value == 2.3
    
    def test_greater_than_equal_criteria(self, device_id):
        """Test greater_than_equal criteria."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 OoB 1",
            criteria_type="greater_than_equal",
            min_value=25.0,
            unit="dBc"
        )
        
        assert criteria.min_value == 25.0
    
    def test_invalid_criteria_type(self, device_id):
        """Test invalid criteria type raises error."""
        with pytest.raises(TestCriteriaError, match="criteria_type must be one of"):
            TestCriteria(
                device_id=device_id,
                test_type="S-Parameters",
                test_stage="SIT",
                requirement_name="Test",
                criteria_type="invalid_type",
                min_value=1.0,
                unit="dB"
            )
    
    def test_evaluate_range_pass(self, device_id):
        """Test range evaluation passing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Gain",
            criteria_type="range",
            min_value=27.5,
            max_value=31.3,
            unit="dB"
        )
        
        assert criteria.evaluate(29.0) is True
        assert criteria.evaluate(27.5) is True  # Boundary
        assert criteria.evaluate(31.3) is True  # Boundary
    
    def test_evaluate_range_fail(self, device_id):
        """Test range evaluation failing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Gain",
            criteria_type="range",
            min_value=27.5,
            max_value=31.3,
            unit="dB"
        )
        
        assert criteria.evaluate(25.0) is False  # Below range
        assert criteria.evaluate(35.0) is False  # Above range
    
    def test_evaluate_min_pass(self, device_id):
        """Test min evaluation passing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 OoB 1",
            criteria_type="min",
            min_value=25.0,
            unit="dBc"
        )
        
        assert criteria.evaluate(30.0) is True
        assert criteria.evaluate(25.0) is True  # Boundary
    
    def test_evaluate_min_fail(self, device_id):
        """Test min evaluation failing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 OoB 1",
            criteria_type="min",
            min_value=25.0,
            unit="dBc"
        )
        
        assert criteria.evaluate(20.0) is False
    
    def test_evaluate_max_pass(self, device_id):
        """Test max evaluation passing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Flatness",
            criteria_type="max",
            max_value=2.3,
            unit="dB"
        )
        
        assert criteria.evaluate(1.5) is True
        assert criteria.evaluate(2.3) is True  # Boundary
    
    def test_evaluate_max_fail(self, device_id):
        """Test max evaluation failing."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 Flatness",
            criteria_type="max",
            max_value=2.3,
            unit="dB"
        )
        
        assert criteria.evaluate(3.0) is False
    
    def test_oob_frequency_field(self, device_id):
        """Test OOB criteria with frequency range fields."""
        criteria = TestCriteria(
            device_id=device_id,
            test_type="S-Parameters",
            test_stage="SIT",
            requirement_name="S21 OOB 1",
            criteria_type="greater_than_equal",
            min_value=25.0,
            unit="dBc",
            frequency_min=3.0,   # OOB range minimum (3 GHz)
            frequency_max=5.0   # OOB range maximum (5 GHz)
        )
        
        assert criteria.frequency_min == 3.0
        assert criteria.frequency_max == 5.0
        assert criteria.min_value == 25.0
