"""Rate limit repository."""

from __future__ import annotations

from datetime import datetime, timezone

from xpersonas.storage.database import Database

DEFAULT_PER_CYCLE = {"like": 5, "reply": 2, "repost": 2, "quote": 1}
DEFAULT_PER_HOUR = {"like": 20, "reply": 8, "repost": 8, "quote": 4, "follow": 3}
DEFAULT_PER_DAY = {"like": 80, "reply": 30, "repost": 30, "quote": 15, "follow": 15}


class RateLimitRepo:
    def __init__(self, db: Database):
        self.db = db

    def record(self, persona_id: str, action_type: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO rate_limits (persona_id, action_type, timestamp) VALUES (?, ?, ?)",
            (persona_id, action_type, now),
        )
        self.db.commit()

    def _count_in_window(self, persona_id: str, action_type: str, seconds: int) -> int:
        row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM rate_limits "
            "WHERE persona_id = ? AND action_type = ? AND timestamp > datetime('now', ?)",
            (persona_id, action_type, f"-{seconds} seconds"),
        )
        return row["cnt"] if row else 0

    def hourly_count(self, persona_id: str, action_type: str) -> int:
        return self._count_in_window(persona_id, action_type, 3600)

    def daily_count(self, persona_id: str, action_type: str) -> int:
        return self._count_in_window(persona_id, action_type, 86400)

    def can_act(
        self,
        persona_id: str,
        action_type: str,
        hourly_cap: int | None = None,
        daily_cap: int | None = None,
    ) -> tuple[bool, str | None]:
        h_cap = (hourly_cap or DEFAULT_PER_HOUR.get(action_type, 999))
        d_cap = (daily_cap or DEFAULT_PER_DAY.get(action_type, 999))

        h_count = self.hourly_count(persona_id, action_type)
        if h_count >= h_cap:
            return False, f"Hourly limit reached for {action_type}: {h_count}/{h_cap}"

        d_count = self.daily_count(persona_id, action_type)
        if d_count >= d_cap:
            return False, f"Daily limit reached for {action_type}: {d_count}/{d_cap}"

        return True, None

    def get_status(self, persona_id: str) -> dict:
        """Get current rate limit usage for all action types."""
        status = {}
        for action_type in DEFAULT_PER_HOUR:
            h_limit = DEFAULT_PER_HOUR[action_type]
            d_limit = DEFAULT_PER_DAY.get(action_type, 999)
            h_count = self.hourly_count(persona_id, action_type)
            d_count = self.daily_count(persona_id, action_type)
            status[action_type] = {
                "hourly": {"used": h_count, "limit": h_limit},
                "daily": {"used": d_count, "limit": d_limit},
            }
        return status
