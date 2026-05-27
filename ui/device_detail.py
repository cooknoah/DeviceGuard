"""Device detail panel showing full info for a selected device or event."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout


class DeviceDetailPanel(QFrame):
    """Right-side panel showing details of a selected device or event."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detail_panel")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title = QLabel("Select a device")
        self._title.setObjectName("detail_title")
        layout.addWidget(self._title)
        layout.addSpacing(12)

        self._grid = QGridLayout()
        self._grid.setVerticalSpacing(8)
        self._grid.setHorizontalSpacing(12)
        layout.addLayout(self._grid)

        self._rows: list[tuple[QLabel, QLabel]] = []
        layout.addStretch()

    def _clear_grid(self) -> None:
        for label, value in self._rows:
            self._grid.removeWidget(label)
            self._grid.removeWidget(value)
            label.deleteLater()
            value.deleteLater()
        self._rows.clear()

    def _add_row(self, label_text: str, value_text: str) -> None:
        row = len(self._rows)
        label = QLabel(label_text)
        label.setObjectName("detail_label")
        value = QLabel(value_text)
        value.setObjectName("detail_value")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignTop)
        self._grid.addWidget(value, row, 1)
        self._rows.append((label, value))

    def show_device(self, device: dict) -> None:
        """Show details for a currently connected device."""
        self._clear_grid()
        self._title.setText(device.get("name") or "Unknown Device")
        self._add_row("Device ID", device.get("device_id") or "—")
        self._add_row("Class", device.get("pnp_class") or "—")
        self._add_row("Manufacturer", device.get("manufacturer") or "—")
        self._add_row("Status", device.get("status") or "—")

    def show_event(self, event: dict) -> None:
        """Show details for a device event from history."""
        self._clear_grid()
        self._title.setText(event.get("device_name") or "Unknown Device")

        event_type = event.get("event_type", "")
        self._add_row("Event Type", "Connected" if event_type == "connect" else "Disconnected")

        ts = event.get("timestamp") or "—"
        if "T" in ts:
            ts = ts.replace("T", " ").split("+")[0].split(".")[0] + " UTC"
        self._add_row("Timestamp", ts)
        self._add_row("Device Name", event.get("device_name") or "—")
        self._add_row("Device ID", event.get("device_id") or "—")
        self._add_row("Device Class", event.get("device_class") or "—")
        self._add_row("Manufacturer", event.get("manufacturer") or "—")

        ds = event.get("driver_signed")
        self._add_row("Driver Signed", "Yes" if ds else "No" if ds is not None else "—")
        self._add_row("Scan Result", event.get("scan_result") or "—")

    def clear(self) -> None:
        self._clear_grid()
        self._title.setText("Select a device")
