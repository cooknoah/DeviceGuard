"""Placeholder settings dialog — wired fully in Phase 5."""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings will be available in a future update."))
