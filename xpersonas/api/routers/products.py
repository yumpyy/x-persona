"""Product CRUD endpoints (brand mode)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from xpersonas.api.deps import get_db
from xpersonas.api.schemas import ProductCreate, ProductResponse
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.product_repo import ProductRepo

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse)
def create_product(body: ProductCreate, tenant_id: str, db: Database = Depends(get_db)):
    repo = ProductRepo(db)
    product = repo.create(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        features=body.features,
        pricing=body.pricing,
        buy_url=body.buy_url,
        pain_points=body.pain_points,
        disclosure_rules=body.disclosure_rules,
        frequency_cap_per_week=body.frequency_cap_per_week,
        cooldown_days=body.cooldown_days,
    )
    return ProductResponse(**product)


@router.get("", response_model=list[ProductResponse])
def list_products(tenant_id: str, db: Database = Depends(get_db)):
    repo = ProductRepo(db)
    return [ProductResponse(**p) for p in repo.list_for_tenant(tenant_id)]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Database = Depends(get_db)):
    repo = ProductRepo(db)
    product = repo.get(product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return ProductResponse(**product)


@router.delete("/{product_id}")
def delete_product(product_id: str, db: Database = Depends(get_db)):
    repo = ProductRepo(db)
    repo.delete(product_id)
    return {"deleted": True}
