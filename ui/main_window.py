"""Main application window with sidebar navigation, device list, and detail panel."""

import threading

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QSplitter,
    QStatusBar, QLabel, QComboBox, QPushButton,
)
from pathlib import Path

from core.monitor import get_connected_devices
from ui.device_list import ConnectedDevicesTable
from ui.device_detail import DeviceDetailPanel
from ui.history_view import HistoryView
from ui.settings_dialog import SettingsDialog

_ASSETS = Path(__file__).parent.parent / "assets"

# Device classes to show in the filter dropdown
_CLASS_FILTERS = [
    ("All Devices", None),
    ("USB", "USB"),
    ("HID", "HIDClass"),
    ("Bluetooth", "Bluetooth"),
    ("Display", "Monitor"),
    ("Audio", "AudioEndpoint"),
    ("Network", "Net"),
    ("Storage", "DiskDrive"),
]


class MainWindow(QMainWindow):
    """DeviceGuard main window."""

    device_event = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DeviceGuard")
        self.setMinimumSize(960, 600)
        self.resize(1100, 700)

        icon_path = _ASSETS / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # ── Central widget ──
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(180)
        self._sidebar.setIconSize(QSize(20, 20))

        for label in ["Devices", "History"]:
            self._sidebar.addItem(QListWidgetItem(label))

        self._sidebar.setCurrentRow(0)
        self._sidebar.currentRowChanged.connect(self._switch_page)
        root_layout.addWidget(self._sidebar)

        # ── Page stack ──
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack)

        # Page 0: Devices (live connected devices)
        devices_page = QWidget()
        devices_outer = QVBoxLayout(devices_page)
        devices_outer.setContentsMargins(8, 8, 8, 8)

        # Filter toolbar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Category:"))
        self._class_combo = QComboBox()
        for label, _ in _CLASS_FILTERS:
            self._class_combo.addItem(label)
        self._class_combo.currentIndexChanged.connect(self._refresh_devices)
        filter_bar.addWidget(self._class_combo)
        filter_bar.addStretch()

        self._device_count_label = QLabel()
        filter_bar.addWidget(self._device_count_label)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_devices)
        filter_bar.addWidget(refresh_btn)

        devices_outer.addLayout(filter_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._device_table = ConnectedDevicesTable()
        splitter.addWidget(self._device_table)

        self._detail_panel = DeviceDetailPanel()
        splitter.addWidget(self._detail_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        devices_outer.addWidget(splitter)

        self._stack.addWidget(devices_page)

        # Page 1: History
        self._history_view = HistoryView()
        self._stack.addWidget(self._history_view)

        # ── Status bar ──
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel("Monitoring active")
        self._status.addWidget(self._status_label)

        # ── Connections ──
        self._device_table.row_selected.connect(self._detail_panel.show_device)
        self._history_view.table.row_selected.connect(self._detail_panel.show_event)
        self.device_event.connect(self._on_device_event)

        # Initial load (in background to avoid blocking the UI)
        self._refresh_devices()

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._detail_panel.clear()

    def _refresh_devices(self) -> None:
        """Reload the connected devices table from WMI (runs query in a thread)."""
        idx = self._class_combo.currentIndex()
        _, class_filter = _CLASS_FILTERS[idx] if idx < len(_CLASS_FILTERS) else (None, None)

        def _query():
            devices = get_connected_devices(class_filter)
            # Sort by name
            devices.sort(key=lambda d: (d.get("name") or "").lower())
            # Update UI from main thread
            self._device_table.load_devices(devices)
            self._device_count_label.setText(f"{len(devices)} devices")

        threading.Thread(target=_query, daemon=True).start()

    @pyqtSlot(dict)
    def _on_device_event(self, event_info: dict) -> None:
        """Called (via signal) when a device connects or disconnects."""
        self._refresh_devices()
        event_type = event_info.get("event_type", "")
        name = event_info.get("device_name") or "Unknown device"
        if event_type == "connect":
            self._status_label.setText(f"Connected: {name}")
        else:
            self._status_label.setText(f"Disconnected: {name}")

    def notify_device_event(self, event_type: str, device_info: dict) -> None:
        """Thread-safe method to push device events to the UI."""
        self.device_event.emit({
            "event_type": event_type,
            "device_name": device_info.get("name"),
            "device_id": device_info.get("device_id"),
            "device_class": device_info.get("pnp_class"),
            "manufacturer": device_info.get("manufacturer"),
        })

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()
