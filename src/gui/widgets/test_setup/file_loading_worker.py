"""
Background worker for file loading operations.

All file loading, parsing, and compliance evaluation happens here.
The GUI only displays results.
"""

from typing import List, Tuple
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from ....core.models.device import Device
from ....core.models.measurement import Measurement
from ...utils.service_factory import create_services_for_thread


class FileLoadingWorker(QThread):
    """
    Background worker for loading files and evaluating compliance.
    
    All heavy processing happens here:
    - File loading and parsing
    - Metadata extraction
    - Network deserialization
    - Compliance evaluation
    - Database saving
    
    Creates its own database connection and services for thread safety.
    """
    files_loaded = Signal(object, object)  # (measurements: List[Measurement], warnings: List[str])
    error_occurred = Signal(str)
    
    def __init__(
        self,
        database_path: Path,
        file_paths: List[Path],
        device: Device,
        test_stage: str,
        temperature: str
    ):
        super().__init__()
        self.database_path = database_path
        self.file_paths = file_paths
        self.device = device
        self.test_stage = test_stage
        self.temperature = temperature
    
    def run(self):
        """Execute file loading and compliance evaluation in background thread."""
        try:
            # Create thread-local services with new database connection
            # SQLite connections cannot be shared across threads
            _, measurement_service, compliance_service = create_services_for_thread(self.database_path)
            
            # Load files (includes parsing, metadata extraction, validation)
            measurements, warnings = measurement_service.load_multiple_files(
                self.file_paths,
                self.device,
                self.test_stage,
                self.temperature
            )
            
            # Save measurements to database
            measurement_service.save_multiple_measurements(measurements)
            
            # Evaluate compliance for all measurements (heavy processing)
            for measurement in measurements:
                results = compliance_service.evaluate_compliance(
                    measurement,
                    self.device,
                    self.test_stage
                )
                if results:
                    compliance_service.save_test_results(results)
            
            # Emit success signal with measurements and warnings
            self.files_loaded.emit(measurements, warnings)
            
        except Exception as e:
            import traceback
            error_msg = f"Error loading files: {e}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)

