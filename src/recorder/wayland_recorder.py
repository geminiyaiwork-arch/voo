"""Wayland screen recorder via xdg-desktop-portal + GStreamer.

GNOME and KDE Wayland do not allow arbitrary screen capture. The official
mechanism is `org.freedesktop.portal.ScreenCast`, which returns a PipeWire
node ID after the user grants permission. We then feed that node into a
GStreamer pipeline (`gst-launch-1.0 pipewiresrc fd=N path=M ! ... ! filesink`)
that produces the final MP4/MKV/MOV file.

This module spawns `gst-launch-1.0` as a subprocess and exposes start/stop
semantics matching `FFmpegRecorder`, so callers can swap backends based on
the detected display server.
"""
from __future__ import annotations

import os
import random
import secrets
import shutil
import signal
import string
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    _DBUS_OK = True
except (ImportError, Exception):                  # pylint: disable=broad-except
    _DBUS_OK = False


PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
REQUEST_IFACE = "org.freedesktop.portal.Request"

# SourceTypes: 1 = MONITOR, 2 = WINDOW, 4 = VIRTUAL
SOURCE_MONITOR = 1
SOURCE_WINDOW = 2
# CursorMode: 1 = HIDDEN, 2 = EMBEDDED, 4 = METADATA
CURSOR_EMBEDDED = 2


def _rand_token(prefix: str = "voo") -> str:
    return f"{prefix}_{''.join(random.choices(string.ascii_letters + string.digits, k=12))}"


