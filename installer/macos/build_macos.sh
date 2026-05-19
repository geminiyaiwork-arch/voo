#!/usr/bin/env bash
# ============================================================
#  Visio Eye — macOS installer build orchestrator
#
#  Requirements on the build machine:
#    * macOS 11+ (Big Sur or later)
#    * Python 3.11+        (brew install python@3.11)
#    * create-dmg          (brew install create-dmg)
#
#  Run from the project root:
#      installer/macos/build_macos.sh
#
#  Output:
#      dist/VisioEye-1.7.0.dmg          ← drag-and-drop installer
#      dist/Visio Eye.app/              ← raw .app bundle
# ============================================================
set -euo pipefail

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
export VISIO_EYE_PROJECT_DIR="$PROJECT_DIR"
cd "$PROJECT_DIR"

VERSION="1.7.0"

echo "=== [1/5] Sanity check ============================================"
python3 --version
command -v pyinstaller >/dev/null || python3 -m pip install --upgrade pyinstaller

echo
echo "=== [2/5] Install Python requirements ==========================="
python3 -m pip install --upgrade -r requirements.txt

echo
echo "=== [3/5] Bundle FFmpeg + ffprobe ================================"
mkdir -p installer/macos/ffmpeg
if [ ! -x installer/macos/ffmpeg/ffmpeg ]; then
    echo "Downloading FFmpeg static build from evermeet.cx..."
    curl -fsSL -o installer/macos/ffmpeg/ffmpeg.zip \
        https://evermeet.cx/ffmpeg/getrelease/zip
    (cd installer/macos/ffmpeg && unzip -o ffmpeg.zip && rm ffmpeg.zip)
fi
if [ ! -x installer/macos/ffmpeg/ffprobe ]; then
    curl -fsSL -o installer/macos/ffmpeg/ffprobe.zip \
        https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip
    (cd installer/macos/ffmpeg && unzip -o ffprobe.zip && rm ffprobe.zip)
fi
chmod +x installer/macos/ffmpeg/ffmpeg installer/macos/ffmpeg/ffprobe

echo
echo "=== [4/5] Run PyInstaller ========================================"
rm -rf build "dist/Visio Eye.app"
python3 -m PyInstaller installer/macos/visio-eye.spec --noconfirm

echo
echo "=== [5/5] Build .dmg ============================================="
if ! command -v create-dmg >/dev/null; then
    echo "create-dmg missing; installing via Homebrew..."
    brew install create-dmg
fi
rm -f "dist/VisioEye-${VERSION}.dmg"
create-dmg \
    --volname "Visio Eye ${VERSION}" \
    --volicon "assets/img/logo.png" \
    --window-pos 200 120 \
    --window-size 600 380 \
    --icon-size 96 \
    --icon "Visio Eye.app" 150 180 \
    --hide-extension "Visio Eye.app" \
    --app-drop-link 450 180 \
    "dist/VisioEye-${VERSION}.dmg" \
    "dist/Visio Eye.app" \
    || hdiutil create -volname "Visio Eye ${VERSION}" \
                       -srcfolder "dist/Visio Eye.app" \
                       -ov -format UDZO \
                       "dist/VisioEye-${VERSION}.dmg"

echo
echo "============================================================"
echo "  Build complete."
echo "    Installer:  dist/VisioEye-${VERSION}.dmg"
echo "    App bundle: dist/Visio Eye.app/"
echo "============================================================"
