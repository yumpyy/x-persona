"""Scrape the home feed for a logged-in X account.

Provides ``get_home_feed`` which scrolls the ``/home`` timeline and
returns a deduplicated list of :class:`~utils.models.FeedPost` objects.

Usage::

    page = await bm.get_page("cneuralnetwork")
    posts = await get_home_feed(page, count=30)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from utils._helpers import (
    extract_status_id,
    extract_text,
    goto_and_wait,
    parse_count,
    scroll_page,
)
from utils.models import FeedPost
from utils.selectors import (
    SOCIAL_CONTEXT,
    TWEET_ARTICLE,
    TWEET_PERMALINK,
    TWEET_TEXT,
    TWEET_TIMESTAMP,
    TWEET_USER_NAME,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

logger = logging.getLogger("x_persona")

_HOME_URL = "https://x.com/home"


async def get_home_feed(
    page: Page,
    *,
    count: int = 20,
    max_scrolls: int = 30,
    tab: str | None = None,
) -> list[FeedPost]:
    """Scrape the home timeline and return up to *count* posts.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    count:
        Target number of posts to collect.
    max_scrolls:
        Safety cap on how many times we scroll before giving up.
    tab:
        Optional tab to select (e.g., "following" or "for_you"). If not specified,
        uses whichever tab is currently loaded.

    Returns
    -------
    list[FeedPost]
        Deduplicated posts in feed order.
    """
    await goto_and_wait(page, _HOME_URL)

    if tab:
        tab_name = "Following" if tab.lower() == "following" else "For you"
        logger.info("Switching to '%s' tab", tab_name)
        try:
            tab_locator = page.locator("role=tab").filter(has_text=tab_name)
            await tab_locator.first.wait_for(state="visible", timeout=10_000)
            is_selected = await tab_locator.first.get_attribute("aria-selected")
            if is_selected != "true":
                await tab_locator.first.click()
                await page.wait_for_timeout(2000)
        except Exception as exc:
            logger.warning("Could not switch to '%s' tab: %s. Continuing with current tab.", tab_name, exc)

    logger.info("Scraping home feed (target: %d posts)", count)

    collected: dict[str, FeedPost] = {}  # post_id → FeedPost (dedup)

    for scroll_num in range(max_scrolls):
        articles = page.locator(TWEET_ARTICLE)
        article_count = await articles.count()

        for i in range(article_count):
            article = articles.nth(i)
            post = await _parse_feed_article(article)
            if post and post.post_id not in collected:
                collected[post.post_id] = post

        if len(collected) >= count:
            break

        await scroll_page(page)
        logger.debug("Scroll %d — collected %d/%d", scroll_num + 1, len(collected), count)

    result = list(collected.values())[:count]
    logger.info("Collected %d posts from home feed", len(result))
    return result


async def _parse_feed_article(article: Locator) -> FeedPost | None:
    """Extract a ``FeedPost`` from a single tweet ``<article>`` element.

    Returns ``None`` if we can't extract a valid post ID (e.g. promoted
    tweets or broken DOM).
    """
    try:
        # --- Post ID from permalink ---
        permalink = article.locator("a[href*='/status/']").first
        href = await permalink.get_attribute("href", timeout=3_000)
        if not href:
            return None
        post_id = extract_status_id(href)
        if not post_id:
            return None

        # --- Author ---
        author_handle = _handle_from_href(href)
        name_el = article.locator(TWEET_USER_NAME).first
        author_name = await _extract_display_name(name_el)

        # --- Text ---
        text_el = article.locator(TWEET_TEXT).first
        text = await extract_text(text_el)

        # --- Timestamp ---
        time_el = article.locator(TWEET_TIMESTAMP).first
        timestamp = await time_el.get_attribute("datetime") or ""

        # --- Engagement stats ---
        stats = await _parse_article_stats(article)

        # --- Repost detection ---
        is_repost = False
        reposted_by: str | None = None
        social_ctx = article.locator(SOCIAL_CONTEXT)
        if await social_ctx.count() > 0:
            ctx_text = await extract_text(social_ctx.first)
            if "reposted" in ctx_text.lower():
                is_repost = True
                reposted_by = ctx_text.split(" reposted")[0].strip()

        return FeedPost(
            post_id=post_id,
            author_handle=author_handle,
            author_name=author_name,
            text=text,
            timestamp=timestamp,
            likes=stats.get("likes", 0),
            reposts=stats.get("reposts", 0),
            replies_count=stats.get("replies", 0),
            views=stats.get("views", ""),
            is_repost=is_repost,
            reposted_by=reposted_by,
        )
    except Exception:
        logger.debug("Failed to parse feed article", exc_info=True)
        return None


async def _parse_article_stats(article: Locator) -> dict[str, int | str]:
    """Extract engagement counts from the action bar of a tweet article."""
    stats: dict[str, int | str] = {}
    group = article.locator('[role="group"]').first

    for testid, key in [
        ("reply", "replies"),
        ("retweet", "reposts"),
        ("like", "likes"),
    ]:
        btn = group.locator(f'[data-testid="{testid}"]')
        if await btn.count() > 0:
            label = await btn.first.get_attribute("aria-label") or ""
            # aria-label is like "42 Likes" or "Reply"
            parts = label.split()
            if parts and parts[0].replace(",", "").isdigit():
                stats[key] = parse_count(parts[0])
            else:
                stats[key] = 0
        else:
            stats[key] = 0

    return stats


def _handle_from_href(href: str) -> str:
    """Extract the handle from a ``/{handle}/status/{id}`` URL."""
    # href looks like "/cneuralnetwork/status/123456"
    parts = href.strip("/").split("/")
    return parts[0] if parts else ""


async def _extract_display_name(name_locator: Locator) -> str:
    """Pull the display name from X's User-Name container.

    The container has multiple spans — the first visible text span
    is typically the display name.
    """
    try:
        spans = name_locator.locator("span")
        first_span = spans.first
        return await extract_text(first_span)
    except Exception:
        return ""
