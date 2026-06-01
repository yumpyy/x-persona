from __future__ import annotations

from typing import Any
from langchain_core.runnables import RunnableConfig

from src.agent.log import log
from src.agent.state import PersonaState
from src.models.engagement import ActionType
from src.models.post import PostData
from src.utils.post import get_post_data


async def hydrate_replies(state: PersonaState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Scrape and cache thread replies dynamically for pending reply/quote actions.

    Ensures that content generation is fully context-aware, preventing repetitive
    responses and enabling relationship-building reply-to-reply chains with close mutuals.
    """
    pending = state.get("pending_actions", [])
    configurable = (config or {}).get("configurable", {})
    ctx = configurable.get("browser_context")

    text_actions = [
        a for a in pending if a.action_type in (ActionType.REPLY, ActionType.QUOTE)
    ]

    if not text_actions:
        log("hydrate_replies: no pending reply or quote actions to hydrate")
        return {"thread_contexts": state.get("thread_contexts", {})}

    thread_contexts: dict[str, PostData] = dict(state.get("thread_contexts", {}))

    if ctx is None:
        log("hydrate_replies: WARNING: browser context is None, skipping context hydration")
        return {"thread_contexts": thread_contexts}

    log(f"hydrate_replies: hydrating thread context for {len(text_actions)} action(s)")

    for action in text_actions:
        status_id = action.target_status_id
        if status_id in thread_contexts:
            log(f"  hydrate_replies: status_id={status_id} already cached")
            continue

        try:
            log(f"  hydrate_replies: scraping replies for status_id={status_id} via get_post_data")
            post_data = await get_post_data(ctx, status_id)
            thread_contexts[status_id] = post_data
            log(f"    ✓ parsed {len(post_data.replies)} replies on thread")
        except Exception as e:
            log(f"    ✗ failed to hydrate status_id={status_id}: {e}")

    return {"thread_contexts": thread_contexts}
