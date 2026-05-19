"""Runtime CPU / GPU / disk usage probing + device enumeration.

Cross-platform: Linux uses v4l2/PulseAudio, Windows uses DirectShow via
`ffmpeg -list_devices`. macOS is best-effort (returns defaults).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import psutil


IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"


_DSHOW_CACHE: dict[str, tuple[list[str], list[str]]] = {}
_AVF_CACHE: dict[str, tuple[list[tuple[str, str]], list[tuple[str, str]]]] = {}


def _query_avfoundation_devices() -> tuple[list[tuple[str, str]],
                                            list[tuple[str, str]]]:
    """macOS: parse `ffmpeg -f avfoundation -list_devices` for video + audio.

    Returns ([(id, name)], [(id, name)]).
    """
    if "x" in _AVF_CACHE:
        return _AVF_CACHE["x"]
    video: list[tuple[str, str]] = []
    audio: list[tuple[str, str]] = []
    if not shutil.which("ffmpeg"):
        _AVF_CACHE["x"] = (video, audio)
        return video, audio
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "avfoundation",
             "-list_devices", "true", "-i", ""],
            capture_output=True, text=True, timeout=5,
        )
        text = (proc.stderr or "") + (proc.stdout or "")
    except (OSError, subprocess.SubprocessError):
        text = ""
    section = None
    line_re = re.compile(r"\[(\d+)\]\s+(.+)")
    for line in text.splitlines():
        if "AVFoundation video devices" in line:
            section = "video"
            continue
        if "AVFoundation audio devices" in line:
            section = "audio"
            continue
        m = line_re.search(line)
        if m and section:
            target = video if section == "video" else audio
            target.append((m.group(1), m.group(2).strip()))
    _AVF_CACHE["x"] = (video, audio)
    return video, audio


def _query_dshow_devices() -> tuple[list[str], list[str]]:
    """Run `ffmpeg -list_devices` and parse video + audio dshow devices.

    Returns ([video_devices], [audio_devices]).
    """
    if "x" in _DSHOW_CACHE:
        return _DSHOW_CACHE["x"]

    video: list[str] = []
    audio: list[str] = []
    if not shutil.which("ffmpeg"):
        _DSHOW_CACHE["x"] = (video, audio)
        return video, audio

    try:
        # FFmpeg writes the device list to stderr and exits non-zero;
        # we just collect everything.
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true",
             "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, timeout=8,
        )
        raw = (proc.stderr or "") + "\n" + (proc.stdout or "")
    except (OSError, subprocess.SubprocessError):
        _DSHOW_CACHE["x"] = (video, audio)
        return video, audio

    section = None
    # Lines look like:  [dshow @ ...] "Device Name" (video)
    name_re = re.compile(r'"([^"]+)"\s*\((video|audio)\)')
    for line in raw.splitlines():
        m = name_re.search(line)
        if m:
            name, kind = m.group(1), m.group(2)
            if kind == "video":
                video.append(name)
            else:
                audio.append(name)
            continue
        # Older FFmpeg formatting splits the type onto next line.
        if "DirectShow video devices" in line:
            section = "video"
            continue
        if "DirectShow audio devices" in line:
            section = "audio"
            continue
        m2 = re.search(r'\]\s+"([^"]+)"', line)
        if m2 and section:
            target = video if section == "video" else audio
            if m2.group(1) not in target:
                target.append(m2.group(1))

    _DSHOW_CACHE["x"] = (video, audio)
    return video, audio


class SystemInfo:
    """Lightweight system metrics polled on a timer + device enumeration."""

    @staticmethod
    def cpu_percent() -> float:
        return psutil.cpu_percent(interval=None)

    @staticmethod
    def memory_percent() -> float:
        return psutil.virtual_memory().percent

    @staticmethod
    def disk_free_gb(folder: str) -> float:
        try:
            p = Path(folder).expanduser()
            if not p.exists():
                p = p.parent
            usage = shutil.disk_usage(str(p))
            return usage.free / (1024 ** 3)
        except OSError:
            return 0.0

    @staticmethod
    def gpu_percent() -> float | None:
        """Best-effort NVIDIA GPU usage. Returns None if unavailable."""
        if not shutil.which("nvidia-smi"):
            return None
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL, text=True, timeout=1,
            )
            line = out.strip().splitlines()[0]
            return float(line)
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            return None

    # ------- camera devices -------
    @staticmethod
    def list_v4l2_devices() -> list[str]:
        if IS_WINDOWS:
            # Returns dshow video device names; callers treat the string
            # as the camera identifier rather than a /dev path.
            return list(_query_dshow_devices()[0])
        results: list[str] = []
        for p in sorted(Path("/dev").glob("video*")):
            results.append(str(p))
        return results

    @staticmethod
    def list_camera_devices() -> list[tuple[str, str]]:
        """Return [(id, label)] across platforms."""
        if IS_WINDOWS:
            return [(n, n) for n in _query_dshow_devices()[0]]
        if IS_MACOS:
            return list(_query_avfoundation_devices()[0])
        return [(p, p) for p in SystemInfo.list_v4l2_devices()]

    # ------- audio sources -------
    @staticmethod
    def list_pulse_sources() -> list[tuple[str, str]]:
        """Return [(name, description)] pairs.

        On Linux: PulseAudio / Pipewire sources via pactl.
        On Windows: DirectShow audio capture devices via ffmpeg.
        Always includes a 'default' entry at index 0.
        """
        items: list[tuple[str, str]] = [("default", "System default")]
        if IS_WINDOWS:
            for n in _query_dshow_devices()[1]:
                items.append((n, n))
            return items
        if IS_MACOS:
            for dev_id, name in _query_avfoundation_devices()[1]:
                items.append((dev_id, f"[{dev_id}] {name}"))
            return items
        if shutil.which("pactl"):
            try:
                out = subprocess.check_output(
                    ["pactl", "list", "short", "sources"],
                    stderr=subprocess.DEVNULL, text=True, timeout=2,
                )
                for line in out.strip().splitlines():
                    cols = line.split("\t")
                    if len(cols) >= 2:
                        items.append((cols[1], cols[1]))
            except (OSError, subprocess.SubprocessError):
                pass
        return items
