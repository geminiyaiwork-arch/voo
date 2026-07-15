"""Transparent always-on-top window that loads a live URL.

Complements HtmlOverlay: HtmlOverlay renders a local HTML string, while
WebOverlay loads any URL via QWebEngineView.  The recorder captures the
visible pixels so the site appears in the recorded video AND in every
live-stream target.

When a QWebEngineView is unavailable (no PyQt6-WebEngine) we fall back
to opening the URL in the system browser and printing a hint to the log.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    _WEB_OK = True
except (ImportError, Exception):                # pylint: disable=broad-except
    QWebEngineView = None                                  # type: ignore[assignment]
    QWebEngineSettings = None                              # type: ignore[assignment]
    _WEB_OK = False

logger = logging.getLogger(__name__)


class WebOverlay(QWidget):
    """Frameless, transparent, always-on-top URL renderer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("KO'ZGU — Web Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._url = ""
        self._zoom = 100
        self._transparent = True
        self._click_through = True

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        if _WEB_OK:
            self._view: QWebEngineView | QLabel = QWebEngineView(self)
            self._view.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True
            )
            page = self._view.page()
            try:
                page.setBackgroundColor(QColor(0, 0, 0, 0))
            except (AttributeError, RuntimeError):
                pass
            s = page.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            s.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                True,
            )
            s.setAttribute(
                QWebEngineSettings.WebAttribute.PluginsEnabled, True,
            )
            s.setAttribute(
                QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True,
            )
        else:
            # Fallback: no WebEngine — just show a stub explaining what
            # to install and open the URL in the system browser.
            fallback = QLabel(
                "QtWebEngine is not installed.\n"
                "sudo apt install python3-pyqt6.qtwebengine"
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("color:#fff;background:#0f172a;padding:20px;")
            self._view = fallback
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        v.addWidget(self._view)

    # ---------- public API ----------
    @staticmethod
    def web_engine_available() -> bool:
        return _WEB_OK

    def set_url(self, url: str) -> None:
        self._url = (url or "").strip()
        if not self._url:
            return
        if not self._url.startswith(("http://", "https://", "file://", "data:")):
            self._url = "https://" + self._url
        if _WEB_OK and isinstance(self._view, QWebEngineView):
            self._view.load(QUrl(self._url))
        else:
            # Fallback: system browser.
            import webbrowser
            try:
                webbrowser.open(self._url, new=1)
            except Exception:                       # pylint: disable=broad-except
                pass

    def reload(self) -> None:
        if _WEB_OK and isinstance(self._view, QWebEngineView):
            self._view.reload()

    def set_zoom_pct(self, pct: int) -> None:
        self._zoom = max(25, min(500, int(pct)))
        if _WEB_OK and isinstance(self._view, QWebEngineView):
            self._view.setZoomFactor(self._zoom / 100.0)

    def set_geometry(self, x: int, y: int, w: int, h: int) -> None:
        self.setGeometry(int(x), int(y), max(80, int(w)), max(60, int(h)))

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = bool(enabled)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            self._click_through,
        )

    def set_transparent(self, enabled: bool) -> None:
        self._transparent = bool(enabled)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            self._transparent,
        )
        if _WEB_OK and isinstance(self._view, QWebEngineView):
            try:
                self._view.page().setBackgroundColor(
                    QColor(0, 0, 0, 0) if self._transparent
                    else QColor("#0b1220")
                )
            except (AttributeError, RuntimeError):
                pass
