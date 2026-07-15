#!/usr/bin/env bash
# KO'ZGU — Linux uninstaller (removes every legacy name too)
set -e

echo "Removing KO'ZGU (and any older Visio Eye / VOO Recorder)…"
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
echo "✓ KO'ZGU removed."
echo "  Recorded videos in ~/Videos/KOZGU/ were not touched."
