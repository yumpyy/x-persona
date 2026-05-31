"""Compose and publish a new post on X."""

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
)
from src.utils.exceptions import XActionError
from src.utils.selectors import (
    COMPOSE_POST_BUTTON,
    COMPOSE_TEXTBOX,
)
from src.models.post import PostResponse
from src.utils.post_data import get_post_data

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["post", "get_post_data"]

logger = logging.getLogger("x_persona")

_COMPOSE_URL = "https://x.com/compose/post"


async def post(
    context_or_page: BrowserContext | Page,
    text: str,
    *,
    media_paths: list[Path] | None = None,
    timeout: int = 30_000,
) -> PostResponse:
    """Compose and publish a new post.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
    text:
        The post text content.
    media_paths:
        Optional list of image/video file paths to attach.
    timeout:
        Maximum time (ms) to wait for the post to be published.

    Returns
    -------
    PostResponse
        The response with success status, URL, and status ID. Acts as a string (returns status_id) when cast to str.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    await goto_and_wait(page, _COMPOSE_URL)
    logger.info("Composing new post…")

    # Focus and type text
    try:
        textbox = page.locator(COMPOSE_TEXTBOX).first
        await textbox.wait_for(state="visible", timeout=15_000)
        await textbox.click()
        await asyncio.sleep(0.5)
        await page.keyboard.type(text, delay=0.02)
    except Exception as exc:
        err_msg = f"Failed to focus or type in compose box: {exc}"
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

    # Click Post button
    try:
        await safe_click(page, COMPOSE_POST_BUTTON)
    except Exception as exc:
        err_msg = f"Failed to click compose post button: {exc}"
        logger.error(err_msg)
        return PostResponse(success=False, error=err_msg)

    # Wait for navigation to the new post or back to home
    try:
        status_id = await _wait_for_post_confirmation(page, timeout=timeout)
        logger.info("Post published: %s", status_id)
        
        # Build post URL
        url = f"https://x.com/i/status/{status_id}" if status_id != "unknown" else page.url
        return PostResponse(
            success=True,
            url=url,
            status_id=status_id,
        )
    except Exception as exc:
        err_msg = f"Post confirmation timed out: {exc}"
        logger.error(err_msg)
        return PostResponse(success=False, error=err_msg)


async def _wait_for_post_confirmation(page: Page, *, timeout: int) -> str:
    """Wait for the post to be published and extract the status ID."""
    try:
        # Wait for navigation away from compose
        await page.wait_for_url(
            lambda url: "/compose/" not in url,
            timeout=timeout,
        )
        await asyncio.sleep(2)

        # Check if we landed on a status page
        current_url = page.url
        status_id = extract_status_id(current_url)
        if status_id:
            return status_id

        # If we're on home, try to find the most recent post by scanning
        # the first tweet in the timeline
        permalink = page.locator('article[data-testid="tweet"] a[href*="/status/"]').first
        try:
            href = await permalink.get_attribute("href", timeout=5_000)
            if href:
                sid = extract_status_id(href)
                if sid:
                    return sid
        except Exception:
            pass

        logger.warning("Could not extract status ID — post likely published")
        return "unknown"

    except Exception as exc:
        raise XActionError(f"Post confirmation timed out: {exc}") from exc
