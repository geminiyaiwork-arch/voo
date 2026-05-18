"""Full-screen translucent window for selecting a rectangular capture region."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QGuiApplication, QFont
from PyQt6.QtWidgets import QWidget


class RegionSelector(QWidget):
    region_selected = pyqtSignal(int, int, int, int)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        screen = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._start: QPoint | None = None
        self._end: QPoint | None = None

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def mousePressEvent(self, e) -> None:
        self._start = e.position().toPoint()
        self._end = self._start
        self.update()

    def mouseMoveEvent(self, e) -> None:
        if self._start is not None:
            self._end = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e) -> None:
        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()
            if rect.width() > 8 and rect.height() > 8:
                self.region_selected.emit(rect.x(), rect.y(),
                                           rect.width(), rect.height())
            else:
                self.cancelled.emit()
        else:
            self.cancelled.emit()
        self.close()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 23, 42, 130))

        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(rect, Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            pen = QPen(QColor(56, 189, 248), 2)
            p.setPen(pen)
            p.drawRect(rect)

            p.setPen(QColor(226, 232, 240))
            f = QFont()
            f.setBold(True)
            p.setFont(f)
            p.drawText(rect.x(), max(rect.y() - 8, 14),
                       f"{rect.width()} × {rect.height()}")
        else:
            p.setPen(QColor(226, 232, 240))
            f = QFont()
            f.setBold(True)
            f.setPointSize(14)
            p.setFont(f)
            from i18n import tr
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("region.hint"))
