"""Unit tests for Device model."""

import pytest
from pydantic import ValidationError

from src.core.models.device import Device
from src.core.exceptions import InvalidPartNumberError


class TestDeviceModel:
    """Test Device model validation and behavior."""
    
    def test_create_valid_device(self):
        """Test creating a valid device."""
        device = Device(
            name="Test Device",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1, 2],
            output_ports=[3, 4]
        )
        
        assert device.name == "Test Device"
        assert device.part_number == "L123456"
        assert device.multi_gain_mode is False
        assert device.tests_performed == []
        assert device.input_ports == [1, 2]
        assert device.output_ports == [3, 4]
        assert device.id is not None
    
    def test_part_number_validation_valid(self):
        """Test valid part number formats."""
        valid_numbers = ["L123456", "L000000", "L999999"]
        
        for pn in valid_numbers:
            device = Device(
                name="Test",
                part_number=pn,
                operational_freq_min=0.5,
                operational_freq_max=2.0,
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[1],
                output_ports=[2]
            )
            assert device.part_number == pn
    
    def test_part_number_validation_invalid(self):
        """Test invalid part number formats raise error."""
        invalid_numbers = [
            "L12345",      # Too short
            "L1234567",    # Too long
            "l123456",     # Lowercase L
            "L12345a",     # Non-numeric
            "X123456",     # Wrong letter
            "123456",      # Missing L
        ]
        
        for pn in invalid_numbers:
            with pytest.raises(InvalidPartNumberError):
                Device(
                    name="Test",
                    part_number=pn,
                    operational_freq_min=0.5,
                    operational_freq_max=2.0,
                    wideband_freq_min=0.1,
                    wideband_freq_max=5.0,
                    input_ports=[1],
                    output_ports=[2]
                )
    
    def test_frequency_validation_operational(self):
        """Test that operational freq min must be less than max."""
        with pytest.raises(ValidationError, match="operational_freq_min.*must be less"):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=2.0,
                operational_freq_max=1.0,  # Invalid: min >= max
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[1],
                output_ports=[2]
            )
    
    def test_frequency_validation_wideband(self):
        """Test that wideband freq min must be less than max."""
        with pytest.raises(ValidationError, match="wideband_freq_min.*must be less"):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=0.5,
                operational_freq_max=2.0,
                wideband_freq_min=5.0,
                wideband_freq_max=0.1,  # Invalid: min >= max
                input_ports=[1],
                output_ports=[2]
            )
    
    def test_frequency_validation_positive(self):
        """Test that frequencies must be positive."""
        with pytest.raises(ValidationError):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=-0.5,  # Invalid: negative
                operational_freq_max=2.0,
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[1],
                output_ports=[2]
            )
    
    def test_multi_gain_mode(self):
        """Test multi-gain mode setting."""
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            multi_gain_mode=True,
            input_ports=[1],
            output_ports=[2]
        )
        
        assert device.multi_gain_mode is True
    
    def test_tests_performed_list(self):
        """Test tests_performed can be set."""
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            tests_performed=["S-Parameters", "Power/Linearity"],
            input_ports=[1],
            output_ports=[2]
        )
        
        assert device.tests_performed == ["S-Parameters", "Power/Linearity"]
    
    def test_port_configuration_validation(self):
        """Test port configuration validation."""
        # Valid configuration
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1, 2],
            output_ports=[3, 4]
        )
        
        assert device.input_ports == [1, 2]
        assert device.output_ports == [3, 4]
        assert device.get_all_ports() == [1, 2, 3, 4]
    
    def test_port_configuration_overlap_validation(self):
        """Test that ports cannot overlap between input and output."""
        with pytest.raises(ValueError, match="Ports cannot be both input and output"):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=0.5,
                operational_freq_max=2.0,
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[1, 2],
                output_ports=[2, 3]  # Port 2 overlaps
            )
    
    def test_port_configuration_empty_validation(self):
        """Test that input and output ports cannot be empty."""
        with pytest.raises(ValueError, match="At least one input port"):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=0.5,
                operational_freq_max=2.0,
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[],  # Empty
                output_ports=[1, 2]
            )
        
        with pytest.raises(ValueError, match="At least one output port"):
            Device(
                name="Test",
                part_number="L123456",
                operational_freq_min=0.5,
                operational_freq_max=2.0,
                wideband_freq_min=0.1,
                wideband_freq_max=5.0,
                input_ports=[1, 2],
                output_ports=[]  # Empty
            )
    
    def test_get_gain_s_parameters(self):
        """Test getting gain S-parameters from port configuration."""
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1, 2],
            output_ports=[3, 4]
        )
        
        # For 4-port device: inputs=[1,2], outputs=[3,4]
        # Gain S-parameters: S31, S32, S41, S42
        gain_params = device.get_gain_s_parameters(4)
        assert "S31" in gain_params
        assert "S32" in gain_params
        assert "S41" in gain_params
        assert "S42" in gain_params
        assert len(gain_params) == 4
    
    def test_get_vswr_s_parameters(self):
        """Test getting VSWR S-parameters from port configuration."""
        device = Device(
            name="Test",
            part_number="L123456",
            operational_freq_min=0.5,
            operational_freq_max=2.0,
            wideband_freq_min=0.1,
            wideband_freq_max=5.0,
            input_ports=[1, 2],
            output_ports=[3, 4]
        )
        
        # VSWR for all ports: S11, S22, S33, S44
        vswr_params = device.get_vswr_s_parameters(4)
        assert "S11" in vswr_params
        assert "S22" in vswr_params
        assert "S33" in vswr_params
        assert "S44" in vswr_params
        assert len(vswr_params) == 4
