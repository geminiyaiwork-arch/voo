# Visio Eye

Professional screen + audio recorder for Linux (Kali / Ubuntu / Debian).
Python 3 + PyQt6 UI, FFmpeg recording engine.

![status](https://img.shields.io/badge/platform-linux-blue)
![python](https://img.shields.io/badge/python-3.10%2B-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Features

- Screen recording — full screen, selected area, or active window
- System audio + microphone (PulseAudio / Pipewire), independent volume sliders
- Camera overlay — drag, resize, rounded corners, opacity, custom position
- Logo overlay — PNG / SVG / JPG, drag, resize, opacity
- Resolutions: 480p · 720p · 1080p · 2K · 4K
- FPS: 24 / 30 / 60
- Codec: H.264 / H.265 with CPU **or** GPU encoding (NVENC / VAAPI auto-detect)
- Output: MP4 / MKV / MOV
- Audio quality: 128 / 192 / 256 / 320 kbps + noise suppression + echo cancellation
- Customizable save folder + filename template
- Global hotkeys (Start / Pause / Resume / Stop / Screenshot)
- Realtime CPU / GPU / RAM / disk-free monitor + recording timer
- Author modal with developer contact card

---

## Project layout

```
lunx/
├── src/
│   ├── main.py                  # entry point
│   ├── recorder/                # FFmpeg engine, screenshot helper
│   ├── overlays/                # camera + logo transparent windows
│   ├── settings/                # JSON-backed settings manager
│   ├── ui/                      # PyQt6 windows + styles
│   └── utils/                   # hotkeys, system metrics
├── assets/
│   └── img/author.png           # author photo
├── installer/
│   ├── install.sh               # system install to /opt
│   ├── uninstall.sh
│   ├── build_deb.sh             # builds a .deb package
│   └── visio-eye.desktop
├── visio-eye                 # launcher script
├── requirements.txt
└── README.md
```

---

## Quick start (development)

```bash
# 1. install system deps (Kali / Debian / Ubuntu)
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg v4l-utils xdotool scrot \
    libxcb-cursor0 pulseaudio-utils

# 2. install python deps
pip3 install --break-system-packages -r requirements.txt

# 3. run
./visio-eye
```

---

## System install

```bash
sudo bash installer/install.sh
```

This copies the project to `/opt/visio-eye`, creates the desktop entry,
installs Python dependencies and creates a symlink at
`/usr/local/bin/visio-eye`.

Uninstall:

```bash
sudo bash installer/uninstall.sh
```

---

## Build the .deb package

```bash
bash installer/build_deb.sh
sudo apt install dist/visio-eye_1.3.0_all.deb
```

The package depends on `ffmpeg`, `v4l-utils`, `xdotool`, `scrot`,
`python3-pip` and pulls Python deps via the `postinst` hook.

---

## Usage

1. Launch **Visio Eye** from the application menu (or run
   `visio-eye`).
2. Choose **mode** — full screen, selected area, or active window.
3. Pick **quality**, **FPS** and **audio source**.
4. Toggle **Camera** / **Logo** overlays as needed and drag them to position.
5. Press **● Record** (or `F9`).
6. Press **■ Stop** (or `F11`). MP4 is saved to `~/Videos/VisioEye/` by
   default.

Open **Settings → AUTOR** to see developer contact info.

### Default hotkeys

| Action      | Key |
|-------------|-----|
| Start       | F9  |
| Pause/Resume| F10 |
| Stop        | F11 |
| Screenshot  | F12 |

Hotkeys are editable in **Settings → Hotkeys**.

---

## Notes

- **Wayland** has limited screen-capture and hotkey support — best results on
  X11. The app sets `QT_QPA_PLATFORM=xcb` automatically.
- GPU encoding works automatically when `h264_nvenc` / `hevc_nvenc` / VAAPI
  encoders are available in your FFmpeg build.
- Settings live at `~/.config/visio-eye/settings.json`.
- Recordings default to `~/Videos/VisioEye/record_YYYY_MM_DD_HH_MM_SS.mp4`.

---

## Author

**Elyorbek**
TEL 1: +998 (91) 169-37-66
TEL 2: +998 (99) 433-37-66
Telegram: @voo_uz
Email: elyorbek-13@mail.ru
