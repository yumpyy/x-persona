"""Reply to a tweet by its status ID.

Navigates to the tweet, clicks the reply button, types the reply text,
optionally attaches media, and publishes.

Usage::

    page = await bm.get_page("cneuralnetwork")
    reply_id = await reply(page, "1234567890", "Great take!")
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
    COMPOSE_TEXTBOX,
    REPLY_BUTTON,
    REPLY_POST_BUTTON,
    TWEET_ARTICLE,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")


async def reply(
    page: Page,
    status_id: str,
    text: str,
    *,
    handle: str | None = None,
    media_paths: list[Path] | None = None,
    timeout: int = 30_000,
) -> str:
    """Reply to a tweet by its status ID.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    status_id:
        The numeric status ID of the tweet to reply to.
    text:
        The reply text.
    handle:
        Optional author handle for building the URL.
    media_paths:
        Optional list of image/video file paths to attach.
    timeout:
        Maximum time (ms) to wait for the reply to be published.

    Returns
    -------
    str
        The status ID of the newly published reply.
    """
    url = _build_status_url(status_id, handle)
    await goto_and_wait(page, url)
    logger.info("Replying to post %s", status_id)

    article = page.locator(TWEET_ARTICLE).first
    await article.wait_for(state="visible", timeout=15_000)

    # Click the reply button on the tweet
    reply_btn = article.locator(REPLY_BUTTON).first
    try:
        await reply_btn.wait_for(state="visible", timeout=5_000)
        await reply_btn.click()
    except Exception as exc:
        raise XActionError(f"Failed to click reply button: {exc}") from exc

    # Wait for the reply compose area to appear
    await asyncio.sleep(1)

    # Type the reply text into the compose box
    # The reply compose box uses the same testid as the main compose
    compose_boxes = page.locator(COMPOSE_TEXTBOX)
    # On the status page, the reply box is the inline one below the tweet
    # It may be the second tweetTextarea if the first is the main tweet's
    compose_count = await compose_boxes.count()
    target_box = compose_boxes.last if compose_count > 0 else compose_boxes.first

    try:
        await target_box.wait_for(state="visible", timeout=5_000)
        await target_box.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(text, delay=0.02)
    except Exception as exc:
        raise XActionError(f"Failed to type reply text: {exc}") from exc

    # Attach media if provided
    if media_paths:
        await attach_media(page, media_paths)

    # Click the Reply/Post button
    # On the reply dialog, the button may say "Reply" and use tweetButton testid
    try:
        await safe_click(page, REPLY_POST_BUTTON, timeout=5_000)
    except Exception:
        # Fallback: try the inline post button
        try:
            from utils.selectors import COMPOSE_INLINE_POST_BUTTON
            await safe_click(page, COMPOSE_INLINE_POST_BUTTON, timeout=5_000)
        except Exception as exc:
            raise XActionError(f"Failed to click reply post button: {exc}") from exc

    # Wait for confirmation
    reply_status_id = await _wait_for_reply_confirmation(page, timeout=timeout)

    logger.info("Reply published: %s", reply_status_id)
    return reply_status_id


async def _wait_for_reply_confirmation(page: Page, *, timeout: int) -> str:
    """Wait for the reply to be published and extract its status ID."""
    try:
        await asyncio.sleep(3)

        # After replying, X often stays on the same status page.
        # The new reply should appear in the thread. Look for the most
        # recent reply by scanning articles.
        articles = page.locator('article[data-testid="tweet"]')
        count = await articles.count()

        # The last article is likely our new reply
        if count > 1:
            last_article = articles.nth(count - 1)
            permalink = last_article.locator("a[href*='/status/']").first
            try:
                href = await permalink.get_attribute("href", timeout=3_000)
                if href:
                    sid = extract_status_id(href)
                    if sid:
                        return sid
            except Exception:
                pass

        logger.warning("Could not extract reply status ID")
        return "unknown"

    except Exception as exc:
        raise XActionError(f"Reply confirmation timed out: {exc}") from exc


def _build_status_url(status_id: str, handle: str | None) -> str:
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"
