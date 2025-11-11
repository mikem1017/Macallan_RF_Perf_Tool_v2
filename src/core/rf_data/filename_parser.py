"""
Flexible filename parser for RF measurement files.

This module provides filename parsing functionality to extract metadata from
RF measurement filenames. The parser uses a hybrid approach:
1. Primary: Regex-based parsing for structured filenames
2. Fallback: Keyword-based parsing for non-standard formats

The parser is designed to be robust and handle various filename conventions
that may be used across different measurement systems and laboratories.

Key metadata extracted:
- Date (YYYYMMDD format)
- Serial number (SNXXXX or EMXXXX)
- Part number (Lnnnnnn)
- Path type (PRI/RED, with optional HG/LG suffixes)
- Temperature (AMB/HOT/COLD, defaults to AMB if not found)
- Test type hints (from filename patterns)
- Run number (optional)

Note: Test stage is NOT parsed from filename - users select it in the GUI.
"""

import re
from datetime import date
from typing import Dict, Optional, Tuple, Union
from pathlib import Path

from ..exceptions import FileLoadError


class FilenameParser:
    """
    Parser for extracting metadata from RF measurement filenames.
    
    Uses a hybrid parsing strategy:
    - Regex patterns for structured filenames (primary method)
    - Keyword-based fallback for flexible formats
    
    This design accommodates various naming conventions while maintaining
    reliability for standard formats.
    
    Required fields (must be extracted):
    - date: Measurement date
    - serial_number: SNXXXX or EMXXXX format
    - part_number: Lnnnnnn format
    - path_type: PRI or RED
    
    Optional fields:
    - temperature: AMB, HOT, or COLD (defaults to AMB if not found)
    - test_type: Inferred from filename patterns
    - run_number: Run1, Run2, etc.
    """
    
    # Regex patterns for common filename formats
    # These patterns are designed to match common naming conventions
    
    # Date pattern: 8 consecutive digits (YYYYMMDD)
    # Example: "20250930" in "20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p"
    DATE_PATTERN = r"(\d{8})"  # YYYYMMDD
    
    # Serial number pattern: SN followed by 4 digits, or EM followed by 4 digits
    # Also handles EM-XXXX format (with hyphen)
    # Examples: "SN0001", "EM1234", "EM-1234"
    SERIAL_PATTERN = r"([SE]N\d{4}|EM-?\d{4})"  # SNXXXX or EMXXXX or EM-XXXX
    
    # Part number pattern: L followed by exactly 6 digits
    # Example: "L109908" in "20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p"
    PART_NUMBER_PATTERN = r"(L\d{6})"  # Lnnnnnn
    
    # Path type pattern: PRI or RED (case insensitive)
    # Must be preceded by _/./- and followed by _/./$ or end of string
    # This prevents false matches on substrings (e.g., "PRIMARY" shouldn't match "PRI")
    PATH_TYPE_PATTERN = r"(?i)[_.-](PRI|RED)(?:[_.]|$)"  # Case insensitive, preceded by _/./-, followed by _/./$ or end
    
    # Temperature pattern: Whole words only (word boundaries)
    # Prevents partial matches
    TEMP_PATTERN = r"\b(AMB|HOT|COLD)\b"
    
    def parse(self, filepath: Union[str, Path]) -> Dict[str, any]:
        """
        Parse filename to extract metadata.
        
        This is the main entry point for filename parsing. It:
        1. Extracts the filename from the path
        2. Attempts regex-based parsing (primary method)
        3. Falls back to keyword-based parsing for missing fields
        4. Sets default temperature to AMB if not found
        5. Validates that all required fields are present
        
        Args:
            filepath: Path to the file (can be string or Path object)
            
        Returns:
            Dictionary with parsed metadata containing:
            - date: date object (required)
            - serial_number: str (required, SNXXXX or EMXXXX format)
            - part_number: str (required, Lnnnnnn format)
            - path_type: str (required, PRI or RED)
            - temperature: str (defaults to "AMB" if not found)
            - test_type: str (optional, inferred from filename)
            - run_number: str (optional, e.g., "Run1")
            - filename: str (original filename)
            - file_path: str (full path)
            
        Raises:
            FileLoadError: If required fields cannot be extracted
                (date, serial_number, part_number, or path_type)
        """
        # Extract filename from path
        if isinstance(filepath, Path):
            filename = filepath.name
            full_path = str(filepath)
        else:
            filename = Path(filepath).name
            full_path = filepath
        
        # Try regex-based parsing first (more reliable for structured filenames)
        metadata = self._regex_parse(filename)
        
        # Fallback to keyword-based parsing if regex missed something
        # This handles non-standard filename formats
        if not metadata.get("date"):
            metadata.update(self._keyword_parse(filename))
        
        # Temperature is optional - default to AMB if not found
        # This allows files without explicit temperature designation
        if "temperature" not in metadata:
            metadata["temperature"] = "AMB"
        
        # Validate required fields - these MUST be present
        required = ["date", "serial_number", "part_number", "path_type"]
        missing = [field for field in required if not metadata.get(field)]
        
        if missing:
            raise FileLoadError(
                f"Could not extract required metadata from filename: {filename}. "
                f"Missing: {', '.join(missing)}"
            )
        
        # Add filename and full path to metadata for reference
        metadata["filename"] = filename
        metadata["file_path"] = full_path
        
        return metadata
    
    def _regex_parse(self, filename: str) -> Dict[str, any]:
        """
        Parse using regex patterns (primary method).
        
        This method attempts to extract metadata using structured regex patterns.
        It's designed to handle standard filename formats with predictable structure.
        
        Args:
            filename: The filename to parse (without path)
            
        Returns:
            Dictionary with extracted metadata (may be partial if some fields not found)
        """
        metadata = {}
        
        # Date extraction: Look for 8 consecutive digits (YYYYMMDD)
        date_match = re.search(self.DATE_PATTERN, filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                # Parse YYYYMMDD format
                metadata["date"] = date(
                    int(date_str[0:4]),  # Year
                    int(date_str[4:6]),  # Month
                    int(date_str[6:8])   # Day
                )
            except ValueError:
                # Invalid date (e.g., invalid month/day) - will fall back to keyword parsing
                pass
        
        # Serial number extraction: SNXXXX or EMXXXX format
        # Also handles EM-XXXX format (with hyphen) and normalizes to EMXXXX
        serial_match = re.search(r"([SE]N\d{4}|EM-?\d{4})", filename, re.IGNORECASE)
        if serial_match:
            serial = serial_match.group(1).upper()
            # Normalize EM-XXXX to EMXXXX (remove hyphen)
            serial = serial.replace("EM-", "EM")
            # Validate format: SN or EM followed by exactly 4 digits
            # This ensures we don't accept invalid formats like "SN123" or "SN12345"
            if re.match(r"^[SE]N\d{4}$|^EM\d{4}$", serial, re.IGNORECASE):
                metadata["serial_number"] = serial
        
        # Part number extraction: L followed by exactly 6 digits
        part_match = re.search(self.PART_NUMBER_PATTERN, filename)
        if part_match:
            metadata["part_number"] = part_match.group(1)
        
        # Path type extraction: PRI or RED (case insensitive)
        # Pattern already has (?i) flag for case insensitivity
        # Must be preceded by _/./- to avoid false matches
        path_match = re.search(self.PATH_TYPE_PATTERN, filename)
        if path_match:
            metadata["path_type"] = path_match.group(1).upper()  # Normalize to uppercase
        
        # Temperature extraction: AMB, HOT, or COLD (whole words only)
        temp_match = re.search(self.TEMP_PATTERN, filename)
        if temp_match:
            metadata["temperature"] = temp_match.group(1)
        
        # Test stage is NOT parsed from filename - user selects it in UI
        # This prevents confusion and gives user control over test stage assignment
        
        # Test type inference: Look for common patterns in filename
        # These are hints, not definitive - user can override in GUI
        if "S-Par" in filename or ".s" in filename.lower():
            metadata["test_type"] = "S-Parameters"
        elif "NF" in filename or "Noise" in filename:
            metadata["test_type"] = "Noise Figure"
        
        # Run number extraction (optional): Run1, Run2, etc.
        # Looks for "Run" followed by digits, with word boundary or separator
        # Example: "_Run1_" or ".Run2." or "-Run3-"
        run_match = re.search(r"(?i)[_.-]Run(\d+)(?:[_.]|$)", filename)
        if run_match:
            metadata["run_number"] = f"Run{run_match.group(1)}"
        
        return metadata
    
    def _keyword_parse(self, filename: str) -> Dict[str, any]:
        """
        Fallback keyword-based parsing when regex fails.
        
        This method uses a more flexible approach for non-standard filename formats.
        It searches for keywords and patterns without strict structural requirements.
        Used as a fallback when regex parsing doesn't extract all required fields.
        
        Args:
            filename: The filename to parse (without path)
            
        Returns:
            Dictionary with extracted metadata (may be partial)
        """
        metadata = {}
        filename_upper = filename.upper()  # Convert to uppercase for case-insensitive matching
        
        # Date extraction: Try to find any 8-digit sequence that could be a date
        date_match = re.search(r"(\d{8})", filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                # Validate reasonable date ranges (1900-2100, valid month/day)
                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    metadata["date"] = date(year, month, day)
            except (ValueError, IndexError):
                # Invalid date - skip
                pass
        
        # Serial number extraction: Look for SN or EM followed by digits
        # More flexible than regex - finds pattern anywhere in filename
        for prefix in ["SN", "EM"]:
            pattern = rf"{prefix}(\d{{4}})"  # e.g., "SN" + 4 digits
            match = re.search(pattern, filename_upper)
            if match:
                metadata["serial_number"] = f"{prefix}{match.group(1)}"
                break  # Found one, no need to continue
        
        # Part number extraction: Look for L followed by 6 digits
        # More flexible pattern matching
        part_match = re.search(r"L(\d{6})", filename_upper)
        if part_match:
            metadata["part_number"] = f"L{part_match.group(1)}"
        
        # Path type extraction: Look for PRI or RED as whole words
        # Word boundaries prevent false matches (e.g., "PRIMARY" won't match "PRI")
        if re.search(r"\bPRI\b", filename_upper) and "path_type" not in metadata:
            metadata["path_type"] = "PRI"
        elif re.search(r"\bRED\b", filename_upper) and "path_type" not in metadata:
            metadata["path_type"] = "RED"
        
        # Temperature extraction: Look for temperature keywords
        for temp in ["AMB", "HOT", "COLD"]:
            if temp in filename_upper:
                metadata["temperature"] = temp
                break  # Found one, no need to continue
        
        return metadata
