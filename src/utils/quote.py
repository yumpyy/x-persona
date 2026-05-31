"""Quote-tweet a post by its status ID."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import Page, BrowserContext

from src.utils._helpers import (
    attach_media,
    extract_status_id,
    goto_and_wait,
    safe_click,
    safe_type,
)
from src.utils.exceptions import XActionError
from src.utils.selectors import (
    COMPOSE_POST_BUTTON,
    COMPOSE_TEXTBOX,
    QUOTE_MENU_ITEM,
    REPOST_BUTTON,
    TWEET_ARTICLE,
)
from src.models.post import PostResponse

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger("x_persona")


async def quote(
    context_or_page: BrowserContext | Page,
    status_id: str,
    text: str,
    *,
    handle: str | None = None,
    media_paths: list[Path] | None = None,
    timeout: int = 30_000,
) -> PostResponse:
    """Quote-tweet a post with custom text and optional media.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
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
    PostResponse
        The response containing status ID, URL, and success status. Acts as a string.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Quoting post %s", status_id)

    try:
        article = page.locator(TWEET_ARTICLE).first
        await article.wait_for(state="visible", timeout=15_000)

        # Click the repost button to open the menu
        repost_btn = article.locator(REPOST_BUTTON).first
        await repost_btn.wait_for(state="visible", timeout=5_000)
        await repost_btn.click()

        # Select "Quote" from the dropdown
        await safe_click(page, QUOTE_MENU_ITEM, timeout=5_000)
        
        # Wait for the compose dialog to appear
        await asyncio.sleep(1)

        # Type the quote text
        await safe_type(page, COMPOSE_TEXTBOX, text)
    except Exception as exc:
        err_msg = f"Failed to open compose dialog or type text: {exc}"
        logger.error(err_msg)
        return PostResponse(success=False, error=err_msg)

    # Attach media if provided
    if media_paths:
        try:
            await attach_media(page, media_paths)
        except Exception as exc:
            err_msg = f"Failed to attach media: {exc}"
            logger.error(err_msg)
            return PostResponse(success=False, error=err_msg)

    # Click the Post button
    try:
        await safe_click(page, COMPOSE_POST_BUTTON)
    except Exception as exc:
        err_msg = f"Failed to click compose post button: {exc}"
        logger.error(err_msg)
        return PostResponse(success=False, error=err_msg)

    # Wait for confirmation
    try:
        new_status_id = await _wait_for_quote_confirmation(page, timeout=timeout)
        logger.info("Quote published: %s", new_status_id)
        url = f"https://x.com/i/status/{new_status_id}" if new_status_id != "unknown" else page.url
        return PostResponse(
            success=True,
            url=url,
            status_id=new_status_id,
        )
    except Exception as exc:
        err_msg = f"Quote confirmation timed out: {exc}"
        logger.error(err_msg)
        return PostResponse(success=False, error=err_msg)


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
