#!/usr/bin/env python3
"""Test like and repost actions."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import BrowserSession
from src.utils.post import like, repost


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python tests/test_actions.py <status_id> [action]")
        print("  actions: like (default), repost, both")
        print("  e.g. uv run python tests/test_actions.py 2060820483797332132 like")
        sys.exit(1)

    status_id = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else "like"

    session = BrowserSession(headless=False)
    ctx = await session.start()
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    url = f"https://x.com/i/status/{status_id}"
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)

    if action in ("like", "both"):
        result = await like(ctx, status_id)
        print(f"Like:      {'✓' if result.success else '✗'}")

    if action in ("repost", "both"):
        result = await repost(ctx, status_id)
        print(f"Repost:    {'✓' if result.success else '✗'}")

    await session.stop()


if __name__ == "__main__":
    asyncio.run(main())