class WaylandPortalRecorder:
    """Performs the portal handshake, then streams via gst-launch-1.0."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._stream_proc: Optional[subprocess.Popen] = None
        self._stream_log: str = ""
        self._paused = False
        self._loop: Optional[GLib.MainLoop] = None
        self._bus = None
        self._sender_name: str = ""
        self._tcp_port: int = 0

    # ---------- availability ----------
    @staticmethod
    def available() -> tuple[bool, str]:
        if not _DBUS_OK:
            return False, "python3-dbus / python3-gi not installed"
        if not shutil.which("gst-launch-1.0"):
            return False, "gst-launch-1.0 not installed (install gstreamer1.0-tools)"
        return True, ""

    _gpu_enc_cache: str | None = None

    @classmethod
    def _detect_gpu_encoder(cls) -> str:
        """Return the name of the fastest available GST encoder.

        We probe with gst-inspect-1.0 once and cache.  Order of
        preference: VAAPI (Intel/AMD) > QSV (Intel) > NVENC (NVIDIA)
        > x264 (CPU fallback).  VAAPI runs anywhere with `intel-
        media-va-driver` + `gstreamer1.0-vaapi`, NVENC requires the
        proprietary NVIDIA build of gst-plugins-bad.
        """
        if cls._gpu_enc_cache is not None:
            return cls._gpu_enc_cache
        for cand in ("vah264enc", "vaapih264enc", "qsvh264enc",
                      "nvcudah264enc", "nvh264enc"):
            try:
                subprocess.check_output(
                    ["gst-inspect-1.0", cand],
                    stderr=subprocess.DEVNULL, timeout=2,
                )
                cls._gpu_enc_cache = cand
                return cand
            except (OSError, subprocess.SubprocessError):
                continue
        cls._gpu_enc_cache = ""
        return ""

    @staticmethod
    def _detect_screen_size() -> tuple[int, int]:
        """Best-effort primary monitor size for videocrop math."""
        try:
            out = subprocess.check_output(
                ["xrandr"], stderr=subprocess.DEVNULL,
                text=True, timeout=2,
            )
            for line in out.splitlines():
                if " connected" in line and "primary" in line:
                    for part in line.split():
                        if "x" in part and "+" in part:
                            geo = part.split("+")[0]
                            w, h = geo.split("x")
                            return int(w), int(h)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        return 1920, 1080

    @staticmethod
    def is_wayland() -> bool:
        return (
            os.environ.get("XDG_SESSION_TYPE") == "wayland"
            or bool(os.environ.get("WAYLAND_DISPLAY"))
        )

    # ---------- portal handshake ----------
    def _request_path(self, token: str) -> str:
        sender = self._sender_name.lstrip(":").replace(".", "_")
        return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

    def _await_response(self, request_path: str, timeout_sec: float = 60.0):
        result: dict = {"code": None, "results": None}
        loop = GLib.MainLoop()

        def _on_response(code, results):
            result["code"] = int(code)
            result["results"] = dict(results) if results else {}
            loop.quit()

        proxy = self._bus.get_object(PORTAL_BUS, request_path)
        signal_match = proxy.connect_to_signal("Response", _on_response,
                                                dbus_interface=REQUEST_IFACE)

        timer_id = GLib.timeout_add(int(timeout_sec * 1000), loop.quit)
        try:
            loop.run()
        finally:
            GLib.source_remove(timer_id)
            signal_match.remove()

        return result

    def _portal_session(self, capture_window: bool = False):
        """Walk the portal flow, return (streams, pipewire_fd)."""
        DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SessionBus()
        self._sender_name = self._bus.get_unique_name()

        portal_obj = self._bus.get_object(PORTAL_BUS, PORTAL_PATH)
        sc = dbus.Interface(portal_obj, SCREENCAST_IFACE)

        # --- 1. CreateSession ---
        sess_token = _rand_token("session")
        req_token = _rand_token("createsess")
        sc.CreateSession({
            "session_handle_token": sess_token,
            "handle_token": req_token,
        })
        resp = self._await_response(self._request_path(req_token))
        if resp["code"] != 0 or "session_handle" not in (resp["results"] or {}):
            raise RuntimeError("Portal CreateSession denied or timed out")
        session_handle = resp["results"]["session_handle"]

        # --- 2. SelectSources ---
        req_token = _rand_token("selsrc")
        types = SOURCE_WINDOW if capture_window else SOURCE_MONITOR
        sc.SelectSources(session_handle, {
            "handle_token": req_token,
            "types": dbus.UInt32(types),
            "multiple": False,
            "cursor_mode": dbus.UInt32(CURSOR_EMBEDDED),
        })
        resp = self._await_response(self._request_path(req_token))
        if resp["code"] != 0:
            raise RuntimeError("Portal SelectSources denied")

        # --- 3. Start ---
        req_token = _rand_token("start")
        sc.Start(session_handle, "", {"handle_token": req_token})
        resp = self._await_response(self._request_path(req_token), timeout_sec=120)
        if resp["code"] != 0:
            raise RuntimeError("Portal Start denied (user cancelled or no permission)")

        streams = resp["results"].get("streams")
        if not streams:
            raise RuntimeError("Portal returned no PipeWire streams")
        # streams is a(ua{sv})  → list of (node_id, props)
        node_id = int(streams[0][0])

        # --- 4. OpenPipeWireRemote ---
        fd_obj = sc.OpenPipeWireRemote(session_handle, {})
        # dbus returns a UnixFD wrapper — convert to int
        fd = fd_obj.take() if hasattr(fd_obj, "take") else int(fd_obj)
        return node_id, fd, session_handle

    # ---------- gstreamer pipeline ----------
    @staticmethod
    def _build_pipeline(node_id: int, output_path: str,
                        fps: int, codec: str, container: str,
                        audio_source: str, audio_kbps: int,
                        mic_device: str, desktop_device: str,
                        stream_urls: list[str] | None = None,
                        stream_bitrate_kbps: int = 4500,
                        stream_keyint_sec: int = 2,
                        stream_audio_kbps: int = 160,
                        capture_region: tuple[int, int, int, int] | None = None,
                        screen_size: tuple[int, int] | None = None,
                        target_width: int = 1920,
                        target_height: int = 1080) -> list[str]:
        """Build a gst-launch-1.0 argv.

        Key points:
          * `pipewiresrc` emits DMA-BUF / NV12 / I420 etc. — we let it
            negotiate freely, then push through videoconvert + videorate
            BEFORE constraining caps. Forcing caps right after pipewiresrc
            triggers 'no more input formats / not-negotiated' errors.
          * `videorate` normalises variable rate from compositors.
          * Encoders are wired with explicit bitrate (kbps).
        """
        # Streaming-aware pipeline.
        # When stream_fd > 0 we also produce an FLV stream on that fd
        # (an OS pipe to the FFmpeg relay) so the *exact same* portal
        # video source is teed to both the file recorder and the
        # streamer.  No XWayland blackouts.
        _ = stream_keyint_sec
        _ = stream_audio_kbps
        _ = stream_bitrate_kbps
        streaming = bool(stream_urls)

        # ---- encoder ----
        # Detect GPU encoders at module import time (cached on class).
        gpu_enc = WaylandPortalRecorder._detect_gpu_encoder()
        if codec == "H265":
            if gpu_enc == "vaapih265enc":
                v_enc = [
                    "vaapih265enc",
                    f"bitrate={stream_bitrate_kbps}",
                    f"keyframe-period={fps * 2}",
                    "!", "h265parse",
                ]
            elif gpu_enc == "nvh265enc":
                v_enc = [
                    "nvh265enc", "preset=low-latency-hq",
                    f"bitrate={stream_bitrate_kbps}",
                    "!", "h265parse",
                ]
            else:
                v_enc = [
                    "x265enc", "tune=zerolatency", "speed-preset=superfast",
                    f"bitrate={stream_bitrate_kbps}",
                    "!", "h265parse",
                ]
        else:
            if gpu_enc == "vaapih264enc":
                v_enc = [
                    "vaapih264enc",
                    f"bitrate={stream_bitrate_kbps}",
                    f"keyframe-period={fps * 2}",
                    "!", "h264parse",
                ]
            elif gpu_enc == "vah264enc":
                v_enc = [
                    "vah264enc", "target-usage=4",
                    f"bitrate={stream_bitrate_kbps}",
                    "!", "h264parse",
                ]
            elif gpu_enc == "qsvh264enc":
                v_enc = [
                    "qsvh264enc",
                    f"bitrate={stream_bitrate_kbps}",
                    "!", "h264parse",
                ]
            elif gpu_enc == "nvh264enc":
                v_enc = [
                    "nvh264enc", "preset=low-latency-hq",
                    f"bitrate={stream_bitrate_kbps}",
                    "!", "h264parse",
                ]
            else:
                # Software fallback — superfast trades quality for speed.
                # 1-sec GOP (key-int-max=fps) cuts the time-to-first-frame
                # at the RTMP server by ~1 sec.  bframes=0 + zerolatency
                # removes the encoder lookahead delay.
                v_enc = [
                    "x264enc", "tune=zerolatency", "speed-preset=superfast",
                    f"bitrate={stream_bitrate_kbps}",
                    f"key-int-max={fps}", "bframes=0",
                    "rc-lookahead=0", "sliced-threads=true",
                    "threads=0",
                    "!", "h264parse", "config-interval=-1",
                ]

        # We always use the *fragmented* MP4/MOV variants so the file
        # remains playable even if the app or system crashes mid-record.
        # `fragment-duration=5000` writes a moof every 5 seconds.
        muxer_map = {
            "mp4": ["mp4mux", "fragment-duration=5000",
                     "presentation-time=true", "streamable=true"],
            "mkv": ["matroskamux", "streamable=true"],
            "mov": ["qtmux", "fragment-duration=5000",
                     "presentation-time=true", "streamable=true"],
        }
        muxer_tokens = muxer_map.get(container, muxer_map["mp4"])

        parts: list[str] = [
            "gst-launch-1.0", "-q", "-e",
            "pipewiresrc", f"path={node_id}",
            "do-timestamp=true",
            "!", "queue", "max-size-buffers=2", "max-size-time=0",
            "max-size-bytes=0", "leaky=downstream",
            "!", "videoconvert",
            "!", "video/x-raw,format=I420",
        ]

        # ---- Region crop ----
        if capture_region and screen_size:
            x, y, w, h = capture_region
            sw, sh = screen_size
            top = max(0, int(y))
            left = max(0, int(x))
            right = max(0, int(sw - (x + w)))
            bottom = max(0, int(sh - (y + h)))
            parts += [
                "!", "videocrop",
                f"top={top}", f"left={left}",
                f"right={right}", f"bottom={bottom}",
            ]

        # Downscale before the encoder.  Pipewire delivers the
        # compositor's native resolution which on HiDPI laptops can
        # be 2880x1800 / 3840x2400 — way too heavy for software x264.
        # We bound the output at the user's quality setting (1080p
        # default) which keeps CPU manageable.
        parts += [
            "!", "videoscale", "method=bilinear", "add-borders=false",
            "!", f"video/x-raw,width={target_width},height={target_height},"
                  "pixel-aspect-ratio=1/1",
            "!", "queue", "max-size-buffers=2", "max-size-time=0",
            "max-size-bytes=0", "leaky=downstream",
            "!", *v_enc,
        ]

        # Build the file muxer chunk with a fixed `name=mux` so the
        # audio branch can request a sink pad on it.
        file_muxer = [muxer_tokens[0], "name=mux"] + list(muxer_tokens[1:])
        if streaming:
            # tee the encoded H.264 into the file muxer + flvmux (stream)
            parts += [
                "!", "tee", "name=vtee",
                "vtee.", "!", "queue",
                "!", *file_muxer,
                "!", "filesink", f"location={output_path}",
                "vtee.", "!", "queue", "max-size-buffers=2",
                "max-size-time=0", "max-size-bytes=0", "leaky=downstream",
                "!", "flvmux", "name=smux", "streamable=true",
                "latency=0",
                "!", "fdsink", "fd=__STREAM_FD__", "sync=false",
            ]
        else:
            parts += [
                "!", "queue",
                "!", *file_muxer,
                "!", "filesink", f"location={output_path}",
            ]

        # ---- audio branch ----
        if audio_source in ("mic", "both", "desktop"):
            if audio_source == "desktop":
                device = desktop_device if desktop_device != "default" else ""
            else:
                device = mic_device if mic_device != "default" else ""

            audio_branch = ["pulsesrc"]
            if device:
                audio_branch.append(f"device={device}")
            audio_branch += [
                "!", "audioconvert",
                "!", "audioresample",
                "!", "queue", "max-size-buffers=8", "max-size-time=0",
            "max-size-bytes=0", "leaky=downstream",
                "!", "voaacenc", f"bitrate={audio_kbps * 1000}",
                "!", "aacparse",
            ]
            if streaming:
                audio_branch += [
                    "!", "tee", "name=atee",
                    "atee.", "!", "queue", "!", "mux.",
                    "atee.", "!", "queue", "!", "smux.",
                ]
            else:
                audio_branch += ["!", "queue", "!", "mux."]
            parts += audio_branch

        return parts

    # ---------- public API ----------
    def start(self, cfg) -> None:
        """`cfg` is the same RecordConfig used by FFmpegRecorder."""
        ok, msg = self.available()
        if not ok:
            raise RuntimeError(f"Wayland backend unavailable: {msg}")
        if self._proc is not None:
            raise RuntimeError("Recording already in progress")

        capture_window = (cfg.capture_mode == "window")
        node_id, pipewire_fd, _session = self._portal_session(capture_window)

        Path(cfg.output_path).parent.mkdir(parents=True, exist_ok=True)

        stream_urls = list(getattr(cfg, "stream_urls", []) or [])

        # Detect the source monitor size so videocrop knows the canvas.
        screen_size = self._detect_screen_size()
        capture_region = None
        if (getattr(cfg, "capture_mode", "fullscreen") == "area"
                and getattr(cfg, "capture_region", None)):
            capture_region = tuple(cfg.capture_region)        # type: ignore[arg-type]

        # Resolve target width/height from the user's video setting.
        from .ffmpeg_handler import RESOLUTION_MAP
        tw, th = RESOLUTION_MAP.get(cfg.resolution, (1920, 1080))
        # Pick the streaming bitrate that matches the chosen quality
        # when the user hasn't customised it (8 Mbps for 1080p felt
        # heavy under software encode).
        stream_br = int(getattr(cfg, "stream_bitrate_kbps", 4500) or 4500)

        pipeline = self._build_pipeline(
            node_id=node_id,
            output_path=cfg.output_path,
            fps=cfg.fps,
            codec=cfg.codec,
            container=cfg.container,
            audio_source=cfg.audio_source,
            audio_kbps=cfg.audio_kbps,
            mic_device=cfg.mic_device,
            desktop_device=cfg.desktop_device,
            stream_urls=stream_urls,
            stream_bitrate_kbps=stream_br,
            stream_keyint_sec=int(getattr(cfg, "stream_keyint_sec", 2)),
            stream_audio_kbps=int(getattr(cfg, "stream_audio_kbps", 160)),
            capture_region=capture_region,
            screen_size=screen_size,
            target_width=tw,
            target_height=th,
        )

        env = os.environ.copy()
        env["PIPEWIRE_REMOTE"] = "1"

        # ---------- streaming bridge wiring ----------
        # Create an OS pipe so that GStreamer's flvmux output (via fdsink)
        # feeds straight into FFmpeg's stdin.  No XWayland, no x11grab —
        # the exact same portal-granted frames go to BOTH outputs.
        stream_read_fd = -1
        stream_write_fd = -1
        if stream_urls:
            stream_read_fd, stream_write_fd = os.pipe()

        # Substitute the placeholder for the streaming FD.
        if stream_write_fd >= 0:
            pipeline = [tok.replace("__STREAM_FD__", str(stream_write_fd))
                        for tok in pipeline]

        # The portal handed us a PipeWire FD; we pass it via `fd=` arg to
        # pipewiresrc.  Build a fresh argv with that inserted.
        new_args: list[str] = []
        inserted = False
        for tok in pipeline:
            new_args.append(tok)
            if not inserted and tok == "pipewiresrc":
                new_args.append(f"fd={pipewire_fd}")
                inserted = True

        self._paused = False
        pass_fds = [pipewire_fd]
        if stream_write_fd >= 0:
            pass_fds.append(stream_write_fd)
        self._proc = subprocess.Popen(
            new_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
            env=env,
            pass_fds=tuple(pass_fds),
            close_fds=True,
        )
        # Close our copy of the write end — gst owns it now.
        if stream_write_fd >= 0:
            os.close(stream_write_fd)

        # ---------- spawn FFmpeg relay ----------
        if stream_urls and stream_read_fd >= 0:
            self._start_streaming_bridge(
                stream_urls=stream_urls,
                input_fd=stream_read_fd,
            )

    # ---------- streaming bridge ----------
    @staticmethod
    def _stream_log_path() -> Path:
        cache = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
        out = cache / "visio-eye"
        out.mkdir(parents=True, exist_ok=True)
        return out / "stream.log"

    def _start_streaming_bridge(self, stream_urls: list[str],
                                 input_fd: int) -> None:
        """Spawn an FFmpeg subprocess that reads the GStreamer FLV
        stream from a pipe FD and forwards it to every RTMP/RTMPS
        destination via the tee muxer (one re-mux, many outputs).

        We use copy codec because GStreamer already encoded H.264+AAC.
        This means streaming adds <2% CPU on top of recording, and the
        source frames are *identical* to what the file gets — solving
        the Wayland/XWayland black-screen problem entirely.
        """
        if len(stream_urls) == 1:
            # Direct push, simpler and lighter than tee.
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "info",
                "-fflags", "+nobuffer+discardcorrupt+genpts",
                "-flags", "+low_delay",
                "-probesize", "32",
                "-analyzeduration", "0",
                "-f", "flv", "-i", "pipe:0",
                "-c", "copy",
                "-flush_packets", "1",
                "-f", "flv", stream_urls[0],
            ]
        else:
            outputs = "|".join(
                f"[f=flv:onfail=ignore:flvflags=no_duration_filesize]{u}"
                for u in stream_urls
            )
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "info",
                "-fflags", "+nobuffer+discardcorrupt+genpts",
                "-flags", "+low_delay",
                "-probesize", "32",
                "-analyzeduration", "0",
                "-f", "flv", "-i", "pipe:0",
                "-map", "0:v:0", "-map", "0:a:0",
                "-c", "copy",
                "-flush_packets", "1",
                "-flags", "+global_header",
                "-f", "tee", outputs,
            ]
        log_path = self._stream_log_path()
        try:
            log_fh = open(log_path, "ab", buffering=0)
            log_fh.write(b"\n\n===== Visio Eye streaming session =====\n")
            log_fh.write(("cmd: " + " ".join(cmd) + "\n").encode())
            log_fh.flush()
            self._stream_proc = subprocess.Popen(
                cmd,
                stdin=input_fd,                 # GStreamer pipe → FFmpeg stdin
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )
            # We've passed the fd to the child; close ours.
            os.close(input_fd)
            self._stream_log = str(log_path)
        except OSError as exc:
            self._stream_proc = None
            self._stream_log = f"FFmpeg failed to launch: {exc}"
            try:
                os.close(input_fd)
            except OSError:
                pass

    def pause(self) -> None:
        if self._proc and not self._paused:
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGSTOP)
                self._paused = True
            except ProcessLookupError:
                pass

    def resume(self) -> None:
        if self._proc and self._paused:
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGCONT)
                self._paused = False
            except ProcessLookupError:
                pass

    def stop(self) -> tuple[int, str]:
        if not self._proc:
            return 0, ""
        try:
            if self._paused:
                self.resume()
            # gst-launch with -e cleanly finalizes on SIGINT
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                    self._proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                    self._proc.wait()
            err = ""
            if self._proc.stderr:
                err = self._proc.stderr.read().decode("utf-8", errors="ignore")
            code = self._proc.returncode or 0

            # Stop the streaming subprocess too
            if self._stream_proc is not None:
                try:
                    os.killpg(os.getpgid(self._stream_proc.pid), signal.SIGINT)
                except ProcessLookupError:
                    pass
                try:
                    self._stream_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        self._stream_proc.kill()
                        self._stream_proc.wait()
                    except OSError:
                        pass
                if self._stream_proc.stderr:
                    self._stream_log = self._stream_proc.stderr.read().decode(
                        "utf-8", errors="ignore"
                    )
            return code, err
        finally:
            self._proc = None
            self._stream_proc = None
            self._tcp_port = 0
            self._paused = False

    def is_recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_paused(self) -> bool:
        return self._paused
