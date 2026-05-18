# Visio Eye — Windows Build Instructions

This directory contains everything you need to produce a Windows
installer (`VisioEye-1.4.0-setup.exe`) and a portable folder
(`dist\visio-eye\visio-eye.exe`).

The codebase itself is fully cross-platform. The Linux `.deb` continues
to work; this folder only adds the Windows packaging.

---

## What you build

| Artifact                                | Path                                    |
| --------------------------------------- | --------------------------------------- |
| Single-file installer (recommended)     | `dist\VisioEye-1.4.0-setup.exe`      |
| Portable folder (no install)            | `dist\visio-eye\visio-eye.exe`    |

The installer is **fully self-contained**:
- Installs to `C:\Program Files\Visio Eye\`
- Creates Start Menu shortcut + optional desktop icon (with `logo.ico`)
- Adds bundled `ffmpeg\` to `PATH`
- Auto-installs Visual C++ 2015-2022 Redistributable if missing
- Registers a clean uninstaller in **Apps & Features**

End users need **no Python, no pip, no FFmpeg, no GStreamer** —
everything is bundled inside `visio-eye.exe` thanks to PyInstaller.

---

## Prerequisites (build machine, one-time setup)

1. **Windows 10 or 11**, x64
2. **Python 3.11+** from <https://python.org> — tick "Add to PATH" during install
3. **Inno Setup 6** from <https://jrsoftware.org/isdl.php>
   - During install, add `iscc.exe` to PATH (or use Inno IDE manually)
4. **FFmpeg** — `build_windows.bat` downloads it automatically from
   <https://www.gyan.dev/ffmpeg/builds/> on first build, so you don't
   need to do anything.  (You CAN drop your own `ffmpeg.exe` +
   `ffprobe.exe` into `installer\windows\ffmpeg\` to override the
   auto-download.)
5. **Visual C++ 2015-2022 Redistributable** — the installer downloads
   and installs this on demand on end-user machines that don't
   already have it (silently, ~25 MB).

---

## Build

Open **Command Prompt** in the project root, then:

```cmd
installer\windows\build_windows.bat
```

The script:
1. Installs PyInstaller + project requirements
2. Refreshes `logo.ico` from `logo.png`
3. Runs PyInstaller using `visio-eye.spec`
4. Calls Inno Setup compiler (`iscc`) to produce the final installer

**Time**: 2–5 minutes on a typical machine.

---

## Manual build (without the .bat)

If something goes wrong, run the steps individually:

```cmd
pip install --upgrade pip pyinstaller
pip install -r requirements.txt

set VISIO_EYE_PROJECT_DIR=%CD%
pyinstaller installer\windows\visio-eye.spec --noconfirm

