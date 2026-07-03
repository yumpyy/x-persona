from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static

from x_personas.tui.widgets.help_bar import HelpBar


def _status_icon(status: str) -> str:
    return {"running": "●", "starting": "◐", "break": "◑", "stopped": "○", "error": "●"}.get(status, "○")


def _rate_bar(used: int, max_: int, width: int = 10) -> str:
    filled = min(int((used / max(max_, 1)) * width), width)
    empty = width - filled
    return "█" * filled + "░" * empty


class Dashboard(Screen):
    """Main dashboard — persona table + rate limits."""

    def compose(self) -> ComposeResult:
        yield Static("X-Personas", id="header")
        yield Static(id="dash-status")
        yield DataTable(id="dash-table", cursor_type="row")
        yield Static(id="dash-rates")
        yield HelpBar()

    def on_mount(self) -> None:
        table = self.query_one("#dash-table", DataTable)
        table.add_columns("Name", "Status", "Cycle", "Scrolls", "Today", "Total", "Last Action")
        self._rebuild()

    def _rebuild(self) -> None:
        table = self.query_one("#dash-table", DataTable)
        table.clear()
        store = self.app.store
        for info in store.personas.values():
            icon = _status_icon(info.status)
            color = {"running": "#a6e3a1", "starting": "#f9e2af", "break": "#cba6f7",
                      "stopped": "#585b70", "error": "#f38ba8"}.get(info.status, "#585b70")
            status_str = f"[{color}]{icon} {info.status}[/]"
            cycle = str(info.cycle_count) if info.status == "running" else "—"
            scrolls = str(info.current_scroll) if info.status == "running" else "—"
            last = info.last_action if info.last_action else "—"
            table.add_row(
                f"[bold]{info.name}[/]",
                status_str,
                cycle,
                scrolls,
                str(info.engagements_today),
                str(info.total_engagements),
                last,
            )
        self._update_status()
        self._update_rates()

    def _update_status(self) -> None:
        store = self.app.store
        self.query_one("#dash-status", Static).update(
            f"Active: [bold]{store.active_count}[/]/[bold]{len(store.personas)}[/]"
            f" │ Today: [bold]{store.engagements_today_all}[/]"
            f" │ Total: [bold]{store.total_engagements_all}[/]"
        )

    def _update_rates(self) -> None:
        store = self.app.store
        parts = []
        for action in ("like", "reply", "repost", "quote"):
            used = sum(p.rate_limits.get(action, 0) for p in store.personas.values())
            max_ = sum(p.rate_limits_max.get(action, 10) for p in store.personas.values()) or 1
            bar = _rate_bar(used, max_)
            color = "#f38ba8" if used / max_ >= 0.8 else "#f9e2af" if used / max_ >= 0.5 else "#a6e3a1"
            parts.append(f"[{color}]{action}: {bar} {used}/{max_}[/]")
        self.query_one("#dash-rates", Static).update("  ".join(parts))

    def refresh_dashboard(self) -> None:
        self._rebuild()

    def _selected_name(self) -> str | None:
        table = self.query_one("#dash-table", DataTable)
        row = table.cursor_row
        if row is None:
            names = list(self.app.store.personas.keys())
            return names[0] if names else None
        names = list(self.app.store.personas.keys())
        return names[row] if row < len(names) else None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter pressed on a row → go to detail view."""
        self.app.push_screen("detail")

    def key_s(self) -> None:
        name = self._selected_name()
        if name:
            self.app.handle_start_stop(name)

    def key_k(self) -> None:
        name = self._selected_name()
        if name:
            self.app.stop_persona(name, force=True)

    def key_r(self) -> None:
        self._rebuild()

    def key_tab(self) -> None:
        self.app.push_screen("detail")

    def key_c(self) -> None:
        if self.app.compose_mode:
            self.run_worker(self.app.compose_custom())
            return
        name = self._selected_name()
        if name:
            from x_personas.tui.screens.config_editor import ConfigEditor
            self.app.push_screen(ConfigEditor(str(self.app.store.get_persona(name).persona_path)))

    def key_i(self) -> None:
        name = self._selected_name()
        if name:
            from x_personas.tui.screens.intervene import InterveneScreen
            self.app.push_screen(InterveneScreen(name))

    def key_o(self) -> None:
        name = self._selected_name()
        if name:
            self.app.enter_compose(name)

    def key_e(self) -> None:
        name = self._selected_name()
        if name:
            from x_personas.tui.screens.persona_settings import PersonaSettingsScreen
            self.app.push_screen(PersonaSettingsScreen(name))

    def key_g(self) -> None:
        if self.app.compose_mode and not self.app.compose_prompt_mode:
            self.app.show_compose_prompt()

    def key_escape(self) -> None:
        if self.app.compose_prompt_mode:
            self.app._hide_prompt()
            self.app._update_footer()
        elif self.app.compose_mode:
            self.app.exit_compose()

    def key_question_mark(self) -> None:
        from x_personas.tui.screens.help_overlay import HelpOverlay
        self.app.push_screen(HelpOverlay())

    def key_q(self) -> None:
        self.app.exit()
