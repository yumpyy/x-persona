from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

_QUIET = False
_log_sinks: list[Callable[[str], None]] = []


def set_quiet(v: bool) -> None:
    global _QUIET
    _QUIET = v


def add_sink(fn: Callable[[str], None]) -> None:
    _log_sinks.append(fn)


def remove_sink(fn: Callable[[str], None]) -> None:
    try:
        _log_sinks.remove(fn)
    except ValueError:
        pass


def clear_sinks() -> None:
    _log_sinks.clear()


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    if not _QUIET:
        print(formatted)
    for sink in _log_sinks:
        sink(formatted)
