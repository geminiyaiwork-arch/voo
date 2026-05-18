#!/usr/bin/env bash
# Visio Eye - Linux installer
# Installs the app to /opt/visio-eye and registers desktop entry.
set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
INSTALL_DIR="/opt/visio-eye"
BIN_LINK="/usr/local/bin/visio-eye"
DESKTOP_FILE="/usr/share/applications/visio-eye.desktop"
ICON_TARGET="/usr/share/icons/hicolor/256x256/apps/visio-eye.png"

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

log()  { printf "${GREEN}[+]${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${RESET} %s\n" "$*"; }
err()  { printf "${RED}[x]${RESET} %s\n" "$*" >&2; }

require_root() {
    if [ "$EUID" -ne 0 ]; then
        err "Please run as root:   sudo bash $0"
        exit 1
    fi
}

install_system_deps() {
    log "Installing system packages (ffmpeg, python3, v4l-utils, ...)"
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y --no-install-recommends \
            python3 python3-pip python3-venv \
            python3-dbus python3-gi gir1.2-glib-2.0 \
            ffmpeg v4l-utils xdotool scrot \
            gstreamer1.0-tools gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
            gstreamer1.0-plugins-ugly gstreamer1.0-libav \
            gstreamer1.0-pipewire gstreamer1.0-pulseaudio \
            libgl1 libxcb-cursor0 libxkbcommon-x11-0 \
            libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
            libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
            libxcb-sync1 libxcb-xfixes0 libxcb-xinerama0 \
            libdbus-1-3 libpulse0
    else
        warn "Non-apt distro detected. Install ffmpeg, python3-pip manually."
    fi
}

install_python_deps() {
    log "Installing Python dependencies"
    pip3 install --break-system-packages -r "$PROJECT_DIR/requirements.txt" \
        || pip3 install -r "$PROJECT_DIR/requirements.txt"
}

copy_files() {
    log "Copying application files to ${INSTALL_DIR}"
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cp -r "$PROJECT_DIR/src" "$INSTALL_DIR/"
    cp -r "$PROJECT_DIR/assets" "$INSTALL_DIR/"
    cp "$PROJECT_DIR/visio-eye" "$INSTALL_DIR/visio-eye"
    cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/visio-eye"
}

register_desktop() {
    log "Registering launcher and icon"
    install -Dm755 "$PROJECT_DIR/visio-eye" "$INSTALL_DIR/visio-eye"
    install -Dm644 "$PROJECT_DIR/installer/visio-eye.desktop" "$DESKTOP_FILE"

    if [ -f "$PROJECT_DIR/assets/img/logo.png" ]; then
        install -Dm644 "$PROJECT_DIR/assets/img/logo.png" "$ICON_TARGET"
    elif [ -f "$PROJECT_DIR/assets/img/author.png" ]; then
        install -Dm644 "$PROJECT_DIR/assets/img/author.png" "$ICON_TARGET"
    fi

    ln -sf "$INSTALL_DIR/visio-eye" "$BIN_LINK"

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q /usr/share/icons/hicolor || true
    fi
}

main() {
    require_root
    install_system_deps
    install_python_deps
    copy_files
    register_desktop
    log "Installation complete."
    log "Launch with:   visio-eye"
    log "Or find 'Visio Eye' in your application menu."
}

main "$@"
