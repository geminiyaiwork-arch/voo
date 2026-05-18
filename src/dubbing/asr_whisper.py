"""Streaming ASR built on faster-whisper.

Whisper auto-detects language each call, so we don't need a separate
language-classifier. We feed it ~3-second mono float32 chunks at 16 kHz
and get back (text, language_code). The first call lazy-loads the model.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ASRSegment:
    text: str
    language: str           # 'en', 'ru', 'uz', ...
    confidence: float       # avg log-prob, ~0.5..1.0 useful
    start: float
    end: float


class WhisperASR:
    """Lazy-loaded faster-whisper wrapper."""

    def __init__(self, model_size: str = "large-v3",
                 device: str = "cuda",
                 compute_type: str = "int8_float16") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:
                raise RuntimeError(
                    "faster-whisper is not installed. "
                    "Install with: pip install faster-whisper"
                ) from e
            logger.info("Loading Whisper model: %s on %s (%s)",
                        self.model_size, self.device, self.compute_type)
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
            except Exception as exc:                # pylint: disable=broad-except
                # GPU OOM or no CUDA -> fall back to CPU int8.
                logger.warning("GPU init failed (%s); falling back to CPU int8", exc)
                self._model = WhisperModel(
                    self.model_size if self.model_size != "large-v3" else "medium",
                    device="cpu",
                    compute_type="int8",
                )

    def transcribe(self, audio: np.ndarray,
                   sample_rate: int = 16000,
                   language_hint: Optional[str] = None,
                   ) -> list[ASRSegment]:
        """Run Whisper on a mono float32 chunk."""
        self._ensure_model()
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        # Whisper expects 16k mono; resample if needed.
        if sample_rate != 16000:
            audio = _resample_linear(audio, sample_rate, 16000)

        # restrict_languages: we only want en/ru/uz transcripts.  If hint
        # is None, faster-whisper auto-detects each call.
        segments_iter, info = self._model.transcribe(
            audio,
            language=language_hint,           # None = auto-detect
            beam_size=1,                       # speed > absolute quality
            vad_filter=True,                   # silence-trim chunks
            vad_parameters={"min_silence_duration_ms": 250},
            condition_on_previous_text=False,  # safer for chunked input
        )
        lang = (info.language or "").lower()
        out: list[ASRSegment] = []
        for seg in segments_iter:
            out.append(ASRSegment(
                text=seg.text.strip(),
                language=lang,
                confidence=float(getattr(seg, "avg_logprob", 0.0)),
                start=float(seg.start or 0.0),
                end=float(seg.end or 0.0),
            ))
        return out


def _resample_linear(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Cheap linear resample. Good enough for ASR (Whisper is robust)."""
    if src_rate == dst_rate:
        return audio
    ratio = dst_rate / src_rate
    new_len = int(round(len(audio) * ratio))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)
