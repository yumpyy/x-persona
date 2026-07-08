"""Persona repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from xpersonas.storage.database import Database


class PersonaRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        tenant_id: str,
        platform: str,
        handle: str,
        display_name: str,
        persona_config: dict,
    ) -> dict:
        persona_id = f"p_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO personas (id, tenant_id, platform, handle, display_name, persona_config, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (persona_id, tenant_id, platform, handle, display_name, json.dumps(persona_config), now, now),
        )
        self.db.commit()
        return self.get(persona_id)

    def get(self, persona_id: str) -> dict | None:
        row = self.db.fetchone("SELECT * FROM personas WHERE id = ?", (persona_id,))
        if row:
            d = dict(row)
            d["persona_config"] = json.loads(d["persona_config"])
            return d
        return None

    def list_for_tenant(self, tenant_id: str) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM personas WHERE tenant_id = ? AND is_active = 1", (tenant_id,)
        )
        result = []
        for r in rows:
            d = dict(r)
            d["persona_config"] = json.loads(d["persona_config"])
            result.append(d)
        return result

    def list_all(self) -> list[dict]:
        rows = self.db.fetchall("SELECT * FROM personas WHERE is_active = 1")
        result = []
        for r in rows:
            d = dict(r)
            d["persona_config"] = json.loads(d["persona_config"])
            result.append(d)
        return result

    def update(self, persona_id: str, **fields: object) -> dict | None:
        sets = []
        vals: list[object] = []
        for k, v in fields.items():
            if k == "persona_config":
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        now = datetime.now(timezone.utc).isoformat()
        sets.append("updated_at = ?")
        vals.append(now)
        vals.append(persona_id)
        self.db.execute(f"UPDATE personas SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        self.db.commit()
        return self.get(persona_id)

    def delete(self, persona_id: str) -> None:
        self.db.execute("UPDATE personas SET is_active = 0 WHERE id = ?", (persona_id,))
        self.db.commit()
