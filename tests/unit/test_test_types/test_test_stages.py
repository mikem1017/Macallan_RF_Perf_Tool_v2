"""Unit tests for test stages."""

import pytest

from src.core.test_stages import (
    TEST_STAGES,
    validate_test_stage,
    get_test_stage_display_name
)


class TestTestStages:
    """Test test stage constants and utilities."""
    
    def test_test_stages_defined(self):
        """Test that standard test stages are defined."""
        assert "Board-Bring-Up" in TEST_STAGES
        assert "SIT" in TEST_STAGES
        assert "Test-Campaign" in TEST_STAGES
        assert len(TEST_STAGES) == 3
    
    def test_validate_test_stage_valid(self):
        """Test validation of valid test stages."""
        assert validate_test_stage("Board-Bring-Up") is True
        assert validate_test_stage("SIT") is True
        assert validate_test_stage("Test-Campaign") is True
    
    def test_validate_test_stage_invalid(self):
        """Test validation of invalid test stages."""
        assert validate_test_stage("Invalid") is False
        assert validate_test_stage("") is False
    
    def test_get_display_name(self):
        """Test getting display names."""
        assert get_test_stage_display_name("Board-Bring-Up") == "Board Bring-Up"
        assert get_test_stage_display_name("SIT") == "Select-In-Test"
        assert get_test_stage_display_name("Test-Campaign") == "Test Campaign"
        
        # Invalid stage returns as-is
        assert get_test_stage_display_name("Invalid") == "Invalid"










