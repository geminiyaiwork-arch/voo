#!/usr/bin/env bash
# ============================================================
#  KO'ZGU — macOS installer build orchestrator
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
#      dist/KOZGU-1.8.0.dmg          ← drag-and-drop installer
#      dist/KO'ZGU.app/              ← raw .app bundle
# ============================================================
set -euo pipefail

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
export KOZGU_PROJECT_DIR="$PROJECT_DIR"
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
rm -rf build "dist/KO'ZGU.app"
python3 -m PyInstaller installer/macos/kozgu.spec --noconfirm

echo
echo "=== [5/5] Build .dmg ============================================="
if ! command -v create-dmg >/dev/null; then
    echo "create-dmg missing; installing via Homebrew..."
    brew install create-dmg
fi
rm -f "dist/KOZGU-${VERSION}.dmg"
create-dmg \
    --volname "KO'ZGU ${VERSION}" \
    --volicon "assets/img/logo.png" \
    --window-pos 200 120 \
    --window-size 600 380 \
    --icon-size 96 \
    --icon "KO'ZGU.app" 150 180 \
    --hide-extension "KO'ZGU.app" \
    --app-drop-link 450 180 \
    "dist/KOZGU-${VERSION}.dmg" \
    "dist/KO'ZGU.app" \
    || hdiutil create -volname "KO'ZGU ${VERSION}" \
                       -srcfolder "dist/KO'ZGU.app" \
                       -ov -format UDZO \
                       "dist/KOZGU-${VERSION}.dmg"

echo
echo "============================================================"
echo "  Build complete."
echo "    Installer:  dist/KOZGU-${VERSION}.dmg"
echo "    App bundle: dist/KO'ZGU.app/"
echo "============================================================"
