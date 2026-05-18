#!/usr/bin/env bash
# Remove Visio Eye from this system.
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:   sudo bash $0"
    exit 1
fi

rm -rf /opt/visio-eye /opt/voo-recorder
rm -f /usr/local/bin/visio-eye /usr/local/bin/voo-recorder
rm -f /usr/share/applications/visio-eye.desktop /usr/share/applications/voo-recorder.desktop
rm -f /usr/share/icons/hicolor/256x256/apps/visio-eye.png
rm -f /usr/share/icons/hicolor/256x256/apps/voo-recorder.png

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

echo "Visio Eye removed."
echo "User settings remain in ~/.config/visio-eye/"
