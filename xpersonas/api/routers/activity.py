"""Activity log endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from xpersonas.api.deps import get_db
from xpersonas.api.schemas import ActivityLogEntry, ActivityStats
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.activity_repo import ActivityRepo

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/{persona_id}", response_model=list[ActivityLogEntry])
async def get_activity(
    persona_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    repo = ActivityRepo(db)
    entries, _ = repo.get_paginated(persona_id, page, limit)
    return [
        ActivityLogEntry(
            id=e["id"],
            timestamp=e["timestamp"],
            platform=e["platform"],
            action_type=e["action_type"],
            target_post_id=e["target_post_id"],
            target_author=e["target_author"],
            content=e["content"],
            score=e["score"],
            reason=e["reason"],
            success=bool(e["success"]),
            error=e["error"],
        )
        for e in entries
    ]


@router.get("/{persona_id}/stats", response_model=ActivityStats)
async def get_stats(persona_id: str, db: Database = Depends(get_db)):
    repo = ActivityRepo(db)
    stats = repo.get_stats(persona_id)
    return ActivityStats(**stats)


@router.get("/{persona_id}/dedup")
async def get_engaged_ids(persona_id: str, db: Database = Depends(get_db)):
    repo = ActivityRepo(db)
    return {"engaged_ids": repo.get_engaged_ids(persona_id)}
