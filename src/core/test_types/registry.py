"""
Test type registry for managing available test types.

This module implements the TestTypeRegistry, a singleton that manages all
available test type implementations. Test types are registered automatically
on first access and can be retrieved by name.

The registry pattern allows:
- Centralized test type management
- Dynamic discovery of available test types
- Easy extension (new test types register themselves)
- Consistent access point for test type retrieval

Usage:
    registry = TestTypeRegistry()
    test_type = registry.get("S-Parameters")
    all_types = registry.list_all()
"""

from typing import Dict, Optional

from .base import AbstractTestType
from .s_parameters import SParametersTestType


class TestTypeRegistry:
    """
    Registry for managing test type implementations.
    
    Singleton pattern ensures only one registry instance exists. Test types
    are registered automatically when the registry is first accessed.
    
    The registry provides:
    - Automatic registration of built-in test types (S-Parameters)
    - Manual registration of custom test types
    - Lookup by name
    - List of all available test types
    
    Extensibility:
    - New test types can be registered at runtime
    - Custom test types can be added by implementing AbstractTestType
    - Registry is used by GUI to populate test type dropdowns
    """
    
    # Singleton instance (class variable)
    _instance = None
    
    # Registry dictionary: test_type_name -> AbstractTestType instance
    _registry: Dict[str, AbstractTestType] = {}
    
    def __new__(cls):
        """
        Singleton pattern implementation.
        
        Ensures only one registry instance exists across the application.
        On first instantiation, creates instance and initializes with default
        test types. Subsequent calls return the same instance.
        
        Returns:
            TestTypeRegistry instance (same instance on all calls)
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """
        Initialize registry with default test types.
        
        Registers built-in test types automatically. This is called once
        when the registry is first created.
        
        Currently registers:
        - S-Parameters test type
        """
        # Register S-Parameters test type (built-in, always available)
        s_params = SParametersTestType()
        self.register(s_params)
    
    def register(self, test_type: AbstractTestType) -> None:
        """
        Register a test type in the registry.
        
        Allows adding new test types at runtime. Test type name must be
        unique. If a test type with the same name already exists, it will
        be overwritten.
        
        Args:
            test_type: AbstractTestType implementation to register
            
        Note:
            Test type name must be unique. Use get() to check if a test type
            with the same name already exists before registering.
        """
        self._registry[test_type.name] = test_type
    
    def get(self, name: str) -> Optional[AbstractTestType]:
        """
        Get a test type by name.
        
        Looks up a test type in the registry by its name. Returns None
        if the test type is not registered.
        
        Args:
            name: Test type name (e.g., "S-Parameters")
            
        Returns:
            AbstractTestType instance if found, None otherwise
        """
        return self._registry.get(name)
    
    def list_all(self) -> list[str]:
        """
        List all registered test type names.
        
        Returns a list of all test type names currently registered.
        Useful for populating UI dropdowns or listing available test types.
        
        Returns:
            List of test type names (e.g., ["S-Parameters", "Noise Figure"])
        """
        return list(self._registry.keys())
    
    def is_registered(self, name: str) -> bool:
        """
        Check if a test type is registered.
        
        Convenience method to check if a test type exists in the registry
        without retrieving it.
        
        Args:
            name: Test type name to check
            
        Returns:
            True if registered, False otherwise
        """
        return name in self._registry
