"""Global hotkey manager using pynput.

Runs a background listener thread; emits PyQt signals when the user presses
one of the configured combinations.
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from pynput import keyboard
    _PYNPUT_OK = True
except (ImportError, Exception):    # pylint: disable=broad-except
    _PYNPUT_OK = False


class HotkeyManager(QObject):
    triggered = pyqtSignal(str)   # emits action name

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._listener: "keyboard.GlobalHotKeys | None" = None
        self._bindings: dict[str, str] = {}

    def update(self, hotkeys: dict[str, str]) -> None:
        self._bindings = dict(hotkeys)
        self.stop()
        self.start()

    def start(self) -> None:
        if not _PYNPUT_OK or not self._bindings:
            return
        mapping: dict[str, Callable[[], None]] = {}
        for action, combo in self._bindings.items():
            seq = self._to_pynput(combo)
            if not seq:
                continue
            mapping[seq] = lambda a=action: self.triggered.emit(a)
        try:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.start()
        except Exception:                     # pylint: disable=broad-except
            self._listener = None

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:                 # pylint: disable=broad-except
                pass
            self._listener = None

    @staticmethod
    def _to_pynput(combo: str) -> str:
        """Convert 'Ctrl+Shift+F9' -> '<ctrl>+<shift>+<f9>'."""
        if not combo:
            return ""
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        out: list[str] = []
        for p in parts:
            if p in ("ctrl", "control"):
                out.append("<ctrl>")
            elif p == "alt":
                out.append("<alt>")
            elif p == "shift":
                out.append("<shift>")
            elif p in ("super", "cmd", "win"):
                out.append("<cmd>")
            elif p.startswith("f") and p[1:].isdigit():
                out.append(f"<{p}>")
            else:
                out.append(p)
        return "+".join(out)
