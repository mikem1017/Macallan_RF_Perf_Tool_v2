"""
Service factory for creating service instances with dependencies.

This module provides a factory function that creates all service instances
with their dependencies properly injected. This centralizes the dependency
setup and makes it easy to swap implementations (e.g., for testing).

The factory creates a database connection, initializes repositories, and
wires them together with services. This is the single point of configuration
for the application's service layer.
"""

import sqlite3
from pathlib import Path

from ...database.schema import create_schema, get_database_path
from ...core.repositories.device_repository import DeviceRepository
from ...core.repositories.test_criteria_repository import TestCriteriaRepository
from ...core.repositories.measurement_repository import MeasurementRepository
from ...core.repositories.test_result_repository import TestResultRepository
from ...core.services.device_service import DeviceService
from ...core.services.measurement_service import MeasurementService
from ...core.services.compliance_service import ComplianceService


def create_services(database_path: Path = None) -> tuple:
    """
    Create all service instances with dependencies injected.
    
    This function:
    1. Creates or opens database connection
    2. Initializes schema if needed
    3. Creates all repositories
    4. Creates all services with repositories injected
    5. Returns tuple of (device_service, measurement_service, compliance_service)
    
    Args:
        database_path: Optional path to database file. If None, uses default location
                      (same directory as executable, or home directory for dev)
    
    Returns:
        Tuple of (DeviceService, MeasurementService, ComplianceService)
        
    Raises:
        DatabaseError: If database initialization fails
    """
    # Determine database path
    if database_path is None:
        # In production, use same directory as executable
        # For development, use default location
        try:
            # Try to get executable directory (for .exe or .bat)
            import sys
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_dir = Path(sys.executable).parent
                database_path = exe_dir / "rf_performance.db"
            else:
                # Running as script - check if there's a database in script directory
                script_dir = Path(__file__).parent.parent.parent.parent  # Go up to project root
                local_db = script_dir / "rf_performance.db"
                if local_db.exists():
                    # Use database in project directory
                    database_path = local_db
                else:
                    # Use default location (home directory)
                    database_path = get_database_path()
        except Exception:
            # Fallback to default location
            database_path = get_database_path()
    
    # Create database directory if needed
    database_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open database connection
    conn = sqlite3.connect(str(database_path))
    conn.row_factory = sqlite3.Row
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Create schema if needed
    create_schema(conn)
    
    # Create repositories
    device_repo = DeviceRepository(conn)
    criteria_repo = TestCriteriaRepository(conn)
    measurement_repo = MeasurementRepository(conn)
    result_repo = TestResultRepository(conn)
    
    # Create services with dependency injection
    # Ensure all repositories are properly initialized
    if criteria_repo is None:
        raise ValueError("TestCriteriaRepository must be initialized before creating DeviceService")
    
    device_service = DeviceService(
        device_repository=device_repo,
        criteria_repository=criteria_repo,
        measurement_repository=measurement_repo,
        result_repository=result_repo
    )
    
    # Verify service was created correctly
    if device_service.criteria_repo is None:
        raise ValueError("DeviceService.criteria_repo is None after initialization")
    
    measurement_service = MeasurementService(
        measurement_repository=measurement_repo,
        device_repository=device_repo
    )
    
    compliance_service = ComplianceService(
        measurement_repository=measurement_repo,
        criteria_repository=criteria_repo,
        device_repository=device_repo,
        result_repository=result_repo
    )
    
    return device_service, measurement_service, compliance_service, conn, database_path


def create_services_for_thread(database_path: Path) -> tuple:
    """
    Create service instances with a NEW database connection for use in a worker thread.
    
    SQLite connections cannot be shared across threads. This function creates
    a new connection and new service instances that can be safely used in
    background worker threads.
    
    Args:
        database_path: Path to the database file
    
    Returns:
        Tuple of (DeviceService, MeasurementService, ComplianceService)
        Note: Connection is NOT returned - it's managed by repositories
    """
    import sqlite3
    
    # Create new connection for this thread
    conn = sqlite3.connect(str(database_path))
    conn.row_factory = sqlite3.Row
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Create repositories with new connection
    device_repo = DeviceRepository(conn)
    criteria_repo = TestCriteriaRepository(conn)
    measurement_repo = MeasurementRepository(conn)
    result_repo = TestResultRepository(conn)
    
    # Create services with dependency injection
    device_service = DeviceService(
        device_repository=device_repo,
        criteria_repository=criteria_repo,
        measurement_repository=measurement_repo,
        result_repository=result_repo
    )
    
    measurement_service = MeasurementService(
        measurement_repository=measurement_repo,
        device_repository=device_repo
    )
    
    compliance_service = ComplianceService(
        measurement_repository=measurement_repo,
        criteria_repository=criteria_repo,
        device_repository=device_repo,
        result_repository=result_repo
    )
    
    return device_service, measurement_service, compliance_service

