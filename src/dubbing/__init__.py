"""Real-time dubbing engine: English/Russian -> Uzbek.

Pipeline:
  capture (PulseAudio monitor) -> Whisper (auto-detect) ->
  Yandex/Google Translate -> Edge TTS -> virtual PulseAudio sink
  -> recorder mixes that sink into the output file.
"""
from .pipeline import DubbingEngine, DubbingConfig
from .audio_router import AudioRouter

__all__ = ["DubbingEngine", "DubbingConfig", "AudioRouter"]
