#!/usr/bin/env python3
"""Test like and repost actions."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import BrowserManager
from src.utils.like import like
from src.utils.repost import repost


async def main():
    if len(sys.argv) < 3:
        print("Usage: uv run python tests/test_actions.py <handle> <status_id> [action]")
        print("  actions: like (default), repost, both")
        print("  e.g. uv run python tests/test_actions.py imnot_linear 2060820483797332132 like")
        sys.exit(1)

    handle = sys.argv[1]
    status_id = sys.argv[2]
    action = sys.argv[3].lower() if len(sys.argv) > 3 else "like"

    async with BrowserManager(headless=False) as bm:
        auth_path = bm._auth_state_path(handle)
        if not auth_path.is_file():
            print(f"No saved session for @{handle} - opening manual login flow...")
            await bm.login(handle)

        page = await bm.get_page(handle)

        if action in ("like", "both"):
            result = await like(page, status_id)
            print(f"Like:      {'✓' if result.success else '✗'}")

        if action in ("repost", "both"):
            result = await repost(page, status_id)
            print(f"Repost:    {'✓' if result.success else '✗'}")

        await page.close()


if __name__ == "__main__":
    asyncio.run(main())
