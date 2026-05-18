"""Settings persistence layer for Visio Eye."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


IS_WINDOWS = sys.platform.startswith("win")


def _default_videos_dir() -> Path:
    if IS_WINDOWS:
        userprofile = os.environ.get("USERPROFILE") or str(Path.home())
        return Path(userprofile) / "Videos" / "VisioEye"
    return Path.home() / "Videos" / "VisioEye"


def _default_config_dir() -> Path:
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "VisioEye"
    return Path.home() / ".config" / "visio-eye"


_DEFAULT_CAMERA = "" if IS_WINDOWS else "/dev/video0"


DEFAULT_SETTINGS: dict[str, Any] = {
    "general": {
        "language": "uz",
        "theme": "dark",
        "start_with_system": False,
    },
    "video": {
        "fps": 30,
        "resolution": "1080p",
        "encoder": "CPU",
        "bitrate": "Auto",
        "codec": "H264",
        "format": "mp4",
        "capture_mode": "fullscreen",
        "monitor": 0,
    },
    "audio": {
        "source": "both",
        "mic_volume": 80,
        "desktop_volume": 80,
        "noise_suppression": True,
        "echo_cancellation": True,
        "quality_kbps": 192,
        "mic_device": "default",
        "desktop_device": "default",
    },
    "camera": {
        "enabled": False,
        "device": _DEFAULT_CAMERA,
        "position": "bottom_right",
        "custom_x": 20,
        "custom_y": 20,
        "width": 240,
        "height": 180,
        "border_radius": 16,
        "shadow": True,
        "opacity": 100,
    },
    "logo": {
        "enabled": False,
        "path": "",
        "position": "top_right",
        "custom_x": 20,
        "custom_y": 20,
        "width": 120,
        "height": 120,
        "opacity": 90,
    },
    "output": {
        "folder": str(_default_videos_dir()),
        "filename_template": "record_{Y}_{M}_{D}_{h}_{m}_{s}",
    },
    "hotkeys": {
        "start": "F9",
        "pause": "F10",
        "resume": "F10",
        "stop": "F11",
        "screenshot": "F12",
    },
    "dubbing": {
        "enabled": False,
        "source_languages": ["en", "ru"],
        "target_language": "uz",
        "voice": "uz-UZ-MadinaNeural",
        "asr_model": "large-v3",          # base | small | medium | large-v3
        "asr_device": "cuda",             # cuda | cpu
        "asr_compute": "int8_float16",    # int8_float16 | int8 | float16 | float32
        "translator": "auto",             # auto | yandex | google
        "yandex_api_key": "",
        "yandex_folder_id": "",
        "chunk_seconds": 3.0,
    },
    "streaming": {
        "enabled": False,
        "targets": [],          # list of {"platform":"youtube","url":"rtmp://...","key":"..."}
        "bitrate_kbps": 4500,
        "keyframe_seconds": 2,
        "audio_kbps": 160,
    },
    "html_overlay": {
        "enabled": False,
        "html": (
            "<!doctype html>\n"
            "<html><head><meta charset=\"utf-8\">\n"
            "<style>\n"
            "  body { margin:0; background:transparent;\n"
            "         font-family:'Segoe UI',sans-serif; color:#fff; }\n"
            "  .badge { display:inline-block; padding:8px 16px;\n"
            "           background:linear-gradient(135deg,#3b82f6,#06b6d4);\n"
            "           border-radius:10px; font-weight:800;\n"
            "           box-shadow:0 8px 22px rgba(59,130,246,.45); }\n"
            "</style></head>\n"
            "<body><div class=\"badge\">LIVE · Visio Eye</div></body></html>"
        ),
        "x": 40,
        "y": 40,
        "width": 480,
        "height": 200,
        "click_through": True,
        "transparent_background": True,
    },
}


class SettingsManager:
    """Loads and saves settings to ~/.config/visio-eye/settings.json."""

    def __init__(self) -> None:
        self._config_dir = _default_config_dir()
        self._config_file = self._config_dir / "settings.json"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self._config_file.exists():
            try:
                with self._config_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = self._merge(DEFAULT_SETTINGS, loaded)
                return
            except (OSError, json.JSONDecodeError):
                pass
        self._data = json.loads(json.dumps(DEFAULT_SETTINGS))
        self.save()

    def save(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._config_file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._config_file)

    def get(self, section: str, key: str | None = None, default: Any = None) -> Any:
        if key is None:
            return self._data.get(section, default)
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        self._data.setdefault(section, {})[key] = value

    def set_section(self, section: str, values: dict[str, Any]) -> None:
        self._data[section] = {**self._data.get(section, {}), **values}

    def all(self) -> dict[str, Any]:
        return self._data

    @staticmethod
    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = json.loads(json.dumps(base))
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = SettingsManager._merge(result[k], v)
            else:
                result[k] = v
        return result
