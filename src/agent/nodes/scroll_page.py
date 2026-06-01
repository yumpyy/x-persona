from __future__ import annotations

import asyncio

from src.agent.log import log
from src.agent.rate_limiter import scroll_delay
from src.agent.state import PersonaState
from src.utils.feed import scroll_down

SCROLLS_PER_CYCLE = 3


async def scroll_page(state: PersonaState, config=None) -> dict:
    configurable = (config or {}).get("configurable", {})
    home_page = configurable.get("home_page")

    if home_page is None:
        log("scroll_page: no home_page in config, skipping")
        return {}

    delay = scroll_delay()
    log(f"scroll_page: waiting {delay:.0f}s, then scrolling {SCROLLS_PER_CYCLE}x")
    await asyncio.sleep(delay)
    await scroll_down(home_page, times=SCROLLS_PER_CYCLE)

    scroll_count = state.get("scroll_count", 0) + SCROLLS_PER_CYCLE

    return {
        "scroll_count": scroll_count,
    }
