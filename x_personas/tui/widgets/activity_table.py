from __future__ import annotations

from pathlib import Path

from textual.widgets import DataTable


class ActivityTable(DataTable):
    """DataTable that reads from a persona's activity-log.md."""

    def __init__(self, activity_log_file: str, max_rows: int = 100, **kwargs) -> None:
        super().__init__(**kwargs)
        self._log_file = activity_log_file
        self._max_rows = max_rows

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self._refresh()

    def _refresh(self) -> None:
        self.clear()
        self.add_columns("Time", "Action", "Target", "Content", "Score")
        path = Path(self._log_file)
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        rows = []
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                ts = parts[1][:19] if len(parts[1]) > 19 else parts[1]
                action = parts[2][:12]
                target = parts[3][:20]
                content = parts[4][:60]
                score = parts[5][:6]
                rows.append((ts, action, target, content, score))
        rows.reverse()
        for row in rows[: self._max_rows]:
            self.add_row(*row)

    def refresh_log(self) -> None:
        self._refresh()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Emit a message so the parent screen can show full content."""
        self.post_message(self.RowSelected(event.row_key))
