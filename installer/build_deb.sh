#!/usr/bin/env bash
# Build a .deb package for Visio Eye.
# Output: dist/visio-eye_<VERSION>_all.deb
set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
VERSION="1.7.0"
PKG_NAME="visio-eye_${VERSION}_all"
STAGING="$PROJECT_DIR/build/$PKG_NAME"
DIST_DIR="$PROJECT_DIR/dist"

rm -rf "$STAGING"
mkdir -p "$STAGING/DEBIAN"
mkdir -p "$STAGING/opt/visio-eye"
mkdir -p "$STAGING/usr/local/bin"
mkdir -p "$STAGING/usr/share/applications"
mkdir -p "$STAGING/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$DIST_DIR"

# ---- payload ----
cp -r "$PROJECT_DIR/src"      "$STAGING/opt/visio-eye/"
cp -r "$PROJECT_DIR/assets"   "$STAGING/opt/visio-eye/"
cp    "$PROJECT_DIR/visio-eye"     "$STAGING/opt/visio-eye/visio-eye"
cp    "$PROJECT_DIR/requirements.txt" "$STAGING/opt/visio-eye/"
chmod +x "$STAGING/opt/visio-eye/visio-eye"

ln -sf /opt/visio-eye/visio-eye "$STAGING/usr/local/bin/visio-eye"

cp "$PROJECT_DIR/installer/visio-eye.desktop" \
   "$STAGING/usr/share/applications/visio-eye.desktop"

ICON_SRC=""
if [ -f "$PROJECT_DIR/assets/img/logo.png" ]; then
    ICON_SRC="$PROJECT_DIR/assets/img/logo.png"
elif [ -f "$PROJECT_DIR/assets/img/author.png" ]; then
    ICON_SRC="$PROJECT_DIR/assets/img/author.png"
fi
if [ -n "$ICON_SRC" ]; then
    cp "$ICON_SRC" \
       "$STAGING/usr/share/icons/hicolor/256x256/apps/visio-eye.png"
fi

# ---- control ----
cat > "$STAGING/DEBIAN/control" <<EOF
Package: visio-eye
Version: ${VERSION}
Section: video
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip, python3-dbus, python3-gi, gir1.2-glib-2.0, python3-pyqt6.qtwebengine, ffmpeg, v4l-utils, xdotool, scrot, gstreamer1.0-tools, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good, gstreamer1.0-plugins-bad, gstreamer1.0-plugins-ugly, gstreamer1.0-libav, gstreamer1.0-pipewire, gstreamer1.0-pulseaudio, libxcb-cursor0
Recommends: pulseaudio-utils, libxcb-xinerama0, pipewire
Conflicts: voo-recorder
Replaces: voo-recorder
Maintainer: Elyorbek <elyorbek-13@mail.ru>
Description: Visio Eye - all-in-one recorder + dubbing + streaming
 Records the screen with system + microphone audio, webcam overlay,
 logo overlay, fully custom HTML/CSS/JS overlay rendered through
 Chromium WebEngine, multi-resolution output up to 4K and FFmpeg-powered
 MP4/MKV/MOV output.  Built-in real-time EN/RU->UZ dubbing pipeline
 (Whisper ASR + Yandex/Google translate + Microsoft Edge TTS).  Live
 streaming to YouTube, Facebook, Twitch, Telegram and custom RTMP/RTMPS
 ingest, all simultaneously while recording locally.
EOF

cat > "$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/bash
# Visio Eye postinst — make sure every runtime tool the recording
# and streaming pipelines need is actually installed.  We do NOT
# rely solely on Depends because users sometimes install with
# `dpkg -i` which skips dep resolution.
set -e

log() { printf "[visio-eye/postinst] %s\n" "$*"; }

# ---- 1. APT dependencies (only if missing) ------------------------
APT_REQ=(
    ffmpeg
    v4l-utils
    xdotool
    scrot
    gstreamer1.0-tools
    gstreamer1.0-plugins-base
    gstreamer1.0-plugins-good
    gstreamer1.0-plugins-bad
    gstreamer1.0-plugins-ugly
    gstreamer1.0-libav
    gstreamer1.0-pipewire
    gstreamer1.0-pulseaudio
    gstreamer1.0-vaapi
    pulseaudio-utils
    python3-dbus
    python3-gi
    gir1.2-glib-2.0
    libxcb-cursor0
    intel-media-va-driver
    libva2
    libva-drm2
    vainfo
)
MISSING=()
for pkg in "${APT_REQ[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING+=("$pkg")
    fi
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    log "Installing missing system packages: ${MISSING[*]}"
    if command -v apt-get >/dev/null 2>&1; then
        DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1 || true
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            --no-install-recommends "${MISSING[@]}" || \
        log "WARNING: apt-get could not install all packages — install manually: sudo apt install ${MISSING[*]}"
    else
        log "WARNING: apt-get not found — install these packages manually: ${MISSING[*]}"
    fi
fi

# ---- 2. WebEngine for the HTML overlay (optional) -----------------
if ! dpkg -s python3-pyqt6.qtwebengine >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends python3-pyqt6.qtwebengine >/dev/null 2>&1 \
        || log "WebEngine not installed — HTML overlay will fall back to QTextEdit"
fi

# ---- 3. Python pip packages ---------------------------------------
PIP_PKGS="PyQt6 opencv-python numpy pynput psutil Pillow faster-whisper edge-tts deep-translator httpx"
log "Installing Python packages (may take a few minutes for faster-whisper)..."
pip3 install --break-system-packages $PIP_PKGS >/dev/null 2>&1 \
 || pip3 install $PIP_PKGS >/dev/null 2>&1 \
 || log "WARNING: pip install partially failed — run manually if needed: pip3 install --break-system-packages $PIP_PKGS"

# ---- 4. Desktop integration ---------------------------------------
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

# ---- 5. Quick health summary --------------------------------------
log "Visio Eye installed.  Tooling check:"
for t in ffmpeg gst-launch-1.0 parec paplay pactl; do
    if command -v "$t" >/dev/null 2>&1; then
        log "  ✓ $t"
    else
        log "  ✗ $t  (NOT FOUND — some features may not work)"
    fi
done

exit 0
EOF
chmod 755 "$STAGING/DEBIAN/postinst"

cat > "$STAGING/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
exit 0
EOF
chmod 755 "$STAGING/DEBIAN/prerm"

# ---- build ----
if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "dpkg-deb is missing — install with: sudo apt install dpkg-dev"
    exit 1
fi

dpkg-deb --build --root-owner-group "$STAGING" "$DIST_DIR/${PKG_NAME}.deb"

echo
echo "✔ Built: $DIST_DIR/${PKG_NAME}.deb"
echo "Install with:   sudo apt install $DIST_DIR/${PKG_NAME}.deb"
