from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, Switch


class PersonaSettingsScreen(ModalScreen):
    """Per-persona runtime flags — ask (approval mode) and visible (headless toggle)."""

    def __init__(self, persona_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._persona_name = persona_name

    def compose(self) -> ComposeResult:
        info = self.app.store.get_persona(self._persona_name)
        yield Vertical(
            Static(f"[bold]Persona Settings — {self._persona_name}[/]", classes="settings-title"),
            Horizontal(
                Label("Approval mode (ask before acting):"),
                Switch(value=info.ask if info else False, id="ps-ask"),
                classes="settings-row",
            ),
            Horizontal(
                Label("Show browser (visible):"),
                Switch(value=not info.headless if info else False, id="ps-visible"),
                classes="settings-row",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-ps"),
                Button("Cancel", variant="default", id="cancel-ps"),
                classes="settings-buttons",
            ),
            id="settings-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-ps":
            self._save()
        self.app.pop_screen()

    def _save(self) -> None:
        info = self.app.store.get_persona(self._persona_name)
        if not info:
            return
        info.ask = self.query_one("#ps-ask", Switch).value
        info.headless = not self.query_one("#ps-visible", Switch).value
