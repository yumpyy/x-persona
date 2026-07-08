"""Platform adapter abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from xpersonas.core.models import AuthConfig, PlatformActionResult, PlatformPost

if TYPE_CHECKING:
    pass


class PlatformAdapter(ABC):
    """Abstract base for all platform integrations.

    Each platform (X/Twitter, Reddit, LinkedIn, etc.) implements
    this interface to provide platform-specific behavior.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier: 'x', 'reddit', 'linkedin'."""
        ...

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """Actions this platform supports."""
        ...

    @abstractmethod
    async def initialize(self, auth: AuthConfig, visible: bool = False) -> None:
        """Set up browser session or API client."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up browser sessions, close connections."""
        ...

    # --- Feed / Content Discovery ---

    @abstractmethod
    async def fetch_feed(
        self, cursor: str | None = None, limit: int = 20
    ) -> tuple[list[PlatformPost], str | None]:
        """Fetch the home feed. Returns (posts, next_cursor)."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[PlatformPost]:
        """Search for posts matching a query."""
        ...

    @abstractmethod
    async def get_post_detail(self, post_id: str) -> PlatformPost:
        """Fetch a single post with full context."""
        ...

    @abstractmethod
    async def get_replies(self, post_id: str, limit: int = 20) -> list[PlatformPost]:
        """Fetch replies/comments on a post."""
        ...

    # --- Actions ---

    @abstractmethod
    async def like(self, post_id: str) -> PlatformActionResult:
        ...

    @abstractmethod
    async def reply(self, post_id: str, text: str) -> PlatformActionResult:
        ...

    @abstractmethod
    async def repost(self, post_id: str) -> PlatformActionResult:
        ...

    @abstractmethod
    async def quote(self, post_id: str, text: str) -> PlatformActionResult:
        ...

    async def follow(self, author_id: str) -> PlatformActionResult:
        raise NotImplementedError(f"{self.name} does not support follow")

    async def upvote(self, post_id: str) -> PlatformActionResult:
        raise NotImplementedError(f"{self.name} does not support upvote")

    async def post_original(
        self, text: str, media_paths: list[str] | None = None
    ) -> PlatformActionResult:
        raise NotImplementedError(f"{self.name} does not support original posts")

    # --- Navigation (browser-based platforms) ---

    async def navigate_home(self) -> None:
        """Navigate to the platform home."""
        ...

    async def scroll(self, times: int = 1) -> None:
        """Scroll the current page."""
        ...
