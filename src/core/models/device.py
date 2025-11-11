"""
Device model with validation.

This module defines the Device model, which represents a device configuration
in the RF performance testing system. Devices define the physical characteristics
of the unit under test, including frequency ranges, port configurations, and
which test types are performed.

Key features:
- Part number validation (Lnnnnnn format)
- Frequency range validation (operational and wideband)
- Port configuration (input/output ports for S-parameter identification)
- Support for multi-gain mode devices
"""

import re
from typing import List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from ..exceptions import InvalidPartNumberError


class Device(BaseModel):
    """
    Device configuration model.
    
    Represents a device type that can be tested. Each device has:
    - Identification (name, part number, description)
    - Frequency specifications (operational and wideband ranges)
    - Port configuration (which ports are inputs vs outputs)
    - Test configuration (which test types are performed, multi-gain mode)
    
    Port configuration is critical for S-parameter evaluation:
    - Input ports: ports where signals enter the device
    - Output ports: ports where signals exit the device
    - Gain S-parameters: transmission from input to output (e.g., S31 = port 1 input → port 3 output)
    - VSWR S-parameters: reflection at each port (e.g., S11 = reflection at port 1)
    
    Validation ensures:
    - Part number follows strict format (Lnnnnnn)
    - Frequency ranges are valid (min < max, positive values)
    - Port configuration is valid (no overlap, non-empty lists, positive integers)
    """
    
    # Unique identifier for this device (auto-generated if not provided)
    id: UUID = Field(default_factory=uuid4)
    
    # Human-readable device name (e.g., "Macallan RF Amplifier")
    name: str
    
    # Optional description of the device
    description: str = ""
    
    # Part number in format Lnnnnnn (L followed by exactly 6 digits)
    # This format is enforced by the validate_part_number method
    part_number: str
    
    # Operational frequency range (in GHz)
    # This is the primary frequency band where the device operates
    # Used for gain, flatness, and other primary measurements
    operational_freq_min: float = Field(gt=0, description="Minimum operational frequency in GHz")
    operational_freq_max: float = Field(gt=0, description="Maximum operational frequency in GHz")
    
    # Wideband frequency range (in GHz)
    # This is a wider range used for plotting and extended analysis
    # Typically encompasses operational range plus extended spectrum
    wideband_freq_min: float = Field(gt=0, description="Minimum wideband frequency in GHz")
    wideband_freq_max: float = Field(gt=0, description="Maximum wideband frequency in GHz")
    
    # Multi-gain mode flag
    # When True, device has separate high-gain (HG) and low-gain (LG) paths
    # This affects file loading (4 files per temperature instead of 2)
    multi_gain_mode: bool = False
    
    # List of test types that this device undergoes
    # Example: ["S-Parameters", "Power/Linearity", "Noise Figure"]
    # Each test type has its own tab in the Device Maintenance GUI
    tests_performed: List[str] = Field(default_factory=list)
    
    # Port configuration: lists of port numbers (1-indexed)
    # These define which S-parameters represent gain (input→output) vs VSWR (reflection)
    # Example: input_ports=[1, 2], output_ports=[3, 4] means:
    #   - Gain S-parameters: S31, S32, S41, S42
    #   - VSWR S-parameters: S11, S22, S33, S44
    input_ports: List[int] = Field(description="List of input port numbers (1-indexed)")
    output_ports: List[int] = Field(description="List of output port numbers (1-indexed)")
    
    @field_validator("part_number")
    @classmethod
    def validate_part_number(cls, v: str) -> str:
        """
        Validate part number format: L followed by 6 digits.
        
        Part numbers must follow strict format: Lnnnnnn
        Examples: L123456, L000001, L999999
        
        This validation ensures consistency across the system and prevents
        invalid part numbers from being stored.
        
        Args:
            v: Part number string to validate
            
        Returns:
            Validated part number (unchanged if valid)
            
        Raises:
            InvalidPartNumberError: If part number doesn't match format
        """
        # Regex pattern: L at start, followed by exactly 6 digits, end of string
        pattern = r"^L\d{6}$"
        if not re.match(pattern, v):
            raise InvalidPartNumberError(
                f"Part number must be in format Lnnnnnn (L followed by 6 digits), got: {v}"
            )
        return v
    
    @model_validator(mode="after")
    def validate_frequencies(self):
        """
        Validate that min < max for both frequency ranges.
        
        This validator runs after all fields are set, allowing us to compare
        min and max values. Both operational and wideband ranges must have
        valid ordering (min < max).
        
        Returns:
            self (required by Pydantic)
            
        Raises:
            ValueError: If frequency ranges are invalid
        """
        # Check operational frequency range
        if self.operational_freq_min >= self.operational_freq_max:
            raise ValueError(
                f"operational_freq_min ({self.operational_freq_min}) must be less than "
                f"operational_freq_max ({self.operational_freq_max})"
            )
        
        # Check wideband frequency range
        if self.wideband_freq_min >= self.wideband_freq_max:
            raise ValueError(
                f"wideband_freq_min ({self.wideband_freq_min}) must be less than "
                f"wideband_freq_max ({self.wideband_freq_max})"
            )
        
        return self
    
    @model_validator(mode="after")
    def validate_port_configuration(self):
        """
        Validate port configuration for consistency and correctness.
        
        Ensures:
        1. No port appears in both input and output lists (ports are exclusive)
        2. Port numbers are positive integers (1-indexed, not 0-indexed)
        3. At least one input port and one output port are specified
        
        Note: We don't validate that all ports in the device are assigned here.
        That validation happens during measurement evaluation when we know the
        actual port count from the Touchstone file.
        
        Returns:
            self (required by Pydantic)
            
        Raises:
            ValueError: If port configuration is invalid
        """
        # Check for overlap between input and output ports
        # A port cannot be both an input and an output
        overlap = set(self.input_ports) & set(self.output_ports)
        if overlap:
            raise ValueError(
                f"Ports cannot be both input and output: {overlap}"
            )
        
        # Check that all ports are assigned (for now, require explicit assignment)
        # This assumes we know the total port count from elsewhere (e.g., from measurement file)
        # We'll validate this when needed during evaluation
        
        # Check that ports are positive integers (1-indexed)
        # Port numbering starts at 1 (not 0) to match RF engineering conventions
        if any(p < 1 for p in self.input_ports + self.output_ports):
            raise ValueError("Port numbers must be >= 1 (1-indexed)")
        
        # Check that lists are not empty
        # We need at least one input and one output to define gain paths
        if not self.input_ports:
            raise ValueError("At least one input port must be specified")
        
        if not self.output_ports:
            raise ValueError("At least one output port must be specified")
        
        return self
    
    def get_all_ports(self) -> List[int]:
        """
        Get list of all ports (inputs + outputs), sorted and deduplicated.
        
        Useful for determining which ports need VSWR evaluation.
        
        Returns:
            Sorted list of all unique port numbers
        """
        return sorted(set(self.input_ports + self.output_ports))
    
    def get_gain_s_parameters(self, n_ports: int) -> List[str]:
        """
        Get list of gain S-parameters (input → output) based on port configuration.
        
        Gain S-parameters represent transmission from input ports to output ports.
        For each input port and each output port, we generate an S-parameter.
        
        Example: input_ports=[1, 2], output_ports=[3, 4]
        Returns: ["S31", "S32", "S41", "S42"]
        
        Note: S-parameter naming is S{output_port}{input_port}
        - S31 means signal goes from port 1 (input) to port 3 (output)
        - This matches standard RF S-parameter notation
        
        Args:
            n_ports: Total number of ports in the device (from Touchstone file)
                     Used to filter out invalid port combinations
            
        Returns:
            List of S-parameter strings, sorted (e.g., ["S21", "S31", "S41"])
        """
        gain_params = []
        
        # Generate all input→output combinations
        for input_port in self.input_ports:
            for output_port in self.output_ports:
                # Only include if both ports are within device's port count
                # This prevents errors when port config has ports > n_ports
                if input_port <= n_ports and output_port <= n_ports:
                    # Format: S{output}{input} (standard RF notation)
                    gain_params.append(f"S{output_port}{input_port}")
        
        # Return sorted for consistency
        return sorted(gain_params)
    
    def get_vswr_s_parameters(self, n_ports: int) -> List[str]:
        """
        Get list of VSWR S-parameters (reflection coefficients for all ports).
        
        VSWR (Voltage Standing Wave Ratio) is measured at each port using
        reflection coefficients. For a port N, the S-parameter is SNN.
        
        Example: input_ports=[1, 2], output_ports=[3, 4] (all ports = [1, 2, 3, 4])
        Returns: ["S11", "S22", "S33", "S44"]
        
        VSWR measures how well matched each port is. Lower VSWR is better
        (ideal is 1.0, meaning no reflection).
        
        Args:
            n_ports: Total number of ports in the device (from Touchstone file)
                     Used to filter out invalid port numbers
            
        Returns:
            List of S-parameter strings, sorted (e.g., ["S11", "S22", "S33", "S44"])
        """
        all_ports = self.get_all_ports()
        
        # Generate reflection coefficient S-parameters for each port
        # Format: S{port}{port} (e.g., S11 for port 1, S22 for port 2)
        vswr_params = [f"S{p}{p}" for p in all_ports if p <= n_ports]
        
        return sorted(vswr_params)
    
    model_config = ConfigDict(
        # Allow UUID serialization to string for JSON compatibility
        json_encoders={
            UUID: str
        }
    )
