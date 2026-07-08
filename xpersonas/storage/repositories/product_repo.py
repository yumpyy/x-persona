"""Product repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from xpersonas.storage.database import Database


class ProductRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        features: list[str] | None = None,
        pricing: str = "",
        buy_url: str = "",
        pain_points: list[str] | None = None,
        disclosure_rules: dict | None = None,
        frequency_cap_per_week: int = 3,
        cooldown_days: int = 90,
    ) -> dict:
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO products "
            "(id, tenant_id, name, description, features, pricing, buy_url, "
            "pain_points, disclosure_rules, frequency_cap_per_week, cooldown_days, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product_id, tenant_id, name, description,
                json.dumps(features or []), pricing, buy_url,
                json.dumps(pain_points or []), json.dumps(disclosure_rules or {}),
                frequency_cap_per_week, cooldown_days, now,
            ),
        )
        self.db.commit()
        return self.get(product_id)

    def get(self, product_id: str) -> dict | None:
        row = self.db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        return _row_to_dict(row) if row else None

    def list_for_tenant(self, tenant_id: str) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM products WHERE tenant_id = ? AND is_active = 1", (tenant_id,)
        )
        return [_row_to_dict(r) for r in rows]

    def update(self, product_id: str, **fields) -> dict | None:
        sets = []
        vals = []
        for k, v in fields.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(product_id)
        self.db.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        self.db.commit()
        return self.get(product_id)

    def delete(self, product_id: str) -> None:
        self.db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        self.db.commit()


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("features", "pain_points", "disclosure_rules"):
        if key in d and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d
