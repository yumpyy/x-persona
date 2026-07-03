from __future__ import annotations

import asyncio

from textual.widgets import RichLog


class ErrorLog(RichLog):
    """Error-only log viewer with red emphasis."""

    def __init__(self, queue: asyncio.Queue, max_lines: int = 200, **kwargs) -> None:
        super().__init__(highlight=True, markup=True, max_lines=max_lines, **kwargs)
        self._queue = queue
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.5, self._drain)

    def _drain(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self.write(f"[bold #f38ba8]{msg}[/]")
                self.scroll_end(animate=False)
        except asyncio.QueueEmpty:
            pass

    def clear_log(self) -> None:
        self.clear()

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.cancel()
