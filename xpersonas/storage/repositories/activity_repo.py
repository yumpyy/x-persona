"""Activity log repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from xpersonas.storage.database import Database


class ActivityRepo:
    def __init__(self, db: Database):
        self.db = db

    def record(
        self,
        persona_id: str,
        platform: str,
        action_type: str,
        target_post_id: str,
        target_author: str | None = None,
        content: str | None = None,
        score: float | None = None,
        reason: str | None = None,
        success: bool = True,
        error: str | None = None,
        is_promo: bool = False,
        product_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO activity_log "
            "(persona_id, timestamp, platform, action_type, target_post_id, target_author, "
            "content, score, reason, success, error, is_promo, product_id, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                persona_id, now, platform, action_type, target_post_id,
                target_author, content, score, reason, int(success), error,
                int(is_promo), product_id, json.dumps(metadata) if metadata else None,
            ),
        )
        self.db.commit()

    def get_engaged_ids(self, persona_id: str) -> list[str]:
        """Get all target_post_ids this persona has engaged with."""
        rows = self.db.fetchall(
            "SELECT DISTINCT target_post_id FROM activity_log WHERE persona_id = ? AND success = 1",
            (persona_id,),
        )
        return [r["target_post_id"] for r in rows]

    def get_recent(self, persona_id: str, limit: int = 15) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM activity_log WHERE persona_id = ? AND success = 1 "
            "ORDER BY timestamp DESC LIMIT ?",
            (persona_id, limit),
        )
        return [dict(r) for r in rows]

    def get_paginated(
        self, persona_id: str, page: int = 1, limit: int = 50
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * limit
        total_row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM activity_log WHERE persona_id = ?",
            (persona_id,),
        )
        total = total_row["cnt"] if total_row else 0
        rows = self.db.fetchall(
            "SELECT * FROM activity_log WHERE persona_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (persona_id, limit, offset),
        )
        return [dict(r) for r in rows], total

    def get_stats(self, persona_id: str) -> dict:
        """Get engagement statistics for a persona."""
        total = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM activity_log WHERE persona_id = ?",
            (persona_id,),
        )
        by_type = self.db.fetchall(
            "SELECT action_type, COUNT(*) as cnt FROM activity_log "
            "WHERE persona_id = ? GROUP BY action_type",
            (persona_id,),
        )
        success_row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM activity_log WHERE persona_id = ? AND success = 1",
            (persona_id,),
        )
        recent = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM activity_log "
            "WHERE persona_id = ? AND success = 1 AND timestamp > datetime('now', '-1 day')",
            (persona_id,),
        )
        return {
            "total_actions": total["cnt"] if total else 0,
            "actions_by_type": {r["action_type"]: r["cnt"] for r in by_type},
            "success_rate": (success_row["cnt"] / total["cnt"]) if total and total["cnt"] > 0 else 0,
            "actions_last_24h": recent["cnt"] if recent else 0,
        }

    def count_since_last_original(self, persona_id: str) -> int:
        """Count successful engagements since last original post."""
        row = self.db.fetchone(
            "SELECT id FROM activity_log "
            "WHERE persona_id = ? AND action_type = 'original_post' AND success = 1 "
            "ORDER BY timestamp DESC LIMIT 1",
            (persona_id,),
        )
        if not row:
            total = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM activity_log WHERE persona_id = ? AND success = 1",
                (persona_id,),
            )
            return total["cnt"] if total else 0

        count = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM activity_log "
            "WHERE persona_id = ? AND success = 1 AND id > ?",
            (persona_id, row["id"]),
        )
        return count["cnt"] if count else 0
