"""Hydrate thread context for reply/quote actions."""

from __future__ import annotations

from xpersonas.agent.state import AgentState
from xpersonas.platforms.base import PlatformAdapter


async def hydrate_context(state: AgentState, config=None) -> dict:
    """Fetch thread replies for posts we plan to reply to or quote."""
    adapter: PlatformAdapter = config["configurable"]["adapter"]
    pending = state.get("pending_actions", [])
    contexts = dict(state.get("thread_contexts", {}))

    text_actions = [a for a in pending if a.get("action_type") in ("reply", "quote")]

    for action in text_actions:
        post_id = action["target_id"]
        if post_id in contexts:
            continue
        try:
            replies = await adapter.get_replies(post_id, limit=15)
            contexts[post_id] = replies
        except Exception:
            contexts[post_id] = []

    return {"thread_contexts": contexts}
