import sys

from .ffmpeg_handler import FFmpegRecorder
from .screen_recorder import ScreenRecorder

if sys.platform.startswith("linux"):
    from .wayland_recorder import WaylandPortalRecorder
else:                                                # pragma: no cover - non-linux
    WaylandPortalRecorder = None                      # type: ignore[assignment]
