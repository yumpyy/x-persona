from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from textual.app import App
from textual.binding import Binding
from textual.widgets import Static, Input

from x_personas.tui.store import TUIStore, PersonaRuntimeInfo
from x_personas.tui.screens.dashboard import Dashboard
from x_personas.tui.screens.persona_detail import PersonaDetail
from x_personas.tui.workers.persona_worker import PersonaWorker
from x_personas.tui.workers.stats_worker import StatsWatcher


def _find_editor() -> str:
    for var in ("VISUAL", "EDITOR"):
        editor = os.environ.get(var)
        if editor:
            return editor
    for candidate in ("editor", "vim", "nano", "vi"):
        if shutil.which(candidate):
            return candidate
    return "vim"


class XPersonasTUI(App):
    """X-Personas Textual TUI — keyboard-driven, dense, htop-like."""

    CSS_PATH = "css/app.tcss"
    COLOR = "#89b4fa"

    SCREENS = {
        "dashboard": Dashboard,
        "detail": PersonaDetail,
    }

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Palette"),
    ]

    def __init__(self, filter_personas: list[str] | None = None, headless: bool = True) -> None:
        super().__init__()
        self.store = TUIStore()
        self._filter_personas = filter_personas
        self._headless = headless
        self._persona_workers: dict[str, PersonaWorker] = {}
        self._stats_watcher: StatsWatcher | None = None
        self.compose_mode = False
        self.compose_prompt_mode = False
        self._compose_persona: str = ""
        self.ask_mode = False
        self._ask_worker: PersonaWorker | None = None

    def on_mount(self) -> None:
        self.title = "X-Personas"
        self.sub_title = "Autonomous X/Twitter Persona Agent"

        settings_path = Path("personas") / "tui-settings.json"
        self.store.load_settings(settings_path)
        self.store.settings.headless = self._headless

        discovered = self.store.discover_personas(
            "personas", filter_names=self._filter_personas
        )
        for info in discovered:
            info.headless = self._headless
            self.store.add_persona(info)

        self.push_screen("dashboard")

        self._stats_watcher = StatsWatcher(self.store, self._on_stats_update)
        self.run_worker(self._stats_watcher.run(), group="stats", name="stats-watcher")

    def on_unmount(self) -> None:
        if self._stats_watcher:
            self._stats_watcher.stop()

    def refresh_all(self) -> None:
        screen = self.screen
        if hasattr(screen, "refresh_dashboard"):
            screen.refresh_dashboard()
        elif hasattr(screen, "refresh_detail"):
            screen.refresh_detail()

    def _on_stats_update(self) -> None:
        self.refresh_all()

    def _update_persona_status(self, name: str, status: str) -> None:
        info = self.store.get_persona(name)
        if info:
            info.status = status
            self.refresh_all()

    def _update_persona_stats(self, name: str) -> None:
        self.refresh_all()

    def _update_persona_error(self, name: str, error: str) -> None:
        info = self.store.get_persona(name)
        if info:
            info.error_message = error
            info.status = "error"
            self.refresh_all()

    # ── Persona lifecycle ──

    def handle_start_stop(self, name: str) -> None:
        info = self.store.get_persona(name)
        if not info:
            return
        if info.status == "running":
            self.stop_persona(name)
        else:
            self.start_persona(name)

    def start_persona(self, name: str) -> None:
        info = self.store.get_persona(name)
        if not info or info.status == "running":
            return

        worker = PersonaWorker(
            persona_info=info,
            settings=self.store.settings,
            on_status=lambda s: self._update_persona_status(name, s),
            on_stats=lambda i: self._update_persona_stats(name),
            on_error=lambda e: self._update_persona_error(name, e),
            on_ask=self._on_worker_ask,
        )
        self._persona_workers[name] = worker
        self.run_worker(worker.run(), group="personas", name=f"persona-{name}")

    def stop_persona(self, name: str, force: bool = False) -> None:
        info = self.store.get_persona(name)
        if not info:
            return
        worker = self._persona_workers.pop(name, None)
        if worker:
            worker.stop()
        if force:
            for w in self.workers:
                if w.name == f"persona-{name}":
                    w.cancel()
        info.status = "stopped"
        self.refresh_all()

    def start_all(self) -> None:
        for name in list(self.store.personas.keys()):
            if self.store.get_persona(name).status != "running":
                self.start_persona(name)

    def stop_all(self) -> None:
        for name in list(self._persona_workers.keys()):
            self.stop_persona(name, force=True)

    # ── Compose mode ──

    def enter_compose(self, persona_name: str) -> None:
        self.compose_mode = True
        self._compose_persona = persona_name
        self._update_footer()

    def exit_compose(self) -> None:
        self.compose_mode = False
        self.compose_prompt_mode = False
        self._compose_persona = ""
        self._hide_prompt()
        self._update_footer()

    def _update_footer(self) -> None:
        screen = self.screen
        footer = screen.query_one("#footer")
        footer.set_compose_mode(self.compose_mode)

    def show_compose_prompt(self) -> None:
        """Show inline prompt input in footer to guide LLM generation."""
        self.compose_prompt_mode = True
        footer = self.screen.query_one("#footer")
        footer.show_prompt()

    def _hide_prompt(self) -> None:
        self.compose_prompt_mode = False
        try:
            footer = self.screen.query_one("#footer")
            footer.hide_prompt()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "compose-prompt-input":
            prompt = event.value.strip()
            self._hide_prompt()
            if prompt:
                await self.compose_generate(prompt=prompt)

    async def compose_generate(self, prompt: str = "") -> None:
        from x_personas.agent.nodes.generate_content import generate_original_post
        from x_personas.agent.config import get_llm_config
        from x_personas.agent.history import load_recent_original_posts
        from datetime import datetime

        name = self._compose_persona
        info = self.store.get_persona(name)
        if not info:
            return

        try:
            llm_config = get_llm_config()
            hour = datetime.now().hour
            if 5 <= hour < 12:
                tod = "Morning"
            elif 12 <= hour < 20:
                tod = "Afternoon/Evening"
            else:
                tod = "Late Night"
            recent = load_recent_original_posts(info.activity_log_file, limit=5)
            persona_sections = getattr(info, "_persona_sections", {})
            text = await generate_original_post(persona_sections, llm_config, tod, recent, prompt=prompt)
            await self._open_editor_and_publish(text)
        except Exception as e:
            self._show_compose_error(str(e))

    async def compose_custom(self) -> None:
        await self._open_editor_and_publish("")

    async def _open_editor_and_publish(self, initial_text: str) -> None:
        from x_personas.utils.post import post
        from x_personas.utils.browser import BrowserSession
        from x_personas.agent.history import load_engaged_status_ids
        from datetime import datetime, timezone

        name = self._compose_persona
        info = self.store.get_persona(name)
        if not info:
            return

        draft = Path(tempfile.mktemp(suffix=".md"))
        draft.write_text(initial_text, encoding="utf-8")

        editor = _find_editor()
        try:
            with self.suspend():
                subprocess.run([editor, str(draft)], check=False)
        except Exception:
            self._show_compose_error("Editor not supported in this environment")
            draft.unlink(missing_ok=True)
            return

        text = draft.read_text(encoding="utf-8").strip()
        draft.unlink(missing_ok=True)

        if not text:
            self._show_compose_error("Empty draft — nothing to publish.")
            return
        if len(text) > 280:
            self._show_compose_error(f"Too long ({len(text)}/280).")
            return

        try:
            auth = info.persona_path.parent / "auth.json"
            async with BrowserSession(headless=True, auth_state_path=str(auth) if auth.exists() else None) as ctx:
                resp = await post(ctx, text)
                if resp.success:
                    ts = datetime.now(timezone.utc).isoformat()
                    entry = f"| {ts} | original_post | self | {text} | 10.0 | Published from TUI composer. |"
                    with open(info.activity_log_file, "a", encoding="utf-8") as f:
                        f.write(entry + "\n")
                    self._show_compose_error("")  # clear, or we could flash success
                else:
                    self._show_compose_error(f"Failed: {resp.error}")
        except Exception as e:
            self._show_compose_error(f"Error: {e}")

    def _show_compose_error(self, msg: str) -> None:
        if not msg:
            return
        screen = self.screen
        for selector in ("#dash-status", "#detail-header"):
            try:
                widget = screen.query_one(selector, Static)
                widget.update(f"[#f38ba8]{msg}[/]")
                return
            except Exception:
                continue

    # ── Ask (approval) mode ──

    def _on_worker_ask(self, worker: PersonaWorker, description: str) -> None:
        self.ask_mode = True
        self._ask_worker = worker
        self._show_ask_footer()

    def _show_ask_footer(self) -> None:
        try:
            footer = self.screen.query_one("#footer")
            footer.show_ask()
        except Exception:
            pass

    def _hide_ask(self) -> None:
        self.ask_mode = False
        self._ask_worker = None
        try:
            footer = self.screen.query_one("#footer")
            footer.hide_ask()
        except Exception:
            pass
