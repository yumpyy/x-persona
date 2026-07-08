"""Agent run repository."""

from __future__ import annotations

from datetime import datetime, timezone
from xpersonas.storage.database import Database


class RunRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, persona_id: str, strategy: str, config: dict | None = None) -> str:
        import uuid
        import json
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO agent_runs (id, persona_id, status, strategy, config, started_at) "
            "VALUES (?, ?, 'starting', ?, ?, ?)",
            (run_id, persona_id, strategy, json.dumps(config or {}), now),
        )
        self.db.commit()
        return run_id

    def update_status(self, run_id: str, status: str, **fields) -> None:
        sets = ["status = ?"]
        vals = [status]
        for k, v in fields.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(run_id)
        self.db.execute(
            f"UPDATE agent_runs SET {', '.join(sets)} WHERE id = ?", tuple(vals)
        )
        self.db.commit()

    def get_running(self, persona_id: str) -> dict | None:
        row = self.db.fetchone(
            "SELECT * FROM agent_runs WHERE persona_id = ? AND status = 'running' "
            "ORDER BY started_at DESC LIMIT 1",
            (persona_id,),
        )
        return dict(row) if row else None

    def list_running(self) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM agent_runs WHERE status = 'running' ORDER BY started_at DESC"
        )
        return [dict(r) for r in rows]
