"""Main application window with sidebar navigation, device list, and detail panel."""

import threading

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QSplitter,
    QStatusBar, QLabel, QComboBox, QPushButton,
)
from core.monitor import get_connected_devices, get_external_devices
from core.paths import resource_path
from ui.device_list import ConnectedDevicesTable
from ui.device_detail import DeviceDetailPanel
from ui.history_view import HistoryView
from ui.settings_dialog import SettingsDialog

_ASSETS = resource_path("assets")

# Sentinel for the grouped external-devices view.
_EXTERNAL = "__external__"

# Device classes to show in the filter dropdown
_CLASS_FILTERS = [
    ("External Devices", _EXTERNAL),
    ("USB", "USB"),
    ("HID", "HIDClass"),
    ("Bluetooth", "Bluetooth"),
    ("Display", "Monitor"),
    ("Audio", "AudioEndpoint"),
    ("Network", "Net"),
    ("Storage", "DiskDrive"),
    ("All PnP Devices", None),
]


class MainWindow(QMainWindow):
    """DeviceGuard main window."""

    device_event = pyqtSignal(dict)
    scan_event = pyqtSignal(dict)
    _devices_loaded = pyqtSignal(list)
    # Emitted from the tray (pystray) thread; slots run on the Qt main thread.
    _tray_open_requested = pyqtSignal()
    _tray_settings_requested = pyqtSignal()

    def __init__(self, config: dict | None = None):
        super().__init__()
        # Live config dict shared with main.py / Scanner so settings edits apply at runtime.
        self._config = config if config is not None else {}
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
        refresh_btn.clicked.connect(lambda: self._refresh_devices(force=True))
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
        self.scan_event.connect(self._on_scan_event)
        self._devices_loaded.connect(self._on_devices_loaded)
        self._tray_open_requested.connect(self._bring_to_front)
        self._tray_settings_requested.connect(self._open_settings_on_main_thread)

        # Map device_id -> latest scan info (for detail panel + table badge).
        self._latest_scans: dict[str, dict] = {}
        # Monotonic id of the latest refresh request (stale-result guard).
        self._refresh_seq = 0

        # Initial load (in background to avoid blocking the UI)
        self._refresh_devices(force=True)

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._detail_panel.clear()

    def _refresh_devices(self, *_args, force: bool = False) -> None:
        """Reload the connected devices table (WMI query runs in a thread).

        Category switches reuse a recent cached snapshot (instant); device
        events and the Refresh button pass force=True to re-query WMI."""
        idx = self._class_combo.currentIndex()
        _, class_filter = _CLASS_FILTERS[idx] if idx < len(_CLASS_FILTERS) else (None, None)
        max_age = 0.0 if force else 30.0

        # Drop results of superseded refreshes so a slow query that was
        # already in flight can't overwrite a newer one.
        self._refresh_seq += 1
        seq = self._refresh_seq

        def _query():
            if class_filter == _EXTERNAL:
                devices = get_external_devices(max_age_sec=max_age)
            else:
                devices = get_connected_devices(class_filter, max_age_sec=max_age)
            devices.sort(key=lambda d: (d.get("name") or "").lower())
            if seq != self._refresh_seq:
                return
            # Marshal back to the main thread — widgets must not be touched here.
            self._devices_loaded.emit(devices)

        threading.Thread(target=_query, daemon=True).start()

    @pyqtSlot(list)
    def _on_devices_loaded(self, devices: list) -> None:
        self._device_table.load_devices(devices)
        self._device_count_label.setText(f"{len(devices)} devices")

    @pyqtSlot(dict)
    def _on_device_event(self, event_info: dict) -> None:
        """Called (via signal) when a device connects or disconnects."""
        self._refresh_devices(force=True)
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

    def notify_scan_result(self, scan_info: dict) -> None:
        """Thread-safe method to push a security scan update to the UI."""
        self.scan_event.emit(scan_info)

    @pyqtSlot(dict)
    def _on_scan_event(self, scan_info: dict) -> None:
        device_id = scan_info.get("device_id")
        if device_id:
            self._latest_scans[device_id] = scan_info
        status = scan_info.get("status", "")
        name = scan_info.get("device_name") or "device"
        summary = scan_info.get("summary") or ""
        if status == "scanning":
            self._status_label.setText(f"Scanning {name}: {summary}")
        elif status == "threats_found":
            self._status_label.setText(f"Threats found on {name}: {summary}")
        elif status == "unsigned":
            self._status_label.setText(f"Unsigned driver: {name}")
        elif status == "clean":
            self._status_label.setText(f"Scan clean: {name}")
        elif status == "error":
            self._status_label.setText(f"Scan error ({name}): {summary}")
        # Refresh detail panel if it's showing this device.
        self._detail_panel.update_scan(scan_info)
        # If we just finished a scan, refresh history to show the new scan row.
        if status not in ("scanning",):
            self._history_view.refresh_if_visible()

    def request_open(self) -> None:
        """Thread-safe: bring the window to the front. Callable from any thread."""
        self._tray_open_requested.emit()

    def request_settings(self) -> None:
        """Thread-safe: open the settings dialog. Callable from any thread."""
        self._tray_settings_requested.emit()

    @pyqtSlot()
    def _bring_to_front(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    @pyqtSlot()
    def _open_settings_on_main_thread(self) -> None:
        self._bring_to_front()
        self.open_settings()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, live_config=self._config)
        dialog.exec()
