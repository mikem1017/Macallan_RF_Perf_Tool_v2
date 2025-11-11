"""
Touchstone file loader using scikit-rf.

This module provides functionality to load Touchstone files (S-parameter data)
using the scikit-rf library. Touchstone files are standard RF measurement files
with extensions like .s2p (2-port), .s4p (4-port), etc.

Key features:
- Loads Touchstone files (S2P to S10P supported)
- Parses filename metadata using FilenameParser
- Serializes/deserializes Network objects for database storage
- Handles scikit-rf import errors gracefully

The loader integrates with FilenameParser to extract metadata from filenames,
enabling automatic identification of serial numbers, part numbers, paths, etc.
"""

import pickle
from pathlib import Path
from typing import Optional, Union

# Try to import scikit-rf - handle gracefully if not installed
try:
    import skrf as rf
    from skrf import Network
    SKRF_AVAILABLE = True
except ImportError:
    SKRF_AVAILABLE = False
    Network = None

from ..exceptions import FileLoadError
from .filename_parser import FilenameParser


class TouchstoneLoader:
    """
    Load and manage Touchstone files using scikit-rf.
    
    Provides functionality to:
    - Load Touchstone files (.s2p, .s4p, etc.) into scikit-rf Network objects
    - Parse filename metadata automatically
    - Serialize Network objects for database storage (pickle)
    - Deserialize stored Network objects back for analysis
    
    The loader validates file existence and format before attempting to load,
    providing clear error messages for common issues.
    
    Network objects contain S-parameter data in complex format (magnitude/phase
    or real/imaginary). scikit-rf handles the file format details.
    """
    
    def __init__(self):
        """
        Initialize the loader.
        
        Checks for scikit-rf availability and initializes the filename parser.
        
        Raises:
            FileLoadError: If scikit-rf is not installed
        """
        if not SKRF_AVAILABLE:
            raise FileLoadError(
                "scikit-rf is not installed. Please install it with: pip install scikit-rf"
            )
        # Initialize filename parser for metadata extraction
        self.parser = FilenameParser()
    
    def load_file(self, filepath: Union[str, Path]) -> Network:
        """
        Load a Touchstone file using scikit-rf.
        
        Validates file existence and format, then uses scikit-rf to load
        the S-parameter data into a Network object.
        
        Args:
            filepath: Path to the Touchstone file (.s2p, .s4p, etc.)
                     Supports S2P through S10P files
            
        Returns:
            scikit-rf Network object containing S-parameter data
            Network has properties like:
            - network.f: frequency array (in Hz)
            - network.s: S-parameter matrix (complex values)
            - network.nports: number of ports
            
        Raises:
            FileLoadError: If file not found, wrong format, or loading fails
        """
        filepath = Path(filepath)
        
        # Validate file exists
        if not filepath.exists():
            raise FileLoadError(f"File not found: {filepath}")
        
        # Validate file extension (should start with .s followed by number)
        # Examples: .s2p, .s4p, .s10p
        if not filepath.suffix.lower().startswith('.s'):
            raise FileLoadError(
                f"File does not appear to be a Touchstone file: {filepath}. "
                f"Expected extension like .s2p, .s4p, etc."
            )
        
        try:
            # Use scikit-rf to load the Touchstone file
            # scikit-rf automatically handles format parsing (frequency, S-parameters, etc.)
            network = rf.Network(str(filepath))
            return network
        except Exception as e:
            # Wrap any loading errors in FileLoadError for consistent error handling
            raise FileLoadError(f"Failed to load Touchstone file {filepath}: {e}") from e
    
    def load_with_metadata(self, filepath: Union[str, Path]) -> tuple:
        """
        Load a Touchstone file and parse its filename for metadata.
        
        Convenience method that combines file loading and metadata extraction.
        Useful when you need both the RF data and the parsed filename information.
        
        Args:
            filepath: Path to the Touchstone file
            
        Returns:
            Tuple of (Network object, metadata dictionary)
            - Network: scikit-rf Network object with S-parameter data
            - metadata: Dictionary with parsed filename metadata:
              * date, serial_number, part_number, path_type, temperature, etc.
              
        Raises:
            FileLoadError: If file cannot be loaded or metadata cannot be extracted
        """
        # Load the RF data
        network = self.load_file(filepath)
        
        # Parse filename for metadata
        metadata = self.parser.parse(filepath)
        
        return network, metadata
    
    def serialize_network(self, network: Network) -> bytes:
        """
        Serialize a Network object to bytes for database storage.
        
        Network objects are complex Python objects that cannot be directly
        stored in SQLite. This method uses pickle to convert the Network
        object to a byte string that can be stored as a BLOB.
        
        The serialized data contains all Network properties:
        - Frequency array
        - S-parameter matrices
        - Port count
        - Metadata (if any)
        
        Args:
            network: scikit-rf Network object to serialize
            
        Returns:
            Serialized bytes (can be stored as BLOB in database)
            
        Raises:
            FileLoadError: If serialization fails
        """
        try:
            # Use pickle to serialize Network object to bytes
            # Pickle handles complex objects with nested arrays, etc.
            return pickle.dumps(network)
        except Exception as e:
            raise FileLoadError(f"Failed to serialize Network object: {e}") from e
    
    def deserialize_network(self, data: bytes) -> Network:
        """
        Deserialize bytes back to a Network object.
        
        Reverse operation of serialize_network. Converts stored bytes back
        into a scikit-rf Network object for analysis and calculations.
        
        Args:
            data: Serialized bytes (from database BLOB or previous serialization)
            
        Returns:
            scikit-rf Network object (fully functional, ready for analysis)
            
        Raises:
            FileLoadError: If deserialization fails (corrupted data, format mismatch, etc.)
        """
        try:
            # Use pickle to deserialize bytes back to Network object
            # Restores all Network properties and data structures
            return pickle.loads(data)
        except Exception as e:
            raise FileLoadError(f"Failed to deserialize Network object: {e}") from e
