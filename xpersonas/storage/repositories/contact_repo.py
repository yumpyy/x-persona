"""Contact repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from xpersonas.storage.database import Database


class ContactRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert_interaction(
        self,
        persona_id: str,
        platform: str,
        handle: str,
        display_name: str = "",
        interaction_type: str = "",
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.db.fetchone(
            "SELECT * FROM contacts WHERE persona_id = ? AND handle = ?",
            (persona_id, handle),
        )

        if existing:
            new_count = existing["interaction_count"] + 1
            self.db.execute(
                "UPDATE contacts SET interaction_count = ?, last_interaction_at = ?, updated_at = ? WHERE id = ?",
                (new_count, now, now, existing["id"]),
            )
            contact_id = existing["id"]
        else:
            contact_id = f"c_{uuid.uuid4().hex[:12]}"
            self.db.execute(
                "INSERT INTO contacts "
                "(id, persona_id, platform, handle, display_name, interaction_count, "
                "last_interaction_at, stage, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, 'stranger', ?, ?)",
                (contact_id, persona_id, platform, handle, display_name, now, now, now),
            )

        # Record interaction
        self.db.execute(
            "INSERT INTO contact_interactions (contact_id, interaction_type, created_at) VALUES (?, ?, ?)",
            (contact_id, interaction_type, now),
        )
        self.db.commit()
        return self.get(contact_id)

    def get(self, contact_id: str) -> dict | None:
        row = self.db.fetchone("SELECT * FROM contacts WHERE id = ?", (contact_id,))
        return dict(row) if row else None

    def list_for_persona(self, persona_id: str, stage: str | None = None) -> list[dict]:
        if stage:
            rows = self.db.fetchall(
                "SELECT * FROM contacts WHERE persona_id = ? AND stage = ? ORDER BY rapport_score DESC",
                (persona_id, stage),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM contacts WHERE persona_id = ? ORDER BY rapport_score DESC",
                (persona_id,),
            )
        return [dict(r) for r in rows]

    def get_ready_for_connection(self, persona_id: str) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM contacts WHERE persona_id = ? AND stage = 'connect_ready' ORDER BY rapport_score DESC",
            (persona_id,),
        )
        return [dict(r) for r in rows]
