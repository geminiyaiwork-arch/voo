#!/usr/bin/env bash
# KO'ZGU — Linux installer (uninstall old + install new in one shot)
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEB_FILE=$(ls -1 "$SCRIPT_DIR"/kozgu_*.deb 2>/dev/null | tail -1)

if [ -z "$DEB_FILE" ]; then
    echo "✗ kozgu_*.deb not found in $SCRIPT_DIR"
    exit 1
fi

echo "════════════════════════════════════════════════════════"
echo "  KO'ZGU Linux installer"
echo "════════════════════════════════════════════════════════"
echo "Found .deb: $DEB_FILE"
echo

# --- step 1: remove EVERY old version (voo-recorder, visio-eye, kozgu) ---
echo "[1/3] Removing old versions..."
sudo apt remove --purge -y voo-recorder visio-eye kozgu 2>/dev/null || true
sudo rm -rf /opt/voo-recorder /opt/visio-eye /opt/kozgu
sudo rm -f /usr/local/bin/voo-recorder /usr/local/bin/visio-eye /usr/local/bin/kozgu
sudo rm -f /usr/share/applications/voo-recorder.desktop \
           /usr/share/applications/visio-eye.desktop \
           /usr/share/applications/kozgu.desktop
sudo rm -f /usr/share/icons/hicolor/256x256/apps/voo-recorder.png \
           /usr/share/icons/hicolor/256x256/apps/visio-eye.png \
           /usr/share/icons/hicolor/256x256/apps/kozgu.png
rm -rf "$HOME/.config/voo-recorder" \
       "$HOME/.config/visio-eye" \
       "$HOME/.config/kozgu"
echo "  ✓ old versions removed"

# --- step 2: install new version ---
echo
echo "[2/3] Installing new version (may auto-install dependencies)..."
sudo apt install -y "$DEB_FILE"

# --- step 3: launch ---
echo
echo "[3/3] All done."
echo
echo "════════════════════════════════════════════════════════"
echo "  ✓ KO'ZGU is installed."
echo "  Launch: kozgu   (or Applications menu)"
echo "════════════════════════════════════════════════════════"
