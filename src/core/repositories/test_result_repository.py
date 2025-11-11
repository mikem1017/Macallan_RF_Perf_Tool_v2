"""
Test result repository implementation.

This module provides the SQLite implementation of IRepository[TestResult],
handling all database operations for test result entities. It includes:
- Standard CRUD operations
- Specialized queries for compliance table display
- Stale marking functionality (when criteria change)

Test results are generated during compliance evaluation and linked to both
measurements and criteria. Results can be marked as stale when criteria
are updated, indicating they need recalculation.
"""

import sqlite3
from typing import List, Optional
from uuid import UUID

from ..models.test_result import TestResult
from ..exceptions import DatabaseError
from .base import IRepository


class TestResultRepository(IRepository[TestResult]):
    """
    SQLite implementation of test result repository.
    
    Handles all database operations for TestResult entities. In addition
    to standard CRUD operations, provides specialized methods for querying
    results by measurement or criteria, and marking results as stale.
    
    Key features:
    - Efficient querying by measurement_id (for compliance table)
    - Querying by criteria_id (for finding stale results)
    - Batch stale marking when criteria change
    - Boolean conversion (is_stale: bool -> INTEGER 0/1)
    """
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: SQLite connection (should have row_factory=sqlite3.Row)
        """
        self.conn = connection
    
    def get_by_id(self, id: UUID) -> Optional[TestResult]:
        """
        Get test result by ID.
        
        Args:
            id: UUID of the result to retrieve
            
        Returns:
            TestResult object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM test_results WHERE id = ?",
            (str(id),)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_result(row)
    
    def get_all(self) -> List[TestResult]:
        """
        Get all test results, ordered by created_at descending.
        
        Returns:
            List of all TestResult objects, sorted by creation time (newest first)
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_results ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        return [self._row_to_result(row) for row in rows]
    
    def get_by_measurement_id(self, measurement_id: UUID) -> List[TestResult]:
        """
        Get all test results for a measurement.
        
        Primary query method for compliance table display. Retrieves all
        results for a measurement, which can then be organized by criterion
        and S-parameter for display.
        
        Args:
            measurement_id: UUID of the measurement
            
        Returns:
            List of TestResult objects for this measurement
            Empty list if no results found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM test_results WHERE measurement_id = ? ORDER BY created_at DESC",
            (str(measurement_id),)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_result(row) for row in rows]
    
    def get_by_criteria_id(self, criteria_id: UUID) -> List[TestResult]:
        """
        Get all test results for a criterion.
        
        Used when marking results as stale after criteria updates or when
        checking which results are affected by a criteria change.
        
        Args:
            criteria_id: UUID of the criterion
            
        Returns:
            List of TestResult objects for this criterion
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM test_results WHERE test_criteria_id = ?",
            (str(criteria_id),)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_result(row) for row in rows]
    
    def get_by_measurement_and_criteria(
        self,
        measurement_id: UUID,
        criteria_id: UUID
    ) -> List[TestResult]:
        """
        Get test results for a specific measurement and criterion.
        
        Useful for finding specific results or checking if results already exist
        before creating new ones.
        
        Args:
            measurement_id: UUID of the measurement
            criteria_id: UUID of the criterion
            
        Returns:
            List of TestResult objects (typically one per S-parameter)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM test_results 
            WHERE measurement_id = ? AND test_criteria_id = ?
            """,
            (str(measurement_id), str(criteria_id))
        )
        rows = cursor.fetchall()
        
        return [self._row_to_result(row) for row in rows]
    
    def create(self, result: TestResult) -> TestResult:
        """
        Create a new test result.
        
        Args:
            result: TestResult object to create (ID may be auto-generated)
            
        Returns:
            The created TestResult
            
        Raises:
            DatabaseError: If creation fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO test_results (
                    id, measurement_id, test_criteria_id,
                    measured_value, passed, s_parameter, is_stale
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(result.id),
                    str(result.measurement_id),
                    str(result.test_criteria_id),
                    result.measured_value,
                    1 if result.passed else 0,  # bool -> INTEGER
                    result.s_parameter,
                    1 if result.is_stale else 0  # bool -> INTEGER
                )
            )
            self.conn.commit()
            return result
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create test result: {e}") from e
    
    def update(self, result: TestResult) -> TestResult:
        """
        Update an existing test result.
        
        Args:
            result: TestResult object to update (must have valid ID)
            
        Returns:
            The updated TestResult
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE test_results SET
                    measured_value = ?,
                    passed = ?,
                    s_parameter = ?,
                    is_stale = ?
                WHERE id = ?
                """,
                (
                    result.measured_value,
                    1 if result.passed else 0,
                    result.s_parameter,
                    1 if result.is_stale else 0,
                    str(result.id)
                )
            )
            self.conn.commit()
            return result
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update test result: {e}") from e
    
    def delete(self, id: UUID) -> None:
        """
        Delete a test result by ID.
        
        Args:
            id: UUID of the result to delete
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM test_results WHERE id = ?", (str(id),))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete test result: {e}") from e
    
    def mark_as_stale_by_criteria(self, criteria_id: UUID) -> int:
        """
        Mark all test results for a criterion as stale.
        
        Called when criteria are updated or deleted. Marks all existing
        results for that criterion as stale, indicating they need to be
        recalculated before being used for compliance decisions.
        
        Args:
            criteria_id: UUID of the criterion whose results should be marked stale
            
        Returns:
            Number of results marked as stale
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE test_results SET is_stale = 1
                WHERE test_criteria_id = ?
                """,
                (str(criteria_id),)
            )
            count = cursor.rowcount
            self.conn.commit()
            return count
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to mark results as stale: {e}") from e
    
    def mark_as_stale_by_measurement(self, measurement_id: UUID) -> int:
        """
        Mark all test results for a measurement as stale.
        
        Used when measurement data changes or needs recalculation.
        
        Args:
            measurement_id: UUID of the measurement whose results should be marked stale
            
        Returns:
            Number of results marked as stale
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE test_results SET is_stale = 1
                WHERE measurement_id = ?
                """,
                (str(measurement_id),)
            )
            count = cursor.rowcount
            self.conn.commit()
            return count
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to mark results as stale: {e}") from e
    
    def delete_by_measurement(self, measurement_id: UUID) -> None:
        """
        Delete all test results for a measurement.
        
        Used when a measurement is deleted or results need to be recalculated
        from scratch.
        
        Args:
            measurement_id: UUID of the measurement
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM test_results WHERE measurement_id = ?",
                (str(measurement_id),)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete test results: {e}") from e
    
    def _row_to_result(self, row: sqlite3.Row) -> TestResult:
        """
        Convert database row to TestResult model object.
        
        Handles deserialization:
        - TEXT -> UUID (for id, measurement_id, criteria_id)
        - INTEGER -> bool (for passed and is_stale)
        
        Args:
            row: SQLite Row object
            
        Returns:
            TestResult object populated from row data
        """
        return TestResult(
            id=UUID(row["id"]),
            measurement_id=UUID(row["measurement_id"]),
            test_criteria_id=UUID(row["test_criteria_id"]),
            measured_value=row["measured_value"],  # Can be None
            passed=bool(row["passed"]),  # INTEGER -> bool
            s_parameter=row["s_parameter"],  # Can be None
            is_stale=bool(row["is_stale"])  # INTEGER -> bool
        )











