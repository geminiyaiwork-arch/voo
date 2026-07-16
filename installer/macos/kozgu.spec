# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for KO'ZGU on macOS.
#
# Run from the project root on a macOS build machine:
#     pyinstaller installer/macos/kozgu.spec --noconfirm
#
# Output: dist/KO'ZGU.app   (a fully-wrapped .app bundle)
# A separate shell script (build_macos.sh) turns the .app into a .dmg.

import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("KOZGU_PROJECT_DIR", os.getcwd())).resolve()
ASSETS = PROJECT_DIR / "assets"
SRC = PROJECT_DIR / "src"

block_cipher = None

datas = [
    (str(ASSETS / "img" / "logo.png"),   "assets/img"),
    (str(ASSETS / "img" / "author.png"), "assets/img"),
    (str(ASSETS / "icons" / "check_white.svg"), "assets/icons"),
    (str(ASSETS / "icons" / "usdt.svg"),        "assets/icons"),
    (str(ASSETS / "icons" / "btc.svg"),         "assets/icons"),
]
# Bundle FFmpeg + ffprobe fetched by build_macos.sh / GitHub Actions
# from evermeet.cx.  This ships the .dmg fully self-contained so the
# user doesn't need internet on first launch.  If bundling failed at
# build time, ffmpeg_bootstrap downloads it lazily instead.
ffmpeg_dir = PROJECT_DIR / "installer" / "macos" / "ffmpeg"
if (ffmpeg_dir / "ffmpeg").exists():
    datas.append((str(ffmpeg_dir / "ffmpeg"), "ffmpeg"))
    if (ffmpeg_dir / "ffprobe").exists():
        datas.append((str(ffmpeg_dir / "ffprobe"), "ffmpeg"))

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "cv2", "numpy", "PIL", "PIL.Image",
        "pynput", "pynput.keyboard", "pynput.mouse",
        "psutil",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Linux-only modules — not present on macOS
        "dbus", "gi", "Xlib",
        # tkinter is huge and we don't use it
        "tkinter",
    ],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="kozgu",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ASSETS / "img" / "logo.png"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="kozgu",
)

# Wrap the COLLECT into a proper .app bundle so macOS treats it as an
# application (Launchpad icon, Dock entry, Info.plist permissions).
app = BUNDLE(
    coll,
    name="KO'ZGU.app",
    icon=str(ASSETS / "img" / "logo.png"),
    bundle_identifier="uz.kozgu.app",
    version="1.9.2",
    info_plist={
        "CFBundleName": "KO'ZGU",
        "CFBundleDisplayName": "KO'ZGU",
        "CFBundleShortVersionString": "1.9.2",
        "CFBundleVersion": "1.9.2",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        # Permissions prompts that macOS shows on first launch:
        "NSCameraUsageDescription":
            "KO'ZGU uses the camera for the webcam overlay.",
        "NSMicrophoneUsageDescription":
            "KO'ZGU uses the microphone for narration.",
        "NSScreenCaptureUsageDescription":
            "KO'ZGU records the screen for video capture and streaming.",
    },
)
