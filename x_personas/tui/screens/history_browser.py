from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, Select, Static
from textual.containers import Vertical, Horizontal


class HistoryBrowser(ModalScreen):
    """Full-screen activity log viewer with search and filter."""

    def __init__(self, activity_log_file: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._log_file = activity_log_file
        self._all_rows: list[tuple] = []

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[bold]Activity Log Browser[/]", classes="history-title"),
            Horizontal(
                Input(placeholder="Search text...", id="history-search"),
                Select(
                    [("All", "all"), ("Like", "like"), ("Reply", "reply"), ("Repost", "repost"), ("Quote", "quote"),
                     ("Original Post", "original_post")],
                    value="all",
                    id="history-filter",
                    allow_blank=False,
                ),
                classes="history-controls",
            ),
            DataTable(id="history-table", cursor_type="row"),
            id="history-container",
        )

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.add_columns("Timestamp", "Action", "Target", "Content", "Score")
        self._load_all()

    def _load_all(self) -> None:
        self._all_rows = []
        path = Path(self._log_file)
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                ts = parts[1][:19]
                action = parts[2][:15]
                target = parts[3][:25]
                content = parts[4][:80]
                score = parts[5][:6]
                self._all_rows.append((ts, action, target, content, score))
        self._all_rows.reverse()
        self._apply_filter()

    def _apply_filter(self) -> None:
        search = self.query_one("#history-search", Input).value.lower()
        filter_val = self.query_one("#history-filter", Select).value
        table = self.query_one("#history-table", DataTable)
        table.clear()
        for row in self._all_rows:
            ts, action, target, content, score = row
            if filter_val != "all" and action != filter_val:
                continue
            if search and search not in content.lower() and search not in target.lower():
                continue
            table.add_row(ts, action, target, content, score)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filter()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._apply_filter()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
