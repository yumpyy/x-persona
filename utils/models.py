"""Pydantic data models for X (Twitter) automation utilities.

All structured return types live here so every tool module shares
the same vocabulary. Models are kept flat where possible and use
recursive self-references only for threaded replies.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Feed & Post models
# ---------------------------------------------------------------------------


class FeedPost(BaseModel):
    """Lightweight representation of a post scraped from the home feed.

    Intentionally minimal — use `get_post_data` to hydrate into a full
    `PostData` with threaded replies.
    """

    post_id: str = Field(description="Numeric status ID extracted from the permalink.")
    author_handle: str = Field(description="Handle without the leading '@'.")
    author_name: str = Field(description="Display name shown above the post.")
    text: str = Field(description="Visible text content of the post.")
    timestamp: str = Field(description="ISO-style timestamp or relative time string.")
    likes: int = Field(default=0)
    reposts: int = Field(default=0)
    replies_count: int = Field(default=0)
    views: str = Field(default="")
    is_repost: bool = Field(
        default=False,
        description="True when this item is someone else's repost appearing in the feed.",
    )
    reposted_by: str | None = Field(
        default=None,
        description="Handle of the user who reposted, if `is_repost` is True.",
    )


class Reply(BaseModel):
    """A single reply in a conversation thread.

    Replies whose author matches the parent form a *chain* (thread
    continuation) and are nested inside the parent's `replies` list.
    """

    reply_id: str = Field(description="Status ID of this reply.")
    author_handle: str
    author_name: str
    text: str
    timestamp: str
    likes: int = Field(default=0)
    reposts: int = Field(default=0)
    replies: list[Reply] = Field(
        default_factory=list,
        description="Sub-replies forming a nested conversation chain.",
    )


class PostData(BaseModel):
    """Fully hydrated post with threaded reply tree.

    Returned by `get_post_data` after navigating to the individual
    status page and scraping the full conversation.
    """

    post_id: str
    author_handle: str
    author_name: str
    full_text: str = Field(description="Complete text including show-more expansion.")
    timestamp: str
    likes: int = Field(default=0)
    reposts: int = Field(default=0)
    replies_count: int = Field(default=0)
    quotes: int = Field(default=0)
    views: str = Field(default="")
    replies: list[Reply] = Field(
        default_factory=list,
        description="Top-level replies; each may contain nested sub-replies.",
    )


# ---------------------------------------------------------------------------
# Profile models
# ---------------------------------------------------------------------------


class ProfileStats(BaseModel):
    """Public profile information scraped from `x.com/{handle}`."""

    handle: str
    display_name: str
    bio: str = Field(default="")
    location: str | None = Field(default=None)
    website: str | None = Field(default=None)
    followers: int = Field(default=0)
    following: int = Field(default=0)
    posts_count: int = Field(default=0)
    joined: str = Field(default="")
    verified: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Media helper
# ---------------------------------------------------------------------------


class MediaAttachment(BaseModel):
    """Descriptor for a media file to attach to a post, reply, or quote."""

    file_path: Path = Field(description="Absolute or project-relative path to the media file.")

    def resolve(self) -> Path:
        """Return the resolved absolute path, raising if the file is missing."""
        resolved = self.file_path.resolve()
        if not resolved.is_file():
            msg = f"Media file not found: {resolved}"
            raise FileNotFoundError(msg)
        return resolved
