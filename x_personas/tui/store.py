from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from textual.reactive import var


@dataclass
class PersonaRuntimeInfo:
    name: str
    persona_path: Path
    activity_log_file: str
    rate_limit_file: str

    status: str = "stopped"
    cycle_count: int = 0
    engagements_today: int = 0
    total_engagements: int = 0
    follows: int = 0
    original_posts: int = 0
    last_action: str = ""
    last_action_time: str = ""
    current_scroll: int = 0
    error_message: str = ""

    ask: bool = False
    headless: bool = True

    rate_limits: dict[str, int] = field(default_factory=lambda: {"like": 0, "reply": 0, "repost": 0, "quote": 0})
    rate_limits_max: dict[str, int] = field(default_factory=lambda: {"like": 10, "reply": 5, "repost": 5, "quote": 3})

    log_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    error_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    worker = None


@dataclass
class AppSettings:
    scroll_limit: int = 2500
    break_min: int = 600
    break_max: int = 1800
    min_action_delay: int = 3
    max_action_delay: int = 8
    min_scroll_delay: int = 5
    max_scroll_delay: int = 15
    approval_mode: bool = False
    log_verbosity: str = "info"
    headless: bool = True
    browser_path: str | None = None
    auth_file: str | None = None

    def to_dict(self) -> dict:
        return {
            "scroll_limit": self.scroll_limit,
            "break_min": self.break_min,
            "break_max": self.break_max,
            "min_action_delay": self.min_action_delay,
            "max_action_delay": self.max_action_delay,
            "min_scroll_delay": self.min_scroll_delay,
            "max_scroll_delay": self.max_scroll_delay,
            "approval_mode": self.approval_mode,
            "log_verbosity": self.log_verbosity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AppSettings:
        s = cls()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


class TUIStore:
    def __init__(self) -> None:
        self.personas: dict[str, PersonaRuntimeInfo] = {}
        self.settings = AppSettings()
        self._settings_path: Path | None = None

    def add_persona(self, info: PersonaRuntimeInfo) -> None:
        self.personas[info.name] = info

    def remove_persona(self, name: str) -> None:
        self.personas.pop(name, None)

    def get_persona(self, name: str) -> PersonaRuntimeInfo | None:
        return self.personas.get(name)

    @property
    def active_count(self) -> int:
        return sum(1 for p in self.personas.values() if p.status == "running")

    @property
    def total_engagements_all(self) -> int:
        return sum(p.total_engagements for p in self.personas.values())

    @property
    def engagements_today_all(self) -> int:
        return sum(p.engagements_today for p in self.personas.values())

    def load_settings(self, path: str | Path) -> None:
        self._settings_path = Path(path)
        if self._settings_path.exists():
            import json
            try:
                data = json.loads(self._settings_path.read_text())
                self.settings = AppSettings.from_dict(data)
            except (json.JSONDecodeError, Exception):
                pass

    def save_settings(self) -> None:
        if self._settings_path:
            import json
            self._settings_path.write_text(json.dumps(self.settings.to_dict(), indent=2))

    def discover_personas(self, personas_dir: str = "personas", filter_names: list[str] | None = None) -> list[PersonaRuntimeInfo]:
        base = Path(personas_dir)
        if not base.exists():
            return []
        found = []
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            md = entry / "persona.md"
            if not md.exists():
                continue
            if filter_names and entry.name not in filter_names:
                continue
            info = PersonaRuntimeInfo(
                name=entry.name,
                persona_path=md,
                activity_log_file=str(entry / "activity-log.md"),
                rate_limit_file=str(entry / "rate-limits.json"),
            )
            # create activity log if missing
            (entry / "activity-log.md").touch(exist_ok=True)
            found.append(info)
        return found
