"""
Repository implementations for data access.

This module provides repository implementations that abstract database
operations. All repositories implement the IRepository interface, enabling
consistent API and easy testing.

Repositories provided:
- DeviceRepository: Device CRUD operations
- TestCriteriaRepository: Test criteria CRUD operations
- MeasurementRepository: Measurement CRUD operations
- TestResultRepository: Test result CRUD operations
"""

from .base import IRepository
from .device_repository import DeviceRepository
from .test_criteria_repository import TestCriteriaRepository
from .measurement_repository import MeasurementRepository
from .test_result_repository import TestResultRepository

__all__ = [
    "IRepository",
    "DeviceRepository",
    "TestCriteriaRepository",
    "MeasurementRepository",
    "TestResultRepository"
]
