from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static


_FIELDS = [
    ("scroll_limit", "Scroll limit", "int", 100),
    ("break_min", "Break min (s)", "int", 60),
    ("break_max", "Break max (s)", "int", 60),
    ("min_action_delay", "Min action delay (s)", "int", 1),
    ("max_action_delay", "Max action delay (s)", "int", 1),
    ("min_scroll_delay", "Min scroll delay (s)", "int", 1),
    ("max_scroll_delay", "Max scroll delay (s)", "int", 1),
    ("approval_mode", "Approval mode (ask)", "bool", 0),
    ("log_verbosity", "Log verbosity", "select", 0),
]

_VERBOSITY = ("debug", "info", "error")


class SettingsScreen(Screen):
    """Global runtime settings — keyboard-driven, no buttons."""

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("space", "toggle", "Toggle/Cycle"),
        Binding("plus", "increment", "+"),
        Binding("minus", "decrement", "-"),
        Binding("enter", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cursor = 0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[#89b4fa bold]Runtime Settings[/]", id="set-title")
            for i in range(len(_FIELDS)):
                yield Static(self._item_line(i), id=f"set-item-{i}")
            yield Static("[#6c7086]↑↓: move  Space: toggle/cycle  +/-: adjust  Enter: save  Esc: cancel[/]", id="set-hint")

    def _item_line(self, idx: int) -> str:
        s = self.app.store.settings
        key, label, kind, _step = _FIELDS[idx]
        cursor = "[#89b4fa]→[/]" if idx == self._cursor else " "
        val = getattr(s, key)
        if kind == "bool":
            display = "[#a6e3a1][x][/]" if val else "[#6c7086][ ][/]"
        elif kind == "select":
            display = val if val in _VERBOSITY else _VERBOSITY[1]
            display = f"[#f9e2af]{display}[/]"
        else:
            display = f"[#cdd6f4]{val}[/]"
        return f" {cursor} {display}  {label}"

    def _refresh(self) -> None:
        for i in range(len(_FIELDS)):
            self.query_one(f"#set-item-{i}", Static).update(self._item_line(i))

    def _current(self) -> tuple[str, str, int]:
        return _FIELDS[self._cursor]

    def action_cursor_up(self) -> None:
        self._cursor = max(0, self._cursor - 1)
        self._refresh()

    def action_cursor_down(self) -> None:
        self._cursor = min(len(_FIELDS) - 1, self._cursor + 1)
        self._refresh()

    def action_toggle(self) -> None:
        s = self.app.store.settings
        key, _, kind, _ = self._current()
        if kind == "bool":
            setattr(s, key, not getattr(s, key))
        elif kind == "select":
            curr = getattr(s, key)
            idx = _VERBOSITY.index(curr) if curr in _VERBOSITY else 1
            setattr(s, key, _VERBOSITY[(idx + 1) % len(_VERBOSITY)])
        self._refresh()

    def action_increment(self) -> None:
        s = self.app.store.settings
        key, _, kind, step = self._current()
        if kind == "int":
            setattr(s, key, getattr(s, key) + step)
        self._refresh()

    def action_decrement(self) -> None:
        s = self.app.store.settings
        key, _, kind, step = self._current()
        if kind == "int":
            setattr(s, key, max(1, getattr(s, key) - step))
        self._refresh()

    def action_save(self) -> None:
        self.app.store.save_settings()
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
