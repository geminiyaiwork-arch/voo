"""Cross-platform OS detection helpers shared across modules."""
from __future__ import annotations

import os
import sys
from pathlib import Path


IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"


def is_wayland() -> bool:
    return IS_LINUX and (
        os.environ.get("XDG_SESSION_TYPE") == "wayland"
        or bool(os.environ.get("WAYLAND_DISPLAY"))
    )


def default_videos_dir() -> Path:
    """Platform-correct default folder for recordings."""
    if IS_WINDOWS:
        userprofile = os.environ.get("USERPROFILE") or str(Path.home())
        return Path(userprofile) / "Videos" / "VisioEye"
    if IS_MACOS:
        return Path.home() / "Movies" / "VisioEye"
    return Path.home() / "Videos" / "VisioEye"


def default_camera_device() -> str:
    """Default camera identifier used in saved settings."""
    if IS_WINDOWS:
        return ""           # filled in at runtime from dshow enumeration
    if IS_MACOS:
        return "0"          # AVFoundation device index 0 (FaceTime camera)
    return "/dev/video0"
