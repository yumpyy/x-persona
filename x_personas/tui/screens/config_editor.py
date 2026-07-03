from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical


def _find_editor() -> str:
    for var in ("VISUAL", "EDITOR"):
        editor = os.environ.get(var)
        if editor:
            return editor
    for candidate in ("editor", "vim", "nano", "vi"):
        if shutil.which(candidate):
            return candidate
    return "vim"


class ConfigEditor(ModalScreen):
    """Opens persona.md in system editor via TUI suspend, fallback to textarea."""

    def __init__(self, persona_path: str | Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._path = Path(persona_path)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold]persona.md — {self._path.parent.name}[/]", classes="editor-title"),
            Static(id="editor-status"),
            id="editor-dialog",
        )

    async def on_mount(self) -> None:
        editor = _find_editor()
        try:
            with self.app.suspend():
                subprocess.run([editor, str(self._path)], check=False)
            self.query_one("#editor-status", Static).update("[#a6e3a1]Saved! Reloading persona...[/]")
            await asyncio.sleep(0.8)
        except Exception:
            self.query_one("#editor-status", Static).update("[#f9e2af]Editor not supported in this environment[/]")
            await asyncio.sleep(1.5)
        self.app.pop_screen()
