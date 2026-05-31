"""Compose and publish a new post on X.

Navigates to ``x.com/compose/post``, types the text, optionally
attaches media, and clicks Post.

Usage::

    page = await bm.get_page("cneuralnetwork")
    status_id = await post(page, "Hello world!")
    status_id = await post(page, "Check this out", media_paths=[Path("screenshot.png")])
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
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")

_COMPOSE_URL = "https://x.com/compose/post"


async def post(
    page: Page,
    text: str,
    *,
    media_paths: list[Path] | None = None,
    timeout: int = 30_000,
) -> str:
    """Compose and publish a new post.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    text:
        The post text content.
    media_paths:
        Optional list of image/video file paths to attach.
    timeout:
        Maximum time (ms) to wait for the post to be published.

    Returns
    -------
    str
        The status ID of the newly published post.

    Raises
    ------
    XActionError
        If the post fails to publish within the timeout.
    """
    await goto_and_wait(page, _COMPOSE_URL)
    logger.info("Composing new post (%d chars)", len(text))

    # Type the post text
    await safe_type(page, COMPOSE_TEXTBOX, text)

    # Attach media if provided
    if media_paths:
        await attach_media(page, media_paths)

    # Click Post
    await safe_click(page, COMPOSE_POST_BUTTON)

    # Wait for navigation to the new post or back to home
    status_id = await _wait_for_post_confirmation(page, timeout=timeout)

    logger.info("Post published: %s", status_id)
    return status_id


async def _wait_for_post_confirmation(page: Page, *, timeout: int) -> str:
    """Wait for the post to be published and extract the status ID.

    After posting, X either:
    - Redirects to the new post's status page, or
    - Shows a toast and stays on home / compose

    We handle both by watching for URL changes and toast notifications.
    """
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

        # Fallback: return a placeholder (the post was likely published)
        logger.warning("Could not extract status ID — post likely published")
        return "unknown"

    except Exception as exc:
        raise XActionError(f"Post confirmation timed out: {exc}") from exc
