"""KO'ZGU — application entry point."""
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
from PyQt6.QtGui import QIcon, QPalette, QColor
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
    app.setApplicationName("KO'ZGU")
    app.setApplicationDisplayName("KO'ZGU")
    app.setOrganizationName("KO'ZGU")
    app.setStyle("Fusion")

    # Force a LIGHT palette across the whole app so QComboBox / QMenu
    # popups (which are top-level windows Qt creates outside the parent
    # stylesheet's scope) don't inherit the OS dark palette.  Without
    # this the language dropdown paints its popup black even though the
    # rest of Settings is white.
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor("#f8fafc"))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor("#0f172a"))
    pal.setColor(QPalette.ColorRole.Base,            QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#f1f5f9"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#0f172a"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#f8fafc"))
    pal.setColor(QPalette.ColorRole.Text,            QColor("#0f172a"))
    pal.setColor(QPalette.ColorRole.Button,          QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#0f172a"))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor("#ef4444"))
    pal.setColor(QPalette.ColorRole.Link,            QColor("#2563eb"))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor("#3b82f6"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))
    # Disabled variants stay in the same family so combos don't flash dark.
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.WindowText, QColor("#94a3b8"))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text,       QColor("#94a3b8"))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText, QColor("#94a3b8"))
    app.setPalette(pal)

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
