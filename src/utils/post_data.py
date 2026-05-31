"""Hydrate a post into a full PostData with threaded replies."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from playwright.async_api import Page, BrowserContext

from src.utils._helpers import (
    extract_status_id,
    extract_text,
    goto_and_wait,
    parse_count,
    scroll_page,
)
from src.models.feed import PostMetrics, FeedPost
from src.models.post import PostData, Reply
from src.utils.selectors import (
    CONVERSATION_TWEET,
    TWEET_TEXT,
    TWEET_TIMESTAMP,
    TWEET_USER_NAME,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator

logger = logging.getLogger("x_persona")


async def get_post_data(
    context_or_page: BrowserContext | Page,
    feed_post_or_id: FeedPost | str,
    *,
    max_reply_scrolls: int = 15,
) -> PostData:
    """Navigate to a post's status page and scrape the full conversation.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
    feed_post_or_id:
        A lightweight ``FeedPost`` or a numeric status ID string.
    max_reply_scrolls:
        How many times to scroll down to load more replies.

    Returns
    -------
    PostData
        The complete post with full text, metrics, media, and a nested reply tree.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    if isinstance(feed_post_or_id, str):
        status_id = feed_post_or_id
        handle = None
        author_name = "Unknown"
        initial_likes = 0
        initial_reposts = 0
        initial_replies = 0
    else:
        status_id = feed_post_or_id.status_id
        handle = feed_post_or_id.handle
        author_name = feed_post_or_id.author_name
        initial_likes = feed_post_or_id.metrics.likes
        initial_reposts = feed_post_or_id.metrics.retweets
        initial_replies = feed_post_or_id.metrics.replies

    status_url = _build_status_url(status_id, handle)
    await goto_and_wait(page, status_url)
    logger.info("Scraping post data: %s", status_url)

    # --- Main post (first article on the page) ---
    main_article = page.locator(CONVERSATION_TWEET).first
    await main_article.wait_for(state="visible", timeout=15_000)

    full_text = await _extract_post_text(main_article)
    timestamp = await _extract_timestamp(main_article)
    stats = await _extract_detail_stats(page)

    # Hydrate missing author info if we navigated directly by status ID
    if author_name == "Unknown":
        name_el = main_article.locator(TWEET_USER_NAME).first
        if await name_el.count() > 0:
            spans = name_el.locator("span")
            author_name = await extract_text(spans.first)
            
            # Find handle
            handle_el = name_el.locator('a[tabindex="-1"] span').first
            if await handle_el.count() > 0:
                handle = (await extract_text(handle_el)).replace("@", "").strip()
            else:
                handle = "unknown"

    # --- Media URLs ---
    media_urls: list[str] = []
    img_els = main_article.locator('img[src*="pbs.twimg.com/media"]')
    img_count = await img_els.count()
    for idx in range(img_count):
        src = await img_els.nth(idx).get_attribute("src")
        if src:
            media_urls.append(src)

    # --- Replies ---
    replies = await _collect_replies(
        page,
        main_post_id=status_id,
        max_scrolls=max_reply_scrolls,
    )

    metrics = PostMetrics(
        likes=stats.get("likes", initial_likes),
        retweets=stats.get("reposts", initial_reposts),
        replies=stats.get("replies", initial_replies),
        views=stats.get("views"),
        bookmarks=stats.get("bookmarks", 0),
    )

    return PostData(
        status_id=status_id,
        author_name=author_name,
        handle=handle or "unknown",
        text=full_text,
        timestamp=timestamp,
        metrics=metrics,
        replies=replies,
        media_urls=media_urls,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_status_url(status_id: str, handle: str | None) -> str:
    if handle:
        return f"https://x.com/{handle.lstrip('@')}/status/{status_id}"
    return f"https://x.com/i/status/{status_id}"


async def _extract_post_text(article: Locator) -> str:
    """Extract the full text from a post article, including show-more."""
    text_el = article.locator(TWEET_TEXT).first
    return await extract_text(text_el)


async def _extract_timestamp(article: Locator) -> str:
    """Extract the datetime attribute from the <time> element."""
    time_el = article.locator(TWEET_TIMESTAMP).first
    try:
        return await time_el.get_attribute("datetime") or ""
    except Exception:
        return ""


async def _extract_detail_stats(page: Page) -> dict[str, int]:
    """Parse the detailed stat bar on the individual status page."""
    stats: dict[str, int] = {}

    stat_links = page.locator('a[href*="/likes"], a[href*="/retweets"], a[href*="/quotes"]')
    link_count = await stat_links.count()

    for i in range(link_count):
        link = stat_links.nth(i)
        href = await link.get_attribute("href") or ""
        text = await extract_text(link)

        if "/likes" in href:
            stats["likes"] = parse_count(text.split()[0]) if text else 0
        elif "/retweets" in href:
            stats["reposts"] = parse_count(text.split()[0]) if text else 0
        elif "/quotes" in href:
            stats["quotes"] = parse_count(text.split()[0]) if text else 0

    return stats


async def _collect_replies(
    page: Page,
    *,
    main_post_id: str,
    max_scrolls: int,
) -> list[Reply]:
    """Scroll through the reply section and build a nested reply tree."""
    seen_ids: set[str] = set()
    raw_replies: list[dict] = []

    for _ in range(max_scrolls):
        articles = page.locator(CONVERSATION_TWEET)
        count = await articles.count()

        for i in range(count):
            article = articles.nth(i)
            reply_data = await _parse_reply_article(article)
            if not reply_data:
                continue
            rid = reply_data["reply_id"]
            # Skip the main post itself
            if rid == main_post_id or rid in seen_ids:
                continue
            seen_ids.add(rid)
            raw_replies.append(reply_data)

        # Check if we've loaded enough or hit the bottom
        await scroll_page(page, pause=2.0)

        # Re-check — if no new articles appeared, stop
        new_count = await page.locator(CONVERSATION_TWEET).count()
        if new_count <= count:
            break

    return _build_reply_tree(raw_replies)


async def _parse_reply_article(article: Locator) -> dict | None:
    """Extract reply metadata from a tweet article element."""
    try:
        permalink = article.locator("a[href*='/status/']").first
        href = await permalink.get_attribute("href", timeout=3_000)
        if not href:
            return None

        reply_id = extract_status_id(href)
        if not reply_id:
            return None

        handle = href.strip("/").split("/")[0]

        name_el = article.locator(TWEET_USER_NAME).first
        spans = name_el.locator("span")
        author_name = await extract_text(spans.first)

        text_el = article.locator(TWEET_TEXT).first
        text = await extract_text(text_el)

        time_el = article.locator(TWEET_TIMESTAMP).first
        timestamp = await time_el.get_attribute("datetime") or ""

        # Parse like/repost counts from aria-labels
        likes = 0
        group = article.locator('[role="group"]')
        if await group.count() > 0:
            grp = group.first
            btn = grp.locator('[data-testid="like"]')
            if await btn.count() > 0:
                label = await btn.first.get_attribute("aria-label") or ""
                parts = label.split()
                if parts and parts[0].replace(",", "").isdigit():
                    likes = parse_count(parts[0])

        return {
            "reply_id": reply_id,
            "author_handle": handle,
            "author_name": author_name,
            "text": text,
            "timestamp": timestamp,
            "likes": likes,
        }
    except Exception:
        logger.debug("Failed to parse reply article", exc_info=True)
        return None


def _build_reply_tree(raw_replies: list[dict]) -> list[Reply]:
    """Organize flat replies into a nested tree."""
    if not raw_replies:
        return []

    top_level: list[Reply] = []
    prev_reply: Reply | None = None

    for data in raw_replies:
        reply = Reply(
            status_id=data["reply_id"],
            handle=data["author_handle"],
            author_name=data["author_name"],
            text=data["text"],
            timestamp=data["timestamp"],
            likes=data["likes"],
            replies=[],
        )

        # Chain consecutive same-author replies
        if prev_reply and reply.handle == prev_reply.handle:
            _append_to_chain(prev_reply, reply)
        else:
            top_level.append(reply)
            prev_reply = reply

    return top_level


def _append_to_chain(parent: Reply, child: Reply) -> None:
    """Append *child* to the deepest node of *parent*'s reply chain."""
    current = parent
    while current.replies:
        current = current.replies[-1]
    current.replies.append(child)
