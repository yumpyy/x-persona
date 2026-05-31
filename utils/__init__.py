"""X (Twitter) automation utilities for persona management.

This package provides a clean, modular set of Playwright-based tools
for interacting with X programmatically.  Each tool is a standalone
module that can be imported individually or used via the top-level
re-exports below.

Quick start::

    from utils import BrowserManager, get_home_feed, like, post

    async with BrowserManager() as bm:
        page = await bm.get_page("cneuralnetwork")

        # Scrape the home feed
        feed = await get_home_feed(page)

        # Like the first post
        await like(page, feed[0].post_id, handle=feed[0].author_handle)

        # Compose a new post with media
        from pathlib import Path
        await post(page, "Hello world!", media_paths=[Path("image.png")])

        await page.close()
"""

# -- Browser session management ---------------------------------------------
from utils.browser import BrowserManager

# -- Data models -------------------------------------------------------------
from utils.models import FeedPost, MediaAttachment, PostData, ProfileStats, Reply

# -- Exceptions --------------------------------------------------------------
from utils.exceptions import (
    XActionError,
    XAuthError,
    XElementNotFoundError,
    XMediaUploadError,
    XNavigationError,
    XPersonaError,
    XRateLimitError,
)

# -- Tool functions ----------------------------------------------------------
from utils.edit_profile import edit_profile
from utils.feed import get_home_feed
from utils.like import like
from utils.post import post
from utils.post_data import get_post_data
from utils.profile import get_profile_stats
from utils.quote import quote
from utils.reply import reply
from utils.repost import repost

__all__ = [
    # Browser
    "BrowserManager",
    # Models
    "FeedPost",
    "MediaAttachment",
    "PostData",
    "ProfileStats",
    "Reply",
    # Exceptions
    "XActionError",
    "XAuthError",
    "XElementNotFoundError",
    "XMediaUploadError",
    "XNavigationError",
    "XPersonaError",
    "XRateLimitError",
    # Tools
    "edit_profile",
    "get_home_feed",
    "get_post_data",
    "like",
    "post",
    "get_profile_stats",
    "quote",
    "reply",
    "repost",
]
