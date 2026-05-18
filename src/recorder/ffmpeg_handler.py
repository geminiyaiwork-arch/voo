"""FFmpeg subprocess-based screen + audio recorder.

Cross-platform: builds different FFmpeg pipelines depending on the OS.

Linux (X11):     -f x11grab    + -f pulse  + -f v4l2
Linux (Wayland): handled by WaylandPortalRecorder via xdg-desktop-portal
Windows:         -f gdigrab    + -f dshow  + -f dshow

Supports webcam overlay, logo overlay, multiple resolutions up to 4K,
hardware-accelerated encoding when available (nvenc / qsv / vaapi),
and pause/resume/stop semantics.
"""
from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


IS_WINDOWS = sys.platform.startswith("win")


RESOLUTION_MAP = {
    "480p":  (854, 480),
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    "2K":    (2560, 1440),
    "4K":    (3840, 2160),
}

BITRATE_MAP = {
    "Low":    "2M",
    "Medium": "5M",
    "High":   "10M",
    "Ultra":  "20M",
    "Auto":   None,
}

POSITION_MAP = {
    "top_left":     "{m}:{m}",
    "top_right":    "main_w-overlay_w-{m}:{m}",
    "bottom_left":  "{m}:main_h-overlay_h-{m}",
    "bottom_right": "main_w-overlay_w-{m}:main_h-overlay_h-{m}",
}


def position_expr(position: str, margin: int = 20,
                  custom: tuple[int, int] | None = None) -> str:
    if position == "custom" and custom is not None:
        return f"{custom[0]}:{custom[1]}"
    template = POSITION_MAP.get(position, POSITION_MAP["bottom_right"])
    return template.format(m=margin)


@dataclass
class RecordConfig:
    output_path: str
    resolution: str = "1080p"
    fps: int = 30
    codec: str = "H264"
    container: str = "mp4"
    bitrate: str = "Auto"
    encoder: str = "CPU"          # CPU | GPU
    audio_source: str = "both"    # mic | desktop | both | none
    audio_kbps: int = 192
    mic_device: str = "default"
    desktop_device: str = "default"
    noise_suppression: bool = True
    echo_cancellation: bool = True
    capture_mode: str = "fullscreen"   # fullscreen | area | window
    capture_region: tuple[int, int, int, int] | None = None  # x,y,w,h
    monitor_index: int = 0
    camera_enabled: bool = False
    camera_device: str = ""        # /dev/videoN on Linux, dshow name on Windows
    camera_position: str = "bottom_right"
    camera_custom: tuple[int, int] | None = None
    camera_size: tuple[int, int] = (240, 180)
    camera_opacity: int = 100
    logo_enabled: bool = False
    logo_path: str = ""
    logo_position: str = "top_right"
    logo_custom: tuple[int, int] | None = None
    logo_size: tuple[int, int] = (120, 120)
    logo_opacity: int = 90
    extra_args: list[str] = field(default_factory=list)
    # ----- streaming -----
    stream_urls: list[str] = field(default_factory=list)
    stream_bitrate_kbps: int = 4500
    stream_keyint_sec: int = 2
    stream_audio_kbps: int = 160


