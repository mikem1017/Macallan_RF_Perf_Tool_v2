"""
Device service for business logic operations.

This module provides the DeviceService, which orchestrates device and test
criteria management. It uses dependency injection to receive repositories,
enabling easy testing and flexibility.

The service handles:
- Device CRUD operations with validation
- Test criteria management (add, update, delete)
- Relationship management (deleting device requires checking related data)
- Stale result marking when criteria change

All operations go through the service layer, which provides business logic
validation and error handling before delegating to repositories.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models.device import Device
from ..models.test_criteria import TestCriteria
from ..repositories.device_repository import DeviceRepository
from ..repositories.test_criteria_repository import TestCriteriaRepository
from ..repositories.measurement_repository import MeasurementRepository
from ..repositories.test_result_repository import TestResultRepository
from ..exceptions import DeviceNotFoundError, ValidationError, DatabaseError


class DeviceService:
    """
    Service for device and test criteria management.
    
    Provides high-level operations for device CRUD and test criteria management.
    Uses dependency injection to receive repositories, enabling easy testing
    and swapping implementations.
    
    Key responsibilities:
    - Validate business rules before repository operations
    - Coordinate multi-step operations (e.g., delete device and related data)
    - Mark test results as stale when criteria change
    - Provide information about related data for deletion confirmation
    """
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        criteria_repository: TestCriteriaRepository,
        measurement_repository: Optional[MeasurementRepository] = None,
        result_repository: Optional[TestResultRepository] = None
    ):
        """
        Initialize device service with dependencies.
        
        Args:
            device_repository: Repository for device operations
            criteria_repository: Repository for test criteria operations
            measurement_repository: Optional - used for checking related data
            result_repository: Optional - used for marking stale results
            
        Raises:
            ValueError: If device_repository or criteria_repository is None
        """
        if device_repository is None:
            raise ValueError("DeviceService requires device_repository (cannot be None)")
        if criteria_repository is None:
            raise ValueError("DeviceService requires criteria_repository (cannot be None)")
        
        self.device_repo = device_repository
        self.criteria_repo = criteria_repository
        self.measurement_repo = measurement_repository
        self.result_repo = result_repository
        
        # Verify criteria_repo has the required method
        if not hasattr(self.criteria_repo, 'get_by_device_and_test'):
            raise ValueError(
                f"criteria_repository must have get_by_device_and_test method, "
                f"but got {type(self.criteria_repo)}"
            )
    
    def create_device(self, device: Device) -> Device:
        """
        Create a new device.
        
        Validates device model (Pydantic handles validation) and creates
        in database. Device ID is auto-generated if not provided.
        
        Args:
            device: Device object to create
            
        Returns:
            Created Device object
            
        Raises:
            ValidationError: If device validation fails (from Pydantic)
            DatabaseError: If database operation fails
        """
        # Validation is handled by Pydantic model
        # Repository will raise DatabaseError if operation fails
        return self.device_repo.create(device)
    
    def get_device(self, device_id: UUID) -> Optional[Device]:
        """
        Get a device by ID.
        
        Args:
            device_id: UUID of the device
            
        Returns:
            Device object if found, None otherwise
        """
        return self.device_repo.get_by_id(device_id)
    
    def get_all_devices(self) -> List[Device]:
        """
        Get all devices.
        
        Returns:
            List of all Device objects, ordered by name
        """
        return self.device_repo.get_all()
    
    def update_device(self, device: Device) -> Device:
        """
        Update an existing device.
        
        Validates device model and updates in database.
        
        Args:
            device: Device object to update (must have valid ID)
            
        Returns:
            Updated Device object
            
        Raises:
            DeviceNotFoundError: If device doesn't exist
            ValidationError: If device validation fails
            DatabaseError: If database operation fails
        """
        # Validation is handled by Pydantic model
        return self.device_repo.update(device)
    
    def get_deletion_info(self, device_id: UUID) -> Dict[str, Any]:
        """
        Get information about related data for device deletion.
        
        Returns information about measurements and criteria that would be
        deleted if the device is deleted. Used for user confirmation in GUI.
        
        Note: Does NOT delete the device - only provides information.
        
        Args:
            device_id: UUID of the device to check
            
        Returns:
            Dictionary with:
            - device: Device object (if found)
            - criteria_count: Number of test criteria
            - measurement_count: Number of measurements (if measurement_repo available)
            - has_related_data: True if any related data exists
            
        Raises:
            DeviceNotFoundError: If device doesn't exist
        """
        device = self.device_repo.get_by_id(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device with id {device_id} not found")
        
        # Get count of criteria for this device
        # Get all criteria and filter by device_id (since get_by_device_and_test requires test_type/test_stage)
        all_criteria_for_device = [
            c for c in self.criteria_repo.get_all()
            if c.device_id == device_id
        ]
        criteria_count = len(all_criteria_for_device)
        
        # Get count of measurements if repository available
        measurement_count = 0
        if self.measurement_repo:
            measurements = self.measurement_repo.get_by_device(device_id)
            measurement_count = len(measurements)
        
        return {
            "device": device,
            "criteria_count": criteria_count,
            "measurement_count": measurement_count,
            "has_related_data": criteria_count > 0 or measurement_count > 0
        }
    
    def delete_device(self, device_id: UUID) -> None:
        """
        Delete a device.
        
        Note: Due to foreign key CASCADE constraints, deleting a device will
        automatically delete all associated test criteria and measurements.
        However, this method does NOT check for related data - that should
        be done via get_deletion_info() before calling this method.
        
        Args:
            device_id: UUID of the device to delete
            
        Raises:
            DeviceNotFoundError: If device doesn't exist
            DatabaseError: If deletion fails
        """
        # Repository will raise DeviceNotFoundError if device doesn't exist
        # CASCADE will handle deletion of related criteria and measurements
        self.device_repo.delete(device_id)
    
    def get_criteria_for_device(
        self,
        device_id: UUID,
        test_type: str,
        test_stage: str
    ) -> List[TestCriteria]:
        """
        Get test criteria for a device, test type, and test stage.
        
        Primary query method for Test Setup screen. Retrieves all criteria
        that apply to the selected device/test_type/test_stage combination.
        
        Args:
            device_id: UUID of the device
            test_type: Test type name (e.g., "S-Parameters")
            test_stage: Test stage name (e.g., "SIT", "Board-Bring-Up")
            
        Returns:
            List of TestCriteria objects for this combination
            Empty list if no criteria defined yet
            
        Raises:
            ValueError: If criteria_repo is not initialized
        """
        if self.criteria_repo is None:
            raise ValueError("DeviceService.criteria_repo is not initialized. Cannot get criteria.")
        return self.criteria_repo.get_by_device_and_test(
            device_id, test_type, test_stage
        )
    
    def add_criteria(self, criteria: TestCriteria) -> TestCriteria:
        """
        Add new test criteria.
        
        Validates criteria model and creates in database. Criteria ID is
        auto-generated if not provided.
        
        Args:
            criteria: TestCriteria object to create
            
        Returns:
            Created TestCriteria object
            
        Raises:
            ValidationError: If criteria validation fails
            DatabaseError: If database operation fails
        """
        # Validation is handled by Pydantic model
        return self.criteria_repo.create(criteria)
    
    def update_criteria(self, criteria: TestCriteria) -> TestCriteria:
        """
        Update existing test criteria.
        
        When criteria are updated, marks all associated test results as stale
        so they can be recalculated.
        
        Args:
            criteria: TestCriteria object to update (must have valid ID)
            
        Returns:
            Updated TestCriteria object
            
        Raises:
            ValidationError: If criteria validation fails
            DatabaseError: If database operation fails
        """
        # Update criteria
        updated = self.criteria_repo.update(criteria)
        
        # Mark associated test results as stale
        if self.result_repo:
            self.result_repo.mark_as_stale_by_criteria(criteria.id)
        
        return updated
    
    def delete_criteria(self, criteria_id: UUID) -> None:
        """
        Delete test criteria.
        
        Due to CASCADE constraints, deleting criteria will automatically
        delete all associated test results.
        
        Args:
            criteria_id: UUID of the criteria to delete
            
        Raises:
            DatabaseError: If deletion fails
        """
        self.criteria_repo.delete(criteria_id)
    
    def mark_results_stale_for_criteria(self, criteria_id: UUID) -> int:
        """
        Mark all test results for a criterion as stale.
        
        Called when criteria are updated to indicate that existing results
        need to be recalculated.
        
        Args:
            criteria_id: UUID of the criterion
            
        Returns:
            Number of results marked as stale
            
        Raises:
            DatabaseError: If operation fails
        """
        if not self.result_repo:
            raise DatabaseError("Result repository not available")
        
        return self.result_repo.mark_as_stale_by_criteria(criteria_id)

