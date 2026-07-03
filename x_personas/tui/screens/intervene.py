from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical


class InterveneScreen(ModalScreen):
    """Modal for manual intervention on a running persona."""

    def __init__(self, persona_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.persona_name = persona_name

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold]Intervene — {self.persona_name}[/]", classes="help-title"),
            Static(""),
            Static("  [bold]1[/]  Force original post now"),
            Static("  [bold]2[/]  Reset scroll count & re-navigate"),
            Static("  [bold]3[/]  Clear rate limits"),
            Static("  [bold]4[/]  Reset error state"),
            Static("  [bold]E[/]  View error queue"),
            Static(""),
            Static(id="intervene-result", classes="dim"),
            id="intervene-dialog",
        )

    def _info(self):
        return self.app.store.get_persona(self.persona_name)

    def _worker(self):
        return self.app._persona_workers.get(self.persona_name)

    def _result(self, msg: str) -> None:
        self.query_one("#intervene-result", Static).update(msg)

    async def key_1(self) -> None:
        """Force original post."""
        worker = self._worker()
        if not worker or not worker.is_running:
            self._result("[#f38ba8]Persona not running[/]")
            return
        worker.send_command("original_post")
        self._result("[#a6e3a1]Queued original post command.[/]")

    async def key_2(self) -> None:
        """Reset scroll count & re-navigate."""
        info = self._info()
        if not info:
            return
        worker = self._worker()
        if worker and worker.is_running:
            worker.send_command("reset_scroll")
            self._result("[#a6e3a1]Queued scroll reset & re-navigate.[/]")
        else:
            info.current_scroll = 0
            self._result("[#a6e3a1]Scroll count reset (offline).[/]")

    async def key_3(self) -> None:
        """Clear rate limits."""
        import json
        from pathlib import Path
        info = self._info()
        if not info:
            return
        path = Path(info.rate_limit_file)
        path.write_text(json.dumps({"cycle": {"like": 0, "reply": 0, "repost": 0, "quote": 0}}))
        info.rate_limits = {"like": 0, "reply": 0, "repost": 0, "quote": 0}
        self._result("[#a6e3a1]Rate limits cleared.[/]")

    async def key_4(self) -> None:
        """Reset error state."""
        info = self._info()
        if not info:
            return
        info.status = "stopped"
        info.error_message = ""
        self._result("[#a6e3a1]Error state cleared.[/]")

    async def key_e(self) -> None:
        """View error queue."""
        info = self._info()
        if not info:
            return
        errors = []
        try:
            while True:
                msg = info.error_queue.get_nowait()
                errors.append(msg)
        except Exception:
            pass
        if errors:
            lines = "\n".join(errors[-20:])  # last 20
            self._result(f"[#f9e2af]Recent errors:[/]\n{lines}")
        else:
            self._result("[#a6e3a1]No errors in queue.[/]")

    def key_escape(self) -> None:
        self.app.pop_screen()
