"""Scroll the page down."""

from __future__ import annotations

import asyncio
import random

from xpersonas.agent.state import AgentState
from xpersonas.platforms.base import PlatformAdapter

SCROLLS_PER_CYCLE = 3


async def scroll_page(state: AgentState, config=None) -> dict:
    """Scroll the feed page down with human-like timing."""
    adapter: PlatformAdapter = config["configurable"]["adapter"]

    # Random delay before scrolling
    await asyncio.sleep(random.uniform(5.0, 15.0))

    await adapter.scroll(times=SCROLLS_PER_CYCLE)

    current = state.get("scroll_count", 0)
    return {"scroll_count": current + SCROLLS_PER_CYCLE}
