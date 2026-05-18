"""Microsoft Edge TTS — free, 4 Uzbek neural voices, studio quality.

Voices supported by Microsoft for uz-UZ:
  - uz-UZ-MadinaNeural    (Female)
  - uz-UZ-SardorNeural    (Male)

We synthesise to PCM 24 kHz mono and return raw bytes.  The audio
router pipes those bytes into the visio-eye-dub virtual sink.
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


UZ_VOICES = {
    "madina": "uz-UZ-MadinaNeural",
    "sardor": "uz-UZ-SardorNeural",
}
DEFAULT_VOICE = "uz-UZ-MadinaNeural"


class EdgeTTS:
    """Lightweight wrapper around edge-tts. Each call yields PCM bytes.

    Network is required; the cloud endpoint is anonymous (no key).
    """

    def __init__(self, voice: str = DEFAULT_VOICE,
                 rate: str = "+0%", volume: str = "+0%") -> None:
        try:
            import edge_tts                          # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "edge-tts missing. pip install edge-tts"
            ) from e
        self.voice = voice if voice.startswith("uz-UZ-") else UZ_VOICES.get(
            voice.lower(), DEFAULT_VOICE
        )
        self.rate = rate
        self.volume = volume

    async def _synth_async(self, text: str) -> bytes:
        import edge_tts
        if not text.strip():
            return b""
        com = edge_tts.Communicate(text, self.voice,
                                    rate=self.rate, volume=self.volume)
        buf = io.BytesIO()
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    def synth(self, text: str) -> bytes:
        """Synchronous synth -> MP3 bytes (Edge default)."""
        try:
            return asyncio.run(self._synth_async(text))
        except RuntimeError:
            # already inside a running loop; create a new one in a thread
            import threading
            result: dict[str, bytes] = {}
            def _runner() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result["b"] = loop.run_until_complete(self._synth_async(text))
                finally:
                    loop.close()
            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout=20)
            return result.get("b", b"")

    @staticmethod
    def list_uz_voices() -> list[tuple[str, str]]:
        """[(id, label)] for the UI."""
        return [
            ("uz-UZ-MadinaNeural", "Madina (ayol ovozi)"),
            ("uz-UZ-SardorNeural", "Sardor (erkak ovozi)"),
        ]
