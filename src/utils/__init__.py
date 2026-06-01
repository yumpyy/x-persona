"""X (Twitter) automation utilities for persona management."""

# -- Browser session management ---------------------------------------------
from src.utils.browser import BrowserSession

# -- Data models ------------------------------------------------------------
from src.models import (
    PostMetrics,
    QuotedPost,
    FeedPost,
    FeedResponse,
    Reply,
    PostData,
    ActionResult,
    PostResponse,
    ProfileStats,
    MediaAttachment,
)

# -- Exceptions --------------------------------------------------------------
from src.utils.exceptions import (
    XPersonaError,
    XAuthError,
    XNavigationError,
    XElementNotFoundError,
    XActionError,
    XMediaUploadError,
    XRateLimitError,
)

# -- Tool functions ----------------------------------------------------------
from src.utils.edit_profile import edit_profile
from src.utils.feed import get_home_feed
from src.utils.like import like
from src.utils.post import post
from src.utils.post_data import get_post_data
from src.utils.profile import get_profile_stats
from src.utils.quote import quote
from src.utils.reply import reply
from src.utils.repost import repost

__all__ = [
    # Browser
    "BrowserSession",
    # Models
    "PostMetrics",
    "QuotedPost",
    "FeedPost",
    "FeedResponse",
    "Reply",
    "PostData",
    "ActionResult",
    "PostResponse",
    "ProfileStats",
    "MediaAttachment",
    # Exceptions
    "XPersonaError",
    "XAuthError",
    "XNavigationError",
    "XElementNotFoundError",
    "XActionError",
    "XMediaUploadError",
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
