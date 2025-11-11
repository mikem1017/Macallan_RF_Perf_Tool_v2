"""
Main application entry point.

This module launches the PyQt6 GUI application. It initializes the database,
creates service instances, and shows the main window.
"""

import sys
import traceback
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from .main_window import MainWindow
from .utils.service_factory import create_services
from .utils.error_handler import handle_exception

# Enable logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(name)s: %(message)s'
)


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to catch all unhandled exceptions.
    
    This prevents the application from crashing silently and shows
    error dialogs for any unhandled exceptions.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow normal keyboard interrupt handling
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Format the exception
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Show error dialog if we have a QApplication
    app = QApplication.instance()
    if app is not None:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Unhandled Exception")
        msg.setText(f"An unexpected error occurred:\n\n{exc_type.__name__}: {str(exc_value)}")
        msg.setDetailedText(error_msg)
        msg.exec()
    else:
        # No QApplication, print to console
        print("Unhandled exception:", error_msg, file=sys.stderr)
    
    # Also call the standard exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def main():
    """
    Main entry point for the application.
    
    Creates the QApplication, initializes services, and shows the main window.
    """
    # Install global exception handler to catch all unhandled exceptions
    sys.excepthook = exception_hook
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Macallan RF Performance Tool")
    app.setOrganizationName("Macallan Engineering")
    
    try:
        # Create services (this also initializes database)
        device_service, measurement_service, compliance_service, db_conn, database_path = create_services()
        
        # Create and show main window
        window = MainWindow(
            device_service=device_service,
            measurement_service=measurement_service,
            compliance_service=compliance_service,
            database_path=database_path
        )
        window.show()
        
        # Run event loop
        exit_code = app.exec()
        
        # Close database connection
        db_conn.close()
        
        return exit_code
        
    except Exception as e:
        # Handle initialization errors
        # Create a minimal app just to show error dialog
        if not QApplication.instance():
            app = QApplication(sys.argv)
        
        from .utils.error_handler import show_error
        show_error(None, "Application Startup Error", f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

