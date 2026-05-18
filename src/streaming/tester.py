"""Quick connectivity probe for an RTMP / RTMPS target.

We push a 2-second synthetic colour-bar pattern via FFmpeg's `lavfi`
test source.  If FFmpeg exits cleanly we know the URL + key are
valid and the server accepted the publish.  Anything else (timeout,
non-zero exit, RTMP auth error) is bubbled up as a human-readable
message.
"""
from __future__ import annotations

import subprocess
from typing import Tuple


def test_rtmp_target(url: str, timeout_sec: float = 12.0) -> Tuple[bool, str]:
    """Return (ok, message)."""
    if not url:
        return False, "URL is empty"
    if not url.startswith(("rtmp://", "rtmps://")):
        return False, "URL must start with rtmp:// or rtmps://"

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=30",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
        "-t", "2",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-g", "30",
        "-c:a", "aac", "-b:a", "96k",
        "-f", "flv", url,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout_sec,
        )
    except FileNotFoundError:
        return False, "FFmpeg not installed"
    except subprocess.TimeoutExpired:
        return False, ("Timed out after %.0fs — server unreachable or "
                       "stream key wrong" % timeout_sec)

    if proc.returncode == 0:
        return True, "Connected — server accepted the stream"

    err = (proc.stderr or "").strip()
    salient = ""
    for line in err.splitlines():
        low = line.lower()
        if any(k in low for k in ("error", "failed", "refused",
                                    "unable", "denied", "auth")):
            salient = line.strip()
            break
    if not salient:
        salient = err.splitlines()[-1] if err else f"exit code {proc.returncode}"
    return False, salient[:300]
