from __future__ import annotations

import asyncio
import random

from src.agent.log import log
from src.agent.state import PersonaState
from src.utils.feed import _parse_article, navigate_home


async def scroll_feed(state: PersonaState, config=None) -> dict:
    configurable = (config or {}).get("configurable", {})
    home_page = configurable.get("home_page")
    ctx = configurable.get("browser_context")

    if home_page is None:
        if ctx is None:
            return {
                "feed_posts": [],
                "error": "No browser context or home_page in config",
            }
        home_page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await navigate_home(home_page)

    engaged = set(state.get("engaged_ids", []))
    seen = set(state.get("seen_post_ids", []))
    new_posts = []

    article_els = await home_page.query_selector_all('article[data-testid="tweet"]')
    for article in article_els:
        try:
            post = await _parse_article(article)
            if post is None:
                continue
            if post.status_id in seen:
                continue
            if post.status_id in engaged:
                continue
            new_posts.append(post)
            seen.add(post.status_id)
        except Exception:
            continue

    log(f"scroll: {len(new_posts)} new posts (session seen: {len(seen)}, history engaged: {len(engaged)})")

    return {
        "feed_posts": new_posts,
        "seen_post_ids": list(seen),
    }
