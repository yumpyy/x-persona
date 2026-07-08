"""Personal mode: track relationships and suggest connections."""

from __future__ import annotations

from xpersonas.agent.state import AgentState
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.contact_repo import ContactRepo


async def relationship_track(state: AgentState, config=None) -> dict:
    """Track interactions with contacts and suggest connections."""
    db: Database = config["configurable"]["db"]
    persona_id = state.get("persona_id", "")
    executed = state.get("executed_actions", [])

    if not executed:
        return {}

    contact_repo = ContactRepo(db)

    for entry in executed:
        if not entry.get("success"):
            continue
        action = entry.get("action", {})
        handle = action.get("target_author", "")
        if not handle:
            continue

        contact_repo.upsert_interaction(
            persona_id=persona_id,
            platform=state.get("platform", "x"),
            handle=handle,
            display_name=handle,
            interaction_type=action.get("action_type", ""),
        )

    return {}
