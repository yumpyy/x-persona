from __future__ import annotations

import asyncio


class StatsWatcher:
    """Periodically refreshes per-persona stats from filesystem (activity log, rate limits)."""

    def __init__(self, store, on_update) -> None:
        self.store = store
        self._on_update = on_update
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(5)
            if not self.store.personas:
                continue
            for info in self.store.personas.values():
                self._refresh_rate_limits(info)
            self._on_update()

    def _refresh_rate_limits(self, info) -> None:
        path = info.rate_limit_file
        try:
            import json
            from pathlib import Path
            p = Path(path)
            if p.exists():
                data = json.loads(p.read_text())
                for action in ("like", "reply", "repost", "quote"):
                    used = data.get("cycle", {}).get(action, 0)
                    info.rate_limits[action] = used
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