class FFmpegRecorder:
    """Wraps an FFmpeg subprocess for screen+audio recording."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._cfg: Optional[RecordConfig] = None
        self._paused = False

    @staticmethod
    def ffmpeg_available() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def detect_display_server() -> str:
        if IS_WINDOWS:
            return "windows"
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        return "x11"

    @staticmethod
    def detect_screen_size() -> tuple[int, int]:
        if IS_WINDOWS:
            try:
                import ctypes
                user32 = ctypes.windll.user32                        # type: ignore[attr-defined]
                user32.SetProcessDPIAware()
                return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            except (OSError, AttributeError):
                return 1920, 1080
        try:
            out = subprocess.check_output(
                ["xrandr"], stderr=subprocess.DEVNULL, text=True, timeout=2
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

    # ----------------------------------------------------------------
    # command builders
    # ----------------------------------------------------------------
    def build_command(self, cfg: RecordConfig) -> list[str]:
        cmd: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

        screen_w, screen_h = self.detect_screen_size()
        if cfg.capture_mode == "area" and cfg.capture_region:
            x, y, w, h = cfg.capture_region
            video_size = f"{w}x{h}"
        else:
            x, y, w, h = 0, 0, screen_w, screen_h
            video_size = f"{screen_w}x{screen_h}"

        # ---------- video input ----------
        if IS_WINDOWS:
            # gdigrab works on every Windows version. ddagrab is faster
            # for 4K but requires DXGI 11 and FFmpeg 6+; gdigrab is the
            # safer default. Region capture via offset_x/offset_y.
            if cfg.capture_mode == "area" and cfg.capture_region:
                cmd += [
                    "-f", "gdigrab",
                    "-framerate", str(cfg.fps),
                    "-offset_x", str(x), "-offset_y", str(y),
                    "-video_size", video_size,
                    "-i", "desktop",
                ]
            else:
                cmd += [
                    "-f", "gdigrab",
                    "-framerate", str(cfg.fps),
                    "-i", "desktop",
                ]
        else:
            display_offset = f":0.0+{x},{y}" if cfg.capture_mode == "area" else ":0.0"
            cmd += [
                "-f", "x11grab",
                "-framerate", str(cfg.fps),
                "-video_size", video_size,
                "-i", display_offset,
            ]

        # ---------- camera input ----------
        camera_active = False
        if cfg.camera_enabled and cfg.camera_device:
            cw, ch = cfg.camera_size
            if IS_WINDOWS:
                cmd += [
                    "-f", "dshow",
                    "-framerate", str(min(cfg.fps, 30)),
                    "-video_size", f"{cw}x{ch}",
                    "-i", f"video={cfg.camera_device}",
                ]
                camera_active = True
            elif Path(cfg.camera_device).exists():
                cmd += [
                    "-f", "v4l2",
                    "-framerate", str(min(cfg.fps, 30)),
                    "-video_size", f"{cw}x{ch}",
                    "-i", cfg.camera_device,
                ]
                camera_active = True

        # ---------- logo input ----------
        logo_active = False
        if cfg.logo_enabled and cfg.logo_path and Path(cfg.logo_path).exists():
            cmd += ["-loop", "1", "-i", cfg.logo_path]
            logo_active = True

        # ---------- audio inputs ----------
        audio_inputs = 0
        if cfg.audio_source in ("mic", "both"):
            if IS_WINDOWS:
                dev = cfg.mic_device if cfg.mic_device and cfg.mic_device != "default" else ""
                if dev:
                    cmd += ["-f", "dshow", "-i", f"audio={dev}"]
                    audio_inputs += 1
            else:
                cmd += ["-f", "pulse", "-i", cfg.mic_device]
                audio_inputs += 1
        if cfg.audio_source in ("desktop", "both"):
            if IS_WINDOWS:
                dev = cfg.desktop_device if cfg.desktop_device and cfg.desktop_device != "default" else ""
                if dev:
                    cmd += ["-f", "dshow", "-i", f"audio={dev}"]
                    audio_inputs += 1
            else:
                cmd += ["-f", "pulse", "-i", cfg.desktop_device]
                audio_inputs += 1

        # ---------- filter graph ----------
        target_w, target_h = RESOLUTION_MAP.get(cfg.resolution, (1920, 1080))
        filter_parts: list[str] = []

        last_video = "0:v"
        video_chain = (
            f"[{last_video}]scale={target_w}:{target_h}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1[base]"
        )
        filter_parts.append(video_chain)
        current = "base"

        next_input_idx = 1
        if camera_active:
            cam_idx = next_input_idx
            next_input_idx += 1
            cw, ch = cfg.camera_size
            opacity = max(0.0, min(1.0, cfg.camera_opacity / 100.0))
            cam_chain = (
                f"[{cam_idx}:v]scale={cw}:{ch},"
                f"format=yuva420p,colorchannelmixer=aa={opacity}[cam]"
            )
            filter_parts.append(cam_chain)
            pos = position_expr(cfg.camera_position, 20, cfg.camera_custom)
            filter_parts.append(f"[{current}][cam]overlay={pos}[withcam]")
            current = "withcam"

        if logo_active:
            logo_idx = next_input_idx
            next_input_idx += 1
            lw, lh = cfg.logo_size
            opacity = max(0.0, min(1.0, cfg.logo_opacity / 100.0))
            logo_chain = (
                f"[{logo_idx}:v]scale={lw}:{lh},"
                f"format=yuva420p,colorchannelmixer=aa={opacity}[logo]"
            )
            filter_parts.append(logo_chain)
            pos = position_expr(cfg.logo_position, 20, cfg.logo_custom)
            filter_parts.append(f"[{current}][logo]overlay={pos}[withlogo]")
            current = "withlogo"

        # audio mix
        audio_label = None
        if audio_inputs > 0:
            mic_filters: list[str] = []
            if cfg.noise_suppression:
                mic_filters.append("afftdn=nf=-25")
            if cfg.echo_cancellation:
                mic_filters.append("highpass=f=200,lowpass=f=3000")

            audio_input_start = next_input_idx
            chains: list[str] = []
            labels: list[str] = []
            for i in range(audio_inputs):
                idx = audio_input_start + i
                filters = mic_filters if i == 0 and cfg.audio_source in ("mic", "both") else []
                chain = f"[{idx}:a]" + (",".join(filters) if filters else "anull")
                lbl = f"a{i}"
                chains.append(f"{chain}[{lbl}]")
                labels.append(f"[{lbl}]")
            filter_parts.extend(chains)
            if len(labels) > 1:
                filter_parts.append(
                    f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest[aout]"
                )
                audio_label = "aout"
            else:
                audio_label = labels[0].strip("[]")

        cmd += ["-filter_complex", ";".join(filter_parts)]
        cmd += ["-map", f"[{current}]"]
        if audio_label:
            cmd += ["-map", f"[{audio_label}]"]

        # ---------- codec selection ----------
        cmd += self._codec_args(cfg)

        # ---------- audio codec ----------
        if audio_label:
            cmd += ["-c:a", "aac", "-b:a", f"{cfg.audio_kbps}k", "-ar", "48000"]

        # ---------- output ----------
        cmd += ["-pix_fmt", "yuv420p"]
        cmd += ["-r", str(cfg.fps)]
        # Crash-safe MP4/MOV: write a moov atom at the START + fragment
        # every 5 seconds so a power loss only loses the unsaved tail.
        # `+empty_moov+default_base_moof+frag_keyframe` is FFmpeg's
        # canonical recipe for streamable / recoverable MP4 files.
        if (cfg.container or "mp4").lower() in ("mp4", "mov"):
            cmd += ["-movflags",
                    "+empty_moov+default_base_moof+frag_keyframe",
                    "-frag_duration", "5000000"]    # microseconds
        cmd += list(cfg.extra_args)

        if cfg.stream_urls:
            cmd += self._tee_output_args(cfg)
        else:
            cmd += [cfg.output_path]
        return cmd

    @staticmethod
    def _tee_output_args(cfg: RecordConfig) -> list[str]:
        """Build a `-f tee` clause that writes file + RTMP destinations.

        FFmpeg's tee muxer accepts a pipe-separated list of outputs, each
        with format-specific options.  Important quirks:
          * Each output gets its own format and key=value option block.
          * The file path goes last to give the recorder a deterministic
            `cfg.output_path` value.
          * RTMP needs `-f flv` and `onfail=ignore` so a dead destination
            doesn't kill the whole pipeline.
        """
        outputs: list[str] = []
        for url in cfg.stream_urls:
            if not url:
                continue
            outputs.append(
                f"[f=flv:onfail=ignore:flvflags=no_duration_filesize]{url}"
            )
        container = cfg.container or "mp4"
        outputs.append(f"[f={container}]{cfg.output_path}")
        # The tee output expects a single string.
        tee_string = "|".join(outputs)
        # Force AAC and reasonable streaming GOP.
        gop = max(1, int(cfg.fps * cfg.stream_keyint_sec))
        return [
            "-flags", "+global_header",
            "-g", str(gop),
            "-keyint_min", str(gop),
            "-sc_threshold", "0",
            "-f", "tee", tee_string,
        ]

    @staticmethod
    def _codec_args(cfg: RecordConfig) -> list[str]:
        bitrate = BITRATE_MAP.get(cfg.bitrate)
        args: list[str] = []
        gpu = (cfg.encoder == "GPU")

        if cfg.codec == "H265":
            if gpu and FFmpegRecorder._has_encoder("hevc_nvenc"):
                args += ["-c:v", "hevc_nvenc", "-preset", "fast"]
            elif gpu and FFmpegRecorder._has_encoder("hevc_qsv"):
                args += ["-c:v", "hevc_qsv"]
            elif gpu and FFmpegRecorder._has_encoder("hevc_amf"):
                args += ["-c:v", "hevc_amf"]
            elif gpu and FFmpegRecorder._has_encoder("hevc_vaapi") and not IS_WINDOWS:
                args += ["-c:v", "hevc_vaapi"]
            else:
                args += ["-c:v", "libx265", "-preset", "veryfast"]
        else:
            if gpu and FFmpegRecorder._has_encoder("h264_nvenc"):
                args += ["-c:v", "h264_nvenc", "-preset", "fast"]
            elif gpu and FFmpegRecorder._has_encoder("h264_qsv"):
                args += ["-c:v", "h264_qsv"]
            elif gpu and FFmpegRecorder._has_encoder("h264_amf"):
                args += ["-c:v", "h264_amf"]
            elif gpu and FFmpegRecorder._has_encoder("h264_vaapi") and not IS_WINDOWS:
                args += ["-c:v", "h264_vaapi"]
            else:
                args += ["-c:v", "libx264", "-preset", "veryfast"]

        if bitrate:
            args += ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", bitrate]
        else:
            args += ["-crf", "23"]
        return args

    _encoder_cache: dict[str, bool] = {}

    @classmethod
    def _has_encoder(cls, name: str) -> bool:
        if name in cls._encoder_cache:
            return cls._encoder_cache[name]
        try:
            out = subprocess.check_output(
                ["ffmpeg", "-hide_banner", "-encoders"],
                stderr=subprocess.DEVNULL, text=True, timeout=2,
            )
            cls._encoder_cache[name] = (name in out)
        except (OSError, subprocess.SubprocessError):
            cls._encoder_cache[name] = False
        return cls._encoder_cache[name]

    # ----------------------------------------------------------------
    # runtime — start / pause / resume / stop, with platform-correct
    # process group + signal handling.
    # ----------------------------------------------------------------
    def start(self, cfg: RecordConfig) -> None:
        if self._proc is not None:
            raise RuntimeError("Recording already in progress")
        Path(cfg.output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = self.build_command(cfg)
        self._cfg = cfg
        self._paused = False

        kwargs: dict = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["preexec_fn"] = os.setsid
        self._proc = subprocess.Popen(cmd, **kwargs)

    def pause(self) -> None:
        if self._proc and not self._paused:
            if IS_WINDOWS:
                # Windows FFmpeg has no SIGSTOP; we approximate pause by
                # suspending threads via SuspendThread. Best-effort.
                try:
                    self._suspend_windows(self._proc.pid, suspend=True)
                    self._paused = True
                except OSError:
                    pass
            else:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGSTOP)
                    self._paused = True
                except ProcessLookupError:
                    pass

    def resume(self) -> None:
        if self._proc and self._paused:
            if IS_WINDOWS:
                try:
                    self._suspend_windows(self._proc.pid, suspend=False)
                    self._paused = False
                except OSError:
                    pass
            else:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGCONT)
                    self._paused = False
                except ProcessLookupError:
                    pass

    @staticmethod
    def _suspend_windows(pid: int, suspend: bool) -> None:
        import ctypes
        TH32CS_SNAPTHREAD = 0x00000004
        THREAD_SUSPEND_RESUME = 0x0002

        class THREADENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ThreadID", ctypes.c_ulong),
                ("th32OwnerProcessID", ctypes.c_ulong),
                ("tpBasePri", ctypes.c_long),
                ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
            ]

        k = ctypes.windll.kernel32                            # type: ignore[attr-defined]
        snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if snap in (0, -1):
            return
        try:
            entry = THREADENTRY32()
            entry.dwSize = ctypes.sizeof(THREADENTRY32)
            ok = k.Thread32First(snap, ctypes.byref(entry))
            while ok:
                if entry.th32OwnerProcessID == pid:
                    h = k.OpenThread(THREAD_SUSPEND_RESUME, False,
                                     entry.th32ThreadID)
                    if h:
                        if suspend:
                            k.SuspendThread(h)
                        else:
                            k.ResumeThread(h)
                        k.CloseHandle(h)
                ok = k.Thread32Next(snap, ctypes.byref(entry))
        finally:
            k.CloseHandle(snap)

    def stop(self) -> tuple[int, str]:
        if not self._proc:
            return 0, ""
        try:
            if self._paused:
                self.resume()
            # Ask FFmpeg to flush its trailer by sending 'q' on stdin.
            try:
                self._proc.stdin.write(b"q")
                self._proc.stdin.flush()
            except (OSError, ValueError):
                pass
            try:
                self._proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if IS_WINDOWS:
                    try:
                        self._proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                    except (OSError, ValueError, AttributeError):
                        pass
                else:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
                try:
                    self._proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    if IS_WINDOWS:
                        self._proc.kill()
                    else:
                        os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                    self._proc.wait()
            err = ""
            if self._proc.stderr:
                err = self._proc.stderr.read().decode("utf-8", errors="ignore")
            code = self._proc.returncode or 0
            return code, err
        finally:
            self._proc = None
            self._cfg = None
            self._paused = False

    def is_recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_paused(self) -> bool:
        return self._paused

    def preview_command(self, cfg: RecordConfig) -> str:
        if IS_WINDOWS:
            return subprocess.list2cmdline(self.build_command(cfg))
        return " ".join(shlex.quote(p) for p in self.build_command(cfg))
