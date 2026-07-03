from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, RichLog, Static

from x_personas.tui.widgets.help_bar import HelpBar


def _icon(status: str) -> str:
    return {"running": "●", "starting": "◐", "break": "◑", "stopped": "○", "error": "●"}.get(status, "○")


def _color(status: str) -> str:
    return {"running": "#a6e3a1", "starting": "#f9e2af", "break": "#cba6f7",
            "stopped": "#585b70", "error": "#f38ba8"}.get(status, "#585b70")


def _rate_bar(used: int, max_: int, width: int = 5) -> str:
    filled = min(int((used / max(max_, 1)) * width), width)
    return "█" * filled + "░" * (width - filled)


class MainScreen(Screen):
    """Single-screen layout — sidebar persona list + main area."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_idx = 0
        self._log_initialized = False
        self._detail_open = False
        self._activity_data: dict[int, dict] = {}
        self._flags_mode = False
        self._flags_cursor = 0

    # ── Compose ──

    def compose(self) -> ComposeResult:
        yield Static("X-Personas — Autonomous Persona Agent", id="header")
        with Horizontal(id="root"):
            with Vertical(id="sidebar"):
                yield RichLog(id="side-list", highlight=True, markup=True, wrap=True)
                yield Static(id="side-stats")
                yield Static(id="side-rates")
            with Vertical(id="main"):
                yield Static(id="main-header")
                yield DataTable(id="main-activity", cursor_type="row")
                yield RichLog(id="main-log", highlight=True, markup=True)
        yield HelpBar()

    def on_mount(self) -> None:
        self._init_log()
        self._rebuild_sidebar()
        self._show_persona()
        activity = self.query_one("#main-activity", DataTable)
        activity.add_column("Time", width=20)
        activity.add_column("Action", width=14)
        activity.add_column("Target", width=22)
        activity.add_column("Score", width=8)

    # ── Sidebar ──

    def _names(self) -> list[str]:
        return list(self.app.store.personas.keys())

    def _selected_name(self) -> str | None:
        names = self._names()
        if not names:
            return None
        return names[min(self._selected_idx, len(names) - 1)]

    def _current_info(self):
        name = self._selected_name()
        return self.app.store.get_persona(name) if name else None

    def _rebuild_sidebar(self) -> None:
        if self._flags_mode:
            self._render_flags()
        else:
            self._render_persona_list()

    def _render_persona_list(self) -> None:
        store = self.app.store
        names = self._names()
        log = self.query_one("#side-list", RichLog)
        log.clear()
        if not names:
            log.write("[#6c7086](no personas)[/]")
        else:
            for i, name in enumerate(names):
                info = store.get_persona(name)
                ic = _icon(info.status)
                co = _color(info.status)
                cursor = "[#89b4fa]▸[/]" if i == self._selected_idx else " "
                log.write(f"{cursor} [{co}]{ic}[/] [bold]{name}[/]")

        self.query_one("#side-stats", Static).update(
            f"[#6c7086]active:[/] {store.active_count}/{len(names)}"
            f"  [#6c7086]today:[/] {store.engagements_today_all}"
            f"  [#6c7086]total:[/] {store.total_engagements_all}"
        )

        rate_lines = [""]
        for action in ("like", "reply", "repost", "quote"):
            used = sum(p.rate_limits.get(action, 0) for p in store.personas.values())
            max_ = sum(p.rate_limits_max.get(action, 10) for p in store.personas.values()) or 1
            bar = _rate_bar(used, max_)
            rcol = "#f38ba8" if used / max_ >= 0.8 else "#f9e2af" if used / max_ >= 0.5 else "#a6e3a1"
            rate_lines.append(f"[{rcol}]{action[:4]} {bar} {used}/{max_}[/]")
        self.query_one("#side-rates", Static).update("\n".join(rate_lines))

    def _render_flags(self) -> None:
        info = self._current_info()
        if not info:
            return
        log = self.query_one("#side-list", RichLog)
        log.clear()
        log.write(f"[#f9e2af bold]Flags — {info.name}[/]\n")
        ask_cur = "[#89b4fa]▸[/]" if self._flags_cursor == 0 else " "
        ask_checked = "[#a6e3a1][x][/]" if info.ask else "[#6c7086][ ][/]"
        log.write(f"{ask_cur} {ask_checked}  ask before acting\n")
        vis_cur = "[#89b4fa]▸[/]" if self._flags_cursor == 1 else " "
        vis_checked = "[#a6e3a1][x][/]" if not info.headless else "[#6c7086][ ][/]"
        log.write(f"{vis_cur} {vis_checked}  show browser")
        self.query_one("#side-stats", Static).update(
            "[#6c7086]↑↓: pick  space: toggle  esc: done[/]"
        )
        self.query_one("#side-rates", Static).update("")

    # ── Main area ──

    def _show_persona(self) -> None:
        info = self._current_info()
        if not info:
            return

        ic = _icon(info.status)
        co = _color(info.status)
        self.query_one("#main-header", Static).update(
            f"[bold]{info.name}[/]  [{co}]{ic} {info.status}[/]"
            f"  │ [#6c7086]cycle:[/] [bold]{info.cycle_count}[/]"
            f"  [#6c7086]scrolls:[/] [bold]{info.current_scroll}[/]"
            f"  [#6c7086]today:[/] [bold]{info.engagements_today}[/]"
            f"  [#6c7086]total:[/] [bold]{info.total_engagements}[/]"
            f"  │ [#6c7086]last:[/] [italic]{info.last_action or '—'}[/]"
        )

        self._refresh_activity(info)
        self._reset_log()

    def _refresh_activity(self, info) -> None:
        table = self.query_one("#main-activity", DataTable)
        table.clear()
        self._activity_data.clear()
        if not table.columns:
            table.add_column("Time", width=20)
            table.add_column("Action", width=14)
            table.add_column("Target", width=22)
            table.add_column("Score", width=8)
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

    def _init_log(self) -> None:
        info = self._current_info()
        if not info:
            return
        log_widget = self.query_one("#main-log", RichLog)
        log_widget.clear()
        try:
            while True:
                msg = info.log_queue.get_nowait()
                log_widget.write(msg)
        except asyncio.QueueEmpty:
            pass
        self._log_timer = self.set_interval(0.3, self._drain_log)
        self._log_initialized = True

    def _reset_log(self) -> None:
        info = self._current_info()
        if not info:
            return
        log_widget = self.query_one("#main-log", RichLog)
        log_widget.clear()
        try:
            while True:
                msg = info.log_queue.get_nowait()
                log_widget.write(msg)
        except asyncio.QueueEmpty:
            pass

    def _drain_log(self) -> None:
        info = self._current_info()
        if not info:
            return
        try:
            log_widget = self.query_one("#main-log", RichLog)
        except Exception:
            return
        try:
            while True:
                msg = info.log_queue.get_nowait()
                log_widget.write(msg)
        except asyncio.QueueEmpty:
            pass
        log_widget.scroll_end(animate=False)

    # ── Navigation ──

    def _next(self) -> None:
        names = self._names()
        if len(names) <= 1:
            return
        self._selected_idx = (self._selected_idx + 1) % len(names)
        self._rebuild_sidebar()
        self._show_persona()

    def _prev(self) -> None:
        names = self._names()
        if len(names) <= 1:
            return
        self._selected_idx = (self._selected_idx - 1) % len(names)
        self._rebuild_sidebar()
        self._show_persona()

    def refresh_main(self) -> None:
        self._rebuild_sidebar()
        self._show_persona()

    # ── Keybindings ──

    def key_up(self) -> None:
        if self._flags_mode:
            self._flags_cursor_up()
        else:
            self._prev()

    def key_down(self) -> None:
        if self._flags_mode:
            self._flags_cursor_down()
        else:
            self._next()

    def key_enter(self) -> None:
        name = self._selected_name()
        if name:
            self.app.handle_start_stop(name)

    def key_s(self) -> None:
        name = self._selected_name()
        if name:
            self.app.handle_start_stop(name)

    def key_k(self) -> None:
        name = self._selected_name()
        if name:
            self.app.stop_persona(name, force=True)

    def key_r(self) -> None:
        self._rebuild_sidebar()
        self._show_persona()

    def key_i(self) -> None:
        name = self._selected_name()
        if name:
            from x_personas.tui.screens.intervene import InterveneScreen
            self.app.push_screen(InterveneScreen(name))

    def key_o(self) -> None:
        name = self._selected_name()
        if name:
            self.app.enter_compose(name)

    def key_g(self) -> None:
        if self.app.compose_mode and not self.app.compose_prompt_mode:
            self.app.show_compose_prompt()

    def key_c(self) -> None:
        if self.app.compose_mode:
            self.run_worker(self.app.compose_custom())
            return
        name = self._selected_name()
        if name:
            info = self.app.store.get_persona(name)
            if info:
                from x_personas.tui.screens.config_editor import ConfigEditor
                self.app.push_screen(ConfigEditor(str(info.persona_path)))

    def key_h(self) -> None:
        info = self._current_info()
        if info:
            from x_personas.tui.screens.history_browser import HistoryBrowser
            self.app.push_screen(HistoryBrowser(info.activity_log_file))

    def key_f(self) -> None:
        from x_personas.tui.screens.settings import SettingsScreen
        self.app.push_screen(SettingsScreen())

    def key_e(self) -> None:
        if self._flags_mode:
            self._flags_toggle()
        else:
            self._flags_mode = True
            self._flags_cursor = 0
            self._rebuild_sidebar()

    def key_escape(self) -> None:
        if self._flags_mode:
            self._flags_mode = False
            self._rebuild_sidebar()
        elif self.app.compose_prompt_mode:
            self.app._hide_prompt()
            self.app._update_footer()
        elif self.app.compose_mode:
            self.app.exit_compose()

    def key_question_mark(self) -> None:
        from x_personas.tui.screens.help_overlay import HelpOverlay
        self.app.push_screen(HelpOverlay())

    def key_q(self) -> None:
        self.app.exit()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        data = self._activity_data.get(idx)
        if data:
            self._show_detail(data)

    # ── Detail panel ──

    def _show_detail(self, data: dict) -> None:
        self._detail_open = True
        from x_personas.tui.screens.activity_detail import ActivityDetailScreen
        self.app.push_screen(ActivityDetailScreen(data))

    # ── Inline flags ──

    def _flags_cursor_up(self) -> None:
        self._flags_cursor = max(0, self._flags_cursor - 1)
        self._rebuild_sidebar()

    def _flags_cursor_down(self) -> None:
        self._flags_cursor = min(1, self._flags_cursor + 1)
        self._rebuild_sidebar()

    def _flags_toggle(self) -> None:
        info = self._current_info()
        if not info:
            return
        if self._flags_cursor == 0:
            info.ask = not info.ask
        else:
            info.headless = not info.headless
        self._rebuild_sidebar()
