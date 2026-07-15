"""Cross-platform system audio loopback capture.

Linux: spawns ``parec`` reading from ``@DEFAULT_MONITOR@`` (PulseAudio
or PipeWire-pulse). No PortAudio needed; parec is in
``pulseaudio-utils`` which is already a KO'ZGU dependency.

Windows: uses ``sounddevice`` (PortAudio) with WASAPI loopback on the
default output device. WASAPI loopback is a built-in Windows feature
(Vista+), so no VB-Cable or Stereo Mix is required to capture system
audio for ASR. The user still needs VB-Cable for the *playback* side
of the dubbing pipeline (see audio_router.py).
"""
from __future__ import annotations

import collections
import logging
import shutil
import subprocess
import sys
import threading
from typing import Callable, Optional

import numpy as np

try:                                            # pragma: no cover - optional dep
    from scipy.signal import resample_poly as _RESAMPLE_POLY
except Exception:                               # pylint: disable=broad-except
    _RESAMPLE_POLY = None

logger = logging.getLogger(__name__)


IS_WINDOWS = sys.platform.startswith("win")

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SECONDS_DEFAULT = 3.0
BYTES_PER_SAMPLE = 4          # FLOAT32LE
WASAPI_BLOCK_MS = 20          # sounddevice callback granularity (ms)
STDERR_RING_LINES = 32        # last N stderr lines kept for diagnostics


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
        self._err_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._callback: Callable[[np.ndarray], None] | None = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._buf = bytearray()
        # Diagnostics — reader-thread health & captured stderr.
        self._stderr_ring: "collections.deque[str]" = collections.deque(
            maxlen=STDERR_RING_LINES,
        )
        self._reader_died = False
        # WASAPI-side: device-native rate + 16 kHz accumulator (guarded by lock
        # because the sounddevice audio callback runs off-thread).
        self._dev_rate: int = SAMPLE_RATE
        self._pcm16 = np.zeros(0, dtype=np.float32)
        self._pcm_lock = threading.Lock()

    def set_error_callback(self, fn: Optional[Callable[[str], None]]) -> None:
        """Register a callback fired once if the capture reader dies before
        ``stop()`` is called. Fed the diagnostic message (includes tail of
        captured stderr where available)."""
        self._on_error = fn

    @property
    def healthy(self) -> bool:
        """False once the reader thread / WASAPI stream has exited abnormally."""
        return not self._reader_died

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
        self._reader_died = False
        self._stderr_ring.clear()
        with self._pcm_lock:
            self._pcm16 = np.zeros(0, dtype=np.float32)

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
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self._thread = threading.Thread(target=self._parec_loop, daemon=True,
                                         name="dub-capture")
        self._thread.start()
        self._err_thread = threading.Thread(target=self._drain_stderr,
                                             daemon=True, name="dub-capture-err")
        self._err_thread.start()

    def _drain_stderr(self) -> None:
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        try:
            for raw in iter(proc.stderr.readline, b""):
                if not raw:
                    break
                try:
                    line = raw.decode("utf-8", errors="replace").rstrip()
                except Exception:                           # pylint: disable=broad-except
                    continue
                if line:
                    self._stderr_ring.append(line)
        except (OSError, ValueError):
            pass

    def _parec_loop(self) -> None:
        assert self._proc is not None
        assert self._callback is not None
        chunk_bytes = int(SAMPLE_RATE * self.chunk_seconds) * BYTES_PER_SAMPLE
        buf = bytearray()
        exit_reason = "eof"
        try:
            while not self._stop.is_set():
                data = self._proc.stdout.read(8192)
                if not data:
                    exit_reason = "eof"
                    break
                buf.extend(data)
                while len(buf) >= chunk_bytes:
                    block = bytes(buf[:chunk_bytes])
                    del buf[:chunk_bytes]
                    samples = np.frombuffer(block, dtype="<f4").copy()
                    self._safe_cb(samples)
        except (OSError, ValueError) as exc:
            exit_reason = f"error: {exc}"
        if not self._stop.is_set():
            self._notify_reader_death(f"parec reader exited ({exit_reason})")

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

        # Query the *device-native* rate — WASAPI loopback rejects any other
        # samplerate, and hard-coding 48 kHz breaks capture on 44.1 kHz
        # outputs (which are common on laptops / USB DACs).
        dev_rate = int(SAMPLE_RATE)
        try:
            info = sd.query_devices(device if device is not None else sd.default.device)
            dev_rate = int(round(float(info["default_samplerate"])))
        except Exception:                                   # pylint: disable=broad-except
            logger.warning("Could not query WASAPI default_samplerate; "
                           "assuming %d Hz", dev_rate)
        self._dev_rate = dev_rate if dev_rate > 0 else SAMPLE_RATE

        if _RESAMPLE_POLY is None and self._dev_rate != SAMPLE_RATE:
            logger.warning(
                "scipy.signal.resample_poly unavailable — falling back to "
                "cheap decimation; install scipy or soxr for clean audio.",
            )

        # Small callback block (~20 ms) — accumulate to chunk_seconds in
        # Python so we don't add 3 s of buffering to the audio thread.
        block_frames = max(1, int(self._dev_rate * WASAPI_BLOCK_MS / 1000))

        # sounddevice's WasapiSettings(loopback=True) captures the speaker
        # output instead of a mic.
        extra = sd.WasapiSettings(loopback=True) if wasapi_idx is not None else None

        self._sd_stream = sd.InputStream(
            device=device,
            channels=2,
            samplerate=self._dev_rate,
            dtype="float32",
            blocksize=block_frames,
            extra_settings=extra,
            callback=self._wasapi_callback,
            finished_callback=self._wasapi_finished,
        )
        self._sd_stream.start()

    def _wasapi_callback(self, indata, frames, _time, status) -> None:
        if status:
            # sounddevice CallbackFlags — overflow, priming, etc. Keep in the
            # diagnostic ring so a stall can be explained later.
            self._stderr_ring.append(f"wasapi status: {status}")
        if indata is None or len(indata) == 0:
            return
        try:
            mono = indata.mean(axis=1) if indata.ndim == 2 else indata
            mono = np.ascontiguousarray(mono, dtype=np.float32)
            if self._dev_rate == SAMPLE_RATE:
                resampled = mono
            elif _RESAMPLE_POLY is not None:
                # resample_poly reduces up/down by gcd internally; anti-alias
                # filter is applied.
                resampled = _RESAMPLE_POLY(
                    mono, SAMPLE_RATE, int(self._dev_rate),
                ).astype(np.float32, copy=False)
            else:
                step = max(1, int(round(self._dev_rate / SAMPLE_RATE)))
                resampled = mono[::step].astype(np.float32, copy=False)

            chunk_frames = int(SAMPLE_RATE * self.chunk_seconds)
            with self._pcm_lock:
                if self._pcm16.size == 0:
                    self._pcm16 = resampled
                else:
                    self._pcm16 = np.concatenate((self._pcm16, resampled))
                while self._pcm16.size >= chunk_frames:
                    block = self._pcm16[:chunk_frames].copy()
                    self._pcm16 = self._pcm16[chunk_frames:]
                    # Release the lock while invoking the user callback so a
                    # slow consumer can't starve the audio thread's next tick.
                    self._pcm_lock.release()
                    try:
                        self._safe_cb(block)
                    finally:
                        self._pcm_lock.acquire()
        except Exception as exc:                            # pylint: disable=broad-except
            self._stderr_ring.append(f"wasapi callback error: {exc}")
            logger.exception("WASAPI callback failed")

    def _wasapi_finished(self) -> None:
        if not self._stop.is_set():
            self._notify_reader_death("WASAPI loopback stream ended")

    # ---------- shared ----------
    def _safe_cb(self, samples: np.ndarray) -> None:
        if self._callback is None:
            return
        try:
            self._callback(samples)
        except Exception:                                  # pylint: disable=broad-except
            logger.exception("dub capture callback failed")

    def _notify_reader_death(self, reason: str) -> None:
        """Fire once when the reader exits before ``stop()`` was requested."""
        if self._reader_died:
            return
        self._reader_died = True
        tail = " | ".join(list(self._stderr_ring)[-8:])
        msg = f"{reason}" + (f" — stderr: {tail}" if tail else "")
        logger.warning("dub capture stopped unexpectedly: %s", msg)
        cb = self._on_error
        if cb is not None:
            try:
                cb(msg)
            except Exception:                              # pylint: disable=broad-except
                logger.exception("dub capture on_error callback failed")

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
        if self._err_thread is not None:
            self._err_thread.join(timeout=1)
            self._err_thread = None
