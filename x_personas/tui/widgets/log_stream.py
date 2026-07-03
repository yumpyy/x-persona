from __future__ import annotations

import asyncio

from textual.reactive import reactive
from textual.widgets import RichLog


class LogStream(RichLog):
    """Queue-backed real-time log viewer with color-coded levels."""

    auto_scroll: bool = reactive(True)

    def __init__(self, queue: asyncio.Queue, max_lines: int = 500, **kwargs) -> None:
        super().__init__(highlight=True, markup=True, max_lines=max_lines, **kwargs)
        self._queue = queue
        self._timer_handle = None

    def on_mount(self) -> None:
        self._timer_handle = self.set_interval(0.2, self._drain_queue)

    def _drain_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                styled = self._colorize(msg)
                self.write(styled)
        except asyncio.QueueEmpty:
            pass
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def _colorize(self, msg: str) -> str:
        lower = msg.lower()
        if "error" in lower or "fail" in lower or "exception" in lower:
            return f"[#f38ba8]{msg}[/]"
        if "error" in msg_lower:
            return f"[#f9e2af]{msg}[/]"
        if "success" in msg_lower or "published" in msg_lower or "saved" in msg_lower:
            return f"[#a6e3a1]{msg}[/]"
        if "cycle" in msg_lower:
            return f"[#cba6f7]{msg}[/]"
        return msg

    def clear_log(self) -> None:
        self.clear()

    def on_unmount(self) -> None:
        if self._timer_handle:
            self._timer_handle.cancel()
