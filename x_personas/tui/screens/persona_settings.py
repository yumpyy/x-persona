from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static


_ITEMS = [
    ("ask", "Approval mode (ask before acting)"),
    ("visible", "Show browser (visible window)"),
]


class PersonaSettingsScreen(Screen):
    """Per-persona runtime flags — keyboard-driven, no buttons."""

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("space", "toggle", "Toggle"),
        Binding("enter", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, persona_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._persona_name = persona_name
        self._cursor = 0
        self._values: dict[str, bool] = {}

    def compose(self) -> ComposeResult:
        info = self.app.store.get_persona(self._persona_name)
        self._values = {"ask": info.ask, "visible": not info.headless}
        with Vertical():
            yield Static(f"[#89b4fa bold]Persona Settings — {self._persona_name}[/]", id="ps-title")
            yield Static(self._item_line(0), id="ps-item-0")
            yield Static(self._item_line(1), id="ps-item-1")
            yield Static("[#6c7086]↑↓: move  Space: toggle  Enter: save  Esc: cancel[/]", id="ps-hint")

    def _item_line(self, idx: int) -> str:
        key, label = _ITEMS[idx]
        cursor = "[#89b4fa]→[/]" if idx == self._cursor else " "
        checked = "[#a6e3a1][x][/]" if self._values[key] else "[#6c7086][ ][/]"
        return f" {cursor} {checked}  {label}"

    def _refresh(self) -> None:
        self.query_one("#ps-item-0", Static).update(self._item_line(0))
        self.query_one("#ps-item-1", Static).update(self._item_line(1))

    def action_cursor_up(self) -> None:
        self._cursor = max(0, self._cursor - 1)
        self._refresh()

    def action_cursor_down(self) -> None:
        self._cursor = min(len(_ITEMS) - 1, self._cursor + 1)
        self._refresh()

    def action_toggle(self) -> None:
        key = _ITEMS[self._cursor][0]
        self._values[key] = not self._values[key]
        self._refresh()

    def action_save(self) -> None:
        info = self.app.store.get_persona(self._persona_name)
        if info:
            info.ask = self._values["ask"]
            info.headless = not self._values["visible"]
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
