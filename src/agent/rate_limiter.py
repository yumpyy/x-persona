from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_PER_CYCLE_CAPS = {
    "like": 5,
    "reply": 2,
    "repost": 2,
    "quote": 1,
}

_HOURLY_CAPS = {
    "like": 20,
    "reply": 8,
    "repost": 8,
    "quote": 4,
    "follow": 3,
}

_DAILY_CAPS = {
    "like": 80,
    "reply": 30,
    "repost": 30,
    "quote": 15,
    "follow": 15,
}

_MIN_DELAY_BETWEEN_ACTIONS = 3.0
_MAX_DELAY_BETWEEN_ACTIONS = 6.0


class RateLimitState:
    def __init__(self, state_file: str | None = None) -> None:
        self.state_file = state_file
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.state_file:
            return
        path = Path(self.state_file)
        if path.exists():
            import json
            try:
                data = json.loads(path.read_text())
                self.entries = data.get("entries", [])
            except (json.JSONDecodeError, Exception):
                self.entries = []

    def save(self) -> None:
        if not self.state_file:
            return
        import json
        path = Path(self.state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"entries": self.entries}, indent=2))

    def record(self, action: str, timestamp: str | None = None) -> None:
        self.entries.append({
            "action": action,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        })

    def _count_in_window(self, action: str, seconds: int) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - seconds
        count = 0
        for e in self.entries:
            if e["action"] != action:
                continue
            try:
                ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                if ts.timestamp() >= cutoff:
                    count += 1
            except (ValueError, TypeError):
                pass
        return count

    def hourly_count(self, action: str) -> int:
        return self._count_in_window(action, 3600)

    def daily_count(self, action: str) -> int:
        return self._count_in_window(action, 86400)

    def can_act(self, action: str) -> tuple[bool, str | None]:
        action = action.lower()
        hourly = self.hourly_count(action)
        daily = self.daily_count(action)
        hourly_cap = _HOURLY_CAPS.get(action, 5)
        daily_cap = _DAILY_CAPS.get(action, 20)
        if hourly >= hourly_cap:
            return False, f"Hourly limit reached for {action} ({hourly}/{hourly_cap})"
        if daily >= daily_cap:
            return False, f"Daily limit reached for {action} ({daily}/{daily_cap})"
        return True, None


def cycle_caps() -> dict[str, int]:
    return dict(_PER_CYCLE_CAPS)


def min_delay() -> float:
    import random
    return random.uniform(_MIN_DELAY_BETWEEN_ACTIONS, _MAX_DELAY_BETWEEN_ACTIONS)


def scroll_delay() -> float:
    import random
    return random.uniform(5.0, 15.0)


def action_delay() -> float:
    import random
    return random.uniform(3.0, 8.0)
