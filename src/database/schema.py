"""
Database schema definitions and initialization.

This module provides database schema creation and management for the RF
performance tool. It uses SQLite as the database backend and includes:

- Schema versioning for future migrations
- Table definitions for all entities (devices, criteria, measurements, results)
- Index creation for performance optimization
- Database path management (stored in user's home directory)

Key tables:
- devices: Device configurations (part numbers, frequency ranges, port configs)
- test_criteria: Test requirements organized by device/test_type/test_stage
- measurements: Loaded Touchstone files with RF data
- test_results: Pass/fail evaluation results

Schema versioning:
- Current version: 1
- Future versions will support migrations
- Version mismatch detection prevents data corruption

Database location:
- Default: ~/.macallan_rf_tool/rf_performance.db
- In-memory: ":memory:" (for testing)
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from uuid import UUID

# Current schema version - increment when schema changes
# Used for migration detection and validation
SCHEMA_VERSION = 1


def get_database_path() -> Path:
    """
    Get the path to the database file in user's home directory.
    
    Creates the application data directory if it doesn't exist. Database
    is stored in a hidden directory (.macallan_rf_tool) in the user's
    home directory to avoid clutter.
    
    Returns:
        Path to database file: ~/.macallan_rf_tool/rf_performance.db
    """
    home = Path.home()
    db_dir = home / ".macallan_rf_tool"
    db_dir.mkdir(exist_ok=True)  # Create directory if it doesn't exist
    return db_dir / "rf_performance.db"


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create the database schema.
    
    Creates all tables, indexes, and schema version tracking. This function
    is called when initializing a new database or when schema version changes.
    
    Table structure:
    - schema_version: Tracks current schema version
    - devices: Device configurations
    - test_criteria: Test requirements (with frequency ranges for OOB)
    - measurements: RF measurement data (with pickled Network objects)
    - test_results: Compliance evaluation results (with s_parameter tags)
    
    Foreign keys use CASCADE deletion:
    - Deleting a device deletes all its criteria and measurements
    - Deleting a measurement deletes all its test results
    - Deleting criteria deletes all associated test results
    
    Args:
        conn: SQLite connection (will be committed by caller)
    """
    cursor = conn.cursor()
    
    # Schema version tracking table
    # Used to detect schema mismatches and trigger migrations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
    """)
    
    # Insert current schema version
    # INSERT OR REPLACE ensures version is always current
    cursor.execute("""
        INSERT OR REPLACE INTO schema_version (version) VALUES (?)
    """, (SCHEMA_VERSION,))
    
    # Devices table: Stores device configurations
    # Devices define the physical characteristics and test requirements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            part_number TEXT NOT NULL,
            operational_freq_min REAL NOT NULL,
            operational_freq_max REAL NOT NULL,
            wideband_freq_min REAL NOT NULL,
            wideband_freq_max REAL NOT NULL,
            multi_gain_mode INTEGER NOT NULL DEFAULT 0,
            tests_performed TEXT NOT NULL DEFAULT '[]',
            input_ports TEXT NOT NULL,
            output_ports TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(operational_freq_min < operational_freq_max),
            CHECK(wideband_freq_min < wideband_freq_max)
        )
    """)
    
    # Test criteria table: Stores test requirements
    # Organized hierarchically: device → test_type → test_stage → criteria
    # frequency_min and frequency_max are for OOB requirements (frequency ranges)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_criteria (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            test_type TEXT NOT NULL,
            test_stage TEXT NOT NULL,
            requirement_name TEXT NOT NULL,
            criteria_type TEXT NOT NULL,
            min_value REAL,
            max_value REAL,
            unit TEXT NOT NULL,
            frequency_min REAL,
            frequency_max REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
            CHECK(criteria_type IN ('range', 'min', 'max', 'less_than_equal', 'greater_than_equal'))
        )
    """)
    
    # Measurements table: Stores loaded RF measurement files
    # touchstone_data is stored as BLOB (pickled Network objects)
    # metadata is stored as JSON text (flexible additional information)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            test_type TEXT NOT NULL,
            test_stage TEXT NOT NULL,
            temperature TEXT NOT NULL,
            path_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            measurement_date DATE NOT NULL,
            touchstone_data BLOB NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
            CHECK(temperature IN ('AMB', 'HOT', 'COLD')),
            CHECK(path_type IN ('PRI', 'RED', 'PRI_HG', 'PRI_LG', 'RED_HG', 'RED_LG'))
        )
    """)
    
    # Test results table: Stores pass/fail evaluation results
    # One result per criterion per applicable S-parameter (for S-Parameters test)
    # s_parameter field identifies which S-parameter this result applies to
    # is_stale field marks results that need recalculation (criteria changed)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id TEXT PRIMARY KEY,
            measurement_id TEXT NOT NULL,
            test_criteria_id TEXT NOT NULL,
            measured_value REAL,
            passed INTEGER NOT NULL,
            s_parameter TEXT,
            is_stale INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (measurement_id) REFERENCES measurements(id) ON DELETE CASCADE,
            FOREIGN KEY (test_criteria_id) REFERENCES test_criteria(id) ON DELETE CASCADE
        )
    """)
    
    # Create indices for performance optimization
    # These speed up common queries (filtering by device, test type, stage)
    
    # Index on test_criteria for filtering by device/test_type/test_stage
    # Used when loading criteria for compliance evaluation
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_test_criteria_device ON test_criteria(device_id, test_type, test_stage)
    """)
    
    # Index on measurements for filtering by device/test_type/test_stage
    # Used when querying measurements for a specific device/stage
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_measurements_device ON measurements(device_id, test_type, test_stage)
    """)
    
    # Index on test_results for filtering by measurement
    # Used when retrieving all results for a measurement
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_test_results_measurement ON test_results(measurement_id)
    """)
    
    conn.commit()


