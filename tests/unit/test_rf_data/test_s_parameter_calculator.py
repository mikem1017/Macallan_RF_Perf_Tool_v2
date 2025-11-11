"""Unit tests for S-Parameter calculator."""

import pytest
import numpy as np
from pathlib import Path

from src.core.rf_data.touchstone_loader import TouchstoneLoader
from src.core.rf_data.s_parameter_calculator import SParameterCalculator
from src.core.exceptions import FileLoadError


class TestSParameterCalculator:
    """Test S-Parameter calculations with real data."""
    
    @pytest.fixture
    def loader(self):
        """Provide a Touchstone loader."""
        try:
            return TouchstoneLoader()
        except FileLoadError:
            pytest.skip("scikit-rf not installed")
    
    @pytest.fixture
    def calculator(self):
        """Provide an S-Parameter calculator."""
        try:
            return SParameterCalculator()
        except FileLoadError:
            pytest.skip("scikit-rf not installed")
    
    @pytest.fixture
    def sample_network(self, loader):
        """Load a sample S4P network for testing."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        return loader.load_file(filepath)
    
    def test_filter_frequency_range(self, calculator, sample_network):
        """Test frequency range filtering."""
        # Filter to a subset of frequencies
        filtered = calculator.filter_frequency_range(
            sample_network, 1.0, 2.0  # 1-2 GHz
        )
        
        assert filtered is not None
        assert len(filtered.f) <= len(sample_network.f)
        
        # Check that frequencies are within range (or at boundaries)
        freq_ghz = filtered.f / 1e9
        assert np.isclose(freq_ghz[0], 1.0, atol=1e-6)
        assert np.isclose(freq_ghz[-1], 2.0, atol=1e-6)
        assert np.all(freq_ghz >= 1.0 - 1e-6)
        assert np.all(freq_ghz <= 2.0 + 1e-6)
    
    def test_calculate_gain_s21(self, calculator, sample_network):
        """Test gain calculation for S21."""
        gain = calculator.calculate_gain(sample_network, "S21")
        
        assert gain is not None
        assert len(gain) == len(sample_network.f)
        assert np.all(np.isfinite(gain))  # All values should be finite
    
    def test_calculate_gain_s31(self, calculator, sample_network):
        """Test gain calculation for S31 (4-port file)."""
        gain = calculator.calculate_gain(sample_network, "S31")
        
        assert gain is not None
        assert len(gain) == len(sample_network.f)
    
    def test_calculate_gain_range(self, calculator, sample_network):
        """Test gain range calculation over frequency range."""
        min_gain, max_gain = calculator.calculate_gain_range(
            sample_network, 1.0, 2.0, "S21"
        )
        
        assert isinstance(min_gain, float)
        assert isinstance(max_gain, float)
        assert max_gain >= min_gain
    
    def test_calculate_flatness(self, calculator, sample_network):
        """Test flatness calculation."""
        flatness = calculator.calculate_flatness(
            sample_network, 1.0, 2.0, "S21"
        )
        
        assert isinstance(flatness, float)
        assert flatness >= 0  # Flatness should be positive (max - min)
    
    def test_calculate_lowest_in_band_gain(self, calculator, sample_network):
        """Test lowest in-band gain calculation."""
        lowest = calculator.calculate_lowest_in_band_gain(
            sample_network, 1.0, 2.0, "S21"
        )
        
        assert isinstance(lowest, float)
        assert np.isfinite(lowest)
    
    def test_calculate_oob_rejection(self, calculator, sample_network):
        """Test OOB rejection calculation across a frequency range."""
        # Use operational range (1-2 GHz), then check OOB rejection across a range (3-5 GHz)
        # The calculator returns the worst-case (minimum) rejection across the OOB range
        rejection = calculator.calculate_oob_rejection(
            sample_network,
            oob_freq_min=3.0,   # OOB range minimum (3 GHz)
            oob_freq_max=5.0,   # OOB range maximum (5 GHz)
            operational_freq_min=1.0,
            operational_freq_max=2.0,
            s_param="S21"
        )
        
        assert isinstance(rejection, float)
        # Rejection should typically be positive (gain lower than in-band min)
        # This is the worst-case (minimum) rejection across the 3-5 GHz range
    
    def test_calculate_vswr(self, calculator, sample_network):
        """Test VSWR calculation."""
        vswr = calculator.calculate_vswr(
            sample_network,
            port=1,
            freq_min=1.0,
            freq_max=2.0
        )
        
        assert isinstance(vswr, float)
        assert vswr >= 1.0  # VSWR should be >= 1.0
    
    def test_get_available_s_params(self, calculator, sample_network):
        """Test getting available S-parameters."""
        s_params = calculator.get_available_s_params(sample_network)
        
        assert "S21" in s_params
        assert "S31" in s_params
        assert "S41" in s_params  # 4-port file should have S41
