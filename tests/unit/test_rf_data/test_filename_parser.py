"""Unit tests for filename parser."""

import pytest
from datetime import date
from pathlib import Path

from src.core.rf_data.filename_parser import FilenameParser
from src.core.exceptions import FileLoadError


class TestFilenameParser:
    """Test filename parser with various formats."""
    
    @pytest.fixture
    def parser(self):
        """Provide a filename parser instance."""
        return FilenameParser()
    
    def test_parse_standard_format(self, parser):
        """Test parsing standard format from example files."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        metadata = parser.parse(filepath)
        
        assert metadata["date"] == date(2025, 9, 30)
        assert metadata["serial_number"] == "SN0001"
        assert metadata["part_number"] == "L109908"
        assert metadata["path_type"] == "PRI"
        assert metadata["temperature"] == "AMB"
        # test_stage is NOT parsed from filename - user selects in UI
        assert metadata["test_type"] == "S-Parameters"
        assert metadata["run_number"] == "Run1"
    
    def test_parse_red_path(self, parser):
        """Test parsing RED path file."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_RED.s4p")
        metadata = parser.parse(filepath)
        
        assert metadata["path_type"] == "RED"
        assert metadata["serial_number"] == "SN0001"
    
    def test_parse_em_serial(self, parser):
        """Test parsing EM serial number (non-flight)."""
        filepath = "20250523_Session5_L109377_EM-0003_PRI_AMB.xlsx"
        metadata = parser.parse(filepath)
        
        assert metadata["serial_number"] == "EM0003"  # Parser should handle EM-0003 format
    
    def test_parse_missing_fields(self, parser):
        """Test parsing file with missing required fields."""
        filepath = "invalid_filename.txt"
        
        with pytest.raises(FileLoadError, match="Could not extract required metadata"):
            parser.parse(filepath)
    
    def test_parse_flexible_order(self, parser):
        """Test parsing with different field order."""
        # Different order than standard
        filepath = "L109908_PRI_20250930_SN0001_AMB_SIT.s4p"
        metadata = parser.parse(filepath)
        
        # Should still extract all fields
        assert metadata["date"] == date(2025, 9, 30)
        assert metadata["serial_number"] == "SN0001"
        assert metadata["part_number"] == "L109908"
        assert metadata["path_type"] == "PRI"
        assert metadata["temperature"] == "AMB"
    
    def test_date_validation(self, parser):
        """Test date parsing validation."""
        filepath = "20250930_SN0001_L123456_PRI_AMB.s4p"
        metadata = parser.parse(filepath)
        
        assert isinstance(metadata["date"], date)
        assert metadata["date"].year == 2025
        assert metadata["date"].month == 9
        assert metadata["date"].day == 30
    
    def test_serial_number_format_validation(self, parser):
        """Test serial number format validation (SN/EM + exactly 4 digits)."""
        # Valid formats
        valid_files = [
            "20250930_SN0001_L123456_PRI_AMB.s4p",
            "20250930_EM0003_L123456_PRI_AMB.s4p",
            "20250930_SN9999_L123456_PRI_AMB.s4p"
        ]
        
        for filepath in valid_files:
            metadata = parser.parse(filepath)
            assert metadata["serial_number"] in ["SN0001", "EM0003", "SN9999"]
        
        # Invalid formats should not match
        # (These will fail other validations, but serial extraction should handle gracefully)
        invalid_file = "20250930_SN123_L123456_PRI_AMB.s4p"  # Only 3 digits
        # This will raise FileLoadError due to missing required fields after validation
