"""Health check and metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from xpersonas.api.schemas import HealthResponse
from xpersonas.platforms.registry import list_platforms

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        platforms=list_platforms(),
    )
