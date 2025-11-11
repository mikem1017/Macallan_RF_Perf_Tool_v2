"""Pytest fixtures and configuration."""

import pytest
import sqlite3
from uuid import UUID

from src.database.schema import get_in_memory_connection
from src.core.repositories.device_repository import DeviceRepository
from src.core.models.device import Device


@pytest.fixture
def db_connection():
    """Provide an in-memory database connection for tests."""
    conn = get_in_memory_connection()
    yield conn
    conn.close()


@pytest.fixture
def device_repository(db_connection):
    """Provide a device repository with test database."""
    return DeviceRepository(db_connection)


@pytest.fixture
def sample_device():
    """Provide a sample device for testing."""
    return Device(
        name="Test Device",
        description="A test device",
        part_number="L123456",
        operational_freq_min=0.5,
        operational_freq_max=2.0,
        wideband_freq_min=0.1,
        wideband_freq_max=5.0,
        multi_gain_mode=False,
        tests_performed=["S-Parameters"],
        input_ports=[1, 2],
        output_ports=[3, 4]
    )


@pytest.fixture
def sample_device_multi_gain():
    """Provide a sample device with multi-gain mode enabled."""
    return Device(
        name="Multi-Gain Device",
        description="A test device with multi-gain mode",
        part_number="L789012",
        operational_freq_min=1.0,
        operational_freq_max=3.0,
        wideband_freq_min=0.5,
        wideband_freq_max=6.0,
        multi_gain_mode=True,
        tests_performed=["S-Parameters"],
        input_ports=[1],
        output_ports=[2, 3, 4]
    )
