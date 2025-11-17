"""
Plotting service for RF measurement visualization.

This service handles ALL data processing for plotting:
- Filtering measurements
- Deserializing Network objects
- Calculating VSWR/gain from Network objects
- Preparing plot data structures

The GUI should ONLY call this service and update the display based on results.
All heavy processing happens here, not in the GUI.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from uuid import UUID
import numpy as np
import logging

from skrf import Network

from ..models.device import Device
from ..models.measurement import Measurement
from ..models.test_criteria import TestCriteria
from ..rf_data.s_parameter_calculator import SParameterCalculator
from ..rf_data.touchstone_loader import TouchstoneLoader


logger = logging.getLogger(__name__)


@dataclass
class PlotTrace:
    """A complete trace to plot (one line on the plot)."""
    label: str  # e.g., "AMB PRI Port 1 (S11)"
    s_parameter: str  # e.g., "S11"
    port: int  # Port number (1-indexed, 0 for gain)
    frequencies: np.ndarray  # Frequency array in GHz
    values: np.ndarray  # Gain (dB) or VSWR values
    temperature: str
    path_type: str


@dataclass
class PassRegion:
    """Pass region data for operational plots."""
    freq_min: float
    freq_max: float
    value_min: Optional[float] = None  # For gain range
    value_max: Optional[float] = None  # For gain range or VSWR max


@dataclass
class PlotData:
    """Complete plot data ready for display."""
    plot_type: str
    device_name: str
    serial_number: str
    test_stage: str
    measurement_dates: List[str]
    traces: List[PlotTrace]
    freq_min: float
    freq_max: float
    pass_region: Optional[PassRegion] = None
    default_x_label: str = "Frequency (GHz)"
    default_y_label: str = "Gain (dB)"
    

class PlottingService:
    """
    Service for processing plot data.
    
    All data processing happens here - filtering, calculations, etc.
    The GUI should only call methods and update displays based on results.
    """
    
    def __init__(self):
        """Initialize plotting service."""
        self.calculator = SParameterCalculator()
        self.loader = TouchstoneLoader()
    
    def prepare_plot_data(
        self,
        device: Device,
        measurements: List[Measurement],
        plot_type: str,
        selected_temperatures: Set[str],
        selected_paths: Set[str],
        selected_s_params: Set[str],
        test_stage: str,
        compliance_service: Optional[Any] = None  # Avoid circular import
    ) -> PlotData:
        """
        Prepare plot data from measurements.
        
        This is the main processing method. It:
        1. Filters measurements
        2. Deserializes Network objects
        3. Calculates VSWR or gain
        4. Returns structured data ready for plotting
        
        Args:
            device: Device configuration
            measurements: List of measurements to process
            plot_type: "Operational Gain", "Operational VSWR", etc.
            selected_temperatures: Set of selected temperatures (e.g., {"AMB", "HOT"})
            selected_paths: Set of selected paths (e.g., {"PRI", "RED"})
            selected_s_params: Set of selected S-parameters (e.g., {"S11", "S22"})
            test_stage: Test stage for criteria lookup
            compliance_service: Optional compliance service for pass region
            
        Returns:
            PlotData object with all traces and metadata ready for plotting
        """
        logger.info(f"Preparing plot data: plot_type={plot_type}, measurements={len(measurements)}")
        
        # Determine plot characteristics
        plot_type_lower = plot_type.lower()
        is_vswr_plot = "vswr" in plot_type_lower
        is_return_loss_plot = "return loss" in plot_type_lower
        is_wideband_plot = "wideband" in plot_type_lower
        
        # Get frequency range
        if is_wideband_plot:
            freq_min = device.wideband_freq_min
            freq_max = device.wideband_freq_max
        else:
            freq_min = device.operational_freq_min
            freq_max = device.operational_freq_max
        
        # Filter measurements
        filtered_measurements = self._filter_measurements(
            measurements, device, selected_temperatures, selected_paths
        )
        
        logger.info(f"Filtered to {len(filtered_measurements)} measurements")
        
        if not filtered_measurements:
            # Return empty plot data
            return PlotData(
                plot_type=plot_type,
                device_name=device.name,
                serial_number="",
                test_stage=test_stage,
                measurement_dates=[],
                traces=[],
                freq_min=freq_min,
                freq_max=freq_max,
                default_y_label=self._get_y_label(is_vswr_plot, is_return_loss_plot)
            )
        
        # Get single serial number (should be filtered to one)
        serial_numbers = set(m.serial_number for m in filtered_measurements)
        if len(serial_numbers) > 1:
            logger.warning(f"Multiple serial numbers: {serial_numbers}, using first")
        target_serial = list(serial_numbers)[0] if serial_numbers else ""
        filtered_measurements = [m for m in filtered_measurements if m.serial_number == target_serial]
        
        # Get measurement dates
        measurement_dates = sorted(set(str(m.measurement_date) for m in filtered_measurements))
        
        # Process each measurement and create traces
        traces: List[PlotTrace] = []
        
        for measurement in filtered_measurements:
            try:
                logger.debug(f"Processing measurement: {measurement.path_type}, {measurement.temperature}")
                
                # Deserialize Network if needed
                if isinstance(measurement.touchstone_data, Network):
                    network = measurement.touchstone_data
                else:
                    network = self.loader.deserialize_network(measurement.touchstone_data)
                
                # Filter to frequency range
                filtered_network = self.calculator.filter_frequency_range(
                    network, freq_min, freq_max
                )
                
                # Get appropriate S-parameters
                if is_vswr_plot or is_return_loss_plot:
                    # For VSWR and Return Loss, use ALL ports in the network
                    s_params = [f"S{p}{p}" for p in range(1, network.nports + 1)]
                else:
                    s_params = device.get_gain_s_parameters(network.nports)
                    logger.debug(
                        f"Gain S-parameters for device {device.name}: input_ports={device.input_ports}, "
                        f"output_ports={device.output_ports}, n_ports={network.nports}, "
                        f"returned s_params={s_params}"
                    )
                
                # If no S-params selected, use all available
                if not selected_s_params:
                    selected_s_params = set(s_params)
                    logger.debug(f"No S-params selected, using all available: {selected_s_params}")
                
                # Process each selected S-parameter
                logger.debug(f"Processing S-parameters: available={sorted(s_params)}, selected={sorted(selected_s_params)}")
                for s_param in s_params:
                    if s_param not in selected_s_params:
                        logger.debug(f"Skipping {s_param} - not in selected set")
                        continue
                    logger.debug(f"Processing {s_param} for {measurement.path_type}")
                    
                    # Calculate data
                    if is_vswr_plot or is_return_loss_plot:
                        # Extract port number
                        import re
                        match = re.match(r"S(\d+)(\d+)", s_param)
                        if not match:
                            logger.error(f"Invalid S-parameter format: {s_param}")
                            continue
                        port = int(match.group(1))
                        
                        if is_return_loss_plot:
                            # Calculate Return Loss
                            values = self.calculator.calculate_return_loss(
                                filtered_network, port=port, freq_min=None, freq_max=None
                            )
                        else:
                            # Calculate VSWR
                            values = self.calculator.calculate_vswr(
                                filtered_network, port=port, freq_min=None, freq_max=None
                            )
                            
                            # Verify VSWR values are reasonable
                            if np.allclose(values, 1.0, atol=0.001):
                                logger.warning(f"VSWR for {measurement.path_type} {s_param} is all 1.0 - may indicate data issue")
                    else:
                        # Calculate gain
                        values = self.calculator.calculate_gain(filtered_network, s_param)
                        port = 0  # Not applicable for gain
                    
                    # Get frequency array
                    frequencies = filtered_network.f / 1e9  # Convert Hz to GHz
                    
                    # Ensure arrays are same length
                    if len(frequencies) != len(values):
                        logger.error(f"Array length mismatch: freq={len(frequencies)}, values={len(values)}")
                        continue
                    
                    # Create label
                    if is_vswr_plot or is_return_loss_plot:
                        label = f"{measurement.temperature} {measurement.path_type} Port {port} ({s_param})"
                    else:
                        label = f"{measurement.temperature} {measurement.path_type} {s_param}"
                    
                    # Create trace
                    trace = PlotTrace(
                        label=label,
                        s_parameter=s_param,
                        port=port,
                        frequencies=frequencies,
                        values=values,
                        temperature=measurement.temperature,
                        path_type=measurement.path_type
                    )
                    traces.append(trace)
                    
            except Exception as e:
                logger.error(f"Error processing measurement {measurement.id}: {e}", exc_info=True)
                continue
        
        # Get pass region for operational plots
        pass_region = None
        if not is_wideband_plot and compliance_service and compliance_service.criteria_repo:
            if is_return_loss_plot:
                # Get VSWR Max criteria and convert to Return Loss
                criteria = compliance_service.criteria_repo.get_by_device_and_test(
                    device.id, "S-Parameters", test_stage
                )
                for criterion in criteria:
                    if criterion.requirement_name == "VSWR Max" and criterion.criteria_type == "max":
                        if criterion.max_value is not None:
                            # Convert VSWR Max to Return Loss Max (more negative is better)
                            return_loss_max = self.calculator.vswr_to_return_loss(criterion.max_value)
                            # For Return Loss, pass region is below the threshold (more negative = better)
                            # So value_max is the Return Loss threshold (e.g., -14 dB)
                            pass_region = PassRegion(
                                freq_min=freq_min,
                                freq_max=freq_max,
                                value_max=return_loss_max  # More negative values pass
                            )
                        break
            elif is_vswr_plot:
                # Get VSWR Max criteria
                criteria = compliance_service.criteria_repo.get_by_device_and_test(
                    device.id, "S-Parameters", test_stage
                )
                for criterion in criteria:
                    if criterion.requirement_name == "VSWR Max" and criterion.criteria_type == "max":
                        if criterion.max_value is not None:
                            pass_region = PassRegion(
                                freq_min=freq_min,
                                freq_max=freq_max,
                                value_max=criterion.max_value
                            )
                        break
            else:
                # Get Gain Range criteria
                criteria = compliance_service.criteria_repo.get_by_device_and_test(
                    device.id, "S-Parameters", test_stage
                )
                for criterion in criteria:
                    if criterion.requirement_name == "Gain Range" and criterion.criteria_type == "range":
                        if criterion.min_value is not None and criterion.max_value is not None:
                            pass_region = PassRegion(
                                freq_min=freq_min,
                                freq_max=freq_max,
                                value_min=criterion.min_value,
                                value_max=criterion.max_value
                            )
                        break
        
        return PlotData(
            plot_type=plot_type,
            device_name=device.name,
            serial_number=target_serial,
            test_stage=test_stage,
            measurement_dates=measurement_dates,
            traces=traces,
            freq_min=freq_min,
            freq_max=freq_max,
            pass_region=pass_region,
            default_y_label=self._get_y_label(is_vswr_plot, is_return_loss_plot)
        )
    
    def _get_y_label(self, is_vswr_plot: bool, is_return_loss_plot: bool) -> str:
        """Get appropriate Y-axis label based on plot type."""
        if is_return_loss_plot:
            return "Return Loss (dB)"
        elif is_vswr_plot:
            return "VSWR"
        else:
            return "Gain (dB)"
    
    def _filter_measurements(
        self,
        measurements: List[Measurement],
        device: Device,
        selected_temperatures: Set[str],
        selected_paths: Set[str]
    ) -> List[Measurement]:
        """Filter measurements by device, temperature, and path."""
        filtered = [
            m for m in measurements
            if m.device_id == device.id
            and m.test_type == "S-Parameters"
            and (len(selected_temperatures) == 0 or m.temperature in selected_temperatures)
            and (len(selected_paths) == 0 or m.path_type in selected_paths)
        ]
        return filtered
    
    def get_available_s_parameters(
        self,
        device: Device,
        network: Network,
        is_vswr_plot: bool
    ) -> List[str]:
        """
        Get list of available S-parameters for filtering.
        
        Args:
            device: Device configuration
            network: Network object to determine port count
            is_vswr_plot: True for VSWR plots, False for gain plots
            
        Returns:
            List of S-parameter strings (e.g., ["S11", "S22", "S33", "S44"])
        """
        if is_vswr_plot:
            # For VSWR, use ALL ports in the network
            return [f"S{p}{p}" for p in range(1, network.nports + 1)]
        else:
            return device.get_gain_s_parameters(network.nports)
