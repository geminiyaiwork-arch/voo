"""Global QSS stylesheet — light / clean / modern."""
from __future__ import annotations

APP_STYLE = """
* {
    font-family: "Inter", "Segoe UI", "Cantarell", "Roboto", sans-serif;
    font-size: 13px;
    color: #0f172a;
}

QMainWindow, QDialog {
    background-color: #f8fafc;
}

QWidget#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}

QWidget#mainArea {
    background-color: #f8fafc;
}

QLabel#title {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QLabel#subtitle {
    color: #64748b;
    font-size: 12px;
}

QLabel#sectionHeader {
    color: #475569;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 4px 0;
}

QLabel#statusValue {
    color: #2563eb;
    font-weight: 700;
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}

QFrame#headerBar {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}

QPushButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border: 1px solid #3b82f6;
    color: #1e3a8a;
}
QPushButton:pressed {
    background-color: #e2e8f0;
}
QPushButton:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}

QPushButton#primary {
    background-color: #3b82f6;
    border: 1px solid #2563eb;
    color: #ffffff;
}
QPushButton#primary:hover {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton#primary:pressed {
    background-color: #1d4ed8;
}

QPushButton#danger {
    background-color: #ef4444;
    border: 1px solid #dc2626;
    color: #ffffff;
}
QPushButton#danger:hover {
    background-color: #dc2626;
    color: #ffffff;
}

QPushButton#ghost {
    background-color: transparent;
    border: 1px solid #cbd5e1;
    color: #334155;
}
QPushButton#ghost:hover {
    background-color: #eff6ff;
    border: 1px solid #3b82f6;
    color: #1e3a8a;
}
QPushButton#ghost:checked {
    background-color: #dbeafe;
    border: 1px solid #3b82f6;
    color: #1e3a8a;
}

QPushButton#sideTab {
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 12px 16px;
    text-align: left;
    color: #475569;
    font-weight: 500;
}
QPushButton#sideTab:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QPushButton#sideTab:checked {
    background-color: #eff6ff;
    border-left: 3px solid #3b82f6;
    color: #1e3a8a;
}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 10px;
    color: #0f172a;
    selection-background-color: #bfdbfe;
    selection-color: #0f172a;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover {
    border: 1px solid #3b82f6;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    selection-background-color: #dbeafe;
    selection-color: #1e3a8a;
    padding: 4px;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    background-color: #ffffff;
    color: #0f172a;
    padding: 6px 10px;
    border: none;
    min-height: 22px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #eff6ff;
    color: #1e3a8a;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #dbeafe;
    color: #1e3a8a;
}
QListView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    outline: 0;
}
QListView::item {
    background-color: #ffffff;
    color: #0f172a;
    padding: 6px 10px;
}
QListView::item:hover {
    background-color: #eff6ff;
    color: #1e3a8a;
}
QListView::item:selected {
    background-color: #dbeafe;
    color: #1e3a8a;
}
QFrame#qt_scrollarea_viewport,
QFrame[frameShape="0"] {
    background-color: transparent;
}

QSlider::groove:horizontal {
    background: #e2e8f0;
    height: 6px;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #3b82f6;
}
QSlider::handle:horizontal:hover {
    background: #eff6ff;
    border: 2px solid #2563eb;
}

QCheckBox {
    color: #334155;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:hover {
    border: 1px solid #3b82f6;
}
QCheckBox::indicator:checked {
    background: #3b82f6;
    border: 1px solid #2563eb;
    image: url({CHECK_ICON});
}
QCheckBox::indicator:checked:hover {
    background: #2563eb;
    border: 1px solid #1d4ed8;
    image: url({CHECK_ICON});
}

QRadioButton {
    color: #334155;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                                fx:0.5, fy:0.5,
                                stop:0 #3b82f6, stop:0.45 #3b82f6,
                                stop:0.5 #ffffff, stop:1 #ffffff);
    border: 1px solid #2563eb;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background-color: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 8px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #1e3a8a;
    background: #ffffff;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover {
    color: #0f172a;
}

QScrollArea {
    background-color: #f8fafc;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #f8fafc;
}
QTabWidget > QWidget {
    background-color: #ffffff;
}
QPlainTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
    selection-background-color: #bfdbfe;
    selection-color: #0f172a;
}
QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    color: #475569;
    font-weight: 600;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #2563eb;
    background-color: #f8fafc;
}

QToolTip {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #1e293b;
    padding: 6px 8px;
    border-radius: 6px;
}

QStatusBar {
    background: #ffffff;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
}

QLabel#recDot {
    color: #ef4444;
    font-size: 18px;
    font-weight: 900;
}

QLabel#timer {
    color: #0f172a;
    font-size: 26px;
    font-weight: 800;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    letter-spacing: 2px;
}
"""
