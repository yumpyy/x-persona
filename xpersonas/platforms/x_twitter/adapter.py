"""X/Twitter platform adapter: ports existing browser automation code."""

from __future__ import annotations

from xpersonas.core.models import AuthConfig, PlatformActionResult, PlatformPost
from xpersonas.platforms.base import PlatformAdapter
from xpersonas.platforms.registry import register_adapter


@register_adapter
class XTwitterAdapter(PlatformAdapter):
    """X/Twitter adapter using Playwright browser automation."""

    def __init__(self):
        self._browser_session = None
        self._page = None

    @property
    def name(self) -> str:
        return "x_twitter"

    @property
    def supported_actions(self) -> list[str]:
        return ["like", "reply", "quote", "repost", "follow", "original_post"]

    async def initialize(self, auth: AuthConfig, visible: bool = False) -> None:
        from xpersonas.platforms.x_twitter.browser import BrowserSession
        self._browser_session = BrowserSession(
            headless=not visible,
            auth_path=auth.session_path,
            slowmo=150 if visible else 0,
        )
        await self._browser_session.start()
        self._page = self._browser_session.page

    async def shutdown(self) -> None:
        if self._browser_session:
            await self._browser_session.stop()
            self._browser_session = None
            self._page = None

    async def fetch_feed(
        self, cursor: str | None = None, limit: int = 20
    ) -> tuple[list[PlatformPost], str | None]:
        from xpersonas.platforms.x_twitter.feed import parse_feed_articles
        posts = await parse_feed_articles(self._page, limit=limit)
        return posts, None

    async def search(self, query: str, limit: int = 20) -> list[PlatformPost]:
        from xpersonas.platforms.x_twitter.feed import search_posts
        return await search_posts(self._page, query, limit=limit)

    async def get_post_detail(self, post_id: str) -> PlatformPost:
        from xpersonas.platforms.x_twitter.feed import get_post_detail
        return await get_post_detail(self._page, post_id)

    async def get_replies(self, post_id: str, limit: int = 20) -> list[PlatformPost]:
        from xpersonas.platforms.x_twitter.feed import get_replies
        return await get_replies(self._page, post_id, limit=limit)

    async def like(self, post_id: str) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import like_on_page
        try:
            await like_on_page(self._page)
            return PlatformActionResult(success=True)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def reply(self, post_id: str, text: str) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import reply_on_page
        try:
            await reply_on_page(self._page, text)
            return PlatformActionResult(success=True)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def repost(self, post_id: str) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import repost_on_page
        try:
            await repost_on_page(self._page)
            return PlatformActionResult(success=True)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def quote(self, post_id: str, text: str) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import quote_on_page
        try:
            await quote_on_page(self._page, text)
            return PlatformActionResult(success=True)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def follow(self, author_id: str) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import follow_on_page
        try:
            await follow_on_page(self._page)
            return PlatformActionResult(success=True)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def post_original(
        self, text: str, media_paths: list[str] | None = None
    ) -> PlatformActionResult:
        from xpersonas.platforms.x_twitter.actions import post_on_page
        try:
            result = await post_on_page(self._page, text)
            return PlatformActionResult(success=True, platform_id=result)
        except Exception as e:
            return PlatformActionResult(success=False, error=str(e))

    async def navigate_home(self) -> None:
        if self._page:
            await self._page.goto("https://x.com/home", wait_until="domcontentloaded")

    async def scroll(self, times: int = 1) -> None:
        if self._page:
            for _ in range(times):
                await self._page.evaluate("window.scrollBy({top: 800, behavior: 'smooth'})")
                await self._page.wait_for_timeout(2000)
