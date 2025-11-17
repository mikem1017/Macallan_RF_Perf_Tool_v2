"""
Test Setup tab for main window.

This module provides the Test Setup tab where users select devices,
load measurement files, and view compliance results.
"""

from typing import Optional, Dict, List
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTabWidget, QGroupBox, QLabel, QFileDialog, QApplication, QSizePolicy
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve

from .compliance_table_widget import ComplianceTableWidget
from .file_loading_worker import FileLoadingWorker
from .compliance_evaluation_worker import ComplianceEvaluationWorker
from ....core.models.device import Device
from ....core.models.measurement import Measurement
from ....core.test_stages import TEST_STAGES, get_test_stage_display_name
from ....core.services.device_service import DeviceService
from ....core.services.measurement_service import MeasurementService
from ....core.services.compliance_service import ComplianceService
from ...utils.error_handler import handle_exception, StatusBarMessage


class TestSetupTab(QWidget):
    """
    Test Setup tab widget.
    
    Provides device selection, test stage selection, file loading,
    and compliance table display.
    """
    
    # Signal emitted when device changes
    device_changed = pyqtSignal()
    
    # Signal emitted when measurements are loaded or cleared
    measurements_loaded = pyqtSignal()
    
    def __init__(
        self,
        device_service: DeviceService,
        measurement_service: MeasurementService,
        compliance_service: ComplianceService,
        database_path: Path,
        status_bar,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize test setup tab.
        
        Args:
            device_service: DeviceService instance
            measurement_service: MeasurementService instance
            compliance_service: ComplianceService instance
            database_path: Path to database file (for worker threads)
            status_bar: QStatusBar for showing warnings
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.device_service = device_service
        self.measurement_service = measurement_service
        self.compliance_service = compliance_service
        self.database_path = database_path
        self.status_bar = status_bar
        
        self.current_device: Optional[Device] = None
        self.current_test_stage = TEST_STAGES[0]  # Default to first stage
        
        # Store file display widgets for each temperature (keyed by test_type and temperature)
        self.file_display_widgets: Dict[str, Dict[str, QLabel]] = {}  # {test_type: {temperature: QLabel}}
        
        # Track measurements loaded in current session (only show these in compliance table)
        self.session_measurements: List[Measurement] = []
        
        # Background workers
        self.file_loading_worker: Optional[FileLoadingWorker] = None
        self.compliance_evaluation_worker: Optional[ComplianceEvaluationWorker] = None
        
        self._setup_ui()
            # Ensure everything starts cleared BEFORE populating device list
        self.compliance_table.clear()
        self._clear_file_displays()
        self.test_type_tabs.clear()
        self.session_measurements.clear()  # Clear session measurements
        # Now populate device list (this will also clear everything in finally block)
        self.refresh_device_list()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Top controls
        controls_group = QGroupBox("Test Setup")
        controls_layout = QVBoxLayout()
        
        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        # Use currentIndexChanged with blocking to prevent auto-trigger on population
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self.device_combo)
        device_layout.addStretch()
        controls_layout.addLayout(device_layout)
        
        # Test stage selection
        stage_layout = QHBoxLayout()
        stage_layout.addWidget(QLabel("Test Stage:"))
        self.stage_combo = QComboBox()
        for stage in TEST_STAGES:
            self.stage_combo.addItem(get_test_stage_display_name(stage), stage)
        # Block signals during initial setup to prevent auto-trigger
        self.stage_combo.blockSignals(True)
        self.stage_combo.setCurrentIndex(0)  # Set default without triggering
        self.stage_combo.blockSignals(False)
        self.stage_combo.currentIndexChanged.connect(self._on_test_stage_changed)
        stage_layout.addWidget(self.stage_combo)
        stage_layout.addStretch()
        controls_layout.addLayout(stage_layout)
        
        # Clear All Data button
        clear_layout = QHBoxLayout()
        clear_button = QPushButton("Clear All Data")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        clear_button.clicked.connect(self._clear_all_data)
        clear_layout.addWidget(clear_button)
        clear_layout.addStretch()
        controls_layout.addLayout(clear_layout)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Test type tabs (will be populated when device is selected)
        self.test_type_tabs = QTabWidget()
        layout.addWidget(self.test_type_tabs)
        
        # Compliance table
        compliance_group = QGroupBox("Compliance Results")
        compliance_layout = QVBoxLayout()
        self.compliance_table = ComplianceTableWidget(
            self.compliance_service,
            self.status_bar
        )
        compliance_layout.addWidget(self.compliance_table)
        compliance_group.setLayout(compliance_layout)
        # Make compliance table expand to fill available space
        compliance_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(compliance_group, stretch=1)  # Add stretch factor to make it expand
    
    def refresh_device_list(self) -> None:
        """Refresh the device combo box."""
        # Block signals during population to prevent auto-selection
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        
        # Clear everything BEFORE adding items
        self.current_device = None
        self.compliance_table.clear()
        self._clear_file_displays()
        self.test_type_tabs.clear()
        
        try:
            devices = self.device_service.get_all_devices()
            for device in devices:
                self.device_combo.addItem(f"{device.name} ({device.part_number})", device.id)
        except Exception as e:
            handle_exception(self, e, "Loading devices")
        finally:
            # Ensure index is -1 (nothing selected) WHILE signals are still blocked
            # This prevents any signal from firing
            self.device_combo.setCurrentIndex(-1)
            # Verify it's actually -1
            if self.device_combo.currentIndex() != -1:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Combo box index is {self.device_combo.currentIndex()} instead of -1, forcing to -1")
                self.device_combo.setCurrentIndex(-1)
            # Now unblock signals - any future USER selection will trigger updates
            self.device_combo.blockSignals(False)
    
    def _on_device_changed(self) -> None:
        """Handle device selection change."""
        # Get current index and data
        current_index = self.device_combo.currentIndex()
        device_id = self.device_combo.currentData()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[Device Changed] Signal fired: index={current_index}, device_id={device_id}")
        
        # Explicitly check: if index is -1 or device_id is None/empty, clear everything
        if current_index < 0 or not device_id:
            logger.debug("[Device Changed] No device selected - clearing everything")
            self.current_device = None
            self.test_type_tabs.clear()
            self.session_measurements.clear()  # Clear session measurements
            self.measurements_loaded.emit()  # Signal that measurements were cleared
            self._update_compliance_table()
            return
        
        # We have a valid device selection - load it
        try:
            logger.debug(f"[Device Changed] Loading device with ID: {device_id}")
            
            # Clear ALL data when device changes (same as Clear button)
            self._clear_all_data(silent=True)
            
            self.current_device = self.device_service.get_device(device_id)
            if self.current_device:
                logger.debug(f"[Device Changed] Device loaded: {self.current_device.name}, tests_performed: {self.current_device.tests_performed}")
                logger.debug(f"[Device Changed] Calling _update_test_type_tabs()...")
                self._update_test_type_tabs()
                logger.debug(f"[Device Changed] Tabs created, count: {self.test_type_tabs.count()}")
                self._update_file_loaders()
                # Ensure compliance table is cleared (should already be, but double-check)
                self._update_compliance_table()
                # Don't auto-load compliance data or metadata - user must load files explicitly
                self.device_changed.emit()
            else:
                logger.warning(f"[Device Changed] Device {device_id} not found in database")
                self.current_device = None
                self.test_type_tabs.clear()
                self._update_compliance_table()
        except Exception as e:
            import traceback
            logger.error(f"[Device Changed] Error: {e}\n{traceback.format_exc()}")
            handle_exception(self, e, "Loading device")
            self.current_device = None
            self.test_type_tabs.clear()
            self._update_compliance_table()
    
    def _on_test_stage_changed(self) -> None:
        """Handle test stage selection change."""
        self.current_test_stage = self.stage_combo.currentData()
        self._update_file_loaders()
        # Update compliance table with existing measurements using new test stage criteria
        # (different criteria = different pass/fail, but don't reload metadata)
        self._update_compliance_table()
    
    def _update_test_type_tabs(self) -> None:
        """Update test type tabs based on current device."""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[Update Tabs] Starting - current_device={self.current_device}")
        
        self.test_type_tabs.clear()
        # Clear old widget references when tabs are cleared
        self.file_display_widgets.clear()
        
        if not self.current_device:
            logger.debug("[Update Tabs] No current device, returning early")
            return
        
        # Debug: Check if device has tests_performed
        logger.debug(f"[Update Tabs] Device: {self.current_device.name}, tests_performed: {self.current_device.tests_performed}")
        
        # Get test types - use device's tests_performed or default to S-Parameters
        test_types = self.current_device.tests_performed if self.current_device.tests_performed else ["S-Parameters"]
        
        if not test_types:
            logger.warning(f"[Update Tabs] Device {self.current_device.name} has no tests_performed and no default")
            return
        
        logger.debug(f"[Update Tabs] Creating tabs for test types: {test_types}")
        
        # Create a tab for each test type
        for test_type in test_types:
            logger.debug(f"[Update Tabs] Creating tab for: {test_type}")
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            
            # File loader buttons (collapsible shelf)
            # Create a collapsible frame with a clickable header button
            file_container = QWidget()
            file_container_layout = QVBoxLayout(file_container)
            file_container_layout.setContentsMargins(0, 0, 0, 0)
            file_container_layout.setSpacing(0)
            # Allow container to shrink when content collapses
            file_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            
            # Create header button that toggles collapse/expand
            header_button = QPushButton("Load Measurement Files ▼")
            header_button.setCheckable(False)
            header_button.setFlat(False)
            header_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    font-weight: bold;
                    border: 1px solid #666;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #444;
                }
            """)
            file_container_layout.addWidget(header_button)
            
            # Create the content widget for the file loaders
            file_content = QWidget()
            file_layout = QVBoxLayout(file_content)
            file_layout.setContentsMargins(10, 10, 10, 10)
            file_layout.setSpacing(5)
            
            # Initialize file display widgets dictionary for this test type
            if test_type not in self.file_display_widgets:
                self.file_display_widgets[test_type] = {}
            
            # Ambient
            amb_layout = QHBoxLayout()
            amb_layout.addWidget(QLabel("Ambient:"))
            amb_button = QPushButton("Load Ambient Files")
            # Use a closure to properly capture the temperature value
            amb_button.clicked.connect(lambda checked, t="AMB": self._load_files(t))
            amb_layout.addWidget(amb_button)
            amb_layout.addStretch()
            file_layout.addLayout(amb_layout)
            
            # Ambient file display
            amb_display = QLabel()
            amb_display.setWordWrap(True)
            amb_display.setStyleSheet("color: rgb(128, 128, 128); font-style: italic;")
            file_layout.addWidget(amb_display)
            self.file_display_widgets[test_type]["AMB"] = amb_display
            
            # Hot
            hot_layout = QHBoxLayout()
            hot_layout.addWidget(QLabel("Hot:"))
            hot_button = QPushButton("Load Hot Files")
            # Use a closure to properly capture the temperature value
            hot_button.clicked.connect(lambda checked, t="HOT": self._load_files(t))
            hot_layout.addWidget(hot_button)
            hot_layout.addStretch()
            file_layout.addLayout(hot_layout)
            
            # Hot file display
            hot_display = QLabel()
            hot_display.setWordWrap(True)
            hot_display.setStyleSheet("color: rgb(128, 128, 128); font-style: italic;")
            file_layout.addWidget(hot_display)
            self.file_display_widgets[test_type]["HOT"] = hot_display
            
            # Cold
            cold_layout = QHBoxLayout()
            cold_layout.addWidget(QLabel("Cold:"))
            cold_button = QPushButton("Load Cold Files")
            # Use a closure to properly capture the temperature value
            cold_button.clicked.connect(lambda checked, t="COLD": self._load_files(t))
            cold_layout.addWidget(cold_button)
            cold_layout.addStretch()
            file_layout.addLayout(cold_layout)
            
            # Cold file display
            cold_display = QLabel()
            cold_display.setWordWrap(True)
            cold_display.setStyleSheet("color: rgb(128, 128, 128); font-style: italic;")
            file_layout.addWidget(cold_display)
            self.file_display_widgets[test_type]["COLD"] = cold_display
            
            # Add content to container
            file_container_layout.addWidget(file_content)
            
            # Simple state tracking
            collapse_state = {"is_collapsed": True}
            
            # Start collapsed - set height to 0 to reclaim space
            file_content.setMaximumHeight(0)
            file_content.setMinimumHeight(0)
            
            # Connect header button to toggle collapse/expand
            def toggle_collapse():
                if collapse_state["is_collapsed"]:
                    # Expanding - allow natural size
                    header_button.setText("Load Measurement Files ▼")
                    file_content.setMaximumHeight(16777215)
                    file_content.setMinimumHeight(0)
                    collapse_state["is_collapsed"] = False
                else:
                    # Collapsing - set height to 0
                    header_button.setText("Load Measurement Files ▶")
                    file_content.setMaximumHeight(0)
                    file_content.setMinimumHeight(0)
                    collapse_state["is_collapsed"] = True
                
                # Force layout update to recalculate space
                file_container.updateGeometry()
                file_content.updateGeometry()
                tab_widget.updateGeometry()
                QApplication.processEvents()
            
            header_button.clicked.connect(toggle_collapse)
            # Set initial button text
            header_button.setText("Load Measurement Files ▶")
            
            tab_layout.addWidget(file_container)
            tab_layout.addStretch()
            
            self.test_type_tabs.addTab(tab_widget, test_type)
            logger.debug(f"[Update Tabs] Tab '{test_type}' added, total tabs: {self.test_type_tabs.count()}")
        
        # Don't auto-load file metadata - user must load files explicitly
    
    def _update_file_loaders(self) -> None:
        """Update file loader buttons (placeholder - UI already set up)."""
        pass
    
    def _load_files(self, temperature: str) -> None:
        """Load measurement files for a temperature."""
        if not self.current_device:
            StatusBarMessage.show_warning(
                self.status_bar, "Please select a device first."
            )
            return
        
        # Determine expected file count
        expected_count = 4 if self.current_device.multi_gain_mode else 2
        
        # Open file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            f"Load {temperature} Files",
            "",
            "Touchstone Files (*.s2p *.s3p *.s4p *.s5p *.s6p *.s7p *.s8p *.s9p *.s10p);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        # Validate file count
        if len(file_paths) != expected_count:
            from ...utils.error_handler import show_warning
            show_warning(
                self,
                "Invalid File Count",
                f"Expected {expected_count} files for {'multi-gain' if self.current_device.multi_gain_mode else 'standard'} mode, "
                f"got {len(file_paths)}."
            )
            return
        
        # Stop any existing worker
        if self.file_loading_worker and self.file_loading_worker.isRunning():
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Stopping previous file loading worker")
            self.file_loading_worker.terminate()
            self.file_loading_worker.wait()
        
        # Remove existing measurements for this device/test_stage/temperature combination
        # This allows selective replacement (e.g., replace AMB but keep HOT/COLD)
        if self.current_device:
            self.session_measurements = [
                m for m in self.session_measurements
                if not (
                    m.device_id == self.current_device.id
                    and m.test_stage == self.current_test_stage
                    and m.temperature == temperature
                )
            ]
            # Clear file display for this specific temperature
            if "S-Parameters" in self.file_display_widgets:
                if temperature in self.file_display_widgets["S-Parameters"]:
                    self.file_display_widgets["S-Parameters"][temperature].setText("")
        
        # Show loading message
        StatusBarMessage.show_info(self.status_bar, f"Loading {len(file_paths)} {temperature} files...")
        
        # Create and start background worker
        file_paths_list = [Path(f) for f in file_paths]
        self.file_loading_worker = FileLoadingWorker(
            database_path=self.database_path,
            file_paths=file_paths_list,
            device=self.current_device,
            test_stage=self.current_test_stage,
            temperature=temperature
        )
        
        # Connect signals
        self.file_loading_worker.files_loaded.connect(
            lambda measurements, warnings: self._on_files_loaded(temperature, measurements, warnings)
        )
        self.file_loading_worker.error_occurred.connect(self._on_file_loading_error)
        
        # Start worker (runs in background thread)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting background file loading worker for {temperature} files")
        self.file_loading_worker.start()
    
    def _on_files_loaded(self, temperature: str, measurements: List[Measurement], warnings: List[str]) -> None:
        """
        Handle successful file loading - called from background worker.
        
        This method ONLY updates the UI - all processing is already done.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Files loaded successfully: {len(measurements)} measurements")
            
        # Show warnings if any
        if warnings:
            for warning in warnings:
                StatusBarMessage.show_warning(self.status_bar, warning)
        
        # Add to session measurements (only these will be shown in compliance table)
        self.session_measurements.extend(measurements)
        
        # Emit signal that measurements were loaded
        self.measurements_loaded.emit()
        
        # Update compliance table (only displays data - evaluation already done)
        self._update_compliance_table()
        
        # Update file display for the specific temperature that was just loaded
        self._update_file_display_for_temperature("S-Parameters", temperature, measurements)
        
        StatusBarMessage.show_info(
            self.status_bar, f"Loaded {len(measurements)} {temperature} files successfully."
        )
        
        # Debug: Log what measurements were loaded
        logger.debug(f"Loaded {len(measurements)} {temperature} measurements:")
        for m in measurements:
            logger.debug(f"  - {m.serial_number}, {m.temperature}, {m.path_type}, test_stage={m.test_stage}")
    
    def _on_file_loading_error(self, error_msg: str) -> None:
        """Handle error from background file loading worker."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(error_msg)
        
        StatusBarMessage.show_warning(
            self.status_bar,
            f"Error loading files. Check logs for details."
        )
        
        # Show error dialog
        from ...utils.error_handler import show_error
        show_error(
            self,
            "Error Loading Files",
            "An error occurred while loading files. See logs for details.",
            details=error_msg
        )
    
    def refresh_compliance_table(self) -> None:
        """Public method to refresh compliance table from external calls."""
        self._update_compliance_table()
    
    def _update_compliance_table(self) -> None:
        """Update the compliance table."""
        if not self.current_device:
            self.compliance_table.clear()
            return
        
        # Only show measurements loaded in current session
        # Filter to current device/test_type/test_stage
        measurements = [
            m for m in self.session_measurements
            if m.device_id == self.current_device.id
            and m.test_type == "S-Parameters"  # TODO: Get from current tab
        ]
        
        # Debug: Log retrieved measurements
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Retrieved {len(measurements)} measurements for device {self.current_device.id}, test_stage {self.current_test_stage}")
        temps = {}
        for m in measurements:
            temps[m.temperature] = temps.get(m.temperature, 0) + 1
        logger.debug(f"Temperature breakdown: {temps}")
        
        # If we have measurements, re-evaluate compliance in background (test stage may have changed)
        if measurements:
            # Stop any existing compliance worker
            if self.compliance_evaluation_worker and self.compliance_evaluation_worker.isRunning():
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Stopping previous compliance evaluation worker")
                self.compliance_evaluation_worker.terminate()
                self.compliance_evaluation_worker.wait()
            
            # Start background compliance re-evaluation
            self.compliance_evaluation_worker = ComplianceEvaluationWorker(
                database_path=self.database_path,
                measurements=measurements,
                device=self.current_device,
                test_stage=self.current_test_stage
            )
            self.compliance_evaluation_worker.evaluation_complete.connect(
                lambda results: self._on_compliance_evaluation_complete(measurements, results)
            )
            self.compliance_evaluation_worker.error_occurred.connect(self._on_compliance_evaluation_error)
            self.compliance_evaluation_worker.start()
        else:
            # No measurements - just update display
            self.compliance_table.update_measurements(
                self.current_device,
                measurements,
                self.current_test_stage
            )
    
    def _on_compliance_evaluation_complete(
        self,
        measurements: List[Measurement],
        results_by_measurement: Optional[Dict]
    ) -> None:
        """Handle completion of compliance re-evaluation - only updates display."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            missing_results = False
            results_by_measurement = results_by_measurement or {}
            
            # Normalize keys to UUID objects (signals may convert keys to str)
            from uuid import UUID
            normalized_results = {}
            for key, value in results_by_measurement.items():
                try:
                    normalized_key = key if isinstance(key, UUID) else UUID(str(key))
                except (ValueError, TypeError):
                    logger.warning("[Compliance Complete] Unable to normalize measurement id key: %s", key)
                    continue
                normalized_results[normalized_key] = value or []
            results_by_measurement = normalized_results
            
            logger.debug(
                "[Compliance Complete] Received results for stage %s: %s measurements",
                self.current_test_stage,
                len(results_by_measurement)
            )
            print(f"[Compliance Complete] Stage {self.current_test_stage} results keys: {list(results_by_measurement.keys())}")
            for meas_id, results in results_by_measurement.items():
                logger.debug(
                    "[Compliance Complete] Measurement %s -> %s results",
                    meas_id,
                    len(results) if results is not None else None
                )
                print(f"[Compliance Complete] Measurement {meas_id} -> {len(results) if results is not None else None} results")
            
            # Determine if any measurement ended up without results for this stage
            for measurement in measurements:
                stage_results = results_by_measurement.get(measurement.id)
                if stage_results is None:
                    stage_results = self.compliance_service.get_compliance_results(
                        measurement.id,
                        self.current_test_stage
                    )
                if not stage_results:
                    missing_results = True
                    break
            
            if missing_results:
                logger.info(
                    "[Compliance Complete] Missing results for stage %s, re-evaluating inline",
                    self.current_test_stage
                )
                for measurement in measurements:
                    # Remove any stale results for this stage before recalculating
                    self.compliance_service.delete_results_for_measurement_and_stage(
                        measurement.id,
                        self.current_test_stage
                    )
                    refreshed_results = self.compliance_service.evaluate_compliance(
                        measurement,
                        self.current_device,
                        self.current_test_stage
                    )
                    if refreshed_results:
                        self.compliance_service.save_test_results(refreshed_results)
            
            sample_measurement = measurements[0] if measurements else None
            if sample_measurement:
                results_count = len(self.compliance_service.get_compliance_results(
                    sample_measurement.id,
                    self.current_test_stage
                ))
                logger.debug(
                    "[Compliance Complete] Sample measurement %s results for stage %s: %s",
                    sample_measurement.id,
                    self.current_test_stage,
                    results_count
                )
        except Exception as log_exc:
            logger.warning(f"[Compliance Complete] Unable to log results: {log_exc}")
        # Update compliance table (only displays data - evaluation already done)
        self.compliance_table.update_measurements(
            self.current_device,
            measurements,
            self.current_test_stage,
            precomputed_results=results_by_measurement
        )
    
    def _on_compliance_evaluation_error(self, error_msg: str) -> None:
        """Handle error from compliance evaluation worker."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(error_msg)
        
        # Still update display with existing data
        measurements = [
            m for m in self.session_measurements
            if m.device_id == self.current_device.id
            and m.test_type == "S-Parameters"
        ]
        self.compliance_table.update_measurements(
            self.current_device,
            measurements,
            self.current_test_stage
        )
    
    def _update_file_displays(self) -> None:
        """Update file display widgets with loaded files for current device/test_stage.
        
        Note: This method is not used after file loading - use _update_file_display_for_temperature instead.
        """
        # Clear all displays if no device
        if not self.current_device:
            self._clear_file_displays()
            return
        
        # Update ALL test types, not just the current tab
        # This ensures all file displays are updated regardless of which tab is visible
        if self.current_device:
            for test_type in self.current_device.tests_performed:
                if test_type in self.file_display_widgets:
                    self._update_file_display_for_test_type(test_type)
    
    def _update_file_display_for_temperature(
        self, 
        test_type: str, 
        temperature: str, 
        new_measurements: List
    ) -> None:
        """Update file display for a specific test type and temperature with newly loaded measurements.
        
        Args:
            test_type: Test type (e.g., "S-Parameters")
            temperature: Temperature (AMB, HOT, or COLD)
            new_measurements: List of Measurement objects that were just loaded
        """
        if not self.current_device:
            return
        
        # Verify widgets exist for this test type
        if test_type not in self.file_display_widgets:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"No file display widgets for test type: {test_type}")
            return
        
        if temperature not in self.file_display_widgets[test_type]:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"No file display widget for temperature: {temperature}")
            return
        
        # Only update the display for the specific temperature that was loaded
        display = self.file_display_widgets[test_type][temperature]
        
        if not new_measurements:
            display.setText("")
            return
        
        # Format metadata for the newly loaded measurements only
        lines = []
        for measurement in new_measurements:
            # Use direct fields from Measurement object (not metadata dict)
            filename = Path(measurement.file_path).name
            serial = measurement.serial_number
            path_type = measurement.path_type
            date_str = measurement.measurement_date.strftime("%Y-%m-%d")
            
            # Build metadata string with direct fields
            metadata_parts = [f"Serial: {serial}", f"Path: {path_type}", f"Date: {date_str}"]
            
            # Add optional metadata from metadata dict if available
            if measurement.metadata:
                if measurement.metadata.get("part_number"):
                    metadata_parts.append(f"Part: {measurement.metadata['part_number']}")
                if measurement.metadata.get("run_number"):
                    metadata_parts.append(f"Run: {measurement.metadata['run_number']}")
                if measurement.metadata.get("test_type"):
                    metadata_parts.append(f"Test: {measurement.metadata['test_type']}")
            
            metadata_str = ", ".join(metadata_parts)
            lines.append(f"✓ {filename} - {metadata_str}")
        
        display.setText("\n".join(lines))
    
    def _update_file_display_for_test_type(self, current_test_type: str) -> None:
        """Update file displays for a specific test type."""
        if not self.current_device:
            return
        
        # Verify widgets exist for this test type
        if current_test_type not in self.file_display_widgets:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"No file display widgets for test type: {current_test_type}")
            return
        
        # Get measurements for current device/test_stage
        try:
            measurements = self.measurement_service.get_measurements_for_device(
                self.current_device.id,
                current_test_type,
                self.current_test_stage
            )
        except Exception as e:
            # If there's an error getting measurements, clear displays and return
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting measurements for file display ({current_test_type}): {e}")
            if current_test_type in self.file_display_widgets:
                for display in self.file_display_widgets[current_test_type].values():
                    display.setText("")
            return
        
        # Ensure measurements is a list (handle edge cases)
        if not isinstance(measurements, list):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"get_measurements_for_device returned non-list: {type(measurements)}")
            measurements = []
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Updating file displays for {current_test_type}: {len(measurements)} measurements")
        
        # Group measurements by temperature
        by_temperature: Dict[str, List] = {}
        for measurement in measurements:
            temp = measurement.temperature
            if temp not in by_temperature:
                by_temperature[temp] = []
            by_temperature[temp].append(measurement)
        
        # Update display widgets for current test type
        if current_test_type in self.file_display_widgets:
            for temperature in ["AMB", "HOT", "COLD"]:
                if temperature in self.file_display_widgets[current_test_type]:
                    display = self.file_display_widgets[current_test_type][temperature]
                    
                    if temperature in by_temperature and by_temperature[temperature]:
                        # Format files for this temperature
                        file_lines = []
                        for measurement in by_temperature[temperature]:
                            # Extract metadata
                            filename = Path(measurement.file_path).name
                            serial = measurement.serial_number
                            path_type = measurement.path_type
                            date_str = measurement.measurement_date.strftime("%Y-%m-%d")
                            
                            # Build metadata string
                            metadata_parts = [f"Serial: {serial}", f"Path: {path_type}", f"Date: {date_str}"]
                            
                            # Add optional metadata
                            if measurement.metadata.get("part_number"):
                                metadata_parts.append(f"Part: {measurement.metadata['part_number']}")
                            if measurement.metadata.get("run_number"):
                                metadata_parts.append(f"Run: {measurement.metadata['run_number']}")
                            if measurement.metadata.get("test_type"):
                                metadata_parts.append(f"Test: {measurement.metadata['test_type']}")
                            
                            metadata_str = ", ".join(metadata_parts)
                            file_lines.append(f"✓ {filename} - {metadata_str}")
                        
                        display.setText("\n".join(file_lines))
                    else:
                        display.setText("")
    
    def _clear_all_data(self, silent: bool = False) -> None:
        """
        Clear all loaded measurement data and reset to initial state.
        
        This clears:
        - All session measurements
        - Compliance table
        - All file displays (all temperatures)
        
        Args:
            silent: If True, don't show status message (used when called from device switch)
        """
        # Clear session measurements
        self.session_measurements.clear()
        self.measurements_loaded.emit()  # Signal that measurements were cleared
        
        # Clear compliance table
        self.compliance_table.clear()
        
        # Clear all file displays
        self._clear_file_displays()
        
        if not silent:
            StatusBarMessage.show_info(
                self.status_bar,
                "All measurement data cleared",
                timeout=2000
            )
    
    def _clear_file_displays(self) -> None:
        """Clear all file display widgets."""
        for test_type_widgets in self.file_display_widgets.values():
            for display in test_type_widgets.values():
                display.setText("")



