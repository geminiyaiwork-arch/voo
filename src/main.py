"""Visio Eye — application entry point."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _setup_path() -> None:
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))


_setup_path()


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from i18n import set_language
from settings import SettingsManager
from ui.main_window import MainWindow
from ui.styles import APP_STYLE


def main() -> int:
    if sys.platform.startswith("linux"):
        # Force xcb under Wayland so PyQt6 windows render predictably
        # without missing XWayland fallbacks for our overlays.
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    app = QApplication(sys.argv)
    app.setApplicationName("Visio Eye")
    app.setApplicationDisplayName("Visio Eye")
    app.setOrganizationName("Visio Eye")
    app.setStyle("Fusion")
    check_icon = Path(__file__).resolve().parents[1] / "assets" / "icons" / "check_white.svg"
    app.setStyleSheet(APP_STYLE.replace("{CHECK_ICON}", str(check_icon)))

    for cand in ("logo.png", "author.png"):
        icon = Path(__file__).resolve().parents[1] / "assets" / "img" / cand
        if icon.exists():
            app.setWindowIcon(QIcon(str(icon)))
            break

    settings = SettingsManager()
    set_language(settings.get("general", "language", "uz"))

    try:
        win = MainWindow(settings)
        win.show()
    except Exception:                               # pylint: disable=broad-except
        msg = traceback.format_exc()
        sys.stderr.write(msg)
        QMessageBox.critical(None, "Startup error", msg)
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
