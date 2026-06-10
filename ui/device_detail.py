"""Device detail panel showing full info for a selected device or event."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout


_STATUS_COLORS = {
    "clean": "#4caf50",
    "scanning": "#2196f3",
    "threats_found": "#f44336",
    "unsigned": "#ff9800",
    "error": "#9e9e9e",
    "skipped": "#9e9e9e",
}

_STATUS_LABELS = {
    "clean": "Clean",
    "scanning": "Scanning…",
    "threats_found": "Threats Found",
    "unsigned": "Unsigned Driver",
    "error": "Scan Error",
    "skipped": "Scan Skipped",
}


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

        self._scan_badge = QLabel("")
        self._scan_badge.setObjectName("scan_badge")
        self._scan_badge.setVisible(False)
        self._scan_badge.setStyleSheet(
            "padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold;"
        )
        layout.addWidget(self._scan_badge)

        self._scan_summary = QLabel("")
        self._scan_summary.setWordWrap(True)
        self._scan_summary.setVisible(False)
        layout.addWidget(self._scan_summary)

        self._findings_label = QLabel("")
        self._findings_label.setWordWrap(True)
        self._findings_label.setVisible(False)
        self._findings_label.setStyleSheet("color: #f44336;")
        layout.addWidget(self._findings_label)

        layout.addSpacing(12)

        self._grid = QGridLayout()
        self._grid.setVerticalSpacing(8)
        self._grid.setHorizontalSpacing(12)
        layout.addLayout(self._grid)

        self._rows: list[tuple[QLabel, QLabel]] = []
        layout.addStretch()

        # Track which device is currently displayed (for live scan updates).
        self._current_device_id: str | None = None
        # Latest scan info per device_id, retained across detail switches.
        self._scan_cache: dict[str, dict] = {}

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

    def _render_scan(self, scan_info: dict | None) -> None:
        if not scan_info:
            self._scan_badge.setVisible(False)
            self._scan_summary.setVisible(False)
            self._findings_label.setVisible(False)
            return
        status = scan_info.get("status", "")
        color = _STATUS_COLORS.get(status, "#9e9e9e")
        label = _STATUS_LABELS.get(status, status.title() or "Unknown")
        self._scan_badge.setStyleSheet(
            f"padding: 4px 8px; border-radius: 4px; "
            f"color: white; font-weight: bold; background-color: {color};"
        )
        self._scan_badge.setText(label)
        self._scan_badge.setVisible(True)

        summary = scan_info.get("summary") or ""
        self._scan_summary.setText(summary)
        self._scan_summary.setVisible(bool(summary))

        findings = scan_info.get("findings") or []
        if findings:
            lines = []
            for f in findings[:10]:
                src = f.get("source", "?")
                lbl = f.get("label", "")
                det = f.get("detail", "")
                if det:
                    lines.append(f"• [{src}] {lbl} — {det}")
                else:
                    lines.append(f"• [{src}] {lbl}")
            if len(findings) > 10:
                lines.append(f"… and {len(findings) - 10} more")
            self._findings_label.setText("\n".join(lines))
            self._findings_label.setVisible(True)
        else:
            self._findings_label.setVisible(False)

    def show_device(self, device: dict) -> None:
        """Show details for a currently connected device."""
        self._clear_grid()
        self._current_device_id = device.get("device_id")
        self._title.setText(device.get("name") or "Unknown Device")
        self._add_row("Device ID", device.get("device_id") or "—")
        self._add_row("Class", device.get("pnp_class") or "—")
        self._add_row("Manufacturer", device.get("manufacturer") or "—")
        self._add_row("Status", device.get("status") or "—")
        self._render_scan(self._scan_cache.get(self._current_device_id))

    def show_event(self, event: dict) -> None:
        """Show details for a device event from history."""
        self._clear_grid()
        self._current_device_id = event.get("device_id")
        self._title.setText(event.get("device_name") or "Unknown Device")

        event_type = event.get("event_type", "")
        type_label = {
            "connect": "Connected",
            "disconnect": "Disconnected",
            "scan": "Security Scan",
        }.get(event_type, event_type or "—")
        self._add_row("Event Type", type_label)

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
        self._render_scan(self._scan_cache.get(self._current_device_id))

    def update_scan(self, scan_info: dict) -> None:
        """Receive a live scan-status update from the scanner."""
        device_id = scan_info.get("device_id")
        if device_id:
            self._scan_cache[device_id] = scan_info
        if device_id and device_id == self._current_device_id:
            self._render_scan(scan_info)

    def clear(self) -> None:
        self._clear_grid()
        self._current_device_id = None
        self._title.setText("Select a device")
        self._render_scan(None)
