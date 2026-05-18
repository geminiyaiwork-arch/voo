"""Draggable, resizable logo overlay (frameless transparent window).

Displays user-chosen PNG / SVG / JPG on top of the screen for preview only.
FFmpeg performs the real overlay into the encoded video.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QMouseEvent, QResizeEvent, QImage,
)
from PyQt6.QtWidgets import QWidget, QSizeGrip


class LogoOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(160, 160)
        self.setMinimumSize(40, 40)

        self._pixmap: QPixmap | None = None
        self._opacity = 0.9
        self._drag_pos: QPoint | None = None

        self._grip = QSizeGrip(self)
        self._grip.setStyleSheet("background: transparent;")

    def resizeEvent(self, a0: QResizeEvent) -> None:
        size = QSize(16, 16)
        self._grip.setGeometry(
            QRect(self.width() - size.width() - 2,
                  self.height() - size.height() - 2,
                  size.width(), size.height())
        )
        super().resizeEvent(a0)

    def load(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        img = QImage(str(p))
        if img.isNull():
            return False
        self._pixmap = QPixmap.fromImage(img)
        self.update()
        return True

    def set_opacity_pct(self, pct: int) -> None:
        self._opacity = max(0.0, min(1.0, pct / 100.0))
        self.setWindowOpacity(self._opacity)
        self.update()

    def paintEvent(self, _evt) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = self.rect().adjusted(2, 2, -2, -2)
        if self._pixmap is None or self._pixmap.isNull():
            painter.fillRect(rect, QColor(30, 41, 59, 180))
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Logo")
            painter.setPen(QColor(59, 130, 246, 100))
            painter.drawRect(rect)
            return
        pm = self._pixmap.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = rect.x() + (rect.width() - pm.width()) // 2
        y = rect.y() + (rect.height() - pm.height()) // 2
        painter.drawPixmap(x, y, pm)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_pos is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_pos = None

    def position_dict(self) -> dict:
        g = self.geometry()
        return {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()}
