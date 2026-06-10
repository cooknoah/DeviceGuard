"""Dark theme QSS stylesheet for DeviceGuard."""

DARK_THEME = """
/* ── Global ── */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── Main Window ── */
QMainWindow {
    background-color: #1a1a2e;
}

/* ── Sidebar ── */
QListWidget#sidebar {
    background-color: #16213e;
    border: none;
    border-right: 1px solid #0f3460;
    padding: 8px 4px;
    outline: none;
}
QListWidget#sidebar::item {
    padding: 10px 16px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #a0a0b8;
}
QListWidget#sidebar::item:selected {
    background-color: #0f3460;
    color: #00d4aa;
}
QListWidget#sidebar::item:hover:!selected {
    background-color: #1a2a4e;
    color: #c0c0d0;
}

/* ── Tables ── */
QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a2540;
    border: 1px solid #0f3460;
    border-radius: 6px;
    gridline-color: #0f3460;
    selection-background-color: #0f3460;
    selection-color: #00d4aa;
    outline: none;
}
QTableWidget::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #0f3460;
    color: #00d4aa;
    border: none;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #00d4aa;
    padding: 8px 18px 8px 10px;
    border: none;
    border-right: 1px solid #16213e;
    font-weight: bold;
}
QHeaderView::up-arrow, QHeaderView::down-arrow {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 12px;
    height: 12px;
    right: 4px;
}

/* ── Scroll bars ── */
QScrollBar:vertical {
    background: #16213e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #00d4aa;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #16213e;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #0f3460;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #00d4aa;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Detail panel ── */
QFrame#detail_panel {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 16px;
}
QLabel#detail_title {
    font-size: 18px;
    font-weight: bold;
    color: #00d4aa;
}
QLabel#detail_label {
    color: #808098;
    font-size: 12px;
}
QLabel#detail_value {
    color: #e0e0e0;
    font-size: 13px;
}

/* ── Buttons ── */
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #00d4aa;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #00d4aa;
    color: #1a1a2e;
}
QPushButton:pressed {
    background-color: #00b893;
}
QPushButton:disabled {
    background-color: #1a2540;
    border-color: #0f3460;
    color: #505068;
}

/* ── Combo box (filter) ── */
QComboBox {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 6px 12px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    selection-background-color: #0f3460;
    selection-color: #00d4aa;
    border: 1px solid #0f3460;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #0f3460;
    color: #00d4aa;
    font-size: 12px;
}
QStatusBar::item {
    border: none;
}
QSizeGrip {
    background-color: #0f3460;
    width: 12px;
    height: 12px;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #0f3460;
    width: 2px;
}

/* ── Tab widget (history) ── */
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 6px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #16213e;
    color: #808098;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0f3460;
    color: #00d4aa;
}
QTabBar::tab:hover:!selected {
    background-color: #1a2a4e;
    color: #c0c0d0;
}
"""
