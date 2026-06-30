"""Like a post by its status ID."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from playwright.async_api import Page, BrowserContext

from x_personas.utils._helpers import goto_and_wait, safe_click
from x_personas.utils.exceptions import XActionError
from x_personas.utils.selectors import LIKE_BUTTON, UNLIKE_BUTTON, TWEET_ARTICLE
from x_personas.models.post import ActionResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger("x_persona")


async def like(
    context_or_page: BrowserContext | Page,
    status_id: str,
    *,
    handle: str | None = None,
) -> ActionResult:
    """Like a tweet by its status ID.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
    status_id:
        The numeric status ID to like.
    handle:
        Optional author handle for building the URL.

    Returns
    -------
    ActionResult
        True-compatible action result if successful or already liked.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Liking post %s", status_id)

    try:
        article = page.locator(TWEET_ARTICLE).first
        await article.wait_for(state="visible", timeout=15_000)

        # Check if already liked
        unlike_btn = article.locator(UNLIKE_BUTTON)
        if await unlike_btn.count() > 0:
            logger.info("Post %s is already liked", status_id)
            return ActionResult(success=True)

        # Click the like button
        like_btn = article.locator(LIKE_BUTTON).first
        await like_btn.wait_for(state="visible", timeout=5_000)
        await like_btn.click()
    except Exception as exc:
        err_msg = f"Failed to like post {status_id}: {exc}"
        logger.error(err_msg)
        return ActionResult(success=False, error=err_msg)

    # Verify the like registered (button should flip to "unlike")
    try:
        await article.locator(UNLIKE_BUTTON).first.wait_for(
            state="visible", timeout=5_000
        )
    except Exception:
        logger.warning("Like button did not flip — may not have registered")
        return ActionResult(success=False, error="Like verification timed out")

    logger.info("Liked post %s", status_id)
    return ActionResult(success=True)


def _build_status_url(status_id: str, handle: str | None) -> str:
    """Build a tweet URL. Uses /i/status/ if handle is unknown."""
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"
