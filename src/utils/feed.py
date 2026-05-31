"""Scrape the home feed for X (Twitter) accounts.

Provides ``get_home_feed`` which scrolls the ``/home`` timeline and
returns a deduplicated list of posts inside a ``FeedResponse`` object.
"""

from __future__ import annotations

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
from src.models.feed import FeedPost, FeedResponse, PostMetrics, QuotedPost
from src.utils.selectors import (
    SOCIAL_CONTEXT,
    TWEET_ARTICLE,
    TWEET_TEXT,
    TWEET_TIMESTAMP,
    TWEET_USER_NAME,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator

logger = logging.getLogger("x_persona")

_HOME_URL = "https://x.com/home"


async def get_home_feed(
    context_or_page: BrowserContext | Page,
    *,
    count: int = 20,
    max_scrolls: int = 30,
    tab: str | None = None,
    scroll_count: int | None = None,  # for compatibility with scroll_count argument
) -> FeedResponse:
    """Scrape the home timeline and return up to *count* posts inside a FeedResponse.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright page or BrowserContext.
    count:
        Target number of posts to collect.
    max_scrolls:
        Safety cap on how many times we scroll before giving up.
    tab:
        Optional tab to select (e.g., "following" or "for_you").
    scroll_count:
        Alias for max_scrolls. Used for compat with feat/playwright-scraper.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    if scroll_count is not None:
        max_scrolls = scroll_count

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

    # Wait for articles to load
    try:
        await page.wait_for_selector(TWEET_ARTICLE, state="visible", timeout=15_000)
    except Exception:
        logger.warning("Timeline articles did not load within timeout.")

    collected: dict[str, FeedPost] = {}  # status_id → FeedPost (dedup)

    for scroll_num in range(max_scrolls):
        articles = page.locator(TWEET_ARTICLE)
        article_count = await articles.count()

        for i in range(article_count):
            article = articles.nth(i)
            post = await _parse_feed_article(article)
            if post and post.status_id not in collected:
                collected[post.status_id] = post

        if len(collected) >= count:
            break

        await scroll_page(page)
        logger.debug("Scroll %d — collected %d/%d", scroll_num + 1, len(collected), count)

    result = list(collected.values())[:count]
    logger.info("Collected %d posts from home feed", len(result))
    return FeedResponse(posts=result)


async def _parse_feed_article(article: Locator) -> FeedPost | None:
    """Extract a ``FeedPost`` from a single tweet ``<article>`` element."""
    try:
        # --- Post ID from permalink ---
        permalink = article.locator("a[href*='/status/']").first
        href = await permalink.get_attribute("href", timeout=3_000)
        if not href:
            return None
        status_id = extract_status_id(href)
        if not status_id:
            return None

        # --- Author ---
        handle = _handle_from_href(href)
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
        metrics = PostMetrics(
            likes=stats.get("likes", 0),
            retweets=stats.get("reposts", 0),
            replies=stats.get("replies", 0),
            views=stats.get("views"),
            bookmarks=stats.get("bookmarks", 0),
        )

        # --- Social context (repost, reply, pinned, sponsored) ---
        is_retweet = False
        is_reply = False
        is_pinned = False
        is_sponsored = False
        
        social_ctx = article.locator(SOCIAL_CONTEXT)
        if await social_ctx.count() > 0:
            ctx_text = await extract_text(social_ctx.first)
            ctx_text_lower = ctx_text.lower()
            if "reposted" in ctx_text_lower:
                is_retweet = True
            elif "reply" in ctx_text_lower:
                is_reply = True
            elif "pinned" in ctx_text_lower:
                is_pinned = True
            elif "promoted" in ctx_text_lower or "ad" in ctx_text_lower or "sponsored" in ctx_text_lower:
                is_sponsored = True

        # --- Quote detection ---
        is_quote = False
        quoted_post = None
        qt_el = article.locator('[data-testid="quoteTweet"]').first
        if await qt_el.count() > 0:
            is_quote = True
            qt_text_el = qt_el.locator('[data-testid="tweetText"]').first
            qt_text = await extract_text(qt_text_el)
            qt_name_el = qt_el.locator('[data-testid="User-Name"]').first
            qt_name = await _extract_display_name(qt_name_el)
            
            qt_handle_el = qt_el.locator('[data-testid="User-Name"] a[tabindex="-1"] span').first
            qt_handle = ""
            if await qt_handle_el.count() > 0:
                qt_handle = (await extract_text(qt_handle_el)).replace("@", "").strip()

            quoted_post = QuotedPost(
                status_id="",  # Quoted status ID is empty unless we navigate
                author_name=qt_name,
                handle=qt_handle or "unknown",
                text=qt_text,
            )

        # --- Media URLs ---
        media_urls: list[str] = []
        img_locs = article.locator('img[src*="pbs.twimg.com/media"]')
        img_count = await img_locs.count()
        for idx in range(img_count):
            img_src = await img_locs.nth(idx).get_attribute("src")
            if img_src:
                media_urls.append(img_src)
        if not media_urls:
            photo_locs = article.locator('[data-testid="tweetPhoto"] img')
            photo_count = await photo_locs.count()
            for idx in range(photo_count):
                img_src = await photo_locs.nth(idx).get_attribute("src")
                if img_src:
                    media_urls.append(img_src)

        # --- Avatar ---
        avatar_url = None
        avatar_loc = article.locator('img[src*="pbs.twimg.com/profile_images"]').first
        if await avatar_loc.count() > 0:
            avatar_url = await avatar_loc.get_attribute("src")

        return FeedPost(
            status_id=status_id,
            author_name=author_name,
            handle=handle,
            text=text,
            timestamp=timestamp,
            is_retweet=is_retweet,
            is_quote=is_quote,
            is_reply=is_reply,
            is_pinned=is_pinned,
            is_sponsored=is_sponsored,
            metrics=metrics,
            quoted_post=quoted_post,
            media_urls=media_urls,
            author_avatar_url=avatar_url,
        )
    except Exception:
        logger.debug("Failed to parse feed article", exc_info=True)
        return None


async def _parse_article_stats(article: Locator) -> dict[str, int]:
    """Extract engagement counts from the action bar of a tweet article."""
    stats: dict[str, int] = {}
    group = article.locator('[role="group"]').first

    for testid, key in [
        ("reply", "replies"),
        ("retweet", "reposts"),
        ("like", "likes"),
        ("bookmark", "bookmarks"),
    ]:
        btn = group.locator(f'[data-testid="{testid}"]')
        if await btn.count() > 0:
            label = await btn.first.get_attribute("aria-label") or ""
            parts = label.split()
            if parts and parts[0].replace(",", "").isdigit():
                stats[key] = parse_count(parts[0])
            else:
                stats[key] = 0
        else:
            stats[key] = 0

    # Views metric extraction
    views_link = article.locator('a[href*="/analytics"]').first
    if await views_link.count() > 0:
        label = await views_link.get_attribute("aria-label") or ""
        parts = label.split()
        if parts and parts[0].replace(",", "").isdigit():
            stats["views"] = parse_count(parts[0])
        else:
            stats["views"] = 0
    else:
        stats["views"] = 0

    return stats


def _handle_from_href(href: str) -> str:
    """Extract the handle from a ``/{handle}/status/{id}`` URL."""
    parts = href.strip("/").split("/")
    return parts[0] if parts else ""


async def _extract_display_name(name_locator: Locator) -> str:
    """Pull the display name from X's User-Name container."""
    try:
        spans = name_locator.locator("span")
        first_span = spans.first
        return await extract_text(first_span)
    except Exception:
        return ""
