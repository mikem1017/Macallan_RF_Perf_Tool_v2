"""Unit tests for TestResult model."""

import pytest
from uuid import uuid4

from src.core.models.test_result import TestResult


class TestTestResultModel:
    """Test TestResult model."""
    
    def test_create_valid_result_pass(self):
        """Test creating a valid pass result."""
        result = TestResult(
            measurement_id=uuid4(),
            test_criteria_id=uuid4(),
            measured_value=29.5,
            passed=True
        )
        
        assert result.measured_value == 29.5
        assert result.passed is True
    
    def test_create_valid_result_fail(self):
        """Test creating a valid fail result."""
        result = TestResult(
            measurement_id=uuid4(),
            test_criteria_id=uuid4(),
            measured_value=25.0,
            passed=False
        )
        
        assert result.measured_value == 25.0
        assert result.passed is False
    
    def test_create_result_no_value(self):
        """Test creating result without measured value."""
        result = TestResult(
            measurement_id=uuid4(),
            test_criteria_id=uuid4(),
            measured_value=None,
            passed=False
        )
        
        assert result.measured_value is None
        assert result.passed is False













