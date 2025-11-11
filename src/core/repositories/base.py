"""
Abstract repository interface.

This module defines the generic repository pattern interface (IRepository),
which provides a standard CRUD interface for data access. All concrete
repository implementations should inherit from this interface.

The repository pattern:
- Encapsulates data access logic
- Provides abstraction over data storage (SQLite, in-memory, etc.)
- Enables easy testing (can use in-memory databases or mocks)
- Keeps business logic separate from data access

This generic interface uses Python's Generic type system to ensure type safety.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

# Type variable for the entity type
# When implementing IRepository[Device], T becomes Device
T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Abstract repository interface for data access.
    
    Provides standard CRUD (Create, Read, Update, Delete) operations for
    any entity type. Concrete implementations (e.g., DeviceRepository,
    TestCriteriaRepository) implement these methods for specific entity types.
    
    This interface ensures:
    - Consistent API across all repositories
    - Easy swapping of implementations (SQLite, PostgreSQL, in-memory, etc.)
    - Testability (can mock this interface)
    - Type safety (Generic[T] ensures correct types)
    
    Example usage:
        device_repo: IRepository[Device] = DeviceRepository(conn)
        device = device_repo.get_by_id(some_uuid)
    """
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: UUID of the entity to retrieve
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """
        Get all entities.
        
        Returns:
            List of all entities, ordered by implementation (e.g., by name)
        """
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        The entity's ID is typically auto-generated if not provided.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity (may have auto-generated ID)
            
        Raises:
            DatabaseError: If creation fails (e.g., constraint violation)
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity to update (must have valid ID)
            
        Returns:
            The updated entity
            
        Raises:
            DatabaseError: If update fails (e.g., entity not found, constraint violation)
        """
        pass
    
    @abstractmethod
    def delete(self, id: UUID) -> None:
        """
        Delete an entity by ID.
        
        Args:
            id: UUID of the entity to delete
            
        Raises:
            DatabaseError: If deletion fails (e.g., entity not found, foreign key constraint)
        """
        pass
