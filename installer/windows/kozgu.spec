# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for KO'ZGU (Windows).
#
# Run from the project root on Windows:
#     pyinstaller installer\windows\kozgu.spec --noconfirm
#
# Output: dist\kozgu\kozgu.exe plus its bundled runtime.
# The Inno Setup script (kozgu.iss) packages that folder into an
# installer .exe.

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("KOZGU_PROJECT_DIR", os.getcwd())).resolve()
ASSETS = PROJECT_DIR / "assets"
SRC = PROJECT_DIR / "src"

block_cipher = None

datas = [
    (str(ASSETS / "img" / "logo.png"),   "assets/img"),
    (str(ASSETS / "img" / "author.png"), "assets/img"),
    (str(ASSETS / "img" / "logo.ico"),   "assets/img"),
    (str(ASSETS / "icons" / "check_white.svg"), "assets/icons"),
    (str(ASSETS / "icons" / "usdt.svg"),        "assets/icons"),
    (str(ASSETS / "icons" / "btc.svg"),         "assets/icons"),
]
# FFmpeg is intentionally NOT bundled — it adds ~140 MB and the app
# now auto-downloads a static build on first launch via ffmpeg_bootstrap.
# This keeps the installer under the UCMS upload limit.

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
        # --- dubbing module (live EN/RU -> UZ) ---
        "dubbing", "dubbing.pipeline", "dubbing.asr_whisper",
        "dubbing.translator", "dubbing.tts_edge",
        "dubbing.audio_capture", "dubbing.audio_router",
        "faster_whisper", "ctranslate2",
        "edge_tts", "edge_tts.communicate",
        "deep_translator", "deep_translator.google",
        "httpx", "httpcore",
        "sounddevice", "soundfile", "_sounddevice_data",
        "tokenizers", "huggingface_hub",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "dbus", "gi", "Xlib",          # Linux-only modules — not present on Windows
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
    icon=str(ASSETS / "img" / "logo.ico"),
    version=None,
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
