"""
Compliance table widget with hierarchical tree view.

This module provides a widget that displays compliance results in a
hierarchical tree structure: Temperature → Criterion Type → S-parameter.
Each row shows the 6 columns: Requirement, Limit, PRI (value), PRI Status,
RED (value), RED Status.
"""

from typing import Optional, List, Dict
from uuid import UUID
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QPushButton, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap

from ....core.models.device import Device
from ....core.models.measurement import Measurement
from ....core.models.test_result import TestResult
from ....core.models.test_criteria import TestCriteria
from ....core.services.compliance_service import ComplianceService
from ...utils.error_handler import StatusBarMessage


class ComplianceTableWidget(QWidget):
    """
    Compliance table widget with hierarchical tree view.
    
    Displays compliance results organized by:
    - Temperature (AMB, HOT, COLD)
    - Criterion Type (Gain, VSWR, OOB)
    - S-parameter (S21, S31, etc.)
    
    Each row shows 6 columns with pass/fail status color-coded.
    """
    
    def __init__(
        self,
        compliance_service: ComplianceService,
        status_bar,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize compliance table widget.
        
        Args:
            compliance_service: ComplianceService instance
            status_bar: QStatusBar for status messages
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.compliance_service = compliance_service
        self.status_bar = status_bar
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels([
            "Requirement", "Limit", "PRI", "PRI Status", "RED", "RED Status"
        ])
        
        # Configure column sizing for even distribution
        header = self.tree.header()
        header.setStretchLastSection(False)  # Don't stretch last column
        # Use Interactive mode so columns can be resized and are evenly sized initially
        for col in range(6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set initial column widths proportionally (each column gets ~16.67% of width)
        # We'll do this after widget is shown, but set minimum widths here
        header.setMinimumSectionSize(80)  # Minimum width for readability
        
        self.tree.setAlternatingRowColors(True)
        
        layout.addWidget(self.tree)
        
        # Set proportional column widths after widget is ready
        # Use a single-shot timer to set widths after layout is complete
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._set_proportional_column_widths)
        
        # Copy buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        copy_button = QPushButton("Copy Table to Clipboard")
        copy_button.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(copy_button)
        copy_image_button = QPushButton("Copy as Image")
        copy_image_button.clicked.connect(self._copy_as_image)
        button_layout.addWidget(copy_image_button)
        layout.addLayout(button_layout)
    
    def clear(self) -> None:
        """Clear the compliance table."""
        self.tree.clear()
    
    def update_measurements(
        self,
        device: Device,
        measurements: List[Measurement],
        test_stage: str,
        precomputed_results: Optional[Dict[UUID, List[TestResult]]] = None
    ) -> None:
        """
        Update the compliance table with measurements.
        
        Args:
            device: Current device
            measurements: List of measurements to display
            test_stage: Current test stage
        """
        self.tree.clear()
        
        if not measurements:
            return
        
        # Group measurements by temperature
        by_temperature: Dict[str, List[Measurement]] = {}
        for measurement in measurements:
            temp = measurement.temperature
            if temp not in by_temperature:
                by_temperature[temp] = []
            by_temperature[temp].append(measurement)
        
        # Debug: Log temperature groups
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Compliance table update: {len(measurements)} measurements grouped by temperature:")
        for temp, temp_measurements in by_temperature.items():
            logger.debug(f"  - {temp}: {len(temp_measurements)} measurements")
            for m in temp_measurements:
                if precomputed_results and m.id in precomputed_results:
                    stage_results = precomputed_results[m.id]
                else:
                    stage_results = self.compliance_service.get_compliance_results(m.id, test_stage)
                logger.debug(
                    "    measurement %s (%s %s) -> %s results for stage %s",
                    m.id,
                    m.temperature,
                    m.path_type,
                    len(stage_results),
                    test_stage
                )
                print(f"[ComplianceTableWidget] Stage {test_stage} measurement {m.id} results: {len(stage_results)} (precomputed={m.id in precomputed_results if precomputed_results else False})")
        
        # Create tree structure
        for temperature in sorted(by_temperature.keys()):
            temp_measurements = by_temperature[temperature]
            
            # Create temperature root item
            temp_item = QTreeWidgetItem(self.tree)
            temp_item.setText(0, temperature)
            temp_item.setExpanded(True)
            
            # Group by path type (PRI/RED)
            pri_measurements = [m for m in temp_measurements if m.path_type.startswith("PRI")]
            red_measurements = [m for m in temp_measurements if m.path_type.startswith("RED")]
            
            if not pri_measurements and not red_measurements:
                continue
            
            # Get results for PRI and RED
            pri_results = {}
            red_results = {}
            
            if pri_measurements:
                for m in pri_measurements:
                    if precomputed_results and m.id in precomputed_results:
                        results = precomputed_results[m.id]
                    else:
                        results = self.compliance_service.get_compliance_results(m.id, test_stage)
                    pri_results[m.id] = results
            
            if red_measurements:
                for m in red_measurements:
                    if precomputed_results and m.id in precomputed_results:
                        results = precomputed_results[m.id]
                    else:
                        results = self.compliance_service.get_compliance_results(m.id, test_stage)
                    red_results[m.id] = results
            
            # Group results by criterion type
            criterion_groups: Dict[str, Dict[str, List[TestResult]]] = {}
            
            # Process PRI results
            for measurement_id, results in pri_results.items():
                for result in results:
                    # Get criterion name (without S-parameter suffix)
                    criterion_name = self._get_criterion_base_name(result)
                    if criterion_name not in criterion_groups:
                        criterion_groups[criterion_name] = {}
                    if result.s_parameter not in criterion_groups[criterion_name]:
                        criterion_groups[criterion_name][result.s_parameter] = []
                    criterion_groups[criterion_name][result.s_parameter].append(result)
            
            # Process RED results (merge)
            for measurement_id, results in red_results.items():
                for result in results:
                    criterion_name = self._get_criterion_base_name(result)
                    if criterion_name not in criterion_groups:
                        criterion_groups[criterion_name] = {}
                    if result.s_parameter not in criterion_groups[criterion_name]:
                        criterion_groups[criterion_name][result.s_parameter] = []
                    criterion_groups[criterion_name][result.s_parameter].append(result)
            
            # Create criterion type items
            for criterion_name in sorted(criterion_groups.keys()):
                criterion_item = QTreeWidgetItem(temp_item)
                criterion_item.setText(0, criterion_name)
                criterion_item.setExpanded(True)
                
                # Get all S-parameters for this criterion
                s_params = sorted(criterion_groups[criterion_name].keys())
                
                # Calculate aggregate pass/fail for this criterion
                all_criterion_results = []
                for s_param in s_params:
                    all_criterion_results.extend(criterion_groups[criterion_name][s_param])
                
                pri_pass = all([r.passed for r in all_criterion_results if any(
                    m.id in pri_results for m in pri_measurements
                )])
                red_pass = all([r.passed for r in all_criterion_results if any(
                    m.id in red_results for m in red_measurements
                )])
                
                # Set aggregate status
                criterion_item.setText(3, "PASS" if pri_pass else "FAIL")
                criterion_item.setText(5, "PASS" if red_pass else "FAIL")
                self._set_status_color(criterion_item, 3, pri_pass)
                self._set_status_color(criterion_item, 5, red_pass)
                
                # Create S-parameter items
                for s_param in s_params:
                    s_item = QTreeWidgetItem(criterion_item)
                    
                    # Find PRI and RED results for this S-parameter
                    pri_result = None
                    red_result = None
                    
                    for result in criterion_groups[criterion_name][s_param]:
                        # Find which measurement this result belongs to
                        for m in pri_measurements:
                            if m.id == result.measurement_id:
                                pri_result = result
                                break
                        for m in red_measurements:
                            if m.id == result.measurement_id:
                                red_result = result
                                break
                    
                    # Fill in row data
                    s_item.setText(0, f"{s_param} {criterion_name}")
                    
                    # Limit (from criterion - need to get from service)
                    limit_text = self._get_limit_text(result)
                    s_item.setText(1, limit_text)
                    
                    # PRI
                    if pri_result:
                        # Find the corresponding measurement for PRI
                        pri_measurement = None
                        for m in pri_measurements:
                            if m.id == pri_result.measurement_id:
                                pri_measurement = m
                                break
                        pri_value_text = self._format_value(
                            pri_result.measured_value,
                            pri_result,
                            pri_measurement,
                            device
                        )
                        s_item.setText(2, pri_value_text)
                        s_item.setText(3, "PASS" if pri_result.passed else "FAIL")
                        self._set_status_color(s_item, 3, pri_result.passed)
                    
                    # RED
                    if red_result:
                        # Find the corresponding measurement for RED
                        red_measurement = None
                        for m in red_measurements:
                            if m.id == red_result.measurement_id:
                                red_measurement = m
                                break
                        red_value_text = self._format_value(
                            red_result.measured_value,
                            red_result,
                            red_measurement,
                            device
                        )
                        s_item.setText(4, red_value_text)
                        s_item.setText(5, "PASS" if red_result.passed else "FAIL")
                        self._set_status_color(s_item, 5, red_result.passed)
        
        # Expand all items
        self.tree.expandAll()
        
        # Set proportional column widths after populating
        self._set_proportional_column_widths()
    
    def _get_criterion_base_name(self, result: TestResult) -> str:
        """Get base criterion name (without S-parameter)."""
        # Get criterion from service to get requirement_name
        try:
            criteria_repo = self.compliance_service.criteria_repo
            criteria = criteria_repo.get_by_id(result.test_criteria_id)
            if criteria:
                return criteria.requirement_name
        except Exception:
            pass
        return "Unknown"  # Fallback
    
    def _get_limit_text(self, result: TestResult) -> str:
        """Get limit text from criterion."""
        try:
            criteria_repo = self.compliance_service.criteria_repo
            criteria = criteria_repo.get_by_id(result.test_criteria_id)
            if criteria:
                if criteria.criteria_type == "range":
                    return f"{criteria.min_value} to {criteria.max_value} {criteria.unit}"
                elif criteria.criteria_type == "max":
                    return f"<= {criteria.max_value} {criteria.unit}"
                elif criteria.criteria_type == "min":
                    return f">= {criteria.min_value} {criteria.unit}"
                elif criteria.criteria_type == "greater_than_equal":
                    return f">= {criteria.min_value} {criteria.unit}"
                elif criteria.criteria_type == "less_than_equal":
                    return f"<= {criteria.max_value} {criteria.unit}"
        except Exception:
            pass
        return "N/A"  # Fallback
    
    def _format_value(
        self,
        value: Optional[float],
        result: TestResult,
        measurement: Optional[Measurement] = None,
        device: Optional[Device] = None
    ) -> str:
        """
        Format measured value for display.
        
        For Gain Range criteria, displays min-max range format.
        For other criteria, displays single value.
        
        Args:
            value: Measured value (typically max for gain range)
            result: TestResult object (contains criterion info)
            measurement: Optional measurement object (needed for recalculating gain range)
            device: Optional device object (needed for frequency ranges)
        """
        if value is None:
            return "N/A"
        
        # Check if this is a Gain Range criterion
        try:
            criteria_repo = self.compliance_service.criteria_repo
            criteria = criteria_repo.get_by_id(result.test_criteria_id)
            
            # Check for Gain Range criterion - use exact match for reliability
            is_gain_range = (criteria and 
                           criteria.requirement_name == "Gain Range" and
                           criteria.criteria_type == "range")
            
            if is_gain_range:
                # This is a Gain Range criterion - need to show min-max range
                # Recalculate from measurement if available
                if measurement and device and result.s_parameter:
                    # Check if measurement has touchstone_data
                    if not hasattr(measurement, 'touchstone_data') or measurement.touchstone_data is None:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Measurement {measurement.id} has no touchstone_data")
                        unit = criteria.unit if criteria.unit else "dB"
                        return f"{value:.2f} {unit}"
                    
                    try:
                        from ....core.rf_data.s_parameter_calculator import SParameterCalculator
                        from skrf import Network
                        
                        calculator = SParameterCalculator()
                        
                        # Get network from measurement - it's already deserialized from database
                        # touchstone_data is a Network object, not bytes
                        if isinstance(measurement.touchstone_data, Network):
                            network = measurement.touchstone_data
                        else:
                            # If it's bytes (shouldn't happen, but handle gracefully)
                            from ....core.rf_data.touchstone_loader import TouchstoneLoader
                            loader = TouchstoneLoader()
                            network = loader.deserialize_network(measurement.touchstone_data)
                        
                        # Calculate gain range for this S-parameter
                        min_gain, max_gain = calculator.calculate_gain_range(
                            network,
                            device.operational_freq_min,
                            device.operational_freq_max,
                            result.s_parameter
                        )
                        
                        # Format as range: "min to max dB"
                        unit = criteria.unit if criteria.unit else "dB"
                        return f"{min_gain:.2f} to {max_gain:.2f} {unit}"
                    except Exception as e:
                        # Log error for debugging but fall back gracefully
                        import logging
                        import traceback
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to recalculate gain range for display: {e}")
                        logger.warning(f"Measurement ID: {measurement.id if measurement else 'None'}, Device: {device.id if device else 'None'}, S-param: {result.s_parameter}")
                        logger.debug(f"Traceback: {traceback.format_exc()}")
                        # If recalculation fails, fall back to single value
                        unit = criteria.unit if criteria.unit else "dB"
                        return f"{value:.2f} {unit}"
                else:
                    # Don't have measurement data - format as single value with unit
                    import logging
                    logger = logging.getLogger(__name__)
                    missing = []
                    if not measurement:
                        missing.append("measurement")
                    if not device:
                        missing.append("device")
                    if not result.s_parameter:
                        missing.append("s_parameter")
                    logger.debug(f"Cannot format gain range: missing {', '.join(missing)}")
                    unit = criteria.unit if criteria.unit else "dB"
                    return f"{value:.2f} {unit}"
        except Exception as e:
            # If criterion lookup fails, format as single value
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not lookup criterion for gain range formatting: {e}")
            pass
        
        # Default: format as single value
        return f"{value:.2f}"
    
    def _set_status_color(self, item: QTreeWidgetItem, column: int, passed: bool) -> None:
        """Set background and foreground colors for pass/fail status."""
        if passed:
            item.setBackground(column, QColor(200, 255, 200))  # Light green
            item.setForeground(column, QColor(0, 0, 0))  # Black text for readability
        else:
            item.setBackground(column, QColor(255, 200, 200))  # Light red
            item.setForeground(column, QColor(0, 0, 0))  # Black text for readability
    
    def _set_proportional_column_widths(self) -> None:
        """Set column widths proportionally for even distribution."""
        if not self.tree.isVisible():
            return
        
        # Get available width
        available_width = self.tree.viewport().width()
        if available_width <= 0:
            return
        
        # Calculate proportional widths (each column gets equal share)
        # Reserve some space for scrollbar
        column_width = int((available_width - 20) / 6)
        
        # Set widths for all columns
        header = self.tree.header()
        for col in range(6):
            header.resizeSection(col, column_width)
    
    def _copy_to_clipboard(self) -> None:
        """
        Copy the entire compliance table to clipboard as plain text.
        
        Exports the complete table (all items, including collapsed ones) as
        tab-separated text, suitable for pasting into Excel, PowerPoint, etc.
        The format preserves the hierarchical structure with indentation.
        """
        # Get clipboard
        clipboard = QApplication.clipboard()
        
        # Build text representation
        lines = []
        
        # Add header
        header = "\t".join([
            "Requirement", "Limit", "PRI", "PRI Status", "RED", "RED Status"
        ])
        lines.append(header)
        
        # Traverse all items (including collapsed ones)
        def traverse_item(item: QTreeWidgetItem, level: int = 0) -> None:
            """Recursively traverse tree items to get all data."""
            # Build row data
            row_data = []
            for col in range(6):
                text = item.text(col)
                row_data.append(text)
            
            # Add indentation based on level (using tabs for Excel compatibility)
            indent = "\t" * level
            line = indent + "\t".join(row_data)
            lines.append(line)
            
            # Recursively process children
            for i in range(item.childCount()):
                traverse_item(item.child(i), level + 1)
        
        # Process all top-level items
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            traverse_item(root.child(i), 0)
        
        # Join all lines and copy to clipboard
        text = "\n".join(lines)
        clipboard.setText(text)
        
        # Show confirmation
        StatusBarMessage.show_info(
            self.status_bar,
            f"Copied {len(lines) - 1} rows to clipboard (tab-separated format)",
            timeout=3000
        )
    
    def _save_expansion_state(self) -> Dict[str, bool]:
        """
        Save the expansion state of all tree items.
        
        Returns:
            Dictionary mapping item text to expansion state
        """
        state = {}
        
        def save_item(item: QTreeWidgetItem) -> None:
            """Recursively save expansion state."""
            # Use item text as key (or a combination if needed)
            key = item.text(0) if item.parent() else f"root_{item.text(0)}"
            state[key] = item.isExpanded()
            
            # Recursively process children
            for i in range(item.childCount()):
                save_item(item.child(i))
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            save_item(root.child(i))
        
        return state
    
    def _restore_expansion_state(self, state: Dict[str, bool]) -> None:
        """
        Restore the expansion state of all tree items.
        
        Args:
            state: Dictionary mapping item text to expansion state
        """
        def restore_item(item: QTreeWidgetItem) -> None:
            """Recursively restore expansion state."""
            key = item.text(0) if item.parent() else f"root_{item.text(0)}"
            if key in state:
                item.setExpanded(state[key])
            
            # Recursively process children
            for i in range(item.childCount()):
                restore_item(item.child(i))
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            restore_item(root.child(i))
    
    def _copy_as_image(self) -> None:
        """
        Copy the entire compliance table to clipboard as PNG image.
        
        Expands all items to capture the full tree, temporarily resizes widget
        to show all content, captures the widget, copies to clipboard, and
        optionally saves to file.
        """
        if self.tree.topLevelItemCount() == 0:
            StatusBarMessage.show_warning(
                self.status_bar,
                "No data to copy. Please load measurements first."
            )
            return
        
        # Save current expansion state and size
        expansion_state = self._save_expansion_state()
        original_size = self.tree.size()
        original_min_height = self.tree.minimumHeight()
        original_max_height = self.tree.maximumHeight()
        
        try:
            # Expand all items to capture full tree
            self.tree.expandAll()
            
            # Force update to ensure all items are rendered
            QApplication.processEvents()
            
            # Use QTimer to ensure rendering completes before capture
            def capture_and_copy():
                try:
                    # Calculate the total height needed by iterating through all items
                    # Get the last visible item's bottom position
                    total_height = self.tree.header().height()
                    
                    # Find the last item in the tree
                    def get_last_item(item):
                        if item.childCount() > 0 and item.isExpanded():
                            last_child = item.child(item.childCount() - 1)
                            return get_last_item(last_child)
                        return item
                    
                    if self.tree.topLevelItemCount() > 0:
                        last_item = self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)
                        last_item = get_last_item(last_item)
                        last_rect = self.tree.visualItemRect(last_item)
                        total_height = last_rect.bottom() + self.tree.header().height() + 10
                    else:
                        total_height = self.tree.header().height() + 50
                    
                    # Temporarily remove size constraints and resize to fit all content
                    self.tree.setMinimumHeight(0)
                    self.tree.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
                    
                    # Resize to show all content
                    temp_width = max(original_size.width(), 600)
                    temp_height = min(total_height, 50000)  # Cap at reasonable max
                    
                    self.tree.setMinimumHeight(temp_height)
                    self.tree.resize(temp_width, temp_height)
                    
                    # Scroll to top to ensure we capture from the beginning
                    self.tree.scrollToTop()
                    
                    # Force update and process events
                    self.tree.update()
                    QApplication.processEvents()
                    
                    # Wait a bit more for rendering
                    QTimer.singleShot(150, lambda: _do_capture())
                except Exception as e:
                    StatusBarMessage.show_warning(
                        self.status_bar,
                        f"Failed to prepare capture: {str(e)}"
                    )
                    self._restore_expansion_state(expansion_state)
                    self.tree.setMinimumHeight(original_min_height)
                    self.tree.setMaximumHeight(original_max_height)
                    self.tree.resize(original_size)
            
            def _do_capture():
                try:
                    # Capture the widget (now showing all content)
                    pixmap = self.tree.grab()
                    
                    if pixmap.isNull():
                        StatusBarMessage.show_warning(
                            self.status_bar,
                            "Failed to capture table image."
                        )
                        return
                    
                    # Copy to clipboard
                    clipboard = QApplication.clipboard()
                    clipboard.setPixmap(pixmap)
                    
                    # Show file save dialog
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "Save Compliance Table Image",
                        "compliance_table.png",
                        "PNG Files (*.png);;All Files (*)"
                    )
                    
                    if file_path:
                        # Save to file
                        if pixmap.save(file_path, "PNG"):
                            StatusBarMessage.show_info(
                                self.status_bar,
                                f"Image copied to clipboard and saved to {file_path}",
                                timeout=3000
                            )
                        else:
                            StatusBarMessage.show_warning(
                                self.status_bar,
                                f"Image copied to clipboard, but failed to save to {file_path}"
                            )
                    else:
                        StatusBarMessage.show_info(
                            self.status_bar,
                            "Image copied to clipboard",
                            timeout=3000
                        )
                    
                    # Restore expansion state and size
                    self._restore_expansion_state(expansion_state)
                    self.tree.setMinimumHeight(original_min_height)
                    self.tree.setMaximumHeight(original_max_height)
                    self.tree.resize(original_size)
                except Exception as e:
                    StatusBarMessage.show_warning(
                        self.status_bar,
                        f"Failed to capture image: {str(e)}"
                    )
                    # Restore expansion state and size on error
                    self._restore_expansion_state(expansion_state)
                    self.tree.setMinimumHeight(original_min_height)
                    self.tree.setMaximumHeight(original_max_height)
                    self.tree.resize(original_size)
            
            # Delay capture to ensure rendering completes
            QTimer.singleShot(100, capture_and_copy)
            
        except Exception as e:
            # Restore expansion state on error
            self._restore_expansion_state(expansion_state)
            self.tree.setMinimumHeight(original_min_height)
            self.tree.setMaximumHeight(original_max_height)
            self.tree.resize(original_size)
            StatusBarMessage.show_warning(
                self.status_bar,
                f"Failed to copy image: {str(e)}"
            )

