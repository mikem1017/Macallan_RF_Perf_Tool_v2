"""
Measurement data model.

This module defines the Measurement model, which represents a single loaded
RF measurement file. Each measurement contains:
- Identification (serial number, device, test type/stage)
- Environmental conditions (temperature, path type)
- File information (path, date)
- RF data (Touchstone network object)

Measurements are created when users load Touchstone files in the Test Setup
screen. The filename is parsed to extract metadata, and the file contents
are loaded using scikit-rf.
"""

from datetime import date
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Type stub for scikit-rf Network - will import at runtime
# This allows type checking without requiring scikit-rf at import time
try:
    from skrf import Network
except ImportError:
    Network = Any


class Measurement(BaseModel):
    """
    Measurement data model for loaded RF files.
    
    Represents a single measurement instance - one Touchstone file loaded
    for a specific device, serial number, temperature, and path type.
    
    Key fields:
    - touchstone_data: The actual RF data (scikit-rf Network object)
                      Stored as bytes (pickled) in database, deserialized when needed
    - metadata: Additional parsed information from filename (part number, run number, etc.)
    
    Temperature and path_type are validated to ensure only allowed values:
    - Temperature: AMB (ambient), HOT, COLD
    - Path type: PRI (primary), RED (redundant), or with _HG/_LG suffixes for multi-gain
    
    The measurement_date is extracted from the filename during parsing.
    """
    
    # Unique identifier for this measurement (auto-generated if not provided)
    id: UUID = Field(default_factory=uuid4)
    
    # Which device this measurement is for
    device_id: UUID
    
    # Serial number in format SNXXXX or EMXXXX
    # Extracted from filename during parsing
    serial_number: str  # SNXXXX or EMXXXX
    
    # Test type (e.g., "S-Parameters", "Power/Linearity")
    # Determines which test type implementation processes this measurement
    test_type: str
    
    # Test stage (e.g., "Board-Bring-Up", "SIT", "Test-Campaign")
    # User selects this in the Test Setup GUI (not parsed from filename)
    test_stage: str
    
    # Temperature condition: AMB (ambient), HOT, or COLD
    # Defaults to AMB if not found in filename
    temperature: str  # 'AMB', 'HOT', 'COLD'
    
    # Path type: PRI (primary) or RED (redundant)
    # For multi-gain mode: PRI_HG, PRI_LG, RED_HG, RED_LG
    # Extracted from filename during parsing
    path_type: str  # 'PRI', 'RED', or 'PRI_HG', 'PRI_LG', 'RED_HG', 'RED_LG' for multi-gain
    
    # Original file path where this measurement was loaded from
    file_path: str
    
    # Date when measurement was taken (extracted from filename)
    measurement_date: date
    
    # The actual RF data (scikit-rf Network object)
    # When stored in database, this is pickled to bytes
    # When loaded from database, it's deserialized back to Network object
    # Field allows Any type because Network may not be importable at module load time
    touchstone_data: Any = Field(description="scikit-rf Network object (stored as blob in DB)")
    
    # Additional metadata extracted from filename
    # Examples: part_number, run_number, test_type hints
    # This is a flexible dictionary for extensibility
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: str) -> str:
        """
        Validate temperature is one of the allowed values.
        
        Only three temperature conditions are supported:
        - AMB: Ambient (room temperature)
        - HOT: High temperature testing
        - COLD: Low temperature testing
        
        Args:
            v: Temperature string to validate
            
        Returns:
            Validated temperature (unchanged if valid)
            
        Raises:
            ValueError: If temperature is not in allowed set
        """
        allowed = {"AMB", "HOT", "COLD"}
        if v not in allowed:
            raise ValueError(f"temperature must be one of {allowed}, got: {v}")
        return v
    
    @field_validator("path_type")
    @classmethod
    def validate_path_type(cls, v: str) -> str:
        """
        Validate path type is one of the allowed values.
        
        Path types indicate which signal path this measurement represents:
        - PRI: Primary path
        - RED: Redundant path
        - PRI_HG, PRI_LG: Primary path high-gain/low-gain (multi-gain mode)
        - RED_HG, RED_LG: Redundant path high-gain/low-gain (multi-gain mode)
        
        Args:
            v: Path type string to validate
            
        Returns:
            Validated path type (unchanged if valid)
            
        Raises:
            ValueError: If path_type is not in allowed set
        """
        allowed = {"PRI", "RED", "PRI_HG", "PRI_LG", "RED_HG", "RED_LG"}
        if v not in allowed:
            raise ValueError(f"path_type must be one of {allowed}, got: {v}")
        return v
    
    model_config = ConfigDict(
        # Allow arbitrary types (Network object) for touchstone_data
        arbitrary_types_allowed=True,
        # Custom serializers for non-JSON-serializable types
        json_encoders={
            UUID: str,
            date: str
        }
    )
