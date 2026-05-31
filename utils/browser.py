"""Multi-account browser session manager for X (Twitter).

Manages Playwright browser contexts with per-handle persistent auth
state.  Each X account gets its own ``BrowserContext`` backed by a
saved storage-state JSON file in the auth directory.

Usage::

    async with BrowserManager() as bm:
        page = await bm.get_page("cneuralnetwork")
        # … use page …
        await page.close()

First-time setup for a new account::

    async with BrowserManager(headless=False) as bm:
        await bm.login("cneuralnetwork")
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Self

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from utils.exceptions import XAuthError, XNavigationError

logger = logging.getLogger("x_persona")

# ---------------------------------------------------------------------------
# Defaults (overridable via env vars)
# ---------------------------------------------------------------------------

_DEFAULT_AUTH_DIR = Path(".auth")
_DEFAULT_HEADLESS = False
_DEFAULT_SLOW_MO = 50  # ms between Playwright actions
_DEFAULT_VIEWPORT = {"width": 1366, "height": 900}
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)
_LOGIN_TIMEOUT_MS = 180_000  # 3 minutes for manual login


class BrowserManager:
    """Manages a shared Playwright browser with per-account contexts.

    Parameters
    ----------
    auth_dir:
        Directory where ``{handle}.json`` auth-state files are stored.
        Created automatically if it doesn't exist.
    headless:
        Run the browser without a visible window.  Override with the
        ``X_HEADLESS`` env var (``"true"`` / ``"1"``).
    slow_mo:
        Milliseconds to wait between Playwright operations.  Helps with
        debugging and reduces the chance of anti-bot detection.
    """

    def __init__(
        self,
        *,
        auth_dir: Path | str | None = None,
        headless: bool | None = None,
        slow_mo: int | None = None,
    ) -> None:
        self._auth_dir = Path(
            auth_dir or os.getenv("X_AUTH_DIR", str(_DEFAULT_AUTH_DIR))
        )
        self._headless = (
            headless
            if headless is not None
            else os.getenv("X_HEADLESS", "").lower() in {"true", "1"}
        )
        self._slow_mo = slow_mo if slow_mo is not None else int(
            os.getenv("X_SLOW_MO", str(_DEFAULT_SLOW_MO))
        )

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}

    # -- async context manager ----------------------------------------------

    async def __aenter__(self) -> Self:
        self._auth_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            slow_mo=self._slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        logger.info(
            "Browser launched (headless=%s, slow_mo=%dms)",
            self._headless,
            self._slow_mo,
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        for handle, ctx in self._contexts.items():
            try:
                await self._save_state(handle, ctx)
                await ctx.close()
            except Exception:
                logger.warning("Failed to close context for @%s", handle, exc_info=True)
        self._contexts.clear()

        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    # -- public API ---------------------------------------------------------

    async def get_context(self, handle: str) -> BrowserContext:
        """Return (or create) the ``BrowserContext`` for *handle*.

        If a saved auth-state file exists for the handle it is loaded
        automatically.
        """
        handle = handle.lstrip("@").lower()

        if handle in self._contexts:
            return self._contexts[handle]

        auth_file = self._auth_state_path(handle)
        storage_state = str(auth_file) if auth_file.is_file() else None

        if storage_state:
            logger.info("Loading saved session for @%s", handle)
        else:
            logger.warning(
                "No saved session for @%s — run `await bm.login('%s')` first",
                handle,
                handle,
            )

        context = await self._browser.new_context(  # type: ignore[union-attr]
            storage_state=storage_state,
            viewport=_DEFAULT_VIEWPORT,
            user_agent=_DEFAULT_USER_AGENT,
            locale="en-US",
            timezone_id="Asia/Kolkata",
            color_scheme="dark",
        )
        self._contexts[handle] = context
        return context

    async def get_page(self, handle: str) -> Page:
        """Open a new ``Page`` inside the context for *handle*."""
        ctx = await self.get_context(handle)
        page = await ctx.new_page()
        return page

    async def login(self, handle: str) -> None:
        """Open a headed browser for manual login and save the session.

        The user must complete login within 3 minutes.  Once the browser
        reaches the home timeline the auth state is persisted to disk.
        """
        handle = handle.lstrip("@").lower()
        logger.info("Starting manual login flow for @%s …", handle)

        # Force a fresh context (no saved state)
        context = await self._browser.new_context(  # type: ignore[union-attr]
            viewport=_DEFAULT_VIEWPORT,
            user_agent=_DEFAULT_USER_AGENT,
            locale="en-US",
            timezone_id="Asia/Kolkata",
            color_scheme="dark",
        )
        page = await context.new_page()

        await page.goto("https://x.com/i/flow/login")
        print(
            f"\n{'=' * 60}\n"
            f"  Please log in as @{handle} in the browser window.\n"
            f"  You have 3 minutes.\n"
            f"{'=' * 60}\n"
        )

        try:
            await page.wait_for_url("**/home", timeout=_LOGIN_TIMEOUT_MS)
        except Exception as exc:
            await context.close()
            raise XNavigationError(
                f"Login timed out for @{handle}. Did not reach /home."
            ) from exc

        # Save the state
        auth_file = self._auth_state_path(handle)
        await context.storage_state(path=str(auth_file))
        logger.info("Auth state saved → %s", auth_file)
        print(f"  ✓ Session saved for @{handle}")

        # Store context for reuse in this session
        await page.close()
        self._contexts[handle] = context

    async def save_session(self, handle: str) -> Path:
        """Manually persist the current session for *handle* to disk.

        Returns the path to the saved auth-state JSON file.
        """
        handle = handle.lstrip("@").lower()
        ctx = self._contexts.get(handle)
        if ctx is None:
            raise XAuthError(f"No active context for @{handle}")
        path = self._auth_state_path(handle)
        await ctx.storage_state(path=str(path))
        logger.info("Session saved for @%s → %s", handle, path)
        return path

    @property
    def active_handles(self) -> list[str]:
        """List of handles with an active browser context."""
        return list(self._contexts.keys())

    # -- private helpers ----------------------------------------------------

    def _auth_state_path(self, handle: str) -> Path:
        return self._auth_dir / f"{handle}.json"

    async def _save_state(self, handle: str, ctx: BrowserContext) -> None:
        """Best-effort save of context state on shutdown."""
        try:
            path = self._auth_state_path(handle)
            await ctx.storage_state(path=str(path))
            logger.debug("Auto-saved session for @%s", handle)
        except Exception:
            logger.debug("Could not auto-save session for @%s", handle, exc_info=True)


# ---------------------------------------------------------------------------
# CLI entry-point for first-time login
# ---------------------------------------------------------------------------


def cli_login() -> None:
    """CLI command: ``uv run x-login``

    Prompts for a handle and opens a browser for manual login.
    """
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    handle = input("Enter X handle (without @): ").strip().lstrip("@")
    if not handle:
        print("No handle provided. Aborting.")
        sys.exit(1)

    async def _run() -> None:
        async with BrowserManager(headless=False) as bm:
            await bm.login(handle)

    asyncio.run(_run())


if __name__ == "__main__":
    cli_login()
