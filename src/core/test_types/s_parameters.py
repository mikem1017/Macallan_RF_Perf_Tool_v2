"""
S-Parameters test type implementation.

This module implements the SParametersTestType, which handles all S-parameter
compliance testing. It calculates RF metrics and evaluates compliance for:

- Gain Range: Min/max gain over operational frequency range
- Flatness: Gain variation (max - min) across operational range
- VSWR: Voltage Standing Wave Ratio (reflection at each port)
- OOB Rejection: Out-of-band gain suppression (worst-case across OOB range)

Key design features:
- Generic criteria names ("Gain Range") that apply to multiple S-parameters
- Port-based S-parameter identification (from device configuration)
- Per-S-parameter results (each result tagged with s_parameter field)
- Frequency range filtering (operational vs OOB ranges)

The implementation uses SParameterCalculator for RF calculations and
TouchstoneLoader for data handling.
"""

from typing import List, Dict, Any, Optional, Union
from uuid import uuid4

from ..models.device import Device
from ..models.measurement import Measurement
from ..models.test_criteria import TestCriteria
from ..models.test_result import TestResult
from ..rf_data.touchstone_loader import TouchstoneLoader
from ..rf_data.s_parameter_calculator import SParameterCalculator
from .base import AbstractTestType


class SParametersTestType(AbstractTestType):
    """
    S-Parameters test type implementation.
    
    Handles all S-parameter compliance testing including gain, flatness,
    VSWR, and out-of-band rejection. Uses device port configuration to
    determine which S-parameters represent gain (input→output) vs VSWR
    (reflection at each port).
    
    Key workflow:
    1. Calculate all metrics for all possible S-parameters
    2. Filter applicable S-parameters based on device port configuration
    3. Evaluate each criterion against applicable S-parameters
    4. Generate one TestResult per criterion per S-parameter
    
    Generic criteria allow one requirement name (e.g., "Gain Range") to
    apply to multiple S-parameters automatically (e.g., S21, S31, S41).
    """
    
    def __init__(self):
        """
        Initialize S-Parameters test type.
        
        Creates instances of TouchstoneLoader and SParameterCalculator
        for RF data processing and calculations.
        """
        self.loader = TouchstoneLoader()
        self.calculator = SParameterCalculator()
    
    @property
    def name(self) -> str:
        """
        Return the name of this test type.
        
        Returns:
            "S-Parameters" (test type identifier)
        """
        return "S-Parameters"
    
    @property
    def description(self) -> str:
        """
        Return description of this test type.
        
        Returns:
            Human-readable description of what this test type measures
        """
        return "S-Parameter testing including gain, flatness, VSWR, and out-of-band rejection"
    
    def calculate_metrics(
        self,
        measurement: Measurement,
        operational_freq_min: float,
        operational_freq_max: float
    ) -> Dict[str, Any]:
        """
        Calculate all S-parameter metrics for a measurement.
        
        Calculates metrics for ALL possible S-parameters in the network.
        This comprehensive approach ensures we have all data available
        when filtering by port configuration during evaluation.
        
        Metrics calculated:
        - Gain Range: Min and max gain for each S-parameter
        - Flatness: Gain variation for each S-parameter
        - Lowest In-Band Gain: Reference for OOB calculations
        - VSWR: For each port (reflection coefficients)
        
        Args:
            measurement: Measurement containing touchstone_data (Network object)
            operational_freq_min: Minimum operational frequency in GHz
            operational_freq_max: Maximum operational frequency in GHz
            
        Returns:
            Dictionary with metrics keyed by S-parameter and metric type
            Example: {
                "S21 Gain Range": {"min": 27.5, "max": 31.3},
                "S21 Flatness": 2.1,
                "S11 VSWR": 1.8,
                ...
            }
            
        Raises:
            ValueError: If measurement has no touchstone_data
        """
        # Validate measurement has data
        if measurement.touchstone_data is None:
            raise ValueError("Measurement has no touchstone data")
        
        # Get network object (may need to deserialize from bytes)
        # Touchstone data can be stored as bytes (pickled) in database
        # or as Network object in memory
        if isinstance(measurement.touchstone_data, bytes):
            network = self.loader.deserialize_network(measurement.touchstone_data)
        else:
            network = measurement.touchstone_data
        
        metrics = {}
        n_ports = network.nports
        
        # Calculate metrics for ALL possible S-parameters (we'll filter usage based on port config during evaluation)
        # This ensures we have all data available when determining which S-parameters to evaluate
        # Strategy: Calculate everything, filter by port config during compliance evaluation
        for out_port in range(1, n_ports + 1):
            for in_port in range(1, n_ports + 1):
                s_param = f"S{out_port}{in_port}"
                
                try:
                    # Gain range (transmission parameters)
                    # Calculated for all S-parameters, but only used for input→output combinations
                    min_gain, max_gain = self.calculator.calculate_gain_range(
                        network, operational_freq_min, operational_freq_max, s_param
                    )
                    metrics[f"{s_param} Gain Range"] = {
                        "min": min_gain,
                        "max": max_gain
                    }
                    
                    # Flatness: Variation in gain across operational range
                    flatness = self.calculator.calculate_flatness(
                        network, operational_freq_min, operational_freq_max, s_param
                    )
                    metrics[f"{s_param} Flatness"] = flatness
                    
                    # Lowest in-band gain (needed for OOB calculations)
                    # Used as reference point for OOB rejection calculations
                    lowest_gain = self.calculator.calculate_lowest_in_band_gain(
                        network, operational_freq_min, operational_freq_max, s_param
                    )
                    metrics[f"{s_param} Lowest In-Band Gain"] = lowest_gain
                except (ValueError, IndexError):
                    # Skip if S-parameter calculation fails (invalid port combination, etc.)
                    pass
        
        # VSWR for all ports (reflection coefficients: S11, S22, S33, etc.)
        # VSWR measures port matching quality - calculated for each port independently
        for port in range(1, n_ports + 1):
            try:
                vswr = self.calculator.calculate_vswr(
                    network, port=port, freq_min=operational_freq_min, freq_max=operational_freq_max
                )
                s_param = f"S{port}{port}"  # Reflection coefficient (same port in/out)
                metrics[f"{s_param} VSWR"] = vswr
            except (ValueError, IndexError):
                # Skip if VSWR calculation fails
                pass
        
        return metrics
    
    def evaluate_compliance(
        self,
        measurement: Measurement,
        device: Device,
        test_criteria: List[TestCriteria],
        operational_freq_min: float,
        operational_freq_max: float
    ) -> List[TestResult]:
        """
        Evaluate compliance of measurement against S-parameter criteria.
        
        This is the main compliance evaluation method. It:
        1. Calculates all metrics for the measurement
        2. Gets port configuration from device (determines which S-parameters to evaluate)
        3. Evaluates each criterion against applicable S-parameters
        4. Generates TestResult objects with s_parameter tags
        
        Generic criteria (e.g., "Gain Range") are automatically applied to
        all relevant S-parameters based on port configuration. Each application
        generates a separate TestResult.
        
        Args:
            measurement: The measurement to evaluate (one Touchstone file)
            device: Device configuration (needed for port configuration)
                   Port configuration determines which S-parameters are gain vs VSWR
            test_criteria: List of test criteria to evaluate against
                          Should be filtered by device/test_type/test_stage
            operational_freq_min: Minimum operational frequency in GHz
            operational_freq_max: Maximum operational frequency in GHz
            
        Returns:
            List of TestResult objects (one per S-parameter per criterion)
            Each result is tagged with s_parameter field for display in compliance table
            
        Example output for device with ports [1,2]→[3,4] and criteria ["Gain Range", "VSWR Max"]:
            - Gain Range for S31
            - Gain Range for S32
            - Gain Range for S41
            - Gain Range for S42
            - VSWR Max for S11
            - VSWR Max for S22
            - VSWR Max for S33
            - VSWR Max for S44
        """
        results = []
        
        # Step 1: Calculate all metrics first (one-time calculation for all criteria)
        metrics = self.calculate_metrics(measurement, operational_freq_min, operational_freq_max)
        
        # Step 2: Get network object for OOB calculations (needed if OOB criteria present)
        if isinstance(measurement.touchstone_data, bytes):
            network = self.loader.deserialize_network(measurement.touchstone_data)
        else:
            network = measurement.touchstone_data
        
        n_ports = network.nports
        
        # Step 3: Get port configuration from device
        # This determines which S-parameters represent gain (input→output) vs VSWR (reflection)
        gain_s_params = device.get_gain_s_parameters(n_ports)
        vswr_s_params = device.get_vswr_s_parameters(n_ports)
        
        # Step 4: Evaluate each criterion against applicable S-parameters
        for criterion in test_criteria:
            criterion_results = self._evaluate_criterion_for_all_s_params(
                criterion, metrics, network, measurement, device,
                operational_freq_min, operational_freq_max,
                gain_s_params, vswr_s_params
            )
            results.extend(criterion_results)
        
        return results
    
    def _evaluate_criterion_for_all_s_params(
        self,
        criterion: TestCriteria,
        metrics: Dict[str, Any],
        network: Any,
        measurement: Measurement,
        device: Device,
        operational_freq_min: float,
        operational_freq_max: float,
        gain_s_params: List[str],
        vswr_s_params: List[str]
    ) -> List[TestResult]:
        """
        Evaluate a criterion for all applicable S-parameters.
        
        Determines which type of criterion this is and evaluates it against
        all relevant S-parameters. Generic criteria names allow one requirement
        to apply to multiple S-parameters automatically.
        
        Criterion types:
        - Gain Range: Applied to all gain S-parameters (input→output)
        - Flatness: Applied to all gain S-parameters
        - VSWR Max: Applied to all ports (reflection coefficients)
        - OOB: Applied to all gain S-parameters (frequency range from criterion)
        
        Args:
            criterion: TestCriteria to evaluate
            metrics: Pre-calculated metrics dictionary
            network: scikit-rf Network object (for OOB calculations)
            measurement: Measurement being evaluated
            device: Device configuration
            operational_freq_min: Minimum operational frequency in GHz
            operational_freq_max: Maximum operational frequency in GHz
            gain_s_params: List of gain S-parameters (from port config, e.g., ["S31", "S41"])
            vswr_s_params: List of VSWR S-parameters (from port config, e.g., ["S11", "S22", "S33", "S44"])
            
        Returns:
            List of TestResult objects (one per applicable S-parameter)
            Empty list if criterion doesn't match any recognized type
        """
        results = []
        req_name = criterion.requirement_name.lower()  # Case-insensitive matching
        
        # Determine which type of criterion this is and evaluate accordingly
        # Gain Range: evaluate for all input→output S-parameters
        # Example: "Gain Range" applies to S31, S32, S41, S42 (from port config)
        if "gain" in req_name and "range" in req_name:
            for s_param in gain_s_params:
                result = self._evaluate_gain_range_criterion(
                    criterion, metrics, s_param, measurement
                )
                if result:
                    results.append(result)
        
        # Flatness: evaluate for all input→output S-parameters
        # Measures gain variation across frequency range
        elif "flatness" in req_name:
            for s_param in gain_s_params:
                result = self._evaluate_flatness_criterion(
                    criterion, metrics, s_param, measurement
                )
                if result:
                    results.append(result)
        
        # VSWR: evaluate for all ports (reflection coefficients)
        # Each port gets its own VSWR measurement (S11, S22, S33, etc.)
        elif "vswr" in req_name:
            for s_param in vswr_s_params:
                result = self._evaluate_vswr_criterion(
                    criterion, metrics, s_param, measurement
                )
                if result:
                    results.append(result)
        
        # OOB rejection: evaluate for all input→output S-parameters
        # OOB criteria must have both frequency_min and frequency_max defined
        elif criterion.frequency_min is not None and criterion.frequency_max is not None:
            for s_param in gain_s_params:
                result = self._evaluate_oob_criterion(
                    criterion, network, s_param, measurement,
                    operational_freq_min, operational_freq_max
                )
                if result:
                    results.append(result)
        
        return results
    
    def _evaluate_gain_range_criterion(
        self,
        criterion: TestCriteria,
        metrics: Dict[str, Any],
        s_param: str,
        measurement: Measurement
    ) -> Optional[TestResult]:
        """
        Evaluate gain range criterion for a specific S-parameter.
        
        Checks if the gain range (min and max) for this S-parameter meets
        the criterion requirements. Both min and max must pass for overall pass.
        
        Args:
            criterion: TestCriteria with criteria_type="range"
            metrics: Pre-calculated metrics dictionary
            s_param: S-parameter being evaluated (e.g., "S21", "S31")
            measurement: Measurement being evaluated
            
        Returns:
            TestResult if metric exists and evaluation succeeds, None otherwise
        """
        metric_key = f"{s_param} Gain Range"
        if metric_key not in metrics:
            return None
        
        gain_range = metrics[metric_key]
        min_gain = gain_range["min"]
        max_gain = gain_range["max"]
        
        # Check if entire range is within limits
        # Both min and max must pass for overall pass
        # This ensures the full gain range meets requirements
        min_pass = criterion.evaluate(min_gain)
        max_pass = criterion.evaluate(max_gain)
        passed = min_pass and max_pass
        
        # Store max_gain as measured_value for database compatibility
        # The GUI will recalculate min/max from measurement data for display
        # This allows showing "min to max" format in the compliance table
        measured_value = max_gain
        
        return TestResult(
            id=uuid4(),
            measurement_id=measurement.id,
            test_criteria_id=criterion.id,
            measured_value=measured_value,
            passed=passed,
            s_parameter=s_param
        )
    
    def _evaluate_flatness_criterion(
        self,
        criterion: TestCriteria,
        metrics: Dict[str, Any],
        s_param: str,
        measurement: Measurement
    ) -> Optional[TestResult]:
        """
        Evaluate flatness criterion for a specific S-parameter.
        
        Flatness measures gain variation. Lower flatness is better (more
        consistent gain). Typically evaluated as max criterion (flatness <= max_value).
        
        Args:
            criterion: TestCriteria (typically criteria_type="max")
            metrics: Pre-calculated metrics dictionary
            s_param: S-parameter being evaluated
            measurement: Measurement being evaluated
            
        Returns:
            TestResult if metric exists, None otherwise
        """
        metric_key = f"{s_param} Flatness"
        if metric_key not in metrics:
            return None
        
        flatness = metrics[metric_key]
        passed = criterion.evaluate(flatness)
        
        return TestResult(
            id=uuid4(),
            measurement_id=measurement.id,
            test_criteria_id=criterion.id,
            measured_value=flatness,
            passed=passed,
            s_parameter=s_param
        )
    
    def _evaluate_vswr_criterion(
        self,
        criterion: TestCriteria,
        metrics: Dict[str, Any],
        s_param: str,
        measurement: Measurement
    ) -> Optional[TestResult]:
        """
        Evaluate VSWR criterion for a specific S-parameter (reflection coefficient).
        
        VSWR measures port matching. Lower VSWR is better. Typically evaluated
        as max criterion (VSWR <= max_value, e.g., VSWR <= 2.0).
        
        Args:
            criterion: TestCriteria (typically criteria_type="max")
            metrics: Pre-calculated metrics dictionary
            s_param: S-parameter being evaluated (reflection: S11, S22, S33, etc.)
            measurement: Measurement being evaluated
            
        Returns:
            TestResult if metric exists, None otherwise
        """
        metric_key = f"{s_param} VSWR"
        if metric_key not in metrics:
            return None
        
        vswr = metrics[metric_key]
        passed = criterion.evaluate(vswr)
        
        return TestResult(
            id=uuid4(),
            measurement_id=measurement.id,
            test_criteria_id=criterion.id,
            measured_value=vswr,
            passed=passed,
            s_parameter=s_param
        )
    
    def _evaluate_oob_criterion(
        self,
        criterion: TestCriteria,
        network: Any,
        s_param: str,
        measurement: Measurement,
        operational_freq_min: float,
        operational_freq_max: float
    ) -> Optional[TestResult]:
        """
        Evaluate OOB rejection criterion for a specific S-parameter.
        
        OOB rejection is evaluated across a frequency range (frequency_min to frequency_max).
        The calculator returns the worst-case (minimum) rejection across this range,
        which is then compared against the criterion requirement.
        
        IMPORTANT: This evaluates REJECTION (in dBc) >= requirement, NOT gain.
        Rejection = min_in_band_gain - worst_case_oob_gain.
        
        Example:
        - Requirement: >= 60 dBc
        - Calculated rejection: 65 dBc (worst-case across OOB range)
        - Result: 65 >= 60 → PASS
        
        Args:
            criterion: TestCriteria with frequency_min and frequency_max set
            network: scikit-rf Network object (needed for OOB calculation)
            s_param: S-parameter to evaluate (e.g., "S21")
            measurement: Measurement being evaluated
            operational_freq_min: Minimum operational frequency in GHz
            operational_freq_max: Maximum operational frequency in GHz
            
        Returns:
            TestResult if evaluation succeeds, None if calculation fails
        """
        # Validate that frequency range is provided
        if criterion.frequency_min is None or criterion.frequency_max is None:
            return None
        
        try:
            # Calculate worst-case (minimum) rejection across OOB frequency range
            # Rejection is calculated as: min_in_band_gain - worst_case_oob_gain (in dBc)
            rejection = self.calculator.calculate_oob_rejection(
                network,
                criterion.frequency_min,  # OOB range minimum
                criterion.frequency_max,  # OOB range maximum
                operational_freq_min,
                operational_freq_max,
                s_param
            )
            
            # IMPORTANT: Compare REJECTION (dBc) >= requirement, NOT gain
            # Example: If requirement is >= 60 dBc:
            #   - rejection = 65 dBc → passes (65 >= 60)
            #   - rejection = 55 dBc → fails (55 < 60)
            # The rejection value is the minimum (worst-case) across the OOB range
            # Higher rejection is better (means OOB gain is much lower than in-band)
            passed = rejection >= criterion.min_value if criterion.min_value else False
            
            return TestResult(
                id=uuid4(),
                measurement_id=measurement.id,
                test_criteria_id=criterion.id,
                measured_value=rejection,
                passed=passed,
                s_parameter=s_param
            )
        except (ValueError, IndexError):
            # Return None if calculation fails (invalid frequency range, missing data, etc.)
            return None
    
    def get_required_criteria_names(self) -> List[str]:
        """
        Get list of required criteria names for S-Parameters test.
        
        Returns standard criteria names that can be used when setting up
        device requirements. These are generic names that apply to multiple
        S-parameters automatically.
        
        Returns:
            List of standard criteria names:
            - "Gain Range": Min/max gain requirements
            - "Flatness": Gain variation requirement
            - "VSWR Max": Maximum VSWR requirement
        """
        return [
            "Gain Range",
            "Flatness",
            "VSWR Max"
        ]
