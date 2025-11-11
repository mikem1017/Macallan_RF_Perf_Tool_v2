"""
Measurement service for file loading and measurement management.

This module provides the MeasurementService, which handles loading Touchstone
files, parsing metadata, validating against device configuration, and storing
measurements. It orchestrates the interaction between TouchstoneLoader,
FilenameParser, and MeasurementRepository.

Key responsibilities:
- Load and parse Touchstone files
- Validate file metadata against device (part number matching)
- Handle multiple file loading (2 or 4 files per temperature)
- Serialize Network objects for database storage
- Coordinate file loading workflow

Design principle: Device must be selected BEFORE files are loaded.
The service validates that files match the selected device but allows
user to proceed even if part numbers don't match (with warning).
"""

from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from pathlib import Path

from ..models.device import Device
from ..models.measurement import Measurement
from ..repositories.measurement_repository import MeasurementRepository
from ..repositories.device_repository import DeviceRepository
from ..rf_data.touchstone_loader import TouchstoneLoader
from ..rf_data.filename_parser import FilenameParser
from ..exceptions import FileLoadError, ValidationError, DeviceNotFoundError


class MeasurementService:
    """
    Service for measurement file loading and management.
    
    Handles the complete workflow of loading Touchstone files:
    1. Parse filename for metadata
    2. Load Touchstone data using scikit-rf
    3. Validate against selected device
    4. Create Measurement objects
    5. Store in database
    
    Key design:
    - Device must be selected before files are loaded
    - Validates part number match but allows user to proceed with warning
    - Validates multiple files have consistent metadata (serial number, temperature)
    - Handles 2 or 4 files per temperature based on Multi-Gain-Mode
    """
    
    def __init__(
        self,
        measurement_repository: MeasurementRepository,
        device_repository: DeviceRepository,
        touchstone_loader: Optional[TouchstoneLoader] = None,
        filename_parser: Optional[FilenameParser] = None
    ):
        """
        Initialize measurement service with dependencies.
        
        Args:
            measurement_repository: Repository for measurement storage
            device_repository: Repository for device lookup/validation
            touchstone_loader: Optional - creates default if not provided
            filename_parser: Optional - creates default if not provided
        """
        self.measurement_repo = measurement_repository
        self.device_repo = device_repository
        self.loader = touchstone_loader or TouchstoneLoader()
        self.parser = filename_parser or FilenameParser()
    
    def load_measurement_file(
        self,
        filepath: Path,
        device: Device,
        test_stage: str
    ) -> Tuple[Measurement, Optional[str]]:
        """
        Load a single Touchstone file and create Measurement object.
        
        This method:
        1. Loads the Touchstone file using scikit-rf
        2. Parses filename metadata
        3. Validates part number matches device (warns if mismatch)
        4. Creates Measurement object with all metadata
        
        Note: Measurement is NOT saved to database - caller must call save_measurement().
        This allows caller to validate multiple files before saving.
        
        Args:
            filepath: Path to the Touchstone file
            device: Device object (must be selected before loading)
            test_stage: Test stage (user-selected, not from filename)
            
        Returns:
            Tuple of (Measurement object, warning_message)
            - Measurement: Created measurement (not yet saved)
            - warning_message: Optional warning if part number doesn't match
                            None if everything matches
            
        Raises:
            FileLoadError: If file cannot be loaded or parsed
            DeviceNotFoundError: If device doesn't exist in database
        """
        # Verify device exists
        existing_device = self.device_repo.get_by_id(device.id)
        if existing_device is None:
            raise DeviceNotFoundError(f"Device with id {device.id} not found")
        
        # Load Touchstone file and parse metadata
        network, metadata = self.loader.load_with_metadata(filepath)
        
        # Validate part number match (warn but don't block)
        warning_message = None
        filename_part_number = metadata.get("part_number")
        if filename_part_number and filename_part_number != device.part_number:
            warning_message = (
                f"Part number in filename ({filename_part_number}) does not match "
                f"selected device part number ({device.part_number}). "
                f"Proceeding anyway - user may override."
            )
        
        # Create Measurement object
        measurement = Measurement(
            device_id=device.id,
            serial_number=metadata["serial_number"],
            test_type=metadata.get("test_type", "S-Parameters"),  # Default if not parsed
            test_stage=test_stage,  # User-selected, not from filename
            temperature=metadata["temperature"],
            path_type=metadata["path_type"],
            file_path=metadata["file_path"],
            measurement_date=metadata["date"],
            touchstone_data=network,  # Network object (will be serialized on save)
            metadata=metadata  # Store all parsed metadata
        )
        
        return measurement, warning_message
    
    def load_multiple_files(
        self,
        filepaths: List[Path],
        device: Device,
        test_stage: str,
        temperature: str
    ) -> Tuple[List[Measurement], List[str]]:
        """
        Load multiple Touchstone files (2 or 4 files per temperature).
        
        Validates that all files have:
        - Same serial number
        - Same temperature (matches provided temperature parameter)
        
        If mismatches found, raises error but allows user to proceed (flag/warn).
        Returns list of warnings for each mismatch.
        
        Expected file counts:
        - 2 files: PRI and RED (standard mode)
        - 4 files: PRI_HG, PRI_LG, RED_HG, RED_LG (multi-gain mode)
        
        Args:
            filepaths: List of paths to Touchstone files (2 or 4 files)
            device: Device object (must be selected before loading)
            test_stage: Test stage (user-selected)
            temperature: Temperature condition (AMB, HOT, or COLD)
                         Used to validate files match this temperature
            
        Returns:
            Tuple of (List[Measurement], List[str] warnings)
            - Measurements: List of created Measurement objects (not yet saved)
            - warnings: List of warning messages for any validation issues
            
        Raises:
            FileLoadError: If files cannot be loaded
            ValidationError: If file count is invalid (not 2 or 4)
            DeviceNotFoundError: If device doesn't exist
        """
        # Validate file count
        if len(filepaths) not in [2, 4]:
            raise ValidationError(
                f"Expected 2 or 4 files (got {len(filepaths)}). "
                f"Standard mode: 2 files (PRI, RED). "
                f"Multi-Gain mode: 4 files (PRI_HG, PRI_LG, RED_HG, RED_LG)."
            )
        
        # Validate file count matches device mode
        if device.multi_gain_mode and len(filepaths) != 4:
            raise ValidationError(
                f"Device has Multi-Gain-Mode enabled but only {len(filepaths)} files provided. "
                f"Expected 4 files (PRI_HG, PRI_LG, RED_HG, RED_LG)."
            )
        elif not device.multi_gain_mode and len(filepaths) != 2:
            raise ValidationError(
                f"Device does not have Multi-Gain-Mode but {len(filepaths)} files provided. "
                f"Expected 2 files (PRI, RED)."
            )
        
        measurements = []
        warnings = []
        
        # Load each file
        serial_numbers = set()
        temperatures = set()
        
        for filepath in filepaths:
            measurement, warning = self.load_measurement_file(filepath, device, test_stage)
            
            # Override temperature with the parameter value (user-selected)
            # This ensures HOT/COLD files are correctly tagged even if filename doesn't contain temperature
            measurement.temperature = temperature
            
            if warning:
                warnings.append(warning)
            
            # Track serial numbers and temperatures for validation
            serial_numbers.add(measurement.serial_number)
            temperatures.add(measurement.temperature)
            
            measurements.append(measurement)
        
        # Validate all files have same serial number
        if len(serial_numbers) > 1:
            warning_msg = (
                f"Files have mismatched serial numbers: {serial_numbers}. "
                f"All files should be for the same unit. Proceeding anyway."
            )
            warnings.append(warning_msg)
        
        # Validate all files have same temperature (and match provided temperature)
        if len(temperatures) > 1:
            warning_msg = (
                f"Files have mismatched temperatures: {temperatures}. "
                f"Expected temperature: {temperature}. Proceeding anyway."
            )
            warnings.append(warning_msg)
        elif temperatures and temperature not in temperatures:
            warning_msg = (
                f"File temperature ({temperatures.pop()}) does not match "
                f"selected temperature ({temperature}). Proceeding anyway."
            )
            warnings.append(warning_msg)
        
        return measurements, warnings
    
    def save_measurement(self, measurement: Measurement) -> Measurement:
        """
        Save a measurement to the database.
        
        Serializes the Network object to bytes (BLOB) before storing.
        The measurement_repository handles the serialization automatically.
        
        Args:
            measurement: Measurement object to save (ID may be auto-generated)
            
        Returns:
            Saved Measurement object (same object, unchanged)
            
        Raises:
            DatabaseError: If save operation fails
        """
        return self.measurement_repo.create(measurement)
    
    def save_multiple_measurements(self, measurements: List[Measurement]) -> List[Measurement]:
        """
        Save multiple measurements to the database.
        
        Convenience method for saving a batch of measurements (e.g., from
        load_multiple_files). Each measurement is saved individually.
        
        Args:
            measurements: List of Measurement objects to save
            
        Returns:
            List of saved Measurement objects
            
        Raises:
            DatabaseError: If any save operation fails
        """
        saved = []
        for measurement in measurements:
            saved.append(self.save_measurement(measurement))
        return saved
    
    def get_measurements_for_device(
        self,
        device_id: UUID,
        test_type: str,
        test_stage: str
    ) -> List[Measurement]:
        """
        Get measurements for a device, test type, and test stage.
        
        Primary query method for Test Setup screen. Retrieves all measurements
        that have been loaded for the selected device/test_type/test_stage.
        
        Args:
            device_id: UUID of the device
            test_type: Test type name (e.g., "S-Parameters")
            test_stage: Test stage name (e.g., "SIT", "Board-Bring-Up")
            
        Returns:
            List of Measurement objects, ordered by temperature, path_type
            Empty list if no measurements loaded yet
        """
        return self.measurement_repo.get_by_device_and_test_stage(
            device_id, test_type, test_stage
        )
    
    def validate_part_number_match(
        self,
        filename_part_number: str,
        device_part_number: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that part number from filename matches device part number.
        
        Helper method for validation logic. Returns match status and optional
        warning message. Does NOT raise exception - allows caller to decide
        how to handle mismatch.
        
        Args:
            filename_part_number: Part number extracted from filename
            device_part_number: Part number from device configuration
            
        Returns:
            Tuple of (matches: bool, warning_message: Optional[str])
            - matches: True if part numbers match
            - warning_message: Warning message if mismatch, None if match
        """
        if filename_part_number != device_part_number:
            warning = (
                f"Part number mismatch: filename has {filename_part_number}, "
                f"device has {device_part_number}"
            )
            return False, warning
        
        return True, None



