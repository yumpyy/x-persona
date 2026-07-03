from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, DataTable


class HelpOverlay(ModalScreen):
    """Keybindings reference overlay."""

    def compose(self) -> ComposeResult:
        yield Static("[bold]Keyboard Shortcuts[/]", classes="help-title")
        table = DataTable()
        table.add_columns("Key", "Scope", "Action")
        table.add_rows([
            ("Tab / Shift+Tab", "Detail", "Cycle personas"),
            ("Esc", "Detail", "Close detail / go back"),
            ("S", "Per-persona", "Start / Stop selected persona"),
            ("K", "Per-persona", "Kill (force stop worker)"),
            ("I", "Per-persona", "Manual intervene"),
            ("R", "Per-persona", "Refresh"),
            ("O", "Per-persona", "Enter compose mode (inline footer)"),
            ("G / C / Esc", "Compose", "Generate / Custom / Cancel"),
            ("C", "Per-persona", "Open config in editor"),
            ("H", "Per-persona", "History browser"),
            ("Drag handles", "Detail", "Resize sections (mouse)"),
            ("?", "Global", "Help overlay"),
            ("Q", "Global", "Quit"),
        ])
        yield table
        yield Static("Press any key to close", classes="help-footer")

    def on_key(self, event) -> None:
        self.app.pop_screen()
