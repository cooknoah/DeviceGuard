"""Dark theme QSS stylesheet for DeviceGuard.

Palette (three background layers + soft teal accent):
  page #0a1628 · surface #0f2035 · raised card #162840
  accent #38bdf8 · body text #cbd5e1 · muted #94a3b8 / #64748b
  borders rgba(255,255,255,7%)
Radius scale: 4px status pills · 6px badges/chips · 8px buttons/inputs · 10px cards/panels.

Translucent fills on item views (selection, sidebar pill, alternating rows)
are pre-blended into solid hex over their surface color — Qt composites
rgba item fills over its default highlight, so only solids render true.
"""

PAGE_BG = "#0a1628"
SURFACE_BG = "#0f2035"
CARD_BG = "#162840"
BORDER = "rgba(255, 255, 255, 7%)"
SELECTION_BG = "#133049"    # rgba(56,189,248,0.10) over surface
SIDEBAR_ACTIVE = "#14334c"  # rgba(56,189,248,0.12) over surface
SIDEBAR_HOVER = "#1b2b3f"   # rgba(255,255,255,0.05) over surface
ALT_ROW = "#15263a"         # rgba(255,255,255,0.025) over surface
ROW_SEPARATOR = "#22334a"   # rgba(255,255,255,0.05) over card
ACCENT = "#38bdf8"
BODY_TEXT = "#cbd5e1"
MUTED = "#94a3b8"
MUTED_DIM = "#64748b"

DARK_THEME = f"""
/* ── Global ── */
QWidget {{
    background-color: {PAGE_BG};
    color: {BODY_TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}

/* ── Main Window ── */
QMainWindow {{
    background-color: {PAGE_BG};
}}

/* ── Sidebar ── */
QListWidget#sidebar {{
    background-color: {SURFACE_BG};
    border: none;
    border-right: 1px solid {BORDER};
    border-radius: 12px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    padding: 8px 4px;
    outline: none;
}}
QListWidget#sidebar::item {{
    padding: 10px 16px;
    border-radius: 6px;
    border-left: 3px solid transparent;
    margin: 2px 8px;
    color: {MUTED};
}}
QListWidget#sidebar::item:selected {{
    background-color: {SIDEBAR_ACTIVE};
    border-left: 3px solid {ACCENT};
    border-radius: 6px;
    color: {ACCENT};
}}
QListWidget#sidebar::item:hover:!selected {{
    background-color: {SIDEBAR_HOVER};
    border-radius: 6px;
    color: {BODY_TEXT};
}}

/* ── Table card (rounded container wrapping each table) ── */
QFrame#table_card {{
    background-color: {SURFACE_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

/* ── Tables ── */
QTableWidget {{
    background-color: transparent;
    alternate-background-color: {ALT_ROW};
    border: none;
    gridline-color: transparent;
    selection-background-color: {SELECTION_BG};
    selection-color: {BODY_TEXT};
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {SELECTION_BG};
    color: {BODY_TEXT};
}}
QHeaderView::section {{
    background-color: {SURFACE_BG};
    color: {MUTED};
    padding: 8px 18px 8px 10px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 500;
}}
QHeaderView::up-arrow, QHeaderView::down-arrow {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 12px;
    height: 12px;
    right: 4px;
}}
QTableCornerButton::section {{
    background-color: {SURFACE_BG};
    border: none;
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 12%);
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(56, 189, 248, 60%);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 12%);
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(56, 189, 248, 60%);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Detail panel (raised card) ── */
QFrame#detail_panel {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px;
}}
QFrame#detail_panel QWidget {{
    background-color: transparent;
}}
QLabel#detail_title {{
    font-size: 16px;
    font-weight: 600;
    color: #e2e8f0;
}}
QLabel#detail_label {{
    color: {MUTED_DIM};
    font-size: 12px;
}}
QLabel#detail_value {{
    color: {BODY_TEXT};
    font-size: 13px;
}}
QFrame#row_separator {{
    background-color: {ROW_SEPARATOR};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {CARD_BG};
    color: {BODY_TEXT};
    border: 1px solid rgba(255, 255, 255, 14%);
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: rgba(56, 189, 248, 14%);
    border-color: rgba(56, 189, 248, 45%);
    color: #e2f3ff;
}}
QPushButton:pressed {{
    background-color: rgba(56, 189, 248, 24%);
}}
QPushButton:disabled {{
    background-color: {SURFACE_BG};
    border-color: {BORDER};
    color: {MUTED_DIM};
}}

/* ── Combo box (category chip) ── */
QComboBox {{
    background-color: {CARD_BG};
    color: {BODY_TEXT};
    border: 1px solid rgba(255, 255, 255, 12%);
    border-radius: 6px;
    padding: 5px 12px;
}}
QComboBox:hover {{
    border-color: rgba(56, 189, 248, 40%);
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {CARD_BG};
    color: {BODY_TEXT};
    selection-background-color: rgba(56, 189, 248, 14%);
    selection-color: {ACCENT};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* ── Line edits (search box, settings) ── */
QLineEdit {{
    background-color: {SURFACE_BG};
    color: {BODY_TEXT};
    border: 1px solid rgba(255, 255, 255, 12%);
    border-radius: 8px;
    padding: 6px 10px;
}}
QLineEdit:focus {{
    border-color: rgba(56, 189, 248, 50%);
}}

/* ── Muted secondary labels (device count, history count) ── */
QLabel#muted_label {{
    color: {MUTED_DIM};
    font-size: 12px;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {PAGE_BG};
    border-top: 1px solid {BORDER};
    padding: 8px 8px;
    font-size: 12px;
}}
QStatusBar::item {{
    border: none;
}}
QLabel#status_dot {{
    background-color: #4ade80;
    border-radius: 4px;
    margin-left: 6px;
}}
QLabel#status_text {{
    color: {MUTED_DIM};
    font-size: 12px;
}}
QSizeGrip {{
    background-color: transparent;
    width: 12px;
    height: 12px;
}}

/* ── Splitter (table ⇄ detail divider) ── */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
    margin: 0 4px;
}}

/* ── Checkboxes / spinboxes (settings dialog) ── */
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid rgba(255, 255, 255, 20%);
    border-radius: 4px;
    background-color: {SURFACE_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QSpinBox, QDoubleSpinBox {{
    background-color: {SURFACE_BG};
    color: {BODY_TEXT};
    border: 1px solid rgba(255, 255, 255, 12%);
    border-radius: 8px;
    padding: 5px 8px;
}}

/* ── Tab widget (history) ── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background-color: {SURFACE_BG};
}}
QTabBar::tab {{
    background-color: {SURFACE_BG};
    color: {MUTED};
    padding: 8px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {CARD_BG};
    color: {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: rgba(255, 255, 255, 4%);
    color: {BODY_TEXT};
}}
"""
