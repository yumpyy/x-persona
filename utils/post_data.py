"""Hydrate a feed post into a full PostData with threaded replies.

Given a :class:`~utils.models.FeedPost` (from ``get_home_feed``),
navigates to the status page and scrapes the complete post text plus
the full reply tree with nested chains.

Usage::

    feed = await get_home_feed(page)
    full = await get_post_data(page, feed[0])
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
from utils.models import FeedPost, PostData, Reply
from utils.selectors import (
    CONVERSATION_TWEET,
    TWEET_TEXT,
    TWEET_TIMESTAMP,
    TWEET_USER_NAME,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

logger = logging.getLogger("x_persona")


async def get_post_data(
    page: Page,
    feed_post: FeedPost,
    *,
    max_reply_scrolls: int = 15,
) -> PostData:
    """Navigate to a post's status page and scrape the full conversation.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    feed_post:
        A lightweight ``FeedPost`` returned by ``get_home_feed``.
    max_reply_scrolls:
        How many times to scroll down to load more replies.

    Returns
    -------
    PostData
        The complete post with full text and a nested reply tree.
    """
    status_url = f"https://x.com/{feed_post.author_handle}/status/{feed_post.post_id}"
    await goto_and_wait(page, status_url)
    logger.info("Scraping post data: %s", status_url)

    # --- Main post (first article on the page) ---
    main_article = page.locator(CONVERSATION_TWEET).first
    await main_article.wait_for(state="visible", timeout=15_000)

    full_text = await _extract_post_text(main_article)
    timestamp = await _extract_timestamp(main_article)
    stats = await _extract_detail_stats(page)

    # --- Replies ---
    replies = await _collect_replies(
        page,
        main_post_id=feed_post.post_id,
        main_author=feed_post.author_handle,
        max_scrolls=max_reply_scrolls,
    )

    return PostData(
        post_id=feed_post.post_id,
        author_handle=feed_post.author_handle,
        author_name=feed_post.author_name,
        full_text=full_text,
        timestamp=timestamp,
        likes=stats.get("likes", feed_post.likes),
        reposts=stats.get("reposts", feed_post.reposts),
        replies_count=stats.get("replies", feed_post.replies_count),
        quotes=stats.get("quotes", 0),
        views=stats.get("views", ""),
        replies=replies,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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


async def _extract_detail_stats(page: Page) -> dict[str, int | str]:
    """Parse the detailed stat bar on the individual status page.

    On the status page, X shows exact counts (not abbreviated) in an
    aria-label or as direct text in stat links.
    """
    stats: dict[str, int | str] = {}

    # Try to extract from the stat links below the main tweet
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
    main_author: str,
    max_scrolls: int,
) -> list[Reply]:
    """Scroll through the reply section and build a nested reply tree.

    Replies by the same author that form a thread are chained together
    in a nested ``replies`` list on the parent ``Reply`` object.
    """
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
        reposts = 0
        group = article.locator('[role="group"]')
        if await group.count() > 0:
            grp = group.first
            for testid, key in [("like", "likes"), ("retweet", "reposts")]:
                btn = grp.locator(f'[data-testid="{testid}"]')
                if await btn.count() > 0:
                    label = await btn.first.get_attribute("aria-label") or ""
                    parts = label.split()
                    if parts and parts[0].replace(",", "").isdigit():
                        val = parse_count(parts[0])
                        if key == "likes":
                            likes = val
                        else:
                            reposts = val

        return {
            "reply_id": reply_id,
            "author_handle": handle,
            "author_name": author_name,
            "text": text,
            "timestamp": timestamp,
            "likes": likes,
            "reposts": reposts,
        }
    except Exception:
        logger.debug("Failed to parse reply article", exc_info=True)
        return None


def _build_reply_tree(raw_replies: list[dict]) -> list[Reply]:
    """Organize flat replies into a nested tree.

    Thread continuations (consecutive replies by the same author) are
    chained as nested children.  All other replies are top-level.
    """
    if not raw_replies:
        return []

    top_level: list[Reply] = []
    prev_reply: Reply | None = None

    for data in raw_replies:
        reply = Reply(
            reply_id=data["reply_id"],
            author_handle=data["author_handle"],
            author_name=data["author_name"],
            text=data["text"],
            timestamp=data["timestamp"],
            likes=data["likes"],
            reposts=data["reposts"],
        )

        # Chain consecutive same-author replies
        if prev_reply and reply.author_handle == prev_reply.author_handle:
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
