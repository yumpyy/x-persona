"""Fetch content from the platform via adapter."""

from __future__ import annotations

from xpersonas.agent.state import AgentState
from xpersonas.platforms.base import PlatformAdapter


async def fetch_content(state: AgentState, config=None) -> dict:
    """Fetch feed posts or search results via the platform adapter."""
    adapter: PlatformAdapter = config["configurable"]["adapter"]
    engaged_ids = set(state.get("engaged_ids", []))
    seen_ids = set(state.get("seen_ids", []))
    strategy = state.get("persona_config", {}).get("engagement", {}).get("strategy", "active")

    if strategy in ("monitor_and_escalate", "competitive_intel", "support"):
        queries = state.get("persona_config", {}).get("promo", {}).get("search_queries", [])
        if not queries:
            queries = state.get("persona_config", {}).get("networking", {}).get("target_connections", [])
        all_posts = []
        for q in queries:
            posts = await adapter.search(q, limit=20)
            all_posts.extend(posts)
    else:
        posts, _ = await adapter.fetch_feed(cursor=state.get("feed_cursor"), limit=20)
        all_posts = posts

    new_posts = [p for p in all_posts if p.id not in engaged_ids and p.id not in seen_ids]

    return {
        "feed_posts": new_posts,
        "seen_ids": list(seen_ids | {p.id for p in new_posts}),
    }
