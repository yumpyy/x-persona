#!/usr/bin/env python3
"""Test fetching the home timeline feed."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from x_personas.utils.browser import BrowserSession
from x_personas.utils.feed import get_home_feed


def _fmt(n: int | None) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


async def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    session = BrowserSession(headless=False)
    ctx = await session.start()
    feed = await get_home_feed(ctx, scroll_count=count)

    print(f"Fetched {len(feed.posts)} posts\n")
    for i, p in enumerate(feed.posts[:15]):
        flags = ""
        if p.is_retweet:
            flags += " [RT]"
        if p.is_reply:
            flags += " [REPLY]"
        if p.is_quote:
            flags += " [QUOTE]"
        if p.is_pinned:
            flags += " [PINNED]"
        if p.is_sponsored:
            flags += " [AD]"

        print(
            f"{i+1:>2}. @{p.handle}{flags}\n"
            f"     {p.text[:120]}\n"
            f"     ♥ {_fmt(p.metrics.likes)}  🔁 {_fmt(p.metrics.retweets)}  "
            f"💬 {_fmt(p.metrics.replies)}  👁 {_fmt(p.metrics.views)}  "
            f"📷 {len(p.media_urls)}\n"
        )
        for url in p.media_urls:
            print(f"        {url}")
        if p.media_urls:
            print()

    await session.stop()


if __name__ == "__main__":
    asyncio.run(main())
