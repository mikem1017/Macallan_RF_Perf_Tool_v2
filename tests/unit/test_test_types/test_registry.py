"""Unit tests for test type registry."""

import pytest

from src.core.test_types.registry import TestTypeRegistry
from src.core.test_types.s_parameters import SParametersTestType


class TestTestTypeRegistry:
    """Test test type registry."""
    
    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        reg1 = TestTypeRegistry()
        reg2 = TestTypeRegistry()
        
        assert reg1 is reg2
    
    def test_registry_has_s_parameters(self):
        """Test that S-Parameters is registered by default."""
        registry = TestTypeRegistry()
        
        assert registry.is_registered("S-Parameters")
        assert "S-Parameters" in registry.list_all()
    
    def test_get_s_parameters(self):
        """Test getting S-Parameters test type."""
        registry = TestTypeRegistry()
        
        test_type = registry.get("S-Parameters")
        
        assert test_type is not None
        assert isinstance(test_type, SParametersTestType)
        assert test_type.name == "S-Parameters"
    
    def test_get_nonexistent(self):
        """Test getting non-existent test type."""
        registry = TestTypeRegistry()
        
        test_type = registry.get("Non-Existent")
        
        assert test_type is None
    
    def test_register_new_type(self):
        """Test registering a new test type."""
        registry = TestTypeRegistry()
        
        # Create a mock test type
        class MockTestType:
            name = "Mock Test"
            description = "A mock test type"
        
        registry.register(MockTestType())
        
        assert registry.is_registered("Mock Test")
        assert registry.get("Mock Test") is not None
    
    def test_list_all(self):
        """Test listing all registered test types."""
        registry = TestTypeRegistry()
        
        all_types = registry.list_all()
        
        assert isinstance(all_types, list)
        assert "S-Parameters" in all_types













