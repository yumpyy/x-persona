from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Static, RichLog

from x_personas.tui.widgets.help_bar import HelpBar
from x_personas.tui.widgets.height_splitter import HeightSplitter
from x_personas.tui.widgets.width_splitter import WidthSplitter


def _rate_bar(used: int, max_: int, width: int = 8) -> str:
    filled = min(int((used / max(max_, 1)) * width), width)
    empty = width - filled
    return "█" * filled + "░" * empty


class PersonaDetail(Screen):
    """Detail view — activity log (main) + expandable detail panel (right)."""

    BINDINGS = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_idx = 0
        self._log_initialized = False
        self._activity_data: dict[int, dict] = {}
        self._detail_open = False

    def compose(self) -> ComposeResult:
        yield Static(id="detail-header")
        yield Static(id="detail-stats")
        yield Static(id="detail-rates")
        with Horizontal(id="detail-container"):
            with Vertical(id="detail-left"):
                yield DataTable(id="detail-activity", cursor_type="row")
                yield HeightSplitter(target_widget=None, min_height=5, max_height=40)
                yield RichLog(id="detail-log", highlight=True, markup=True)
            yield WidthSplitter(target_widget=None, min_width=15, max_width=60)
            with Vertical(id="detail-right"):
                yield Static(id="detail-right-content")
        yield HelpBar()

    def on_mount(self) -> None:
        self._init_log_stream()
        self._show_current()
        table = self.query_one("#detail-activity", DataTable)
        h_splitter = self.query_one(HeightSplitter)
        h_splitter.target_widget = table
        w_splitter = self.query_one(WidthSplitter)
        w_splitter.target_widget = self.query_one("#detail-right")
        table.focus()

    def _init_log_stream(self) -> None:
        info = self._current_info()
        if not info:
            return
        log_widget = self.query_one("#detail-log", RichLog)
        log_widget.clear()
        try:
            while True:
                msg = info.log_queue.get_nowait()
                log_widget.write(msg)
        except asyncio.QueueEmpty:
            pass
        self._log_timer = self.set_interval(0.3, self._drain_log)
        self._log_initialized = True

    def _persona_names(self) -> list[str]:
        return list(self.app.store.personas.keys())

    def _current_info(self):
        names = self._persona_names()
        if not names:
            return None
        idx = min(self._current_idx, len(names) - 1)
        self._current_idx = idx
        return self.app.store.personas[names[idx]]

    def _show_current(self) -> None:
        info = self._current_info()
        if not info:
            return

        icon = {"running": "●", "starting": "◐", "break": "◑", "stopped": "○", "error": "●"}.get(info.status, "○")
        color = {"running": "#a6e3a1", "starting": "#f9e2af", "break": "#cba6f7",
                  "stopped": "#585b70", "error": "#f38ba8"}.get(info.status, "#585b70")
        self.query_one("#detail-header", Static).update(
            f"[bold]{info.name}[/]  [{color}]{icon} {info.status}[/]"
            f"  │ [dim]Cycle:[/] [bold]{info.cycle_count}[/]"
            f"  │ [dim]Scrolls:[/] [bold]{info.current_scroll}[/]"
        )

        self.query_one("#detail-stats", Static).update(
            f"[dim]Today:[/] {info.engagements_today}"
            f"  [dim]Total:[/] {info.total_engagements}"
            f"  [dim]Follows:[/] {info.follows}"
            f"  [dim]Original:[/] {info.original_posts}"
            f"  [dim]Last:[/] [italic]{info.last_action or '—'}[/]"
        )

        rate_lines = []
        for action in ("like", "reply", "repost", "quote"):
            used = info.rate_limits.get(action, 0)
            max_ = info.rate_limits_max.get(action, 10) or 1
            bar = _rate_bar(used, max_)
            c = "#f38ba8" if used / max_ >= 0.8 else "#f9e2af" if used / max_ >= 0.5 else "#a6e3a1"
            rate_lines.append(f"[{c}]{action}: {bar} {used}/{max_}[/]")
        self.query_one("#detail-rates", Static).update("  ".join(rate_lines))

        self._refresh_activity(info)

    def _drain_log(self) -> None:
        info = self._current_info()
        if not info:
            return
        log_widget = self.query_one("#detail-log", RichLog)
        try:
            while True:
                msg = info.log_queue.get_nowait()
                log_widget.write(msg)
        except asyncio.QueueEmpty:
            pass
        log_widget.scroll_end(animate=False)

    def _refresh_activity(self, info) -> None:
        table = self.query_one("#detail-activity", DataTable)
        table.clear(columns=True)
        table.add_column("Time", width=20)
        table.add_column("Action", width=14)
        table.add_column("Target", width=22)
        table.add_column("Score", width=8)
        self._activity_data.clear()
        path = Path(info.activity_log_file)
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        for i, line in enumerate(reversed(lines)):
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                table.add_row(parts[1][:19], parts[2][:12], parts[3][:20], parts[5][:6])
                self._activity_data[i] = {
                    "timestamp": parts[1],
                    "action": parts[2],
                    "target": parts[3],
                    "content": parts[4] if len(parts) > 4 else "",
                    "score": parts[5],
                    "context": parts[6] if len(parts) > 6 else "",
                }
        table.refresh(layout=True)

    def _show_detail(self, data: dict) -> None:
        panel = self.query_one("#detail-right")
        panel.styles.display = "block"
        self.query_one(WidthSplitter).styles.display = "block"
        self._detail_open = True

        action_label = data.get("action", "—").upper()
        content = (
            f"[bold]Activity Detail[/]\n"
            f"\n"
            f"[bold]Time:[/]    {data.get('timestamp', '—')}\n"
            f"[bold]Action:[/]  [bold #89b4fa]{action_label}[/]\n"
            f"[bold]Target:[/]  {data.get('target', '—')}\n"
            f"[bold]Score:[/]   {data.get('score', '—')}\n"
            f"\n"
            f"[bold]Content:[/]\n"
            f"  {data.get('content') or '[dim]none[/]'}\n"
            f"\n"
            f"[bold]Context / Reasoning:[/]\n"
            f"  [italic]{data.get('context') or '[dim]n/a[/]'}[/]\n"
        )
        self.query_one("#detail-right-content", Static).update(content)

    def _hide_detail(self) -> None:
        panel = self.query_one("#detail-right")
        panel.styles.display = "none"
        self.query_one(WidthSplitter).styles.display = "none"
        self._detail_open = False

    def refresh_detail(self) -> None:
        self._show_current()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        data = self._activity_data.get(idx)
        if data:
            self._show_detail(data)

    def _next_persona(self) -> None:
        names = self._persona_names()
        if len(names) <= 1:
            return
        self._current_idx = (self._current_idx + 1) % len(names)
        self._show_current()

    def _prev_persona(self) -> None:
        names = self._persona_names()
        if len(names) <= 1:
            return
        self._current_idx = (self._current_idx - 1) % len(names)
        self._show_current()

    # ── Keybindings ──

    def key_tab(self) -> None:
        self._next_persona()

    def key_escape(self) -> None:
        if self.app.ask_mode:
            self.app._ask_worker.resolve_ask(False)
            self.app._hide_ask()
        elif self.app.compose_prompt_mode:
            self.app._hide_prompt()
            self.app._update_footer()
        elif self.app.compose_mode:
            self.app.exit_compose()
        elif self._detail_open:
            self._hide_detail()
        else:
            self.app.pop_screen()

    def key_y(self) -> None:
        if self.app.ask_mode and self.app._ask_worker:
            self.app._ask_worker.resolve_ask(True)
            self.app._hide_ask()

    def key_n(self) -> None:
        if self.app.ask_mode and self.app._ask_worker:
            self.app._ask_worker.resolve_ask(False)
            self.app._hide_ask()

    def key_e(self) -> None:
        info = self._current_info()
        if info:
            from x_personas.tui.screens.persona_settings import PersonaSettingsScreen
            self.app.push_screen(PersonaSettingsScreen(info.name))

    def key_shift_tab(self) -> None:
        self._prev_persona()

    def key_s(self) -> None:
        info = self._current_info()
        if info:
            self.app.handle_start_stop(info.name)

    def key_k(self) -> None:
        info = self._current_info()
        if info:
            self.app.stop_persona(info.name, force=True)

    def key_r(self) -> None:
        self._show_current()

    def key_i(self) -> None:
        info = self._current_info()
        if info:
            from x_personas.tui.screens.intervene import InterveneScreen
            self.app.push_screen(InterveneScreen(info.name))

    def key_o(self) -> None:
        info = self._current_info()
        if info:
            self.app.enter_compose(info.name)

    def key_g(self) -> None:
        if self.app.compose_mode and not self.app.compose_prompt_mode:
            self.app.show_compose_prompt()

    def key_c(self) -> None:
        if self.app.compose_mode:
            self.run_worker(self.app.compose_custom())
            return
        info = self._current_info()
        if info:
            from x_personas.tui.screens.config_editor import ConfigEditor
            self.app.push_screen(ConfigEditor(str(info.persona_path)))

    def key_h(self) -> None:
        info = self._current_info()
        if info:
            from x_personas.tui.screens.history_browser import HistoryBrowser
            self.app.push_screen(HistoryBrowser(info.activity_log_file))

    def key_backspace(self) -> None:
        self.app.pop_screen()

    def key_question_mark(self) -> None:
        from x_personas.tui.screens.help_overlay import HelpOverlay
        self.app.push_screen(HelpOverlay())

    def key_q(self) -> None:
        self.app.exit()

    def on_screen_resume(self) -> None:
        self._show_current()
        self.query_one("#detail-activity", DataTable).focus()
