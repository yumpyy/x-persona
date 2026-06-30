"""X (Twitter) automation utilities for persona management."""

# -- Browser session management ---------------------------------------------
from x_personas.utils.browser import BrowserSession

# -- Data models ------------------------------------------------------------
from x_personas.models import (
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
from x_personas.utils.exceptions import (
    XPersonaError,
    XAuthError,
    XNavigationError,
    XElementNotFoundError,
    XActionError,
    XMediaUploadError,
    XRateLimitError,
)

# -- Tool functions ----------------------------------------------------------
from x_personas.utils.edit_profile import edit_profile
from x_personas.utils.feed import get_home_feed
from x_personas.utils.post import post, reply, quote, like, repost
from x_personas.utils.post_data import get_post_data
from x_personas.utils.profile import get_profile_stats

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
