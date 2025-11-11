"""
Test criteria repository implementation.

This module provides the SQLite implementation of IRepository[TestCriteria],
handling all database operations for test criteria entities. It includes:
- Standard CRUD operations
- Specialized query: get_by_device_and_test (filters by device, test type, and stage)
- Batch deletion: delete_by_device (removes all criteria for a device)

Test criteria are organized hierarchically:
- Device (root)
  - Test Type (e.g., "S-Parameters")
    - Test Stage (e.g., "SIT")
      - Criteria (multiple per stage)

This hierarchy enables efficient querying of criteria for specific device/test/stage combinations.
"""

import json
import sqlite3
from typing import List, Optional
from uuid import UUID

from ..models.test_criteria import TestCriteria
from ..exceptions import DatabaseError
from .base import IRepository


class TestCriteriaRepository(IRepository[TestCriteria]):
    """
    SQLite implementation of test criteria repository.
    
    Handles all database operations for TestCriteria entities. In addition
    to standard CRUD operations, provides specialized methods for querying
    criteria by device/test/stage combination, which is the primary access
    pattern in the application.
    
    Key features:
    - Efficient querying by device_id, test_type, and test_stage
    - Batch deletion for device removal (cascading deletes)
    - Proper handling of optional fields (frequency, min_value, max_value)
    """
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: SQLite connection (should have row_factory=sqlite3.Row)
        """
        self.conn = connection
    
    def get_by_id(self, id: UUID) -> Optional[TestCriteria]:
        """
        Get test criteria by ID.
        
        Args:
            id: UUID of the criteria to retrieve
            
        Returns:
            TestCriteria object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM test_criteria WHERE id = ?",
            (str(id),)  # Convert UUID to string for SQLite
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_criteria(row)
    
    def get_all(self) -> List[TestCriteria]:
        """
        Get all test criteria, ordered by device, test type, and stage.
        
        Returns:
            List of all TestCriteria objects, sorted for logical grouping
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_criteria ORDER BY device_id, test_type, test_stage")
        rows = cursor.fetchall()
        
        return [self._row_to_criteria(row) for row in rows]
    
    def get_by_device_and_test(
        self,
        device_id: UUID,
        test_type: str,
        test_stage: str
    ) -> List[TestCriteria]:
        """
        Get test criteria for a specific device, test type, and test stage.
        
        This is the primary query method used in the application. When evaluating
        compliance, we need all criteria for a specific device/test/stage combination.
        
        Args:
            device_id: UUID of the device
            test_type: Test type name (e.g., "S-Parameters")
            test_stage: Test stage name (e.g., "SIT", "Board-Bring-Up")
            
        Returns:
            List of TestCriteria objects, ordered by requirement_name
            Empty list if no criteria found (valid - device may not have criteria yet)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM test_criteria 
            WHERE device_id = ? AND test_type = ? AND test_stage = ?
            ORDER BY requirement_name
            """,
            (str(device_id), test_type, test_stage)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_criteria(row) for row in rows]
    
    def create(self, criteria: TestCriteria) -> TestCriteria:
        """
        Create new test criteria.
        
        Args:
            criteria: TestCriteria object to create (ID may be auto-generated)
            
        Returns:
            The created TestCriteria (same object, unchanged)
            
        Raises:
            DatabaseError: If creation fails (e.g., constraint violation, foreign key violation)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO test_criteria (
                    id, device_id, test_type, test_stage,
                    requirement_name, criteria_type,
                    min_value, max_value, unit, frequency_min, frequency_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(criteria.id),
                    str(criteria.device_id),
                    criteria.test_type,
                    criteria.test_stage,
                    criteria.requirement_name,
                    criteria.criteria_type,
                    criteria.min_value,  # Optional - can be None
                    criteria.max_value,  # Optional - can be None
                    criteria.unit,
                    criteria.frequency_min,  # Optional - can be None
                    criteria.frequency_max   # Optional - can be None
                )
            )
            self.conn.commit()
            return criteria
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create test criteria: {e}") from e
    
    def update(self, criteria: TestCriteria) -> TestCriteria:
        """
        Update existing test criteria.
        
        Updates all fields except ID, device_id, test_type, and test_stage
        (these define the criteria's identity and shouldn't change).
        updated_at is automatically set to CURRENT_TIMESTAMP.
        
        Args:
            criteria: TestCriteria object to update (must have valid ID)
            
        Returns:
            The updated TestCriteria (same object, unchanged)
            
        Raises:
            TestCriteriaError: If criteria with given ID doesn't exist
            DatabaseError: If update fails
        """
        # Check if exists first
        existing = self.get_by_id(criteria.id)
        if existing is None:
            from ..exceptions import TestCriteriaError
            raise TestCriteriaError(f"Test criteria with id {criteria.id} not found")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE test_criteria SET
                    requirement_name = ?,
                    criteria_type = ?,
                    min_value = ?,
                    max_value = ?,
                    unit = ?,
                    frequency_min = ?,
                    frequency_max = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    criteria.requirement_name,
                    criteria.criteria_type,
                    criteria.min_value,
                    criteria.max_value,
                    criteria.unit,
                    criteria.frequency_min,
                    criteria.frequency_max,
                    str(criteria.id)
                )
            )
            self.conn.commit()
            return criteria
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update test criteria: {e}") from e
    
    def delete(self, id: UUID) -> None:
        """
        Delete test criteria by ID.
        
        Args:
            id: UUID of the criteria to delete
            
        Raises:
            TestCriteriaError: If criteria with given ID doesn't exist
            DatabaseError: If deletion fails
        """
        # Check if exists
        existing = self.get_by_id(id)
        if existing is None:
            from ..exceptions import TestCriteriaError
            raise TestCriteriaError(f"Test criteria with id {id} not found")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM test_criteria WHERE id = ?", (str(id),))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete test criteria: {e}") from e
    
    def delete_by_device(self, device_id: UUID) -> None:
        """
        Delete all test criteria for a device.
        
        Used when deleting a device (should be called before device deletion
        if not using CASCADE, or automatically handled by CASCADE foreign key).
        
        Args:
            device_id: UUID of the device whose criteria should be deleted
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM test_criteria WHERE device_id = ?",
                (str(device_id),)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete test criteria: {e}") from e
    
    def _row_to_criteria(self, row: sqlite3.Row) -> TestCriteria:
        """
        Convert database row to TestCriteria model object.
        
        Handles deserialization:
        - TEXT -> UUID (for id and device_id)
        - NULL -> None (for optional fields: frequency, min_value, max_value)
        
        Args:
            row: SQLite Row object (from cursor.fetchone() or fetchall())
            
        Returns:
            TestCriteria object populated from row data
        """
        return TestCriteria(
            id=UUID(row["id"]),
            device_id=UUID(row["device_id"]),
            test_type=row["test_type"],
            test_stage=row["test_stage"],
            requirement_name=row["requirement_name"],
            criteria_type=row["criteria_type"],
            min_value=row["min_value"],  # Can be None
            max_value=row["max_value"],  # Can be None
            unit=row["unit"],
            frequency_min=row["frequency_min"],  # Can be None
            frequency_max=row["frequency_max"]   # Can be None
        )
