"""
Plot window for displaying RF measurements.

This module provides a separate window for plotting RF data with filtering
controls, axis controls, and export capabilities.
"""

from typing import Optional, List, Dict, Set, Tuple
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QCheckBox, QPushButton, QDoubleSpinBox, QLineEdit, QLabel, QComboBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MultipleLocator, FuncFormatter
from matplotlib.collections import LineCollection
import numpy as np
import math

# Try to import mplcursors for hover functionality
try:
    import mplcursors
    MPLCURSORS_AVAILABLE = True
except ImportError:
    MPLCURSORS_AVAILABLE = False

from skrf import Network

from ....core.services.device_service import DeviceService
from ....core.services.measurement_service import MeasurementService
from ....core.services.compliance_service import ComplianceService
from ....core.services.plotting_service import PlottingService, PlotData
from ....core.models.device import Device
from ....core.models.measurement import Measurement
from ....core.models.test_criteria import TestCriteria
from ...utils.error_handler import StatusBarMessage
from ...utils.service_factory import create_services_for_thread


class PlottingWorker(QThread):
    """
    Background worker thread for plot data processing.
    
    All heavy processing (filtering, deserialization, calculations) happens here.
    Creates its own database connection and services for thread safety.
    """
    data_ready = Signal(object)  # PlotData
    error_occurred = Signal(str)
    
    def __init__(
        self,
        database_path: Path,
        plotting_service: PlottingService,
        device: Device,
        measurements: List[Measurement],
        plot_type: str,
        selected_temperatures: Set[str],
        selected_paths: Set[str],
        selected_s_params: Set[str],
        test_stage: str
    ):
        super().__init__()
        self.database_path = database_path
        self.plotting_service = plotting_service
        self.device = device
        self.measurements = measurements
        self.plot_type = plot_type
        self.selected_temperatures = selected_temperatures
        self.selected_paths = selected_paths
        self.selected_s_params = selected_s_params
        self.test_stage = test_stage
    
    def run(self):
        """Execute plot data processing in background thread."""
        try:
            # Create thread-local compliance service with new database connection
            # SQLite connections cannot be shared across threads
            _, _, compliance_service = create_services_for_thread(self.database_path)
            
            plot_data = self.plotting_service.prepare_plot_data(
                device=self.device,
                measurements=self.measurements,
                plot_type=self.plot_type,
                selected_temperatures=self.selected_temperatures,
                selected_paths=self.selected_paths,
                selected_s_params=self.selected_s_params,
                test_stage=self.test_stage,
                compliance_service=compliance_service
            )
            self.data_ready.emit(plot_data)
        except Exception as e:
            import traceback
            error_msg = f"Error preparing plot data: {e}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)


