"""
Compliance service for pass/fail evaluation.

This module provides the ComplianceService, which orchestrates compliance
evaluation using test types from the TestTypeRegistry. It handles:

- Evaluating measurements against criteria
- Storing test results
- Retrieving compliance results for display
- Marking results as stale when criteria change
- Aggregating pass/fail status across all results

The service can evaluate automatically when measurements are loaded, or
manually when requested. It evaluates all measurements at once (all
temperatures, all paths) for comprehensive compliance checking.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models.measurement import Measurement
from ..models.device import Device
from ..models.test_criteria import TestCriteria
from ..models.test_result import TestResult
from ..repositories.measurement_repository import MeasurementRepository
from ..repositories.test_criteria_repository import TestCriteriaRepository
from ..repositories.device_repository import DeviceRepository
from ..repositories.test_result_repository import TestResultRepository
from ..test_types.registry import TestTypeRegistry
from ..exceptions import DeviceNotFoundError, DatabaseError


class ComplianceService:
    """
    Service for compliance evaluation and result management.
    
    Orchestrates the compliance evaluation workflow:
    1. Get criteria for device/test_type/test_stage
    2. Get test type implementation from registry
    3. Evaluate measurement against criteria
    4. Store results in database
    5. Retrieve results for compliance table display
    
    Key features:
    - Automatic or manual evaluation (configurable)
    - Batch evaluation (all measurements at once)
    - Stale result management (mark when criteria change)
    - Pass/fail aggregation across all results
    """
    
    def __init__(
        self,
        measurement_repository: MeasurementRepository,
        criteria_repository: TestCriteriaRepository,
        device_repository: DeviceRepository,
        result_repository: TestResultRepository,
        test_type_registry: Optional[TestTypeRegistry] = None,
        auto_evaluate_on_load: bool = True
    ):
        """
        Initialize compliance service with dependencies.
        
        Args:
            measurement_repository: Repository for measurement queries
            criteria_repository: Repository for criteria queries
            device_repository: Repository for device lookup
            result_repository: Repository for result storage
            test_type_registry: Optional - creates default if not provided
            auto_evaluate_on_load: If True, automatically evaluate when measurements loaded
        """
        self.measurement_repo = measurement_repository
        self.criteria_repo = criteria_repository  # Make accessible for GUI
        self.device_repo = device_repository
        self.result_repo = result_repository
        self.registry = test_type_registry or TestTypeRegistry()
        self.auto_evaluate_on_load = auto_evaluate_on_load
    
    def evaluate_compliance(
        self,
        measurement: Measurement,
        device: Device,
        test_stage: str
    ) -> List[TestResult]:
        """
        Evaluate compliance of a single measurement against criteria.
        
        This method:
        1. Gets criteria for device/test_type/test_stage
        2. Gets appropriate test type from registry
        3. Calls test_type.evaluate_compliance()
        4. Returns list of TestResult objects
        
        Note: Results are NOT saved automatically - caller must call save_test_results().
        This allows batch saving of multiple evaluation results.
        
        Args:
            measurement: Measurement to evaluate
            device: Device configuration (needed for port configuration, etc.)
            test_stage: Test stage (used to get correct criteria)
            
        Returns:
            List of TestResult objects (one per criterion per applicable S-parameter)
            
        Raises:
            DeviceNotFoundError: If device doesn't exist
            DatabaseError: If criteria lookup fails
        """
        # Verify device exists
        existing_device = self.device_repo.get_by_id(device.id)
        if existing_device is None:
            raise DeviceNotFoundError(f"Device with id {device.id} not found")
        
        # Get criteria for this device/test_type/test_stage
        criteria = self.criteria_repo.get_by_device_and_test(
            device.id, measurement.test_type, test_stage
        )
        
        # If no criteria defined, return empty list (nothing to evaluate)
        if not criteria:
            return []
        
        # Get test type implementation from registry
        test_type = self.registry.get(measurement.test_type)
        if test_type is None:
            # No test type registered - return empty results
            return []
        
        # Evaluate compliance using test type
        results = test_type.evaluate_compliance(
            measurement=measurement,
            device=device,
            test_criteria=criteria,
            operational_freq_min=device.operational_freq_min,
            operational_freq_max=device.operational_freq_max
        )
        
        return results
    
    def evaluate_all_measurements(
        self,
        device_id: UUID,
        test_type: str,
        test_stage: str
    ) -> Dict[UUID, List[TestResult]]:
        """
        Evaluate ALL measurements for a device/test_type/test_stage.
        
        This method evaluates all measurements at once (all temperatures,
        all paths). Useful for comprehensive compliance checking across
        all measurement conditions.
        
        Args:
            device_id: UUID of the device
            test_type: Test type name (e.g., "S-Parameters")
            test_stage: Test stage name (e.g., "SIT", "Board-Bring-Up")
            
        Returns:
            Dictionary mapping measurement_id -> List[TestResult]
            Each measurement gets evaluated independently
            
        Raises:
            DeviceNotFoundError: If device doesn't exist
            DatabaseError: If queries fail
        """
        # Get device
        device = self.device_repo.get_by_id(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device with id {device_id} not found")
        
        # Get all measurements for this device/test_type (regardless of test_stage)
        # This allows the same files to be evaluated against different test stage criteria
        # when the user changes the test stage dropdown
        all_measurements = self.measurement_repo.get_by_device(device_id)
        measurements = [m for m in all_measurements if m.test_type == test_type]
        
        # Evaluate each measurement against the specified test_stage criteria
        all_results = {}
        for measurement in measurements:
            results = self.evaluate_compliance(measurement, device, test_stage)
            all_results[measurement.id] = results
        
        return all_results
    
    def save_test_results(self, results: List[TestResult]) -> List[TestResult]:
        """
        Save test results to the database.
        
        Stores all results from compliance evaluation. Each result is saved
        individually. If results already exist for a measurement/criterion,
        they are overwritten (new results replace old ones).
        
        Args:
            results: List of TestResult objects to save
            
        Returns:
            List of saved TestResult objects
            
        Raises:
            DatabaseError: If save operation fails
        """
        saved = []
        for result in results:
            saved.append(self.result_repo.create(result))
        return saved
    
    def save_all_results(
        self,
        results_by_measurement: Dict[UUID, List[TestResult]]
    ) -> Dict[UUID, List[TestResult]]:
        """
        Save all results from batch evaluation.
        
        Convenience method for saving results from evaluate_all_measurements().
        Saves all results for all measurements.
        
        Args:
            results_by_measurement: Dictionary from evaluate_all_measurements()
            
        Returns:
            Dictionary of saved results (same structure as input)
        """
        saved = {}
        for measurement_id, results in results_by_measurement.items():
            saved[measurement_id] = self.save_test_results(results)
        return saved
    
    def get_compliance_results(
        self,
        measurement_id: UUID,
        test_stage: Optional[str] = None
    ) -> List[TestResult]:
        """
        Retrieve compliance results for a measurement.
        
        Primary query method for compliance table display. Gets all results
        for a measurement, optionally filtered by test_stage.
        
        Excludes stale results - they should be recalculated before being used.
        
        Args:
            measurement_id: UUID of the measurement
            test_stage: Optional test stage filter (if None, gets all results)
            
        Returns:
            List of TestResult objects for this measurement (excluding stale results)
            Empty list if no results found
        """
        # Get all results for measurement
        all_results = self.result_repo.get_by_measurement_id(measurement_id)
        
        # Filter out stale results - they need to be recalculated
        fresh_results = [r for r in all_results if not r.is_stale]
        
        # Filter by test_stage if provided
        # Results are linked to criteria via test_criteria_id, and criteria have test_stage
        # So we need to check each result's criteria to filter by test_stage
        if test_stage:
            filtered_results = []
            for result in fresh_results:
                # Get the criterion for this result
                criterion = self.criteria_repo.get_by_id(result.test_criteria_id)
                if criterion and criterion.test_stage == test_stage:
                    filtered_results.append(result)
            return filtered_results
        
        return fresh_results
    
    def delete_results_for_measurement_and_stage(
        self,
        measurement_id: UUID,
        test_stage: str
    ) -> None:
        """
        Delete all results for a measurement/test_stage combination.
        
        Used when re-evaluating compliance for a new test stage to ensure
        old results are removed before saving new ones. Prevents duplicates
        and guarantees the compliance table reflects fresh calculations.
        
        Args:
            measurement_id: Measurement whose results should be cleared
            test_stage: Test stage whose results should be removed
        """
        results_to_delete = self.get_compliance_results(
            measurement_id,
            test_stage=test_stage
        )
        
        for result in results_to_delete:
            self.result_repo.delete(result.id)
    
    def get_overall_pass_status(self, measurement_id: UUID) -> bool:
        """
        Get overall pass/fail status for a measurement.
        
        Aggregates all results for a measurement. Returns True only if ALL
        results pass. If any result fails, overall status is False.
        
        Args:
            measurement_id: UUID of the measurement
            
        Returns:
            True if all results pass, False if any result fails
            Returns True if no results found (nothing to fail)
        """
        results = self.result_repo.get_by_measurement_id(measurement_id)
        
        if not results:
            return True  # No results = nothing to fail
        
        # All results must pass for overall pass
        return all(result.passed for result in results)
    
    def get_overall_pass_status_for_all_measurements(
        self,
        measurement_ids: List[UUID]
    ) -> Dict[UUID, bool]:
        """
        Get overall pass/fail status for multiple measurements.
        
        Convenience method for checking pass status across all measurements
        for a device/test_stage combination.
        
        Args:
            measurement_ids: List of measurement UUIDs
            
        Returns:
            Dictionary mapping measurement_id -> pass_status (bool)
        """
        statuses = {}
        for measurement_id in measurement_ids:
            statuses[measurement_id] = self.get_overall_pass_status(measurement_id)
        return statuses
    
    def mark_results_stale_for_criteria(self, criteria_id: UUID) -> int:
        """
        Mark all test results for a criterion as stale.
        
        Called when criteria are updated. Marks existing results as stale
        so they can be recalculated before being used for compliance decisions.
        
        Args:
            criteria_id: UUID of the criterion
            
        Returns:
            Number of results marked as stale
        """
        return self.result_repo.mark_as_stale_by_criteria(criteria_id)
    
    def delete_stale_results(self, measurement_id: UUID) -> int:
        """
        Delete stale results for a measurement.
        
        Used before recalculating compliance to remove old results that
        are no longer valid (criteria changed).
        
        Args:
            measurement_id: UUID of the measurement
            
        Returns:
            Number of results deleted
        """
        # Get all results for measurement
        results = self.result_repo.get_by_measurement_id(measurement_id)
        
        # Delete stale ones
        count = 0
        for result in results:
            if result.is_stale:
                self.result_repo.delete(result.id)
                count += 1
        
        return count

