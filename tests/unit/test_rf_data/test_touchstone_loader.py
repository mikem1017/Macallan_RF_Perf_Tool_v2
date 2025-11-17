"""Unit tests for Touchstone loader."""

import pytest
from pathlib import Path

from src.core.rf_data.touchstone_loader import TouchstoneLoader
from src.core.exceptions import FileLoadError


class TestTouchstoneLoader:
    """Test Touchstone file loading."""
    
    @pytest.fixture
    def loader(self):
        """Provide a Touchstone loader instance."""
        try:
            return TouchstoneLoader()
        except FileLoadError:
            pytest.skip("scikit-rf not installed")
    
    def test_load_s4p_file(self, loader):
        """Test loading a real S4P file."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        
        network = loader.load_file(filepath)
        
        assert network is not None
        assert network.nports == 4
        assert len(network.f) > 0  # Should have frequency points
    
    def test_load_with_metadata(self, loader):
        """Test loading file with metadata parsing."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        
        network, metadata = loader.load_with_metadata(filepath)
        
        assert network is not None
        assert metadata["serial_number"] == "SN0001"
        assert metadata["part_number"] == "L109908"
        assert metadata["path_type"] == "PRI"
    
    def test_load_nonexistent_file(self, loader):
        """Test loading non-existent file raises error."""
        filepath = Path("nonexistent.s4p")
        
        with pytest.raises(FileLoadError, match="File not found"):
            loader.load_file(filepath)
    
    def test_serialize_deserialize(self, loader):
        """Test serializing and deserializing Network objects."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
        network = loader.load_file(filepath)
        
        # Serialize
        serialized = loader.serialize_network(network)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize
        deserialized = loader.deserialize_network(serialized)
        assert deserialized is not None
        assert deserialized.nports == network.nports
        assert len(deserialized.f) == len(network.f)
    
    def test_load_red_file(self, loader):
        """Test loading RED path file."""
        filepath = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_RED.s4p")
        
        network, metadata = loader.load_with_metadata(filepath)
        
        assert network is not None
        assert metadata["path_type"] == "RED"













