from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Switch, Select, Button, Static, Label
from textual.containers import Horizontal, Vertical


class SettingsScreen(ModalScreen):
    """Runtime settings editor."""

    def compose(self) -> ComposeResult:
        store = self.app.store  # type: ignore
        s = store.settings
        yield Vertical(
            Static("[bold]Runtime Settings[/]", classes="settings-title"),
            Horizontal(
                Label("Scroll limit:"), Input(str(s.scroll_limit), id="set-scroll-limit"), classes="settings-row"
            ),
            Horizontal(
                Label("Break min (s):"), Input(str(s.break_min), id="set-break-min"), classes="settings-row"
            ),
            Horizontal(
                Label("Break max (s):"), Input(str(s.break_max), id="set-break-max"), classes="settings-row"
            ),
            Horizontal(
                Label("Min action delay (s):"), Input(str(s.min_action_delay), id="set-min-action"), classes="settings-row"
            ),
            Horizontal(
                Label("Max action delay (s):"), Input(str(s.max_action_delay), id="set-max-action"), classes="settings-row"
            ),
            Horizontal(
                Label("Min scroll delay (s):"), Input(str(s.min_scroll_delay), id="set-min-scroll"), classes="settings-row"
            ),
            Horizontal(
                Label("Max scroll delay (s):"), Input(str(s.max_scroll_delay), id="set-max-scroll"), classes="settings-row"
            ),
            Horizontal(
                Label("Approval mode:"),
                Switch(value=s.approval_mode, id="set-approval"),
                classes="settings-row",
            ),
            Horizontal(
                Label("Log verbosity:"),
                Select(
                    [(v, v) for v in ("debug", "info", "error")],
                    value=s.log_verbosity,
                    id="set-verbosity",
                    allow_blank=False,
                ),
                classes="settings-row",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-settings"),
                Button("Cancel", variant="default", id="cancel-settings"),
                classes="settings-buttons",
            ),
            id="settings-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self._save()
        self.app.pop_screen()

    def _save(self) -> None:
        from x_personas.tui.store import AppSettings
        s = self.app.store.settings
        try:
            s.scroll_limit = int(self.query_one("#set-scroll-limit", Input).value)
            s.break_min = int(self.query_one("#set-break-min", Input).value)
            s.break_max = int(self.query_one("#set-break-max", Input).value)
            s.min_action_delay = int(self.query_one("#set-min-action", Input).value)
            s.max_action_delay = int(self.query_one("#set-max-action", Input).value)
            s.min_scroll_delay = int(self.query_one("#set-min-scroll", Input).value)
            s.max_scroll_delay = int(self.query_one("#set-max-scroll", Input).value)
            s.approval_mode = self.query_one("#set-approval", Switch).value
            s.log_verbosity = self.query_one("#set-verbosity", Select).value
            s._settings_path = self.app.store._settings_path
            self.app.store.save_settings()
        except Exception:
            pass
