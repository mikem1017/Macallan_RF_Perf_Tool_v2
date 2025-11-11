"""
Test stage constants and utilities.

This module defines the standard test stages used throughout the application.
Test stages represent different phases of device testing, each with potentially
different requirements.

Standard test stages:
- Board-Bring-Up: Initial testing during board development
- SIT (Select-In-Test): Testing during device selection/qualification
- Test-Campaign: Full production testing campaign

Different test stages can have different requirements for the same test type.
For example, SIT might have stricter gain requirements than Board-Bring-Up.

The module provides:
- List of valid test stages (for validation)
- Display name mapping (for UI presentation)
- Validation functions
- Utility functions for stage handling

Note: Test stages are NOT parsed from filenames - users select them in the GUI.
This gives explicit control over which stage a measurement belongs to.
"""

# Standard test stages - if adding new stages, ensure all places that use test stages are updated
# These represent the three standard phases of device testing
TEST_STAGES = [
    "Board-Bring-Up",  # Initial board development testing
    "SIT",             # Select-In-Test (device qualification)
    "Test-Campaign"    # Full production testing
]

# Map of normalized names (for UI display)
# Provides human-readable display names for each test stage
# Used in dropdowns, labels, and reports
TEST_STAGE_DISPLAY_NAMES = {
    "Board-Bring-Up": "Board Bring-Up",  # Hyphen removed for display
    "SIT": "Select-In-Test",            # Full expansion of acronym
    "Test-Campaign": "Test Campaign"     # Hyphen removed for display
}

def validate_test_stage(stage: str) -> bool:
    """
    Validate that a test stage is valid.
    
    Checks if the provided test stage string is one of the standard
    test stages defined in TEST_STAGES.
    
    Args:
        stage: Test stage string to validate
        
    Returns:
        True if stage is valid, False otherwise
        
    Example:
        validate_test_stage("SIT") → True
        validate_test_stage("Invalid") → False
    """
    return stage in TEST_STAGES

def get_test_stage_display_name(stage: str) -> str:
    """
    Get display name for a test stage.
    
    Returns the human-readable display name for a test stage. If no
    display name is defined, returns the stage name unchanged.
    
    Useful for UI display where you want full names rather than codes.
    
    Args:
        stage: Test stage identifier (e.g., "SIT", "Board-Bring-Up")
        
    Returns:
        Display name (e.g., "Select-In-Test", "Board Bring-Up")
        Falls back to original stage name if no display name defined
        
    Example:
        get_test_stage_display_name("SIT") → "Select-In-Test"
        get_test_stage_display_name("Board-Bring-Up") → "Board Bring-Up"
        get_test_stage_display_name("Unknown") → "Unknown"
    """
    return TEST_STAGE_DISPLAY_NAMES.get(stage, stage)
