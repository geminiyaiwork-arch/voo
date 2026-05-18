"""Screenshot helper — FFmpeg first, with platform-specific fallbacks."""
from __future__ import annotations

import datetime
import shutil
import subprocess
import sys
from pathlib import Path


IS_WINDOWS = sys.platform.startswith("win")


def take_screenshot(folder: str,
                    region: tuple[int, int, int, int] | None = None) -> str | None:
    """Capture a PNG screenshot. Region is (x, y, w, h) or None for full screen."""
    folder_p = Path(folder).expanduser()
    folder_p.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    out = folder_p / f"screenshot_{ts}.png"

    if shutil.which("ffmpeg"):
        if IS_WINDOWS:
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                   "-f", "gdigrab"]
            if region:
                x, y, w, h = region
                cmd += ["-offset_x", str(x), "-offset_y", str(y),
                        "-video_size", f"{w}x{h}"]
            cmd += ["-i", "desktop", "-frames:v", "1", str(out)]
        else:
            if region:
                x, y, w, h = region
                cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                       "-f", "x11grab", "-video_size", f"{w}x{h}",
                       "-i", f":0.0+{x},{y}", "-frames:v", "1", str(out)]
            else:
                cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                       "-f", "x11grab", "-video_size", _screen_geom(),
                       "-i", ":0.0", "-frames:v", "1", str(out)]
        if subprocess.call(cmd) == 0 and out.exists():
            return str(out)

    if not IS_WINDOWS:
        if shutil.which("import"):
            cmd = ["import", "-window", "root", str(out)]
            if subprocess.call(cmd) == 0 and out.exists():
                return str(out)
        if shutil.which("scrot"):
            cmd = ["scrot", str(out)]
            if subprocess.call(cmd) == 0 and out.exists():
                return str(out)

    return None


def _screen_geom() -> str:
    if IS_WINDOWS:
        try:
            import ctypes
            user32 = ctypes.windll.user32                          # type: ignore[attr-defined]
            user32.SetProcessDPIAware()
            return f"{user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"
        except (OSError, AttributeError):
            return "1920x1080"
    try:
        out = subprocess.check_output(["xrandr"], stderr=subprocess.DEVNULL,
                                      text=True, timeout=2)
        for line in out.splitlines():
            if " connected primary" in line:
                for tok in line.split():
                    if "x" in tok and "+" in tok:
                        return tok.split("+")[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return "1920x1080"
