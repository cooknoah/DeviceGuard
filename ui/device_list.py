"""Device table widgets — live connected devices and event history."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView

from core.security.types import ScanStatus
from ui.scan_status import EVENT_LABELS, is_alert_result, status_of_log_string


class _SortToggleTable(QTableWidget):
    """QTableWidget where rapid header clicks keep toggling the sort.

    Qt swallows the second of two quick clicks as a double-click, which
    normally does nothing on a header — making sort toggling feel laggy.
    Treat it as another sort toggle instead."""

    def __init__(self, rows: int, cols: int, parent=None):
        super().__init__(rows, cols, parent)
        self.horizontalHeader().sectionDoubleClicked.connect(self._toggle_sort)

    def _toggle_sort(self, section: int) -> None:
        header = self.horizontalHeader()
        flipped = (
            Qt.SortOrder.DescendingOrder
            if header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        header.setSortIndicator(section, flipped)


class ConnectedDevicesTable(_SortToggleTable):
    """Table showing currently connected PnP devices."""

    row_selected = pyqtSignal(dict)

    _COLUMNS = ["Device Name", "Class", "Manufacturer", "Device ID"]

    def __init__(self, parent=None):
        super().__init__(0, len(self._COLUMNS), parent)
        self.setHorizontalHeaderLabels(self._COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self._devices: list[dict] = []
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_devices(self, devices: list[dict]) -> None:
        # Remember the selection so background refreshes don't wipe it.
        selected_id = None
        rows = self.selectionModel().selectedRows()
        if rows:
            sel_item = self.item(rows[0].row(), 3)
            if sel_item:
                selected_id = sel_item.text()

        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setCurrentItem(None)
        self._devices = devices

        for row_idx, dev in enumerate(devices):
            self.insertRow(row_idx)
            items = [
                dev.get("name") or "",
                dev.get("pnp_class") or "",
                dev.get("manufacturer") or "",
                dev.get("device_id") or "",
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(text)
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

        if selected_id:
            for row_idx in range(self.rowCount()):
                item = self.item(row_idx, 3)
                if item and item.text() == selected_id:
                    self.selectRow(row_idx)
                    break

    def _on_selection_changed(self) -> None:
        rows = self.selectionModel().selectedRows()
        if rows:
            # Map visual row back to data index accounting for sorting
            visual_row = rows[0].row()
            # Get the device_id from column 3 to find the right device
            item = self.item(visual_row, 3)
            if item:
                device_id = item.text()
                for dev in self._devices:
                    if dev.get("device_id") == device_id:
                        self.row_selected.emit(dev)
                        return


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

            ts = ev.get("timestamp", "")
            if "T" in ts:
                ts = ts.replace("T", " ").split("+")[0].split(".")[0]

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
                ts,
                event_label,
                ev.get("device_name") or "",
                ev.get("device_class") or "",
                ev.get("manufacturer") or "",
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 1:
                    if event_type == "connect":
                        item.setForeground(Qt.GlobalColor.green)
                    elif event_type == "disconnect":
                        item.setForeground(Qt.GlobalColor.red)
                    elif event_type == "scan":
                        if is_alert_result(scan_result):
                            item.setForeground(Qt.GlobalColor.red)
                        elif status_of_log_string(scan_result) == ScanStatus.CLEAN:
                            item.setForeground(Qt.GlobalColor.cyan)
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

    def _on_selection_changed(self) -> None:
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            if 0 <= row < len(self._events):
                self.row_selected.emit(self._events[row])
