"""Contact tracking endpoints (personal mode)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from xpersonas.api.deps import get_db
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.contact_repo import ContactRepo

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/{persona_id}")
def list_contacts(persona_id: str, db: Database = Depends(get_db)):
    repo = ContactRepo(db)
    return repo.list_for_persona(persona_id)


@router.get("/{persona_id}/ready")
def ready_contacts(persona_id: str, db: Database = Depends(get_db)):
    repo = ContactRepo(db)
    return repo.get_ready_for_connection(persona_id)


@router.get("/{persona_id}/stats")
def contact_stats(persona_id: str, db: Database = Depends(get_db)):
    contacts = ContactRepo(db).list_for_persona(persona_id)
    by_stage = {}
    for c in contacts:
        s = c.get("stage", "stranger")
        by_stage[s] = by_stage.get(s, 0) + 1
    return {
        "total": len(contacts),
        "by_stage": by_stage,
        "average_rapport": sum(c.get("rapport_score", 0) for c in contacts) / max(len(contacts), 1),
    }
