"""Like a post by its status ID.

Navigates to the tweet and toggles the like button.

Usage::

    page = await bm.get_page("cneuralnetwork")
    success = await like(page, "1234567890")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from utils._helpers import goto_and_wait, safe_click
from utils.exceptions import XActionError
from utils.selectors import LIKE_BUTTON, UNLIKE_BUTTON, TWEET_ARTICLE

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")


async def like(page: Page, status_id: str, *, handle: str | None = None) -> bool:
    """Like a tweet by its status ID.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    status_id:
        The numeric status ID to like.
    handle:
        Optional author handle for building the URL. If not provided,
        the function navigates via the generic status endpoint.

    Returns
    -------
    bool
        ``True`` if the like action succeeded (or was already liked).
    """
    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Liking post %s", status_id)

    article = page.locator(TWEET_ARTICLE).first
    await article.wait_for(state="visible", timeout=15_000)

    # Check if already liked
    unlike_btn = article.locator(UNLIKE_BUTTON)
    if await unlike_btn.count() > 0:
        logger.info("Post %s is already liked", status_id)
        return True

    # Click the like button
    like_btn = article.locator(LIKE_BUTTON).first
    try:
        await like_btn.wait_for(state="visible", timeout=5_000)
        await like_btn.click()
    except Exception as exc:
        raise XActionError(f"Failed to like post {status_id}: {exc}") from exc

    # Verify the like registered (button should flip to "unlike")
    try:
        await article.locator(UNLIKE_BUTTON).first.wait_for(
            state="visible", timeout=5_000
        )
    except Exception:
        logger.warning("Like button did not flip — may not have registered")
        return False

    logger.info("Liked post %s", status_id)
    return True


def _build_status_url(status_id: str, handle: str | None) -> str:
    """Build a tweet URL. Uses /i/status/ if handle is unknown."""
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    # X supports /i/status/<id> as a generic redirect
    return f"https://x.com/i/status/{status_id}"
