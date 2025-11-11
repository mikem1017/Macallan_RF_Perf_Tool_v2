"""
Background worker for compliance re-evaluation.

When test stage changes, compliance needs to be re-evaluated with new criteria.
This happens in the background to keep UI responsive.
"""

from typing import List, Dict
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from ....core.models.device import Device
from ....core.models.measurement import Measurement
from ...utils.service_factory import create_services_for_thread


class ComplianceEvaluationWorker(QThread):
    """
    Background worker for re-evaluating compliance.
    
    Used when test stage changes - re-evaluates all session measurements
    with new criteria in the background.
    
    Creates its own database connection and services for thread safety.
    """
    evaluation_complete = Signal(object)  # Dict[UUID, List[TestResult]]
    error_occurred = Signal(str)
    
    def __init__(
        self,
        database_path: Path,
        measurements: List[Measurement],
        device: Device,
        test_stage: str
    ):
        super().__init__()
        self.database_path = database_path
        self.measurements = measurements
        self.device = device
        self.test_stage = test_stage
    
    def run(self):
        """Execute compliance re-evaluation in background thread."""
        try:
            # Create thread-local services with new database connection
            # SQLite connections cannot be shared across threads
            _, _, compliance_service = create_services_for_thread(self.database_path)
            
            results_by_measurement: Dict = {}
            print(f"[ComplianceEvaluationWorker] Starting stage {self.test_stage} for {len(self.measurements)} measurements")
            
            # Re-evaluate all measurements with new test stage criteria
            for measurement in self.measurements:
                print(f"[ComplianceEvaluationWorker] Evaluating measurement {measurement.id} ({measurement.temperature} {measurement.path_type})")
                # Remove existing results for this measurement/stage before recalculating
                compliance_service.delete_results_for_measurement_and_stage(
                    measurement.id,
                    self.test_stage
                )
                
                results = compliance_service.evaluate_compliance(
                    measurement,
                    self.device,
                    self.test_stage
                )
                if results:
                    compliance_service.save_test_results(results)
                results_by_measurement[measurement.id] = results
                print(f"[ComplianceEvaluationWorker] Measurement {measurement.id} -> {len(results) if results else 0} results saved")
            
            # Signal completion
            print(f"[ComplianceEvaluationWorker] Completed stage {self.test_stage}")
            self.evaluation_complete.emit(results_by_measurement)
            
        except Exception as e:
            import traceback
            error_msg = f"Error re-evaluating compliance: {e}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)


