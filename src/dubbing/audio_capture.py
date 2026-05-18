"""Cross-platform system audio loopback capture.

Linux: spawns ``parec`` reading from ``@DEFAULT_MONITOR@`` (PulseAudio
or PipeWire-pulse). No PortAudio needed; parec is in
``pulseaudio-utils`` which is already a Visio Eye dependency.

Windows: uses ``sounddevice`` (PortAudio) with WASAPI loopback on the
default output device. WASAPI loopback is a built-in Windows feature
(Vista+), so no VB-Cable or Stereo Mix is required to capture system
audio for ASR. The user still needs VB-Cable for the *playback* side
of the dubbing pipeline (see audio_router.py).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


IS_WINDOWS = sys.platform.startswith("win")

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SECONDS_DEFAULT = 3.0
BYTES_PER_SAMPLE = 4          # FLOAT32LE


class MonitorCapture:
    """Background thread that emits float32 PCM chunks at 16 kHz mono.

    The callback runs in the reader thread — keep it short (push to a
    queue, return immediately).
    """

    def __init__(self,
                 source: str = "@DEFAULT_MONITOR@",
                 chunk_seconds: float = CHUNK_SECONDS_DEFAULT) -> None:
        self.source = source
        self.chunk_seconds = chunk_seconds
        self._proc: subprocess.Popen | None = None
        self._sd_stream = None                              # sounddevice stream
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._callback: Callable[[np.ndarray], None] | None = None
        self._buf = bytearray()

    @staticmethod
    def available() -> tuple[bool, str]:
        if IS_WINDOWS:
            try:
                import sounddevice as _sd                   # noqa: F401
            except ImportError:
                return False, ("sounddevice not installed "
                               "(pip install sounddevice)")
            return True, ""
        if not shutil.which("parec"):
            return False, "parec not installed (apt install pulseaudio-utils)"
        return True, ""

    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        ok, msg = self.available()
        if not ok:
            raise RuntimeError(msg)
        if self._proc is not None or self._sd_stream is not None:
            raise RuntimeError("capture already running")
        self._callback = callback
        self._stop.clear()

        if IS_WINDOWS:
            self._start_wasapi()
        else:
            self._start_parec()

    # ---------- Linux: parec subprocess ----------
    def _start_parec(self) -> None:
        cmd = [
            "parec",
            f"--device={self.source}",
            "--format=float32le",
            f"--rate={SAMPLE_RATE}",
            f"--channels={CHANNELS}",
            "--latency-msec=200",
        ]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self._thread = threading.Thread(target=self._parec_loop, daemon=True,
                                         name="dub-capture")
        self._thread.start()

    def _parec_loop(self) -> None:
        assert self._proc is not None
        assert self._callback is not None
        chunk_bytes = int(SAMPLE_RATE * self.chunk_seconds) * BYTES_PER_SAMPLE
        buf = bytearray()
        try:
            while not self._stop.is_set():
                data = self._proc.stdout.read(8192)
                if not data:
                    break
                buf.extend(data)
                while len(buf) >= chunk_bytes:
                    block = bytes(buf[:chunk_bytes])
                    del buf[:chunk_bytes]
                    samples = np.frombuffer(block, dtype="<f4").copy()
                    self._safe_cb(samples)
        except (OSError, ValueError):
            pass

    # ---------- Windows: WASAPI loopback ----------
    def _start_wasapi(self) -> None:
        import sounddevice as sd
        # Pick the WASAPI host API; fall back to default if not present.
        hostapis = sd.query_hostapis()
        wasapi_idx = next((i for i, h in enumerate(hostapis)
                           if "wasapi" in h.get("name", "").lower()), None)
        device = None
        if wasapi_idx is not None:
            default_out = hostapis[wasapi_idx]["default_output_device"]
            if default_out >= 0:
                device = default_out

        chunk_frames = int(SAMPLE_RATE * self.chunk_seconds)
        # sounddevice's WasapiSettings(loopback=True) captures the speaker
        # output instead of a mic.
        extra = sd.WasapiSettings(loopback=True) if wasapi_idx is not None else None

        # We let sounddevice handle the device-native rate, then resample
        # in our callback to 16 kHz mono float32 for Whisper.
        self._sd_stream = sd.InputStream(
            device=device,
            channels=2,
            samplerate=48000,
            dtype="float32",
            blocksize=int(48000 * self.chunk_seconds),
            extra_settings=extra,
            callback=self._wasapi_callback,
        )
        self._sd_stream.start()

    def _wasapi_callback(self, indata, frames, _time, status) -> None:
        # downmix to mono, then naive resample 48000 -> 16000 (factor 3).
        if indata is None or len(indata) == 0:
            return
        mono = indata.mean(axis=1) if indata.ndim == 2 else indata
        # decimate by 3 — Whisper is robust to cheap downsampling
        resampled = mono[::3].astype(np.float32, copy=False)
        self._safe_cb(resampled)

    # ---------- shared ----------
    def _safe_cb(self, samples: np.ndarray) -> None:
        if self._callback is None:
            return
        try:
            self._callback(samples)
        except Exception:                                  # pylint: disable=broad-except
            logger.exception("dub capture callback failed")

    def stop(self) -> None:
        self._stop.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self._proc.kill()
                except OSError:
                    pass
            self._proc = None
        if self._sd_stream is not None:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception:                              # pylint: disable=broad-except
                pass
            self._sd_stream = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
