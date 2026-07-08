"""Persona management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from xpersonas.api.deps import get_db
from xpersonas.api.schemas import PersonaCreate, PersonaResponse
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.persona_repo import PersonaRepo

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=PersonaResponse)
async def create_persona(body: PersonaCreate, db: Database = Depends(get_db)):
    repo = PersonaRepo(db)
    # Get tenant_id from first tenant for now (single-tenant mode)
    tenants = db.fetchall("SELECT id FROM tenants WHERE is_active = 1 LIMIT 1")
    if not tenants:
        raise HTTPException(400, "No tenant found. Create a tenant first.")
    tenant_id = tenants[0]["id"]
    persona = repo.create(tenant_id, body.platform, body.handle, body.display_name, body.config)
    strategy = body.config.get("engagement", {}).get("strategy", "active")
    return PersonaResponse(
        id=persona["id"],
        tenant_id=persona["tenant_id"],
        platform=persona["platform"],
        handle=persona["handle"],
        display_name=persona["display_name"],
        strategy=strategy,
        is_active=persona["is_active"],
        created_at=persona["created_at"],
        updated_at=persona["updated_at"],
    )


@router.get("/{persona_id}")
async def get_persona(persona_id: str, db: Database = Depends(get_db)):
    repo = PersonaRepo(db)
    persona = repo.get(persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    return persona


@router.get("", response_model=list[PersonaResponse])
async def list_personas(db: Database = Depends(get_db)):
    repo = PersonaRepo(db)
    tenants = db.fetchall("SELECT id FROM tenants WHERE is_active = 1")
    result = []
    for t in tenants:
        for p in repo.list_for_tenant(t["id"]):
            strategy = p.get("persona_config", {}).get("engagement", {}).get("strategy", "active")
            result.append(PersonaResponse(
                id=p["id"],
                tenant_id=p["tenant_id"],
                platform=p["platform"],
                handle=p["handle"],
                display_name=p["display_name"],
                strategy=strategy,
                is_active=p["is_active"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
            ))
    return result


@router.patch("/{persona_id}")
async def update_persona(persona_id: str, body: PersonaCreate, db: Database = Depends(get_db)):
    repo = PersonaRepo(db)
    persona = repo.update(persona_id, handle=body.handle, display_name=body.display_name, persona_config=body.config)
    if not persona:
        raise HTTPException(404, "Persona not found")
    return persona


@router.delete("/{persona_id}")
async def delete_persona(persona_id: str, db: Database = Depends(get_db)):
    repo = PersonaRepo(db)
    repo.delete(persona_id)
    return {"status": "deleted"}
