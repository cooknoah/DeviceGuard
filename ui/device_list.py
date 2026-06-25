"""Device table widgets — live connected devices and event history."""

from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStyle, QStyledItemDelegate,
)

from core.security.types import ScanStatus
from ui.device_icons import icon_for_class
from ui.scan_status import (
    BADGE_LABELS, EVENT_LABELS, STATUS_COLORS,
    is_alert_result, status_of_log_string,
)

# Soft event colors matching the theme palette (ui/styles.py).
_CONNECT_COLOR = QColor("#4ade80")
_ALERT_COLOR = QColor("#f87171")
_CLEAN_COLOR = QColor("#38bdf8")

_SELECTION_BAR = QColor("#38bdf8")
_PLACEHOLDER_COLOR = QColor("#64748b")  # MUTED_DIM
_MUTED_COLOR = QColor("#94a3b8")  # MUTED

# Monospaced, muted styling for the long Device ID column. An explicit pixel
# size (matching the 13px UI font) avoids an unset point-size (-1) warning,
# since this is built at import time before the QApplication exists.
_MONO_FONT = QFont("Consolas")
_MONO_FONT.setStyleHint(QFont.StyleHint.Monospace)
_MONO_FONT.setPixelSize(13)

# Row data lives on column 0 under this role so selection survives sorting.
_ROW_DATA = Qt.ItemDataRole.UserRole


def _relative_time(iso: str) -> tuple[str, str]:
    """Map a stored UTC ISO timestamp to (relative label, absolute tooltip).

    The absolute form matches the detail panel's "… UTC" convention; the
    relative label is a coarse age ("2m ago", "3h ago", "5d ago") and falls
    back to an absolute date once events are more than a week old."""
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso, iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    absolute = dt_utc.strftime("%Y-%m-%d %H:%M:%S") + " UTC"

    delta = (datetime.now(timezone.utc) - dt_utc).total_seconds()
    if delta < 0:
        rel = absolute
    elif delta < 45:
        rel = "just now"
    elif delta < 3600:
        rel = f"{int(delta // 60)}m ago"
    elif delta < 86400:
        rel = f"{int(delta // 3600)}h ago"
    elif delta < 7 * 86400:
        rel = f"{int(delta // 86400)}d ago"
    else:
        rel = dt_utc.strftime("%Y-%m-%d")
    return rel, absolute


class _TimeItem(QTableWidgetItem):
    """History Time cell that shows a relative label but sorts chronologically
    by the raw ISO timestamp (lexical order matches time order)."""

    def __init__(self, text: str, sort_key: str):
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other: "QTableWidgetItem") -> bool:
        if isinstance(other, _TimeItem):
            return self._sort_key < other._sort_key
        return super().__lt__(other)


class _RowHighlightDelegate(QStyledItemDelegate):
    """Adds a 2px accent bar on the leftmost cell of the selected row; the
    soft row fill itself comes from the QSS item:selected rule."""

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if option.state & QStyle.StateFlag.State_Selected and index.column() == 0:
            bar = QRect(option.rect.left(), option.rect.top(), 2, option.rect.height())
            painter.fillRect(bar, _SELECTION_BAR)


