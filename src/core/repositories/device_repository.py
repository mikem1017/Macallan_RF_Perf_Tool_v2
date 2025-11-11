"""
Device repository implementation.

This module provides the SQLite implementation of IRepository[Device],
handling all database operations for device entities. It handles:
- CRUD operations (Create, Read, Update, Delete)
- Serialization of complex fields (lists, ports) to JSON
- Deserialization when reading from database
- Error handling and transaction management

Key design decisions:
- Uses JSON for lists (tests_performed, input_ports, output_ports) since SQLite
  doesn't have native array support
- UUIDs stored as strings (TEXT) for SQLite compatibility
- Boolean values stored as INTEGER (0/1)
- Automatic timestamp management (created_at, updated_at)
"""

import json
import sqlite3
from typing import List, Optional
from uuid import UUID

from ..models.device import Device
from ..exceptions import DeviceNotFoundError, DatabaseError
from .base import IRepository


class DeviceRepository(IRepository[Device]):
    """
    SQLite implementation of device repository.
    
    Handles all database operations for Device entities. Converts between
    Device model objects and SQLite database rows, handling:
    - UUID serialization (UUID -> TEXT)
    - List serialization (List -> JSON TEXT)
    - Boolean conversion (bool -> INTEGER 0/1)
    - Timestamp management
    
    All operations use transactions for data integrity. Errors are caught
    and converted to application-specific exceptions.
    """
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: SQLite connection (should have row_factory=sqlite3.Row)
                        This enables column access by name
        """
        self.conn = connection
    
    def get_by_id(self, id: UUID) -> Optional[Device]:
        """
        Get a device by ID.
        
        Args:
            id: UUID of the device to retrieve
            
        Returns:
            Device object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM devices WHERE id = ?",
            (str(id),)  # Convert UUID to string for SQLite
        )
        row = cursor.fetchone()
        
        # Return None if not found, otherwise convert row to Device
        if row is None:
            return None
        
        return self._row_to_device(row)
    
    def get_all(self) -> List[Device]:
        """
        Get all devices, ordered by name.
        
        Returns:
            List of all Device objects, sorted by name
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM devices ORDER BY name")
        rows = cursor.fetchall()
        
        # Convert each row to Device object
        return [self._row_to_device(row) for row in rows]
    
    def create(self, device: Device) -> Device:
        """
        Create a new device in the database.
        
        Inserts all device fields into the devices table. Complex fields
        (lists, ports) are serialized to JSON strings.
        
        Args:
            device: Device object to create (ID may be auto-generated)
            
        Returns:
            The created Device (same object, unchanged)
            
        Raises:
            DatabaseError: If insertion fails (e.g., constraint violation)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO devices (
                    id, name, description, part_number,
                    operational_freq_min, operational_freq_max,
                    wideband_freq_min, wideband_freq_max,
                    multi_gain_mode, tests_performed,
                    input_ports, output_ports
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(device.id),  # UUID -> TEXT
                    device.name,
                    device.description,
                    device.part_number,
                    device.operational_freq_min,
                    device.operational_freq_max,
                    device.wideband_freq_min,
                    device.wideband_freq_max,
                    1 if device.multi_gain_mode else 0,  # bool -> INTEGER
                    json.dumps(device.tests_performed),  # List -> JSON TEXT
                    json.dumps(device.input_ports),  # List -> JSON TEXT
                    json.dumps(device.output_ports)  # List -> JSON TEXT
                )
            )
            self.conn.commit()
            return device
        except sqlite3.Error as e:
            # Rollback on error and convert to application exception
            self.conn.rollback()
            raise DatabaseError(f"Failed to create device: {e}") from e
    
    def update(self, device: Device) -> Device:
        """
        Update an existing device in the database.
        
        Updates all fields except ID and created_at timestamp.
        updated_at is automatically set to CURRENT_TIMESTAMP.
        
        Args:
            device: Device object to update (must have valid ID)
            
        Returns:
            The updated Device (same object, unchanged)
            
        Raises:
            DeviceNotFoundError: If device with given ID doesn't exist
            DatabaseError: If update fails
        """
        # Check if device exists first
        existing = self.get_by_id(device.id)
        if existing is None:
            raise DeviceNotFoundError(f"Device with id {device.id} not found")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE devices SET
                    name = ?,
                    description = ?,
                    part_number = ?,
                    operational_freq_min = ?,
                    operational_freq_max = ?,
                    wideband_freq_min = ?,
                    wideband_freq_max = ?,
                    multi_gain_mode = ?,
                    tests_performed = ?,
                    input_ports = ?,
                    output_ports = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    device.name,
                    device.description,
                    device.part_number,
                    device.operational_freq_min,
                    device.operational_freq_max,
                    device.wideband_freq_min,
                    device.wideband_freq_max,
                    1 if device.multi_gain_mode else 0,
                    json.dumps(device.tests_performed),
                    json.dumps(device.input_ports),
                    json.dumps(device.output_ports),
                    str(device.id)
                )
            )
            self.conn.commit()
            return device
        except sqlite3.Error as e:
            # Rollback on error and convert to application exception
            self.conn.rollback()
            raise DatabaseError(f"Failed to update device: {e}") from e
    
    def delete(self, id: UUID) -> None:
        """
        Delete a device by ID.
        
        Note: Due to foreign key constraints with CASCADE, deleting a device
        will also delete all associated test_criteria and measurements.
        
        Args:
            id: UUID of the device to delete
            
        Raises:
            DeviceNotFoundError: If device with given ID doesn't exist
            DatabaseError: If deletion fails
        """
        # Check if device exists first
        existing = self.get_by_id(id)
        if existing is None:
            raise DeviceNotFoundError(f"Device with id {id} not found")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM devices WHERE id = ?", (str(id),))
            self.conn.commit()
        except sqlite3.Error as e:
            # Rollback on error and convert to application exception
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete device: {e}") from e
    
    def _row_to_device(self, row: sqlite3.Row) -> Device:
        """
        Convert database row to Device model object.
        
        Handles deserialization:
        - TEXT -> UUID
        - INTEGER -> bool (for multi_gain_mode)
        - JSON TEXT -> List (for tests_performed, ports)
        - NULL -> default values (empty lists, None handling)
        
        Args:
            row: SQLite Row object (from cursor.fetchone() or fetchall())
            
        Returns:
            Device object populated from row data
            
        Raises:
            DatabaseError: If data conversion fails (malformed JSON, etc.)
        """
        try:
            # Handle JSON deserialization with error handling
            # tests_performed
            tests_performed_str = row["tests_performed"]
            if tests_performed_str is None or tests_performed_str == "":
                tests_performed = []
            else:
                try:
                    tests_performed = json.loads(tests_performed_str)
                except (json.JSONDecodeError, TypeError) as e:
                    # Fallback to empty list if JSON is malformed
                    tests_performed = []
            
            # input_ports
            input_ports_str = row["input_ports"]
            if input_ports_str is None or input_ports_str == "":
                input_ports = []
            else:
                try:
                    input_ports = json.loads(input_ports_str)
                except (json.JSONDecodeError, TypeError) as e:
                    # Fallback to empty list if JSON is malformed
                    input_ports = []
            
            # output_ports
            output_ports_str = row["output_ports"]
            if output_ports_str is None or output_ports_str == "":
                output_ports = []
            else:
                try:
                    output_ports = json.loads(output_ports_str)
                except (json.JSONDecodeError, TypeError) as e:
                    # Fallback to empty list if JSON is malformed
                    output_ports = []
            
            # Handle NULL frequency values - use defaults if None
            operational_freq_min = row["operational_freq_min"]
            if operational_freq_min is None:
                operational_freq_min = 1.0
            
            operational_freq_max = row["operational_freq_max"]
            if operational_freq_max is None:
                operational_freq_max = 2.0
            
            wideband_freq_min = row["wideband_freq_min"]
            if wideband_freq_min is None:
                wideband_freq_min = 0.5
            
            wideband_freq_max = row["wideband_freq_max"]
            if wideband_freq_max is None:
                wideband_freq_max = 1.0
            
            return Device(
                id=UUID(row["id"]),  # TEXT -> UUID
                name=row["name"] or "",  # Handle NULL
                description=row["description"] or "",  # Handle NULL as empty string
                part_number=row["part_number"] or "",  # Handle NULL
                operational_freq_min=operational_freq_min,
                operational_freq_max=operational_freq_max,
                wideband_freq_min=wideband_freq_min,
                wideband_freq_max=wideband_freq_max,
                multi_gain_mode=bool(row["multi_gain_mode"]) if row["multi_gain_mode"] is not None else False,  # INTEGER -> bool
                tests_performed=tests_performed,
                input_ports=input_ports,
                output_ports=output_ports
            )
        except Exception as e:
            raise DatabaseError(f"Failed to convert database row to Device: {e}") from e