iscc installer\windows\visio-eye.iss
```

---

## Running the portable build

After PyInstaller finishes you can launch the app without installing:

```cmd
dist\visio-eye\visio-eye.exe
```

This is useful for testing before signing/distributing the installer.

---

## What changed for Windows

| Concern              | Linux                          | Windows                        |
| -------------------- | ------------------------------ | ------------------------------ |
| Screen capture       | `-f x11grab` (or Wayland portal) | `-f gdigrab -i desktop`     |
| Microphone           | `-f pulse -i <source>`         | `-f dshow -i audio="..."`      |
| System audio         | PulseAudio monitor source       | DirectShow capture device      |
| Webcam               | `-f v4l2 -i /dev/videoN`       | `-f dshow -i video="..."`      |
| Pause/Resume         | `SIGSTOP` / `SIGCONT`          | `SuspendThread` / `ResumeThread` |
| Stop                 | `q` then `SIGINT`              | `q` then `CTRL_BREAK_EVENT`    |
| GPU encoders         | `nvenc`, `vaapi`               | `nvenc`, `qsv`, `amf`          |
| Settings folder      | `~/.config/visio-eye/`      | `%APPDATA%\VisioEye\`       |
| Default output       | `~/Videos/VisioEye/`        | `%USERPROFILE%\Videos\VisioEye\` |

---

## System audio capture on Windows

DirectShow does **not** natively expose loopback for system audio.
There are three common solutions:

1. **Enable "Stereo Mix"** in `mmsys.cpl` → Recording → right-click → Show
   disabled devices → enable Stereo Mix.
   Then in Visio Eye: Settings → Audio → Desktop Audio = "Stereo Mix".
2. **Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)** and
   pick `CABLE Output` as the Desktop Audio device.
3. **Install OBS Virtual Audio** (comes with OBS Studio if installed).

Visio Eye's enumeration shows whatever DirectShow capture devices the
OS exposes, so these solutions work out of the box.

---

## Common issues

**`PyInstaller: ModuleNotFoundError: No module named 'PyQt6'`**
Run `pip install -r requirements.txt` first.

**`iscc is not recognized as an internal or external command`**
Inno Setup is installed but its bin folder isn't on PATH. Either add
`C:\Program Files (x86)\Inno Setup 6` to PATH, or open
`visio-eye.iss` in the Inno Setup IDE and click "Compile".

**`FFmpeg not found` after install**
Either the bundled `ffmpeg` folder wasn't included (check that
`installer\windows\ffmpeg\ffmpeg.exe` existed at build time), or
PATH wasn't picked up — open a new Command Prompt after install.

**Recording produces a black screen**
GDI cannot capture protected content (Netflix, some games with anti-cheat).
Switch to `ddagrab` by editing `ffmpeg_handler.py` or accept the limitation.

---

## Producing both 32-bit and 64-bit installers

The `.iss` script now accepts **x64 and x86** Windows targets, but the
.exe bitness produced by PyInstaller matches whatever Python you ran
it from. To ship both, install **two** Python interpreters side by
side (e.g. Python 3.11 64-bit and Python 3.11 32-bit) and run
`build_windows.bat` once with each. Rename the outputs to e.g.

- `VisioEye-1.4.0-setup-x64.exe`
- `VisioEye-1.4.0-setup-x86.exe`

64-bit is strongly recommended whenever possible — the bundled
`faster-whisper` ASR routinely uses 1.5–3 GB of address space during
inference and may exceed the 4 GB ceiling of 32-bit processes when
loading the `large-v3` model. On 32-bit builds, prefer `medium` or
smaller Whisper models in Settings → Dubbing.

---

## Live dubbing on Windows (EN/RU → UZ)

Visio Eye ships a real-time dubbing engine. On Windows it needs two
pieces in addition to FFmpeg:

1. **WASAPI loopback** — built into Windows Vista+, no install needed.
   `sounddevice` (auto-installed) captures the speaker output and
   feeds it to Whisper.
2. **VB-Audio Virtual Cable** —
   <https://vb-audio.com/Cable/> (free).
   After install, reboot, then in Visio Eye:
   - Open Settings → **Dubbing** → tick *Enable live dubbing*.
   - The router automatically picks `CABLE Input` as the dub output
     and `CABLE Output` as the recorder input, so the finished `.mp4`
     contains **only the Uzbek voice**.
   - Listen through your normal speakers (the recorder's `CABLE Output`
     does not block your default playback device).

If you skip VB-Cable, the app still runs — the dubbing tab will show
*"No virtual audio cable detected"* and recording continues without
dubbing. The Linux path uses PulseAudio's `module-null-sink` so no
extra software is required.

GPU acceleration (CUDA) is recommended for the `large-v3` Whisper
model. On systems without an NVIDIA GPU, change Settings → Dubbing →
Device to **CPU** and pick **medium** or **small** as the model.

---

## Sign the installer (optional, for distribution)

To avoid SmartScreen warnings, sign `VisioEye-1.4.0-setup.exe`:

```cmd
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a ^
    dist\VisioEye-1.4.0-setup.exe
```

(Requires a code-signing certificate. Without it, users will see a
"Windows protected your PC" prompt on first install — they can click
"More info" → "Run anyway".)
