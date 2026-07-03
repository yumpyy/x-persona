from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical


class ActivityDetailScreen(ModalScreen):
    """Expanded view of a single activity log entry."""

    def __init__(self, data: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = data

    def compose(self) -> ComposeResult:
        d = self._data
        yield Vertical(
            Static(f"[bold]Action Detail[/]", classes="help-title"),
            Static(""),
            Static(f"[dim]Time:[/]  {d.get('timestamp', '—')}"),
            Static(f"[dim]Action:[/]  [bold]{d.get('action', '—').upper()}[/]"),
            Static(f"[dim]Target:[/]  {d.get('target', '—')}"),
            Static(f"[dim]Score:[/]  {d.get('score', '—')}"),
            Static(""),
            Static("[dim]Content:[/]"),
            Static(f"{d.get('content') or '[italic]none[/]'}"),
            Static(""),
            Static("[dim]Context / Reasoning:[/]"),
            Static(f"[italic]{d.get('context') or '[dim]n/a[/]'}[/]"),
            Static(""),
            Static("[dim]Press any key or Esc to close[/]", classes="dim"),
            id="activity-detail-dialog",
        )

    def on_key(self, event) -> None:
        self.app.pop_screen()
