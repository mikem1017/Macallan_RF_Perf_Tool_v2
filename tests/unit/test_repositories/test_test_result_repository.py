"""Unit tests for TestResultRepository."""

import pytest
from uuid import uuid4

from src.core.repositories.test_result_repository import TestResultRepository
from src.core.models.test_result import TestResult


class TestTestResultRepository:
    """Test TestResultRepository CRUD operations."""
    
    @pytest.fixture
    def db_connection(self):
        """Provide in-memory database connection."""
        from src.database.schema import get_in_memory_connection
        conn = get_in_memory_connection()
        yield conn
        conn.close()
    
    @pytest.fixture
    def repository(self, db_connection):
        """Provide TestResultRepository instance."""
        return TestResultRepository(db_connection)
    
    @pytest.fixture
    def measurement_id(self):
        """Provide a measurement ID for testing."""
        return uuid4()
    
    @pytest.fixture
    def criteria_id(self):
        """Provide a criteria ID for testing."""
        return uuid4()
    
    @pytest.fixture
    def sample_result(self, measurement_id, criteria_id):
        """Provide a sample TestResult for testing."""
        return TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=29.5,
            passed=True,
            s_parameter="S21",
            is_stale=False
        )
    
    def test_create_result(self, repository, sample_result):
        """Test creating a test result."""
        created = repository.create(sample_result)
        
        assert created.id == sample_result.id
        assert created.passed is True
        assert created.s_parameter == "S21"
        assert created.is_stale is False
    
    def test_get_by_id_exists(self, repository, sample_result):
        """Test getting result by ID when it exists."""
        repository.create(sample_result)
        
        retrieved = repository.get_by_id(sample_result.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_result.id
        assert retrieved.passed is True
    
    def test_get_by_measurement_id(self, repository, measurement_id, criteria_id):
        """Test getting results by measurement ID."""
        # Create multiple results for same measurement
        r1 = TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=29.5,
            passed=True,
            s_parameter="S21"
        )
        r2 = TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=30.2,
            passed=True,
            s_parameter="S31"
        )
        
        repository.create(r1)
        repository.create(r2)
        
        results = repository.get_by_measurement_id(measurement_id)
        
        assert len(results) == 2
        assert {r.s_parameter for r in results} == {"S21", "S31"}
    
    def test_get_by_criteria_id(self, repository, measurement_id, criteria_id):
        """Test getting results by criteria ID."""
        r1 = TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=29.5,
            passed=True,
            s_parameter="S21"
        )
        
        repository.create(r1)
        
        results = repository.get_by_criteria_id(criteria_id)
        
        assert len(results) == 1
        assert results[0].s_parameter == "S21"
    
    def test_mark_as_stale_by_criteria(self, repository, measurement_id, criteria_id):
        """Test marking results as stale by criteria."""
        r1 = TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=29.5,
            passed=True,
            s_parameter="S21",
            is_stale=False
        )
        
        repository.create(r1)
        
        # Mark as stale
        count = repository.mark_as_stale_by_criteria(criteria_id)
        
        assert count == 1
        
        # Verify it's marked stale
        retrieved = repository.get_by_id(r1.id)
        assert retrieved.is_stale is True
    
    def test_is_stale_field_persistence(self, repository, measurement_id, criteria_id):
        """Test that is_stale field is properly persisted."""
        r1 = TestResult(
            measurement_id=measurement_id,
            test_criteria_id=criteria_id,
            measured_value=29.5,
            passed=True,
            s_parameter="S21",
            is_stale=True
        )
        
        created = repository.create(r1)
        retrieved = repository.get_by_id(created.id)
        
        assert retrieved.is_stale is True














