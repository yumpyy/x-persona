"""Scrape profile statistics from ``x.com/{handle}``."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from playwright.async_api import Page, BrowserContext

from src.utils._helpers import extract_text, goto_and_wait, parse_count
from src.utils.exceptions import XNavigationError
from src.models.profile import ProfileStats
from src.utils.selectors import (
    PROFILE_BIO,
    PROFILE_FOLLOWERS_LINK,
    PROFILE_FOLLOWING_LINK,
    PROFILE_HEADER,
    PROFILE_JOINED,
    PROFILE_LOCATION,
    PROFILE_STAT_VALUE,
    PROFILE_URL,
    PROFILE_VERIFIED,
    PRIMARY_COLUMN,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("x_persona")


async def get_profile_stats(
    context_or_page: BrowserContext | Page,
    username: str,
) -> ProfileStats:
    """Scrape public profile information for *username*.

    Parameters
    ----------
    context_or_page:
        An authenticated Playwright Page or BrowserContext.
    username:
        The handle (without ``@``) to look up.

    Returns
    -------
    ProfileStats
        Structured profile data.

    Raises
    ------
    XNavigationError
        If the profile page fails to load.
    """
    if isinstance(context_or_page, Page):
        page = context_or_page
    else:
        page = context_or_page.pages[0] if context_or_page.pages else await context_or_page.new_page()

    username = username.lstrip("@").lower()
    profile_url = f"https://x.com/{username}"
    await goto_and_wait(page, profile_url)
    logger.info("Scraping profile: @%s", username)

    # Wait for the primary column to render
    try:
        await page.locator(PRIMARY_COLUMN).first.wait_for(
            state="visible", timeout=15_000
        )
    except Exception as exc:
        raise XNavigationError(
            f"Profile page for @{username} did not load"
        ) from exc

    # --- Display name ---
    display_name = await _extract_display_name(page)

    # --- Bio ---
    bio = await _safe_text(page, PROFILE_BIO)

    # --- Location ---
    location = await _safe_text(page, PROFILE_LOCATION) or None

    # --- Website ---
    website = await _safe_text(page, PROFILE_URL) or None

    # --- Joined date ---
    joined = await _safe_text(page, PROFILE_JOINED)
    # Strip "Joined " prefix if present
    if joined.lower().startswith("joined"):
        joined = joined[6:].strip()

    # --- Verified ---
    verified = await page.locator(PROFILE_VERIFIED).count() > 0

    # --- Follower / following counts ---
    followers = await _extract_stat(page, PROFILE_FOLLOWERS_LINK)
    following = await _extract_stat(page, PROFILE_FOLLOWING_LINK)

    # --- Posts count (from the header tab) ---
    posts_count = await _extract_posts_count(page, username)

    stats = ProfileStats(
        handle=username,
        display_name=display_name,
        bio=bio,
        location=location,
        website=website,
        followers=followers,
        following=following,
        posts_count=posts_count,
        joined=joined,
        verified=verified,
    )

    logger.info(
        "Profile @%s: %d followers, %d following, %d posts",
        username,
        followers,
        following,
        posts_count,
    )
    return stats


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _extract_display_name(page: Page) -> str:
    """Pull the display name from the profile header."""
    header = page.locator(PROFILE_HEADER).first
    try:
        await header.wait_for(state="visible", timeout=5_000)
        # The first span inside UserName is typically the display name
        span = header.locator("span span").first
        return await extract_text(span)
    except Exception:
        return ""


async def _safe_text(page: Page, selector: str) -> str:
    """Extract text from a selector, returning "" on failure."""
    loc = page.locator(selector).first
    try:
        await loc.wait_for(state="attached", timeout=3_000)
        return await extract_text(loc)
    except Exception:
        return ""


async def _extract_stat(page: Page, link_selector: str) -> int:
    """Extract a numeric stat from a profile link (followers/following)."""
    link = page.locator(link_selector).first
    try:
        await link.wait_for(state="attached", timeout=5_000)
        stat_span = link.locator(PROFILE_STAT_VALUE).first
        raw = await extract_text(stat_span)
        return parse_count(raw)
    except Exception:
        return 0


async def _extract_posts_count(page: Page, username: str) -> int:
    """Extract the posts count from the profile navigation tab."""
    heading = page.locator(f'[data-testid="UserProfileHeader_Items"]')
    try:
        if await heading.count() > 0:
            text = await extract_text(heading.first)
            match = re.search(r"([\d,.]+[KMB]?)\s*posts?", text, re.IGNORECASE)
            if match:
                return parse_count(match.group(1))
    except Exception:
        pass

    # Fallback: try the tab bar
    tab = page.locator(f'a[href="/{username}"] span')
    try:
        count = await tab.count()
        for i in range(count):
            raw = await extract_text(tab.nth(i))
            if raw and raw[0].isdigit():
                return parse_count(raw)
    except Exception:
        pass

    return 0
