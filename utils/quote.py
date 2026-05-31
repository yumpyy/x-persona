"""Quote-tweet a post by its status ID.

Navigates to the tweet, clicks the repost button, selects "Quote",
types the quote text, optionally attaches media, and publishes.

Usage::

    page = await bm.get_page("cneuralnetwork")
    new_id = await quote(page, "1234567890", "This is brilliant 🔥")
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from utils._helpers import (
    attach_media,
    extract_status_id,
    goto_and_wait,
    safe_click,
    safe_type,
)
from utils.exceptions import XActionError
from utils.selectors import (
    COMPOSE_POST_BUTTON,
    COMPOSE_TEXTBOX,
    QUOTE_MENU_ITEM,
    REPOST_BUTTON,
    TWEET_ARTICLE,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")


async def quote(
    page: Page,
    status_id: str,
    text: str,
    *,
    handle: str | None = None,
    media_paths: list[Path] | None = None,
    timeout: int = 30_000,
) -> str:
    """Quote-tweet a post with custom text and optional media.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    status_id:
        The numeric status ID of the post to quote.
    text:
        The quote text to add above the embedded post.
    handle:
        Optional author handle for building the URL.
    media_paths:
        Optional list of image/video file paths to attach.
    timeout:
        Maximum time (ms) to wait for the quote to be published.

    Returns
    -------
    str
        The status ID of the newly published quote tweet.
    """
    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Quoting post %s", status_id)

    article = page.locator(TWEET_ARTICLE).first
    await article.wait_for(state="visible", timeout=15_000)

    # Click the repost button to open the menu
    repost_btn = article.locator(REPOST_BUTTON).first
    try:
        await repost_btn.wait_for(state="visible", timeout=5_000)
        await repost_btn.click()
    except Exception as exc:
        raise XActionError(f"Failed to click repost button: {exc}") from exc

    # Select "Quote" from the dropdown
    try:
        await safe_click(page, QUOTE_MENU_ITEM, timeout=5_000)
    except Exception as exc:
        raise XActionError(f"Failed to select Quote from menu: {exc}") from exc

    # Wait for the compose dialog to appear
    await asyncio.sleep(1)

    # Type the quote text
    await safe_type(page, COMPOSE_TEXTBOX, text)

    # Attach media if provided
    if media_paths:
        await attach_media(page, media_paths)

    # Click the Post button
    await safe_click(page, COMPOSE_POST_BUTTON)

    # Wait for confirmation
    new_status_id = await _wait_for_quote_confirmation(page, timeout=timeout)

    logger.info("Quote published: %s", new_status_id)
    return new_status_id


async def _wait_for_quote_confirmation(page: Page, *, timeout: int) -> str:
    """Wait for the quote tweet to be published and extract its status ID."""
    try:
        # Wait for the compose modal to close / page to update
        await asyncio.sleep(3)

        # Check current URL for a status ID
        current_url = page.url
        status_id = extract_status_id(current_url)
        if status_id:
            return status_id

        # Scan the first tweet for the new quote
        permalink = page.locator(
            'article[data-testid="tweet"] a[href*="/status/"]'
        ).first
        try:
            href = await permalink.get_attribute("href", timeout=5_000)
            if href:
                sid = extract_status_id(href)
                if sid:
                    return sid
        except Exception:
            pass

        logger.warning("Could not extract quote status ID")
        return "unknown"

    except Exception as exc:
        raise XActionError(f"Quote confirmation timed out: {exc}") from exc


def _build_status_url(status_id: str, handle: str | None) -> str:
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"
