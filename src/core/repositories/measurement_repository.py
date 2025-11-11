"""
Measurement repository implementation.

This module provides the SQLite implementation of IRepository[Measurement],
handling all database operations for measurement entities. It handles:
- CRUD operations (Create, Read, Update, Delete)
- Serialization of Network objects to BLOB (pickled bytes)
- Deserialization when reading from database
- Specialized queries for Test Setup screen and measurement lookup

Key design decisions:
- Network objects stored as BLOB (pickled bytes) using TouchstoneLoader
- Metadata stored as JSON TEXT for flexible additional information
- UUIDs stored as strings (TEXT) for SQLite compatibility
- Automatic timestamp management (created_at)
"""

import json
import sqlite3
from typing import List, Optional, Any
from uuid import UUID
from datetime import date

from ..models.measurement import Measurement
from ..exceptions import DatabaseError
from ..rf_data.touchstone_loader import TouchstoneLoader
from .base import IRepository


class MeasurementRepository(IRepository[Measurement]):
    """
    SQLite implementation of measurement repository.
    
    Handles all database operations for Measurement entities. Converts between
    Measurement model objects and SQLite database rows, handling:
    - UUID serialization (UUID -> TEXT)
    - Network object serialization (Network -> BLOB via pickle)
    - Network object deserialization (BLOB -> Network via pickle)
    - Metadata serialization (Dict -> JSON TEXT)
    - Date serialization (date -> DATE)
    
    All operations use transactions for data integrity. Errors are caught
    and converted to application-specific exceptions.
    """
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: SQLite connection (should have row_factory=sqlite3.Row)
        """
        self.conn = connection
        self.loader = TouchstoneLoader()
    
    def get_by_id(self, id: UUID) -> Optional[Measurement]:
        """
        Get a measurement by ID.
        
        Args:
            id: UUID of the measurement to retrieve
            
        Returns:
            Measurement object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurements WHERE id = ?",
            (str(id),)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_measurement(row)
    
    def get_all(self) -> List[Measurement]:
        """
        Get all measurements, ordered by measurement_date descending.
        
        Returns:
            List of all Measurement objects, sorted by date (newest first)
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM measurements ORDER BY measurement_date DESC")
        rows = cursor.fetchall()
        
        return [self._row_to_measurement(row) for row in rows]
    
    def get_by_device_and_test_stage(
        self,
        device_id: UUID,
        test_type: str,
        test_stage: str
    ) -> List[Measurement]:
        """
        Get measurements for a specific device, test type, and test stage.
        
        Primary query method used in Test Setup screen to load measurements
        for the selected device and test stage.
        
        Args:
            device_id: UUID of the device
            test_type: Test type name (e.g., "S-Parameters")
            test_stage: Test stage name (e.g., "SIT", "Board-Bring-Up")
            
        Returns:
            List of Measurement objects, ordered by temperature, path_type
            Empty list if no measurements found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM measurements 
            WHERE device_id = ? AND test_type = ? AND test_stage = ?
            ORDER BY temperature, path_type
            """,
            (str(device_id), test_type, test_stage)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_measurement(row) for row in rows]
    
    def get_by_device(self, device_id: UUID) -> List[Measurement]:
        """
        Get all measurements for a device.
        
        Used when checking for related data before device deletion.
        
        Args:
            device_id: UUID of the device
            
        Returns:
            List of all Measurement objects for this device
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurements WHERE device_id = ? ORDER BY measurement_date DESC",
            (str(device_id),)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_measurement(row) for row in rows]
    
    def get_by_serial_number(self, serial_number: str) -> List[Measurement]:
        """
        Get all measurements for a specific serial number.
        
        Useful for querying all measurements for a specific unit across
        different devices, test stages, etc.
        
        Args:
            serial_number: Serial number (SNXXXX or EMXXXX)
            
        Returns:
            List of Measurement objects for this serial number
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurements WHERE serial_number = ? ORDER BY measurement_date DESC",
            (serial_number,)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_measurement(row) for row in rows]
    
    def create(self, measurement: Measurement) -> Measurement:
        """
        Create a new measurement in the database.
        
        Serializes the Network object to bytes (BLOB) before storing.
        If measurement.touchstone_data is already bytes, uses it directly.
        Otherwise, serializes the Network object.
        
        Args:
            measurement: Measurement object to create (ID may be auto-generated)
            
        Returns:
            The created Measurement (same object, unchanged)
            
        Raises:
            DatabaseError: If insertion fails
        """
        try:
            # Serialize Network object to bytes if needed
            if isinstance(measurement.touchstone_data, bytes):
                touchstone_blob = measurement.touchstone_data
            else:
                # Network object - serialize to bytes
                touchstone_blob = self.loader.serialize_network(measurement.touchstone_data)
            
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO measurements (
                    id, device_id, serial_number, test_type, test_stage,
                    temperature, path_type, file_path, measurement_date,
                    touchstone_data, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(measurement.id),
                    str(measurement.device_id),
                    measurement.serial_number,
                    measurement.test_type,
                    measurement.test_stage,
                    measurement.temperature,
                    measurement.path_type,
                    measurement.file_path,
                    measurement.measurement_date.isoformat(),
                    touchstone_blob,  # BLOB - pickled Network object
                    json.dumps(measurement.metadata, default=self._json_serializer)  # JSON TEXT
                )
            )
            self.conn.commit()
            return measurement
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create measurement: {e}") from e
    
    def update(self, measurement: Measurement) -> Measurement:
        """
        Update an existing measurement in the database.
        
        Note: Typically measurements are immutable (not updated after creation).
        This method is provided for completeness but is rarely used.
        
        Args:
            measurement: Measurement object to update (must have valid ID)
            
        Returns:
            The updated Measurement
            
        Raises:
            DatabaseError: If update fails
        """
        # Serialize Network object if needed
        if isinstance(measurement.touchstone_data, bytes):
            touchstone_blob = measurement.touchstone_data
        else:
            touchstone_blob = self.loader.serialize_network(measurement.touchstone_data)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE measurements SET
                    serial_number = ?,
                    temperature = ?,
                    path_type = ?,
                    file_path = ?,
                    measurement_date = ?,
                    touchstone_data = ?,
                    metadata = ?
                WHERE id = ?
                """,
                (
                    measurement.serial_number,
                    measurement.temperature,
                    measurement.path_type,
                    measurement.file_path,
                    measurement.measurement_date.isoformat(),
                    touchstone_blob,
                    json.dumps(measurement.metadata, default=self._json_serializer),
                    str(measurement.id)
                )
            )
            self.conn.commit()
            return measurement
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update measurement: {e}") from e
    
    def delete(self, id: UUID) -> None:
        """
        Delete a measurement by ID.
        
        Note: Due to foreign key constraints with CASCADE, deleting a measurement
        will also delete all associated test_results.
        
        Args:
            id: UUID of the measurement to delete
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM measurements WHERE id = ?", (str(id),))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete measurement: {e}") from e
    
    def _json_serializer(self, obj: Any) -> str:
        """
        Custom JSON serializer for objects that aren't JSON serializable by default.
        
        Handles date objects by converting them to ISO format strings.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable representation of the object
            
        Raises:
            TypeError: If object type is not supported
        """
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def _row_to_measurement(self, row: sqlite3.Row) -> Measurement:
        """
        Convert database row to Measurement model object.
        
        Handles deserialization:
        - TEXT -> UUID (for id and device_id)
        - BLOB -> Network object (via pickle deserialization)
        - JSON TEXT -> Dict (for metadata)
        - DATE -> date object
        
        Args:
            row: SQLite Row object
            
        Returns:
            Measurement object populated from row data
        """
        # Deserialize Network object from BLOB
        touchstone_blob = row["touchstone_data"]
        network = self.loader.deserialize_network(touchstone_blob)
        
        # Parse date from ISO format string
        measurement_date = date.fromisoformat(row["measurement_date"])
        
        return Measurement(
            id=UUID(row["id"]),
            device_id=UUID(row["device_id"]),
            serial_number=row["serial_number"],
            test_type=row["test_type"],
            test_stage=row["test_stage"],
            temperature=row["temperature"],
            path_type=row["path_type"],
            file_path=row["file_path"],
            measurement_date=measurement_date,
            touchstone_data=network,  # Deserialized Network object
            metadata=json.loads(row["metadata"])  # JSON -> Dict
        )