class PlotWindow(QMainWindow):
    """
    Plot window for RF data visualization.
    
    Provides filtering controls, matplotlib plot, axis controls, and export.
    """
    
    def __init__(
        self,
        plot_type: str,
        device_service: DeviceService,
        measurement_service: MeasurementService,
        compliance_service: ComplianceService,
        database_path: Path,
        status_bar,
        test_setup_tab=None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize plot window.
        
        Args:
            plot_type: Type of plot (Operational Gain, Operational VSWR, etc.)
            device_service: DeviceService instance
            measurement_service: MeasurementService instance
            compliance_service: ComplianceService instance
            database_path: Path to database file (for worker threads)
            status_bar: QStatusBar for status messages
            test_setup_tab: Reference to TestSetupTab for accessing session measurements
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.plot_type = plot_type
        self.device_service = device_service
        self.measurement_service = measurement_service
        self.compliance_service = compliance_service
        self.database_path = database_path
        self.status_bar = status_bar
        self.test_setup_tab = test_setup_tab
        
        # Initialize plotting service (does all processing)
        self.plotting_service = PlottingService()
        self.plotting_worker: Optional[PlottingWorker] = None
        
        self.s_param_checks: Dict[str, QCheckBox] = {}  # Dynamic S-parameter checkboxes
        self.path_hg_lg_checks: Dict[str, QCheckBox] = {}  # HG/LG checkboxes if multi-gain
        self.legend_position = "best"  # Default legend position
        self._title_updating = False  # Flag to prevent recursive title updates
        self._subtitle_updating = False  # Flag to prevent recursive subtitle updates
        self._default_title = ""  # Store default title for reset
        self._default_subtitle = ""  # Store default subtitle for reset
        
        # Determine plot mode from plot_type
        plot_type_lower = plot_type.lower()
        self.is_vswr_plot = "vswr" in plot_type_lower
        self.is_return_loss_plot = "return loss" in plot_type_lower
        self.is_wideband_plot = "wideband" in plot_type_lower
        self.is_operational_plot = "operational" in plot_type_lower or not self.is_wideband_plot
        self.show_pass_region = self.is_operational_plot  # Only show for operational plots
        
        # Set default Y-axis label based on plot type
        if self.is_return_loss_plot:
            self._default_y_label = "Return Loss (dB)"
        elif self.is_vswr_plot:
            self._default_y_label = "VSWR"
        else:
            self._default_y_label = "Gain (dB)"
        
        self.setWindowTitle(f"{plot_type} - Macallan RF Performance Tool")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Ensure all plot type flags are set before calling _setup_ui()
        assert hasattr(self, 'is_return_loss_plot'), "is_return_loss_plot must be set before _setup_ui()"
        assert hasattr(self, 'is_vswr_plot'), "is_vswr_plot must be set before _setup_ui()"
        assert hasattr(self, 'is_wideband_plot'), "is_wideband_plot must be set before _setup_ui()"
        
        self._setup_ui()
        # Don't populate filters here - wait until we have data
        # Filters will be populated in _update_plot() when needed
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Combined Filters and Controls (collapsible)
        controls_container = QWidget()
        controls_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        controls_container_layout = QVBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(0, 0, 0, 0)
        controls_container_layout.setSpacing(0)
        
        # Header button
        controls_header_button = QPushButton("Controls ▼")
        controls_header_button.setFlat(False)
        controls_header_button.setStyleSheet("""
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
        controls_container_layout.addWidget(controls_header_button)
        
        # Controls content (contains both filters and axis controls)
        controls_content = QWidget()
        controls_content_layout = QVBoxLayout(controls_content)
        controls_content_layout.setContentsMargins(10, 10, 10, 10)
        controls_content_layout.setSpacing(15)
        
        # Filters section (horizontal layout)
        filter_layout = QHBoxLayout()
        
        # Temperature filters
        temp_layout = QVBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.amb_check = QCheckBox("Ambient")
        self.amb_check.setChecked(True)
        self.hot_check = QCheckBox("Hot")
        self.hot_check.setChecked(True)
        self.cold_check = QCheckBox("Cold")
        self.cold_check.setChecked(True)
        temp_layout.addWidget(self.amb_check)
        temp_layout.addWidget(self.hot_check)
        temp_layout.addWidget(self.cold_check)
        filter_layout.addLayout(temp_layout)
        
        # Path filters (will be populated with HG/LG if multi-gain)
        self.path_layout = QVBoxLayout()
        self.path_layout.addWidget(QLabel("Path:"))
        self.pri_check = QCheckBox("Primary")
        self.pri_check.setChecked(True)
        self.red_check = QCheckBox("Redundant")
        self.red_check.setChecked(True)
        self.path_layout.addWidget(self.pri_check)
        self.path_layout.addWidget(self.red_check)
        # HG/LG checkboxes will be added dynamically if multi-gain mode
        filter_layout.addLayout(self.path_layout)
        
        # S-parameter filters (populated dynamically)
        self.s_param_layout = QVBoxLayout()
        self.s_param_layout.addWidget(QLabel("S-Parameters:"))
        # Will be populated in _populate_s_param_filters()
        filter_layout.addLayout(self.s_param_layout)
        
        filter_layout.addStretch()
        controls_content_layout.addLayout(filter_layout)
        
        # Separator line between filters and axis controls
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #666;")
        controls_content_layout.addWidget(separator)
        
        # Axis controls section starts here (will be added below)
        
        # Matplotlib plot (with stretch to take available space)
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=1)  # Give plot priority for space
        
        # Axis controls section (part of combined controls)
        # Axis controls (limits)
        axis_limits_layout = QHBoxLayout()
        axis_limits_layout.addWidget(QLabel("Axis Limits:"))
        axis_limits_layout.addWidget(QLabel("X Min:"))
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(0.0, 1000.0)
        self.x_min_spin.setDecimals(3)
        self.x_min_spin.setSuffix(" GHz")
        self.x_min_spin.setValue(0.0)  # Default to 0 (auto-scale)
        axis_limits_layout.addWidget(self.x_min_spin)
        
        axis_limits_layout.addWidget(QLabel("X Max:"))
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(0.0, 1000.0)
        self.x_max_spin.setDecimals(3)
        self.x_max_spin.setSuffix(" GHz")
        self.x_max_spin.setValue(0.0)  # Default to 0 (auto-scale)
        axis_limits_layout.addWidget(self.x_max_spin)
        
        axis_limits_layout.addWidget(QLabel("Y Min:"))
        self.y_min_spin = QDoubleSpinBox()
        if self.is_vswr_plot:
            # Allow 0.0 as auto-scale flag, but actual range starts at 1.0 (VSWR can't be < 1.0)
            self.y_min_spin.setRange(0.0, 10.0)  # 0.0 = auto-scale, 1.0+ = manual setting
            self.y_min_spin.setSuffix("")  # VSWR is a ratio, no unit
            self.y_min_spin.setValue(0.0)  # Default to 0 (auto-scale, will be set to 1.0)
        elif self.is_return_loss_plot:
            # Return Loss is in dB, typically ranges from -40 to 0 dB
            self.y_min_spin.setRange(-100.0, 0.0)
            self.y_min_spin.setSuffix(" dB")
            self.y_min_spin.setValue(0.0)  # Default to 0 (auto-scale)
        else:
            self.y_min_spin.setRange(-100.0, 100.0)
            self.y_min_spin.setSuffix(" dB")
            self.y_min_spin.setValue(0.0)  # Default to 0 (auto-scale)
        self.y_min_spin.setDecimals(2)
        axis_limits_layout.addWidget(self.y_min_spin)
        
        axis_limits_layout.addWidget(QLabel("Y Max:"))
        self.y_max_spin = QDoubleSpinBox()
        if self.is_vswr_plot:
            self.y_max_spin.setRange(0.0, 10.0)
            self.y_max_spin.setSuffix("")  # VSWR is a ratio, no unit
        elif self.is_return_loss_plot:
            self.y_max_spin.setRange(-100.0, 0.0)
            self.y_max_spin.setSuffix(" dB")
        else:
            self.y_max_spin.setRange(-100.0, 100.0)
            self.y_max_spin.setSuffix(" dB")
        self.y_max_spin.setDecimals(2)
        self.y_max_spin.setValue(0.0)  # Default to 0 (auto-scale)
        axis_limits_layout.addWidget(self.y_max_spin)
        
        # Reset button to clear axis limits (set to 0 for auto-scale)
        reset_button = QPushButton("Reset Limits")
        reset_button.clicked.connect(self._reset_axis_limits)
        axis_limits_layout.addWidget(reset_button)
        axis_limits_layout.addStretch()
        controls_content_layout.addLayout(axis_limits_layout)
        
        # Axis labels
        axis_label_layout = QHBoxLayout()
        axis_label_layout.addWidget(QLabel("Axis Labels:"))
        axis_label_layout.addWidget(QLabel("X-Axis Label:"))
        self.x_axis_label_edit = QLineEdit("Frequency (GHz)")
        self.x_axis_label_edit.editingFinished.connect(self._update_plot)
        axis_label_layout.addWidget(self.x_axis_label_edit)
        reset_x_label_button = QPushButton("Reset")
        reset_x_label_button.setToolTip("Reset X-axis label to default")
        reset_x_label_button.clicked.connect(self._reset_x_axis_label)
        axis_label_layout.addWidget(reset_x_label_button)
        
        axis_label_layout.addWidget(QLabel("Y-Axis Label:"))
        self.y_axis_label_edit = QLineEdit(self._default_y_label)
        self.y_axis_label_edit.editingFinished.connect(self._update_plot)
        axis_label_layout.addWidget(self.y_axis_label_edit)
        reset_y_label_button = QPushButton("Reset")
        reset_y_label_button.setToolTip("Reset Y-axis label to default")
        reset_y_label_button.clicked.connect(self._reset_y_axis_label)
        axis_label_layout.addWidget(reset_y_label_button)
        
        axis_label_layout.addWidget(QLabel("Legend Position:"))
        self.legend_position_combo = QComboBox()
        self.legend_position_combo.addItems([
            "best", "upper right", "upper left", "lower right", "lower left",
            "center", "upper center", "lower center", "right", "left",
            "center left", "center right"
        ])
        self.legend_position_combo.setCurrentText("best")
        self.legend_position_combo.currentTextChanged.connect(self._on_legend_position_changed)
        axis_label_layout.addWidget(self.legend_position_combo)
        
        axis_label_layout.addStretch()
        controls_content_layout.addLayout(axis_label_layout)
        
        # Add controls content to container
        controls_container_layout.addWidget(controls_content)
        
        # Collapse state
        controls_collapsed = {"is_collapsed": True}
        controls_content.setMaximumHeight(0)
        controls_content.setMinimumHeight(0)
        
        def toggle_controls():
            if controls_collapsed["is_collapsed"]:
                controls_header_button.setText("Controls ▼")
                controls_content.setMaximumHeight(16777215)
                controls_content.setMinimumHeight(0)
                controls_collapsed["is_collapsed"] = False
            else:
                controls_header_button.setText("Controls ▶")
                controls_content.setMaximumHeight(0)
                controls_content.setMinimumHeight(0)
                controls_collapsed["is_collapsed"] = True
            controls_container.updateGeometry()
            controls_content.updateGeometry()
            QApplication.processEvents()
        
        controls_header_button.clicked.connect(toggle_controls)
        controls_header_button.setText("Controls ▶")
        
        layout.addWidget(controls_container)
        
        # Title, subtitle and export (compact layout)
        bottom_layout = QHBoxLayout()
        
        # Title and subtitle in a compact group
        title_group = QGroupBox("Plot Labels")
        title_group_layout = QVBoxLayout(title_group)
        title_group_layout.setContentsMargins(5, 5, 5, 5)
        title_group_layout.setSpacing(5)
        
        # Title row
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        title_row.addWidget(self.title_edit, stretch=1)
        reset_title_button = QPushButton("Reset")
        reset_title_button.setToolTip("Reset title to default")
        reset_title_button.clicked.connect(self._reset_title)
        title_row.addWidget(reset_title_button)
        title_group_layout.addLayout(title_row)
        
        # Subtitle row
        subtitle_row = QHBoxLayout()
        subtitle_row.addWidget(QLabel("Subtitle:"))
        self.subtitle_edit = QLineEdit()
        subtitle_row.addWidget(self.subtitle_edit, stretch=1)
        reset_subtitle_button = QPushButton("Reset")
        reset_subtitle_button.setToolTip("Reset subtitle to default")
        reset_subtitle_button.clicked.connect(self._reset_subtitle)
        subtitle_row.addWidget(reset_subtitle_button)
        title_group_layout.addLayout(subtitle_row)
        
        bottom_layout.addWidget(title_group)
        
        # Export buttons
        export_group = QGroupBox("Export")
        export_layout = QHBoxLayout(export_group)
        export_layout.setContentsMargins(5, 5, 5, 5)
        save_button = QPushButton("Save Plot")
        save_button.clicked.connect(self._save_plot)
        export_layout.addWidget(save_button)
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self._copy_plot)
        export_layout.addWidget(copy_button)
        bottom_layout.addWidget(export_group)
        
        layout.addLayout(bottom_layout)
        
        self.setCentralWidget(central_widget)
        
        # Connect filter signals
        self.amb_check.stateChanged.connect(self._update_plot)
        self.hot_check.stateChanged.connect(self._update_plot)
        self.cold_check.stateChanged.connect(self._update_plot)
        self.pri_check.stateChanged.connect(self._update_plot)
        self.red_check.stateChanged.connect(self._update_plot)
        
        # Connect axis spinbox changes to plot update
        self.x_min_spin.valueChanged.connect(self._update_plot)
        self.x_max_spin.valueChanged.connect(self._update_plot)
        self.y_min_spin.valueChanged.connect(self._update_plot)
        self.y_max_spin.valueChanged.connect(self._update_plot)
        
        # Connect title and subtitle edits to update plot
        self.title_edit.editingFinished.connect(self._on_title_changed)
        self.subtitle_edit.editingFinished.connect(self._on_subtitle_changed)
        
        # Initial plot
        self._update_plot()
    
    def _populate_filters(self) -> None:
        """Populate S-parameter and path filters based on device configuration."""
        if self.test_setup_tab is None or self.test_setup_tab.current_device is None:
            return
        
        device = self.test_setup_tab.current_device
        
        # Populate S-parameter filters
        self._populate_s_param_filters(device)
        
        # Populate path filters (HG/LG if multi-gain)
        self._populate_path_filters(device)
    
    def _populate_s_param_filters(self, device) -> None:
        """Populate S-parameter checkboxes based on device configuration."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Clear existing checkboxes
        for checkbox in self.s_param_checks.values():
            self.s_param_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.s_param_checks.clear()
        
        # Get measurements to determine port count
        if not self.test_setup_tab or len(self.test_setup_tab.session_measurements) == 0:
            logger.warning("No session measurements available for populating S-parameter filters")
            return
        
        # Find first measurement with valid network data
        measurement = None
        for m in self.test_setup_tab.session_measurements:
            if m.device_id == device.id and m.test_type == "S-Parameters":
                if isinstance(m.touchstone_data, Network):
                    measurement = m
                    break
                elif isinstance(m.touchstone_data, bytes):
                    # Try to deserialize
                    try:
                        from ....core.rf_data.touchstone_loader import TouchstoneLoader
                        loader = TouchstoneLoader()
                        network = loader.deserialize_network(m.touchstone_data)
                        measurement = m
                        break
                    except Exception as e:
                        logger.debug(f"Failed to deserialize measurement {m.id}: {e}")
                        continue
        
        if measurement is None:
            logger.warning(f"No valid measurement found for device {device.id} to determine port count")
            return
        
        # Get network to determine ports
        if isinstance(measurement.touchstone_data, Network):
            network = measurement.touchstone_data
        else:
            from ....core.rf_data.touchstone_loader import TouchstoneLoader
            loader = TouchstoneLoader()
            network = loader.deserialize_network(measurement.touchstone_data)
        
        logger.debug(f"Using network with {network.nports} ports to determine S-parameters")
        
        # Get appropriate S-parameters based on plot type
        if self.is_vswr_plot or self.is_return_loss_plot:
            # For VSWR and Return Loss, use ALL ports in the network (1 to nports)
            # VSWR and Return Loss are measured at every port regardless of device config
            s_params = [f"S{p}{p}" for p in range(1, network.nports + 1)]
            logger.info(f"{'VSWR' if self.is_vswr_plot else 'Return Loss'} S-parameters for checkbox population: {s_params} (network has {network.nports} ports)")
            logger.info(f"Device config: input_ports={device.input_ports}, output_ports={device.output_ports}")
        else:
            s_params = device.get_gain_s_parameters(network.nports)
            logger.debug(f"Device gain S-parameters: {s_params}")
        
        # Create checkboxes for each S-parameter
        for s_param in s_params:
            checkbox = QCheckBox(s_param)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update_plot)
            self.s_param_checks[s_param] = checkbox
            self.s_param_layout.addWidget(checkbox)
            logger.debug(f"Created checkbox for {s_param}")
    
    def _populate_path_filters(self, device) -> None:
        """Add HG/LG checkboxes if device is in multi-gain mode."""
        # Clear existing HG/LG checkboxes
        for checkbox in self.path_hg_lg_checks.values():
            self.path_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.path_hg_lg_checks.clear()
        
        if not device.multi_gain_mode:
            return
        
        # Add HG/LG checkboxes to path layout
        pri_hg_check = QCheckBox("PRI_HG")
        pri_hg_check.setChecked(True)
        pri_hg_check.stateChanged.connect(self._update_plot)
        self.path_hg_lg_checks["PRI_HG"] = pri_hg_check
        self.path_layout.addWidget(pri_hg_check)
        
        pri_lg_check = QCheckBox("PRI_LG")
        pri_lg_check.setChecked(True)
        pri_lg_check.stateChanged.connect(self._update_plot)
        self.path_hg_lg_checks["PRI_LG"] = pri_lg_check
        self.path_layout.addWidget(pri_lg_check)
        
        red_hg_check = QCheckBox("RED_HG")
        red_hg_check.setChecked(True)
        red_hg_check.stateChanged.connect(self._update_plot)
        self.path_hg_lg_checks["RED_HG"] = red_hg_check
        self.path_layout.addWidget(red_hg_check)
        
        red_lg_check = QCheckBox("RED_LG")
        red_lg_check.setChecked(True)
        red_lg_check.stateChanged.connect(self._update_plot)
        self.path_hg_lg_checks["RED_LG"] = red_lg_check
        self.path_layout.addWidget(red_lg_check)
    
    def _reset_axis_limits(self) -> None:
        """Reset axis limits to auto-scale (0.0)."""
        self.x_min_spin.setValue(0.0)
        self.x_max_spin.setValue(0.0)
        self.y_min_spin.setValue(0.0)
        self.y_max_spin.setValue(0.0)
    
    def _on_title_changed(self) -> None:
        """Handle title edit field changes."""
        if self._title_updating:
            return
        
        new_title = self.title_edit.text()
        if not new_title.strip():
            return
        
        # Update suptitle if it exists
        if self.figure._suptitle is not None:
            self.figure._suptitle.set_text(new_title)
        else:
            # Create new suptitle
            self.figure.suptitle(new_title, fontsize=14, fontweight='bold', y=0.98)
        
        self.canvas.draw()
    
    def _on_legend_position_changed(self, position: str) -> None:
        """Handle legend position combo box changes."""
        self.legend_position = position
        self._update_plot()
    
    def _on_subtitle_changed(self) -> None:
        """Handle subtitle edit field changes."""
        if self._subtitle_updating:
            return
        
        new_subtitle = self.subtitle_edit.text()
        
        # Update subtitle if axes exist
        if self.figure.axes:
            ax = self.figure.axes[0]
            if ax.get_title():
                ax.set_title(new_subtitle, fontsize=10, style='italic', pad=10)
            self.canvas.draw()
    
    def _reset_title(self) -> None:
        """Reset title to default."""
        if self._default_title:
            self._title_updating = True
            self.title_edit.setText(self._default_title)
            self._title_updating = False
            self._update_plot()
    
    def _reset_subtitle(self) -> None:
        """Reset subtitle to default."""
        if self._default_subtitle:
            self._subtitle_updating = True
            self.subtitle_edit.setText(self._default_subtitle)
            self._subtitle_updating = False
            self._update_plot()
    
    def _reset_x_axis_label(self) -> None:
        """Reset X-axis label to default."""
        self.x_axis_label_edit.setText("Frequency (GHz)")
        self._update_plot()
    
    def _reset_y_axis_label(self) -> None:
        """Reset Y-axis label to default."""
        self.y_axis_label_edit.setText(self._default_y_label)
        self._update_plot()
    
    def _get_selected_temperatures(self) -> Set[str]:
        """Get set of selected temperatures."""
        selected = set()
        if self.amb_check.isChecked():
            selected.add("AMB")
        if self.hot_check.isChecked():
            selected.add("HOT")
        if self.cold_check.isChecked():
            selected.add("COLD")
        return selected
    
    def _get_selected_paths(self) -> Set[str]:
        """Get set of selected path types."""
        selected = set()
        if self.pri_check.isChecked():
            selected.add("PRI")
        if self.red_check.isChecked():
            selected.add("RED")
        
        # Add HG/LG if checked and multi-gain mode
        for path_type, checkbox in self.path_hg_lg_checks.items():
            if checkbox.isChecked():
                selected.add(path_type)
        
        return selected
    
    def _get_selected_s_params(self) -> Set[str]:
        """Get set of selected S-parameters."""
        selected = set()
        for s_param, checkbox in self.s_param_checks.items():
            if checkbox.isChecked():
                selected.add(s_param)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Selected S-parameters from checkboxes: {sorted(selected)}")
        logger.info(f"Available S-parameter checkboxes: {sorted(self.s_param_checks.keys())}")
        logger.info(f"Total checkboxes: {len(self.s_param_checks)}, Selected: {len(selected)}")
        
        return selected
    
    def _get_gain_range_criteria(self, device, test_stage: str) -> Optional[TestCriteria]:
        """Get Gain Range criteria for the device and test stage."""
        if self.compliance_service.criteria_repo is None:
            return None
        
        criteria = self.compliance_service.criteria_repo.get_by_device_and_test(
            device.id, "S-Parameters", test_stage
        )
        
        # Find "Gain Range" criteria
        for criterion in criteria:
            if criterion.requirement_name == "Gain Range" and criterion.criteria_type == "range":
                return criterion
        
        return None
    
    def _get_vswr_max_criteria(self, device, test_stage: str) -> Optional[TestCriteria]:
        """Get VSWR Max criteria for the device and test stage."""
        if self.compliance_service.criteria_repo is None:
            return None
        
        criteria = self.compliance_service.criteria_repo.get_by_device_and_test(
            device.id, "S-Parameters", test_stage
        )
        
        # Find "VSWR Max" criteria
        for criterion in criteria:
            if criterion.requirement_name == "VSWR Max" and criterion.criteria_type == "max":
                return criterion
        
        return None
    
    def _update_plot(self) -> None:
        """
        Request plot update - starts background processing.
        
        This method only:
        1. Gets filter selections
        2. Starts background worker
        3. UI updates happen in _render_plot_data() when data is ready
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("_update_plot() called - starting background processing")
        
        # Clear previous plot
        self.figure.clear()
        self.figure.subplots_adjust(top=0.88)
        ax = self.figure.add_subplot(111)
        
        # Show loading message
        ax.text(0.5, 0.5, "Processing plot data...",
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        self.canvas.draw()
        
        # Get current device and session measurements
        if self.test_setup_tab is None or self.test_setup_tab.current_device is None:
            ax.text(0.5, 0.5, "No device selected.\nPlease select a device in the Test Setup tab.",
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            self.canvas.draw()
            return
        
        device = self.test_setup_tab.current_device
        measurements = self.test_setup_tab.session_measurements
        
        if len(measurements) == 0:
            ax.text(0.5, 0.5, "No measurements loaded.\nPlease load measurement files in the Test Setup tab.",
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            self.canvas.draw()
            return
        
        # Ensure filters are populated
        if len(self.s_param_checks) == 0 and len(measurements) > 0:
            logger.info("Populating filters from measurements")
            self._populate_filters()
        
        # Get filter selections
        selected_temps = self._get_selected_temperatures()
        selected_paths = self._get_selected_paths()
        selected_s_params = self._get_selected_s_params()
        test_stage = self.test_setup_tab.current_test_stage
        
        # Stop any existing worker
        if self.plotting_worker and self.plotting_worker.isRunning():
            logger.info("Stopping previous plotting worker")
            self.plotting_worker.terminate()
            self.plotting_worker.wait()
        
        # Create and start background worker
        self.plotting_worker = PlottingWorker(
            database_path=self.database_path,
            plotting_service=self.plotting_service,
            device=device,
            measurements=measurements,
            plot_type=self.plot_type,
            selected_temperatures=selected_temps,
            selected_paths=selected_paths,
            selected_s_params=selected_s_params,
            test_stage=test_stage
        )
        
        # Connect signals
        self.plotting_worker.data_ready.connect(self._render_plot_data)
        self.plotting_worker.error_occurred.connect(self._handle_plot_error)
        
        # Start worker (runs in background thread)
        logger.info("Starting background plotting worker")
        self.plotting_worker.start()
    
    def _calculate_linewidth_for_scale(self, ax) -> float:
        """
        Calculate linewidth in points based on y-axis scale.
        
        This ensures threshold lines appear the same relative thickness
        across different plot types (Gain in dB, VSWR, Return Loss in dB).
        
        Calculates linewidth as a fixed fraction of the axis height in points.
        
        Args:
            ax: Matplotlib axis object (must have y-axis limits already set)
            
        Returns:
            Linewidth in points that will appear consistent across scales
        """
        # Get figure and axis dimensions
        fig = ax.get_figure()
        fig_width_inches, fig_height_inches = fig.get_size_inches()
        
        # Get axis position in figure coordinates (0-1)
        bbox = ax.get_position()
        axis_height_fraction = bbox.height
        
        # Calculate actual axis height in inches
        axis_height_inches = axis_height_fraction * fig_height_inches
        
        # Target: line should be a fixed fraction of axis height
        # Using 0.5% of axis height gives a visible but not too thick line
        target_fraction = 0.005
        
        # Calculate target height in inches, then convert to points
        target_inches = axis_height_inches * target_fraction
        target_points = target_inches * 72  # 72 points per inch
        
        # Clamp to reasonable range (1.0 to 4.0 points)
        # This ensures lines are visible but not too thick
        return max(1.0, min(4.0, target_points))
    
    def _get_units_per_point(self, ax) -> Tuple[float, float]:
        """
        Calculate how many data units correspond to one point on each axis.
        
        Returns:
            Tuple (x_units_per_point, y_units_per_point)
        """
        fig = ax.get_figure()
        bbox = ax.get_position()
        axis_width_inches = bbox.width * fig.get_figwidth()
        axis_height_inches = bbox.height * fig.get_figheight()
        
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        x_range = abs(x_max - x_min)
        y_range = abs(y_max - y_min)
        
        if axis_width_inches <= 0 or x_range == 0:
            x_units_per_point = 0.0
        else:
            x_units_per_point = x_range / (axis_width_inches * 72.0)
        
        if axis_height_inches <= 0 or y_range == 0:
            y_units_per_point = 0.0
        else:
            y_units_per_point = y_range / (axis_height_inches * 72.0)
        
        return x_units_per_point, y_units_per_point

    def _add_hash_marks(
        self,
        ax,
        x_start: float,
        x_end: float,
        y_value: float,
        orientation: str,
        color: str,
        base_linewidth: float
    ) -> None:
        """
        Draw diagonal hash marks with consistent visual size along a horizontal line.
        
        Args:
            ax: Matplotlib axis
            x_start: Starting x coordinate (data units)
            x_end: Ending x coordinate (data units)
            y_value: Base y coordinate of the line (data units)
            orientation: 'up' for hashes above line, 'down' for hashes below line
            color: Line color
            base_linewidth: Base linewidth for scaling hash stroke width
        """
        if x_end <= x_start:
            return
        
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        x_start = max(x_start, x_min)
        x_end = min(x_end, x_max)
        if x_end <= x_start:
            return
        
        x_units_per_point, y_units_per_point = self._get_units_per_point(ax)
        if x_units_per_point == 0.0 or y_units_per_point == 0.0:
            return
        
        # Define segment size and spacing in points
        segment_length_points = 14.0
        spacing_points = 18.0
        stroke_linewidth = max(1.0, base_linewidth * 0.6)
        
        dx_points = segment_length_points / math.sqrt(2)
        dy_points = dx_points  # For 45-degree diagonal
        dx_data = dx_points * x_units_per_point
        dy_data = dy_points * y_units_per_point
        spacing_data = spacing_points * x_units_per_point
        
        if spacing_data <= 0:
            spacing_data = (x_end - x_start) / 10.0
        if spacing_data <= 0:
            spacing_data = x_units_per_point * segment_length_points
        if spacing_data <= 0:
            return
        
        segment_centers: List[float] = []
        span = x_end - x_start
        if span <= 0:
            return
        if spacing_data >= span:
            segment_centers.append((x_start + x_end) / 2.0)
        else:
            x = x_start + spacing_data / 2.0
            while x < x_end:
                segment_centers.append(x)
                x += spacing_data
            if not segment_centers:
                segment_centers.append((x_start + x_end) / 2.0)
        
        segments = []
        for center in segment_centers:
            if orientation == 'up':
                start = (center - dx_data / 2.0, y_value)
                end = (center + dx_data / 2.0, y_value + dy_data)
                # Clamp within axis limits
                if end[1] > y_max:
                    delta = end[1] - y_max
                    end = (end[0], y_max)
                    start = (start[0], start[1] - delta)
                if start[1] < y_min:
                    start = (start[0], y_min)
            else:
                start = (center - dx_data / 2.0, y_value - dy_data)
                end = (center + dx_data / 2.0, y_value)
                if start[1] < y_min:
                    delta = y_min - start[1]
                    start = (start[0], y_min)
                    end = (end[0], min(end[1] + delta, y_max))
                if end[1] > y_max:
                    end = (end[0], y_max)
                    start = (start[0], max(start[1], y_min))
            
            if y_min <= start[1] <= y_max or y_min <= end[1] <= y_max:
                segments.append([start, end])
        
        if not segments:
            return
        
        collection = LineCollection(
            segments,
            colors=color,
            linewidths=stroke_linewidth,
            zorder=0.9
        )
        collection.set_capstyle('round')
        ax.add_collection(collection)

    def _apply_fixed_ticks(self, ax) -> None:
        """Force axes to display 10 uniform intervals regardless of limits."""
        import numpy as np
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        
        if not math.isclose(x_min, x_max):
            x_ticks = np.linspace(x_min, x_max, 11)
            ax.set_xticks(x_ticks)
            ax.set_xticklabels([f"{tick:.3f}" for tick in x_ticks])
        if not math.isclose(y_min, y_max):
            y_ticks = np.linspace(y_min, y_max, 11)
            ax.set_yticks(y_ticks)
        
        ax.tick_params(axis='x', which='major', labelsize=10, bottom=True, labelbottom=True, length=5, width=1)
        ax.tick_params(axis='y', which='major', labelsize=10, left=True, labelleft=True, length=5, width=1)

    def _render_plot_data(self, plot_data: PlotData) -> None:
        """
        Render plot data to the display.
        
        This method ONLY updates the UI - all processing is already done.
        Called when background worker finishes processing.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Rendering plot data: {len(plot_data.traces)} traces")
        
        # Clear figure
        self.figure.clear()
        self.figure.subplots_adjust(top=0.88, bottom=0.15)  # Leave room for x-axis labels
        ax = self.figure.add_subplot(111)
        
        # Check if we have data
        if not plot_data.traces:
            ax.text(0.5, 0.5, "No data to plot.\nCheck filters and data.",
                   ha='center', va='center', transform=ax.transAxes, fontsize=12,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            ax.set_xlabel(plot_data.default_x_label)
            ax.set_ylabel(plot_data.default_y_label)
            self.canvas.draw()
            return
        
        # Calculate default frequency range
        freq_range = plot_data.freq_max - plot_data.freq_min
        freq_padding = freq_range * 0.1
        default_x_min = max(0.0, plot_data.freq_min - freq_padding)
        default_x_max = plot_data.freq_max + freq_padding
        
        # Set title and subtitle early
        title = f"{plot_data.device_name} - {plot_data.plot_type}"
        subtitle_parts = [f"Serial: {plot_data.serial_number}", f"Stage: {plot_data.test_stage}"]
        if plot_data.measurement_dates:
            subtitle_parts.append(f"Dates: {', '.join(plot_data.measurement_dates)}")
        subtitle = " | ".join(subtitle_parts)
        
        self._default_title = title
        self._default_subtitle = subtitle
        
        display_title = self.title_edit.text() if self.title_edit.text().strip() else title
        display_subtitle = self.subtitle_edit.text() if self.subtitle_edit.text().strip() else subtitle
        
        self._title_updating = True
        self._subtitle_updating = True
        self.figure.suptitle(display_title, fontsize=14, fontweight='bold', y=0.98)
        ax.set_title(display_subtitle, fontsize=10, style='italic', pad=10)
        self._title_updating = False
        self._subtitle_updating = False
        
        if not self.title_edit.text().strip() or self.title_edit.text() == title:
            self._title_updating = True
            self.title_edit.setText(title)
            self._title_updating = False
        
        if not self.subtitle_edit.text().strip() or self.subtitle_edit.text() == subtitle:
            self._subtitle_updating = True
            self.subtitle_edit.setText(subtitle)
            self._subtitle_updating = False
        
        # Set axis labels
        x_label = self.x_axis_label_edit.text() or plot_data.default_x_label
        y_label = self.y_axis_label_edit.text() or plot_data.default_y_label
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        
        # Store pass region info for later (will draw after axis limits are set)
        pass_region_info = plot_data.pass_region
        
        # Plot all traces first
        plotted_lines = []
        for trace in plot_data.traces:
            # Ensure values are 1D array
            import numpy as np
            values = np.asarray(trace.values)
            if values.ndim > 1:
                # If 2D, flatten or take first column
                values = values.flatten() if values.size == len(trace.frequencies) else values[:, 0]
            
            lines = ax.plot(trace.frequencies, values, label=trace.label, linewidth=2)
            # ax.plot always returns a list, get the first Line2D object
            plotted_lines.append(lines[0])
        
        # Add legend and grid
        if plotted_lines:
            ax.legend(loc=self.legend_position)
        ax.grid(True, alpha=0.3)
        
        # Apply axis limits FIRST (needed for linewidth calculation)
        x_min_set = self.x_min_spin.value()
        x_max_set = self.x_max_spin.value()
        y_min_set = self.y_min_spin.value()
        y_max_set = self.y_max_spin.value()
        
        # X-axis limits
        if x_min_set == 0.0 and x_max_set == 0.0:
            x_min = default_x_min
            x_max = default_x_max
            ax.set_xlim(x_min, x_max)
        else:
            if x_max_set <= x_min_set:
                x_min = default_x_min
                x_max = default_x_max
                ax.set_xlim(x_min, x_max)
            else:
                x_min = x_min_set
                x_max = x_max_set
                ax.set_xlim(x_min, x_max)
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        
        # Y-axis limits
        if y_min_set == 0.0 and y_max_set == 0.0:
            if self.is_vswr_plot:
                ax.autoscale(axis='y')
                y_lims = ax.get_ylim()
                if y_lims[0] < 1.0:
                    ax.set_ylim(1.0, y_lims[1])
            elif self.is_return_loss_plot:
                # Return Loss: autoscale, but ensure reasonable range
                ax.autoscale(axis='y')
                y_lims = ax.get_ylim()
                # Return Loss is negative, so ensure we show negative values
                if y_lims[1] > 0:
                    ax.set_ylim(y_lims[0], 0.0)
        else:
            if y_max_set <= y_min_set:
                if self.is_vswr_plot:
                    ax.autoscale(axis='y')
                    y_lims = ax.get_ylim()
                    if y_lims[0] < 1.0:
                        ax.set_ylim(1.0, y_lims[1])
                elif self.is_return_loss_plot:
                    ax.autoscale(axis='y')
                    y_lims = ax.get_ylim()
                    if y_lims[1] > 0:
                        ax.set_ylim(y_lims[0], 0.0)
            else:
                if self.is_vswr_plot and y_min_set < 1.0 and y_min_set > 0.0:
                    y_min_set = 1.0
                ax.set_ylim(y_min_set, y_max_set)
        
        # Ensure autoscaled limits include acceptance thresholds
        if pass_region_info and y_min_set == 0.0 and y_max_set == 0.0:
            current_y_min, current_y_max = ax.get_ylim()
            y_span = current_y_max - current_y_min
            padding = y_span * 0.05 if y_span != 0 else 0.1
            
            adj_y_min = current_y_min
            adj_y_max = current_y_max
            
            if pass_region_info.value_min is not None:
                adj_y_min = min(adj_y_min, pass_region_info.value_min - padding)
                adj_y_max = max(adj_y_max, pass_region_info.value_min + padding)
            if pass_region_info.value_max is not None:
                adj_y_min = min(adj_y_min, pass_region_info.value_max - padding)
                adj_y_max = max(adj_y_max, pass_region_info.value_max + padding)
            
            if self.is_vswr_plot:
                adj_y_min = max(adj_y_min, 1.0)
            if self.is_return_loss_plot:
                adj_y_max = min(adj_y_max, 0.0)
            
            if adj_y_min != current_y_min or adj_y_max != current_y_max:
                if adj_y_min == adj_y_max:
                    adj_y_min -= 0.1
                    adj_y_max += 0.1
                ax.set_ylim(adj_y_min, adj_y_max)
        
        # NOW draw pass region with dynamically calculated linewidth
        if pass_region_info:
            # Calculate linewidth based on y-axis scale (ensures consistent appearance across plot types)
            dynamic_linewidth = self._calculate_linewidth_for_scale(ax)
            
            if pass_region_info.value_min is not None and pass_region_info.value_max is not None:
                # Gain range: two lines with hash marks pointing inward
                # Lower limit: hash marks above (pointing upward)
                min_line_y = pass_region_info.value_min
                # Draw line only across operational region with dynamically calculated linewidth
                line, = ax.plot(
                    [pass_region_info.freq_min, pass_region_info.freq_max],
                    [min_line_y, min_line_y],
                    color='green',
                    linestyle='-',
                    label='Gain Min',
                    zorder=1
                )
                line.set_linewidth(dynamic_linewidth)
                self._add_hash_marks(
                    ax=ax,
                    x_start=pass_region_info.freq_min,
                    x_end=pass_region_info.freq_max,
                    y_value=min_line_y,
                    orientation='up',
                    color='green',
                    base_linewidth=dynamic_linewidth
                )
                
                # Upper limit: hash marks below (pointing downward)
                max_line_y = pass_region_info.value_max
                # Draw line only across operational region with dynamically calculated linewidth
                line, = ax.plot(
                    [pass_region_info.freq_min, pass_region_info.freq_max],
                    [max_line_y, max_line_y],
                    color='green',
                    linestyle='-',
                    label='Gain Max',
                    zorder=1
                )
                line.set_linewidth(dynamic_linewidth)
                self._add_hash_marks(
                    ax=ax,
                    x_start=pass_region_info.freq_min,
                    x_end=pass_region_info.freq_max,
                    y_value=max_line_y,
                    orientation='down',
                    color='green',
                    base_linewidth=dynamic_linewidth
                )
            elif pass_region_info.value_max is not None:
                # VSWR max or Return Loss max: single line with hash marks below
                threshold_y = pass_region_info.value_max
                # Draw line only across operational region with dynamically calculated linewidth
                line, = ax.plot(
                    [pass_region_info.freq_min, pass_region_info.freq_max],
                    [threshold_y, threshold_y],
                    color='green',
                    linestyle='-',
                    label='Threshold' if not self.is_return_loss_plot else 'Return Loss Threshold',
                    zorder=1
                )
                line.set_linewidth(dynamic_linewidth)
                self._add_hash_marks(
                    ax=ax,
                    x_start=pass_region_info.freq_min,
                    x_end=pass_region_info.freq_max,
                    y_value=threshold_y,
                    orientation='down',
                    color='green',
                    base_linewidth=dynamic_linewidth
                )
        
        # Enable hover tips
        if MPLCURSORS_AVAILABLE and plotted_lines:
            try:
                if hasattr(self, '_hover_cursor'):
                    try:
                        self._hover_cursor.remove()
                    except:
                        pass
                
                cursor = mplcursors.cursor(plotted_lines, hover=True, multiple=False)
                
                def format_annotation(sel):
                    x_val = sel.target[0]
                    y_val = sel.target[1]
                    if self.is_vswr_plot:
                        sel.annotation.set_text(f"Freq: {x_val:.3f} GHz\nVSWR: {y_val:.2f}")
                    elif self.is_return_loss_plot:
                        sel.annotation.set_text(f"Freq: {x_val:.3f} GHz\nReturn Loss: {y_val:.2f} dB")
                    else:
                        sel.annotation.set_text(f"Freq: {x_val:.3f} GHz\nGain: {y_val:.2f} dB")
                
                cursor.connect("add", format_annotation)
                self._hover_cursor = cursor
            except Exception as e:
                logger.warning(f"Failed to enable mplcursors: {e}")
        
        # Apply fixed tick spacing (10 intervals) and ensure space for labels
        self._apply_fixed_ticks(ax)
        self.figure.subplots_adjust(bottom=0.15)
        
        # Draw plot
        self.canvas.draw()
        
        logger.info(f"Plot rendered with {len(plotted_lines)} traces")
    
    def _handle_plot_error(self, error_msg: str) -> None:
        """Handle error from background worker."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(error_msg)
        
        StatusBarMessage.show_warning(
            self.status_bar,
            f"Error preparing plot: {error_msg[:100]}..." if len(error_msg) > 100 else f"Error preparing plot: {error_msg}",
            timeout=10000  # Show for 10 seconds
        )
        
        # Show error message on plot
        self.figure.clear()
        self.figure.subplots_adjust(top=0.88)
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error preparing plot data.\n\n{error_msg[:200]}...",
               ha='center', va='center', transform=ax.transAxes, fontsize=12,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        self.canvas.draw()
    
    def _save_plot(self) -> None:
        """Save plot to file."""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.figure.savefig(file_path)
            StatusBarMessage.show_info(self.status_bar, f"Plot saved to {file_path}")
    
    def _copy_plot(self) -> None:
        """Copy plot to clipboard."""
        try:
            import io
            from PyQt6.QtGui import QImage
            
            # Get clipboard
            clipboard = QApplication.clipboard()
            
            # Save figure to bytes buffer as PNG
            buf = io.BytesIO()
            self.figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            
            # Convert bytes to QImage
            qimage = QImage()
            qimage.loadFromData(buf.getvalue())
            
            # Copy to clipboard
            clipboard.setImage(qimage)
            
            StatusBarMessage.show_info(self.status_bar, "Plot copied to clipboard")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to copy plot to clipboard: {e}")
            import traceback
            logger.error(traceback.format_exc())
            StatusBarMessage.show_warning(
                self.status_bar,
                f"Failed to copy plot to clipboard: {e}"
            )
    
    def refresh_data(self) -> None:
        """Refresh plot data."""
        self._populate_filters()
        self._update_plot()
