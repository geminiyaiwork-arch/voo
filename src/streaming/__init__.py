"""RTMP live-streaming targets and helpers.

Each target produces a final RTMP URL of the form ``<base>/<stream_key>``
that goes into FFmpeg's tee muxer as a parallel output. The recorder
encodes ONCE and FFmpeg duplicates the packet stream to file + each
RTMP destination.
"""
from .targets import (
    StreamTarget, PLATFORM_PRESETS, build_rtmp_url, validate_target,
)
from .tester import test_rtmp_target

__all__ = ["StreamTarget", "PLATFORM_PRESETS", "build_rtmp_url",
           "validate_target", "test_rtmp_target"]
