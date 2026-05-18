"""Draggable, resizable webcam preview overlay (transparent frameless window).

Uses OpenCV to grab v4l2 frames and renders them with a rounded mask + shadow.
Camera opening is done in a background thread so the UI never freezes while
``cv2.VideoCapture`` probes /dev/video* (which on Linux can take seconds).
"""
from __future__ import annotations

import sys
import threading

import cv2
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QImage, QPainter, QPixmap, QBrush, QColor, QPainterPath, QMouseEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import QWidget, QSizeGrip


class CameraOverlay(QWidget):
    _camera_ready = pyqtSignal(object)        # emitted with cv2.VideoCapture
    _camera_failed = pyqtSignal()

    def __init__(self, device: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(280, 200)
        self.setMinimumSize(120, 90)

        self._device = device
        self._cap: cv2.VideoCapture | None = None
        self._frame: QImage | None = None
        self._radius = 16
        self._opacity = 1.0
        self._drag_pos: QPoint | None = None
        self._opening = False
        self._open_thread: threading.Thread | None = None
        self._status = ""                  # text shown until first frame arrives

        self._grip = QSizeGrip(self)
        self._grip.setStyleSheet("background: transparent;")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._read_frame)

        # Signals fire on the worker thread; QueuedConnection marshals
        # them back to the main thread automatically.
        self._camera_ready.connect(self._on_camera_ready,
                                    Qt.ConnectionType.QueuedConnection)
        self._camera_failed.connect(self._on_camera_failed,
                                     Qt.ConnectionType.QueuedConnection)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        size = QSize(18, 18)
        self._grip.setGeometry(
            QRect(self.width() - size.width() - 4,
                  self.height() - size.height() - 4,
                  size.width(), size.height())
        )
        super().resizeEvent(a0)

    def set_device(self, device: str) -> None:
        was_running = self._timer.isActive()
        self.stop()
        self._device = device
        if was_running:
            self.start()

    def set_radius(self, r: int) -> None:
        self._radius = max(0, int(r))
        self.update()

    def set_opacity_pct(self, pct: int) -> None:
        self._opacity = max(0.0, min(1.0, pct / 100.0))
        self.setWindowOpacity(self._opacity)
        self.update()

    def start(self) -> bool:
        """Non-blocking camera start.

        Returns True immediately; the actual ``cv2.VideoCapture`` call
        runs on a background thread because it can stall the UI for
        several seconds on Linux when probing /dev/video* nodes.
        """
        if self._opening or self._cap is not None:
            self.show()
            return True
        self._opening = True
        self._status = "Camera loading…"
        self.show()
        self.update()
        self._open_thread = threading.Thread(
            target=self._open_worker, args=(self._device,),
            daemon=True, name="cam-open",
        )
        self._open_thread.start()
        return True

    def _open_worker(self, device: str) -> None:
        """Runs on a worker thread — must not touch Qt widgets directly."""
        cap = None
        try:
            if sys.platform.startswith("linux"):
                try:
                    idx = int(device.rsplit("video", 1)[-1])
                except (ValueError, AttributeError):
                    idx = 0
                cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(device) if device else None
            else:
                for i in range(5):
                    backend = (cv2.CAP_DSHOW if sys.platform.startswith("win")
                               else 0)
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        break
                    cap.release()
                    cap = None

            if cap is None or not cap.isOpened():
                self._camera_failed.emit()
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._camera_ready.emit(cap)
        except Exception:                                # pylint: disable=broad-except
            try:
                if cap is not None:
                    cap.release()
            except Exception:                            # pylint: disable=broad-except
                pass
            self._camera_failed.emit()

    def _on_camera_ready(self, cap) -> None:
        self._opening = False
        self._cap = cap
        self._status = ""
        self._timer.start(33)
        self.update()

    def _on_camera_failed(self) -> None:
        self._opening = False
        self._status = "Camera unavailable"
        self.update()

    def stop(self) -> None:
        self._opening = False
        self._timer.stop()
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:                            # pylint: disable=broad-except
                pass
            self._cap = None
        self._frame = None
        self.hide()

    def _read_frame(self) -> None:
        if not self._cap:
            return
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape
        img = QImage(frame.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        self._frame = img
        self.update()

    def paintEvent(self, _evt) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = self.rect().adjusted(6, 6, -6, -6)

        # subtle shadow ring
        for i in range(6, 0, -1):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 18 - i * 2)))
            painter.drawRoundedRect(rect.adjusted(-i, -i, i, i),
                                    self._radius + i, self._radius + i)

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(),
                            self._radius, self._radius)
        painter.setClipPath(path)

        if self._frame is None:
            painter.fillRect(rect, QColor(15, 23, 42, 220))
            painter.setPen(QColor(148, 163, 184))
            msg = self._status or "Camera Preview\n(no signal)"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)
        else:
            pm = QPixmap.fromImage(self._frame).scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = rect.x() + (rect.width() - pm.width()) // 2
            y = rect.y() + (rect.height() - pm.height()) // 2
            painter.drawPixmap(x, y, pm)

        painter.setClipping(False)
        painter.setPen(QColor(59, 130, 246, 140))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

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
