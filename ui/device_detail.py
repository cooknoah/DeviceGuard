"""Device detail panel showing full info for a selected device or event."""

import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget

from ui.scan_status import BADGE_LABELS, STATUS_COLORS


def _breakable(text: str) -> str:
    """Insert zero-width spaces after separators so unbroken tokens
    (device IDs like USB\\VID_046D&PID_C31C\\...) can word-wrap."""
    return re.sub(r"([\\&_/])", lambda m: m.group(1) + "\u200b", text)


def _alpha_bg(hex_color: str, pct: int = 15) -> str:
    """Low-opacity rgba() background from a #rrggbb accent color."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {pct}%)"


# Device health (WMI Status field) \u2192 (background, text color).
_HEALTH_STYLES = {
    "ok": ("rgba(74, 222, 128, 15%)", "#4ade80"),
    "error": ("rgba(248, 113, 113, 15%)", "#f87171"),
    # Warning / Degraded / Unknown fall through to amber.
}
_HEALTH_FALLBACK = ("rgba(251, 191, 36, 15%)", "#fbbf24")



class DeviceDetailPanel(QFrame):
    """Right-side panel showing details of a selected device or event."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detail_panel")
        self.setMinimumWidth(280)

        # No setAlignment(AlignTop) here: it forces children to their size
        # hints, which breaks height-for-width on word-wrapped labels.
        # The addStretch() at the end pins content to the top instead.
        layout = QVBoxLayout(self)

        self._title = QLabel("Select a device")
        self._title.setObjectName("detail_title")
        self._title.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addSpacing(12)

        self._scan_badge = QLabel("")
        self._scan_badge.setObjectName("scan_badge")
        self._scan_badge.setVisible(False)
        self._scan_badge.setStyleSheet(
            "padding: 4px 10px; border-radius: 6px; font-weight: 600;"
        )
        layout.addWidget(self._scan_badge)

        self._scan_summary = QLabel("")
        self._scan_summary.setWordWrap(True)
        self._scan_summary.setVisible(False)
        layout.addWidget(self._scan_summary)

        self._findings_label = QLabel("")
        self._findings_label.setWordWrap(True)
        self._findings_label.setVisible(False)
        self._findings_label.setStyleSheet("color: #f87171;")
        layout.addWidget(self._findings_label)

        layout.addSpacing(12)

        self._grid = QGridLayout()
        self._grid.setVerticalSpacing(10)
        self._grid.setHorizontalSpacing(12)
        # Let the value column absorb the panel width so word-wrapped
        # labels compute their height from the real available width.
        self._grid.setColumnStretch(1, 1)
        layout.addLayout(self._grid)

        self._rows: list[tuple[QLabel, QWidget]] = []
        self._separators: list[QFrame] = []
        self._grid_row = 0
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
        for sep in self._separators:
            self._grid.removeWidget(sep)
            sep.deleteLater()
        self._rows.clear()
        self._separators.clear()
        self._grid_row = 0

    def _begin_row(self, label_text: str) -> QLabel:
        """Add the separator (between rows) and the field label; returns
        the label. The caller places the value widget at column 1."""
        if self._rows:
            sep = QFrame()
            sep.setObjectName("row_separator")
            self._grid.addWidget(sep, self._grid_row, 0, 1, 2)
            self._separators.append(sep)
            self._grid_row += 1
        label = QLabel(label_text)
        label.setObjectName("detail_label")
        self._grid.addWidget(label, self._grid_row, 0, Qt.AlignmentFlag.AlignTop)
        return label

    def _add_row(self, label_text: str, value_text: str) -> None:
        label = self._begin_row(label_text)
        value = QLabel(_breakable(value_text))
        value.setObjectName("detail_value")
        value.setWordWrap(True)
        value.setToolTip(value_text)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._grid.addWidget(value, self._grid_row, 1)
        self._grid_row += 1
        self._rows.append((label, value))
        # Height-for-width doesn't always propagate through the grid when
        # rows are added to an already-visible panel; enforce it deferred,
        # once the label has its final width.
        QTimer.singleShot(0, self._apply_wrap_heights)

    def _add_status_row(self, status: str | None) -> None:
        """Device health as a small colored badge pill (OK/Error/Warning…)."""
        label = self._begin_row("Status")
        text = status or "Unknown"
        bg, fg = _HEALTH_STYLES.get(text.lower(), _HEALTH_FALLBACK)
        badge = QLabel(text)
        badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 4px; "
            f"padding: 3px 10px; font-size: 12px; font-weight: 500;"
        )
        # Keep the pill snug instead of stretching across the column.
        container = QWidget()
        box = QHBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(badge)
        box.addStretch()
        self._grid.addWidget(container, self._grid_row, 1)
        self._grid_row += 1
        self._rows.append((label, container))

    def _apply_wrap_heights(self) -> None:
        for _, value in self._rows:
            w = value.width()
            if w > 0:
                h = value.heightForWidth(w)
                if h > 0:
                    value.setMinimumHeight(h)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._apply_wrap_heights)

    def _render_scan(self, scan_info: dict | None) -> None:
        if not scan_info:
            self._scan_badge.setVisible(False)
            self._scan_summary.setVisible(False)
            self._findings_label.setVisible(False)
            return
        status = scan_info.get("status", "")
        color = STATUS_COLORS.get(status, "#94a3b8")
        label = BADGE_LABELS.get(status, status.title() or "Unknown")
        self._scan_badge.setStyleSheet(
            f"padding: 4px 10px; border-radius: 6px; font-weight: 600; "
            f"color: {color}; background-color: {_alpha_bg(color)};"
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
        self._add_status_row(device.get("status"))
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
