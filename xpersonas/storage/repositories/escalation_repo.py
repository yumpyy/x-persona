"""Escalation repository."""

from __future__ import annotations

from xpersonas.storage.database import Database


class EscalationRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        persona_id: str,
        platform: str,
        reason: str,
        post_id: str = "",
        severity: str = "info",
    ) -> int:
        self.db.execute(
            "INSERT INTO escalations (persona_id, post_id, platform, reason, severity) "
            "VALUES (?, ?, ?, ?, ?)",
            (persona_id, post_id, platform, reason, severity),
        )
        self.db.commit()
        row = self.db.fetchone("SELECT last_insert_rowid() as id")
        return row["id"] if row else 0

    def list_for_persona(self, persona_id: str, limit: int = 50) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM escalations WHERE persona_id = ? ORDER BY created_at DESC LIMIT ?",
            (persona_id, limit),
        )
        return [dict(r) for r in rows]

    def acknowledge(self, escalation_id: int) -> None:
        self.db.execute(
            "UPDATE escalations SET acknowledged = 1 WHERE id = ?", (escalation_id,)
        )
        self.db.commit()

    def pending(self, persona_id: str) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM escalations WHERE persona_id = ? AND acknowledged = 0 "
            "ORDER BY created_at DESC",
            (persona_id,),
        )
        return [dict(r) for r in rows]
