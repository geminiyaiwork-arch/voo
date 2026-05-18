"""High-level orchestrator that wires ASR -> Translate -> TTS -> Router.

Threading model:
  * Capture thread (parec) produces ~3-sec PCM chunks -> queue_asr
  * ASR thread pulls from queue_asr, runs Whisper -> queue_translate
  * Translate+TTS+Play thread pulls from queue_translate, hits Yandex
    -> Edge TTS -> AudioRouter

Each stage is isolated so a slow Whisper call doesn't starve the
capture, and we keep the GIL-friendly bits in I/O-bound threads.

When stopped, all threads drain and exit; the virtual sink is unloaded.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from .asr_whisper import WhisperASR, ASRSegment
from .audio_capture import MonitorCapture
from .audio_router import AudioRouter, MONITOR_SOURCE
from .translator import Translator, build_translator
from .tts_edge import EdgeTTS, DEFAULT_VOICE

logger = logging.getLogger(__name__)


@dataclass
class DubbingConfig:
    enabled: bool = False
    asr_model: str = "large-v3"           # or 'medium', 'small', 'base'
    asr_device: str = "cuda"              # 'cuda' | 'cpu'
    asr_compute: str = "int8_float16"     # 'int8_float16'|'int8'|'float16'|'float32'
    languages: tuple[str, ...] = ("en", "ru")    # which source langs to dub
    target_lang: str = "uz"
    voice: str = DEFAULT_VOICE
    translator: str = "auto"              # 'auto' | 'yandex' | 'google'
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    chunk_seconds: float = 3.0
    min_confidence: float = -1.2          # avg_logprob cutoff
    captions: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class DubbingEvent:
    """Posted to the UI for live transcript display."""
    timestamp: float
    src_lang: str
    src_text: str
    tgt_text: str


class DubbingEngine:
    """Coordinator. Use start(cfg) / stop().

    Subscribe to events via ``set_event_callback(fn)``. The callback is
    invoked from a worker thread; marshal to Qt's thread yourself.
    """

    def __init__(self) -> None:
        self._cfg: Optional[DubbingConfig] = None
        self._capture: Optional[MonitorCapture] = None
        self._router: Optional[AudioRouter] = None
        self._asr: Optional[WhisperASR] = None
        self._tts: Optional[EdgeTTS] = None
        self._translator: Optional[Translator] = None

        self._q_asr: queue.Queue[np.ndarray] = queue.Queue(maxsize=20)
        self._q_tts: queue.Queue[tuple[str, str, str]] = queue.Queue(maxsize=20)

        self._stop = threading.Event()
        self._th_asr: Optional[threading.Thread] = None
        self._th_tts: Optional[threading.Thread] = None

        self._event_cb: Optional[Callable[[DubbingEvent], None]] = None
        self.monitor_source: Optional[str] = None
        self.running = False

    # ------- public -------
    def set_event_callback(self, fn: Callable[[DubbingEvent], None]) -> None:
        self._event_cb = fn

    def start(self, cfg: DubbingConfig) -> str:
        """Bring all stages up. Returns the monitor source name that the
        recorder should capture for audio."""
        if self.running:
            raise RuntimeError("DubbingEngine already running")
        self._cfg = cfg

        self._router = AudioRouter()
        self.monitor_source = self._router.start()

        self._capture = MonitorCapture(chunk_seconds=cfg.chunk_seconds)
        self._asr = WhisperASR(
            model_size=cfg.asr_model,
            device=cfg.asr_device,
            compute_type=cfg.asr_compute,
        )
        self._tts = EdgeTTS(voice=cfg.voice)
        self._translator = build_translator(
            prefer=cfg.translator,
            yandex_key=cfg.yandex_api_key or None,
            yandex_folder=cfg.yandex_folder_id or None,
        )

        self._stop.clear()
        self._th_asr = threading.Thread(target=self._asr_loop, daemon=True,
                                         name="dub-asr")
        self._th_tts = threading.Thread(target=self._tts_loop, daemon=True,
                                         name="dub-tts")
        self._th_asr.start()
        self._th_tts.start()
        self._capture.start(self._on_audio_chunk)

        self.running = True
        logger.info("DubbingEngine running (monitor: %s)", self.monitor_source)
        return self.monitor_source

    def stop(self) -> None:
        if not self.running:
            return
        self._stop.set()
        if self._capture is not None:
            self._capture.stop()
        # drain queues with sentinels so threads exit promptly
        try:
            self._q_asr.put_nowait(None)            # type: ignore[arg-type]
        except queue.Full:
            pass
        try:
            self._q_tts.put_nowait(None)            # type: ignore[arg-type]
        except queue.Full:
            pass
        for th in (self._th_asr, self._th_tts):
            if th is not None:
                th.join(timeout=3)
        if self._router is not None:
            self._router.stop()
        self.running = False
        logger.info("DubbingEngine stopped")

    # ------- internal -------
    def _on_audio_chunk(self, samples: np.ndarray) -> None:
        # Drop oldest if the ASR queue is saturated — better than blocking
        # the capture thread and creating drift.
        try:
            self._q_asr.put_nowait(samples)
        except queue.Full:
            try:
                _ = self._q_asr.get_nowait()
            except queue.Empty:
                pass
            try:
                self._q_asr.put_nowait(samples)
            except queue.Full:
                pass

    def _asr_loop(self) -> None:
        assert self._cfg is not None
        assert self._asr is not None
        langs = set(self._cfg.languages)
        while not self._stop.is_set():
            try:
                chunk = self._q_asr.get(timeout=0.5)
            except queue.Empty:
                continue
            if chunk is None:
                break
            # silence skip
            if float(np.abs(chunk).mean()) < 1e-4:
                continue
            try:
                segs = self._asr.transcribe(chunk, sample_rate=16000)
            except Exception:                       # pylint: disable=broad-except
                logger.exception("Whisper transcribe failed")
                continue
            for seg in segs:
                if seg.confidence < self._cfg.min_confidence:
                    continue
                if seg.language not in langs:
                    continue
                if not seg.text.strip():
                    continue
                try:
                    self._q_tts.put_nowait((seg.language, seg.text,
                                            self._cfg.target_lang))
                except queue.Full:
                    pass

    def _tts_loop(self) -> None:
        assert self._cfg is not None
        assert self._translator is not None
        assert self._tts is not None
        assert self._router is not None
        while not self._stop.is_set():
            try:
                item = self._q_tts.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            src_lang, src_text, tgt_lang = item
            t0 = time.monotonic()
            try:
                tgt_text = self._translator.translate(
                    src_text, src=src_lang, tgt=tgt_lang
                )
            except Exception:                       # pylint: disable=broad-except
                logger.exception("Translate failed")
                continue
            if not tgt_text:
                continue
            try:
                mp3 = self._tts.synth(tgt_text)
            except Exception:                       # pylint: disable=broad-except
                logger.exception("TTS failed")
                continue
            try:
                self._router.play_mp3_bytes(mp3)
            except Exception:                       # pylint: disable=broad-except
                logger.exception("TTS playback failed")
                continue
            logger.debug("dubbed in %.2fs : %s -> %s",
                         time.monotonic() - t0, src_text, tgt_text)
            if self._event_cb is not None:
                try:
                    self._event_cb(DubbingEvent(
                        timestamp=time.time(),
                        src_lang=src_lang,
                        src_text=src_text,
                        tgt_text=tgt_text,
                    ))
                except Exception:                   # pylint: disable=broad-except
                    pass
