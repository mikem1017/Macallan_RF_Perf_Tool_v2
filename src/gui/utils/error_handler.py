"""
Error handling utilities for GUI.

This module provides helper functions for displaying errors and warnings
in the GUI. It distinguishes between critical errors (modal dialogs) and
warnings (non-modal status messages).
"""

from typing import Optional
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import Qt

from ...core.exceptions import (
    FileLoadError,
    ValidationError,
    DatabaseError,
    DeviceNotFoundError,
    InvalidPartNumberError
)


def show_error(parent: QWidget, title: str, message: str, details: Optional[str] = None) -> None:
    """
    Show a critical error in a modal dialog.
    
    Used for errors that block operation and require user acknowledgment.
    Examples: file load failures, database errors, validation failures.
    
    Args:
        parent: Parent widget (for dialog positioning)
        title: Dialog title
        message: Error message to display
        details: Optional detailed error information (shown in expandable section)
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    
    if details:
        msg.setDetailedText(details)
    
    msg.exec()


def show_warning(parent: QWidget, title: str, message: str) -> None:
    """
    Show a warning in a modal dialog.
    
    Used for warnings that don't block operation but user should be aware.
    Examples: part number mismatch, stale results.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Warning message to display
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec()


def show_info(parent: QWidget, title: str, message: str) -> None:
    """
    Show an informational message in a modal dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Information message to display
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec()


def handle_exception(parent: QWidget, exception: Exception, context: str = "") -> None:
    """
    Handle an exception by displaying appropriate error dialog.
    
    Maps application exceptions to appropriate error dialogs.
    Unknown exceptions are shown as generic errors.
    
    Args:
        parent: Parent widget
        exception: Exception that was raised
        context: Optional context string (e.g., "Loading file", "Saving device")
    """
    title = f"Error{': ' + context if context else ''}"
    
    if isinstance(exception, FileLoadError):
        show_error(parent, title, str(exception))
    elif isinstance(exception, ValidationError):
        show_error(parent, title, f"Validation error: {exception}")
    elif isinstance(exception, DatabaseError):
        show_error(parent, title, f"Database error: {exception}")
    elif isinstance(exception, DeviceNotFoundError):
        show_error(parent, title, str(exception))
    elif isinstance(exception, InvalidPartNumberError):
        show_error(parent, title, str(exception))
    else:
        # Generic error for unknown exceptions
        show_error(
            parent,
            title,
            f"An unexpected error occurred: {type(exception).__name__}",
            details=str(exception)
        )


class StatusBarMessage:
    """
    Helper class for managing non-modal status messages.
    
    This can be used with a QStatusBar to show warnings that don't
    require immediate user action.
    """
    
    @staticmethod
    def show_warning(status_bar, message: str, timeout: int = 5000) -> None:
        """
        Show a warning message in the status bar.
        
        Args:
            status_bar: QStatusBar widget
            message: Warning message
            timeout: How long to show message (milliseconds). 0 = show until cleared
        """
        status_bar.showMessage(message, timeout)
        # Optionally set style to indicate warning
        status_bar.setStyleSheet("QStatusBar { color: orange; }")
    
    @staticmethod
    def show_info(status_bar, message: str, timeout: int = 3000) -> None:
        """
        Show an info message in the status bar.
        
        Args:
            status_bar: QStatusBar widget
            message: Info message
            timeout: How long to show message (milliseconds)
        """
        status_bar.showMessage(message, timeout)
        status_bar.setStyleSheet("")  # Clear warning style
    
    @staticmethod
    def clear(status_bar) -> None:
        """
        Clear the status bar message.
        
        Args:
            status_bar: QStatusBar widget
        """
        status_bar.clearMessage()
        status_bar.setStyleSheet("")











