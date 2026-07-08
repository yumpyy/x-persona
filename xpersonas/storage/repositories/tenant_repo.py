"""Tenant repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from xpersonas.storage.database import Database


class TenantRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, name: str, mode: str = "brand", config: dict | None = None) -> dict:
        tenant_id = f"t_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO tenants (id, name, mode, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, name, mode, json.dumps(config or {}), now),
        )
        self.db.commit()
        return self.get(tenant_id)

    def get(self, tenant_id: str) -> dict | None:
        row = self.db.fetchone("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        return [dict(r) for r in self.db.fetchall("SELECT * FROM tenants WHERE is_active = 1")]

    def update(self, tenant_id: str, **fields: object) -> dict | None:
        sets = []
        vals: list[object] = []
        for k, v in fields.items():
            if k == "config":
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(tenant_id)
        self.db.execute(f"UPDATE tenants SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        self.db.commit()
        return self.get(tenant_id)

    def delete(self, tenant_id: str) -> None:
        self.db.execute("UPDATE tenants SET is_active = 0 WHERE id = ?", (tenant_id,))
        self.db.commit()
