"""Device table widgets — live connected devices and event history."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView


class ConnectedDevicesTable(QTableWidget):
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
        self.setSortingEnabled(False)
        self.setRowCount(0)
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
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

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


class EventHistoryTable(QTableWidget):
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
            event_label = "Connected" if event_type == "connect" else "Disconnected"

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
                    item.setForeground(
                        Qt.GlobalColor.green if event_type == "connect"
                        else Qt.GlobalColor.red
                    )
                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

    def _on_selection_changed(self) -> None:
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            if 0 <= row < len(self._events):
                self.row_selected.emit(self._events[row])
