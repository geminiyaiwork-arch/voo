"""Transparent always-on-top window that renders the user's HTML.

Tries QWebEngineView first (full Chromium, modern HTML/CSS/JS); falls
back to QTextEdit's HTML-subset renderer if PyQt6-WebEngine isn't
installed. Both paths expose the same set_html() API.

When ``click_through`` is on, mouse events pass through to whatever is
underneath so the overlay doesn't steal clicks during a stream.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QSizePolicy

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    _WEB_OK = True
except (ImportError, Exception):                # pylint: disable=broad-except
    QWebEngineView = None                                  # type: ignore[assignment]
    QWebEngineSettings = None                              # type: ignore[assignment]
    _WEB_OK = False

logger = logging.getLogger(__name__)


class HtmlOverlay(QWidget):
    """Frameless, transparent, always-on-top HTML renderer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visio Eye — HTML Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._click_through = True
        self._transparent_bg = True

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        if _WEB_OK:
            self._view: QWebEngineView | QTextEdit = QWebEngineView(self)
            self._view.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True
            )
            page = self._view.page()
            try:
                page.setBackgroundColor(QColor(0, 0, 0, 0))
            except (AttributeError, RuntimeError):
                pass
            settings = page.settings()
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                True,
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                True,
            )
        else:
            te = QTextEdit(self)
            te.setReadOnly(True)
            te.setFrameStyle(0)
            te.setStyleSheet("background: transparent;")
            te.viewport().setAutoFillBackground(False)
            self._view = te
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        v.addWidget(self._view)

        self._html = ""

    # ---------- public API ----------
    def set_html(self, html: str) -> None:
        self._html = html or ""
        if _WEB_OK and isinstance(self._view, QWebEngineView):
            self._view.setHtml(self._html, baseUrl=QUrl("about:blank"))
        else:
            assert isinstance(self._view, QTextEdit)
            self._view.setHtml(self._html)

    def set_geometry(self, x: int, y: int, w: int, h: int) -> None:
        self.setGeometry(int(x), int(y), max(60, int(w)), max(40, int(h)))

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = bool(enabled)
        # WA_TransparentForMouseEvents must be applied AFTER show() for
        # X11 to honour it on every redraw.
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            self._click_through,
        )

    def set_transparent_background(self, enabled: bool) -> None:
        self._transparent_bg = bool(enabled)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            self._transparent_bg,
        )
        if not self._transparent_bg:
            pal = self.palette()
            pal.setColor(QPalette.ColorRole.Window, QColor("#000000"))
            self.setPalette(pal)

    @staticmethod
    def web_engine_available() -> bool:
        return _WEB_OK
