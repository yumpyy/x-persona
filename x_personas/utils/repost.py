"""Repost (retweet) a tweet by its status ID."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from playwright.async_api import Page, BrowserContext

from x_personas.utils._helpers import goto_and_wait, safe_click
from x_personas.utils.exceptions import XActionError
from x_personas.utils.selectors import (
    REPOST_BUTTON,
    REPOST_MENU_ITEM,
    TWEET_ARTICLE,
    UNREPOST_BUTTON,
)
from x_personas.models.post import ActionResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger("x_persona")


async def repost(
    context_or_page: BrowserContext | Page,
    status_id: str,
    *,
    handle: str | None = None,
) -> ActionResult:
    """Repost a tweet by its status ID.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
    status_id:
        The numeric status ID to repost.
    handle:
        Optional author handle for building the URL.

    Returns
    -------
    ActionResult
        True-compatible action result if successful or already reposted.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Reposting post %s", status_id)

    try:
        article = page.locator(TWEET_ARTICLE).first
        await article.wait_for(state="visible", timeout=15_000)

        # Check if already reposted
        unrepost_btn = article.locator(UNREPOST_BUTTON)
        if await unrepost_btn.count() > 0:
            logger.info("Post %s is already reposted", status_id)
            return ActionResult(success=True)

        # Click the repost button to open the menu
        repost_btn = article.locator(REPOST_BUTTON).first
        await repost_btn.wait_for(state="visible", timeout=5_000)
        await repost_btn.click()

        # Click "Repost" in the dropdown menu
        await safe_click(page, REPOST_MENU_ITEM, timeout=5_000)
    except Exception as exc:
        err_msg = f"Failed to repost: {exc}"
        logger.error(err_msg)
        return ActionResult(success=False, error=err_msg)

    # Verify the repost registered
    try:
        await article.locator(UNREPOST_BUTTON).first.wait_for(
            state="visible", timeout=5_000
        )
    except Exception:
        logger.warning("Repost button did not flip — may not have registered")
        return ActionResult(success=False, error="Repost verification timed out")

    logger.info("Reposted post %s", status_id)
    return ActionResult(success=True)


def _build_status_url(status_id: str, handle: str | None) -> str:
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"
