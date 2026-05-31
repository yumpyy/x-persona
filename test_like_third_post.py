"""Test script: Log in as @imnot_linear, scrape home feed, like the 3rd post."""

import asyncio
import logging

from utils import BrowserManager, get_home_feed, like

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("test")

HANDLE = "imnot_linear"


async def main() -> None:
    async with BrowserManager(headless=False) as bm:
        # Step 1: Login (opens browser for manual login if no saved session)
        auth_path = bm._auth_state_path(HANDLE)
        if not auth_path.is_file():
            logger.info("No saved session — starting manual login flow…")
            await bm.login(HANDLE)
            logger.info("Login complete!")
        else:
            logger.info("Using saved session for @%s", HANDLE)

        # Step 2: Get following feed
        page = await bm.get_page(HANDLE)
        logger.info("Fetching following feed…")
        feed = await get_home_feed(page, count=5, tab="following")

        logger.info("Got %d posts from feed:", len(feed))
        for i, post in enumerate(feed, 1):
            logger.info(
                "  [%d] @%s: %s (id: %s)",
                i,
                post.author_handle,
                post.text[:80] + ("…" if len(post.text) > 80 else ""),
                post.post_id,
            )

        if len(feed) < 3:
            logger.error("Feed has fewer than 3 posts — cannot like the 3rd one")
            await page.close()
            return

        # Step 3: Like the 3rd post
        target = feed[2]  # 0-indexed → 3rd post
        logger.info(
            "Liking 3rd post by @%s (id: %s): %s",
            target.author_handle,
            target.post_id,
            target.text[:60],
        )
        success = await like(page, target.post_id, handle=target.author_handle)

        if success:
            logger.info("✓ Successfully liked the 3rd post!")
        else:
            logger.warning("✗ Like may not have registered")

        await page.close()


if __name__ == "__main__":
    asyncio.run(main())
