"""PyQt6 application setup."""

import sys

from PyQt6.QtWidgets import QApplication

from ui.styles import DARK_THEME
from ui.main_window import MainWindow


def create_app() -> tuple[QApplication, MainWindow]:
    """Create and configure the QApplication and main window.
    Returns (app, window) — caller is responsible for app.exec()."""
    app = QApplication(sys.argv)
    app.setApplicationName("DeviceGuard")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    return app, window
