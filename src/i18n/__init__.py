"""Lightweight i18n layer for Visio Eye.

We keep everything in a single Python dict (``translations.py``) keyed
by short slugs.  The application picks the language at boot from
settings and calls ``set_language()``.  After that, every string in
the UI is wrapped with ``tr("slug")`` which looks up the live
dictionary; missing keys fall back to the English value, then to the
raw slug, so partially-translated UIs degrade gracefully.

Switching languages at runtime requires a restart — Qt widgets cache
their captions when constructed, so a full app restart is by far the
simplest path and the one used here.
"""
from __future__ import annotations

from typing import Dict

from .translations import TRANSLATIONS


_current: str = "en"
_dicts: Dict[str, Dict[str, str]] = dict(TRANSLATIONS)


def supported_languages() -> list[tuple[str, str]]:
    """[(code, label_in_its_own_language)] for the Settings dialog."""
    return [
        ("uz", "O'zbekcha"),
        ("ru", "Русский"),
        ("en", "English"),
    ]


def set_language(code: str) -> None:
    global _current                       # pylint: disable=global-statement
    if code in _dicts:
        _current = code
    else:
        _current = "en"


def current_language() -> str:
    return _current


def tr(key: str) -> str:
    """Resolve ``key`` in current language; fall back to en, then key."""
    d = _dicts.get(_current) or {}
    if key in d and d[key]:
        return d[key]
    en = _dicts.get("en") or {}
    if key in en and en[key]:
        return en[key]
    return key
