"""Escalation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from xpersonas.api.deps import get_db
from xpersonas.storage.database import Database

router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get("/{persona_id}")
def list_escalations(persona_id: str, db: Database = Depends(get_db)):
    rows = db.fetchall(
        "SELECT * FROM escalations WHERE persona_id = ? ORDER BY created_at DESC",
        (persona_id,),
    )
    return [dict(r) for r in rows]


@router.post("/{escalation_id}/ack")
def acknowledge(escalation_id: str, db: Database = Depends(get_db)):
    db.execute(
        "UPDATE escalations SET acknowledged = 1 WHERE id = ?", (escalation_id,)
    )
    db.commit()
    return {"acknowledged": True}
