"""
S-Parameter calculation service.

This module provides comprehensive S-parameter calculation functionality for
compliance testing. It uses scikit-rf to perform RF calculations including:

- Gain calculations (transmission parameters)
- Gain range (min/max over frequency range)
- Flatness (variation in gain across frequency)
- VSWR (Voltage Standing Wave Ratio - reflection coefficients)
- OOB (Out-of-Band) rejection (gain suppression outside operational band)

All calculations work with scikit-rf Network objects, which contain S-parameter
data in complex format. The calculator handles frequency filtering, unit
conversions (GHz to Hz), and provides RF engineering-specific metrics.

Key design:
- Frequency ranges are specified in GHz (user-friendly)
- Internal calculations use Hz (scikit-rf requirement)
- Results returned in standard RF units (dB, dBc, VSWR ratio)
"""

import re
from typing import Optional, Tuple, List, Union
import numpy as np

# Try to import scikit-rf - handle gracefully if not installed
try:
    from skrf import Network
    SKRF_AVAILABLE = True
except ImportError:
    SKRF_AVAILABLE = False
    Network = None

from ..exceptions import FileLoadError


class SParameterCalculator:
    """
    Calculate S-parameter metrics for compliance testing.
    
    Provides methods to calculate various RF metrics from S-parameter data:
    - Gain (transmission): S21, S31, S41, etc. (input to output)
    - VSWR (reflection): S11, S22, S33, etc. (port matching)
    - Flatness: Variation in gain across frequency
    - OOB rejection: Out-of-band gain suppression
    
    All methods work with scikit-rf Network objects and handle frequency
    range filtering to focus calculations on specific bands (operational,
    wideband, or OOB ranges).
    """
    
    def __init__(self):
        """
        Initialize the calculator.
        
        Verifies that scikit-rf is available. All calculation methods require
        scikit-rf to function.
        
        Raises:
            FileLoadError: If scikit-rf is not installed
        """
        if not SKRF_AVAILABLE:
            raise FileLoadError(
                "scikit-rf is not installed. Please install it with: pip install scikit-rf"
            )
    
    def filter_frequency_range(
        self,
        network: Network,
        freq_min: float,
        freq_max: float
    ) -> Network:
        """
        Filter network to a frequency range, including boundary points.
        
        Creates a filtered Network object containing only data within the
        specified frequency range. Includes boundary points to ensure we
        capture data at the exact range limits, even if the original frequency
        points don't align exactly.
        
        This is used to focus calculations on specific bands:
        - Operational range: For gain, flatness calculations
        - OOB range: For rejection calculations
        
        Args:
            network: scikit-rf Network object (full frequency sweep)
            freq_min: Minimum frequency in GHz (user-friendly unit)
            freq_max: Maximum frequency in GHz
            
        Returns:
            Filtered Network object containing only frequencies in range
            (includes boundary points even if slightly outside range)
        """
        # Convert GHz to Hz for scikit-rf (scikit-rf uses Hz internally)
        freq_min_hz = freq_min * 1e9
        freq_max_hz = freq_max * 1e9
        
        # Get frequency array from network (in Hz)
        freq_hz = network.f
        
        if len(freq_hz) == 0:
            return network.copy()
        
        # Ensure freq_min_hz <= freq_max_hz
        if freq_min_hz > freq_max_hz:
            freq_min_hz, freq_max_hz = freq_max_hz, freq_min_hz
        
        # Clamp desired boundaries to network domain (no extrapolation)
        global_min = freq_hz.min()
        global_max = freq_hz.max()
        target_min = np.clip(freq_min_hz, global_min, global_max)
        target_max = np.clip(freq_max_hz, global_min, global_max)
        
        # Build target frequency list including boundaries
        interior = freq_hz[(freq_hz >= target_min) & (freq_hz <= target_max)]
        targets = np.concatenate([interior, [target_min, target_max]])
        targets = np.unique(np.sort(targets))
        
        # Interpolate to requested frequencies (linear)
        interpolated = network.interpolate(targets)
        
        # Final mask to ensure inclusive boundaries
        mask = (interpolated.f >= target_min - 1e-9) & (interpolated.f <= target_max + 1e-9)
        filtered = interpolated[mask]
        
        return filtered
    
    def calculate_gain(self, network: Network, s_param: str = "S21") -> np.ndarray:
        """
        Calculate gain in dB using scikit-rf.
        
        Extracts transmission S-parameter magnitude and converts to dB.
        For S-parameters like S21 (port 1 input → port 2 output), this
        represents forward gain.
        
        S-parameter format: S{output_port}{input_port}
        Examples:
        - S21: Input at port 1, output at port 2
        - S31: Input at port 1, output at port 3
        - S41: Input at port 1, output at port 4
        
        Args:
            network: scikit-rf Network object
            s_param: S-parameter string (e.g., "S21", "S31", "S41")
                    Format must be S{output}{input} where ports are 1-indexed
            
        Returns:
            Gain array in dB (one value per frequency point)
            Gain is already in dB (20*log10(|S|)) from scikit-rf
            
        Raises:
            ValueError: If S-parameter format is invalid
        """
        # Parse S-parameter string to extract port numbers
        # Format: S{output_port}{input_port} (e.g., "S21" = port 2 out, port 1 in)
        match = re.match(r"S(\d)(\d)", s_param)
        if not match:
            raise ValueError(f"Invalid S-parameter format: {s_param}")
        
        # Convert to 0-indexed for scikit-rf array access
        # scikit-rf uses 0-indexed arrays internally
        output_port = int(match.group(1)) - 1  # Output port (0-indexed)
        input_port = int(match.group(2)) - 1   # Input port (0-indexed)
        
        # Get S-parameter magnitude in dB
        # network.s_db is already in dB (20*log10(|S|))
        # Shape: [frequency_points, output_port, input_port]
        gain_db = network.s_db[:, output_port, input_port]
        
        return gain_db
    
    def calculate_gain_range(
        self,
        network: Network,
        freq_min: float,
        freq_max: float,
        s_param: str = "S21"
    ) -> Tuple[float, float]:
        """
        Calculate gain range (min and max) over operational frequency range.
        
        Filters network to the specified frequency range and finds the minimum
        and maximum gain values. This is used for "Gain Range" criteria that
        require gain to be within specified bounds.
        
        Args:
            network: scikit-rf Network object (full frequency sweep)
            freq_min: Minimum frequency in GHz (operational range start)
            freq_max: Maximum frequency in GHz (operational range end)
            s_param: S-parameter to use (e.g., "S21", "S31", "S41")
            
        Returns:
            Tuple of (min_gain_db, max_gain_db)
            Both values are in dB. The range (max - min) represents gain variation.
        """
        # Filter network to operational frequency range
        filtered = self.filter_frequency_range(network, freq_min, freq_max)
        
        # Calculate gain across the filtered range
        gain_db = self.calculate_gain(filtered, s_param)
        
        # Find minimum and maximum gain values
        min_gain = float(np.min(gain_db))
        max_gain = float(np.max(gain_db))
        
        return (min_gain, max_gain)
    
    def calculate_flatness(
        self,
        network: Network,
        freq_min: float,
        freq_max: float,
        s_param: str = "S21"
    ) -> float:
        """
        Calculate gain flatness (max - min) over operational frequency range.
        
        Flatness measures how much the gain varies across the frequency range.
        Lower flatness is better (more consistent gain). Flatness is the difference
        between maximum and minimum gain in the range.
        
        Formula: flatness = max_gain - min_gain (in dB)
        
        Args:
            network: scikit-rf Network object
            freq_min: Minimum frequency in GHz (operational range)
            freq_max: Maximum frequency in GHz
            s_param: S-parameter to use
            
        Returns:
            Flatness in dB (max_gain - min_gain)
            Positive value representing the gain variation span
        """
        # Get gain range (min and max) across the frequency range
        min_gain, max_gain = self.calculate_gain_range(
            network, freq_min, freq_max, s_param
        )
        
        # Flatness is the difference (span) between max and min
        return max_gain - min_gain
    
    def calculate_lowest_in_band_gain(
        self,
        network: Network,
        freq_min: float,
        freq_max: float,
        s_param: str = "S21"
    ) -> float:
        """
        Calculate lowest gain within operational frequency range.
        
        Finds the minimum gain value in the operational band. This is used as
        the reference point for OOB rejection calculations.
        
        Args:
            network: scikit-rf Network object
            freq_min: Minimum frequency in GHz (operational range)
            freq_max: Maximum frequency in GHz
            s_param: S-parameter to use
            
        Returns:
            Lowest gain in dB (minimum value across the range)
        """
        # Get minimum gain from gain range calculation
        min_gain, _ = self.calculate_gain_range(network, freq_min, freq_max, s_param)
        return min_gain
    
    def calculate_oob_rejection(
        self,
        network: Network,
        oob_freq_min: float,
        oob_freq_max: float,
        operational_freq_min: float,
        operational_freq_max: float,
        s_param: str = "S21"
    ) -> float:
        """
        Calculate OOB rejection in dBc relative to lowest in-band gain.
        
        Evaluates rejection across a frequency range and returns the worst-case
        (minimum) rejection. This ensures compliance is based on the most critical
        point in the OOB range.
        
        IMPORTANT: This calculates REJECTION (in dBc), not gain. Rejection represents
        how much lower the OOB gain is compared to the minimum in-band gain.
        
        Formula: rejection (dBc) = min_in_band_gain - worst_case_oob_gain
        - If OOB gain is much lower than in-band, rejection is large (good)
        - If OOB gain is close to in-band, rejection is small (bad)
        
        The worst-case (minimum) rejection is found across the entire OOB frequency
        range, ensuring compliance is checked against the most critical point.
        
        Example workflow:
        1. Find minimum in-band gain: min_in_band = -30 dB
        2. Find worst-case OOB gain (across OOB range): worst_oob = -90 dB
        3. Calculate rejection: rejection = -30 - (-90) = 60 dBc
        4. Compare to requirement: 60 dBc >= 60 dBc → PASS
        
        Args:
            network: scikit-rf Network object (full frequency sweep)
            oob_freq_min: Minimum OOB frequency in GHz
            oob_freq_max: Maximum OOB frequency in GHz
            operational_freq_min: Minimum operational frequency in GHz
            operational_freq_max: Maximum operational frequency in GHz
            s_param: S-parameter to use (e.g., "S21", "S31", "S41")
            
        Returns:
            Minimum rejection in dBc across the OOB frequency range
            This is the WORST-CASE rejection (minimum value across the range).
            Positive value means OOB gain is lower than in-band minimum (good).
            Example: If requirement is >= 60 dBc, this returns the minimum rejection
            across the range, which is then compared: rejection >= 60 dBc.
        """
        # Get lowest in-band gain (reference point for rejection calculation)
        # This is the baseline - all OOB rejection is measured relative to this
        # Lower in-band gain means lower baseline, affecting rejection calculation
        lowest_in_band = self.calculate_lowest_in_band_gain(
            network, operational_freq_min, operational_freq_max, s_param
        )
        
        # Filter network to OOB frequency range
        # This isolates the out-of-band region for analysis
        oob_network = self.filter_frequency_range(network, oob_freq_min, oob_freq_max)
        
        # Calculate gain across the OOB range
        # This gives us gain values at each frequency point in the OOB region
        gain_at_oob = self.calculate_gain(oob_network, s_param)
        
        # Calculate rejection at each frequency point in the OOB range
        # REJECTION (dBc) = lowest_in_band_gain - oob_gain
        # Higher rejection = better (OOB gain is much lower than in-band)
        # If OOB gain is -90 dB and in-band min is -30 dB, rejection = 60 dBc
        rejections_dbce = lowest_in_band - gain_at_oob
        
        # Return minimum (worst-case) rejection across the range
        # We use MIN because this is the worst case - if the minimum rejection
        # meets the requirement, then all points in the range meet it.
        # This ensures conservative compliance evaluation.
        # Example: If requirement is >= 60 dBc and min_rejection = 65 dBc, it passes.
        # If min_rejection = 55 dBc, it fails (even if some points have 70 dBc rejection).
        min_rejection = float(np.min(rejections_dbce))
        
        return min_rejection
    
    def calculate_vswr(
        self,
        network: Network,
        port: int = 1,
        freq_min: Optional[float] = None,
        freq_max: Optional[float] = None
    ) -> Union[np.ndarray, float]:
        """
        Calculate VSWR (Voltage Standing Wave Ratio) using scikit-rf.
        
        VSWR measures how well matched a port is. It's calculated from the
        reflection coefficient (S-parameter for same port: S11, S22, S33, etc.).
        
        Formula: VSWR = (1 + |Γ|) / (1 - |Γ|) where Γ is reflection coefficient
        
        VSWR interpretation:
        - 1.0: Perfect match (ideal, no reflection)
        - 2.0: Acceptable match
        - Higher: Poor match (more reflection)
        
        Lower VSWR is better. Requirements typically specify maximum VSWR.
        
        Args:
            network: scikit-rf Network object
            port: Port number (1-indexed, e.g., 1, 2, 3, 4)
            freq_min: Optional minimum frequency in GHz for filtering
                    If provided with freq_max, returns max VSWR over range
            freq_max: Optional maximum frequency in GHz for filtering
            
        Returns:
            If freq_min and freq_max provided: float (max VSWR over range)
            Otherwise: np.ndarray (VSWR at each frequency point)
            
        Note:
            VSWR is calculated using scikit-rf's built-in s_vswr property,
            which automatically converts reflection coefficients to VSWR.
        """
        # Filter network to frequency range if specified
        # This focuses VSWR calculation on operational band
        if freq_min is not None and freq_max is not None:
            filtered = self.filter_frequency_range(network, freq_min, freq_max)
        else:
            filtered = network
        
        # Calculate VSWR for specified port
        # VSWR = (1 + |Γ|) / (1 - |Γ|) where Γ is reflection coefficient
        # scikit-rf provides s_vswr which is already calculated
        # Port is 0-indexed in scikit-rf arrays
        port_idx = port - 1
        
        # Use scikit-rf's built-in calculation
        try:
            # s_vswr returns shape [frequency_points, nports, nports]
            # We need the diagonal element for the requested port.
            vswr = filtered.s_vswr[:, port_idx, port_idx]  # Shape: [frequency_points]
        except (IndexError, AttributeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error accessing s_vswr for port {port} (index {port_idx}): {e}")
            logger.error(f"Network has {filtered.nports} ports, trying to access port index {port_idx}")
            raise ValueError(f"Invalid port {port} for network with {filtered.nports} ports") from e
        
        # If frequency range specified, return maximum VSWR (worst case)
        # This ensures compliance is checked against worst matching point
        if freq_min is not None and freq_max is not None:
            # Return max VSWR over the range (worst case)
            return float(np.max(vswr))
        else:
            # Return array of VSWR values (one per frequency point)
            return vswr
    
    def calculate_return_loss(
        self,
        network: Network,
        port: int = 1,
        freq_min: Optional[float] = None,
        freq_max: Optional[float] = None
    ) -> Union[np.ndarray, float]:
        """
        Calculate Return Loss from reflection coefficient S-parameter.
        
        Return Loss measures how well matched a port is, expressed in dB.
        It's calculated from the reflection coefficient (S-parameter for same port: S11, S22, etc.).
        
        Formula: Return Loss = 20*log10(|S11|) where S11 is the reflection coefficient
        
        Return Loss interpretation:
        - More negative values indicate better match (less reflection)
        - -10 dB: Poor match (~10% power reflected)
        - -20 dB: Good match (~1% power reflected)
        - -30 dB: Excellent match (~0.1% power reflected)
        
        Lower (more negative) Return Loss is better. Requirements typically specify maximum Return Loss.
        
        Args:
            network: scikit-rf Network object
            port: Port number (1-indexed, e.g., 1, 2, 3, 4)
            freq_min: Optional minimum frequency in GHz for filtering
                    If provided with freq_max, returns worst Return Loss over range
            freq_max: Optional maximum frequency in GHz for filtering
            
        Returns:
            If freq_min and freq_max provided: float (worst Return Loss over range, most negative)
            Otherwise: np.ndarray (Return Loss at each frequency point in dB)
            
        Note:
            Return Loss is calculated as 20*log10(|S11|), which gives negative values.
            More negative values indicate better matching.
        """
        # Filter network to frequency range if specified
        if freq_min is not None and freq_max is not None:
            filtered = self.filter_frequency_range(network, freq_min, freq_max)
        else:
            filtered = network
        
        # Get reflection coefficient S-parameter (e.g., S11 for port 1)
        # Port is 0-indexed in scikit-rf arrays
        port_idx = port - 1
        
        try:
            # Get S-parameter matrix: shape [frequency_points, nports, nports]
            # For reflection coefficient, we want S[port_idx, port_idx]
            s_param = filtered.s[:, port_idx, port_idx]  # Shape: [frequency_points] (complex)
            
            # Calculate magnitude
            s_magnitude = np.abs(s_param)  # Shape: [frequency_points]
            
            # Calculate Return Loss: RL = 20*log10(|S11|)
            # Use np.clip to avoid log10(0) which would give -inf
            s_magnitude_clipped = np.clip(s_magnitude, 1e-10, 1.0)
            return_loss = 20 * np.log10(s_magnitude_clipped)  # Shape: [frequency_points]
            
        except (IndexError, AttributeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error accessing S-parameter for port {port} (index {port_idx}): {e}")
            logger.error(f"Network has {filtered.nports} ports, trying to access port index {port_idx}")
            raise ValueError(f"Invalid port {port} for network with {filtered.nports} ports") from e
        
        # If frequency range specified, return worst (most negative) Return Loss
        if freq_min is not None and freq_max is not None:
            # Return most negative value (worst case)
            return float(np.min(return_loss))
        else:
            # Return array of Return Loss values (one per frequency point)
            return return_loss
    
    def vswr_to_return_loss(self, vswr: float) -> float:
        """
        Convert VSWR to Return Loss.
        
        Formula: |Γ| = (VSWR - 1) / (VSWR + 1)
                Return Loss = 20*log10(|Γ|)
        
        Example: VSWR = 1.5 → Return Loss ≈ -14 dB
        
        Args:
            vswr: VSWR value (must be >= 1.0)
            
        Returns:
            Return Loss in dB (negative value)
            
        Raises:
            ValueError: If VSWR < 1.0
        """
        if vswr < 1.0:
            raise ValueError(f"VSWR must be >= 1.0, got {vswr}")
        
        # Calculate reflection coefficient magnitude
        gamma_magnitude = (vswr - 1.0) / (vswr + 1.0)
        
        # Calculate Return Loss
        # Use clip to avoid log10(0) if gamma_magnitude is exactly 0
        gamma_clipped = max(gamma_magnitude, 1e-10)
        return_loss = 20 * np.log10(gamma_clipped)
        
        return return_loss
    
    def get_available_s_params(self, network: Network) -> List[str]:
        """
        Get list of available S-parameters for this network.
        
        Returns a list of common transmission S-parameters based on the
        port count. This is a helper method for identifying which S-parameters
        are available for analysis.
        
        Note: This returns a subset of available S-parameters (common
        transmission paths). For full S-parameter matrix, network provides
        all S{out}{in} combinations.
        
        Args:
            network: scikit-rf Network object
            
        Returns:
            List of S-parameter names (e.g., ["S21", "S31", "S41"])
            These represent transmission from port 1 to output ports.
            
        Note:
            This method returns common transmission parameters. For full
            analysis, you may need all S-parameters. The device's port
            configuration determines which S-parameters are actually used
            for gain and VSWR calculations.
        """
        s_params = []
        n_ports = network.nports
        
        # Common transmission parameters from port 1
        if n_ports >= 2:
            # S21 (port 1 to port 2)
            s_params.append("S21")
        if n_ports >= 3:
            # S31 (port 1 to port 3)
            s_params.append("S31")
        if n_ports >= 4:
            # S41 (port 1 to port 4)
            s_params.append("S41")
        
        return s_params
