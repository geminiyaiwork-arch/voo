"""Translator clients.

Default: Yandex Translate (best Uzbek support, ru->uz exceptional, free
tier 1M chars/month after enabling on console.cloud.yandex.com).

Fallback: deep_translator -> GoogleTranslator (no API key, scraped from
the public translate.google.com endpoint — works but rate-limited).

The choice is made at construction time so the rest of the pipeline
stays oblivious.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, src: str, tgt: str = "uz") -> str: ...


class GoogleFreeTranslator(Translator):
    """No API key. Uses deep-translator's scraping endpoint."""

    def __init__(self) -> None:
        try:
            from deep_translator import GoogleTranslator
        except ImportError as e:
            raise RuntimeError(
                "deep-translator missing. pip install deep-translator"
            ) from e
        self._GoogleTranslator = GoogleTranslator
        # cache instances per (src, tgt) pair
        self._cache: dict[tuple[str, str], object] = {}

    def translate(self, text: str, src: str, tgt: str = "uz") -> str:
        if not text.strip():
            return ""
        key = (src, tgt)
        if key not in self._cache:
            self._cache[key] = self._GoogleTranslator(source=src, target=tgt)
        try:
            return (self._cache[key].translate(text) or "").strip()
        except Exception as exc:                    # pylint: disable=broad-except
            logger.warning("Google translate failed: %s", exc)
            return ""


class YandexTranslator(Translator):
    """Yandex Cloud Translate v2. Requires an API key (IAM token or
    folder-id + API key). Provides excellent ru->uz / en->uz quality."""

    URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    def __init__(self, api_key: str, folder_id: str | None = None) -> None:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx missing. pip install httpx") from e
        self._httpx = httpx
        self._api_key = api_key
        self._folder_id = folder_id
        self._client = httpx.Client(timeout=10.0)

    def translate(self, text: str, src: str, tgt: str = "uz") -> str:
        if not text.strip():
            return ""
        payload = {
            "sourceLanguageCode": src,
            "targetLanguageCode": tgt,
            "texts": [text],
        }
        if self._folder_id:
            payload["folderId"] = self._folder_id
        try:
            r = self._client.post(
                self.URL,
                headers={"Authorization": f"Api-Key {self._api_key}"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return (data["translations"][0]["text"] or "").strip()
        except Exception as exc:                    # pylint: disable=broad-except
            logger.warning("Yandex translate failed: %s", exc)
            return ""


def build_translator(prefer: str = "auto",
                     yandex_key: Optional[str] = None,
                     yandex_folder: Optional[str] = None) -> Translator:
    """Factory.

    ``prefer`` is one of: 'yandex' | 'google' | 'auto'.
    With 'auto' we use Yandex if a key is given (best Uzbek), else
    fall back to Google free.
    """
    key = yandex_key or os.environ.get("YANDEX_API_KEY")
    folder = yandex_folder or os.environ.get("YANDEX_FOLDER_ID")
    if prefer == "yandex" or (prefer == "auto" and key):
        if not key:
            raise RuntimeError("Yandex API key required for prefer=yandex")
        return YandexTranslator(key, folder)
    return GoogleFreeTranslator()
