"""Repost (retweet) a tweet by its status ID.

Navigates to the tweet, clicks the repost button, and confirms.

Usage::

    page = await bm.get_page("cneuralnetwork")
    success = await repost(page, "1234567890")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from utils._helpers import goto_and_wait, safe_click
from utils.exceptions import XActionError
from utils.selectors import (
    REPOST_BUTTON,
    REPOST_MENU_ITEM,
    TWEET_ARTICLE,
    UNREPOST_BUTTON,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")


async def repost(page: Page, status_id: str, *, handle: str | None = None) -> bool:
    """Repost a tweet by its status ID.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    status_id:
        The numeric status ID to repost.
    handle:
        Optional author handle for building the URL.

    Returns
    -------
    bool
        ``True`` if the repost succeeded (or was already reposted).
    """
    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Reposting post %s", status_id)

    article = page.locator(TWEET_ARTICLE).first
    await article.wait_for(state="visible", timeout=15_000)

    # Check if already reposted
    unrepost_btn = article.locator(UNREPOST_BUTTON)
    if await unrepost_btn.count() > 0:
        logger.info("Post %s is already reposted", status_id)
        return True

    # Click the repost button to open the menu
    repost_btn = article.locator(REPOST_BUTTON).first
    try:
        await repost_btn.wait_for(state="visible", timeout=5_000)
        await repost_btn.click()
    except Exception as exc:
        raise XActionError(f"Failed to click repost button: {exc}") from exc

    # Click "Repost" in the dropdown menu
    try:
        await safe_click(page, REPOST_MENU_ITEM, timeout=5_000)
    except Exception as exc:
        raise XActionError(f"Failed to confirm repost: {exc}") from exc

    # Verify the repost registered
    try:
        await article.locator(UNREPOST_BUTTON).first.wait_for(
            state="visible", timeout=5_000
        )
    except Exception:
        logger.warning("Repost button did not flip — may not have registered")
        return False

    logger.info("Reposted post %s", status_id)
    return True


def _build_status_url(status_id: str, handle: str | None) -> str:
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"
