from __future__ import annotations

from datetime import datetime, timezone

_QUIET = False


def set_quiet(v: bool) -> None:
    global _QUIET
    _QUIET = v


def log(msg: str) -> None:
    if _QUIET:
        return
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
