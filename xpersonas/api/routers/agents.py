"""Agent lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from xpersonas.api.deps import get_db
from xpersonas.api.schemas import AgentStatusResponse
from xpersonas.storage.database import Database

router = APIRouter(prefix="/agents", tags=["agents"])

# Global runner reference (set by server startup)
_runner = None


def set_runner(runner):
    global _runner
    _runner = runner


@router.post("/start/{persona_id}", response_model=AgentStatusResponse)
async def start_agent(
    persona_id: str,
    visible: bool = Query(False, description="Show browser window"),
    ask: bool = Query(False, description="Confirm each action interactively"),
    db: Database = Depends(get_db),
):
    if not _runner:
        raise HTTPException(503, "Agent runner not available")
    try:
        instance = await _runner.start_persona(persona_id, visible=visible, ask=ask)
        return AgentStatusResponse(
            persona_id=instance.persona_id,
            status=instance.status,
            strategy=instance.strategy,
            cycles_completed=instance.cycles,
            started_at=instance.started_at,
            last_cycle_at=None,
            error_message=None,
        )
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/stop/{persona_id}")
async def stop_agent(persona_id: str):
    if not _runner:
        raise HTTPException(503, "Agent runner not available")
    await _runner.stop_persona(persona_id)
    return {"status": "stopped", "persona_id": persona_id}


@router.get("/status", response_model=list[AgentStatusResponse])
async def list_agents():
    if not _runner:
        return []
    return [
        AgentStatusResponse(
            persona_id=i.persona_id,
            status=i.status,
            strategy=i.strategy,
            cycles_completed=i.cycles,
            started_at=i.started_at,
            last_cycle_at=i.last_cycle_at,
            error_message=i.error_message,
        )
        for i in _runner.instances.values()
    ]


@router.get("/status/{persona_id}", response_model=AgentStatusResponse)
async def get_agent_status(persona_id: str):
    if not _runner:
        raise HTTPException(503, "Agent runner not available")
    if persona_id not in _runner.instances:
        raise HTTPException(404, "Agent not running")
    i = _runner.instances[persona_id]
    return AgentStatusResponse(
        persona_id=i.persona_id,
        status=i.status,
        strategy=i.strategy,
        cycles_completed=i.cycles,
        started_at=i.started_at,
        last_cycle_at=i.last_cycle_at,
        error_message=i.error_message,
    )