def initialize_database(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Initialize the database connection and create schema if needed.
    
    Handles database initialization, schema creation, and version checking.
    For new databases, creates full schema. For existing databases, checks
    version and handles migrations (currently just version updates).
    
    Database location:
    - If db_path provided: Use that path
    - Otherwise: Use default path (~/.macallan_rf_tool/rf_performance.db)
    
    Args:
        db_path: Optional custom database path (for testing or custom locations)
                If None, uses default path in user's home directory
        
    Returns:
        SQLite connection with row_factory set to sqlite3.Row
        (enables column access by name)
        
    Raises:
        DatabaseError: If database version is newer than application version
                      (prevents data corruption from downgrades)
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Create database file if it doesn't exist
    # Creates parent directory structure if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable column access by name (e.g., row["name"])
    
    # Check if schema exists (new database vs existing)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='schema_version'
    """)
    
    if cursor.fetchone() is None:
        # New database - create full schema
        create_schema(conn)
    else:
        # Existing database - check version
        cursor.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row else 0
        
        if current_version < SCHEMA_VERSION:
            # Database is older than application - migration needed
            # TODO: Run migrations here when we have version changes
            # For now, just update version number
            cursor.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
            conn.commit()
        elif current_version > SCHEMA_VERSION:
            # Database is newer than application - prevent data corruption
            from ..core.exceptions import DatabaseError
            raise DatabaseError(
                f"Database schema version ({current_version}) is newer than "
                f"application version ({SCHEMA_VERSION}). Please update the application."
            )
    
    return conn


def get_in_memory_connection() -> sqlite3.Connection:
    """
    Get an in-memory SQLite connection for testing.
    
    Creates a temporary in-memory database with full schema. Used by tests
    to isolate test data and ensure fast test execution.
    
    Returns:
        SQLite connection with row_factory=sqlite3.Row and schema initialized
        
    Note:
        In-memory databases are destroyed when connection closes.
        Perfect for unit tests - no cleanup needed.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # Enable column access by name
    create_schema(conn)  # Create schema in memory
    return conn
