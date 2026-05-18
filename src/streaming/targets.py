"""Per-platform RTMP base URLs + helpers.

YouTube / Facebook / Twitch / Telegram all accept RTMP ingest from
FFmpeg directly. Instagram does not have a public RTMP endpoint —
users typically route through Yellow Duck or InstaFeed, so we expose
a "custom RTMP" target for that case.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StreamTarget:
    platform: str          # 'youtube' | 'facebook' | 'twitch' | 'telegram' | 'custom'
    base_url: str          # rtmp://...   (without trailing key)
    stream_key: str        # platform-supplied secret key
    enabled: bool = True


PLATFORM_PRESETS: dict[str, dict[str, str]] = {
    "youtube": {
        "label": "YouTube Live",
        "base_url": "rtmp://a.rtmp.youtube.com/live2",
        "help": ("YouTube Studio → Go Live → Stream key. "
                  "Paste only the key value here."),
    },
    "facebook": {
        "label": "Facebook Live",
        "base_url": "rtmps://live-api-s.facebook.com:443/rtmp",
        "help": ("Facebook → Live Producer → 'Use Stream Key'. "
                  "Copy the persistent stream key."),
    },
    "twitch": {
        "label": "Twitch",
        "base_url": "rtmp://live.twitch.tv/app",
        "help": ("dashboard.twitch.tv → Settings → Stream → Primary "
                  "Stream Key."),
    },
    "telegram": {
        "label": "Telegram Live",
        "base_url": "",           # user pastes full URL from channel "Start Live"
        "help": ("Telegram channel → Start Live Stream → 'Start "
                  "Streaming With...'. Copy BOTH the URL and Key."),
    },
    "instagram": {
        "label": "Instagram (via Yellow Duck / InstaFeed)",
        "base_url": "",
        "help": ("Instagram has no native RTMP. Use a relay tool like "
                  "Yellow Duck to expose a local RTMP URL, paste it here."),
    },
    "custom": {
        "label": "Custom RTMP",
        "base_url": "",
        "help": "Any RTMP/RTMPS URL accepted by your service.",
    },
}


def build_rtmp_url(target: StreamTarget) -> str:
    """Concatenate base + key with a slash, handling empty fields."""
    base = (target.base_url or "").rstrip("/")
    key = (target.stream_key or "").strip()
    if not base and key.lower().startswith(("rtmp://", "rtmps://")):
        # user pasted full URL into the 'key' field — accept it
        return key
    if not base:
        return ""
    if not key:
        return base
    return f"{base}/{key}"


def validate_target(target: StreamTarget) -> tuple[bool, str]:
    """Return (ok, reason). Empty reason on success."""
    if not target.enabled:
        return False, "disabled"
    url = build_rtmp_url(target)
    if not url:
        return False, "missing url/key"
    if not url.startswith(("rtmp://", "rtmps://")):
        return False, "url must start with rtmp:// or rtmps://"
    return True, ""
