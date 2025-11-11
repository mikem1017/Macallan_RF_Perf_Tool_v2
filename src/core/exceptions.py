"""
Custom exception classes for the application.

This module defines a hierarchy of custom exceptions used throughout the
application. All exceptions inherit from MacallanRFError, allowing catch-all
exception handling while maintaining specific error types for better error
messages and debugging.

Exception hierarchy:
- MacallanRFError (base)
  - ValidationError (validation failures)
    - InvalidPartNumberError (part number format issues)
  - DeviceNotFoundError (device not found in database)
  - DatabaseError (database operation failures)
  - FileLoadError (file loading/parsing failures)
  - TestCriteriaError (test criteria configuration issues)
"""


class MacallanRFError(Exception):
    """
    Base exception for all application errors.
    
    All custom exceptions should inherit from this class. This allows:
    - Catch-all exception handling (catch MacallanRFError)
    - Type checking and error categorization
    - Consistent error handling patterns
    
    Don't raise this directly - use more specific exceptions instead.
    """
    pass


class DeviceNotFoundError(MacallanRFError):
    """
    Raised when a device is not found.
    
    Typically raised by repositories when attempting to:
    - Get a device by ID that doesn't exist
    - Update a device that doesn't exist
    - Delete a device that doesn't exist
    """
    pass


class ValidationError(MacallanRFError):
    """
    Raised when validation fails.
    
    Base class for all validation-related errors. Used for model validation
    failures that aren't specific enough to warrant their own exception class.
    
    More specific validation errors (like InvalidPartNumberError) should
    inherit from this.
    """
    pass


class InvalidPartNumberError(ValidationError):
    """
    Raised when part number format is invalid.
    
    Part numbers must follow strict format: Lnnnnnn (L followed by 6 digits).
    This exception is raised when a part number doesn't match this pattern,
    typically during Device model creation or update.
    """
    pass


class DatabaseError(MacallanRFError):
    """
    Raised when a database operation fails.
    
    Wraps SQLite errors and provides application-specific context. Typically
    raised by repositories when database operations (insert, update, delete)
    fail due to database constraints or connection issues.
    """
    pass


class FileLoadError(MacallanRFError):
    """
    Raised when a file cannot be loaded.
    
    Used for various file-related errors:
    - File not found
    - Invalid file format (not a Touchstone file)
    - Failed to parse filename metadata
    - scikit-rf loading errors
    - Serialization/deserialization failures
    """
    pass


class TestCriteriaError(MacallanRFError):
    """
    Raised when test criteria configuration is invalid.
    
    Used when test criteria have invalid configurations:
    - Invalid criteria_type
    - Missing required min_value or max_value
    - Invalid value combinations (e.g., min >= max for range)
    - Attempting to operate on criteria that don't exist
    """
    pass
