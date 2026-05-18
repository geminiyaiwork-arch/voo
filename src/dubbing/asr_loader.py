"""Background loader for the Whisper model with a Qt progress dialog.

Loading a faster-whisper model on first launch involves downloading
~1.5 GB from the HuggingFace mirror.  We pre-fetch the snapshot with
``huggingface_hub`` so we get a real progress callback, then hand the
local cached directory to ``WhisperModel`` (which loads instantly).
"""
from __future__ import annotations

import os
import threading
from typing import Callable

# Whisper model HuggingFace repo ids that faster-whisper uses.
HF_MODEL_REPO = {
    "tiny":      "Systran/faster-whisper-tiny",
    "base":      "Systran/faster-whisper-base",
    "small":     "Systran/faster-whisper-small",
    "medium":    "Systran/faster-whisper-medium",
    "large-v2":  "Systran/faster-whisper-large-v2",
    "large-v3":  "Systran/faster-whisper-large-v3",
}

# Approximate sizes for the progress UI (bytes).
HF_MODEL_SIZE = {
    "tiny":      75 * 1024 * 1024,
    "base":     142 * 1024 * 1024,
    "small":    466 * 1024 * 1024,
    "medium":  1530 * 1024 * 1024,
    "large-v2": 3094 * 1024 * 1024,
    "large-v3": 3094 * 1024 * 1024,
}


def _cache_dir() -> str:
    """Honour HF / faster-whisper cache env vars."""
    for key in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HOME"):
        v = os.environ.get(key)
        if v:
            return v
    return os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface", "hub"
    )


def is_model_cached(model_size: str) -> bool:
    """Heuristic: does the HF cache already contain the model files?"""
    repo = HF_MODEL_REPO.get(model_size)
    if not repo:
        return False
    cache = _cache_dir()
    # snapshot path: <cache>/models--<org>--<name>/snapshots/<rev>/...
    needle = "models--" + repo.replace("/", "--")
    if not os.path.isdir(cache):
        return False
    try:
        for entry in os.listdir(cache):
            if entry == needle:
                snap_dir = os.path.join(cache, entry, "snapshots")
                if os.path.isdir(snap_dir):
                    for rev in os.listdir(snap_dir):
                        files = os.listdir(os.path.join(snap_dir, rev))
                        if any(f.startswith("model") for f in files):
                            return True
    except OSError:
        pass
    return False


def download_model(model_size: str,
                   progress_cb: Callable[[float, str], bool] | None = None
                   ) -> str:
    """Synchronously download ``model_size`` showing progress.

    ``progress_cb(fraction, status_text)`` is called periodically.
    Return False from the callback to abort.  Returns the local
    snapshot directory on success, "" on cancellation.
    """
    repo = HF_MODEL_REPO.get(model_size)
    if not repo:
        return ""
    if is_model_cached(model_size):
        if progress_cb:
            progress_cb(1.0, "Cached")
        return _resolve_snapshot(repo)

    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import tqdm as hf_tqdm
    except ImportError:
        # huggingface_hub is required by faster-whisper, so this should
        # never trigger — but if it does, fall through to a bare call
        # without progress feedback.
        from huggingface_hub import snapshot_download           # type: ignore
        hf_tqdm = None                                          # type: ignore

    total = HF_MODEL_SIZE.get(model_size, 1)
    downloaded = {"b": 0}
    aborted = {"v": False}

    class _ReportingTqdm:
        """Drop-in tqdm replacement that reports to our callback."""

        def __init__(self, *a, **kw) -> None:
            self.total = kw.get("total") or 0
            self.n = 0
            self.unit = kw.get("unit", "B")
            self.desc = kw.get("desc", "")

        def update(self, n: int = 1) -> None:
            self.n += n
            downloaded["b"] += n
            if progress_cb:
                frac = min(0.999, downloaded["b"] / max(1, total))
                mb = downloaded["b"] / (1024 * 1024)
                tmb = total / (1024 * 1024)
                ok = progress_cb(frac, f"{mb:.1f} / {tmb:.0f} MB")
                if ok is False:
                    aborted["v"] = True
                    raise KeyboardInterrupt("Download cancelled")

        def close(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            self.close()

    try:
        path = snapshot_download(
            repo_id=repo,
            tqdm_class=_ReportingTqdm,                       # type: ignore[arg-type]
        )
    except KeyboardInterrupt:
        return ""
    if progress_cb:
        progress_cb(1.0, "Downloaded")
    return path


def _resolve_snapshot(repo: str) -> str:
    cache = _cache_dir()
    snap_root = os.path.join(cache, "models--" + repo.replace("/", "--"),
                              "snapshots")
    try:
        revs = sorted(os.listdir(snap_root))
        if revs:
            return os.path.join(snap_root, revs[-1])
    except OSError:
        pass
    return ""


def download_in_thread(model_size: str,
                        progress_cb: Callable[[float, str], bool],
                        done_cb: Callable[[bool], None]) -> threading.Thread:
    """Convenience: download on a daemon thread, then call done_cb(ok)."""
    def _runner() -> None:
        ok = bool(download_model(model_size, progress_cb))
        done_cb(ok)
    t = threading.Thread(target=_runner, daemon=True, name="whisper-dl")
    t.start()
    return t
