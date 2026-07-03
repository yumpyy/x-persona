from __future__ import annotations

import asyncio

from x_personas.agent.log import log
from x_personas.agent.rate_limiter import scroll_delay
from x_personas.agent.state import PersonaState
from x_personas.utils.feed import scroll_down

SCROLLS_PER_CYCLE = 3


async def scroll_page(state: PersonaState, config=None) -> dict:
    configurable = (config or {}).get("configurable", {})
    home_page = configurable.get("home_page")
    pause_event = configurable.get("cursor_pause_event")

    if home_page is None:
        log("scroll_page: no home_page in config, skipping")
        return {}

    if pause_event is not None:
        pause_event.clear()

    delay = scroll_delay()
    log(f"scroll_page: waiting {delay:.0f}s, then scrolling {SCROLLS_PER_CYCLE}x")
    await asyncio.sleep(delay)
    await scroll_down(home_page, times=SCROLLS_PER_CYCLE)

    scroll_count = state.get("scroll_count", 0) + SCROLLS_PER_CYCLE

    if pause_event is not None:
        pause_event.set()

    return {
        "scroll_count": scroll_count,
    }
