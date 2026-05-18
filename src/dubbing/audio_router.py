"""Cross-platform audio routing for the dubbing pipeline.

Linux: creates a PulseAudio null-sink ``visio-eye-dub``. TTS bytes go
into the sink via ``paplay``; the recorder captures from the
``visio-eye-dub.monitor`` source. The output .mp4 contains only the
Uzbek dubbing track.

Windows: uses a DirectShow capture device chosen by the user as the
"dub sink". The recommended setup is **VB-Audio Virtual Cable**
(<https://vb-audio.com/Cable/>): play TTS to ``CABLE Input``, the
recorder captures from ``CABLE Output``. With OBS Virtual Audio the
same pattern applies. We resolve the target output device by matching
sounddevice's device list against ``DubbingConfig.windows_output_device``.

If no virtual cable is available on Windows, ``available()`` reports
the missing prerequisite so the UI can show a friendly hint.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)


IS_WINDOWS = sys.platform.startswith("win")

SINK_NAME = "visio-eye-dub"
SINK_DESC = "Visio_Eye_Dub_Mix"
MONITOR_SOURCE = f"{SINK_NAME}.monitor"

# Windows: substring match for known virtual-cable output devices,
# in priority order. Whichever name matches first wins.
WINDOWS_CABLE_HINTS = (
    "cable input",
    "cable-a input",
    "cable-b input",
    "obs virtual",
    "voicemeeter",
    "vac",                       # Virtual Audio Cable
)


class AudioRouter:
    """Creates the dub sink + plays TTS bytes into it."""

    def __init__(self, windows_output_device: Optional[str] = None) -> None:
        self._module_id: int | None = None
        self._win_device_index: int | None = None
        self._win_device_name: str | None = None
        self._win_device_pref = windows_output_device

    # ------- availability -------
    @staticmethod
    def available() -> tuple[bool, str]:
        if IS_WINDOWS:
            try:
                import sounddevice as _sd                   # noqa: F401
            except ImportError:
                return False, ("sounddevice not installed "
                               "(pip install sounddevice)")
            if not shutil.which("ffmpeg"):
                return False, "ffmpeg not on PATH (needed for MP3 decode)"
            return True, ""
        if not shutil.which("pactl"):
            return False, "pactl not installed (apt install pulseaudio-utils)"
        if not shutil.which("paplay"):
            return False, "paplay not installed (apt install pulseaudio-utils)"
        return True, ""

    # ------- lifecycle -------
    def start(self) -> str:
        """Bring the sink up. Returns the *source name* the recorder
        should capture audio from."""
        ok, msg = self.available()
        if not ok:
            raise RuntimeError(msg)
        if IS_WINDOWS:
            return self._start_windows()
        return self._start_linux()

    def stop(self) -> None:
        if IS_WINDOWS:
            self._win_device_index = None
            self._win_device_name = None
            return
        self._stop_linux()

    # ---------- Linux ----------
    def _start_linux(self) -> str:
        if self._sink_exists():
            return MONITOR_SOURCE
        out = subprocess.check_output([
            "pactl", "load-module", "module-null-sink",
            f"sink_name={SINK_NAME}",
            f"sink_properties=device.description={SINK_DESC}",
        ], text=True).strip()
        try:
            self._module_id = int(out)
        except ValueError:
            self._module_id = None
        logger.info("PulseAudio sink %s up (module=%s)", SINK_NAME, self._module_id)
        return MONITOR_SOURCE

    def _stop_linux(self) -> None:
        if self._module_id is None:
            try:
                subprocess.run(
                    ["pactl", "unload-module", "module-null-sink"],
                    capture_output=True, text=True, check=False,
                )
            except OSError:
                pass
            return
        try:
            subprocess.run(["pactl", "unload-module", str(self._module_id)],
                           capture_output=True, text=True, check=False)
        except OSError:
            pass
        self._module_id = None

    def _sink_exists(self) -> bool:
        try:
            out = subprocess.check_output(["pactl", "list", "short", "sinks"],
                                           text=True)
            return SINK_NAME in out
        except (OSError, subprocess.SubprocessError):
            return False

    # ---------- Windows ----------
    def _start_windows(self) -> str:
        """Resolve the virtual cable output device. Returns the dshow
        device name that the recorder should use as audio input."""
        import sounddevice as sd
        devices = sd.query_devices()
        # 1) honour explicit user preference
        if self._win_device_pref:
            for i, d in enumerate(devices):
                if (d.get("max_output_channels", 0) > 0
                        and self._win_device_pref.lower() in d.get("name", "").lower()):
                    self._win_device_index = i
                    self._win_device_name = d["name"]
                    break
        # 2) auto-detect known cables
        if self._win_device_index is None:
            for i, d in enumerate(devices):
                if d.get("max_output_channels", 0) <= 0:
                    continue
                name = (d.get("name") or "").lower()
                if any(h in name for h in WINDOWS_CABLE_HINTS):
                    self._win_device_index = i
                    self._win_device_name = d["name"]
                    break
        if self._win_device_index is None:
            raise RuntimeError(
                "No virtual audio cable detected. Install VB-Audio Virtual "
                "Cable from https://vb-audio.com/Cable/ , reboot, then try "
                "again.  The 'CABLE Input' device will be used to play TTS "
                "and the recorder will capture from 'CABLE Output'."
            )
        logger.info("Windows dub output: %s (idx=%s)",
                    self._win_device_name, self._win_device_index)
        # The DirectShow recording side uses the *companion* "CABLE Output"
        # device name. Heuristic: replace 'Input' with 'Output'.
        recorder_source = (self._win_device_name or "").replace("Input", "Output")
        return recorder_source

    # ------- playback -------
    def play_mp3_bytes(self, mp3: bytes) -> None:
        if not mp3:
            return
        if IS_WINDOWS:
            self._play_windows(mp3)
        else:
            self._play_linux(mp3)

    def _play_linux(self, mp3: bytes) -> None:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg required for TTS playback")
        ff = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0",
             "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        pa = subprocess.Popen(
            ["paplay", "--device", SINK_NAME,
             "--rate=48000", "--format=s16le", "--channels=2",
             "--raw"],
            stdin=ff.stdout,
        )
        try:
            ff.stdin.write(mp3)
            ff.stdin.close()
            pa.wait(timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass
        finally:
            try:
                ff.kill()
            except OSError:
                pass

    def _play_windows(self, mp3: bytes) -> None:
        """Decode MP3 via ffmpeg, then push float32 frames into the
        chosen WASAPI output device using sounddevice."""
        import numpy as np
        import sounddevice as sd
        if self._win_device_index is None:
            raise RuntimeError("AudioRouter not started")
        try:
            proc = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-i", "pipe:0",
                 "-f", "f32le", "-ar", "48000", "-ac", "2", "pipe:1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            pcm, _ = proc.communicate(mp3, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return
        if not pcm:
            return
        arr = np.frombuffer(pcm, dtype="<f4").reshape(-1, 2).copy()
        try:
            sd.play(arr, samplerate=48000,
                    device=self._win_device_index, blocking=True)
        except Exception:                                  # pylint: disable=broad-except
            logger.exception("Windows TTS playback failed")
