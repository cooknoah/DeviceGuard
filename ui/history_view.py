"""History view tab with event table, filters, and CSV export."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFileDialog,
)

from core import logger
from ui.device_list import EventHistoryTable


class HistoryView(QWidget):
    """Full history view with filter combo, event table, and export button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Filter:"))

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All Events", "Connections", "Disconnections"])
        self._filter_combo.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self._filter_combo)

        toolbar.addStretch()

        self._count_label = QLabel()
        toolbar.addWidget(self._count_label)

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(self._export_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self._refresh_btn)

        layout.addLayout(toolbar)

        # Event table
        self.table = EventHistoryTable()
        layout.addWidget(self.table)

    def _get_filter(self) -> str | None:
        idx = self._filter_combo.currentIndex()
        if idx == 1:
            return "connect"
        elif idx == 2:
            return "disconnect"
        return None

    def _refresh(self) -> None:
        events = logger.get_events(limit=500, event_type_filter=self._get_filter())
        self.table.load_events(events)
        self._count_label.setText(f"{len(events)} events")

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Events to CSV", "device_events.csv",
            "CSV Files (*.csv)"
        )
        if path:
            logger.export_csv(path)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh()
