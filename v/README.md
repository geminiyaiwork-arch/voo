# KO'ZGU — Distribution Builds (v1.9.10)

Ready-to-distribute installers for all three desktop platforms.

| Platform | File | How to install |
|----------|------|----------------|
| Linux  | `kozgu_1.9.10_all.deb`   | `bash install-linux.sh` |
| Windows | `KOZGU-1.9.10-setup.exe` | Double-click |
| macOS  | `KOZGU-1.9.10.dmg`        | Open → drag to Applications |

---

## Linux (Kali / Ubuntu / Debian)

Install (removes any previous version automatically):

```bash
cd v/
bash install-linux.sh
```

Uninstall:

```bash
bash uninstall-linux.sh
```

The installer auto-resolves every dependency (FFmpeg, GStreamer,
PyQt6, faster-whisper, etc.) via `apt` + `pip`.

---

## Windows

1. Send `KOZGU-1.9.10-setup.exe` to the user.
2. Double-click → **Yes** (UAC) → **Install** → **Finish**.
3. KO'ZGU opens automatically.

Bundled inside the installer:
- Python + every dependency
- FFmpeg + ffprobe
- Visual C++ 2015-2022 Redistributable (auto-installed if missing)

No internet required at install time. Uninstall via Settings → Apps.

---

## macOS (11 Big Sur+)

1. Send `KOZGU-1.9.10.dmg` to the user.
2. Double-click the .dmg.
3. Drag **KO'ZGU** into **Applications**.
4. Open from Launchpad.

On first launch macOS asks for **Screen Recording**, **Camera** and
**Microphone** permissions. For system audio capture install
[BlackHole](https://existential.audio/blackhole/).

Uninstall: drag KO'ZGU.app to Trash.

---

## Where the builds came from

- Linux .deb — built locally on Kali
- Windows .exe — GitHub Actions, windows-latest runner
- macOS .dmg — GitHub Actions, macos-latest runner

All three were produced from the same source commit, so feature parity
(live streaming, EN/RU→UZ dubbing, HTML overlay, donate) is identical.
