"""High-level recorder that picks the right backend (FFmpeg / Wayland portal)
based on the running display server, and converts settings into a config."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Optional

from .ffmpeg_handler import FFmpegRecorder, RecordConfig

if sys.platform.startswith("linux"):
    from .wayland_recorder import WaylandPortalRecorder
else:                                                # pragma: no cover - non-linux
    WaylandPortalRecorder = None                      # type: ignore[assignment]


class ScreenRecorder:
    """Auto-selects FFmpeg (X11 / Windows) or Wayland portal backend."""

    def __init__(self) -> None:
        self.engine_ffmpeg = FFmpegRecorder()
        self.engine_wayland = (
            WaylandPortalRecorder() if WaylandPortalRecorder is not None else None
        )
        self.backend: str = "ffmpeg"
        self._active = None
        self.last_output: Optional[str] = None

    def _select_backend(self):
        if (
            WaylandPortalRecorder is not None
            and self.engine_wayland is not None
            and WaylandPortalRecorder.is_wayland()
        ):
            ok, _msg = WaylandPortalRecorder.available()
            if ok:
                self.backend = "wayland"
                return self.engine_wayland
        self.backend = "ffmpeg"
        return self.engine_ffmpeg

    @staticmethod
    def generate_filename(folder: str, template: str, container: str) -> str:
        now = datetime.datetime.now()
        name = template.format(
            Y=now.strftime("%Y"),
            M=now.strftime("%m"),
            D=now.strftime("%d"),
            h=now.strftime("%H"),
            m=now.strftime("%M"),
            s=now.strftime("%S"),
        )
        path = Path(folder).expanduser() / f"{name}.{container}"
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def start_from_settings(self, settings: dict,
                            region: tuple[int, int, int, int] | None = None) -> str:
        v = settings["video"]
        a = settings["audio"]
        c = settings["camera"]
        l_ = settings["logo"]
        o = settings["output"]
        st = settings.get("streaming") or {}

        out_path = self.generate_filename(
            o["folder"], o["filename_template"], v.get("format", "mp4")
        )

        # ---- streaming URLs ----
        # Be forgiving: if the user enabled at least one target but
        # forgot to flip the global toggle, still stream (matches
        # OBS / Streamlabs UX where per-target check is enough).
        stream_urls: list[str] = []
        targets_raw = list(st.get("targets") or [])
        any_target_on = any(bool(t.get("enabled")) for t in targets_raw)
        if st.get("enabled") or any_target_on:
            from streaming import build_rtmp_url, validate_target, StreamTarget
            for t in targets_raw:
                tgt = StreamTarget(
                    platform=t.get("platform", "custom"),
                    base_url=t.get("url", ""),
                    stream_key=t.get("key", ""),
                    enabled=bool(t.get("enabled", True)),
                )
                ok, _ = validate_target(tgt)
                if ok:
                    stream_urls.append(build_rtmp_url(tgt))

        cfg = RecordConfig(
            output_path=out_path,
            resolution=v.get("resolution", "1080p"),
            fps=int(v.get("fps", 30)),
            codec=v.get("codec", "H264"),
            container=v.get("format", "mp4"),
            bitrate=v.get("bitrate", "Auto"),
            encoder=v.get("encoder", "CPU"),
            audio_source=a.get("source", "both"),
            audio_kbps=int(a.get("quality_kbps", 192)),
            mic_device=a.get("mic_device", "default"),
            desktop_device=a.get("desktop_device", "default"),
            noise_suppression=bool(a.get("noise_suppression", True)),
            echo_cancellation=bool(a.get("echo_cancellation", True)),
            capture_mode=v.get("capture_mode", "fullscreen"),
            capture_region=region,
            monitor_index=int(v.get("monitor", 0)),
            camera_enabled=bool(c.get("enabled", False)),
            camera_device=c.get("device", "/dev/video0"),
            camera_position=c.get("position", "bottom_right"),
            camera_custom=(int(c.get("custom_x", 20)), int(c.get("custom_y", 20))),
            camera_size=(int(c.get("width", 240)), int(c.get("height", 180))),
            camera_opacity=int(c.get("opacity", 100)),
            logo_enabled=bool(l_.get("enabled", False)),
            logo_path=l_.get("path", ""),
            logo_position=l_.get("position", "top_right"),
            logo_custom=(int(l_.get("custom_x", 20)), int(l_.get("custom_y", 20))),
            logo_size=(int(l_.get("width", 120)), int(l_.get("height", 120))),
            logo_opacity=int(l_.get("opacity", 90)),
            stream_urls=stream_urls,
            stream_bitrate_kbps=int(st.get("bitrate_kbps", 4500)),
            stream_keyint_sec=int(st.get("keyframe_seconds", 2)),
            stream_audio_kbps=int(st.get("audio_kbps", 160)),
        )

        engine = self._select_backend()
        engine.start(cfg)
        self._active = engine
        self.last_output = out_path
        return out_path

    def pause(self) -> None:
        if self._active:
            self._active.pause()

    def resume(self) -> None:
        if self._active:
            self._active.resume()

    def stop(self) -> tuple[int, str]:
        if not self._active:
            return 0, ""
        code, err = self._active.stop()
        self._active = None
        return code, err

    def is_recording(self) -> bool:
        return self._active is not None and self._active.is_recording()

    def is_paused(self) -> bool:
        return self._active is not None and self._active.is_paused()
