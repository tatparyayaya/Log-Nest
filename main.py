"""
LOG NEST — Windows Activity Tracker
Main entry point for the application.

Usage:
    python main.py
"""

import sys
import os
import logging
from datetime import datetime

# Configure logging
log_dir = os.path.join(os.path.expanduser("~"), ".lognest", "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(log_dir, f"lognest_{datetime.now():%Y%m%d}.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger("LogNest")


def main():
    """Launch the LOG NEST application."""
    # PySide6 imports (after logging is configured)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    # Set Windows AppUserModelID so taskbar displays the custom LOG NEST logo
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LogNest.ActivityTracker.1.0")
    except Exception:
        pass

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("LOG NEST")
    app.setOrganizationName("LogNest")
    app.setApplicationVersion("1.0.0")

    # Set application icon globally
    from PySide6.QtGui import QFont, QIcon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Prevent app from quitting when window is hidden to tray
    app.setQuitOnLastWindowClosed(False)

    # Initialize database
    from src.database import DatabaseManager
    db = DatabaseManager()
    logger.info(f"Database initialized at: {db.db_path}")
    logger.info(f"Total stored events: {db.get_event_count()}")

    # Launch main window
    from src.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("LOG NEST started")
    exit_code = app.exec()

    # Cleanup
    logger.info("LOG NEST shutting down")
    db.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
