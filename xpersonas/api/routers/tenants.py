"""Tenant management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from xpersonas.api.auth import generate_api_key, hash_key
from xpersonas.api.deps import get_db
from xpersonas.api.schemas import TenantCreate, TenantResponse
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.tenant_repo import TenantRepo

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse)
async def create_tenant(body: TenantCreate, db: Database = Depends(get_db)):
    repo = TenantRepo(db)
    tenant = repo.create(body.name, body.mode, body.config)
    return TenantResponse(**tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: Database = Depends(get_db)):
    repo = TenantRepo(db)
    tenant = repo.get(tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return TenantResponse(**tenant)


@router.get("", response_model=list[TenantResponse])
async def list_tenants(db: Database = Depends(get_db)):
    repo = TenantRepo(db)
    return [TenantResponse(**t) for t in repo.list_all()]


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, body: TenantCreate, db: Database = Depends(get_db)):
    repo = TenantRepo(db)
    tenant = repo.update(tenant_id, name=body.name, mode=body.mode, config=body.config)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return TenantResponse(**tenant)


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, db: Database = Depends(get_db)):
    repo = TenantRepo(db)
    repo.delete(tenant_id)
    return {"status": "deleted"}


@router.post("/{tenant_id}/api-keys")
async def create_api_key(tenant_id: str, db: Database = Depends(get_db)):
    raw_key = generate_api_key()
    key_hash = hash_key(raw_key)
    db.execute(
        "INSERT INTO api_keys (tenant_id, key_hash, created_at) VALUES (?, ?, datetime('now'))",
        (tenant_id, key_hash),
    )
    db.commit()
    return {"api_key": raw_key, "tenant_id": tenant_id}
