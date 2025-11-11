"""
Test result model for pass/fail evaluation.

This module defines the TestResult model, which stores the result of evaluating
a measurement against a single test criterion. Each TestResult records:
- Which measurement was evaluated
- Which criterion was checked
- What value was measured
- Whether it passed or failed
- Which S-parameter this result applies to (if applicable)

Multiple TestResults are generated for generic criteria (e.g., "Gain Range")
that apply to multiple S-parameters. Each result is tagged with the specific
S-parameter it represents.
"""

from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class TestResult(BaseModel):
    """
    Test result model storing pass/fail evaluation.
    
    Represents the outcome of evaluating a measurement against a single
    test criterion. Generated during compliance evaluation by test type
    implementations (e.g., SParametersTestType).
    
    Key design:
    - One TestResult per criterion per applicable S-parameter
    - For generic criteria like "Gain Range", multiple results are created
      (one for each gain S-parameter: S21, S31, S41, etc.)
    - The s_parameter field identifies which S-parameter this result is for
    - measured_value stores the actual measured metric (e.g., gain in dB, VSWR)
    
    Example:
    - Criterion: "Gain Range" (min=27.5, max=31.3 dB)
    - Measurement has S31 and S41 (from port config)
    - Results generated:
      * Result 1: s_parameter="S31", measured_value=29.5, passed=True
      * Result 2: s_parameter="S41", measured_value=32.0, passed=False
    """
    
    # Unique identifier for this result (auto-generated if not provided)
    id: UUID = Field(default_factory=uuid4)
    
    # Which measurement was evaluated
    measurement_id: UUID
    
    # Which criterion was checked
    test_criteria_id: UUID
    
    # The actual measured value (e.g., gain in dB, VSWR, flatness in dB)
    # None if measurement failed or value couldn't be calculated
    measured_value: Optional[float] = None
    
    # Whether the measurement passed the criterion
    # True if measured_value satisfies the criterion's requirements
    passed: bool
    
    # Which S-parameter this result applies to (e.g., "S21", "S31", "S11")
    # None for criteria that don't apply to specific S-parameters
    # Used to display results in compliance table with per-S-parameter breakdown
    s_parameter: Optional[str] = Field(
        default=None,
        description="S-parameter this result is for (e.g., 'S21', 'S11')"
    )
    
    # Whether this result is stale (criteria changed after result was calculated)
    # Stale results should be recalculated before being used for compliance decisions
    # Marked as stale when criteria are updated or deleted
    is_stale: bool = Field(
        default=False,
        description="True if criteria changed after this result was calculated"
    )
    
    model_config = ConfigDict(
        # Allow UUID serialization to string for JSON compatibility
        json_encoders={
            UUID: str
        }
    )
