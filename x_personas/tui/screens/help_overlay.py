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
            ("↑/↓", "Sidebar", "Previous / next persona"),
            ("Enter", "Sidebar", "Start / Stop selected persona"),
            ("Esc", "Global", "Exit compose / flags / detail"),
            ("S", "Persona", "Start / Stop selected persona"),
            ("K", "Persona", "Kill (force stop worker)"),
            ("I", "Persona", "Manual intervene"),
            ("R", "Persona", "Refresh view"),
            ("O", "Persona", "Enter compose mode (inline footer)"),
            ("G / C / Esc", "Compose", "Generate (LLM) / Custom (editor) / Cancel"),
            ("E", "Persona", "Toggle inline flags (ask / visible)"),
            ("↑/↓ / Space / Esc", "Flags", "Pick / Toggle / Done"),
            ("C", "Persona", "Open config in editor"),
            ("H", "Persona", "History browser"),
            ("F", "Global", "Global runtime settings"),
            ("Enter (row)", "Activity", "View entry detail"),
            ("?", "Global", "Help overlay"),
            ("Q", "Global", "Quit"),
        ])
        yield table
        yield Static("Press any key to close", classes="help-footer")

    def on_key(self, event) -> None:
        self.app.pop_screen()
