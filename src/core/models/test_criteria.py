"""
Test criteria model with structured format.

This module defines the TestCriteria model, which represents a single test
requirement that a device must meet. Criteria are organized by:
- Device: Which device this requirement applies to
- Test Type: Which test (e.g., "S-Parameters") this is for
- Test Stage: Which stage of testing (e.g., "SIT", "Board-Bring-Up")
- Requirement Name: Human-readable name (e.g., "Gain Range", "VSWR Max")

Each criterion can have different evaluation types:
- range: Value must be between min_value and max_value (inclusive)
- min: Value must be >= min_value
- max: Value must be <= max_value
- less_than_equal: Value must be <= max_value
- greater_than_equal: Value must be >= min_value

For OOB (Out-of-Band) requirements, the frequency field specifies the
frequency at which rejection is measured.
"""

from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from ..exceptions import TestCriteriaError


class TestCriteria(BaseModel):
    """
    Test criteria model with structured validation.
    
    Represents a single requirement that a measurement must pass. Each device
    can have multiple criteria, organized by test type and test stage.
    
    Key design decisions:
    - Generic requirement names (e.g., "Gain Range") that apply to multiple
      S-parameters. The test type implementation determines which S-parameters
      each criterion applies to.
    - Structured criteria_type field ensures type safety and prevents invalid
      configurations (e.g., range criteria must have both min and max).
    - Optional frequency range fields (frequency_min, frequency_max) for OOB requirements.
      OOB rejection is measured across a frequency range, with worst-case (minimum)
      rejection used for compliance evaluation.
      
      IMPORTANT: OOB criteria compare REJECTION (in dBc) >= requirement, NOT gain.
      Rejection = min_in_band_gain - worst_case_oob_gain.
      Example: requirement >= 60 dBc means rejection must be at least 60 dBc.
    
    Validation ensures:
    - criteria_type is one of allowed values
    - min_value/max_value are appropriate for the criteria_type
    - Range criteria have min < max
    """
    
    # Unique identifier for this criterion (auto-generated if not provided)
    id: UUID = Field(default_factory=uuid4)
    
    # Which device this criterion applies to
    device_id: UUID
    
    # Which test type (e.g., "S-Parameters", "Power/Linearity")
    test_type: str
    
    # Which test stage (e.g., "Board-Bring-Up", "SIT", "Test-Campaign")
    # Different stages can have different requirements for the same test type
    test_stage: str
    
    # Human-readable requirement name
    # Examples: "Gain Range", "Flatness", "VSWR Max", "OOB 1"
    # Generic names allow one criterion to apply to multiple S-parameters
    requirement_name: str
    
    # Type of criteria evaluation
    # Must be one of: "range", "min", "max", "less_than_equal", "greater_than_equal"
    # This determines how min_value and max_value are used
    criteria_type: str = Field(
        description="Type of criteria: range, min, max, less_than_equal, greater_than_equal"
    )
    
    # Minimum allowed value (required for range, min, greater_than_equal)
    # Optional for max and less_than_equal criteria
    min_value: Optional[float] = None
    
    # Maximum allowed value (required for range, max, less_than_equal)
    # Optional for min and greater_than_equal criteria
    max_value: Optional[float] = None
    
    # Unit of measurement (e.g., "dB", "dBc", "")
    # Used for display purposes in the GUI
    unit: str
    
    # Frequency range in GHz (for OOB requirements only)
    # Specifies the out-of-band frequency range where rejection is measured
    # frequency_min and frequency_max define the range bounds
    # Only used when criteria_type involves frequency-dependent measurement (OOB)
    # For OOB criteria, both frequency_min and frequency_max must be provided
    frequency_min: Optional[float] = Field(
        default=None,
        description="Minimum frequency in GHz (for OOB requirements only)"
    )
    frequency_max: Optional[float] = Field(
        default=None,
        description="Maximum frequency in GHz (for OOB requirements only)"
    )
    
    @field_validator("criteria_type")
    @classmethod
    def validate_criteria_type(cls, v: str) -> str:
        """
        Validate criteria type is one of the allowed values.
        
        Prevents invalid criteria types from being stored and ensures
        type safety throughout the system.
        
        Args:
            v: Criteria type string to validate
            
        Returns:
            Validated criteria type (unchanged if valid)
            
        Raises:
            TestCriteriaError: If criteria_type is not in allowed set
        """
        allowed = {"range", "min", "max", "less_than_equal", "greater_than_equal"}
        if v not in allowed:
            raise TestCriteriaError(
                f"criteria_type must be one of {allowed}, got: {v}"
            )
        return v
    
    @model_validator(mode="after")
    def validate_criteria_values(self):
        """
        Validate that criteria values are appropriate for the criteria type.
        
        Ensures that:
        - Range criteria have both min and max, and min < max
        - Min/greater_than_equal criteria have min_value but not max_value
        - Max/less_than_equal criteria have max_value but not min_value
        
        This validation prevents configuration errors like:
        - Range criteria missing one bound
        - Min criteria with max_value set
        - Max criteria with min_value set
        
        Returns:
            self (required by Pydantic)
            
        Raises:
            TestCriteriaError: If criteria values don't match criteria_type
        """
        # Range criteria require both min and max, and min < max
        if self.criteria_type == "range":
            if self.min_value is None or self.max_value is None:
                raise TestCriteriaError(
                    "range criteria_type requires both min_value and max_value"
                )
            if self.min_value >= self.max_value:
                raise TestCriteriaError(
                    f"min_value ({self.min_value}) must be less than max_value ({self.max_value})"
                )
        
        # Min and greater_than_equal require min_value, should not have max_value
        elif self.criteria_type in ("min", "greater_than_equal"):
            if self.min_value is None:
                raise TestCriteriaError(
                    f"{self.criteria_type} criteria_type requires min_value"
                )
            if self.max_value is not None:
                raise TestCriteriaError(
                    f"{self.criteria_type} criteria_type should not have max_value"
                )
        
        # Max and less_than_equal require max_value, should not have min_value
        elif self.criteria_type in ("max", "less_than_equal"):
            if self.max_value is None:
                raise TestCriteriaError(
                    f"{self.criteria_type} criteria_type requires max_value"
                )
            if self.min_value is not None:
                raise TestCriteriaError(
                    f"{self.criteria_type} criteria_type should not have min_value"
                )
        
        # Validate OOB frequency range if provided
        if self.frequency_min is not None or self.frequency_max is not None:
            # For OOB criteria, both min and max must be provided
            if self.frequency_min is None or self.frequency_max is None:
                raise TestCriteriaError(
                    "OOB criteria requires both frequency_min and frequency_max"
                )
            # Frequency range must be valid (min < max)
            if self.frequency_min >= self.frequency_max:
                raise TestCriteriaError(
                    f"frequency_min ({self.frequency_min}) must be less than "
                    f"frequency_max ({self.frequency_max})"
                )
        
        return self
    
    def evaluate(self, value: float) -> bool:
        """
        Evaluate if a measured value passes this criteria.
        
        This is the core method that performs pass/fail evaluation. It takes
        a measured value and checks it against the criterion's requirements
        based on the criteria_type.
        
        Examples:
        - criteria_type="range", min=27.5, max=31.3: Returns True if 27.5 <= value <= 31.3
        - criteria_type="max", max=2.0: Returns True if value <= 2.0
        - criteria_type="min", min=25.0: Returns True if value >= 25.0
        
        Args:
            value: The measured value to evaluate (e.g., gain in dB, VSWR, etc.)
            
        Returns:
            True if value passes the criterion, False otherwise
            
        Raises:
            TestCriteriaError: If criteria_type is unknown (shouldn't happen after validation)
        """
        # Range: value must be between min and max (inclusive)
        if self.criteria_type == "range":
            return self.min_value <= value <= self.max_value
        
        # Min and greater_than_equal: value must be >= min_value
        elif self.criteria_type == "min" or self.criteria_type == "greater_than_equal":
            return value >= self.min_value
        
        # Max and less_than_equal: value must be <= max_value
        elif self.criteria_type == "max" or self.criteria_type == "less_than_equal":
            return value <= self.max_value
        
        else:
            # This should never happen if validation worked, but safety check
            raise TestCriteriaError(f"Unknown criteria_type: {self.criteria_type}")
    
    model_config = ConfigDict(
        # Allow UUID serialization to string for JSON compatibility
        json_encoders={
            UUID: str
        }
    )