class _SortToggleTable(QTableWidget):
    """QTableWidget where rapid header clicks keep toggling the sort, with a
    centered placeholder message painted when the table has no rows.

    Qt swallows the second of two quick clicks as a double-click, which
    normally does nothing on a header — making sort toggling feel laggy.
    Treat it as another sort toggle instead."""

    def __init__(self, rows: int, cols: int, parent=None):
        super().__init__(rows, cols, parent)
        self.horizontalHeader().sectionDoubleClicked.connect(self._toggle_sort)
        self.setItemDelegate(_RowHighlightDelegate(self))
        self.setShowGrid(False)
        # Single-line rows with elision — keeps every row the same height
        # instead of long names wrapping onto two lines.
        self.setWordWrap(False)
        # Always reserve the scrollbar gutter so the stretch columns keep the
        # same width whether or not a category has enough rows to scroll
        # (an as-needed scrollbar steals viewport width and shifts columns).
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # Roomier rows than the default (~30px) for a less cramped feel.
        self.verticalHeader().setDefaultSectionSize(36)
        self._placeholder = "Nothing to show"
        self._loading = False

    def _toggle_sort(self, section: int) -> None:
        header = self.horizontalHeader()
        flipped = (
            Qt.SortOrder.DescendingOrder
            if header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        header.setSortIndicator(section, flipped)

    def set_placeholder(self, text: str) -> None:
        """Message shown centered when the table is empty (and not loading)."""
        self._placeholder = text
        if self.rowCount() == 0:
            self.viewport().update()

    def set_loading(self, loading: bool) -> None:
        """Show a 'Loading…' placeholder while a background query is in flight."""
        if loading != self._loading:
            self._loading = loading
            if self.rowCount() == 0:
                self.viewport().update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.rowCount() > 0:
            return
        text = "Loading…" if self._loading else self._placeholder
        if not text:
            return
        painter = QPainter(self.viewport())
        painter.setPen(_PLACEHOLDER_COLOR)
        painter.drawText(
            self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, text
        )
        painter.end()


def _scan_cell(scan_info: dict | None) -> QTableWidgetItem:
    """Build the Security-column cell (colored dot + label) for a scan, or a
    muted placeholder when no scan has run for the device yet."""
    item = QTableWidgetItem()
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    status = (scan_info or {}).get("status", "")
    label = BADGE_LABELS.get(status)
    if label:
        item.setText(f"●  {label}")
        item.setForeground(QColor(STATUS_COLORS.get(status, "#94a3b8")))
        summary = (scan_info or {}).get("summary")
        item.setToolTip(summary or label)
    else:
        item.setText("—")
        item.setForeground(_PLACEHOLDER_COLOR)
    return item


class ConnectedDevicesTable(_SortToggleTable):
    """Table showing currently connected PnP devices."""

    row_selected = pyqtSignal(dict)

    _COLUMNS = ["Name", "Class", "Manufacturer", "Security", "Device ID"]
    _SECURITY_COL = 3

    def __init__(self, parent=None):
        super().__init__(0, len(self._COLUMNS), parent)
        self.setHorizontalHeaderLabels(self._COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        self.setIconSize(QSize(18, 18))
        self.set_placeholder("No devices found")

        header = self.horizontalHeader()
        # Name / Manufacturer / Device ID share the remaining width equally
        # (Stretch). Class and Security get FIXED widths rather than sizing to
        # content, so the layout stays identical across categories — otherwise
        # their content-driven widths shift every other column on each switch.
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(1, 110)   # Class
        self.setColumnWidth(3, 130)   # Security

        self._devices: list[dict] = []
        # device_id -> latest scan info, for repaint across refreshes.
        self._scans: dict[str, dict] = {}
        # Signature of the currently displayed rows, to skip redundant rebuilds.
        self._signature: tuple | None = None
        self.itemSelectionChanged.connect(self._on_selection_changed)

    @staticmethod
    def _signature_of(devices: list[dict], scans: dict[str, dict]) -> tuple:
        return tuple(
            (
                d.get("device_id"), d.get("name"), d.get("pnp_class"),
                d.get("manufacturer"), d.get("status"),
                (scans.get(d.get("device_id") or "") or {}).get("status"),
            )
            for d in devices
        )

    def load_devices(self, devices: list[dict], scans: dict[str, dict] | None = None) -> None:
        if scans is not None:
            self._scans = scans

        # Skip the (potentially heavy) rebuild when nothing visible changed —
        # background re-queries usually return the same data already shown, and
        # a needless rebuild mid-interaction can swallow a category-combo click.
        signature = self._signature_of(devices, self._scans)
        if signature == self._signature and self.rowCount() == len(devices):
            self._devices = devices
            return
        self._signature = signature

        # Remember the selection so background refreshes don't wipe it.
        selected_id = None
        sel = self.selectionModel().selectedRows()
        if sel:
            dev = self.item(sel[0].row(), 0).data(_ROW_DATA)
            if dev:
                selected_id = dev.get("device_id")

        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setCurrentItem(None)
        self._devices = devices

        for row_idx, dev in enumerate(devices):
            self.insertRow(row_idx)
            device_id = dev.get("device_id") or ""
            cells = [
                dev.get("name") or "",
                dev.get("pnp_class") or "",
                dev.get("manufacturer") or "",
                None,  # Security column built separately below
                device_id,
            ]
            for col_idx, text in enumerate(cells):
                if col_idx == self._SECURITY_COL:
                    item = _scan_cell(self._scans.get(device_id))
                else:
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setToolTip(text)
                if col_idx == 0:
                    item.setIcon(icon_for_class(dev.get("pnp_class")))
                    item.setData(_ROW_DATA, dev)
                elif col_idx == 4:  # Device ID — monospaced and dimmed
                    item.setFont(_MONO_FONT)
                    item.setForeground(_MUTED_COLOR)
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

        if selected_id:
            for row_idx in range(self.rowCount()):
                dev = self.item(row_idx, 0).data(_ROW_DATA)
                if dev and dev.get("device_id") == selected_id:
                    self.selectRow(row_idx)
                    break

    def update_scan_status(self, device_id: str, scan_info: dict) -> None:
        """Live-update a single device's Security cell when a scan reports in."""
        if not device_id:
            return
        self._scans[device_id] = scan_info
        for row_idx in range(self.rowCount()):
            dev = self.item(row_idx, 0).data(_ROW_DATA)
            if dev and dev.get("device_id") == device_id:
                self.setItem(row_idx, self._SECURITY_COL, _scan_cell(scan_info))
                break

    def _on_selection_changed(self) -> None:
        sel = self.selectionModel().selectedRows()
        if sel:
            dev = self.item(sel[0].row(), 0).data(_ROW_DATA)
            if dev:
                self.row_selected.emit(dev)


class EventHistoryTable(_SortToggleTable):
    """Table showing device event history from the database."""

    row_selected = pyqtSignal(dict)

    _COLUMNS = ["Time", "Event", "Device Name", "Class", "Manufacturer"]

    def __init__(self, parent=None):
        super().__init__(0, len(self._COLUMNS), parent)
        self.setHorizontalHeaderLabels(self._COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        self.set_placeholder("No events recorded yet")

        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self._events: list[dict] = []
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_events(self, events: list[dict]) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self._events = events

        for row_idx, ev in enumerate(events):
            self.insertRow(row_idx)

            raw_ts = ev.get("timestamp", "")
            rel_ts, abs_ts = _relative_time(raw_ts)

            event_type = ev.get("event_type", "")
            scan_result = ev.get("scan_result") or ""
            if event_type == "scan":
                scan_status = status_of_log_string(scan_result)
                event_label = EVENT_LABELS.get(scan_status, "Scan")
            elif event_type == "connect":
                event_label = "Connected"
            else:
                event_label = "Disconnected"

            items = [
                rel_ts,
                event_label,
                ev.get("device_name") or "",
                ev.get("device_class") or "",
                ev.get("manufacturer") or "",
            ]
            for col_idx, text in enumerate(items):
                if col_idx == 0:
                    item = _TimeItem(text, raw_ts)
                    item.setToolTip(abs_ts)
                else:
                    item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 0:
                    # Stable handle back to the source event, survives sorting.
                    item.setData(_ROW_DATA, ev)
                if col_idx == 2:
                    item.setIcon(icon_for_class(ev.get("device_class")))
                if col_idx == 1:
                    if event_type == "connect":
                        item.setForeground(_CONNECT_COLOR)
                    elif event_type == "disconnect":
                        item.setForeground(_ALERT_COLOR)
                    elif event_type == "scan":
                        if is_alert_result(scan_result):
                            item.setForeground(_ALERT_COLOR)
                        elif status_of_log_string(scan_result) == ScanStatus.CLEAN:
                            item.setForeground(_CLEAN_COLOR)
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

    def _on_selection_changed(self) -> None:
        sel = self.selectionModel().selectedRows()
        if sel:
            ev = self.item(sel[0].row(), 0).data(_ROW_DATA)
            if ev is not None:
                self.row_selected.emit(ev)
