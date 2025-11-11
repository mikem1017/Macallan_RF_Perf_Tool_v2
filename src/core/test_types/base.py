"""
Abstract base class for test types.

This module defines the AbstractTestType interface, which all test type
implementations must inherit from. Test types are pluggable components that
handle specific measurement types (e.g., S-Parameters, Noise Figure, etc.).

The abstract base class ensures:
- Consistent interface across all test types
- Type safety (all test types implement required methods)
- Extensibility (new test types can be added by implementing this interface)

Key responsibilities of test types:
- Calculate metrics from measurement data
- Evaluate compliance against test criteria
- Generate test results with pass/fail status
- Apply criteria to appropriate measurements (e.g., per S-parameter)

Test types are registered in TestTypeRegistry and discovered automatically
by the application.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID

from ..models.device import Device
from ..models.measurement import Measurement
from ..models.test_criteria import TestCriteria
from ..models.test_result import TestResult


class AbstractTestType(ABC):
    """
    Abstract base class for all test type implementations.
    
    Defines the interface that all test types must implement. Test types
    handle the business logic for specific measurement types, including:
    - Calculating metrics from raw measurement data
    - Evaluating compliance against criteria
    - Generating detailed pass/fail results
    
    Examples of test types:
    - S-Parameters: Gain, flatness, VSWR, OOB rejection
    - Noise Figure: NF measurements, gain compression
    - Power/Linearity: P1dB, IP3, power handling
    
    Each test type implementation:
    1. Calculates relevant metrics from measurements
    2. Evaluates each criterion against the metrics
    3. Generates TestResult objects for each criterion-measurement pair
    
    The device parameter is needed for configuration (e.g., port assignments
    for S-parameters) that affects which measurements are evaluated.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of this test type.
        
        Used for identification, registration, and user display.
        Must be unique within the system.
        
        Examples: "S-Parameters", "Noise Figure", "Power/Linearity"
        
        Returns:
            Test type name (string identifier)
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a description of this test type.
        
        Provides human-readable information about what this test type measures
        and what metrics it calculates. Used for help text and documentation.
        
        Returns:
            Description string (e.g., "S-Parameter testing including gain, flatness, VSWR")
        """
        pass
    
    @abstractmethod
    def calculate_metrics(
        self,
        measurement: Measurement,
        operational_freq_min: float,
        operational_freq_max: float
    ) -> Dict[str, Any]:
        """
        Calculate all metrics for a measurement.
        
        This method extracts raw metrics from the measurement data. The
        metrics dictionary can contain any test-type-specific values needed
        for compliance evaluation.
        
        Metrics are typically calculated once per measurement, then used
        for all compliance evaluations (multiple criteria may use the same
        metrics).
        
        Args:
            measurement: The measurement to calculate metrics for
                        Contains touchstone_data (RF measurement data)
            operational_freq_min: Minimum operational frequency in GHz
                                 Used to focus calculations on operational band
            operational_freq_max: Maximum operational frequency in GHz
            
        Returns:
            Dictionary of metric_name -> metric_value
            Example: {"S21 Gain Range": {"min": 27.5, "max": 31.3}, ...}
            
        Note:
            Metrics are calculated across the operational frequency range.
            Different metrics may use different frequency ranges (e.g., OOB
            uses its own frequency range from criteria).
        """
        pass
    
    @abstractmethod
    def evaluate_compliance(
        self,
        measurement: Measurement,
        device: Device,
        test_criteria: List[TestCriteria],
        operational_freq_min: float,
        operational_freq_max: float
    ) -> List[TestResult]:
        """
        Evaluate compliance of a measurement against test criteria.
        
        This is the core compliance evaluation method. It:
        1. Calculates metrics from the measurement
        2. Evaluates each criterion against the metrics
        3. Generates TestResult objects for each criterion-measurement combination
        
        For generic criteria (e.g., "Gain Range"), multiple results may be
        generated (one per applicable S-parameter). Each result is tagged
        with the specific S-parameter it applies to.
        
        Args:
            measurement: The measurement to evaluate (one Touchstone file)
            device: Device configuration (needed for port configuration, etc.)
                   Port configuration determines which S-parameters are evaluated
            test_criteria: List of test criteria to evaluate against
                          Criteria should already be filtered by device/test_type/test_stage
            operational_freq_min: Minimum operational frequency in GHz
                                 Used for frequency range filtering
            operational_freq_max: Maximum operational frequency in GHz
            
        Returns:
            List of TestResult objects
            - One result per criterion per applicable measurement parameter
            - For "Gain Range" with 3 gain S-parameters → 3 results
            - Each result has s_parameter field populated
            
        Example:
            Measurement: S4P file for device with ports [1,2] → [3,4]
            Criteria: ["Gain Range", "VSWR Max"]
            Results: 
              - Gain Range for S31
              - Gain Range for S32
              - Gain Range for S41
              - Gain Range for S42
              - VSWR Max for S11
              - VSWR Max for S22
              - VSWR Max for S33
              - VSWR Max for S44
        """
        pass
    
    def get_required_criteria_names(self) -> List[str]:
        """
        Get list of required criteria names for this test type.
        
        Optional method that can be overridden by subclasses to provide
        a list of standard criteria names. This is used by the GUI to
        suggest criteria names when setting up device requirements.
        
        This method is not abstract, so implementations can omit it if
        they don't want to provide standard criteria suggestions.
        
        Returns:
            List of criteria requirement names
            Example: ['Gain Range', 'Flatness', 'VSWR Max']
            
        Note:
            These are generic names that apply to multiple measurements.
            The test type implementation determines which measurements
            each criterion applies to (e.g., which S-parameters).
        """
        return []
