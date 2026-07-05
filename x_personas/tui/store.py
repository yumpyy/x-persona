from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
            (entry / "activity-log.md").touch(exist_ok=True)
            _load_stats_from_log(info)
            _load_rate_limits(info)
            found.append(info)
        return found


def _load_stats_from_log(info: PersonaRuntimeInfo) -> None:
    path = Path(info.activity_log_file)
    if not path.exists():
        return
    today = datetime.now(timezone.utc).date()
    total = 0
    today_count = 0
    last_action = ""
    last_time = ""
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("|") or "timestamp" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            continue
        total += 1
        ts_str = parts[1]
        action = parts[2]
        target = parts[3]
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.date() == today:
                today_count += 1
        except (ValueError, TypeError):
            pass
        last_action = f"{action} {target}"
        last_time = ts_str
    info.total_engagements = total
    info.engagements_today = today_count
    info.last_action = last_action
    info.last_action_time = last_time


def _load_rate_limits(info: PersonaRuntimeInfo) -> None:
    path = Path(info.rate_limit_file)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        for entry in entries:
            action = entry.get("action", "")
            if action in info.rate_limits:
                info.rate_limits[action] += 1
    except (json.JSONDecodeError, Exception):
        pass
