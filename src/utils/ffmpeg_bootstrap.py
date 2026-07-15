"""First-launch FFmpeg installer.

The installer no longer ships FFmpeg — that alone saved ~140 MB on
Windows and ~60 MB on macOS, which is what lets the KO'ZGU installer
fit under UCMS.UZ's upload limit.  Instead we download a static build
on first launch (or the first time the user opens Record) and cache
it under the platform-appropriate app-data directory.

On Linux we rely on the .deb dependency to install `ffmpeg` via apt.

Public API:
    ffmpeg_available() -> bool
    ensure_ffmpeg(progress_cb) -> Path | None
    ffmpeg_dir() -> Path
"""
from __future__ import annotations

import os
import shutil
import sys
import subprocess
import zipfile
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, Optional


IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
MAC_INTEL_URL = "https://evermeet.cx/ffmpeg/getrelease/zip"
MAC_ARM_URL = "https://www.osxexperts.net/ffmpeg7arm.zip"     # best-effort
MAC_PROBE_URL_INTEL = "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"


def _app_data_dir() -> Path:
    """Where we cache the downloaded ffmpeg binary."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
    elif IS_MACOS:
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") \
                or str(Path.home() / ".local" / "share")
    return Path(base) / "KOZGU"


def ffmpeg_dir() -> Path:
    return _app_data_dir() / "ffmpeg"


def _bundled_ffmpeg() -> Optional[Path]:
    """FFmpeg shipped inside the PyInstaller bundle (unused now)."""
    if not getattr(sys, "frozen", False):
        return None
    base = Path(getattr(sys, "_MEIPASS", "")) if hasattr(sys, "_MEIPASS") else None
    if base is None:
        return None
    exe = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"
    p = base / "ffmpeg" / exe
    return p if p.exists() else None


def ffmpeg_binary() -> Optional[Path]:
    """Return an executable FFmpeg path, searching in order:
        1. cached download under _app_data_dir/ffmpeg
        2. bundled inside PyInstaller (legacy)
        3. system PATH (apt/brew install)
    """
    exe = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"
    cached = ffmpeg_dir() / exe
    if cached.exists():
        return cached
    bundled = _bundled_ffmpeg()
    if bundled is not None:
        return bundled
    path_hit = shutil.which("ffmpeg")
    return Path(path_hit) if path_hit else None


def ffmpeg_available() -> bool:
    return ffmpeg_binary() is not None


def _download_with_progress(url: str, dest: Path,
                             cb: Optional[Callable[[float], None]] = None
                             ) -> None:
    """Stream a URL to dest with an optional 0.0..1.0 progress callback."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "KO'ZGU/1.8"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if cb and total:
                    try:
                        cb(min(1.0, got / total))
                    except Exception:                       # pylint: disable=broad-except
                        pass


def _install_windows(cb: Optional[Callable[[float], None]] = None) -> Optional[Path]:
    tmpdir = Path(tempfile.mkdtemp(prefix="kozgu-ffmpeg-"))
    zip_path = tmpdir / "ffmpeg.zip"
    try:
        _download_with_progress(WIN_URL, zip_path, cb)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)
        # gyan.dev structure: ffmpeg-N-essentials_build/bin/{ffmpeg,ffprobe}.exe
        dst = ffmpeg_dir()
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            for src in tmpdir.rglob(name):
                shutil.copy2(src, dst / name)
                break
        return dst / "ffmpeg.exe" if (dst / "ffmpeg.exe").exists() else None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _install_macos(cb: Optional[Callable[[float], None]] = None) -> Optional[Path]:
    tmpdir = Path(tempfile.mkdtemp(prefix="kozgu-ffmpeg-"))
    try:
        dst = ffmpeg_dir()
        dst.mkdir(parents=True, exist_ok=True)

        ff_zip = tmpdir / "ffmpeg.zip"
        fp_zip = tmpdir / "ffprobe.zip"
        _download_with_progress(MAC_INTEL_URL, ff_zip,
                                 lambda f: cb(f * 0.5) if cb else None)
        _download_with_progress(MAC_PROBE_URL_INTEL, fp_zip,
                                 lambda f: cb(0.5 + f * 0.5) if cb else None)
        for z in (ff_zip, fp_zip):
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmpdir)
        for name in ("ffmpeg", "ffprobe"):
            for src in tmpdir.rglob(name):
                if src.is_file():
                    shutil.copy2(src, dst / name)
                    os.chmod(dst / name, 0o755)
                    break
        return dst / "ffmpeg" if (dst / "ffmpeg").exists() else None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _install_linux() -> Optional[Path]:
    """Ask the user to run: sudo apt install ffmpeg.  We don't
    auto-elevate on Linux — the .deb dep should have handled it."""
    return None


def ensure_ffmpeg(progress_cb: Optional[Callable[[float], None]] = None
                  ) -> Optional[Path]:
    """Install FFmpeg if missing.  Returns its path or None on failure."""
    existing = ffmpeg_binary()
    if existing is not None:
        return existing
    try:
        if IS_WINDOWS:
            return _install_windows(progress_cb)
        if IS_MACOS:
            return _install_macos(progress_cb)
        return _install_linux()
    except Exception:                                       # pylint: disable=broad-except
        return None
