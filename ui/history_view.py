"""History view tab with event table, filters, and CSV export."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFileDialog, QLineEdit, QFrame,
)

from core import logger
from ui.device_list import EventHistoryTable
from ui.scan_status import is_alert_result


class HistoryView(QWidget):
    """Full history view with filter combo, event table, and export button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Filter:"))

        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            "All Events", "Connections", "Disconnections", "Scans", "Threats Only",
        ])
        self._filter_combo.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self._filter_combo)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search name, ID, manufacturer…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMaximumWidth(280)
        # Debounce so filtering runs once per pause, not per keystroke.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._refresh)
        self._search_box.textChanged.connect(
            lambda _text: self._search_timer.start()
        )
        toolbar.addWidget(self._search_box)

        toolbar.addStretch()

        self._count_label = QLabel()
        self._count_label.setObjectName("muted_label")
        toolbar.addWidget(self._count_label)

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(self._export_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self._refresh_btn)

        layout.addLayout(toolbar)

        # Event table inside a rounded card
        self.table = EventHistoryTable()
        table_card = QFrame()
        table_card.setObjectName("table_card")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.addWidget(self.table)
        layout.addWidget(table_card)

    def _get_filter(self) -> str | None:
        idx = self._filter_combo.currentIndex()
        return {1: "connect", 2: "disconnect", 3: "scan"}.get(idx)

    def _refresh(self) -> None:
        idx = self._filter_combo.currentIndex()
        if idx == 4:  # Threats Only
            events = logger.get_events(limit=500, event_type_filter="scan")
            events = [e for e in events if is_alert_result(e.get("scan_result"))]
        else:
            events = logger.get_events(limit=500, event_type_filter=self._get_filter())
        query = self._search_box.text().strip().lower()
        if query:
            events = [
                e for e in events
                if any(
                    query in (e.get(field) or "").lower()
                    for field in (
                        "device_name", "device_id", "manufacturer", "scan_result",
                    )
                )
            ]
        self.table.load_events(events)
        self._count_label.setText(f"{len(events)} events")

    def refresh_if_visible(self) -> None:
        if self.isVisible():
            self._refresh()

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
