<!-- 31789580-5aa3-4ad0-bc0c-6964cc2b4819 941572fe-990d-4a2c-8a65-91293c6a7854 -->
# Phase 4: Services Layer Implementation

## Overview

Build the business logic services layer that orchestrates repositories, test types, and RF data processing. All services use dependency injection for maximum testability.

## Implementation Tasks

### 1. Missing Repositories

- **MeasurementRepository**: Implement `IRepository[Measurement]`
- Handle pickled Network objects (serialize/deserialize for BLOB storage)
- Query methods:
- `get_by_device_and_test_stage(device_id, test_type, test_stage)` - for Test Setup screen
- `get_by_serial_number(serial_number)` - for querying specific units
- `get_by_device(device_id)` - get all measurements for a device
- Store touchstone_data as BLOB (pickled Network using TouchstoneLoader)

- **TestResultRepository**: Implement `IRepository[TestResult]`
- Query methods:
- `get_by_measurement_id(measurement_id)` - get all results for a measurement
- `get_by_criteria_id(criteria_id)` - get all results for a criterion
- `get_by_measurement_and_criteria(measurement_id, criteria_id)` - specific result
- `mark_as_stale()` - mark results as stale when criteria change
- Add `is_stale` field to TestResult model (boolean, defaults to False)

### 2. Business Logic Services

#### DeviceService

- **Dependencies**: `DeviceRepository`, `TestCriteriaRepository` (injected via constructor)
- **Methods**:
- `create_device(device: Device)`: Create device with validation
- `get_device(device_id)`, `get_all_devices()`: Device retrieval
- `update_device(device: Device)`: Update with validation
- `delete_device(device_id)`: Check for related measurements/results, return confirmation info
- Returns information about related data that will be deleted
- Does NOT delete automatically - user must confirm (GUI responsibility)
- `get_criteria_for_device(device_id, test_type, test_stage)`: Get criteria by device/test_type/test_stage
- `add_criteria(criteria: TestCriteria)`, `update_criteria(criteria)`, `delete_criteria(criteria_id)`: Criteria CRUD
- `mark_results_stale_for_criteria(criteria_id)`: Mark associated test results as stale

#### MeasurementService

- **Dependencies**: `MeasurementRepository`, `TouchstoneLoader`, `FilenameParser`, `DeviceRepository` (injected)
- **Key Design**: Device must be selected BEFORE files are loaded (user workflow)
- **Methods**:
- `load_measurement_file(filepath, device: Device, test_stage: str)`: Load Touchstone file
- Parse filename metadata
- Validate part number matches device (warn if mismatch, but allow user to proceed)
- Load Touchstone data
- Create Measurement object
- Return Measurement (caller saves via save_measurement())
- `load_multiple_files(filepaths: List, device: Device, test_stage: str, temperature: str)`: Handle 2 or 4 files
- Validates: All files have same serial number
- Validates: All files have same temperature (matches provided temperature parameter)
- If mismatches: Raise error but allow user to proceed (flag/warn)
- Returns List[Measurement] (one per file)
- `save_measurement(measurement: Measurement)`: Store measurement with serialized Network
- `get_measurements_for_device(device_id, test_type, test_stage)`: Get measurements by device/test_stage
- `validate_part_number_match(filename_part_number, device_part_number)`: Validation helper
- Returns (bool, str) - (matches, warning_message)
- Warns but doesn't block if mismatch

#### ComplianceService

- **Dependencies**: `MeasurementRepository`, `TestCriteriaRepository`, `DeviceRepository`, `TestResultRepository`, `TestTypeRegistry` (injected)
- **Key Design**: Can evaluate automatically or manually, evaluates all measurements at once
- **Methods**:
- `evaluate_compliance(measurement: Measurement, device: Device, test_stage: str)`: Evaluate single measurement
- Gets criteria for device/test_type/test_stage
- Uses TestTypeRegistry to get appropriate test type
- Calls test_type.evaluate_compliance()
- Returns List[TestResult]
- `evaluate_all_measurements(device_id, test_type, test_stage)`: Evaluate ALL measurements at once
- Gets all measurements for device/test_type/test_stage (all temperatures, all paths)
- Evaluates each one
- Returns Dict[measurement_id, List[TestResult]]
- `save_test_results(results: List[TestResult])`: Store results using TestResultRepository
- Saves all results to database
- Marks old results as stale if criteria changed
- `get_compliance_results(measurement_id, test_stage)`: Retrieve results for compliance table
- Gets all results for measurement, filtered by test_stage
- Returns results organized by criterion and S-parameter
- `get_overall_pass_status(measurement_id)`: Aggregate pass/fail across all results
- Returns overall pass/fail (all must pass for overall pass)
- `auto_evaluate_on_load`: Configuration flag (default True) for automatic evaluation

### 3. Service Tests

- Unit tests for each service using dependency injection (mock repositories)
- Test all service methods with various scenarios
- Test error handling and validation
- Test integration between services

### 4. Full Phase 1-3 Retest

- Run all Phase 1 tests (models, repositories, database schema)
- Run all Phase 2 tests (RF data processing: filename parser, touchstone loader, calculator)
- Run all Phase 3 tests (test types, registry, test stages)
- Verify all 85+ tests still pass after services implementation

## Key Design Principles

1. **Dependency Injection**: All services receive repositories via constructor

- Enables easy mocking in tests
- Allows swapping implementations

2. **Error Handling**: Services wrap repository errors in application exceptions

- Consistent error messages
- Proper exception propagation

3. **Validation**: Services validate business rules before repository operations

- Device validation (part number format, frequency ranges)
- Measurement validation (file format, metadata matching)

4. **Transaction Management**: Services coordinate multi-step operations

- Ensure atomicity where needed
- Rollback on errors

## Files to Create/Modify

### New Files

- `src/core/repositories/measurement_repository.py`
- `src/core/repositories/test_result_repository.py`
- `src/core/services/device_service.py`
- `src/core/services/measurement_service.py`
- `src/core/services/compliance_service.py`

### Test Files

- `tests/unit/test_repositories/test_measurement_repository.py`
- `tests/unit/test_repositories/test_test_result_repository.py`
- `tests/unit/test_services/test_device_service.py`
- `tests/unit/test_services/test_measurement_service.py`
- `tests/unit/test_services/test_compliance_service.py`

### Modified Files

- `tests/conftest.py`: Add fixtures for new repositories and services
- Update existing test fixtures if needed

## Testing Strategy

1. **Repository Tests**: Test MeasurementRepository and TestResultRepository with in-memory DB
2. **Service Tests**: Mock all repositories, test business logic in isolation
3. **Integration Tests**: Test services with real repositories (end-to-end workflows)
4. **Retest**: Run complete Phase 1-3 test suite to ensure nothing broke

## Success Criteria

- All new repositories implement IRepository interface correctly
- All services use dependency injection (repositories in constructor)
- All services have comprehensive unit tests (90%+ coverage)
- All Phase 1-3 tests still pass (no regressions)
- Services handle errors gracefully with appropriate exceptions