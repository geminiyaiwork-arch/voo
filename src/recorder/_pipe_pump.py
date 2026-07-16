"""Background stderr drainer for long-lived subprocess.PIPE handles.

Rationale: ffmpeg spawns with `stderr=subprocess.PIPE`.  If nothing reads
that pipe, the OS pipe buffer (~64 KB on Linux) fills after a few minutes
of progress lines; ffmpeg then blocks on write() and the encode stops —
mid-broadcast.  This module runs a daemon thread that reads the pipe into
a bounded ring buffer so ffmpeg keeps producing forever, and the last N
KB of stderr are still available for post-mortem logging on stop().
"""
from __future__ import annotations

import collections
import subprocess
import threading


class StderrDrainer:
    """Continuously drain a process stderr into a bounded deque of bytes.

    The last `max_bytes` of stderr are retained.  Call ``.text()`` at any
    time to snapshot as UTF-8; call ``.stop()`` to join the thread (best
    effort — daemon, so process exit is fine too).
    """
    def __init__(self, proc: subprocess.Popen, max_bytes: int = 256 * 1024,
                 on_line=None) -> None:
        self._buf: collections.deque[bytes] = collections.deque()
        self._size = 0
        self._max = max_bytes
        self._lock = threading.Lock()
        self._proc = proc
        self._on_line = on_line
        self._t = threading.Thread(
            target=self._run, name="stderr-drainer", daemon=True,
        )
        self._t.start()

    def _run(self) -> None:
        pipe = self._proc.stderr
        if pipe is None:
            return
        try:
            for chunk in iter(lambda: pipe.readline(), b""):
                if not chunk:
                    break
                with self._lock:
                    self._buf.append(chunk)
                    self._size += len(chunk)
                    while self._size > self._max and self._buf:
                        self._size -= len(self._buf.popleft())
                if self._on_line is not None:
                    try:
                        self._on_line(chunk)
                    except Exception:
                        pass
        except (OSError, ValueError):
            pass

    def text(self) -> str:
        with self._lock:
            data = b"".join(self._buf)
        return data.decode("utf-8", errors="ignore")

    def stop(self, timeout: float = 0.5) -> None:
        try:
            self._t.join(timeout=timeout)
        except RuntimeError:
            pass
